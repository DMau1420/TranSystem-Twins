import sys
import traci
import requests
from sumo_tools import cargar_herramientas_sumo
from data_generators import (
    generar_rutas_aleatorias,
    crear_sumo_config,
    descargar_red,
    conversor_osm_to_netxml,
    conversor_net_to_geojson,
)
from scenario_builder import construir_red_escenario
from simulation_engine import ejecutar_simulacion
from result_analyzer import procesar_resultados
from utils import carpeta_proyecto, carpeta_escenario

BASE_URL = "http://localhost:8000"  # Ajustar al puerto del backend (Mau)
TIMEOUT_BACKEND = 30  # segundos


def calcular_bbox(polygon):
    """Calcula la bbox desde un polígono GeoJSON.

    Devuelve (sur, oeste, norte, este) = (min_lat, min_lon, max_lat, max_lon),
    que es el orden que espera Overpass.
    """
    coords = polygon["coordinates"][0]  # anillo exterior
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return (min(lats), min(lons), max(lats), max(lons))


def importar_zona(proyecto, herramientas):
    """
    Descarga la red real de OpenStreetMap y genera la red base de SUMO + su
    versión en GeoJSON.

    Devuelve un diccionario con las rutas de los archivos generados, que en
    producción se guardarían en la tabla PROYECTOS.
    """
    netconvert_binary = herramientas["netconvert"]

    print(f"Importando zona para el proyecto '{proyecto['nombre']}'...")

    carpeta = carpeta_proyecto(proyecto["id"])

    polygon = proyecto["geometria"]["geoJson"]["geometry"]
    bbox = calcular_bbox(polygon)
    print(f"  bbox calculado: {bbox}")

    archivo_osm = descargar_red(bbox, carpeta)
    if archivo_osm is None:
        raise Exception("No se pudo descargar la red desde Overpass tras varios intentos")

    archivo_red_base = conversor_osm_to_netxml(netconvert_binary, archivo_osm, carpeta)
    archivo_geojson = conversor_net_to_geojson(archivo_red_base, carpeta)

    print("  Red base importada correctamente.")

    return {
        "osm_file_url": archivo_osm,
        "netxml_base_url": archivo_red_base,
        "geojson_url": archivo_geojson,
    }


def simular_escenario(escenario, red_base, herramientas):
    """
    Se ejecuta CADA VEZ que el usuario da clic en "Simular".

    Toma de referencia la red base ya existente del proyecto y genera los
    archivos propios de este escenario: red modificada (si aplica), rutas de
    demanda, configuración de SUMO, y finalmente corre la simulación y calcula
    los indicadores.
    """
    netconvert_binary = herramientas["netconvert"]
    random_trips = herramientas["random_trips"]
    sumo_binary = herramientas["sumo_gui"]

    print(f"Simulando escenario '{escenario['nombre']}'...")

    # Un escenario = una configuración + su resultado más reciente.
    carpeta_del_escenario = carpeta_escenario(escenario["proyecto_id"], escenario["id"])

    # Genera (o reutiliza, si no hay modificaciones) la red propia del escenario.
    archivo_red_escenario = construir_red_escenario(
        netconvert_binary,
        red_base["netxml_base_url"],
        carpeta_del_escenario,
        modificaciones_edges=escenario.get("modificaciones_edges"),
        modificaciones_semaforos=escenario.get("modificaciones_semaforos"),
    )

    archivo_rutas = generar_rutas_aleatorias(
        random_trips, archivo_red_escenario, escenario["demanda_vehicular"], carpeta_del_escenario
    )
    archivo_config = crear_sumo_config(archivo_red_escenario, archivo_rutas, carpeta_del_escenario)

    duracion = escenario.get("duracion_segundos", 7200)  # TODO: definir esto en el esquema del escenario
    archivo_resultados = ejecutar_simulacion(
        sumo_binary, archivo_config, carpeta_del_escenario, duracion_segundos=duracion
    )
    indicadores = procesar_resultados(archivo_resultados)

    print(f"  Indicadores: {indicadores}")
    return indicadores


def enviar_resultado(escenario_id, indicadores):
    """Entrega los indicadores calculados al backend, ligados al escenario_id.

    Si el backend no responde, no se pierde la simulación: se avisa y se
    devuelve None en lugar de tumbar todo el programa.
    """
    payload = {
        "escenario_id": escenario_id,
        **indicadores,
    }
    try:
        respuesta = requests.post(
            f"{BASE_URL}/resultado-sumo", json=payload, timeout=TIMEOUT_BACKEND
        )
    except requests.RequestException as e:
        print(f"No se pudo enviar el resultado al backend: {e}")
        return None

    print(f"Resultado enviado, status: {respuesta.status_code}")
    if not respuesta.ok:
        print(f"  El backend respondió con error: {respuesta.text}")
    return respuesta


def cerrar_traci():
    """Cierra la conexión con SUMO si había una abierta."""
    try:
        traci.close()
    except Exception:
        pass


def main():
    try:
        print("Configurando SUMO...")
        herramientas = cargar_herramientas_sumo()

        # --- Datos para pruebas ---
        proyecto = {
            "id": 3,
            "nombre": "Interseccion Av. Insurgentes",
            "geometria": {
                "id": "b3e33657-6c14-4c60-aeca-0fee5b22ca4a",
                "geoJson": {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [-99.182682, 19.448788],
                            [-99.18045, 19.456395],
                            [-99.175816, 19.471448],
                            [-99.188347, 19.469505],
                            [-99.190407, 19.460442],
                            [-99.182682, 19.448788],
                        ]]
                    },
                },
            },
            # Estos tres campos, en producción, vendrían ya llenos si el
            # proyecto ya había importado su zona antes. Aquí se dejan en
            # None a propósito para forzar la primera importación.
            "osm_file_url": None,
            "netxml_base_url": None,
            "geojson_url": None,
        }

        escenario = {
            "id": 12,
            "proyecto_id": proyecto["id"],
            "nombre": "Situacion actual",
            "modificaciones_edges": [],      # ej: [{"edge_id": "128255275", "carriles": 4, "velocidad_max": 80}]
            "modificaciones_semaforos": [],  # ej: [{"tls_id": "61422324", "fases": [...]}]
            "demanda_vehicular": 100,        # TODO: pasar a "vehiculos_por_hora" explícito
            "duracion_segundos": 3600,       # ej: 1 hora de simulación (7:00-8:00)
        }

        # --- Paso 1: importar la zona SOLO si el proyecto aún no la tiene ---
        if proyecto.get("netxml_base_url") is None:
            red_base = importar_zona(proyecto, herramientas)
            # En producción: aquí se haría un PATCH/POST al backend para
            # guardar red_base en la tabla PROYECTOS, para no volver a
            # descargar la próxima vez que se simule un escenario de este
            # mismo proyecto.
        else:
            print("La zona de este proyecto ya estaba importada, se reutiliza.")
            red_base = {
                "osm_file_url": proyecto.get("osm_file_url"),
                "netxml_base_url": proyecto["netxml_base_url"],
                "geojson_url": proyecto.get("geojson_url"),
            }

        # --- Paso 2: simular el escenario ---
        indicadores = simular_escenario(escenario, red_base, herramientas)

        # --- Paso 3: entregar resultados ligados al escenario, no al proyecto ---
        enviar_resultado(escenario["id"], indicadores)

        return 0

    except KeyboardInterrupt:
        print("\nSimulación interrumpida por el usuario")
        cerrar_traci()
        return 1

    except Exception as e:
        print(f"Error fatal: {e}")
        cerrar_traci()
        return 1


if __name__ == "__main__":
    sys.exit(main())