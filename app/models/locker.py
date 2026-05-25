from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.database.session import Base

class Locker(Base):
    __tablename__ = "lockers"

    id = Column(Integer, primary_key=True, index=True)
    locker_number = Column(String, unique=True, index=True, nullable=False)
    size = Column(String, nullable=False)  # "PEQUEÑO", "MEDIANO", "GRANDE"
    status = Column(String, default="DISPONIBLE", nullable=False)  # "DISPONIBLE", "OCUPADO", "MANTENIMIENTO"
    price_per_hour = Column(Float, nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    occupied_until = Column(DateTime(timezone=True), nullable=True)
    last_payment_at = Column(DateTime(timezone=True), nullable=True)
    pin_close = Column(String, nullable=True)
    pin_open = Column(String, nullable=True)
    is_locked = Column(Boolean, default=False, nullable=False)
    payment_receipt_url = Column(String, nullable=True)
    pending_rent_hours = Column(Float, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    contact_email = Column(String, nullable=True)
    warning_sent = Column(Boolean, default=False, nullable=False)

    # Relaciones
    assigned_user = relationship("User", back_populates="lockers")
