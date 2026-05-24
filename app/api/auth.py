from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from app.core.security import get_password_hash, verify_password, create_access_token
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["auth"])

# Solicitud de Login vía JSON
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Verificar si ya existe un usuario con este correo
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )
    
    # Verificar si ya existe el código de estudiante
    if user_in.student_code:
        existing_student = db.query(User).filter(User.student_code == user_in.student_code).first()
        if existing_student:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El código de estudiante ya está registrado"
            )
            
    # Hashear contraseña
    hashed_pw = get_password_hash(user_in.password)
    
    # Crear usuario
    db_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        student_code=user_in.student_code or None,
        hashed_password=hashed_pw,
        role="CLIENT"  # Por defecto el registro público es para clientes
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    # Buscar usuario por correo electrónico
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Tu cuenta está desactivada"
        )
    
    # Generar token JWT
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        full_name=user.full_name,
        email=user.email
    )
