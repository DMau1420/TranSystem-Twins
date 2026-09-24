from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.md_user import User
from schemas.sc_resultados import CreateResultado, ResultadoResponse
from services.auth_service import AuthService
from services.resultados_service import ResultadoService

router = APIRouter(prefix="/resultados", tags=["Resultados"])


@router.get("/", response_model=list[ResultadoResponse], summary="Obtener todos los resultados")
def obtener_resultados(
    escenario_id: int | None = Query(
        None, description="Filtrar por ID de escenario opcionalmente"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return ResultadoService.obtener_resultados(
        db=db,
        usuario_id=current_user.id,
        escenario_id=escenario_id,
    )


@router.post(
    "/crear",
    response_model=ResultadoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear o registrar un nuevo resultado de simulación",
)
def crear_resultado(
    resultado_in: CreateResultado,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return ResultadoService.crear_resultado(
        db=db,
        resultado_in=resultado_in,
        usuario_id=current_user.id,
    )


@router.get(
    "/{resultado_id}",
    response_model=ResultadoResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener un resultado por ID",
)
def obtener_resultado_por_id(
    resultado_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return ResultadoService.obtener_resultado_por_id(
        db=db,
        resultado_id=resultado_id,
        usuario_id=current_user.id,
    )


@router.delete(
    "/{resultado_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un resultado",
)
def eliminar_resultado(
    resultado_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return ResultadoService.eliminar_resultado(
        db=db,
        resultado_id=resultado_id,
        usuario_id=current_user.id,
    )
