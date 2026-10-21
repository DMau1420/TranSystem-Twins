from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class CreateResultado(BaseModel):
    escenario_id: int
    tiempo_promedio_espera: float | None = None
    velocidad_promedio: float | None = None
    longitud_max_fila: float | None = None
    vehiculos_atendidos: int | None = None
    reporte_pdf_url: str | None = None

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def map_incoming_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Mapeo de formatos alternativos enviados por simuladores
            if "tiempo_promedio_espera" not in data and "espera_promedio" in data:
                data["tiempo_promedio_espera"] = data["espera_promedio"]
            if "vehiculos_atendidos" not in data and "vehiculos_simulados" in data:
                data["vehiculos_atendidos"] = data["vehiculos_simulados"]
            if "velocidad_promedio" not in data and "tiempo_promedio_recorrido" in data:
                data["velocidad_promedio"] = data.get("velocidad_promedio")
        return data


class ResultadoResponse(BaseModel):
    id: int
    escenario_id: int
    fecha_ejecucion: datetime
    tiempo_promedio_espera: float | None = None
    velocidad_promedio: float | None = None
    longitud_max_fila: float | None = None
    vehiculos_atendidos: int | None = None
    reporte_pdf_url: str | None = None

    model_config = ConfigDict(from_attributes=True)
