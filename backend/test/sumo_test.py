import json
from fastapi.testclient import TestClient

from core.database import session_local
from main import app
from models.md_user import User

client = TestClient(app)


def _get_test_token() -> str:
    user_data = {
        "nombre": "SumoTester",
        "correo": "sumo_ws_test@collective.com",
        "password": "SumoTestPassword123",
    }
    db = session_local()
    existing = db.query(User).filter(User.correo == user_data["correo"]).first()
    if existing:
        db.delete(existing)
        db.commit()
    db.close()

    client.post("/auth/register", json=user_data)
    login_res = client.post(
        "/auth/login",
        json={"correo": user_data["correo"], "password": user_data["password"]},
    )
    return login_res.json()["access_token"]


def _cleanup_test_user():
    db = session_local()
    existing = db.query(User).filter(User.correo == "sumo_ws_test@collective.com").first()
    if existing:
        db.delete(existing)
        db.commit()
    db.close()


def test_sumo_simulation_websocket():
    # JSON de prueba, aunque el servidor temporal en sumo/server.py
    # utilizará sus propias variables globales por ahora.
    test_payload = {
        "proyecto": {
            "id": 3,
            "nombre": "Interseccion Av. Insurgentes",
            "geometria": {
                "id": "b3e33657-6c14-4c60-aeca-0fee5b22ca4a",
                "geoJson": {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [-99.182682, 19.448788],
                            [-99.18045, 19.456395],
                            [-99.175816, 19.471448],
                            [-99.188347, 19.469505],
                            [-99.190407, 19.460442],
                            [-99.182682, 19.448788],
                        ]]
                    },
                },
            },
            "netxml_base_url": None,
            "geojson_url": None,
        },
        "escenario": {
            "id": 12,
            "proyecto_id": 3,
            "nombre": "Situacion actual",
            "modificaciones_edges": [],
            "modificaciones_semaforos": [],
            "demanda_vehicular": 100,
            "duracion_segundos": 3600,
        }
    }

    token = _get_test_token()
    try:
        # Nos conectamos al WebSocket autenticado expuesto por FastAPI
        with client.websocket_connect(f"/ws/simular?token={token}") as websocket:
            websocket.send_text(json.dumps(test_payload))

            # 1. Esperamos confirmación de inicio
            response_iniciando = websocket.receive_json()
            assert response_iniciando["status"] == "iniciando"
            assert response_iniciando["progress"] == 5

            # 2. Recibimos notificaciones hasta completar o recibir error si SUMO no está corriendo
            response_final = websocket.receive_json()
            while response_final["status"] == "simulando":
                response_final = websocket.receive_json()

            assert response_final["status"] in ["completado", "error"]

            if response_final["status"] == "completado":
                assert "resultado" in response_final
                assert response_final["progress"] == 100
                print("\n=== RESULTADOS DE LA SIMULACIÓN ===")
                print(json.dumps(response_final["resultado"], indent=2))
            else:
                print("El servidor SUMO temporal no respondió o hubo un error:", response_final.get("detail"))
    finally:
        _cleanup_test_user()
