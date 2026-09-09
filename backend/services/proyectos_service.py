from uuid import UUID
from sqlalchemy.orm import Session

from core.exceptions import ProyectoNotFoundException
from models.md_proyectos import Proyectos
from schemas.sc_proyectos import CreateProyecto, UpdateProyecto


class ProyectoService:
    @staticmethod
    def crear_proyecto(db: Session, proyecto_in: CreateProyecto, usuario_id: UUID) -> Proyectos:
        nuevo_proyecto = Proyectos(
            nombre=proyecto_in.nombre,
            descripcion=proyecto_in.descripcion,
            usuario_id=usuario_id,
        )
        db.add(nuevo_proyecto)
        db.commit()
        db.refresh(nuevo_proyecto)
        return nuevo_proyecto

    @staticmethod
    def obtener_proyectos(db: Session, usuario_id: UUID) -> list[Proyectos]:
        return db.query(Proyectos).filter(Proyectos.usuario_id == usuario_id).all()

    @staticmethod
    def obtener_proyecto_por_id(db: Session, proyecto_id: int, usuario_id: UUID) -> Proyectos:
        proyecto = (
            db.query(Proyectos)
            .filter(Proyectos.id == proyecto_id, Proyectos.usuario_id == usuario_id)
            .first()
        )
        if not proyecto:
            raise ProyectoNotFoundException()
        return proyecto

    @staticmethod
    def modificar_proyecto(
        db: Session, proyecto_id: int, proyecto_in: UpdateProyecto, usuario_id: UUID
    ) -> Proyectos:
        proyecto = (
            db.query(Proyectos)
            .filter(Proyectos.id == proyecto_id, Proyectos.usuario_id == usuario_id)
            .first()
        )
        if not proyecto:
            raise ProyectoNotFoundException()

        if proyecto_in.nombre is not None:
            proyecto.nombre = proyecto_in.nombre
        if proyecto_in.descripcion is not None:
            proyecto.descripcion = proyecto_in.descripcion

        db.commit()
        db.refresh(proyecto)
        return proyecto

    @staticmethod
    def eliminar_proyecto(db: Session, proyecto_id: int, usuario_id: UUID) -> None:
        proyecto = (
            db.query(Proyectos)
            .filter(Proyectos.id == proyecto_id, Proyectos.usuario_id == usuario_id)
            .first()
        )
        if not proyecto:
            raise ProyectoNotFoundException()

        db.delete(proyecto)
        db.commit()
