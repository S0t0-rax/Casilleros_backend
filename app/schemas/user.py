from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# Esquemas de Usuario
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    student_code: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
    student_code: Optional[str] = None

class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True

# Esquemas de Tokens de Autenticación
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str
    email: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
