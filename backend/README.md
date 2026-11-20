# TranSystem Twins — Backend

API REST y WebSocket del backend de **TranSystem Twins**, construida con **FastAPI** sobre Python 3.14. Gestiona usuarios, proyectos, escenarios geoespaciales, resultados de simulación en PostgreSQL/PostGIS y actúa como proxy autenticado hacia el microservicio de tráfico **SUMO** (*Simulation of Urban MObility*).

---

## Tabla de Contenidos

- [Stack tecnológico](#stack-tecnológico)
- [Estructura del directorio `backend/`](#estructura-del-directorio-backend)
- [Arquitectura y funcionamiento](#arquitectura-y-funcionamiento)
- [Base de datos](#base-de-datos)
- [Endpoints de la API](#endpoints-de-la-api)
- [Protocolo WebSocket (`/ws/simular`)](#protocolo-websocket-wssimular)
- [Autenticación y seguridad](#autenticación-y-seguridad)
- [Componentes MQTT y utilidades](#componentes-mqtt-y-utilidades)
- [Variables de entorno](#variables-de-entorno)
- [Instalación y ejecución](#instalación-y-ejecución)
- [Tests](#tests)

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Framework web / ASGI | [FastAPI](https://fastapi.tiangolo.com/) >= 0.141 (`uvicorn`) |
| Runtime | Python 3.14 (estándar con GIL) |
| ORM | SQLAlchemy >= 2.0.52 |
| Base de datos | PostgreSQL 17 + PostGIS 3.5 |
| Driver BD | `psycopg2-binary` >= 2.9.10 |
| Geometría espacial | `GeoAlchemy2` >= 0.20.0 |
| Autenticación y hash | `PyJWT` >= 2.13.0 + `pwdlib[argon2]` >= 0.3.1 |
| Identificadores | UUIDv7 (`uuid6` >= 2025.0.1) |
| Comunicación WebSocket | `websockets` >= 12.0 |
| Mensajería MQTT | `paho-mqtt` >= 2.1.0 |
| Testing | `pytest` >= 9.1.1 |
| Linter | `ruff` >= 0.16.4 |
| Gestor de dependencias | [uv](https://docs.astral.sh/uv/) |

---

## Estructura del directorio `backend/`

```text
backend/
├── main.py                      # Instancia FastAPI, lifespan (simulador MQTT), CORS, routers
├── simulador_vehiculos.py       # Publicador MQTT ejecutado en background durante el lifespan
├── pyproject.toml               # Dependencias y configuración de pytest (pythonpath=["."])
├── uv.lock                      # Lockfile de dependencias
├── .python-version              # Versión de Python fijada (3.14)
├── Dockerfile                   # Imagen python:3.14-slim + uv sync --no-dev
├── .dockerignore
│
├── core/                        # Infraestructura transversal
│   ├── config.py                # DATABASE_URL, SECRET_KEY, ALGORITHM
│   ├── database.py              # Engine SQLAlchemy, session_local, Base, get_db()
│   ├── security.py              # Hash Argon2, creación/decodificación JWT, oauth2_scheme
│   └── exceptions.py            # Excepciones HTTP del dominio (400, 401, 404)
│
├── models/                      # Modelos ORM (PostgreSQL / PostGIS)
│   ├── md_user.py               # Tabla usuarios (UUIDv7)
│   ├── md_proyectos.py          # Tabla proyectos (JSONB geometria + URLs de red)
│   ├── md_escenarios.py         # Tabla escenarios (Geometry SRID 4326 + JSONB)
│   └── md_resultados.py         # Tabla resultados (métricas por ejecución)
│
├── schemas/                     # Esquemas Pydantic de validación y respuesta
│   ├── sc_user.py               # CreateUser, UpdateUser, LoginUser, UserResponse, Token
│   ├── sc_proyectos.py          # CreateProyecto, UpdateProyecto, ProyectoResponse
│   ├── sc_escenarios.py         # CreateEscenario, UpdateEscenario, ModificarEdge,
│   │                            # FaseSemaforo, ModificarSemaforo, DuplicarEscenario, EscenarioResponse
│   └── sc_resultados.py         # CreateResultado (con mapeo de alias SUMO), ResultadoResponse
│
├── routers/                     # Capa HTTP y WebSocket (delegación a services)
│   ├── r_auth.py                # /auth — registro, login, perfil y eliminación
│   ├── r_proyectos.py           # /proyectos — CRUD de proyectos
│   ├── r_escenarios.py          # /escenarios — CRUD, patch de red/semáforos y duplicación
│   ├── r_resultados.py          # /resultados — registro, consulta y eliminación de métricas
│   └── r_simulacion.py          # /ws/simular + proxies REST hacia SUMO (todos con JWT)
│
├── services/                    # Lógica de negocio y comunicación con servicios
│   ├── auth_service.py          # Validación de credenciales y JWT (HTTP y WebSocket)
│   ├── proyectos_service.py     # CRUD de proyectos filtrado por usuario_id
│   ├── escenario_service.py     # CRUD, parseo GeoJSON/WKT -> PostGIS, patches y duplicación
│   ├── resultados_service.py    # Registro y consulta de resultados con aislamiento por usuario
│   ├── sumo_service.py          # Proxy WS hacia SUMO + persistencia automática de resultados
│   ├── gemelo_service.py        # Script suscriptor MQTT independiente (en memoria)
│   └── importacion_osm.py       # Utilidad auxiliar de consulta a Overpass API
│
├── osm_generados/               # Archivos .osm descargados de prueba
└── test/
    ├── api_test.py              # 40 tests de API, aislamiento, auth, duplicación y WS mockeado
    └── sumo_test.py             # 1 test E2E de WebSocket autenticado hacia SUMO
```

---

## Arquitectura y funcionamiento

El backend sigue una arquitectura en tres capas (**Routers -> Services -> Models**) apoyada por módulos transversales en `core/`:

```mermaid
graph TB
    subgraph Client["Clientes externos (HTTP / WS)"]
        HTTP["Peticiones REST\nAuthorization: Bearer JWT"]
        WSC["WebSocket /ws/simular\n?token=JWT o Header Bearer"]
    end

    subgraph Backend["Backend FastAPI (:8000)"]
        MAIN["main.py\nCORS · Lifespan · Base.metadata.create_all"]

        subgraph Routers
            R_AUTH["r_auth (/auth)"]
            R_PROJ["r_proyectos (/proyectos)"]
            R_ESC["r_escenarios (/escenarios)"]
            R_RES["r_resultados (/resultados)"]
            R_SIM["r_simulacion (/ws/simular, /red,\n/infraestructura, /semaforo, /resultado, /simular)"]
        end

        subgraph Services
            S_AUTH["AuthService\nArgon2 + PyJWT"]
            S_PROJ["ProyectoService"]
            S_ESC["EscenarioService\nGeoJSON/WKT + JSONB"]
            S_RES["ResultadoService"]
            S_SUMO["SumoService\nProxy WS + Guardado BD"]
        end

        BG["simulador_vehiculos.py\n(tarea async en lifespan)"]
    end

    DB[("PostgreSQL 17\n+ PostGIS 3.5")]
    SUMO["Microservicio SUMO\nws://sumo:8000 (fallback localhost:8000)"]
    MQTT["Broker MQTT\nlocalhost:1883"]

    HTTP --> MAIN --> Routers
    WSC --> R_SIM
    R_AUTH --> S_AUTH
    R_PROJ --> S_PROJ
    R_ESC --> S_ESC
    R_RES --> S_RES
    R_SIM --> S_AUTH & S_SUMO

    S_AUTH & S_PROJ & S_ESC & S_RES --> DB
    S_SUMO --> S_RES
    S_SUMO -- "WebSocket JSON\n(incluye token en simular)" --> SUMO
    SUMO -. "HTTP GET /escenarios/{id}\nGET /proyectos/{id} (con JWT)" .-> MAIN
    MAIN --> BG -. "publish" .-> MQTT
```

### Ciclo de vida (`main.py`)
1. Al importar `main.py`, ejecuta `Base.metadata.create_all(bind=engine)` para asegurar la existencia de las tablas en PostgreSQL.
2. Configura `CORSMiddleware` con orígenes, métodos y cabeceras permitidos (`*`).
3. Registra los routers `r_auth`, `r_proyectos`, `r_escenarios`, `r_resultados` y `r_simulacion`.
4. En `lifespan`, lanza en segundo plano `iniciar_simulador()` (`simulador_vehiculos.py`) y lo cancela ordenadamente al apagar el servidor.

---

## Base de datos

Las tablas se definen en `models/` y se inicializan también con [`init.sql`](../init.sql) en Docker. Todas las relaciones tienen `ON DELETE CASCADE` (al eliminar un usuario se eliminan sus proyectos, escenarios y resultados).

```mermaid
erDiagram
    usuarios ||--o{ proyectos : "posee"
    proyectos ||--o{ escenarios : "contiene"
    escenarios ||--o{ resultados : "genera"

    usuarios {
        UUID id PK "UUIDv7"
        VARCHAR nombre "255, NOT NULL"
        VARCHAR apodo "255, NULL"
        VARCHAR correo "255, UNIQUE"
        VARCHAR password "Argon2"
        VARCHAR rol "50, default Investigador"
    }
    proyectos {
        INT id PK
        VARCHAR nombre "255"
        TEXT descripcion
        UUID usuario_id FK
        TIMESTAMPTZ fecha_creacion
        JSONB geometria
        VARCHAR osm_file_url "1024"
        VARCHAR netxml_base_url "1024"
        VARCHAR geojson_url "1024"
    }
    escenarios {
        INT id PK
        INT proyecto_id FK
        VARCHAR nombre "255"
        GEOMETRY zona_geom "SRID 4326"
        VARCHAR osm_file_url "1024"
        VARCHAR tipo_demanda "100"
        VARCHAR interseccion_ref "255"
        TIMESTAMPTZ fecha_creacion
        JSONB modificaciones_edges "default []"
        JSONB modificaciones_semaforos "default []"
        INT demanda_vehicular "default 100"
        INT duracion_segundos "default 3600"
        JSONB resultado
    }
    resultados {
        INT id PK
        INT escenario_id FK
        TIMESTAMPTZ fecha_ejecucion
        DOUBLE tiempo_promedio_espera
        DOUBLE velocidad_promedio
        DOUBLE longitud_max_fila
        INT vehiculos_atendidos
        VARCHAR reporte_pdf_url "1024"
    }
```

### Detalles relevantes de persistencia
- **`EscenarioService.parse_geometry_input`:** Acepta GeoJSON directo (`Point`, `Polygon`, etc.), objetos `Feature` (`geometry` / `geoJson`), formatos con `zones`/`points`, o texto WKT; lo convierte a `ST_GeomFromGeoJSON` / `ST_GeomFromText` con SRID `4326`.
- **`EscenarioResponse.parse_geom`:** Convierte el `WKBElement` de PostGIS a diccionario GeoJSON (vía `shapely` si está disponible, o a `str` como respaldo).
- **Aislamiento por usuario:** `ProyectoService`, `EscenarioService` y `ResultadoService` filtran siempre por `Proyectos.usuario_id == current_user.id`. Si el recurso pertenece a otro usuario o no existe, responden `404`.

---

## Endpoints de la API

Documentación interactiva disponible al levantar el backend:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Health Check (`main.py`)

| Método | Ruta | Auth | Descripción | Respuesta |
|---|---|---|---|---|
| `GET` | `/` | No | Verificación de estado de la API | `200` `{"status": "Ok"}` |

### Autenticación — `/auth` (`routers/r_auth.py`)

| Método | Ruta | Auth | Entrada | Respuesta |
|---|---|---|---|---|
| `POST` | `/auth/register` | No | `CreateUser`: `nombre`, `correo`, `password`, `apodo?`, `rol = "Investigador"` | `201` `UserResponse` |
| `POST` | `/auth/login` | No | JSON (`correo`/`username` + `password`) o form (`x-www-form-urlencoded` / `multipart/form-data`) | `200` `Token` (`access_token`, `token_type`) |
| `GET` | `/auth/me` | JWT | — | `200` `UserResponse` |
| `PUT` / `PATCH` | `/auth/me` | JWT | `UpdateUser`: `nombre?`, `apodo?`, `correo?`, `password?`, `rol?` | `200` `UserResponse` |
| `DELETE` | `/auth/me` | JWT | — | `200` `{"mensaje": "Usuario eliminado correctamente"}` |

### Proyectos — `/proyectos` (`routers/r_proyectos.py`)

Todos los endpoints requieren JWT y operan solo sobre los proyectos del usuario autenticado.

| Método | Ruta | Entrada | Respuesta |
|---|---|---|---|
| `GET` | `/proyectos/` | — | `200` `list[ProyectoResponse]` |
| `POST` | `/proyectos/crear` | `CreateProyecto`: `nombre`, `descripcion?`, `geometria?` (`dict`) | `201` `ProyectoResponse` |
| `GET` | `/proyectos/{proyecto_id}` | — | `200` `ProyectoResponse` |
| `PUT` | `/proyectos/modificar/{proyecto_id}` | `UpdateProyecto`: `nombre?`, `descripcion?`, `geometria?` | `200` `ProyectoResponse` |
| `DELETE` | `/proyectos/{proyecto_id}` | — | `204` Sin cuerpo (elimina escenarios en cascada) |

### Escenarios — `/escenarios` (`routers/r_escenarios.py`)

Todos los endpoints requieren JWT y validan que el proyecto padre pertenezca al usuario autenticado.

| Método | Ruta | Entrada | Respuesta |
|---|---|---|---|
| `GET` | `/escenarios/` | Query opcional `?proyecto_id=<int>` | `200` `list[EscenarioResponse]` |
| `POST` | `/escenarios/crear` | `CreateEscenario`: `proyecto_id`, `nombre`, `zona_geom?`, `osm_file_url?`, `tipo_demanda?`, `interseccion_ref?`, `demanda_vehicular = 100`, `duracion_segundos = 3600` | `201` `EscenarioResponse` |
| `GET` | `/escenarios/{escenario_id}` | — | `200` `EscenarioResponse` |
| `PUT` | `/escenarios/modificar/{escenario_id}` | `UpdateEscenario` (campos opcionales, incluyendo `modificaciones_edges` y `modificaciones_semaforos`) | `200` `EscenarioResponse` |
| `DELETE` | `/escenarios/{escenario_id}` | — | `204` Sin cuerpo (elimina resultados en cascada) |
| `PATCH` | `/escenarios/{escenario_id}/infraestructura/{edge_id}` | `ModificarEdge`: `carriles` (`1..10`), `velocidad_max` (`5..120`) | `200` `EscenarioResponse` |
| `PATCH` | `/escenarios/{escenario_id}/semaforo/{tls_id}` | `ModificarSemaforo`: `fases: [{indice, duracion? (1..300), estado?}]` | `200` `EscenarioResponse` |
| `POST` | `/escenarios/{escenario_id}/duplicar` | `DuplicarEscenario` opcional (`{"nombre": "..."}`; default `<nombre> (copia)`) | `201` `EscenarioResponse` |

**Comportamiento de `PATCH` y `duplicar`:**
- `PATCH .../infraestructura/{edge_id}` y `PATCH .../semaforo/{tls_id}` reemplazan la entrada previa con el mismo `edge_id` o `tls_id` dentro de los arreglos JSONB `modificaciones_edges` / `modificaciones_semaforos`, sin sobrescribir otras ediciones.
- `POST /escenarios/{escenario_id}/duplicar` realiza copia profunda de `modificaciones_edges` y `modificaciones_semaforos`, conserva geometría, demanda y duración, e inicializa `resultado` en `null`.

### Resultados — `/resultados` (`routers/r_resultados.py`)

Todos los endpoints requieren JWT y validan pertenencia del escenario/resultado al usuario.

| Método | Ruta | Entrada | Respuesta |
|---|---|---|---|
| `GET` | `/resultados/` | Query opcional `?escenario_id=<int>` | `200` `list[ResultadoResponse]` |
| `POST` | `/resultados/registrar` | `CreateResultado`: `escenario_id`, `tiempo_promedio_espera?`, `velocidad_promedio?`, `longitud_max_fila?`, `vehiculos_atendidos?`, `reporte_pdf_url?` | `201` `ResultadoResponse` |
| `GET` | `/resultados/{resultado_id}` | — | `200` `ResultadoResponse` |
| `DELETE` | `/resultados/{resultado_id}` | — | `204` Sin cuerpo |

> `CreateResultado` acepta campos extra (`extra="allow"`) y mapea alias provenientes de SUMO: `espera_promedio` -> `tiempo_promedio_espera` y `vehiculos_simulados` -> `vehiculos_atendidos`.

### Simulación (Proxy hacia SUMO) — (`routers/r_simulacion.py`)

Todos los endpoints REST y el WebSocket **requieren JWT**.

| Método | Ruta | Auth | Entrada / Descripción |
|---|---|---|---|
| `WS` | `/ws/simular` | JWT (`?token=` o `Bearer`) | Orquesta simulación en tiempo real contra SUMO y guarda el resultado en BD |
| `GET` | `/red` | JWT | Proxy WebSocket a SUMO (`{"action": "get_red"}`) |
| `PATCH` | `/infraestructura/{edge_id}` | JWT | Proxy a SUMO (`{"action": "patch_infraestructura", "edge_id", "datos"}`) |
| `PATCH` | `/semaforo/{tls_id}` | JWT | Proxy a SUMO (`{"action": "patch_semaforo", "tls_id", "datos"}`) |
| `GET` | `/resultado` | JWT | Proxy a SUMO (`{"action": "get_resultado"}`) |
| `POST` | `/simular` | JWT | Proxy síncrono a SUMO (`{"action": "simular", "payload"}` con `token` inyectado) |

---

## Protocolo WebSocket (`/ws/simular`)

1. **Autenticación al conectar:** `r_simulacion.py` extrae el token desde `?token=<jwt>` o del header `Authorization: Bearer <jwt>` y lo valida mediante `AuthService.obtener_usuario_desde_token`. Si falta o es inválido, cierra el socket con código `4001`.
2. **Inicio de simulación:** El cliente envía un JSON, por ejemplo:
   ```json
   {
     "escenario_id": 7,
     "duracion_segundos": 1800,
     "demanda_vehicular": 200
   }
   ```
   El backend responde `{"status": "iniciando", "progress": 5, "message": "Conectando al microservicio SUMO..."}`.
3. **Reenvío a SUMO:** `SumoService` intenta conectarse a `ws://sumo:8000` (y como respaldo a `ws://localhost:8000`), inyecta `"token"` en el `payload` de la acción `simular` para que SUMO pueda consultar `GET /escenarios/{id}` y `GET /proyectos/{id}` autenticado contra el backend.
4. **Progreso:** Cada mensaje `action: "progress"` de SUMO se retransmite al cliente como:
   ```json
   {
     "status": "simulando",
     "progress": 50,
     "message": "...",
     "detail": "..."
   }
   ```
5. **Finalización y persistencia automática:** Cuando SUMO envía `simular_response` (o `data`), el backend:
   - Envía al cliente `{"status": "completado", "progress": 100, "message": "...", "detail": "Simulación completada", "resultado": {...}}`.
   - Si el payload contenía `escenario_id` y el usuario está autenticado, guarda automáticamente el registro en la tabla `resultados` mediante `ResultadoService.crear_resultado`.
6. **Errores:** Si el JSON es inválido devuelve `{"error": "Invalid JSON format", ...}`; si SUMO falla o no responde, envía `{"status": "error", "detail": "...", "message": "..."}`.

---

## Autenticación y seguridad

- **Hashing de contraseñas:** Argon2 vía `pwdlib` (`PasswordHash.recommended()`).
- **Tokens JWT:** Firmados con `PyJWT` (`ALGORITHM = HS256`, expiración de **60 minutos** en el claim `exp`, payload con `sub`, `uuid`, `nombre`, `apodo`, `correo`).
- **Validación centralizada:**
  - Endpoints HTTP: `Depends(AuthService.obtener_usuario_actual)` usando `OAuth2PasswordBearer(tokenUrl="/auth/login")`.
  - WebSocket `/ws/simular`: `AuthService.obtener_usuario_desde_token(db, token)` reutilizando la misma lógica de verificación.

### Catálogo de excepciones (`core/exceptions.py`)

| HTTP | Excepción | Causa |
|---|---|---|
| `400` | `EmailAlreadyRegisteredException` | Correo ya registrado (al crear o actualizar perfil) |
| `401` | `InvalidCredentialsException` | Correo o contraseña faltantes o incorrectos |
| `401` | `InvalidTokenException` | JWT ausente, malformado o expirado |
| `404` | `UserNotFoundException` | El usuario asociado al token no existe |
| `404` | `ProyectoNotFoundException` | Proyecto inexistente o perteneciente a otro usuario |
| `404` | `EscenarioNotFoundException` | Escenario inexistente o perteneciente a otro usuario |
| `404` | `ResultadoNotFoundException` | Resultado inexistente o perteneciente a otro usuario |

---

## Componentes MQTT y utilidades

- **`simulador_vehiculos.py`:** Se ejecuta en background dentro del `lifespan` de FastAPI. Se conecta al broker `localhost:1883` con reintentos exponenciales (hasta 30 s) y publica mensajes JSON `{"vehiculos_por_minuto": int, "timestamp": iso}` en el tópico `transystem/vehiculos_por_minuto`.
- **`services/gemelo_service.py`:** Script independiente (`python services/gemelo_service.py`) que se suscribe al mismo tópico MQTT y acumula las lecturas en la lista en memoria `historial_vehiculos`.
- **`services/importacion_osm.py`:** Contiene `calcular_bbox(polygon)` y `descargar_red(bbox)` contra `overpass-api.de` y `overpass.kumi.systems` (actualmente no está enlazado a ningún router; la importación de red en operación la realiza el servicio SUMO).

---

## Variables de entorno

Definidas en [`core/config.py`](core/config.py):

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión SQLAlchemy hacia PostgreSQL/PostGIS | `postgresql://gis:password@localhost:5432/gis` |
| `SECRET_KEY` | Clave secreta para firmar/verificar JWT | `Bon Voyage` |
| `ALGORITHM` | Algoritmo de firma JWT | `HS256` |

> En producción se recomienda definir un `SECRET_KEY` aleatorio de al menos 32 bytes para evitar advertencias `InsecureKeyLengthWarning` de PyJWT.

---

## Instalación y ejecución

### Con Docker (desde la raíz del repositorio)

[`Dockerfile`](Dockerfile) usa `python:3.14-slim`, instala `libpq-dev` y `gcc`, sincroniza dependencias con `uv sync --no-dev` y ejecuta el backend en el puerto `8000` (en `docker-compose.yaml` arranca con `uv run uvicorn main:app --host 0.0.0.0 --port 8000` y `DATABASE_URL=postgresql://gis:password@postgis:5432/gis`).

```bash
docker compose up --build backend postgis
```

### En local sin Docker

Requisitos: Python 3.14 **con GIL estándar** (`3.14+gil`, ya que `psycopg2-binary` no tiene wheels precompilados para `python3.14t` free-threaded si no hay `pg_config`), [`uv`](https://docs.astral.sh/uv/) y PostgreSQL/PostGIS corriendo.

```bash
cd backend/

# Crear/sincronizar entorno virtual
uv sync --python 3.14+gil

# Inicializar tablas (si no se usa Docker con init.sql)
psql -U gis -d gis -f ../init.sql

# Ejecutar servidor de desarrollo
uv run uvicorn main:app --reload --port 8000
```

---

## Tests

La suite en `backend/test/` contiene **41 pruebas** configuradas vía `pyproject.toml` (`testpaths = ["test"]`, `pythonpath = ["."]`) y requiere PostgreSQL/PostGIS accesible en `DATABASE_URL`:

- **`test/api_test.py` (40 tests):**
  - Health check (`GET /`)
  - Autenticación: registro, correo duplicado (`400`), login JSON y form `x-www-form-urlencoded`, login inválido (`401`), `GET`/`PUT`/`PATCH`/`DELETE /auth/me`, operaciones sin JWT (`401`)
  - Proyectos: CRUD completo, `404`, `401`
  - Escenarios: CRUD completo, `404` por proyecto inválido, filtrado por `?proyecto_id=`, `PATCH` incremental de infraestructura y semáforos (incluyendo validación `422`), duplicación (`POST /escenarios/{id}/duplicar` con nombre por defecto y personalizado)
  - Resultados: registro en `POST /resultados/registrar` con mapeo de alias SUMO, listado/filtrado, consulta, borrado, `401` y `404`
  - Aislamiento entre usuarios distintos sobre proyectos, escenarios, duplicación y resultados
  - Simulación (`r_simulacion.py`): verificación de `401` en endpoints REST sin JWT, rechazo de `/ws/simular` con código `4001` sin token o token inválido, y flujo completo `POST /simular` + `/ws/simular?token=...` (con mock de `websockets.connect`) validando envío de token a SUMO y persistencia automática en `resultados`
- **`test/sumo_test.py` (1 test):**
  - Prueba E2E de conexión autenticada a `/ws/simular?token=...` (acepta resultado `completado` si el servicio SUMO está levantado o `error` controlado si no está activo).

```bash
cd backend/

# Ejecutar toda la suite
uv run pytest -v test/

# Ejecutar solo pruebas de API o solo WebSocket SUMO
uv run pytest -v test/api_test.py
uv run pytest -v test/sumo_test.py
```
