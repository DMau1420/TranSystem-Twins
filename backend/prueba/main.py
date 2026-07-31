import random

from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String, Numeric
from sqlalchemy.orm import sessionmaker, declarative_base, Session

engine = create_engine("postgresql+psycopg2://admin:adminpassword@localhost:5432/ecommerce_db")
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Producto(Base):
    __tablename__ = "productos"
    producto_id = Column(Integer, primary_key=True)
    nombre = Column(String)
    precio = Column(Numeric)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()

@app.get("/")
def saludar():
    return {"Hola": "Mundo"}

@app.get("/ping")
def ping():
    res = f"{random.randint(0,255)}ms"
    return {"ping": res}

@app.get("/productos")
def obtener_productos(db: Session = Depends(get_db)):
    return db.query(Producto).all()

@app.get("/get-sumo-json")
def generar_json_sumo():
    we = round(random.random(),2) 
    ew = round(random.random(),2) 
    ns = round(random.random(),2) 
    d1 = random.randint(1,100)
    d2 = random.randint(1,100)
    d3 = random.randint(1,100)
    d4 = random.randint(1,100)
    estado_list = ["GrGr", "YrYr", "rGrG", "ryry"]
    random.shuffle(estado_list)
    e1 = estado_list.pop()
    e2 = estado_list.pop()
    e3 = estado_list.pop()
    e4 = estado_list.pop()
    seed = random.randint(0,33550336)
    res_json = {"demanda": 
                {"we":we,"ew":ew,"ns":ns},
                "semaforo": {
                    "fases":[
                        {"duracion":d1, "estado":e1},
                        {"duracion":d2, "estado":e2},
                        {"duracion":d3, "estado":e3},
                        {"duracion":d4, "estado":e4}
                        ]
                    },
                "simulacion":{"duracion":3600,"seed":seed}
                }
    return res_json
