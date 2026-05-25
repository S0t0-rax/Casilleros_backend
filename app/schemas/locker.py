from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Esquemas de Casillero
class LockerBase(BaseModel):
    locker_number: str
    size: str
    price_per_hour: float

class LockerCreate(LockerBase):
    pass

class LockerResponse(LockerBase):
    id: int
    status: str
    assigned_user_id: Optional[int] = None
    occupied_until: Optional[datetime] = None
    last_payment_at: Optional[datetime] = None
    pin_close: Optional[str] = None
    pin_open: Optional[str] = None
    is_locked: bool = False
    payment_receipt_url: Optional[str] = None
    pending_rent_hours: Optional[float] = None
    approved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class LockerRent(BaseModel):
    hours: float
