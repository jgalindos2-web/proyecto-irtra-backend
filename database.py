import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Obtener URL de la variable de entorno
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://irtra_user:irtra_password@127.0.0.1:5433/irtra_db")

# Ajuste automático para SQLAlchemy 2.0+ si Render envía 'postgres://'
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configurar connect_args y pooling según el motor de base de datos
connect_args = {"connect_timeout": 10}
engine_kwargs = {}

if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False
else:
    if "postgresql" in DATABASE_URL and "127.0.0.1" in DATABASE_URL:
        connect_args["options"] = "-c client_encoding=utf8"
    # Configuración de Connection Pool optimizada para evitar saturación del servidor
    engine_kwargs.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "15")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "300")),
        "pool_pre_ping": True  # Verifica que la conexión esté viva antes de emitir queries
    })

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

@contextmanager
def get_db_session(factory=None):
    """
    Gestor de contexto para operaciones atómicas puntuales:
    Abre la sesión, ejecuta la acción y la cierra de forma inmediata en el bloque finally,
    asegurando que las conexiones se liberen al pool sin saturar el servidor.
    """
    session_factory = factory or SessionLocal
    db = session_factory()
    try:
        yield db
    finally:
        db.close()

def get_db():
    """
    Generador de sesión para dependencias de FastAPI:
    Garantiza que la sesión se cierre inmediatamente tras finalizar la ejecución del endpoint.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
