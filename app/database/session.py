from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Adaptar la URL de conexión de PostgreSQL para usar el driver psycopg (v3) en Python 3.14
database_url = settings.DATABASE_URL
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

# Crear motor de base de datos
engine = create_engine(
    database_url,
    pool_pre_ping=True  # Verifica si la conexión sigue viva antes de usarla, útil para Supabase
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependencia para obtener la sesión de base de datos en los endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
