from pathlib import Path
import time

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

def generar_ruta_salida(nombre_archivo: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return DATA_DIR / f"{timestamp}_{nombre_archivo}"