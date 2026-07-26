import random
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def saludar():
    return {"Hola": "Mundo"}

@app.get("/ping")
def ping():
    res = f"{random.randint(0,255)}ms"
    return {"ping": res}
