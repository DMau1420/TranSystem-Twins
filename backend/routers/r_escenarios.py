from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.md_user import User
from schemas.sc_escenarios import CreateEscenario, EscenarioResponse, UpdateEscenario
from services.auth_service import AuthService
from services.escenario_service import EscenarioService

router = APIRouter(prefix="/escenarios", tags=["Escenarios"])


@router.get("/", response_model=list[EscenarioResponse], summary="Obtener todos los escenarios")
def obtener_escenarios(
    proyecto_id: int | None = Query(
        None, description="Filtrar por ID de proyecto opcionalmente"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return EscenarioService.obtener_escenarios(
        db=db,
        usuario_id=current_user.id,
        proyecto_id=proyecto_id,
    )


@router.post(
    "/crear",
    response_model=EscenarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo escenario",
)
def crear_escenario(
    escenario_in: CreateEscenario,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return EscenarioService.crear_escenario(
        db=db,
        escenario_in=escenario_in,
        usuario_id=current_user.id,
    )


@router.put(
    "/modificar/{escenario_id}",
    response_model=EscenarioResponse,
    status_code=status.HTTP_200_OK,
    summary="Modificar un escenario",
)
def modificar_escenario(
    escenario_id: int,
    escenario_in: UpdateEscenario,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return EscenarioService.modificar_escenario(
        db=db,
        escenario_id=escenario_id,
        escenario_in=escenario_in,
        usuario_id=current_user.id,
    )


@router.get(
    "/{escenario_id}",
    response_model=EscenarioResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener un escenario por ID",
)
def obtener_escenario_por_id(
    escenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return EscenarioService.obtener_escenario_por_id(
        db=db,
        escenario_id=escenario_id,
        usuario_id=current_user.id,
    )


@router.delete(
    "/{escenario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un escenario",
)
def eliminar_escenario(
    escenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return EscenarioService.eliminar_escenario(
        db=db,
        escenario_id=escenario_id,
        usuario_id=current_user.id,
    )
