# TranSystem Twins — Backend

API REST y WebSocket del sistema **TranSystem Twins**, una plataforma de gemelos digitales para la simulación y análisis del tráfico urbano. Construida con **FastAPI** sobre Python 3.14, se comunica con una base de datos geoespacial PostgreSQL/PostGIS y orquesta simulaciones de tráfico con el motor **SUMO** (*Simulation of Urban MObility*).

---

## Tabla de Contenidos

- [Stack tecnológico](#stack-tecnológico)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Arquitectura por capas](#arquitectura-por-capas)
- [Diagrama de arquitectura](#diagrama-de-arquitectura)
- [Base de datos](#base-de-datos)
- [Endpoints de la API](#endpoints-de-la-api)
- [Autenticación y seguridad](#autenticación-y-seguridad)
- [Variables de entorno](#variables-de-entorno)
- [Instalación y ejecución local](#instalación-y-ejecución-local)
- [Tests](#tests)
- [Integración con el resto del sistema](#integración-con-el-resto-del-sistema)

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Framework web | [FastAPI](https://fastapi.tiangolo.com/) >= 0.141 |
| Runtime | Python 3.14 |
| ORM | SQLAlchemy 2.x |
| Base de datos | PostgreSQL 17 + PostGIS 3.5 |
| Driver BD | psycopg2-binary |
| Geometría espacial | GeoAlchemy2 |
| Autenticación | JWT (PyJWT) + Argon2 (pwdlib) |
| Identificadores | UUIDv7 (uuid6) |
| Comunicación SUMO | WebSockets (websockets) + httpx2 |
| Testing | pytest 9.x |
| Linter | Ruff |
| Gestor de entornos | [uv](https://docs.astral.sh/uv/) |

---

## Estructura del proyecto

```
backend/
├── main.py                  # Punto de entrada: instancia FastAPI, middlewares y routers
├── pyproject.toml           # Dependencias y configuración del proyecto (uv/PEP 517)
│
├── core/                    # Infraestructura transversal
│   ├── config.py            # Variables de entorno (DATABASE_URL, SECRET_KEY, ALGORITHM)
│   ├── database.py          # Motor SQLAlchemy, sesión y Base declarativa
│   ├── security.py          # Hashing Argon2, JWT (crear / decodificar tokens)
│   └── exceptions.py        # Excepciones HTTP personalizadas del dominio
│
├── models/                  # Modelos ORM (mapeo Python <-> tabla PostgreSQL)
│   ├── md_user.py           # Modelo Usuario (UUIDv7, roles)
│   ├── md_proyectos.py      # Modelo Proyecto (geometría JSONB, URLs de archivos)
│   ├── md_escenarios.py     # Modelo Escenario (PostGIS, modificaciones JSONB, demanda)
│   └── md_resultados.py     # Modelo Resultado (métricas de simulación)
│
├── schemas/                 # Esquemas Pydantic (validación de entrada / salida)
│   ├── sc_user.py           # CreateUser, UpdateUser, Token, UserResponse
│   ├── sc_proyectos.py      # CreateProyecto, UpdateProyecto, ProyectoResponse
│   ├── sc_escenarios.py     # CreateEscenario, UpdateEscenario, ModificarEdge, EscenarioResponse
│   ├── sc_resultados.py     # CreateResultado, ResultadoResponse
│   └── sc_points.py         # Schemas para puntos geoespaciales
│
├── routers/                 # Controladores HTTP/WebSocket (thin layer)
│   ├── r_auth.py            # /auth — registro, login, perfil
│   ├── r_proyectos.py       # /proyectos — CRUD de proyectos
│   ├── r_escenarios.py      # /escenarios — CRUD + patch de infraestructura y semáforos
│   ├── r_resultados.py      # /resultados — CRUD de métricas
│   ├── r_simulacion.py      # /ws/simular (WebSocket) + proxies REST hacia SUMO
│   └── r_points.py          # /points — utilidades de puntos geoespaciales
│
├── services/                # Lógica de negocio
│   ├── auth_service.py      # Registro, autenticación, autorización JWT
│   ├── proyectos_service.py # CRUD de proyectos con aislamiento por usuario
│   ├── escenario_service.py # CRUD de escenarios, patch de edges y semáforos
│   ├── resultados_service.py# Almacenamiento y consulta de resultados de simulación
│   ├── sumo_service.py      # Proxy WebSocket <-> SUMO, orquestación de simulaciones
│   ├── points_service.py    # Cálculos geoespaciales auxiliares
│   └── importacion_osm.py   # Descarga de red vial desde Overpass API (OpenStreetMap)
│
├── osm_generados/           # Archivos .osm descargados de OpenStreetMap
├── saved_points/            # Puntos persistidos localmente
└── test/
    ├── api_test.py          # Suite de integración E2E (30 tests)
    └── sumo_test.py         # Test de simulación WebSocket
```

---

## Arquitectura por capas

El backend sigue una **arquitectura de tres capas** estricta que garantiza separación de responsabilidades:

```
HTTP Request
     │
     ▼
┌─────────────┐
│   Routers   │  <- Validación de entrada (Pydantic), routing, inyección de dependencias
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Services   │  <- Lógica de negocio, reglas de dominio, queries ORM
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Models    │  <- Mapeo ORM -> PostgreSQL/PostGIS
└─────────────┘
```

### Capa de Entrada — Routers

Los routers son **delgados**: solo orquestan el flujo entre la petición HTTP, la inyección de dependencias y el servicio correspondiente. No contienen lógica de negocio.

Cada router inyecta automáticamente:
- **`db: Session`** — sesión de base de datos vía `Depends(get_db)`
- **`current_user: User`** — usuario autenticado vía `Depends(AuthService.obtener_usuario_actual)`

### Capa de Lógica — Services

Cada servicio es una clase con métodos estáticos (`@staticmethod`) que encapsula las reglas de negocio:

| Servicio | Responsabilidad |
|---|---|
| `AuthService` | Registro, login (Argon2 + JWT), autorización, CRUD de usuarios |
| `ProyectoService` | Aislamiento de proyectos por `usuario_id`, operaciones CRUD |
| `EscenarioService` | CRUD de escenarios, patch incremental de edges/semáforos en JSONB |
| `ResultadosService` | Persistencia y consulta de métricas de simulación |
| `SumoService` | Proxy bidireccional WebSocket hacia el microservicio SUMO |
| `importacion_osm` | Consultas a Overpass API para descargar redes viales OSM |

### Capa de Datos — Models

Los modelos SQLAlchemy definen el esquema. Las columnas con tipos geoespaciales usan **GeoAlchemy2** (`Geometry`) y las columnas JSON usan el tipo `JSONB` nativo de PostgreSQL para máximo rendimiento en consultas.

> **Nota importante:** El esquema de producción se inicializa con [`init.sql`](../init.sql) en el arranque del contenedor Docker. Los modelos se sincronizan con `Base.metadata.create_all()` al iniciar la app, pero los cambios posteriores al esquema deben aplicarse manualmente con `ALTER TABLE` o con Alembic.

### Capa de Validación — Schemas

Schemas Pydantic separados para operaciones de escritura (`Create*`, `Update*`) y lectura (`*Response`). El schema `EscenarioResponse` incluye un validador personalizado (`@field_validator`) para serializar geometrías `WKBElement` de PostGIS a string.

### Capa Transversal — Core

| Módulo | Función |
|---|---|
| `config.py` | Lee variables de entorno con valores por defecto |
| `database.py` | Crea el engine SQLAlchemy, define `session_local` y el generador `get_db()` |
| `security.py` | Hash Argon2 (recomendado por pwdlib), JWT HS256 con expiración de 60 min, esquema OAuth2 para Swagger |
| `exceptions.py` | Excepciones HTTP con códigos y mensajes estándar del dominio |

---

## Diagrama de arquitectura

```mermaid
graph TB
    subgraph Cliente["Cliente (Frontend / Herramienta)"]
        FE["Frontend\n(React/Vite — :80)"]
        WS_CLIENT["WebSocket Client"]
    end

    subgraph Backend["Backend FastAPI (:8000)"]
        direction TB
        MAIN["main.py\nCORS · Routers · create_all"]

        subgraph Routers
            R_AUTH["/auth"]
            R_PROJ["/proyectos"]
            R_ESC["/escenarios"]
            R_RES["/resultados"]
            R_SIM["/ws/simular\n/red · /infraestructura\n/semaforo · /resultado"]
            R_PTS["/points"]
        end

        subgraph Services
            S_AUTH["AuthService\nJWT · Argon2"]
            S_PROJ["ProyectoService"]
            S_ESC["EscenarioService\nPatch Edges/Semaforos"]
            S_RES["ResultadosService"]
            S_SUMO["SumoService\nWebSocket Proxy"]
            S_OSM["importacion_osm\nOverpass API"]
        end

        subgraph Core
            DB["database.py\nSQLAlchemy Engine"]
            SEC["security.py"]
            CFG["config.py\nEnv vars"]
            EXC["exceptions.py"]
        end
    end

    subgraph DB_Layer["Base de Datos (PostGIS :5432)"]
        PG[("PostgreSQL 17\n+ PostGIS 3.5")]
        T1["usuarios"]
        T2["proyectos\n(JSONB geometria)"]
        T3["escenarios\n(PostGIS · JSONB mods)"]
        T4["resultados"]
    end

    subgraph SUMO_MS["Microservicio SUMO (:8000 interno)"]
        SUMO_SRV["server.py\nWebSocket Server"]
        SUMO_SIM["simulation_engine.py"]
        SUMO_SCN["scenario_builder.py"]
        SUMO_ANA["result_analyzer.py"]
        SUMO_DATA["data_generators.py"]
    end

    subgraph Externos["Servicios Externos"]
        OSM["Overpass API\n(OpenStreetMap)"]
    end

    FE -- "HTTP REST" --> MAIN
    WS_CLIENT -- "ws://" --> R_SIM

    MAIN --> Routers
    R_AUTH --> S_AUTH
    R_PROJ --> S_PROJ
    R_ESC --> S_ESC
    R_RES --> S_RES
    R_SIM --> S_SUMO
    R_PTS --> S_OSM

    S_AUTH --> DB
    S_PROJ --> DB
    S_ESC --> DB
    S_RES --> DB

    DB --> PG
    PG --- T1 & T2 & T3 & T4

    S_SUMO -- "WebSocket\nws://sumo:8000" --> SUMO_SRV
    SUMO_SRV --> SUMO_SIM & SUMO_SCN & SUMO_ANA & SUMO_DATA

    S_OSM -- "HTTP POST\nOverpass QL" --> OSM
```

---

## Base de datos

### Esquema relacional

```mermaid
erDiagram
    usuarios {
        UUID    id          PK
        VARCHAR nombre
        VARCHAR apodo
        VARCHAR correo      UK
        VARCHAR password
        VARCHAR rol
    }

    proyectos {
        INT     id          PK
        VARCHAR nombre
        TEXT    descripcion
        UUID    usuario_id  FK
        TSTZ    fecha_creacion
        JSONB   geometria
        VARCHAR osm_file_url
        VARCHAR netxml_base_url
        VARCHAR geojson_url
    }

    escenarios {
        INT     id              PK
        INT     proyecto_id     FK
        VARCHAR nombre
        GEOM    zona_geom
        VARCHAR osm_file_url
        VARCHAR tipo_demanda
        VARCHAR interseccion_ref
        TSTZ    fecha_creacion
        JSONB   modificaciones_edges
        JSONB   modificaciones_semaforos
        INT     demanda_vehicular
        INT     duracion_segundos
        JSONB   resultado
    }

    resultados {
        INT     id              PK
        INT     escenario_id    FK
        TSTZ    fecha_ejecucion
        FLOAT   tiempo_promedio_espera
        FLOAT   velocidad_promedio
        FLOAT   longitud_max_fila
        INT     vehiculos_atendidos
        VARCHAR reporte_pdf_url
    }

    usuarios ||--o{ proyectos      : "posee"
    proyectos ||--o{ escenarios    : "contiene"
    escenarios ||--o{ resultados   : "genera"
```

### Tablas principales

#### `usuarios`
Almacena credenciales y metadatos de los usuarios del sistema. La contraseña se guarda como hash **Argon2** y el `id` es un **UUIDv7** generado en la capa de aplicación (incluye timestamp para ordenación cronológica eficiente).

#### `proyectos`
Unidad organizativa de alto nivel. Agrupa escenarios de simulación relacionados con una misma zona urbana. El campo `geometria` (JSONB) almacena el GeoJSON del área de estudio y los campos `*_url` apuntan a archivos generados (`.osm`, `.net.xml`, `.geojson`) almacenados en el microservicio SUMO o en almacenamiento externo.

#### `escenarios`
El corazón del sistema. Representa una configuración específica de simulación. Destacan:
- **`zona_geom`**: geometría espacial PostGIS (SRID 4326) indexada con GIST para consultas espaciales.
- **`modificaciones_edges`**: array JSONB con los cambios de infraestructura aplicados (carriles, velocidad máxima por arista).
- **`modificaciones_semaforos`**: array JSONB con las fases y duraciones modificadas por semáforo.
- **`demanda_vehicular`** y **`duracion_segundos`**: parámetros de configuración de la simulación SUMO.

#### `resultados`
Métricas de rendimiento generadas por SUMO después de cada ejecución de simulación: tiempo de espera promedio, velocidad promedio, longitud máxima de cola y vehículos atendidos.

---

## Endpoints de la API

La documentación interactiva (Swagger UI) está disponible en **`http://localhost:8000/docs`** al ejecutar el servidor.

### Autenticación — `/auth`

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `POST` | `/auth/register` | Registrar nuevo usuario | No |
| `POST` | `/auth/login` | Iniciar sesión — devuelve JWT | No |
| `PUT / PATCH` | `/auth/me` | Actualizar datos del usuario autenticado | Si |
| `DELETE` | `/auth/me` | Eliminar cuenta del usuario autenticado | Si |

> El endpoint `/auth/login` acepta tanto `application/json` (`correo` + `password`) como `application/x-www-form-urlencoded` (`username` + `password`) para compatibilidad con OAuth2.

### Proyectos — `/proyectos`

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `GET` | `/proyectos/` | Listar todos los proyectos del usuario | Si |
| `POST` | `/proyectos/crear` | Crear un nuevo proyecto | Si |
| `GET` | `/proyectos/{id}` | Obtener proyecto por ID | Si |
| `PUT` | `/proyectos/modificar/{id}` | Actualizar proyecto | Si |
| `DELETE` | `/proyectos/{id}` | Eliminar proyecto (cascade a escenarios) | Si |

> **Aislamiento por usuario:** todos los endpoints filtran automáticamente por `usuario_id` del JWT, por lo que un usuario nunca puede acceder a proyectos ajenos.

### Escenarios — `/escenarios`

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `GET` | `/escenarios/` | Listar escenarios (filtrable por `?proyecto_id=`) | Si |
| `POST` | `/escenarios/crear` | Crear nuevo escenario | Si |
| `GET` | `/escenarios/{id}` | Obtener escenario por ID | Si |
| `PUT` | `/escenarios/modificar/{id}` | Actualizar escenario | Si |
| `DELETE` | `/escenarios/{id}` | Eliminar escenario | Si |
| `PATCH` | `/escenarios/{id}/infraestructura/{edge_id}` | Modificar carriles/velocidad de una arista | Si |
| `PATCH` | `/escenarios/{id}/semaforo/{tls_id}` | Modificar fases de un semáforo | Si |

Los endpoints `PATCH` de infraestructura y semáforos actualizan de forma **incremental** el array JSONB correspondiente dentro del escenario, permitiendo un historial de modificaciones sin sobrescribir el estado completo.

### Resultados — `/resultados`

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `GET` | `/resultados/` | Listar resultados (filtrable por `?escenario_id=`) | Si |
| `POST` | `/resultados/crear` | Registrar nuevo resultado de simulación | Si |
| `GET` | `/resultados/{id}` | Obtener resultado por ID | Si |
| `DELETE` | `/resultados/{id}` | Eliminar resultado | Si |

### Simulación — WebSocket y REST

| Método | Ruta | Descripción |
|---|---|---|
| `WS` | `/ws/simular` | Canal WebSocket para orquestar simulaciones en tiempo real |
| `GET` | `/red` | Proxy: obtener red vial desde SUMO |
| `PATCH` | `/infraestructura/{edge_id}` | Proxy: modificar arista en SUMO |
| `PATCH` | `/semaforo/{tls_id}` | Proxy: modificar semáforo en SUMO |
| `GET` | `/resultado` | Proxy: obtener último resultado de SUMO |
| `POST` | `/simular` | Proxy: lanzar simulación en SUMO |
| `POST` | `/resultado-sumo` | Endpoint interno: recibir datos post-simulación desde SUMO |

**Flujo del WebSocket `/ws/simular`:**
1. El cliente envía el payload del escenario (JSON) por el socket.
2. El backend responde `{"status": "iniciando", "progress": 0}`.
3. Se abre un nuevo WebSocket hacia el microservicio SUMO (`ws://sumo:8000`).
4. SUMO ejecuta la simulación y devuelve los resultados.
5. El backend responde `{"status": "completado", "progress": 100, "resultado": {...}}`.

---

## Autenticación y seguridad

El sistema utiliza **JWT Bearer tokens** con el esquema estándar OAuth2:

```
POST /auth/login  ->  { "access_token": "<jwt>", "token_type": "bearer" }

Requests protegidos:
Authorization: Bearer <jwt>
```

**Proceso de verificación en cada request:**
1. `oauth2_scheme` extrae el token del header `Authorization`.
2. `decode_access_token()` decodifica y verifica la firma y expiración.
3. Se extrae el `uuid` del payload para buscar al usuario en la BD.
4. El objeto `User` se inyecta como dependencia en el router.

**Parámetros de seguridad:**
- Algoritmo: **HS256**
- Expiración del token: **60 minutos**
- Hash de contraseñas: **Argon2** (recomendado por OWASP para nuevos proyectos)

---

## Variables de entorno

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión SQLAlchemy a PostgreSQL | `postgresql://gis:password@localhost:5432/gis` |
| `SECRET_KEY` | Clave secreta para firma de JWT | `Bon Voyage` |
| `ALGORITHM` | Algoritmo de firma JWT | `HS256` |

> **Produccion:** Cambia `SECRET_KEY` a un valor aleatorio de al menos 32 bytes. La clave de 10 bytes por defecto genera advertencias `InsecureKeyLengthWarning` de PyJWT.

---

## Instalación y ejecución local

### Con Docker (recomendado)

```bash
# Desde la raíz del monorepo
docker-compose up --build
```

El backend estará disponible en `http://localhost:8000`.

### Sin Docker (desarrollo)

**Prerrequisitos:** Python 3.14, [`uv`](https://docs.astral.sh/uv/), PostgreSQL con PostGIS activo.

```bash
# 1. Ir al directorio del backend
cd backend/

# 2. Crear entorno virtual e instalar dependencias
uv sync

# 3. Inicializar la base de datos
psql -U gis -d gis -f ../init.sql

# 4. Configurar variables de entorno (opcional, hay valores por defecto)
export DATABASE_URL="postgresql://gis:password@localhost:5432/gis"
export SECRET_KEY="tu-clave-secreta-segura"

# 5. Iniciar el servidor de desarrollo
uv run fastapi dev main.py
# o con uvicorn directamente:
uv run uvicorn main:app --reload --port 8000
```

---

## Tests

El proyecto tiene una suite de **30 tests de integración E2E** que prueban el flujo completo contra la base de datos real.

```bash
# Ejecutar todos los tests
uv run pytest -v test/

# Solo tests de API
uv run pytest -v test/api_test.py

# Solo tests de simulación WebSocket
uv run pytest -v test/sumo_test.py
```

**Cobertura de tests:**
- Autenticación: registro, login, credenciales inválidas, actualización de contraseña, eliminación de cuenta
- Proyectos: CRUD completo + acceso no autorizado
- Escenarios: CRUD completo + casos de error (proyecto inválido, no autorizado)
- Resultados: CRUD completo + filtrado por escenario
- Simulación: WebSocket E2E

---

## Integración con el resto del sistema

TranSystem Twins es un **monorepo** compuesto por cuatro servicios que se comunican entre sí dentro de la red Docker `transystem_net`:

```mermaid
graph LR
    subgraph transystem_net["Red Docker: transystem_net"]
        FE["Frontend\ntransystem_frontend\n:80 / :5173"]
        BE["Backend\ntransystem_backend\n:8000"]
        DB[("PostGIS\npostgis_simulacion\n:5432")]
        SUMO["SUMO Microservicio\ntransystem_sumo\n:8000 interno"]
    end

    OSM["Overpass API\n(OpenStreetMap)"]

    FE -- "REST HTTP\nJWT Bearer" --> BE
    FE -- "WebSocket\nws://localhost:8000/ws/simular" --> BE
    BE -- "SQLAlchemy\npsycopg2" --> DB
    BE -- "WebSocket\nws://sumo:8000" --> SUMO
    BE -- "HTTP POST\nOverpass QL" --> OSM
    SUMO -- "HTTP POST\nhttp://backend:8000/resultado-sumo" --> BE
```

### Frontend -> Backend

El frontend (React/Vite) consume la API REST del backend con autenticación JWT Bearer. También establece una conexión **WebSocket** directa a `/ws/simular` para recibir actualizaciones de progreso de la simulación en tiempo real.

- **Documentación interactiva:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Backend -> PostGIS

El backend es el **único** servicio que se conecta directamente a la base de datos. Usa SQLAlchemy con el driver `psycopg2-binary` sobre la red interna Docker (`postgis:5432`). La extensión **PostGIS** permite almacenar e indexar geometrías espaciales (zonas de simulación) con el tipo `GEOMETRY(GEOMETRY, 4326)` y el índice GIST.

**Inicialización:** El contenedor PostGIS ejecuta [`init.sql`](../init.sql) automáticamente en el primer arranque (montado como volumen en `/docker-entrypoint-initdb.d/`).

### Backend -> Microservicio SUMO

La comunicación con SUMO ocurre **exclusivamente por WebSockets** a través de `SumoService`. El backend actúa como **proxy bidireccional**:

1. Recibe la petición del frontend (WebSocket o REST).
2. Abre una conexión al servidor WebSocket de SUMO (`ws://sumo:8000`).
3. Envía el payload con el escenario serializado.
4. Espera la respuesta con los resultados de la simulación.
5. Retransmite los resultados al cliente original.

El microservicio SUMO también puede enviar resultados de vuelta al backend usando el endpoint HTTP `POST /resultado-sumo` (comunicación inversa).

**Fallback de conectividad:** `SumoService` intenta primero `ws://sumo:8000` (nombre de servicio Docker) y si falla, reintenta con `ws://localhost:8000` (útil para desarrollo local sin Docker).

### Backend -> OpenStreetMap (Overpass API)

El servicio `importacion_osm.py` descarga redes viales reales desde la **Overpass API** de OpenStreetMap. Dado un polígono GeoJSON, calcula el bounding box y construye una query Overpass QL para obtener todas las vías (`highway`) del área en formato XML (`.osm`).

Los archivos descargados se guardan en `osm_generados/` con timestamp y sirven como insumo para que el microservicio SUMO genere la red de simulación (`.net.xml`).

**Servidores Overpass configurados:**
- `https://overpass-api.de/api/interpreter` (principal)
- `https://overpass.kumi.systems/api/interpreter` (respaldo, con lógica de reintentos y backoff)
