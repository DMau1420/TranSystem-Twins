import pytest
from fastapi.testclient import TestClient

from core.database import session_local
from core.security import decode_access_token
from main import app
from models.md_user import User

client = TestClient(app)

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


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "Ok"}


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
    # Obtener token con las credenciales actuales
    login_data = {
        "correo": TEST_USER["correo"],
        "password": TEST_USER["password"],
    }
    login_res = client.post("/auth/login", json=login_data)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Modificar nombre y apodo
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
    # Obtener token con la contraseña inicial
    login_data = {
        "correo": TEST_USER["correo"],
        "password": TEST_USER["password"],
    }
    login_res = client.post("/auth/login", json=login_data)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Actualizar la contraseña
    patch_res = client.patch(
        "/auth/me",
        json={"password": NEW_PASSWORD},
        headers=headers,
    )
    assert patch_res.status_code == 200

    # Verificar que el login con la contraseña antigua falle (401)
    old_login = client.post(
        "/auth/login",
        json={"correo": TEST_USER["correo"], "password": TEST_USER["password"]},
    )
    assert old_login.status_code == 401

    # Verificar que el login con la nueva contraseña sea exitoso (200)
    new_login = client.post(
        "/auth/login",
        json={"correo": TEST_USER["correo"], "password": NEW_PASSWORD},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()


def test_unauthorized_operations():
    # Intento de modificar sin token
    unauth_patch = client.patch("/auth/me", json={"nombre": "Hacker"})
    assert unauth_patch.status_code == 401

    # Intento de eliminar sin token
    unauth_delete = client.delete("/auth/me")
    assert unauth_delete.status_code == 401


def test_delete_user_and_verify_login_fails():
    # Iniciar sesión con la contraseña actual (NEW_PASSWORD)
    login_res = client.post(
        "/auth/login",
        json={"correo": TEST_USER["correo"], "password": NEW_PASSWORD},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Eliminar el usuario autenticado
    del_res = client.delete("/auth/me", headers=headers)
    assert del_res.status_code == 200
    assert "eliminado" in del_res.json()["mensaje"].lower()

    # Intentar hacer login -> si no da respuesta / da 401, pasa la prueba
    login_after_delete = client.post(
        "/auth/login",
        json={"correo": TEST_USER["correo"], "password": NEW_PASSWORD},
    )
    assert login_after_delete.status_code == 401
