from fastapi import FastAPI

from core.database import Base, engine
from routers import r_auth, r_escenarios, r_points

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(r_auth.router)
app.include_router(r_escenarios.router)
app.include_router(r_points.router)

@app.post("/resultado-sumo", summary="endpoint de prueba para retorno de datos post simulacion sumo")
def recibir_resultado(resultado: dict):
    print(resultado)
    return {"status": "recibido"} if resultado else {"status": error}

@app.get("/")
def app_status():
    return {"status": "Ok"}
