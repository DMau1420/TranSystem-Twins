from datetime import datetime
from typing import Any

from geoalchemy2.elements import WKBElement
from pydantic import BaseModel, ConfigDict, field_validator, Field


class CreateEscenario(BaseModel):
    proyecto_id: int
    nombre: str
    zona_geom: Any | None = None
    osm_file_url: str | None = None
    tipo_demanda: str | None = None
    interseccion_ref: str | None = None
    demanda_vehicular: int = 100
    duracion_segundos: int = 3600


class UpdateEscenario(BaseModel):
    nombre: str | None = None
    proyecto_id: int | None = None
    zona_geom: Any | None = None
    osm_file_url: str | None = None
    tipo_demanda: str | None = None
    interseccion_ref: str | None = None


class ModificarEdge(BaseModel):
    carriles: int = Field(ge=1, le=10)
    velocidad_max: float = Field(ge=5, le=120)


class FaseSemaforo(BaseModel):
    indice: int
    duracion: int | None = Field(default=None, ge=1, le=300)
    estado: str | None = None


class ModificarSemaforo(BaseModel):
    fases: list[FaseSemaforo]


class EscenarioResponse(BaseModel):
    id: int
    proyecto_id: int
    nombre: str
    zona_geom: Any | None = None
    osm_file_url: str | None = None
    tipo_demanda: str | None = None
    interseccion_ref: str | None = None
    demanda_vehicular: int = 100
    duracion_segundos: int = 3600
    modificaciones_edges: list[dict] = []
    modificaciones_semaforos: list[dict] = []
    resultado: dict | None = None
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("zona_geom", mode="before")
    @classmethod
    def parse_geom(cls, v: Any) -> Any:
        if isinstance(v, WKBElement):
            return str(v)
        return v