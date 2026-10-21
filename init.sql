-- ==============================================================================
-- BASE DE DATOS: Sistema de Simulación de Tráfico y Gestión de Escenarios
-- Motor: PostgreSQL 14+ con PostGIS
-- Nota: Los identificadores UUIDv7 son generados y suministrados por el conector/backend
-- ==============================================================================

-- 1. Habilitar extensión PostGIS
CREATE EXTENSION IF NOT EXISTS "postgis";

-- ------------------------------------------------------------------------------
-- Tabla: USUARIOS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id UUID PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    apodo VARCHAR(255),
    correo VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    rol VARCHAR(50) NOT NULL DEFAULT 'Investigador'
);

COMMENT ON TABLE usuarios IS 'Registro de usuarios y roles del sistema';
COMMENT ON COLUMN usuarios.id IS 'Identificador UUIDv7 asignado por la capa de aplicación';

-- ------------------------------------------------------------------------------
-- Tabla: PROYECTOS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS proyectos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    usuario_id UUID NOT NULL,
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    geometria JSONB,
    osm_file_url VARCHAR(1024),
    netxml_base_url VARCHAR(1024),
    geojson_url VARCHAR(1024),
    CONSTRAINT fk_proyectos_usuario
        FOREIGN KEY (usuario_id) 
        REFERENCES usuarios(id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE proyectos IS 'Carpetas de trabajo que agrupan escenarios de estudio';
CREATE INDEX idx_proyectos_usuario_id ON proyectos(usuario_id);

-- ------------------------------------------------------------------------------
-- Tabla: ESCENARIOS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS escenarios (
    id SERIAL PRIMARY KEY,
    proyecto_id INT NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    zona_geom GEOMETRY(GEOMETRY, 4326),
    osm_file_url VARCHAR(1024),
    tipo_demanda VARCHAR(100),
    interseccion_ref VARCHAR(255),
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modificaciones_edges JSONB NOT NULL DEFAULT '[]'::jsonb,
    modificaciones_semaforos JSONB NOT NULL DEFAULT '[]'::jsonb,
    demanda_vehicular INT NOT NULL DEFAULT 100,
    duracion_segundos INT NOT NULL DEFAULT 3600,
    resultado JSONB,
    CONSTRAINT fk_escenarios_proyecto
        FOREIGN KEY (proyecto_id) 
        REFERENCES proyectos(id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE escenarios IS 'Simulaciones específicas y configuraciones dentro de un proyecto';
COMMENT ON COLUMN escenarios.zona_geom IS 'Polígono o geometría espacial de la zona de estudio (PostGIS SRID 4326)';
CREATE INDEX idx_escenarios_proyecto_id ON escenarios(proyecto_id);
CREATE INDEX idx_escenarios_zona_geom ON escenarios USING GIST (zona_geom);
CREATE INDEX idx_escenarios_interseccion_ref ON escenarios(interseccion_ref);

-- ------------------------------------------------------------------------------
-- Tabla: RESULTADOS
-- ------------------------------------------------------------------------------
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

COMMENT ON TABLE resultados IS 'Métricas e indicadores clave generados tras la ejecución de la simulación SUMO';
CREATE INDEX idx_resultados_escenario_id ON resultados(escenario_id);
