from fastapi import APIRouter, WebSocket
from services.sumo_service import SumoService

router = APIRouter(tags=["Simulación"])

@router.websocket("/ws/simular")
async def websocket_simular(websocket: WebSocket):
    await SumoService.simular(websocket)
