from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional, Literal

class UserBase(BaseModel):
    carne: str
    dpi: str
    full_name: str
    role: Optional[Literal["cliente", "administrador"]] = "cliente"

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class ReservationBase(BaseModel):
    park_name: str
    ticket_type: str = "Entrada General"
    visit_date: date
    beneficiaries_count: int

class ReservationCreate(ReservationBase):
    pass

class ReservationDeliver(BaseModel):
    status: Literal["ENTREGADO", "CANCELADO"] = "ENTREGADO"

class Reservation(ReservationBase):
    id: int
    reservation_code: str
    status: str
    delivered_at: Optional[datetime] = None
    delivered_by_id: Optional[int] = None
    version_id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
    role: Optional[str] = "cliente"

class TokenData(BaseModel):
    carne: Optional[str] = None
    role: Optional[str] = None
