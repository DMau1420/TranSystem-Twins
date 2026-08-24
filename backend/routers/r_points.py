from fastapi import APIRouter, status

from schemas.sc_points import PointsPayload
from services.points_service import create_points, get_point_by_id, list_all_points

router = APIRouter(prefix="/points", tags=["Points"])

@router.post("", status_code=status.HTTP_201_CREATED, summary="Crear o guardar puntos")
def save_point(payload: PointsPayload):
    return create_points(payload)

@router.get("", summary="Listar todos los puntos")
def list_points():
    return list_all_points()

@router.get("/{point_id}", summary="Obtener punto por ID")
def get_point(point_id: str):
    return get_point_by_id(point_id)