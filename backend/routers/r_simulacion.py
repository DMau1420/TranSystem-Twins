from fastapi import APIRouter, WebSocket
from services.sumo_service import SumoService

router = APIRouter(tags=["Simulación"])

@router.websocket("/ws/simular")
async def websocket_simular(websocket: WebSocket):
    await SumoService.simular(websocket)

@router.get("/red")
async def get_red():
    return await SumoService.proxy_get_red()

@router.patch("/infraestructura/{edge_id}")
async def patch_infra(edge_id: str, datos: dict):
    return await SumoService.proxy_patch_infraestructura(edge_id, datos)

@router.patch("/semaforo/{tls_id}")
async def patch_semaforo(tls_id: str, datos: dict):
    return await SumoService.proxy_patch_semaforo(tls_id, datos)

@router.get("/resultado")
async def get_resultado():
    return await SumoService.proxy_get_resultado()

@router.post("/simular")
async def post_simular(payload: dict):
    return await SumoService.proxy_post_simular(payload)
