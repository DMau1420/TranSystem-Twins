from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {"status": "Ok"}

def test_login():
    test_data = {"correo": "mau@example.com", "password": "mau12345"}
    response = client.post("/auth/login", json=test_data)
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
