from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CreateProyecto(BaseModel):
    nombre: str
    descripcion: str | None = None


class UpdateProyecto(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None


class ProyectoResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str | None = None
    usuario_id: UUID
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)
