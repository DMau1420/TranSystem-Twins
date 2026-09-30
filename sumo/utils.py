from pathlib import Path
import time

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def carpeta_proyecto(proyecto_id) -> Path:
    """
    Carpeta raíz de UN proyecto. Aquí viven los archivos que se generan
    UNA sola vez por proyecto: la red descargada de OSM, la red base ya
    convertida a .net.xml, y el  GeoJSON"""

    carpeta = DATA_DIR / "proyectos" / str(proyecto_id)
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def carpeta_escenario(proyecto_id, escenario_id) -> Path:
    """
    Carpeta de UN escenario dentro de un proyecto. Aquí viven los archivos
    propios de ese escenario: red modificada (si aplica), demanda vehicular,
    configuración de SUMO, resultado de tripinfo.
    """
    carpeta = carpeta_proyecto(proyecto_id) / "escenarios" / str(escenario_id)
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta
