import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
import websockets

SUMO_WS_URL = "ws://sumo:8000"
SUMO_WS_URL_LOCAL = "ws://localhost:8000"

class SumoService:
    @staticmethod
    async def _send_ws_request(payload: dict):
        try:
            async with websockets.connect(SUMO_WS_URL) as ws:
                await ws.send(json.dumps(payload))
                response = await ws.recv()
                return json.loads(response)
        except Exception:
            async with websockets.connect(SUMO_WS_URL_LOCAL) as ws:
                await ws.send(json.dumps(payload))
                response = await ws.recv()
                return json.loads(response)

    @staticmethod
    async def simular(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    await websocket.send_json({"error": "Invalid JSON format"})
                    continue

                await websocket.send_json({"status": "iniciando", "progress": 0})
                
                try:
                    await websocket.send_json({"status": "simulando", "progress": 50})
                    
                    req_payload = {"action": "simular", "payload": payload}
                    try:
                        async with websockets.connect(SUMO_WS_URL) as ws:
                            await ws.send(json.dumps(req_payload))
                            res = await ws.recv()
                            resultado_data = json.loads(res)
                    except Exception:
                        async with websockets.connect(SUMO_WS_URL_LOCAL) as ws:
                            await ws.send(json.dumps(req_payload))
                            res = await ws.recv()
                            resultado_data = json.loads(res)
                    
                    if "error" in resultado_data:
                        await websocket.send_json({"status": "error", "detail": resultado_data["error"]})
                    else:
                        resultado = resultado_data.get("data", {})
                        await websocket.send_json({"status": "completado", "progress": 100, "resultado": resultado})
                        
                        # Guardar el resultado (esto es de la implementacion original, podemos hacer request via httpx aqui
                        # porque back->back es HTTP normal)
                        import httpx
                        try:
                            async with httpx.AsyncClient() as client:
                                await client.post("http://localhost:8000/resultado-sumo", json=resultado)
                        except httpx.RequestError:
                            pass
                except Exception as e:
                    await websocket.send_json({"status": "error", "detail": f"Error al simular en SUMO: {str(e)}"})

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
