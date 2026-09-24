from uuid import UUID

from sqlalchemy.orm import Session

from core.exceptions import EscenarioNotFoundException, ResultadoNotFoundException
from models.md_escenarios import Escenarios
from models.md_proyectos import Proyectos
from models.md_resultados import Resultados
from schemas.sc_resultados import CreateResultado


class ResultadoService:
    @staticmethod
    def crear_resultado(db: Session, resultado_in: CreateResultado, usuario_id: UUID) -> Resultados:
        escenario = (
            db.query(Escenarios)
            .join(Proyectos, Escenarios.proyecto_id == Proyectos.id)
            .filter(Escenarios.id == resultado_in.escenario_id, Proyectos.usuario_id == usuario_id)
            .first()
        )
        if not escenario:
            raise EscenarioNotFoundException()

        nuevo_resultado = Resultados(
            escenario_id=resultado_in.escenario_id,
            tiempo_promedio_espera=resultado_in.tiempo_promedio_espera,
            velocidad_promedio=resultado_in.velocidad_promedio,
            longitud_max_fila=resultado_in.longitud_max_fila,
            vehiculos_atendidos=resultado_in.vehiculos_atendidos,
            reporte_pdf_url=resultado_in.reporte_pdf_url,
        )
        db.add(nuevo_resultado)
        db.commit()
        db.refresh(nuevo_resultado)
        return nuevo_resultado

    @staticmethod
    def obtener_resultados(
        db: Session, usuario_id: UUID, escenario_id: int | None = None
    ) -> list[Resultados]:
        query = (
            db.query(Resultados)
            .join(Escenarios, Resultados.escenario_id == Escenarios.id)
            .join(Proyectos, Escenarios.proyecto_id == Proyectos.id)
            .filter(Proyectos.usuario_id == usuario_id)
        )
        if escenario_id is not None:
            query = query.filter(Resultados.escenario_id == escenario_id)
        return query.all()

    @staticmethod
    def obtener_resultado_por_id(db: Session, resultado_id: int, usuario_id: UUID) -> Resultados:
        resultado = (
            db.query(Resultados)
            .join(Escenarios, Resultados.escenario_id == Escenarios.id)
            .join(Proyectos, Escenarios.proyecto_id == Proyectos.id)
            .filter(Resultados.id == resultado_id, Proyectos.usuario_id == usuario_id)
            .first()
        )
        if not resultado:
            raise ResultadoNotFoundException()
        return resultado

    @staticmethod
    def eliminar_resultado(db: Session, resultado_id: int, usuario_id: UUID) -> None:
        resultado = (
            db.query(Resultados)
            .join(Escenarios, Resultados.escenario_id == Escenarios.id)
            .join(Proyectos, Escenarios.proyecto_id == Proyectos.id)
            .filter(Resultados.id == resultado_id, Proyectos.usuario_id == usuario_id)
            .first()
        )
        if not resultado:
            raise ResultadoNotFoundException()

        db.delete(resultado)
        db.commit()
