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
    id UUID PRIMARY KEY, -- Generado como UUIDv7 desde la aplicación / conector
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
-- Tabla: CONFIGURACION_INFRAESTRUCTURA
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS configuracion_infraestructura (
    id SERIAL PRIMARY KEY,
    escenario_id INT NOT NULL,
    edge_id VARCHAR(100) NOT NULL,
    carriles INT NOT NULL DEFAULT 1,
    velocidad_max DOUBLE PRECISION,
    tiempos_semaforo JSONB,
    CONSTRAINT fk_config_infra_escenario
        FOREIGN KEY (escenario_id) 
        REFERENCES escenarios(id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE configuracion_infraestructura IS 'Ajustes de infraestructura vial, carriles y semaforización para SUMO';
CREATE INDEX idx_config_infra_escenario_id ON configuracion_infraestructura(escenario_id);

-- ------------------------------------------------------------------------------
-- Tabla: DEMANDA_SINTETICA
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS demanda_sintetica (
    id SERIAL PRIMARY KEY,
    escenario_id INT NOT NULL,
    direccion VARCHAR(100),
    vehiculos_por_hora DOUBLE PRECISION,
    porcentaje_carga DOUBLE PRECISION,
    horario VARCHAR(100),
    CONSTRAINT fk_demanda_sintetica_escenario
        FOREIGN KEY (escenario_id) 
        REFERENCES escenarios(id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE demanda_sintetica IS 'Patrones y volúmenes de demanda sintética asignados a un escenario';
CREATE INDEX idx_demanda_sintetica_escenario_id ON demanda_sintetica(escenario_id);

-- ------------------------------------------------------------------------------
-- Tabla: AFOROS_TIEMPO_REAL
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aforos_tiempo_real (
    id SERIAL PRIMARY KEY,
    interseccion_ref VARCHAR(255) NOT NULL,
    fecha_hora TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    vehiculos_detectados INT NOT NULL DEFAULT 0,
    fuente VARCHAR(100)
);

COMMENT ON TABLE aforos_tiempo_real IS 'Datos de conteo vehicular en tiempo real capturados por sensores/MQTT';
CREATE INDEX idx_aforos_interseccion_ref ON aforos_tiempo_real(interseccion_ref);
CREATE INDEX idx_aforos_fecha_hora ON aforos_tiempo_real(fecha_hora);

-- ------------------------------------------------------------------------------
-- Tabla Intermedia: ESCENARIO_AFOROS (Relación N:M entre Escenarios y Aforos)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS escenario_aforos (
    escenario_id INT NOT NULL,
    aforo_id INT NOT NULL,
    PRIMARY KEY (escenario_id, aforo_id),
    CONSTRAINT fk_ea_escenario
        FOREIGN KEY (escenario_id) 
        REFERENCES escenarios(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_ea_aforo
        FOREIGN KEY (aforo_id) 
        REFERENCES aforos_tiempo_real(id) 
        ON DELETE CASCADE
);

COMMENT ON TABLE escenario_aforos IS 'Asociación muchos a muchos entre escenarios y mediciones de aforo utilizadas';

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