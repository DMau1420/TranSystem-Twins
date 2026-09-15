import sys
import os
import traci
from sumo_tools import cargar_herramientas_sumo
from data_generators import generar_rutas_aleatorias
from data_generators import crear_sumo_config
from data_generators import cargar_escenario
from data_generators import descargar_red
from data_generators import conversor_osm_to_netxml
from data_generators import conversor_net_to_geojson
from scenario_builder import construir_red_escenario
from simulation_engine import ejecutar_simulacion
from result_analyzer import procesar_resultados
from pathlib import Path
import requests


def calcular_bbox(polygon):
    """Calcular la bbox desde un polígono GeoJSON."""
    coords = polygon["coordinates"][0]  # anillo exterior
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return (min(lats), min(lons), max(lats), max(lons))


def importar_zona(proyecto, herramientas):
    """
    Se ejecuta UNA sola vez por proyecto: descarga la red real de OpenStreetMap
    y genera la red base de SUMO + su versión en GeoJSON.

    Devuelve un diccionario con las rutas de los archivos generados, que en
    producción se guardarían en la tabla PROYECTOS (no en escenarios).
    """
    netconvertBinary = herramientas["netconvert"]

    print(f"Importando zona para el proyecto '{proyecto['nombre']}'...")

    polygon = proyecto["geometria"]["geoJson"]["geometry"]
    bbox = calcular_bbox(polygon)
    print(f"  bbox calculado: {bbox}")

    archivo_osm = descargar_red(bbox)
    if archivo_osm is None:
        raise Exception("No se pudo descargar la red desde Overpass tras varios intentos")

    archivo_red_base = conversor_osm_to_netxml(netconvertBinary, archivo_osm)
    archivo_geojson = conversor_net_to_geojson(archivo_red_base)

    print("  Red base importada correctamente.")

    return {
        "osm_file_url": archivo_osm,
        "netxml_base_url": archivo_red_base,
        "geojson_url": archivo_geojson,
    }


def simular_escenario(escenario, red_base, herramientas):
    """
    Se ejecuta CADA VEZ que el usuario da clic en "Simular". Parte de la red
    base ya existente del proyecto (nunca se toca ni se vuelve a descargar) y
    genera los archivos propios de este escenario: red modificada (si aplica),
    rutas de demanda, configuración de SUMO, y finalmente corre la simulación
    y calcula los indicadores.
    """
    netconvertBinary = herramientas["netconvert"]
    random_trips = herramientas["random_trips"]
    sumoBinary = herramientas["sumo"]

    print(f"Simulando escenario '{escenario['nombre']}'...")

    carpeta_escenario = f"storage/proyectos/{escenario['proyecto_id']}/escenarios/{escenario['id']}"

    # Genera (o reutiliza, si no hay modificaciones) la red propia del escenario.
    # Nunca toca red_base["netxml_base_url"] -- eso es de solo lectura aquí.
    archivo_red_escenario = construir_red_escenario(
        netconvertBinary,
        red_base["netxml_base_url"],
        carpeta_escenario,
        modificaciones_edges=escenario.get("modificaciones_edges"),
        modificaciones_semaforos=escenario.get("modificaciones_semaforos"),
    )

    archivo_rutas = generar_rutas_aleatorias(
        random_trips, archivo_red_escenario, escenario["demanda_vehicular"]
    )
    archivo_config = crear_sumo_config(archivo_red_escenario, archivo_rutas)

    duracion = escenario.get("duracion_segundos", 7200)  # TODO: definir esto en el esquema del escenario
    archivo_resultados = ejecutar_simulacion(sumoBinary, archivo_config, duracion_segundos=duracion)
    indicadores = procesar_resultados(archivo_resultados)

    print(f"  Indicadores: {indicadores}")
    return indicadores


def enviar_resultado(escenario_id, indicadores):
    """Entrega los indicadores calculados al backend, ligados al escenario_id"""

    payload = {
        "escenario_id": escenario_id,
        **indicadores,
    }
    base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    if not base_url.startswith("http"):
        base_url = f"http://{base_url}"
    respuesta = requests.post(f"{base_url}/resultado-sumo", json=payload)
    print(f"Resultado enviado, status: {respuesta.status_code}")
    return respuesta


def main():
    try:
        print("Configurando SUMO...")
        herramientas = cargar_herramientas_sumo()

        # --- Datos ficticios para pruebas  ---
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
            # Estos dos campos, en producción, vendrían ya llenos si el
            # proyecto ya había importado su zona antes. Aquí se dejan en
            # None a propósito para forzar la primera importación.
            "netxml_base_url": None,
            "geojson_url": None,
        }

        escenario = {
            "id": 12,
            "proyecto_id": proyecto["id"],
            "nombre": "Situacion actual",
            "modificaciones_edges": [],          # ej: [{"edge_id": "128255275", "carriles": 4, "velocidad_max": 80}]
            "modificaciones_semaforos": [],       # ej: [{"tls_id": "61422324", "fases": [...]}]
            "demanda_vehicular": 100,             # TODO: pasar a "vehiculos_por_hora" explícito
            "duracion_segundos": 3600,            # ej: 1 hora de simulación (7:00-8:00)
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
                "osm_file_url": proyecto["osm_file_url"],
                "netxml_base_url": proyecto["netxml_base_url"],
                "geojson_url": proyecto["geojson_url"],
            }

        # --- Paso 2: simular el escenario (esto sí se repite cada vez) ---
        indicadores = simular_escenario(escenario, red_base, herramientas)

        # --- Paso 3: entregar resultados ligados al escenario, no al proyecto ---
        enviar_resultado(escenario["id"], indicadores)

    except KeyboardInterrupt:
        print("\nSimulación interrumpida por el usuario")
        try:
            traci.close()
        except Exception:
            pass
        return 1

    except Exception as e:
        print(f"Error fatal: {e}")
        try:
            traci.close()
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())