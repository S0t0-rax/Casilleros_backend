from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.user import UserResponse, UserUpdate
from app.models.user import User
from app.core.security import get_current_active_user

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_active_user)):
    """
    Retorna la información del usuario autenticado actualmente.
    """
    return current_user

@router.put("/me", response_model=UserResponse)
def update_user_me(
    user_update: UserUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """
    Actualiza la información del usuario autenticado actualmente.
    """
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
        
    if user_update.student_code is not None:
        if user_update.student_code != "":
            # Verificar que no esté en uso por otro usuario
            existing = db.query(User).filter(
                User.student_code == user_update.student_code, 
                User.id != current_user.id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El código de estudiante ya está en uso"
                )
            current_user.student_code = user_update.student_code
        else:
            current_user.student_code = None

    db.commit()
    db.refresh(current_user)
    return current_user
