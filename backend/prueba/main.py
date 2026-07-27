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
