"""
Test de integración del pipeline SUMO.

"""
import os
import random
import shutil
from pathlib import Path

import pytest

from main import simular_escenario
from sumo_tools import cargar_herramientas_sumo
from utils import carpeta_proyecto, carpeta_escenario

PROYECTO_ID = 3
ESCENARIO_ID_PRUEBA = 99999


SEED = int(os.environ.get("TEST_SEED", "42"))

# Estas son modificaciones de prueba que aplique a 
MOD_SEMAFORO = [{
    "tls_id": "7918185959",
    "fases": [
        {"indice": 0, "duracion": 100, "estado": None},
        {"indice": 1, "duracion": 50, "estado": None},
        {"indice": 2, "duracion": 50, "estado": None},
    ],
}]


@pytest.fixture(scope="module")
def herramientas():
    try:
        return cargar_herramientas_sumo()
    except Exception as e:
        pytest.skip(f"SUMO no disponible: {e}")


@pytest.fixture(scope="module")
def red_base():
    netxml = Path(carpeta_proyecto(PROYECTO_ID)) / "red_base.net.xml"
    if not netxml.exists():
        pytest.skip(f"No existe la red base importada: {netxml}")
    return {"osm_file_url": None, "netxml_base_url": str(netxml), "geojson_url": None}


@pytest.fixture
def carpeta_prueba():
    carpeta = Path(carpeta_escenario(PROYECTO_ID, ESCENARIO_ID_PRUEBA))
    yield carpeta
    shutil.rmtree(carpeta, ignore_errors=True)  # limpia al terminar


def escenario_aleatorio(rng, modificaciones_semaforos=None):
    return {
        "id": ESCENARIO_ID_PRUEBA,
        "proyecto_id": PROYECTO_ID,
        "nombre": f"Escenario de prueba (seed={SEED})",
        "modificaciones_edges": [],
        "modificaciones_semaforos": modificaciones_semaforos or [],
        "demanda_vehicular": rng.randint(50, 300),
        "duracion_segundos": 900,  # corto para que el test sea rápido
    }


@pytest.mark.integration
@pytest.mark.parametrize("modificaciones", [None, MOD_SEMAFORO], ids=["sin_mods", "con_semaforo"])
def test_pipeline_completo(herramientas, red_base, carpeta_prueba, modificaciones):
    rng = random.Random(SEED)
    escenario = escenario_aleatorio(rng, modificaciones)
    print(f"\nDemanda aleatoria: {escenario['demanda_vehicular']} (seed={SEED})")

    indicadores = simular_escenario(escenario, red_base, herramientas)


    # Etapas intermedias: cada una dejó su archivo
    archivos = ["demanda.rou.xml", "simulacion.sumocfg", "tripinfo.xml"]
    if modificaciones:  # solo se reconstruye la red si hubo cambios
        archivos.append("red_escenario.net.xml")

    for nombre in archivos:
        assert (carpeta_prueba / nombre).exists(), f"Falta {nombre}"

    # Indicadores completos
    esperados = {
        "vehiculos_atendidos", "tiempo_promedio_espera", "velocidad_promedio",
        "longitud_max_fila", "tiempo_promedio_recorrido",
    }
    assert esperados <= set(indicadores), f"Faltan: {esperados - set(indicadores)}"

    # Valores con sentido físico
    assert indicadores["vehiculos_atendidos"] > 0
    assert indicadores["tiempo_promedio_espera"] >= 0
    assert 0 < indicadores["velocidad_promedio"] < 130  # km/h
    assert indicadores["longitud_max_fila"] >= 0
    assert indicadores["tiempo_promedio_recorrido"] > 0