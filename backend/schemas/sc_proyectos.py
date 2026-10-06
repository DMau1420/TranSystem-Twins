from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CreateProyecto(BaseModel):
    nombre: str
    descripcion: str | None = None
    geometria: dict | None = None


class UpdateProyecto(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    geometria: dict | None = None


class ProyectoResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str | None = None
    usuario_id: UUID
    fecha_creacion: datetime
    geometria: dict | None = None
    osm_file_url: str | None = None
    netxml_base_url: str | None = None
    geojson_url: str | None = None

    model_config = ConfigDict(from_attributes=True)
