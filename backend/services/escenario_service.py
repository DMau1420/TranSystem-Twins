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
    if isinstance(geom, str):
        trimmed = geom.strip()
        if trimmed.startswith("{"):
            try:
                geom = json.loads(trimmed)
            except Exception:
                return func.ST_SetSRID(func.ST_GeomFromText(trimmed), 4326)
        else:
            return func.ST_SetSRID(func.ST_GeomFromText(trimmed), 4326)

    if isinstance(geom, dict):
        target_geom = None
        if "type" in geom and geom["type"] in (
            "Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon", "GeometryCollection"
        ):
            target_geom = geom
        elif "geometry" in geom and isinstance(geom["geometry"], dict):
            target_geom = geom["geometry"]
        elif "geoJson" in geom and isinstance(geom["geoJson"], dict):
            target_geom = geom["geoJson"].get("geometry", geom["geoJson"])
        elif "zones" in geom and len(geom["zones"]) > 0:
            first_zone = geom["zones"][0]
            if "geoJson" in first_zone:
                target_geom = first_zone["geoJson"]
            elif "coordinates" in first_zone:
                coords = [[c["lng"], c["lat"]] if isinstance(c, dict) else c for c in first_zone["coordinates"]]
                if coords and coords[0] != coords[-1]:
                    coords.append(coords[0])
                target_geom = {"type": "Polygon", "coordinates": [coords]}
        elif "points" in geom and len(geom["points"]) > 0:
            coords = [[p["lng"], p["lat"]] for p in geom["points"] if "lng" in p and "lat" in p]
            if len(coords) >= 3:
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                target_geom = {"type": "Polygon", "coordinates": [coords]}
            elif len(coords) == 1:
                target_geom = {"type": "Point", "coordinates": coords[0]}

        if target_geom:
            return func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(target_geom)), 4326)
        return None
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
            demanda_vehicular=escenario_in.demanda_vehicular,
            duracion_segundos=escenario_in.duracion_segundos,
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
        if escenario_in.demanda_vehicular is not None:
            escenario.demanda_vehicular = escenario_in.demanda_vehicular
        if escenario_in.duracion_segundos is not None:
            escenario.duracion_segundos = escenario_in.duracion_segundos
        if escenario_in.modificaciones_edges is not None:
            escenario.modificaciones_edges = escenario_in.modificaciones_edges
        if escenario_in.modificaciones_semaforos is not None:
            escenario.modificaciones_semaforos = escenario_in.modificaciones_semaforos

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

    @staticmethod
    def modificar_edge(db: Session, escenario_id: int, edge_id: str, data, usuario_id: UUID):
        escenario = (
            db.query(Escenarios)
            .join(Proyectos, Escenarios.proyecto_id == Proyectos.id)
            .filter(Escenarios.id == escenario_id, Proyectos.usuario_id == usuario_id)
            .first()
        )
        if not escenario:
            raise EscenarioNotFoundException()
            
        mods = [m for m in escenario.modificaciones_edges if m["edge_id"] != edge_id]
        mods.append({"edge_id": edge_id, **data.model_dump()})
        escenario.modificaciones_edges = mods
        db.commit()
        db.refresh(escenario)
        return escenario

    @staticmethod
    def modificar_semaforo(db: Session, escenario_id: int, tls_id: str, data, usuario_id: UUID):
        escenario = (
            db.query(Escenarios)
            .join(Proyectos, Escenarios.proyecto_id == Proyectos.id)
            .filter(Escenarios.id == escenario_id, Proyectos.usuario_id == usuario_id)
            .first()
        )
        if not escenario:
            raise EscenarioNotFoundException()
            
        mods = [m for m in escenario.modificaciones_semaforos if m["tls_id"] != tls_id]
        mods.append({"tls_id": tls_id, "fases": [f.model_dump() for f in data.fases]})
        escenario.modificaciones_semaforos = mods
        db.commit()
        db.refresh(escenario)
        return escenario
