from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import schemas, crud, models, auth, database

router = APIRouter()

@router.post("/", response_model=schemas.Reservation)
def create_reservation(
    reservation: schemas.ReservationCreate, 
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    """Crea una compra o reserva de tickets/brazaletes para el usuario autenticado."""
    if reservation.beneficiaries_count > 5:
        raise HTTPException(status_code=400, detail="El máximo de beneficiarios permitidos es 5")
    if reservation.beneficiaries_count < 1:
        raise HTTPException(status_code=400, detail="Debe indicar al menos 1 beneficiario")
    return crud.create_reservation(db=db, reservation=reservation, user_id=current_user.id)

@router.get("/", response_model=List[schemas.Reservation])
def read_user_reservations(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    """Lista las compras y reservas del cliente autenticado."""
    return crud.get_user_reservations(db, user_id=current_user.id)

@router.get("/admin/all", response_model=List[schemas.Reservation])
def read_all_reservations_for_admin(
    park_name: Optional[str] = Query(None, description="Filtrar por parque"),
    status_filter: Optional[str] = Query(None, description="Filtrar por estado (PENDIENTE, ENTREGADO)"),
    search: Optional[str] = Query(None, description="Buscar por carné, DPI o código"),
    admin_user: models.User = Depends(auth.require_role(["administrador"])),
    db: Session = Depends(database.get_db)
):
    """
    Panel de Control de Entrega para Administradores:
    Permite consultar y filtrar todas las compras del sistema para entrega de brazaletes y tickets.
    """
    return crud.get_all_reservations(
        db=db, 
        park_name=park_name, 
        status_filter=status_filter, 
        search=search
    )

@router.put("/{reservation_id}/deliver", response_model=schemas.Reservation)
def deliver_tickets_and_wristbands(
    reservation_id: int,
    payload: schemas.ReservationDeliver = schemas.ReservationDeliver(),
    admin_user: models.User = Depends(auth.require_role(["administrador"])),
    db: Session = Depends(database.get_db)
):
    """
    Acción exclusiva de Administrador:
    Registra la entrega física de los tickets o brazaletes para juegos o entrada al visitante.
    Maneja el control de concurrencia optimista para evitar doble entrega.
    """
    return crud.deliver_reservation(
        db=db, 
        reservation_id=reservation_id, 
        admin_id=admin_user.id,
        new_status=payload.status
    )
