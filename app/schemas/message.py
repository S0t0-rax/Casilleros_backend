from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Esquemas de Mensajes
class MessageBase(BaseModel):
    subject: str
    content: str

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: int
    user_id: int
    response: Optional[str] = None
    status: str
    created_at: datetime
    verified_at: Optional[datetime] = None
    verified_by_id: Optional[int] = None
    user_email: Optional[str] = None  # Útil para el administrador para ver quién envió el mensaje

    class Config:
        orm_mode = True

class MessageVerify(BaseModel):
    response: Optional[str] = None
