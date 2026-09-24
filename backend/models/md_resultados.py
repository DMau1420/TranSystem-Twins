from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func

from core.database import Base


class Resultados(Base):
    __tablename__ = "resultados"

    id = Column(Integer, primary_key=True, autoincrement=True)
    escenario_id = Column(
        Integer,
        ForeignKey("escenarios.id", ondelete="CASCADE", name="fk_resultados_escenario"),
        nullable=False,
        index=True,
    )
    fecha_ejecucion = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    tiempo_promedio_espera = Column(Float, nullable=True)
    velocidad_promedio = Column(Float, nullable=True)
    longitud_max_fila = Column(Float, nullable=True)
    vehiculos_atendidos = Column(Integer, nullable=True)
    reporte_pdf_url = Column(String(1024), nullable=True)


"""
CREATE TABLE IF NOT EXISTS resultados (
    id SERIAL PRIMARY KEY,
    escenario_id INT NOT NULL,
    fecha_ejecucion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    tiempo_promedio_espera DOUBLE PRECISION,
    velocidad_promedio DOUBLE PRECISION,
    longitud_max_fila DOUBLE PRECISION,
    vehiculos_atendidos INT,
    reporte_pdf_url VARCHAR(1024),
    CONSTRAINT fk_resultados_escenario
        FOREIGN KEY (escenario_id) 
        REFERENCES escenarios(id) 
        ON DELETE CASCADE
);
"""