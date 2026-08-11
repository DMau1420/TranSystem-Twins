import random
import json
import os
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Numeric
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from pydantic import BaseModel

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


OUTPUT_DIR = Path("saved_points")
OUTPUT_DIR.mkdir(exist_ok=True)

class Geometry(BaseModel):
    type: str = "Point"
    coordinates: List[float] 

class GeoJson(BaseModel):
    type: str = "Feature"
    properties: Dict[str, Any] = {}
    geometry: Geometry

class PointItem(BaseModel):
    id: str
    lat: float
    lng: float
    geoJson: GeoJson
    street: Optional[str] = None
    displayName: Optional[str] = None

class PointsPayload(BaseModel):
    points: List[PointItem]


@app.post("/points")
async def create_points(payload: PointsPayload):
    saved_files = []

    for point in payload.points:
        point_data = point.model_dump()
        file_path = OUTPUT_DIR / f"{point.id}.json"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(point_data, f, ensure_ascii=False, indent=4)
            saved_files.append(str(file_path))
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error al guardar el archivo para el ID {point.id}: {str(e)}",
            )

    return {
        "status": "success",
        "message": f"Se crearon {len(saved_files)} archivo(s) JSON correctamente.",
        "saved_files": saved_files,
    }

@app.get("/points")
async def list_all_points():
    # Obtiene todos los archivos .json en el directorio
    json_files = list(OUTPUT_DIR.glob("*.json"))
    
    records = []
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                records.append(content)
        except Exception:
            continue

    return {
        "total_files": len(records),
        "available_ids": [f.stem for f in json_files],
        "points": records
    }

@app.get("/points/{point_id}")
async def get_point_by_id(point_id: str):
    file_path = OUTPUT_DIR / f"{point_id}.json"

    # Verifica si el archivo existe
    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró ningún punto guardado con el ID: '{point_id}'"
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            point_data = json.load(f)
        return point_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al leer el archivo del ID {point_id}: {str(e)}"
        )
