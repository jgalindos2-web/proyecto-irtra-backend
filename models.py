from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    carne = Column(String, unique=True, index=True, nullable=False)
    dpi = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="cliente", nullable=False)  # 'cliente' o 'administrador'

    reservations = relationship(
        "Reservation", 
        foreign_keys="[Reservation.user_id]", 
        back_populates="owner"
    )
    delivered_reservations = relationship(
        "Reservation", 
        foreign_keys="[Reservation.delivered_by_id]", 
        back_populates="delivered_by"
    )

class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    reservation_code = Column(String, unique=True, index=True, nullable=False)
    park_name = Column(String, nullable=False)
    ticket_type = Column(String, nullable=False, default="Entrada General")
    visit_date = Column(Date, nullable=False)
    beneficiaries_count = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="PENDIENTE")  # PENDIENTE, ENTREGADO
    delivered_at = Column(DateTime, nullable=True)
    delivered_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    version_id = Column(Integer, nullable=False, default=1)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    __mapper_args__ = {
        "version_id_col": version_id
    }

    owner = relationship("User", foreign_keys=[user_id], back_populates="reservations")
    delivered_by = relationship("User", foreign_keys=[delivered_by_id], back_populates="delivered_reservations")
