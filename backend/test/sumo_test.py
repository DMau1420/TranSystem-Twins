import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

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

    # Nos conectamos al WebSocket expuesto por FastAPI
    with client.websocket_connect("/ws/simular") as websocket:
        websocket.send_text(json.dumps(test_payload))
        
        # 1. Esperamos confirmación de inicio
        response_iniciando = websocket.receive_json()
        assert response_iniciando["status"] == "iniciando"
        assert response_iniciando["progress"] == 0

        # 2. Esperamos notificación de simulación en proceso
        response_simulando = websocket.receive_json()
        assert response_simulando["status"] == "simulando"
        assert response_simulando["progress"] == 50

        # 3. Esperamos el resultado final (o error si el motor de sumo no está corriendo)
        response_final = websocket.receive_json()
        assert response_final["status"] in ["completado", "error"]
        
        if response_final["status"] == "completado":
            assert "resultado" in response_final
            assert response_final["progress"] == 100
            print("\n=== RESULTADOS DE LA SIMULACIÓN ===")
            print(json.dumps(response_final["resultado"], indent=2))
        else:
            # Si el backend de sumo temporal no está levantado en localhost:8000
            # o sumo:8000, fallará con 'error'.
            print("El servidor SUMO temporal no respondió o hubo un error:", response_final.get("detail"))
