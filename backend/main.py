import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import Base, engine
from routers import r_auth, r_escenarios, r_points, r_proyectos, r_resultados, r_simulacion
from simulador_vehiculos import iniciar_simulador

Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ciclo de vida de la aplicación:
    - Startup : lanza el simulador de vehículos en background.
    - Shutdown: cancela el simulador limpiamente.
    """
    logger.info("🚀 Iniciando TranSystem Twins API...")

    simulador_task = asyncio.create_task(iniciar_simulador())
    logger.info("🚦 Simulador de vehículos iniciado en background.")

    yield  # La app corre aquí

    logger.info("🛑 Apagando simulador de vehículos...")
    simulador_task.cancel()
    try:
        await simulador_task
    except asyncio.CancelledError:
        logger.info("✅ Simulador detenido correctamente.")


app = FastAPI(title="TranSystem Twins API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(r_auth.router)
app.include_router(r_proyectos.router)
app.include_router(r_escenarios.router)
app.include_router(r_resultados.router)
app.include_router(r_points.router)
app.include_router(r_simulacion.router)


@app.post("/resultado-sumo", summary="endpoint de prueba para retorno de datos post simulacion sumo")
def recibir_resultado(resultado: dict):
    print(resultado)
    return {"status": "recibido"} if resultado else {"status": "error"}


@app.get("/")
def app_status():
    return {"status": "Ok"}
