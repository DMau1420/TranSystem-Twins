from fastapi import FastAPI

from core.database import Base, engine
from routers import r_auth, r_escenarios

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(r_auth.router)
app.include_router(r_escenarios.router)
@app.get("/")
def app_status():
    return {"status": "Ok"}