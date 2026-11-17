import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from core.database import session_local
from core.security import decode_access_token
from main import app
from models.md_user import User

client = TestClient(app)

# ====================================
# Test Root
# ====================================
def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "Ok"}


# ====================================
# Tests para Autenticación
# ====================================

TEST_USER = {
    "nombre": "Aemeath",
    "apodo": "fleet snowfluff",
    "correo": "aemeath@collective.com",
    "password": "Voyaging Stars Farewell",
    "rol": "Investigador",
}

NEW_PASSWORD = "NewVoyagingStarsPass123"


@pytest.fixture(scope="module", autouse=True)
def cleanup_user():
    db = session_local()
    existing_user = db.query(User).filter(User.correo == TEST_USER["correo"]).first()
    if existing_user:
        db.delete(existing_user)
        db.commit()
    db.close()
    yield
    db = session_local()
    existing_user = db.query(User).filter(User.correo == TEST_USER["correo"]).first()
    if existing_user:
        db.delete(existing_user)
        db.commit()
    db.close()


def test_register_user():
    response = client.post("/auth/register", json=TEST_USER)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["nombre"] == TEST_USER["nombre"]
    assert data["correo"] == TEST_USER["correo"]
    assert data["apodo"] == TEST_USER["apodo"]
    assert data["rol"] == TEST_USER["rol"]


def test_login_user():
    login_data = {
        "correo": TEST_USER["correo"],
        "password": TEST_USER["password"],
    }
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200

    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data

    payload = decode_access_token(data["access_token"])
    assert "uuid" in payload
    assert payload["uuid"] == payload["sub"]
    assert payload["correo"] == TEST_USER["correo"]


def test_login_invalid_credentials():
    login_data = {
        "correo": TEST_USER["correo"],
        "password": "WrongPassword123!",
    }
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 401


def test_register_duplicate_email():
    response = client.post("/auth/register", json=TEST_USER)
    assert response.status_code == 400


