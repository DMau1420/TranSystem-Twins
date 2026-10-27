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

import os
import requests

def make_progress_callback(websocket, loop):
    def on_progress(pct, msg):
        try:
            asyncio.run_coroutine_threadsafe(
                websocket.send(json.dumps({
                    "action": "progress",
                    "progress": pct,
                    "message": msg
                })),
                loop
            )
        except Exception as e:
            print(f"Error reportando progreso: {e}")
    return on_progress

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
                payload = req.get("payload", {})
                escenario_id = payload.get("escenario_id") if isinstance(payload, dict) else None
                escenario_actual = dict(ESCENARIO)
                proyecto_actual = dict(PROYECTO)

                await websocket.send(json.dumps({
                    "action": "progress",
                    "progress": 5,
                    "message": "Inicializando motor de simulación SUMO..."
                }))

                if isinstance(payload, dict):
                    if payload.get("duracion_segundos"):
                        escenario_actual["duracion_segundos"] = int(payload["duracion_segundos"])
                    if payload.get("demanda_vehicular"):
                        escenario_actual["demanda_vehicular"] = int(payload["demanda_vehicular"])

                if escenario_id:
                    backend_url = os.getenv("BACKEND_URL", "http://backend:8000")
                    if not backend_url.startswith("http"):
                        backend_url = f"http://{backend_url}"
                    try:
                        r_esc = requests.get(f"{backend_url}/escenarios/{escenario_id}", timeout=5)
                        if r_esc.status_code == 200:
                            esc_data = r_esc.json()
                            escenario_actual["id"] = esc_data["id"]
                            escenario_actual["proyecto_id"] = esc_data["proyecto_id"]
                            escenario_actual["nombre"] = esc_data.get("nombre", "Escenario")
                            escenario_actual["modificaciones_edges"] = esc_data.get("modificaciones_edges", [])
                            escenario_actual["modificaciones_semaforos"] = esc_data.get("modificaciones_semaforos", [])
                            if not (isinstance(payload, dict) and payload.get("demanda_vehicular")):
                                escenario_actual["demanda_vehicular"] = esc_data.get("demanda_vehicular", 100)
                            if not (isinstance(payload, dict) and payload.get("duracion_segundos")):
                                escenario_actual["duracion_segundos"] = esc_data.get("duracion_segundos", 3600)

                            r_proj = requests.get(f"{backend_url}/proyectos/{esc_data['proyecto_id']}", timeout=5)
                            if r_proj.status_code == 200:
                                proj_data = r_proj.json()
                                proyecto_actual["id"] = proj_data["id"]
                                proyecto_actual["nombre"] = proj_data.get("nombre", "Proyecto")
                                if proj_data.get("geometria"):
                                    proyecto_actual["geometria"] = proj_data["geometria"]
                                proyecto_actual["netxml_base_url"] = proj_data.get("netxml_base_url")
                                proyecto_actual["geojson_url"] = proj_data.get("geojson_url")
                                proyecto_actual["osm_file_url"] = proj_data.get("osm_file_url")
                    except Exception as err:
                        print(f"Aviso: usando fallback local para escenario {escenario_id}: {err}")

                loop = asyncio.get_running_loop()
                prog_cb = make_progress_callback(websocket, loop)

                def run_sim():
                    global RED_BASE
                    red_base_actual = RED_BASE
                    if red_base_actual is None or not red_base_actual.get("netxml_base_url"):
                        prog_cb(10, f"Importando zona para '{proyecto_actual['nombre']}'...")
                        red_base_actual = importar_zona(proyecto_actual, HERRAMIENTAS, on_progress=prog_cb)
                        proyecto_actual["netxml_base_url"] = red_base_actual["netxml_base_url"]
                        proyecto_actual["geojson_url"] = red_base_actual["geojson_url"]
                        proyecto_actual["osm_file_url"] = red_base_actual["osm_file_url"]
                        RED_BASE = red_base_actual

                    indicadores = simular_escenario(escenario_actual, red_base_actual, HERRAMIENTAS, on_progress=prog_cb)
                    return indicadores

                indicadores = await asyncio.to_thread(run_sim)
                ULTIMO_RESULTADO = indicadores
                await websocket.send(json.dumps({
                    "action": "simular_response",
                    "status": "completado",
                    "progress": 100,
                    "message": "Simulación completada exitosamente",
                    "data": indicadores
                }))
                
            elif action == "get_resultado":
                if ULTIMO_RESULTADO is None:
                    await websocket.send(json.dumps({"error": "Todavía no se ha corrido ninguna simulación", "status": 404}))
                else:
                    await websocket.send(json.dumps({"action": "resultado_response", "data": ULTIMO_RESULTADO}))
            else:
                await websocket.send(json.dumps({"error": "Unknown action"}))
                
        except Exception as e:
            print(f"Error en websocket handler: {e}")
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
