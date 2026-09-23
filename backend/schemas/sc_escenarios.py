from pydantic import BaseModel


class zona_geom(BaseModel):
    type: str
    coordinates: list[list[float]]

class demanda_sintetica(BaseModel):
    vehiculos_por_hora: int
    direccion: str

class escenario(BaseModel):
    escenario_id : int
    zona_geom: zona_geom
    demanda_sintetica: demanda_sintetica