import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
import websockets

SUMO_WS_URL = "ws://sumo:8000"
SUMO_WS_URL_LOCAL = "ws://localhost:8000"

class SumoService:
    @staticmethod
    async def _send_ws_request(payload: dict):
        for target_url in [SUMO_WS_URL, SUMO_WS_URL_LOCAL]:
            try:
                async with websockets.connect(target_url) as ws:
                    await ws.send(json.dumps(payload))
                    async for response in ws:
                        data = json.loads(response)
                        if data.get("action") == "progress":
                            continue
                        return data
            except Exception:
                continue
        return {"error": "No se pudo conectar al servicio SUMO"}

    @staticmethod
    async def simular(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    await websocket.send_json({"error": "Invalid JSON format", "message": "Invalid JSON format"})
                    continue

                await websocket.send_json({
                    "status": "iniciando",
                    "progress": 5,
                    "message": "Conectando al microservicio SUMO..."
                })
                
                req_payload = {"action": "simular", "payload": payload}
                connected = False

                for target_url in [SUMO_WS_URL, SUMO_WS_URL_LOCAL]:
                    try:
                        async with websockets.connect(target_url) as ws:
                            connected = True
                            await ws.send(json.dumps(req_payload))
                            
                            async for raw_res in ws:
                                res = json.loads(raw_res)
                                action = res.get("action")

                                if action == "progress":
                                    await websocket.send_json({
                                        "status": "simulando",
                                        "progress": res.get("progress", 50),
                                        "message": res.get("message", "Simulando..."),
                                        "detail": res.get("message", "Simulando...")
                                    })
                                elif action == "simular_response" or "data" in res:
                                    resultado = res.get("data", {})
                                    await websocket.send_json({
                                        "status": "completado",
                                        "progress": 100,
                                        "message": res.get("message", "Simulación completada con éxito"),
                                        "detail": "Simulación completada",
                                        "resultado": resultado
                                    })

                                    import httpx
                                    try:
                                        esc_id = payload.get("escenario_id")
                                        if esc_id:
                                            async with httpx.AsyncClient() as client:
                                                await client.post(
                                                    "http://localhost:8000/resultado-sumo",
                                                    json={"escenario_id": esc_id, **resultado}
                                                )
                                    except Exception:
                                        pass
                                    break
                                elif "error" in res:
                                    await websocket.send_json({
                                        "status": "error",
                                        "detail": res["error"],
                                        "message": res["error"]
                                    })
                                    break
                        if connected:
                            break
                    except Exception:
                        continue

                if not connected:
                    await websocket.send_json({
                        "status": "error",
                        "detail": "No se pudo conectar al microservicio SUMO (ws://sumo:8000).",
                        "message": "No se pudo conectar al microservicio SUMO"
                    })

        except WebSocketDisconnect:
            pass

    @staticmethod
    async def proxy_get_red():
        return await SumoService._send_ws_request({"action": "get_red"})
            
    @staticmethod
    async def proxy_patch_infraestructura(edge_id: str, datos: dict):
        return await SumoService._send_ws_request({
            "action": "patch_infraestructura",
            "edge_id": edge_id,
            "datos": datos
        })
            
    @staticmethod
    async def proxy_patch_semaforo(tls_id: str, datos: dict):
        return await SumoService._send_ws_request({
            "action": "patch_semaforo",
            "tls_id": tls_id,
            "datos": datos
        })
            
    @staticmethod
    async def proxy_get_resultado():
        return await SumoService._send_ws_request({"action": "get_resultado"})
            
    @staticmethod
    async def proxy_post_simular(payload: dict):
        return await SumoService._send_ws_request({
            "action": "simular",
            "payload": payload
        })
