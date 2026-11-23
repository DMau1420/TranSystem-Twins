import asyncio
import json
import websockets

from sumo_tools import cargar_herramientas_sumo
from main import importar_zona, simular_escenario

PROYECTO = {
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
    "osm_file_url": None,
}

ESCENARIO = {
    "id": 12,
    "proyecto_id": PROYECTO["id"],
    "nombre": "Situacion actual",
    "modificaciones_edges": [],
    "modificaciones_semaforos": [],
    "demanda_vehicular": 100,
    "duracion_segundos": 3600,
}

RED_BASE = None
HERRAMIENTAS = None
ULTIMO_RESULTADO = None

async def handler(websocket):
    global RED_BASE, ULTIMO_RESULTADO
    async for message in websocket:
        try:
            req = json.loads(message)
            action = req.get("action")
            
            if action == "get_red":
                if PROYECTO["geojson_url"] is None:
                    await websocket.send(json.dumps({"error": "La zona todavía no se ha importado", "status": 409}))
                    continue
                with open(PROYECTO["geojson_url"], "r", encoding="utf-8") as f:
                    red_geojson = json.load(f)
                await websocket.send(json.dumps({"action": "red_response", "data": red_geojson}))
                
            elif action == "patch_infraestructura":
                edge_id = req.get("edge_id")
                datos = req.get("datos", {})
                modificaciones = ESCENARIO["modificaciones_edges"]
                modificaciones[:] = [m for m in modificaciones if m["edge_id"] != edge_id]
                modificaciones.append({
                    "edge_id": edge_id,
                    "carriles": datos.get("carriles"),
                    "velocidad_max": datos.get("velocidad_max"),
                })
                await websocket.send(json.dumps({"action": "infra_response", "ok": True, "edge_id": edge_id}))
                
            elif action == "patch_semaforo":
                tls_id = req.get("tls_id")
                datos = req.get("datos", {})
                fases_entrada = datos.get("fases", [])
                fases_normalizadas = []
                for fase in fases_entrada:
                    fases_normalizadas.append({
                        "indice": fase["indice"],
                        "duracion": fase.get("duracion"),
                        "estado": fase.get("estado"),
                    })
                modificaciones = ESCENARIO["modificaciones_semaforos"]
                modificaciones[:] = [m for m in modificaciones if m["tls_id"] != tls_id]
                modificaciones.append({"tls_id": tls_id, "fases": fases_normalizadas})
                await websocket.send(json.dumps({"action": "semaforo_response", "ok": True, "tls_id": tls_id}))
                
            elif action == "simular":
                if RED_BASE is None:
                    RED_BASE = importar_zona(PROYECTO, HERRAMIENTAS)
                    PROYECTO["netxml_base_url"] = RED_BASE["netxml_base_url"]
                    PROYECTO["geojson_url"] = RED_BASE["geojson_url"]
                    PROYECTO["osm_file_url"] = RED_BASE["osm_file_url"]
                
                # Payload might contain specific inputs to override the global scenario
                # But here we just use the global variables as before
                indicadores = simular_escenario(ESCENARIO, RED_BASE, HERRAMIENTAS)
                ULTIMO_RESULTADO = indicadores
                await websocket.send(json.dumps({"action": "simular_response", "data": indicadores}))
                
            elif action == "get_resultado":
                if ULTIMO_RESULTADO is None:
                    await websocket.send(json.dumps({"error": "Todavía no se ha corrido ninguna simulación", "status": 404}))
                else:
                    await websocket.send(json.dumps({"action": "resultado_response", "data": ULTIMO_RESULTADO}))
            else:
                await websocket.send(json.dumps({"error": "Unknown action"}))
                
        except Exception as e:
            await websocket.send(json.dumps({"error": str(e)}))

async def main():
    global HERRAMIENTAS
    print("Cargando herramientas de SUMO...")
    HERRAMIENTAS = cargar_herramientas_sumo()
    
    print("Servidor WebSocket iniciado en ws://0.0.0.0:8000")
    async with websockets.serve(handler, "0.0.0.0", 8000):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
