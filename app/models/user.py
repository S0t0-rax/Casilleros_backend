from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    student_code = Column(String, unique=True, index=True, nullable=True)
    role = Column(String, default="CLIENT", nullable=False)  # "ADMIN" o "CLIENT"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    lockers = relationship("Locker", back_populates="assigned_user")
    messages = relationship("Message", back_populates="user", foreign_keys="Message.user_id")
