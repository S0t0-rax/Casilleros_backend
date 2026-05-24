from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from app.database.session import get_db
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse, MessageVerify
from app.core.security import get_current_active_user, get_current_admin, get_current_client

router = APIRouter(prefix="/messages", tags=["messages"])

@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(message_in: MessageCreate, db: Session = Depends(get_db), client: User = Depends(get_current_client)):
    """
    Permite a un cliente enviar un mensaje de ayuda o reclamo (Soporte).
    """
    db_message = Message(
        user_id=client.id,
        subject=message_in.subject,
        content=message_in.content,
        status="PENDIENTE"
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

@router.get("/my", response_model=List[MessageResponse])
def get_my_messages(db: Session = Depends(get_db), client: User = Depends(get_current_client)):
    """
    Permite a un cliente ver todos los mensajes de soporte que ha enviado.
    """
    return db.query(Message).filter(Message.user_id == client.id).order_by(Message.created_at.desc()).all()

@router.get("/admin", response_model=List[MessageResponse])
def get_all_messages(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """
    Permite a un administrador ver todos los mensajes en el sistema (ordenados por pendientes primero).
    """
    messages = db.query(Message).order_by(Message.status.desc(), Message.created_at.desc()).all()
    # Adjuntar email del usuario emisor para mostrar en la interfaz del administrador
    for m in messages:
        m.user_email = m.user.email
    return messages

@router.post("/{message_id}/verify", response_model=MessageResponse)
def verify_message(message_id: int, verify_in: MessageVerify, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """
    Permite a un administrador verificar un mensaje y opcionalmente adjuntar una respuesta.
    """
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    
    message.status = "VERIFICADO"
    message.response = verify_in.response
    message.verified_at = datetime.now(timezone.utc)
    message.verified_by_id = admin.id
    
    db.commit()
    db.refresh(message)
    message.user_email = message.user.email
    return message
