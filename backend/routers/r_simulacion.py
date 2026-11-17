from fastapi import APIRouter, Depends, HTTPException, WebSocket
from core.database import session_local
from models.md_user import User
from services.auth_service import AuthService, oauth2_scheme
from services.sumo_service import SumoService

router = APIRouter(tags=["Simulación"])


def _extract_ws_token(websocket: WebSocket) -> str | None:
    token = websocket.query_params.get("token")
    if token:
        return token
    auth_header = websocket.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return None


@router.websocket("/ws/simular")
async def websocket_simular(websocket: WebSocket):
    token = _extract_ws_token(websocket)
    if not token:
        await websocket.close(code=4001, reason="Token requerido")
        return

    db = session_local()
    try:
        current_user = AuthService.obtener_usuario_desde_token(db=db, token=token)
    except HTTPException:
        await websocket.close(code=4001, reason="Token inválido o expirado")
        return
    finally:
        db.close()

    await SumoService.simular(websocket, usuario_id=current_user.id, token=token)


@router.get("/red")
async def get_red(
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return await SumoService.proxy_get_red()


@router.patch("/infraestructura/{edge_id}")
async def patch_infra(
    edge_id: str,
    datos: dict,
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return await SumoService.proxy_patch_infraestructura(edge_id, datos)


@router.patch("/semaforo/{tls_id}")
async def patch_semaforo(
    tls_id: str,
    datos: dict,
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return await SumoService.proxy_patch_semaforo(tls_id, datos)


@router.get("/resultado")
async def get_resultado(
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return await SumoService.proxy_get_resultado()


@router.post("/simular")
async def post_simular(
    payload: dict,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(AuthService.obtener_usuario_actual),
):
    return await SumoService.proxy_post_simular(payload, token=token)
