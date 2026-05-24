from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.session import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String, nullable=False)
    content = Column(String, nullable=False)
    response = Column(String, nullable=True)
    status = Column(String, default="PENDIENTE", nullable=False)  # "PENDIENTE", "VERIFICADO", "RESPONDIDO"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relaciones
    user = relationship("User", back_populates="messages", foreign_keys=[user_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])