def test_login_form_urlencoded():
    response = client.post(
        "/auth/login",
        data={
            "username": TEST_USER["correo"],
            "password": TEST_USER["password"],
        },
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_update_user_data():
    login_data = {
        "correo": TEST_USER["correo"],
        "password": TEST_USER["password"],
    }
    login_res = client.post("/auth/login", json=login_data)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    update_payload = {
        "nombre": "Aemeath Updated",
        "apodo": "snowfluff prime",
    }
    patch_res = client.patch("/auth/me", json=update_payload, headers=headers)
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["nombre"] == "Aemeath Updated"
    assert updated["apodo"] == "snowfluff prime"


def test_update_password_and_login():
    login_data = {
        "correo": TEST_USER["correo"],
        "password": TEST_USER["password"],
    }
    login_res = client.post("/auth/login", json=login_data)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    patch_res = client.patch(
        "/auth/me",
        json={"password": NEW_PASSWORD},
        headers=headers,
    )
    assert patch_res.status_code == 200

    old_login = client.post(
        "/auth/login",
        json={"correo": TEST_USER["correo"], "password": TEST_USER["password"]},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login",
        json={"correo": TEST_USER["correo"], "password": NEW_PASSWORD},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()


def test_unauthorized_operations():
    unauth_me = client.get("/auth/me")
    assert unauth_me.status_code == 401

    unauth_patch = client.patch("/auth/me", json={"nombre": "Hacker"})
    assert unauth_patch.status_code == 401

    unauth_delete = client.delete("/auth/me")
    assert unauth_delete.status_code == 401


def test_get_current_user_and_put_me():
    headers = get_auth_headers()
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["correo"] == TEST_USER["correo"]

    put_res = client.put(
        "/auth/me",
        json={"apodo": "snowfluff put"},
        headers=headers,
    )
    assert put_res.status_code == 200
    assert put_res.json()["apodo"] == "snowfluff put"


# ====================================
# Tests para Proyectos
# ====================================

PROYECTO_TEST = {
    "nombre": "Simulación Insurgentes Sur",
    "descripcion": "Estudio de aforo vehicular y tiempos semafóricos",
}

created_proyecto_id = None


def get_auth_headers():
    login_res = client.post(
        "/auth/login",
        json={"correo": TEST_USER["correo"], "password": NEW_PASSWORD},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_crear_proyecto():
    global created_proyecto_id
    headers = get_auth_headers()
    response = client.post("/proyectos/crear", json=PROYECTO_TEST, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["nombre"] == PROYECTO_TEST["nombre"]
    assert data["descripcion"] == PROYECTO_TEST["descripcion"]
    assert "usuario_id" in data
    assert "fecha_creacion" in data
    created_proyecto_id = data["id"]


def test_obtener_todos_los_proyectos():
    headers = get_auth_headers()
    response = client.get("/proyectos/", headers=headers)
    assert response.status_code == 200
    proyectos = response.json()
    assert isinstance(proyectos, list)
    assert len(proyectos) >= 1
    ids = [p["id"] for p in proyectos]
    assert created_proyecto_id in ids


def test_obtener_proyecto_por_id():
    headers = get_auth_headers()
    response = client.get(f"/proyectos/{created_proyecto_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_proyecto_id
    assert data["nombre"] == PROYECTO_TEST["nombre"]
    assert data["descripcion"] == PROYECTO_TEST["descripcion"]


def test_modificar_proyecto():
    headers = get_auth_headers()
    modificaciones = {
        "nombre": "Simulación Insurgentes Sur (Fase 2)",
        "descripcion": "Estudio ampliado con rediseño geométrico",
    }
    response = client.put(
        f"/proyectos/modificar/{created_proyecto_id}",
        json=modificaciones,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_proyecto_id
    assert data["nombre"] == modificaciones["nombre"]
    assert data["descripcion"] == modificaciones["descripcion"]


def test_obtener_proyecto_no_existente():
    headers = get_auth_headers()
    response = client.get("/proyectos/999999", headers=headers)
    assert response.status_code == 404


def test_operaciones_proyectos_no_autorizadas():
    res_list = client.get("/proyectos/")
    assert res_list.status_code == 401

    res_create = client.post("/proyectos/crear", json=PROYECTO_TEST)
    assert res_create.status_code == 401

    res_get = client.get(f"/proyectos/{created_proyecto_id}")
    assert res_get.status_code == 401

    res_put = client.put(
        f"/proyectos/modificar/{created_proyecto_id}",
        json={"nombre": "Hack"},
    )
    assert res_put.status_code == 401

    res_del = client.delete(f"/proyectos/{created_proyecto_id}")
    assert res_del.status_code == 401


def test_eliminar_proyecto():
    headers = get_auth_headers()
    temp_project = {
        "nombre": "Proyecto Temporal Para Borrar",
        "descripcion": "Se eliminará inmediatamente",
    }
    create_res = client.post("/proyectos/crear", json=temp_project, headers=headers)
    assert create_res.status_code == 201
    temp_id = create_res.json()["id"]

    del_res = client.delete(f"/proyectos/{temp_id}", headers=headers)
    assert del_res.status_code == 204

    get_res = client.get(f"/proyectos/{temp_id}", headers=headers)
    assert get_res.status_code == 404


# ====================================
# Tests para Escenarios
# ====================================

ESCENARIO_TEST = {
    "nombre": "Escenario Horario Pico Matutino",
    "zona_geom": {
        "type": "Polygon",
        "coordinates": [
            [
                [-99.1332, 19.4326],
                [-99.1400, 19.4400],
                [-99.1300, 19.4450],
                [-99.1332, 19.4326],
            ]
        ],
    },
    "osm_file_url": "https://example.com/osm/insurgentes.osm",
    "tipo_demanda": "Vehicular Intensa",
    "interseccion_ref": "Insurgentes y Reforma",
}

created_escenario_id = None


def test_crear_escenario():
    global created_escenario_id
    headers = get_auth_headers()
    payload = {
        **ESCENARIO_TEST,
        "proyecto_id": created_proyecto_id,
    }
    response = client.post("/escenarios/crear", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["proyecto_id"] == created_proyecto_id
    assert data["nombre"] == ESCENARIO_TEST["nombre"]
    assert data["osm_file_url"] == ESCENARIO_TEST["osm_file_url"]
    assert data["tipo_demanda"] == ESCENARIO_TEST["tipo_demanda"]
    assert data["interseccion_ref"] == ESCENARIO_TEST["interseccion_ref"]
    assert data["zona_geom"] is not None
    assert "fecha_creacion" in data
    created_escenario_id = data["id"]


def test_crear_escenario_proyecto_invalido():
    headers = get_auth_headers()
    payload = {
        **ESCENARIO_TEST,
        "proyecto_id": 999999,
    }
    response = client.post("/escenarios/crear", json=payload, headers=headers)
    assert response.status_code == 404


def test_obtener_todos_los_escenarios():
    headers = get_auth_headers()
    response = client.get("/escenarios/", headers=headers)
    assert response.status_code == 200
    escenarios = response.json()
    assert isinstance(escenarios, list)
    assert len(escenarios) >= 1
    ids = [e["id"] for e in escenarios]
    assert created_escenario_id in ids


def test_obtener_escenarios_filtrados_por_proyecto():
    headers = get_auth_headers()
    response = client.get(
        f"/escenarios/?proyecto_id={created_proyecto_id}", headers=headers
    )
    assert response.status_code == 200
    escenarios = response.json()
    assert isinstance(escenarios, list)
    ids = [e["id"] for e in escenarios]
    assert created_escenario_id in ids

    # Filtrar por un proyecto inexistente
    res_empty = client.get("/escenarios/?proyecto_id=999999", headers=headers)
    assert res_empty.status_code == 200
    assert res_empty.json() == []


def test_obtener_escenario_por_id():
    headers = get_auth_headers()
    response = client.get(f"/escenarios/{created_escenario_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_escenario_id
    assert data["nombre"] == ESCENARIO_TEST["nombre"]
    assert data["proyecto_id"] == created_proyecto_id
    assert data["tipo_demanda"] == ESCENARIO_TEST["tipo_demanda"]


def test_modificar_escenario():
    headers = get_auth_headers()
    modificaciones = {
        "nombre": "Escenario Horario Pico Vespertino",
        "tipo_demanda": "Demanda Calibrada",
        "interseccion_ref": "Insurgentes y Hamburgo",
    }
    response = client.put(
        f"/escenarios/modificar/{created_escenario_id}",
        json=modificaciones,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_escenario_id
    assert data["nombre"] == modificaciones["nombre"]
    assert data["tipo_demanda"] == modificaciones["tipo_demanda"]
    assert data["interseccion_ref"] == modificaciones["interseccion_ref"]


def test_obtener_escenario_no_existente():
    headers = get_auth_headers()
    response = client.get("/escenarios/999999", headers=headers)
    assert response.status_code == 404


def test_operaciones_escenarios_no_autorizadas():
    res_list = client.get("/escenarios/")
    assert res_list.status_code == 401

    res_create = client.post(
        "/escenarios/crear",
        json={**ESCENARIO_TEST, "proyecto_id": created_proyecto_id},
    )
    assert res_create.status_code == 401

    res_get = client.get(f"/escenarios/{created_escenario_id}")
    assert res_get.status_code == 401

    res_put = client.put(
        f"/escenarios/modificar/{created_escenario_id}",
        json={"nombre": "Hack"},
    )
    assert res_put.status_code == 401

    res_del = client.delete(f"/escenarios/{created_escenario_id}")
    assert res_del.status_code == 401


def test_eliminar_escenario():
    headers = get_auth_headers()
    temp_escenario = {
        "proyecto_id": created_proyecto_id,
        "nombre": "Escenario Temporal Para Borrar",
    }
    create_res = client.post("/escenarios/crear", json=temp_escenario, headers=headers)
    assert create_res.status_code == 201
    temp_id = create_res.json()["id"]

    del_res = client.delete(f"/escenarios/{temp_id}", headers=headers)
    assert del_res.status_code == 204

    get_res = client.get(f"/escenarios/{temp_id}", headers=headers)
    assert get_res.status_code == 404


def test_patch_infraestructura_edge():
    headers = get_auth_headers()
    res = client.patch(
        f"/escenarios/{created_escenario_id}/infraestructura/edge_101",
        json={"carriles": 3, "velocidad_max": 60.0},
        headers=headers,
    )
    assert res.status_code == 200
    mods = res.json()["modificaciones_edges"]
    assert mods == [{"edge_id": "edge_101", "carriles": 3, "velocidad_max": 60.0}]

    # Reemplazar el mismo edge_id no duplica la entrada
    res_replace = client.patch(
        f"/escenarios/{created_escenario_id}/infraestructura/edge_101",
        json={"carriles": 4, "velocidad_max": 80.0},
        headers=headers,
    )
    assert res_replace.status_code == 200
    assert res_replace.json()["modificaciones_edges"] == [
        {"edge_id": "edge_101", "carriles": 4, "velocidad_max": 80.0}
    ]

    # Validación de rangos (carriles fuera de [1..10])
    res_invalid = client.patch(
        f"/escenarios/{created_escenario_id}/infraestructura/edge_101",
        json={"carriles": 15, "velocidad_max": 60.0},
        headers=headers,
    )
    assert res_invalid.status_code == 422

    res_404 = client.patch(
        "/escenarios/999999/infraestructura/edge_101",
        json={"carriles": 2, "velocidad_max": 50.0},
        headers=headers,
    )
    assert res_404.status_code == 404

    res_401 = client.patch(
        f"/escenarios/{created_escenario_id}/infraestructura/edge_101",
        json={"carriles": 2, "velocidad_max": 50.0},
    )
    assert res_401.status_code == 401


def test_patch_semaforo_tls():
    headers = get_auth_headers()
    payload = {"fases": [{"indice": 0, "duracion": 35, "estado": "GGrr"}]}
    res = client.patch(
        f"/escenarios/{created_escenario_id}/semaforo/tls_202",
        json=payload,
        headers=headers,
    )
    assert res.status_code == 200
    mods = res.json()["modificaciones_semaforos"]
    assert mods == [{"tls_id": "tls_202", "fases": [{"indice": 0, "duracion": 35, "estado": "GGrr"}]}]

    # Validación de rangos (duracion fuera de [1..300])
    res_invalid = client.patch(
        f"/escenarios/{created_escenario_id}/semaforo/tls_202",
        json={"fases": [{"indice": 0, "duracion": 500, "estado": "GGrr"}]},
        headers=headers,
    )
    assert res_invalid.status_code == 422

    res_404 = client.patch(
        "/escenarios/999999/semaforo/tls_202",
        json=payload,
        headers=headers,
    )
    assert res_404.status_code == 404

    res_401 = client.patch(
        f"/escenarios/{created_escenario_id}/semaforo/tls_202",
        json=payload,
    )
    assert res_401.status_code == 401


def test_duplicar_escenario():
    headers = get_auth_headers()
    orig_res = client.get(f"/escenarios/{created_escenario_id}", headers=headers)
    assert orig_res.status_code == 200
    orig = orig_res.json()

    # Duplicado con nombre por defecto
    dup_default = client.post(
        f"/escenarios/{created_escenario_id}/duplicar",
        headers=headers,
    )
    assert dup_default.status_code == 201
    copia = dup_default.json()
    assert copia["id"] != orig["id"]
    assert copia["proyecto_id"] == orig["proyecto_id"]
    assert copia["nombre"] == f"{orig['nombre']} (copia)"
    assert copia["modificaciones_edges"] == orig["modificaciones_edges"]
    assert copia["modificaciones_semaforos"] == orig["modificaciones_semaforos"]
    assert copia["demanda_vehicular"] == orig["demanda_vehicular"]
    assert copia["duracion_segundos"] == orig["duracion_segundos"]
    assert copia["resultado"] is None

    # Duplicado con nombre personalizado
    dup_custom = client.post(
        f"/escenarios/{created_escenario_id}/duplicar",
        json={"nombre": "Alternativa Semáforo Optimizado"},
        headers=headers,
    )
    assert dup_custom.status_code == 201
    assert dup_custom.json()["nombre"] == "Alternativa Semáforo Optimizado"

    # Error 404 y 401
    assert (
        client.post("/escenarios/999999/duplicar", headers=headers).status_code == 404
    )
    assert client.post(f"/escenarios/{created_escenario_id}/duplicar").status_code == 401

    # Limpieza de copias
    client.delete(f"/escenarios/{copia['id']}", headers=headers)
    client.delete(f"/escenarios/{dup_custom.json()['id']}", headers=headers)


# ====================================
# Tests para Resultados
# ====================================

created_resultado_id = None


def test_crear_resultado_formato_simulador():
    global created_resultado_id
    headers = get_auth_headers()
    payload = {
        "escenario_id": created_escenario_id,
        "vehiculos_simulados": 95,
        "tiempo_promedio_recorrido": 174.3684210526316,
        "espera_promedio": 18.694736842105264,
    }
    response = client.post("/resultados/registrar", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["escenario_id"] == created_escenario_id
    assert data["vehiculos_atendidos"] == 95
    assert data["tiempo_promedio_espera"] == 18.694736842105264
    assert "fecha_ejecucion" in data
    created_resultado_id = data["id"]


def test_obtener_todos_los_resultados():
    headers = get_auth_headers()
    response = client.get("/resultados/", headers=headers)
    assert response.status_code == 200
    resultados = response.json()
    assert isinstance(resultados, list)
    assert len(resultados) >= 1
    ids = [r["id"] for r in resultados]
    assert created_resultado_id in ids


def test_obtener_resultados_filtrados_por_escenario():
    headers = get_auth_headers()
    response = client.get(
        f"/resultados/?escenario_id={created_escenario_id}", headers=headers
    )
    assert response.status_code == 200
    resultados = response.json()
    assert isinstance(resultados, list)
    ids = [r["id"] for r in resultados]
    assert created_resultado_id in ids


def test_obtener_resultado_por_id():
    headers = get_auth_headers()
    response = client.get(f"/resultados/{created_resultado_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_resultado_id
    assert data["escenario_id"] == created_escenario_id
    assert data["vehiculos_atendidos"] == 95


def test_eliminar_resultado():
    headers = get_auth_headers()
    del_res = client.delete(f"/resultados/{created_resultado_id}", headers=headers)
    assert del_res.status_code == 204

    get_res = client.get(f"/resultados/{created_resultado_id}", headers=headers)
    assert get_res.status_code == 404


def test_resultados_no_autorizados_y_no_existentes():
    headers = get_auth_headers()
    assert client.get("/resultados/").status_code == 401
    assert (
        client.post(
            "/resultados/registrar",
            json={"escenario_id": created_escenario_id, "vehiculos_atendidos": 10},
        ).status_code
        == 401
    )
    assert client.get("/resultados/999999").status_code == 401
    assert client.delete("/resultados/999999").status_code == 401

    assert (
        client.post(
            "/resultados/registrar",
            json={"escenario_id": 999999, "vehiculos_atendidos": 10},
            headers=headers,
        ).status_code
        == 404
    )
    assert client.get("/resultados/999999", headers=headers).status_code == 404
    assert client.delete("/resultados/999999", headers=headers).status_code == 404


def test_aislamiento_entre_usuarios():
    other_user = {
        "nombre": "Intruder",
        "correo": "intruder@collective.com",
        "password": "OtherPassword123",
    }
    db = session_local()
    existing = db.query(User).filter(User.correo == other_user["correo"]).first()
    if existing:
        db.delete(existing)
        db.commit()
    db.close()

    try:
        reg = client.post("/auth/register", json=other_user)
        assert reg.status_code == 201
        login = client.post(
            "/auth/login",
            json={"correo": other_user["correo"], "password": other_user["password"]},
        )
        other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        assert client.get(f"/proyectos/{created_proyecto_id}", headers=other_headers).status_code == 404
        assert client.get(f"/escenarios/{created_escenario_id}", headers=other_headers).status_code == 404
        assert (
            client.post(f"/escenarios/{created_escenario_id}/duplicar", headers=other_headers).status_code
            == 404
        )
        assert (
            client.post(
                "/resultados/registrar",
                json={"escenario_id": created_escenario_id, "vehiculos_atendidos": 5},
                headers=other_headers,
            ).status_code
            == 404
        )
    finally:
        db = session_local()
        u = db.query(User).filter(User.correo == other_user["correo"]).first()
        if u:
            db.delete(u)
            db.commit()
        db.close()


# ====================================
# Tests para Simulación y WebSocket (CU-07, CU-13)
# ====================================

def test_simulacion_endpoints_requieren_jwt():
    assert client.get("/red").status_code == 401
    assert client.patch("/infraestructura/e1", json={"carriles": 2}).status_code == 401
    assert client.patch("/semaforo/t1", json={"fases": []}).status_code == 401
    assert client.get("/resultado").status_code == 401
    assert client.post("/simular", json={"escenario_id": 1}).status_code == 401


def test_simulacion_websocket_rechaza_sin_token_o_invalido():
    with pytest.raises(WebSocketDisconnect) as exc_no_token:
        with client.websocket_connect("/ws/simular"):
            pass
    assert exc_no_token.value.code == 4001

    with pytest.raises(WebSocketDisconnect) as exc_bad_token:
        with client.websocket_connect("/ws/simular?token=token_invalido"):
            pass
    assert exc_bad_token.value.code == 4001


def test_simulacion_rest_y_websocket_con_jwt_mock_sumo():
    headers = get_auth_headers()
    token = headers["Authorization"].split(" ", 1)[1]
    sent_to_sumo = []

    class FakeSumoWS:
        def __init__(self, responses):
            self._responses = list(responses)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def send(self, message):
            sent_to_sumo.append(json.loads(message))

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self._responses:
                raise StopAsyncIteration
            return json.dumps(self._responses.pop(0))

    indicadores = {
        "vehiculos_atendidos": 42,
        "tiempo_promedio_espera": 11.5,
        "velocidad_promedio": 32.0,
        "longitud_max_fila": 18.0,
    }

    # 1) POST /simular reenvía el token JWT hacia SUMO
    with patch(
        "services.sumo_service.websockets.connect",
        return_value=FakeSumoWS([{"action": "simular_response", "data": indicadores}]),
    ):
        res = client.post(
            "/simular",
            json={"escenario_id": created_escenario_id},
            headers=headers,
        )
    assert res.status_code == 200
    assert res.json()["data"] == indicadores
    assert sent_to_sumo[-1]["payload"]["token"] == token

    # 2) WS /ws/simular?token=... reenvía progreso, token y persiste resultado en BD
    sent_to_sumo.clear()
    ws_responses = [
        {"action": "progress", "progress": 50, "message": "Simulando tráfico..."},
        {"action": "simular_response", "data": indicadores},
    ]
    with patch(
        "services.sumo_service.websockets.connect",
        return_value=FakeSumoWS(ws_responses),
    ):
        with client.websocket_connect(f"/ws/simular?token={token}") as ws:
            ws.send_text(json.dumps({"escenario_id": created_escenario_id}))
            msg1 = ws.receive_json()
            assert msg1["status"] == "iniciando"
            assert msg1["progress"] == 5

            msg2 = ws.receive_json()
            assert msg2["status"] == "simulando"
            assert msg2["progress"] == 50

            msg3 = ws.receive_json()
            assert msg3["status"] == "completado"
            assert msg3["progress"] == 100
            assert msg3["resultado"] == indicadores

    assert sent_to_sumo[-1]["payload"]["token"] == token

    # Verificar que SumoService persistió el resultado automáticamente en BD
    res_list = client.get(
        f"/resultados/?escenario_id={created_escenario_id}",
        headers=headers,
    )
    assert res_list.status_code == 200
    resultados = res_list.json()
    assert any(r["vehiculos_atendidos"] == 42 for r in resultados)


# ====================================
# Limpieza Final: Eliminación de Usuario
# ====================================

def test_delete_user_and_verify_login_fails():
    login_res = client.post(
        "/auth/login",
        json={"correo": TEST_USER["correo"], "password": NEW_PASSWORD},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    del_res = client.delete("/auth/me", headers=headers)
    assert del_res.status_code == 200
    assert "eliminado" in del_res.json()["mensaje"].lower()

    login_after_delete = client.post(
        "/auth/login",
        json={"correo": TEST_USER["correo"], "password": NEW_PASSWORD},
    )
    assert login_after_delete.status_code == 401
