import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
import httpx

class SumoService:
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

                # Notificar al cliente que inició la simulación
                await websocket.send_json({"status": "iniciando", "progress": 0})

                try:
                    # Enviar a SUMO usando el servidor temporal interno de la red docker (asume que sumo está en http://sumo:8000)
                    # o localhost si se corre todo fuera de docker.
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        await websocket.send_json({"status": "simulando", "progress": 50})

                        # Intentar conectarse al servicio sumo (nombre del contenedor) o localhost fallback
                        try:
                            sumo_url = "http://sumo:8000/simular"
                            response = await client.post(sumo_url, json=payload)
                        except httpx.RequestError:
                            sumo_url = "http://localhost:8000/simular" # Fallback local
                            response = await client.post(sumo_url, json=payload)

                        response.raise_for_status()
                        resultado = response.json()

                        await websocket.send_json({"status": "completado", "progress": 100, "resultado": resultado})

                        # Mandar resultado al endpoint de backend para mantener consistencia con el requerimiento
                        try:
                            # Puede ser a /resultado-sumo
                            backend_url = "http://localhost:8000/resultado-sumo"
                            await client.post(backend_url, json=resultado)
                        except httpx.RequestError:
                            pass # No fallar si este endpoint no responde
                except Exception as e:
                    await websocket.send_json({"status": "error", "detail": f"Error al simular en SUMO: {str(e)}"})

        except WebSocketDisconnect:
            pass # Cliente desconectado
