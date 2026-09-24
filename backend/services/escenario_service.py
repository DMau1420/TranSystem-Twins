import json
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from core.exceptions import EscenarioNotFoundException, ProyectoNotFoundException
from models.md_escenarios import Escenarios
from models.md_proyectos import Proyectos
from schemas.sc_escenarios import CreateEscenario, UpdateEscenario


def parse_geometry_input(geom: dict[str, Any] | str | None):
    if geom is None:
        return None
    if isinstance(geom, dict):
        return func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(geom)), 4326)
    if isinstance(geom, str):
        trimmed = geom.strip()
        if trimmed.startswith("{"):
            return func.ST_SetSRID(func.ST_GeomFromGeoJSON(trimmed), 4326)
        return func.ST_SetSRID(func.ST_GeomFromText(trimmed), 4326)
    return geom


class EscenarioService:
    @staticmethod
    def crear_escenario(db: Session, escenario_in: CreateEscenario, usuario_id: UUID) -> Escenarios:
        proyecto = (
            db.query(Proyectos)
            .filter(Proyectos.id == escenario_in.proyecto_id, Proyectos.usuario_id == usuario_id)
            .first()
        )
        if not proyecto:
            raise ProyectoNotFoundException()

        nuevo_escenario = Escenarios(
            proyecto_id=escenario_in.proyecto_id,
            nombre=escenario_in.nombre,
            zona_geom=parse_geometry_input(escenario_in.zona_geom),
            osm_file_url=escenario_in.osm_file_url,
            tipo_demanda=escenario_in.tipo_demanda,
            interseccion_ref=escenario_in.interseccion_ref,
        )
        db.add(nuevo_escenario)
        db.commit()
        db.refresh(nuevo_escenario)
        return nuevo_escenario

    @staticmethod
    def obtener_escenarios(
        db: Session, usuario_id: UUID, proyecto_id: int | None = None
    ) -> list[Escenarios]:
        query = (
            db.query(Escenarios)
            .join(Proyectos, Escenarios.proyecto_id == Proyectos.id)
            .filter(Proyectos.usuario_id == usuario_id)
        )
        if proyecto_id is not None:
            query = query.filter(Escenarios.proyecto_id == proyecto_id)
        return query.all()

    @staticmethod
    def obtener_escenario_por_id(db: Session, escenario_id: int, usuario_id: UUID) -> Escenarios:
        escenario = (
            db.query(Escenarios)
            .join(Proyectos, Escenarios.proyecto_id == Proyectos.id)
            .filter(Escenarios.id == escenario_id, Proyectos.usuario_id == usuario_id)
            .first()
        )
        if not escenario:
            raise EscenarioNotFoundException()
        return escenario

    @staticmethod
    def modificar_escenario(
        db: Session, escenario_id: int, escenario_in: UpdateEscenario, usuario_id: UUID
    ) -> Escenarios:
        escenario = (
            db.query(Escenarios)
            .join(Proyectos, Escenarios.proyecto_id == Proyectos.id)
            .filter(Escenarios.id == escenario_id, Proyectos.usuario_id == usuario_id)
            .first()
        )
        if not escenario:
            raise EscenarioNotFoundException()

        if (
            escenario_in.proyecto_id is not None
            and escenario_in.proyecto_id != escenario.proyecto_id
        ):
            proyecto_dest = (
                db.query(Proyectos)
                .filter(
                    Proyectos.id == escenario_in.proyecto_id,
                    Proyectos.usuario_id == usuario_id,
                )
                .first()
            )
            if not proyecto_dest:
                raise ProyectoNotFoundException()
            escenario.proyecto_id = escenario_in.proyecto_id

        if escenario_in.nombre is not None:
            escenario.nombre = escenario_in.nombre
        if escenario_in.zona_geom is not None:
            escenario.zona_geom = parse_geometry_input(escenario_in.zona_geom)
        if escenario_in.osm_file_url is not None:
            escenario.osm_file_url = escenario_in.osm_file_url
        if escenario_in.tipo_demanda is not None:
            escenario.tipo_demanda = escenario_in.tipo_demanda
        if escenario_in.interseccion_ref is not None:
            escenario.interseccion_ref = escenario_in.interseccion_ref

        db.commit()
        db.refresh(escenario)
        return escenario

    @staticmethod
    def eliminar_escenario(db: Session, escenario_id: int, usuario_id: UUID) -> None:
        escenario = (
            db.query(Escenarios)
            .join(Proyectos, Escenarios.proyecto_id == Proyectos.id)
            .filter(Escenarios.id == escenario_id, Proyectos.usuario_id == usuario_id)
            .first()
        )
        if not escenario:
            raise EscenarioNotFoundException()

        db.delete(escenario)
        db.commit()
