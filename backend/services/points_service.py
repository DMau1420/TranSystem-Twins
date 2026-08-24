import json
from pathlib import Path

from core.exceptions import CantSavePointException, CantReadPointException, DoesntExistPointsException
from schemas.sc_points import PointsPayload

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "saved_points"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def create_points(payload: PointsPayload):
    saved_files = []

    for point in payload.points:
        point_data = point.model_dump()
        file_path = OUTPUT_DIR / f"{point.id}.json"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(point_data, f, ensure_ascii=False, indent=4)
            saved_files.append(str(file_path))
        except Exception as e:
            raise CantSavePointException(point.id, e)

    return {
        "status": "success",
        "message": f"Se crearon {len(saved_files)} archivo(s) JSON correctamente.",
        "saved_files": saved_files,
    }


def list_all_points():
    json_files = sorted(list(OUTPUT_DIR.glob("*.json")))
    
    records = []
    available_ids = []
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                records.append(content)
                available_ids.append(file_path.stem)
        except Exception:
            continue

    return {
        "total_files": len(records),
        "available_ids": available_ids,
        "points": records
    }

def get_point_by_id(point_id: str):
    clean_id = point_id[:-5] if point_id.endswith(".json") else point_id
    file_path = OUTPUT_DIR / f"{clean_id}.json"

    # Verifica si el archivo existe
    if not file_path.is_file():
        raise DoesntExistPointsException(clean_id)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            point_data = json.load(f)
        return point_data
    except Exception as e:
        raise CantReadPointException(clean_id, str(e))
