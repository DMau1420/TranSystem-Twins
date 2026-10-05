from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from geoalchemy2 import Geometry

from core.database import Base


class Escenarios(Base):
    __tablename__ = "escenarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proyecto_id = Column(
        Integer,
        ForeignKey("proyectos.id", ondelete="CASCADE", name="fk_escenarios_proyecto"),
        nullable=False,
        index=True
    )
    nombre = Column(String(255), nullable=False)
    zona_geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True)
    osm_file_url = Column(String(1024), nullable=True)
    tipo_demanda = Column(String(100), nullable=True)
    interseccion_ref = Column(String(255), nullable=True, index=True)
    fecha_creacion = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


'''
CREATE TABLE IF NOT EXISTS escenarios (
    id SERIAL PRIMARY KEY,
    proyecto_id INT NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    zona_geom GEOMETRY(GEOMETRY, 4326),
    osm_file_url VARCHAR(1024),
    tipo_demanda VARCHAR(100),
    interseccion_ref VARCHAR(255),
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_escenarios_proyecto
        FOREIGN KEY (proyecto_id) 
        REFERENCES proyectos(id) 
        ON DELETE CASCADE
);
'''
