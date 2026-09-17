from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status
import uuid
import models, schemas, auth

# Reglas de negocio para parques y tipos de ticket válidos
VALID_TICKET_TYPES = {
    "Xetulul": [
        "Brazalete Juegos Ilimitados",
        "Ticket Juegos",
        "Entrada General"
    ],
    "Xocomil": [
        "Entrada Xocomil"
    ],
    "Xocomil y Xetulha": [
        "Entrada Combo Xocomil y Xetulha"
    ]
}

def get_user_by_carne(db: Session, carne: str):
    return db.query(models.User).filter(models.User.carne == carne).first()

def get_user_by_dpi(db: Session, dpi: str):
    return db.query(models.User).filter(models.User.dpi == dpi).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        carne=user.carne,
        dpi=user.dpi,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=user.role or "cliente"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def validate_park_and_ticket(park_name: str, ticket_type: str):
    """Valida que el tipo de ticket o brazalete coincida con las opciones del parque."""
    # Mapeo flexible
    park_key = None
    for key in VALID_TICKET_TYPES:
        if key.lower() in park_name.lower():
            park_key = key
            break

    if not park_key:
        # Permitir parques genéricos con entrada general por compatibilidad
        return True

    allowed = VALID_TICKET_TYPES[park_key]
    if ticket_type not in allowed and "Entrada" not in ticket_type and "Brazalete" not in ticket_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de ticket '{ticket_type}' no válido para {park_name}. Opciones válidas: {', '.join(allowed)}"
        )
    return True

def create_reservation(db: Session, reservation: schemas.ReservationCreate, user_id: int):
    # Validar ticket y parque
    validate_park_and_ticket(reservation.park_name, reservation.ticket_type)

    # Generar un código de reserva único
    reservation_code = str(uuid.uuid4())[:8].upper()
    
    db_reservation = models.Reservation(
        park_name=reservation.park_name,
        ticket_type=reservation.ticket_type,
        visit_date=reservation.visit_date,
        beneficiaries_count=reservation.beneficiaries_count,
        status="PENDIENTE",
        reservation_code=reservation_code,
        user_id=user_id,
        version_id=1
    )
    db.add(db_reservation)
    db.commit()
    db.refresh(db_reservation)
    return db_reservation

def get_user_reservations(db: Session, user_id: int):
    return db.query(models.Reservation).filter(models.Reservation.user_id == user_id).order_by(models.Reservation.id.desc()).all()

def get_all_reservations(
    db: Session, 
    park_name: str = None, 
    status_filter: str = None, 
    search: str = None
):
    """Obtiene todas las reservas con filtros para el panel de control de entrega del Administrador."""
    query = db.query(models.Reservation).join(models.User, models.Reservation.user_id == models.User.id)
    
    if park_name:
        query = query.filter(models.Reservation.park_name.ilike(f"%{park_name}%"))
        
    if status_filter:
        query = query.filter(models.Reservation.status == status_filter)
        
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                models.Reservation.reservation_code.ilike(search_pattern),
                models.User.carne.ilike(search_pattern),
                models.User.dpi.ilike(search_pattern),
                models.User.full_name.ilike(search_pattern)
            )
        )
        
    return query.order_by(models.Reservation.visit_date.desc(), models.Reservation.id.desc()).all()

def deliver_reservation(db: Session, reservation_id: int, admin_id: int, new_status: str = "ENTREGADO"):
    """
    Control de entrega con bloqueo de concurrencia optimista (version_id):
    Si dos administradores intentan marcar la entrega en paralelo, SQLAlchemy detectará conflicto
    y elevará StaleDataError, garantizando que el ticket no sea entregado dos veces.
    """
    reservation = db.query(models.Reservation).filter(models.Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva no encontrada"
        )
        
    if reservation.status == "ENTREGADO":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Este ticket ya fue entregado el {reservation.delivered_at.strftime('%Y-%m-%d %H:%M') if reservation.delivered_at else ''}."
        )

    reservation.status = new_status
    reservation.delivered_at = datetime.now(timezone.utc)
    reservation.delivered_by_id = admin_id

    db.commit()
    db.refresh(reservation)
    return reservation
