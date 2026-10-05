from datetime import datetime
from typing import Any

from geoalchemy2.elements import WKBElement
from pydantic import BaseModel, ConfigDict, field_validator


class CreateEscenario(BaseModel):
    proyecto_id: int
    nombre: str
    zona_geom: Any | None = None
    osm_file_url: str | None = None
    tipo_demanda: str | None = None
    interseccion_ref: str | None = None


class UpdateEscenario(BaseModel):
    nombre: str | None = None
    proyecto_id: int | None = None
    zona_geom: Any | None = None
    osm_file_url: str | None = None
    tipo_demanda: str | None = None
    interseccion_ref: str | None = None


class EscenarioResponse(BaseModel):
    id: int
    proyecto_id: int
    nombre: str
    zona_geom: Any | None = None
    osm_file_url: str | None = None
    tipo_demanda: str | None = None
    interseccion_ref: str | None = None
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("zona_geom", mode="before")
    @classmethod
    def parse_geom(cls, v: Any) -> Any:
        if isinstance(v, WKBElement):
            return str(v)
        return v