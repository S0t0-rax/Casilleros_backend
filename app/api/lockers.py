from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile, BackgroundTasks
import asyncio
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import random
import re
import os
import shutil
import uuid
from pydantic import BaseModel

from app.database.session import get_db, SessionLocal
from app.models.locker import Locker
from app.models.user import User
from app.schemas.locker import LockerCreate, LockerResponse, LockerRent
from app.core.security import get_current_active_user, get_current_admin, get_current_client, get_current_user_optional

router = APIRouter(prefix="/lockers", tags=["lockers"])

# Esquema para actualización del cerrojo vía ESP32
class LockStatusUpdate(BaseModel):
    is_locked: bool

# Esquema para registro vía ESP32
class ESP32RegisterRequest(BaseModel):
    codigo: str
    pin: str
    casillero: int

@router.get("/", response_model=List[LockerResponse])
def get_lockers(db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    """
    Retorna la lista de todos los casilleros en el sistema.
    Permite acceso público. Oculta campos sensibles (PIN, comprobante) para no propietarios/administradores.
    """
    lockers = db.query(Locker).order_by(Locker.locker_number).all()
    
    # Si es ADMIN, puede ver toda la información de todos los casilleros
    if current_user and current_user.role == "ADMIN":
        return lockers
        
    # De lo contrario, expurgar de la sesión para no guardar los cambios en DB y ocultar PIN / recibo
    for l in lockers:
        db.expunge(l)
        if not current_user or l.assigned_user_id != current_user.id:
            l.pin_code = None
            l.payment_receipt_url = None
            
    return lockers

@router.post("/", response_model=LockerResponse, status_code=status.HTTP_201_CREATED)
def create_locker(locker_in: LockerCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """
    Crea un nuevo casillero en el sistema (Solo Administradores).
    """
    existing = db.query(Locker).filter(Locker.locker_number == locker_in.locker_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="El número de casillero ya existe")
    
    db_locker = Locker(
        locker_number=locker_in.locker_number,
        size=locker_in.size,
        price_per_hour=locker_in.price_per_hour,
        status="DISPONIBLE",
        is_locked=False
    )
    db.add(db_locker)
    db.commit()
    db.refresh(db_locker)
    return db_locker

@router.post("/{locker_id}/rent", response_model=LockerResponse)
def rent_locker(locker_id: int, rent_in: LockerRent, db: Session = Depends(get_db), client: User = Depends(get_current_client)):
    """
    Permite a un cliente alquilar un casillero disponible por N horas y le asigna un PIN.
    """
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(status_code=404, detail="Casillero no encontrado")
    
    if locker.status != "DISPONIBLE":
        raise HTTPException(status_code=400, detail="El casillero no está disponible")
    
    # Renta del casillero
    locker.status = "OCUPADO"
    locker.assigned_user_id = client.id
    locker.last_payment_at = datetime.now(timezone.utc)
    locker.occupied_until = datetime.now(timezone.utc) + timedelta(hours=rent_in.hours)
    
    # Asignar un PIN aleatorio de 4 dígitos y poner cerrojo abierto inicialmente
    locker.pin_code = f"{random.randint(1000, 9999)}"
    locker.is_locked = False
    
    db.commit()
    db.refresh(locker)
    return locker

@router.post("/{locker_id}/release", response_model=LockerResponse)
def release_locker(locker_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    Libera un casillero (lo vuelve a poner en DISPONIBLE) y limpia el PIN y cerrojo.
    Accesible para el cliente que lo alquiló o para cualquier Administrador.
    """
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(status_code=404, detail="Casillero no encontrado")
    
    if current_user.role != "ADMIN" and locker.assigned_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No tienes permisos para liberar este casillero"
        )
    
    locker.status = "DISPONIBLE"
    locker.assigned_user_id = None
    locker.occupied_until = None
    locker.last_payment_at = None
    locker.pin_code = None
    locker.is_locked = False
    
    db.commit()
    db.refresh(locker)
    return locker

@router.post("/{locker_id}/pay", response_model=LockerResponse)
def pay_and_extend(
    locker_id: int,
    hours: float = Form(...),
    receipt: UploadFile = File(...),
    db: Session = Depends(get_db),
    client: User = Depends(get_current_client)
):
    """
    Registra una solicitud de extensión de alquiler.
    Requiere que se suba el comprobante de pago de la extensión.
    """
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(status_code=404, detail="Casillero no encontrado")
        
    if locker.assigned_user_id != client.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Este casillero no está asignado a tu cuenta"
        )
        
    if not receipt or not receipt.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Por favor sube una foto de tu comprobante de pago para proceder con la extensión."
        )
        
    # Guardar archivo de comprobante de la extensión
    file_ext = os.path.splitext(receipt.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    abs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "app", "static", "receipts")
    os.makedirs(abs_path, exist_ok=True)
    full_destination = os.path.join(abs_path, unique_filename)
    
    try:
        with open(full_destination, "wb") as buffer:
            shutil.copyfileobj(receipt.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar el comprobante de extensión: {e}")
        
    locker.status = "ESPERANDO_VERIFICACION"
    locker.pending_rent_hours = hours
    locker.payment_receipt_url = f"/static/receipts/{unique_filename}"
    locker.last_payment_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(locker)
    return locker

@router.post("/{locker_id}/close", response_model=LockerResponse)
def close_locker_client(locker_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    Permite al cliente (o administrador) cerrar la puerta de su casillero asignado.
    Esto bloquea el casillero e inicia el contador del tiempo de alquiler si no ha comenzado.
    """
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(status_code=404, detail="Casillero no encontrado")
        
    if current_user.role != "ADMIN" and locker.assigned_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No tienes permisos para interactuar con este casillero"
        )
        
    locker.is_locked = True
    
    # Si el casillero se cierra y el temporizador aún no empezó, iniciarlo
    if locker.status == "OCUPADO" and locker.occupied_until is None and locker.pending_rent_hours:
        locker.occupied_until = datetime.now(timezone.utc) + timedelta(hours=locker.pending_rent_hours)
        
    db.commit()
    db.refresh(locker)
    return locker


# ----------------- ENDPOINTS PARA ESP32 -----------------

@router.get("/esp32/sync")
def sync_lockers_esp32(db: Session = Depends(get_db)):
    """
    Retorna la lista de casilleros ocupados y sus PINs/códigos en formato compatible con el parser de C++.
    """
    lockers = db.query(Locker).filter(Locker.status == "OCUPADO").all()
    result = []
    for l in lockers:
        # Buscar el código de estudiante del usuario asignado
        student_code = "1234567890"  # fallback por defecto
        if l.assigned_user_id:
            user = db.query(User).filter(User.id == l.assigned_user_id).first()
            if user and user.student_code:
                student_code = user.student_code
        
        # Extraer el número entero del locker_number (ej: C-12 -> 12)
        digits = re.findall(r'\d+', l.locker_number)
        casillero_num = int(digits[0]) if digits else 1
        
        result.append({
            "codigo": student_code,
            "pin": l.pin_code or "0000",
            "casillero": casillero_num
        })
    return result

@router.post("/esp32/register")
def register_locker_esp32(req: ESP32RegisterRequest, db: Session = Depends(get_db)):
    """
    Permite registrar la asignación de un casillero directamente desde el teclado del ESP32.
    """
    # Buscar usuario por código de estudiante
    user = db.query(User).filter(User.student_code == req.codigo).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado con ese codigo")
    
    # Buscar casillero que termine con el número
    locker = db.query(Locker).filter(Locker.locker_number.like(f"%{req.casillero}")).first()
    if not locker:
        # Buscar por correspondencia exacta
        locker = db.query(Locker).filter(Locker.locker_number == f"C-{req.casillero}").first()
        
    if not locker:
        raise HTTPException(status_code=404, detail=f"Casillero {req.casillero} no encontrado")
        
    if locker.status != "DISPONIBLE":
        raise HTTPException(status_code=400, detail="El casillero no está disponible")
        
    # Asignar renta
    locker.status = "OCUPADO"
    locker.assigned_user_id = user.id
    locker.last_payment_at = datetime.now(timezone.utc)
    # Por defecto 3 días (72 horas) como en el cronómetro físico del ESP32
    locker.occupied_until = datetime.now(timezone.utc) + timedelta(days=3)
    locker.pin_code = req.pin
    locker.is_locked = True
    
    db.commit()
    db.refresh(locker)
    return {"status": "OK", "locker_number": locker.locker_number}

@router.get("/{locker_number}/status-esp32")
def get_locker_status_esp32(locker_number: str, db: Session = Depends(get_db)):
    """
    Consulta el estado detallado de un casillero por su número de casillero.
    """
    locker = db.query(Locker).filter(Locker.locker_number == locker_number).first()
    if not locker:
        raise HTTPException(status_code=404, detail="Casillero no encontrado")
        
    time_left_seconds = 0
    if locker.occupied_until:
        now = datetime.now(timezone.utc)
        if locker.occupied_until > now:
            time_left_seconds = int((locker.occupied_until - now).total_seconds())
            
    return {
        "locker_number": locker.locker_number,
        "status": locker.status,
        "is_locked": locker.is_locked,
        "pin_code": locker.pin_code,
        "time_left_seconds": time_left_seconds
    }

@router.post("/{locker_number}/status-esp32")
def update_locker_status_esp32(locker_number: str, status_in: LockStatusUpdate, db: Session = Depends(get_db)):
    """
    Actualiza el estado físico de bloqueo (cerrojo) de un casillero.
    """
    locker = db.query(Locker).filter(Locker.locker_number == locker_number).first()
    if not locker:
        raise HTTPException(status_code=404, detail="Casillero no encontrado")
        
    locker.is_locked = status_in.is_locked
    
    # Si se cierra el casillero y el temporizador aun no empezo, iniciarlo
    if locker.is_locked and locker.status == "OCUPADO" and locker.occupied_until is None and locker.pending_rent_hours:
        locker.occupied_until = datetime.now(timezone.utc) + timedelta(hours=locker.pending_rent_hours)
        
    db.commit()
    db.refresh(locker)
    return {
        "locker_number": locker.locker_number,
        "is_locked": locker.is_locked,
        "status": "OK"
    }

# ----------------- ACCIONES DE ADMINISTRACIÓN DEL CERROJO -----------------

@router.post("/{locker_id}/lock-admin", response_model=LockerResponse)
def lock_locker_admin(locker_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """
    Bloquea remotamente el cerrojo de un casillero (Solo Administradores).
    """
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(status_code=404, detail="Casillero no encontrado")
        
    locker.is_locked = True
    db.commit()
    db.refresh(locker)
    return locker

@router.post("/{locker_id}/unlock-admin", response_model=LockerResponse)
def unlock_locker_admin(locker_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """
    Desbloquea remotamente el cerrojo de un casillero (Solo Administradores).
    """
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(status_code=404, detail="Casillero no encontrado")
        
    locker.is_locked = False
    db.commit()
    db.refresh(locker)
    return locker

@router.post("/{locker_id}/rent-public", response_model=LockerResponse)
def rent_locker_public(
    locker_id: int,
    background_tasks: BackgroundTasks,
    hours: float = Form(...),
    discount_code: Optional[str] = Form(None),
    receipt: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Permite alquilar un casillero de forma pública (con o sin login).
    Si se aplica código de descuento, se requiere que el usuario esté logueado.
    Sube un archivo de comprobante de pago que se almacena en el servidor (solo si el costo es > 0).
    """
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(status_code=404, detail="Casillero no encontrado")
        
    if locker.status != "DISPONIBLE":
        raise HTTPException(status_code=400, detail="El casillero no está disponible")
        
    # Si ingresó código de descuento, verificar autenticación
    if discount_code and not current_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes iniciar sesión para aplicar códigos de descuento."
        )
        
    # Calcular precio final
    base_price = hours * locker.price_per_hour
    discount = 0.0
    if discount_code and current_user:
        code = discount_code.upper().strip()
        if code == "UPSA":
            discount = 1.0  # 100% descuento
        elif code == "PROMO50":
            discount = 0.5  # 50% descuento
            
    final_price = base_price * (1.0 - discount)
    
    # Si el costo es mayor a 0, se requiere subir comprobante
    if final_price > 0.0 and (not receipt or not receipt.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Por favor sube una foto de tu comprobante de pago para proceder."
        )
        
    unique_filename = None
    if receipt and receipt.filename:
        # Guardar archivo de comprobante en el directorio estático
        file_ext = os.path.splitext(receipt.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Asegurar que existe la ruta absoluta
        abs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "app", "static", "receipts")
        os.makedirs(abs_path, exist_ok=True)
        full_destination = os.path.join(abs_path, unique_filename)
        
        try:
            with open(full_destination, "wb") as buffer:
                shutil.copyfileobj(receipt.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al guardar el comprobante: {e}")
            
    # Renta del casillero
    if final_price > 0.0:
        locker.status = "ESPERANDO_VERIFICACION"
        locker.pin_code = None
        locker.occupied_until = None
    else:
        # Si es gratis, se aprueba automaticamente
        locker.status = "OCUPADO"
        locker.pin_code = f"{random.randint(1000, 9999)}"
        locker.occupied_until = None
        locker.approved_at = datetime.now(timezone.utc)
        background_tasks.add_task(auto_start_locker_timer, locker.id)
        
    locker.assigned_user_id = current_user.id if current_user else None
    locker.last_payment_at = datetime.now(timezone.utc)
    locker.pending_rent_hours = hours
    locker.payment_receipt_url = f"/static/receipts/{unique_filename}" if unique_filename else None
    locker.is_locked = False
    
    db.commit()
    db.refresh(locker)
    return locker

async def auto_start_locker_timer(locker_id: int):
    await asyncio.sleep(300) # 5 minutos
    db = SessionLocal()
    try:
        locker = db.query(Locker).filter(Locker.id == locker_id).first()
        if locker and locker.status == "OCUPADO" and locker.occupied_until is None and locker.pending_rent_hours:
            locker.occupied_until = datetime.now(timezone.utc) + timedelta(hours=locker.pending_rent_hours)
            db.commit()
    finally:
        db.close()

@router.post("/{locker_id}/approve", response_model=LockerResponse)
def approve_rental(locker_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(status_code=404, detail="Casillero no encontrado")
        
    if locker.status != "ESPERANDO_VERIFICACION":
        raise HTTPException(status_code=400, detail="El casillero no está esperando verificación")
        
    # Si pin_code ya está asignado, se trata de una extensión de alquiler
    if locker.pin_code is not None:
        if locker.occupied_until and locker.occupied_until > datetime.now(timezone.utc):
            locker.occupied_until = locker.occupied_until + timedelta(hours=locker.pending_rent_hours)
        else:
            locker.occupied_until = datetime.now(timezone.utc) + timedelta(hours=locker.pending_rent_hours)
        
        locker.status = "OCUPADO"
        locker.pending_rent_hours = None
    else:
        # Alquiler nuevo
        locker.status = "OCUPADO"
        locker.pin_code = f"{random.randint(1000, 9999)}"
        locker.approved_at = datetime.now(timezone.utc)
        
        # Iniciar tarea para comenzar a descontar el tiempo si en 5 mins no cierra la puerta
        background_tasks.add_task(auto_start_locker_timer, locker.id)
        
    db.commit()
    db.refresh(locker)
    return locker

@router.post("/{locker_id}/reject", response_model=LockerResponse)
def reject_rental(locker_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    locker = db.query(Locker).filter(Locker.id == locker_id).first()
    if not locker:
        raise HTTPException(status_code=404, detail="Casillero no encontrado")
        
    if locker.status != "ESPERANDO_VERIFICACION":
        raise HTTPException(status_code=400, detail="El casillero no está esperando verificación")
        
    # Si pin_code ya está asignado, es una extensión rechazada
    if locker.pin_code is not None:
        # Volvemos a ponerlo en OCUPADO sin alterar su alquiler actual
        locker.status = "OCUPADO"
        locker.pending_rent_hours = None
        locker.payment_receipt_url = None
    else:
        # Alquiler nuevo rechazado
        locker.status = "DISPONIBLE"
        locker.assigned_user_id = None
        locker.pending_rent_hours = None
        locker.payment_receipt_url = None
        
    db.commit()
    db.refresh(locker)
    return locker


