from fastapi import APIRouter, HTTPException, status

from schemas.sc_escenarios import escenario

router = APIRouter(
    prefix = "/escenarios"
)

@router.get("/")
def ping():
    return {"esceneario": "ok"}

datos_hardcode = {
    "escenario_id": 101,
    "zona_geom": {
        "type": "Polygon",
        "coordinates": [
            [-99.1332, 19.4326],
            [-99.1400, 19.4400],
            [-99.1300, 19.4450],
            [-99.1332, 19.4326],
        ],
    },
    "demanda_sintetica": {
        "vehiculos_por_hora": 450,
        "direccion": "Norte-Sur",
    },
}

@router.get("/prueba", response_model=escenario)
def hardcoded_scenario():
    return datos_hardcode