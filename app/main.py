from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.database.session import engine, Base, SessionLocal
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.lockers import router as lockers_router
from app.api.messages import router as messages_router
from app.models.user import User
from app.models.locker import Locker
from app.core.security import get_password_hash
from app.core.email import send_warning_email
import asyncio
from datetime import datetime, timezone, timedelta

async def check_locker_warnings():
    while True:
        try:
            db = SessionLocal()
            lockers = db.query(Locker).filter(
                Locker.status == "OCUPADO",
                Locker.occupied_until.isnot(None),
                Locker.warning_sent == False
            ).all()
            
            now = datetime.now(timezone.utc)
            for locker in lockers:
                time_left = locker.occupied_until - now
                # Si le quedan 5 minutos o menos (pero no ha expirado aún)
                if timedelta(minutes=0) < time_left <= timedelta(minutes=5):
                    target_email = locker.contact_email
                    if not target_email and locker.assigned_user_id:
                        user = db.query(User).filter(User.id == locker.assigned_user_id).first()
                        if user:
                            target_email = user.email
                    
                    if target_email:
                        send_warning_email(target_email, locker.locker_number)
                        
                    locker.warning_sent = True
                    db.commit()
            db.close()
        except Exception as e:
            print(f"Error en loop de warnings: {e}")
        
        await asyncio.sleep(60) # Revisa cada minuto

# Crear y montar directorio de archivos estáticos para los recibos de pago
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
RECEIPTS_DIR = os.path.join(STATIC_DIR, "receipts")
os.makedirs(RECEIPTS_DIR, exist_ok=True)

# Crear las tablas en la base de datos (Supabase / local)
# SQLAlchemy creará solo las tablas que no existan previamente
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Locker Project API", 
    version="1.0.0",
    description="Backend en FastAPI para gestionar un sistema de casilleros responsivo"
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Habilitar CORS para permitir llamadas HTTP desde Angular (localhost:4200)
# También se añade "*" en caso de pruebas con IP local en móviles
# Permitir cualquier origen en producción (Vercel)
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar los endpoints
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(lockers_router, prefix="/api/v1")
app.include_router(messages_router, prefix="/api/v1")
# Exponer los endpoints de lockers también bajo el prefijo /api (sin v1) para compatibilidad con dispositivos ESP32
app.include_router(lockers_router, prefix="/api")

@app.on_event("startup")
def startup_event():
    asyncio.create_task(check_locker_warnings())
    
    # Inicialización de datos semilla (Seed) para pruebas rápidas
    db = SessionLocal()
    try:
        # 1. Sembrado de usuarios
        if db.query(User).count() == 0:
            print("Sembrando usuarios por defecto en la base de datos...")
            admin_user = User(
                email="admin@casilleros.com",
                full_name="Administrador Principal",
                hashed_password=get_password_hash("admin123"),
                role="ADMIN"
            )
            client_user = User(
                email="cliente@casilleros.com",
                full_name="Carlos Pérez",
                hashed_password=get_password_hash("cliente123"),
                role="CLIENT"
            )
            db.add(admin_user)
            db.add(client_user)
            db.commit()
            print("Usuarios sembrados con éxito.")

        # 2. Sembrado de casilleros de prueba
        # Si existen casilleros viejos del formato anterior C-101, limpiarlos
        if db.query(Locker).filter(Locker.locker_number == "C-101").first():
            print("Limpiando casilleros antiguos con formato antiguo...")
            db.query(Locker).delete()
            db.commit()

        if db.query(Locker).count() == 0:
            print("Sembrando casilleros de prueba (C-1 a C-12)...")
            lockers_to_create = [
                # Pequeños (1 a 4)
                {"number": "C-1", "size": "PEQUEÑO", "price": 2.00},
                {"number": "C-2", "size": "PEQUEÑO", "price": 2.00},
                {"number": "C-3", "size": "PEQUEÑO", "price": 2.00},
                {"number": "C-4", "size": "PEQUEÑO", "price": 2.00},
                # Medianos (5 a 8)
                {"number": "C-5", "size": "MEDIANO", "price": 2.00},
                {"number": "C-6", "size": "MEDIANO", "price": 2.00},
                {"number": "C-7", "size": "MEDIANO", "price": 2.00},
                {"number": "C-8", "size": "MEDIANO", "price": 2.00},
                # Grandes (9 a 12)
                {"number": "C-9", "size": "GRANDE", "price": 2.00},
                {"number": "C-10", "size": "GRANDE", "price": 2.00},
                {"number": "C-11", "size": "GRANDE", "price": 2.00},
                {"number": "C-12", "size": "GRANDE", "price": 2.00},
            ]
            for item in lockers_to_create:
                locker = Locker(
                    locker_number=item["number"],
                    size=item["size"],
                    price_per_hour=item["price"],
                    status="DISPONIBLE",
                    is_locked=False
                )
                db.add(locker)
            db.commit()
            print("Casilleros sembrados con éxito.")
    except Exception as e:
        print(f"Error al sembrar datos iniciales: {e}")
    finally:
        db.close()

@app.get("/")
def read_root():
    return {
        "estado": "Online",
        "proyecto": "Locker Management API",
        "documentacion": "/docs"
    }

@app.get("/api/status")
def read_status():
    return {
        "status": "Online",
        "message": "Servidor FastAPI accesible"
    }
