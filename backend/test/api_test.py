import pytest
from fastapi.testclient import TestClient

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
    unauth_patch = client.patch("/auth/me", json={"nombre": "Hacker"})
    assert unauth_patch.status_code == 401

    unauth_delete = client.delete("/auth/me")
    assert unauth_delete.status_code == 401


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
