from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
from database import engine
from routers import users, reservations
from middleware import RequestLifecycleMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Intentar crear/verificar las tablas al iniciar la aplicación
    try:
        models.Base.metadata.create_all(bind=engine)
        print("✅ Tablas de la base de datos verificadas/creadas con éxito.")
    except Exception as e:
        print(f"⚠️ Error al conectar con la base de datos durante el inicio: {e}")
    yield

app = FastAPI(title="API Reservas IRTRA - Render", lifespan=lifespan)

# Middleware para ciclo de vida de peticiones, tiempos y concurrencia
app.add_middleware(RequestLifecycleMiddleware)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(reservations.router, prefix="/reservations", tags=["reservations"])

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de Reservas IRTRA en Render"}
