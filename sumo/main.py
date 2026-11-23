"""
main.py: punto de entrada del motor de simulación.

    python main.py                          simula el escenario de prueba y genera su reporte (ficha)
    python main.py --escenario esc.json     igual, pero con un escenario leído de un JSON (como lo mandaría el backend)
    python main.py --reporte 21 22          PDF comparativo de escenarios YA simulados (sin correr SUMO);
                                            el primero es el base
    Opciones: --proyecto 3   --sin-enviar (no manda los resultados al backend)
"""
import argparse
import json
import os
import sys
from pathlib import Path

import requests
import traci


from utils import carpeta_proyecto, carpeta_escenario
from sumo_tools import cargar_herramientas_sumo

from data_generators import crear_sumo_config
from data_generators import descargar_red
from data_generators import conversor_osm_to_netxml
from data_generators import conversor_net_to_geojson

from escenario_demanda import generar_demanda, indicadores_por_flujo
from scenario_builder import construir_red_escenario

from gestion_reportes import generar_reporte, guardar_escenario
from indicadores import calcular_indicadores

from simulation_engine import ejecutar_simulacion



BASE_URL = "http://localhost:8000"

semilla = 40          # semilla por omisión; simular_escenario acepta otra sin tocar esta variable


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
    """

    netconvertBinary = herramientas["netconvert"]

    print(f"Importando zona para el proyecto '{proyecto['nombre']}'...")

    carpeta = carpeta_proyecto(proyecto["id"])

    # Obtencion y calculo de la zona de estudio
    polygon = proyecto["geometria"]["geoJson"]["geometry"]
    bbox = calcular_bbox(polygon)
    archivo_osm = descargar_red(bbox, carpeta)

    if archivo_osm is None:
        raise Exception("No se pudo descargar la red desde Overpass tras varios intentos")

    # Netxml para sumo Geojson para el frontend
    archivo_red_base = conversor_osm_to_netxml(netconvertBinary, archivo_osm, carpeta)
    archivo_geojson = conversor_net_to_geojson(archivo_red_base, carpeta)

    print("  Red base importada correctamente.")

    return {
        "osm_file_url": archivo_osm,
        "netxml_base_url": archivo_red_base,
        "geojson_url": archivo_geojson,
    }


def obtener_red_base(proyecto, herramientas):
    """Reutiliza la red base del proyecto si ya existe; si no, importa la zona (descarga de OpenStreetMap)."""

    if proyecto.get("netxml_base_url"):

        print("La zona de este proyecto ya estaba importada, se reutiliza.")
        return {"osm_file_url": proyecto.get("osm_file_url"), "netxml_base_url": proyecto["netxml_base_url"],
                "geojson_url": proyecto.get("geojson_url")}

    existente = Path(carpeta_proyecto(proyecto["id"])) / "red_base.net.xml"

    if existente.exists():
        print(f"Se reutiliza la red base existente: {existente}")
        return {"osm_file_url": None, "netxml_base_url": existente, "geojson_url": None}

    return importar_zona(proyecto, herramientas)


def armar_indicadores(escenario, salida):
    """
    Une en un solo diccionario todo lo que el reporte y el backend necesitan:
    - KPIs globales (de tripinfo.xml)
    - flujos (si el escenario los define)
    - semaforos: retraso por semáforo (puntos críticos)
    La calidad de la corrida (termino_completo, teletransportados) ya viene
    dentro de los KPIs: calcular_indicadores la lee de resumen_ejecucion.json.
    Regresa None si no se pudieron calcular los KPIs.
    """
    archivo = salida["archivo_resultados"]

    indicadores = calcular_indicadores(archivo)
    if indicadores is None:
        return None

    # Si el escenario tuvo flujos vehiculares especificos
    if escenario.get("flujos"):
        indicadores["flujos"] = indicadores_por_flujo(archivo)

    indicadores["semaforos"] = salida["semaforos"]
    return indicadores


def simular_escenario(escenario, red_base, herramientas, semilla_corrida=None):
    """
    Se ejecuta CADA VEZ que el usuario da clic en "Simular".

    Parte de la red base ya existente del proyecto y genera los archivos propios de este escenario:
    - Red modificada (si aplica),
    - Rutas de demanda
    - Configuración de SUMO,
    - Corre la simulación, calcula los indicadores y los GUARDA en <carpeta del escenario>/indicadores.json
        (de ahí lee el reporte PDF, sin volver a simular).
    Regresa los indicadores, o None si la simulación no produjo resultados.
    """

    netconvertBinary = herramientas["netconvert"]
    sumoBinary = herramientas["sumo_gui"]
    semilla_usada = semilla if semilla_corrida is None else semilla_corrida

    print(f"Simulando escenario '{escenario['nombre']}' (semilla {semilla_usada})...")

    carpeta_del_escenario = carpeta_escenario(escenario["proyecto_id"], escenario["id"])

    archivo_red_escenario = construir_red_escenario(
        netconvertBinary,
        red_base["netxml_base_url"],
        carpeta_del_escenario,
        modificaciones_edges=escenario.get("modificaciones_edges"),
        modificaciones_semaforos=escenario.get("modificaciones_semaforos"),
    )

    archivo_rutas = generar_demanda(escenario, archivo_red_escenario, carpeta_del_escenario, herramientas)

    archivo_config = crear_sumo_config(archivo_red_escenario, archivo_rutas, carpeta_del_escenario)

    duracion = escenario.get("duracion_segundos", 7200)  # TODO: definir esto en el esquema del escenario

    salida = ejecutar_simulacion(sumoBinary, archivo_config, carpeta_del_escenario, duracion_segundos=duracion, semilla=semilla_usada)

    if salida is None or salida["archivo_resultados"] is None:
        print("La simulación no produjo resultados; no se guarda resultado.")
        return None

    indicadores = armar_indicadores(escenario, salida)

    if indicadores is None:
        print("La simulación no produjo indicadores; no se guarda resultado.")
        return None

    guardar_escenario(escenario, indicadores, semilla_usada, carpeta_del_escenario)

    print(f"  Indicadores: {indicadores}")
    return indicadores


def enviar_indicadores(escenario_id, indicadores):
    """Entrega los indicadores calculados al backend, ligados al escenario_id. No truena si el backend no responde."""
    if indicadores is None:
        print("No hay indicadores que enviar.")
        return None
    payload = {"escenario_id": escenario_id, **indicadores}
    base_url = os.getenv("BACKEND_URL", BASE_URL)
    if not base_url.startswith("http"):
        base_url = f"http://{base_url}"
    try:
        respuesta = requests.post(f"{base_url}/resultado-sumo", json=payload, timeout=15)
    except requests.RequestException as e:
        print(f"No se pudo enviar el resultado al backend ({base_url}): {e}")
        return None
    print(f"Resultado enviado, status: {respuesta.status_code}")
    return respuesta


# --- Datos ficticios para pruebas ---
PROYECTO_PRUEBA = {
    "id": 3,
    "nombre": "Interseccion Av. Insurgentes",
    "geometria": {
        "id": "b3e33657-6c14-4c60-aeca-0fee5b22ca4a",
        "geoJson": {
            "type": "Feature", "properties": {},
            "geometry": {"type": "Polygon", "coordinates": [[
                [-99.182682, 19.448788], [-99.18045, 19.456395], [-99.175816, 19.471448],
                [-99.188347, 19.469505], [-99.190407, 19.460442], [-99.182682, 19.448788]]]},
        },
    },
    "netxml_base_url": None,
    "geojson_url": None,
}

ESCENARIO_PRUEBA = {        # el escenario A probado (entrada 8640976#10 del cluster de prueba)
    "id": 21,
    "proyecto_id": 3,
    "nombre": "A: Actual",
    "modificaciones_edges": [],
    "modificaciones_semaforos": [],
    "demanda_vehicular": 800,
    "duracion_segundos": 3600,
    "inicio_s": 0,
    "fin_s": 3600,
    "porcentaje_pesados": 10,
    "flujos": [{"id": "via", "origen": "8640976#9", "destino": "126678383#0",
                "vehiculos_por_hora": 800, "porcentaje_pesados": 10}],
}


def _leer_args(argv):
    ap = argparse.ArgumentParser(description="Motor de simulación del gemelo digital")
    ap.add_argument("--proyecto", type=int, default=PROYECTO_PRUEBA["id"])
    ap.add_argument("--escenario", help="JSON con el escenario a simular (por omisión, el de prueba)")
    ap.add_argument("--reporte", type=int, nargs="+", metavar="ID",
                    help="ids de escenarios ya simulados; el primero es el base")
    ap.add_argument("--sin-enviar", action="store_true", help="no enviar resultados al backend")
    return ap.parse_args(argv)


def main(argv=None):
    args = _leer_args(argv)
    try:
        # --- Solo reporte: no se corre SUMO ---
        if args.reporte:
            ruta = generar_reporte(args.proyecto, args.reporte, zona=PROYECTO_PRUEBA["nombre"])
            print(f"Reporte generado: {ruta}")
            return 0

        print("Configurando SUMO...")
        herramientas = cargar_herramientas_sumo()

        proyecto = PROYECTO_PRUEBA
        escenario = ESCENARIO_PRUEBA
        if args.escenario:
            escenario = json.loads(Path(args.escenario).read_text(encoding="utf-8"))

        # --- Paso 1: red base (importar la zona SOLO si el proyecto aún no la tiene) ---
        red_base = obtener_red_base(proyecto, herramientas)

        # --- Paso 2: simular el escenario (una corrida) ---
        indicadores = simular_escenario(escenario, red_base, herramientas)
        if indicadores is None:
            return 1

        # --- Paso 3: reporte PDF del escenario ---
        ruta = generar_reporte(escenario["proyecto_id"], [escenario["id"]], zona=proyecto["nombre"])
        print(f"Reporte generado: {ruta}")

        # --- Paso 4: entregar resultados ligados al escenario ---
        if not args.sin_enviar:
            enviar_indicadores(escenario["id"], indicadores)
        return 0

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