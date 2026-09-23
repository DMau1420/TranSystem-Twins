import time
import requests


def calcular_bbox(polygon):
    """Calcula bbox desde un polígono GeoJSON."""
    coords = polygon["coordinates"][0]  # anillo exterior
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return (min(lats), min(lons), max(lats), max(lons))

def descargar_red(bbox, intentos_max=3):
    """Descarga la red vial en formato XML (.osm) garantizando geometrías completas.

    Maneja timeouts y reintentos en servidores de respaldo.
    """
    min_lat, min_lon, max_lat, max_lon = bbox

    # Query Overpass 
    query = f"""
    [out:xml][timeout:90];
    (
    way["highway"]({min_lat},{min_lon},{max_lat},{max_lon});
    );
    (._; >;);
    out body;
    """

    # Lista de servidores 
    servidores = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]

    headers = {
        "User-Agent": "TranSytemTwins/1.0 (github.com/DanielMtz)",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    for intento in range(1, intentos_max + 1):
        # Alterna servidor en cada intento si hay problemas
        url_api = servidores[(intento - 1) % len(servidores)]

        try:
            print(
                f" Intento {intento}/{intentos_max} conectando a {url_api}..."
            )

            response = requests.post(
                url_api,
                data={"data": query.strip()},
                timeout=100,
                headers=headers,
            )

            if response.status_code == 200:
                return response.text
            elif response.status_code in (429, 504):
                print(
                    f" Servidor saturado (HTTP {response.status_code}). Esperando antes de reintentar..."
                )
                time.sleep(5 * intento)  
            else:
                print(f" Error devuelto por la API: HTTP {response.status_code}")
                break

        except requests.exceptions.Timeout:
            print(" Timeout de red alcanzado en Python. Reintentando...")
            time.sleep(3)
        except requests.exceptions.RequestException as e:
            print(f" Error de conexión: {e}")
            break

    return None

data = {
    "zones": [
    {
        "id": "b3e33657-6c14-4c60-aeca-0fee5b22ca4a",
        "geoJson": {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
            [
            [-99.182682, 19.448788],
            [-99.18045, 19.456395],
            [-99.175816, 19.471448],
            [-99.188347, 19.469505],
            [-99.190407, 19.460442],
            [-99.182682, 19.448788]
            ]
        ]
        }
    }
}
]
}

zona = data["zones"][0]
polygon = zona["geoJson"]["geometry"]

# Descargar
bbox = calcular_bbox(polygon)
osm_data = descargar_red(bbox)

if osm_data:

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"osm_generados/red_vial_{timestamp}.osm"

    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(osm_data)
    print("¡Descargado!")