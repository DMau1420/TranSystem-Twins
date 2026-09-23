from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.md_user import User
from schemas.sc_proyectos import CreateProyecto, ProyectoResponse, UpdateProyecto
from services.auth_service import AuthService
from services.proyectos_service import ProyectoService

router = APIRouter(prefix="/proyectos", tags=["Proyectos"])

@router.get("/", response_model=list[ProyectoResponse], summary="Obtener todos los proyectos")
def obtener_proyectos(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return ProyectoService.obtener_proyectos(
        db=db,
        usuario_id=current_user.id,
    )

@router.post("/crear", response_model=ProyectoResponse, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo proyecto")
def crear_proyecto(
    proyecto_in: CreateProyecto,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return ProyectoService.crear_proyecto(
        db=db,
        proyecto_in=proyecto_in,
        usuario_id=current_user.id,
    )

@router.put("/modificar/{proyecto_id}", response_model=ProyectoResponse, status_code=status.HTTP_200_OK, summary="Modificar un proyecto")
def modificar_proyecto(
    proyecto_id: int,
    proyecto_in: UpdateProyecto,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return ProyectoService.modificar_proyecto(
        db=db,
        proyecto_id=proyecto_id,
        proyecto_in=proyecto_in,
        usuario_id=current_user.id,
    )

@router.get("/{proyecto_id}", response_model=ProyectoResponse, status_code=status.HTTP_200_OK, summary="Obtener un proyecto por ID")
def obtener_proyecto_por_id(
    proyecto_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return ProyectoService.obtener_proyecto_por_id(
        db=db,
        proyecto_id=proyecto_id,
        usuario_id=current_user.id,
    )

@router.delete("/{proyecto_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un proyecto")
def eliminar_proyecto(
    proyecto_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return ProyectoService.eliminar_proyecto(
        db=db,
        proyecto_id=proyecto_id,
        usuario_id=current_user.id,
    )