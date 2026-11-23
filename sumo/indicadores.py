import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


# PARA EL NIVEL DE SERVICIO

_LOS = [(10, "A"), (20, "B"), (35, "C"), (55, "D"), (80, "E")]  # s/veh (HCM, semaforizadas)

def nivel_de_servicio(retraso_s):
    """Letra A-F según el retraso promedio por vehículo (s)."""
    if retraso_s is None:
        return None
    for limite, letra in _LOS:
        if retraso_s <= limite:
            return letra
    return "F"


def _leer_resumen_ejecucion(carpeta):
    """
    Lee resumen_ejecucion.json (lo escribe simulation_engine.py).
    Regresa un dict vacío si no existe o no se puede leer, para que el
    análisis siga funcionando con corridas hechas antes de este cambio.
    """
    ruta = Path(carpeta) / "resumen_ejecucion.json"
    if not ruta.exists():
        print(f" No se encontró {ruta.name}; no se puede verificar si la simulación terminó completa.")
        return {}
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f" No se pudo leer {ruta.name}: {e}")
        return {}


def calcular_indicadores(archivo):
    """
    Calcula los indicadores de un escenario a partir de tripinfo.xml,
    queue.xml y resumen_ejecucion.json (los tres en la misma carpeta).

    Recibe la ruta de tripinfo.xml (None si la simulación falló).
    Regresa un diccionario de indicadores, o None si no hay resultados.

    Claves que lee el frontend (no cambiar sus nombres):
        - tiempo_promedio_espera
        - velocidad_promedio
        - longitud_max_fila
        - vehiculos_atendidos
    """
    
    if archivo is None:
        print("ERROR: no hay archivo de resultados; la simulación no produjo tripinfo.xml.")
        return None

    archivo = Path(archivo)
    try:
        vehiculos = ET.parse(archivo).getroot().findall("tripinfo")
    except ET.ParseError as e:
        print(f"ERROR: No se pudo parsear {archivo.name}: {e}")
        return None
    except FileNotFoundError:
        print(f"ERROR: no existe {archivo}")
        return None

    if not vehiculos:
        print("No se encontraron vehículos en la simulación")
        return None

    duraciones, espera, retrasos, velocidades = [], [], [], []
    demoras_entrada = []
    por_tipo = Counter()

    for v in vehiculos:
        duracion = float(v.attrib["duration"])
        duraciones.append(duracion)
        espera.append(float(v.attrib["waitingTime"]))
        retrasos.append(float(v.attrib.get("timeLoss", 0)))
        por_tipo[v.attrib.get("vType", "desconocido")] += 1

        # Cola FUERA de la red: tiempo entre la salida planeada y la inserción
        # real. SUMO usa -1 cuando no aplica, esos casos se descartan.
        demora = float(v.attrib.get("departDelay", 0))
        if demora >= 0:
            demoras_entrada.append(demora)

        # Velocidad media del viaje (m/s). Si duration fuera 0 se descarta
        # para no dividir entre cero.
        largo_ruta = float(v.attrib.get("routeLength", 0))
        if duracion > 0:
            velocidades.append(largo_ruta / duracion)

    n = len(vehiculos)
    tiempo_recorrido = sum(duraciones) / n
    tiempo_espera = sum(espera) / n
    retraso_promedio = sum(retrasos) / n
    # Espera para entrar a la red + espera dentro de ella
    retraso_entrada = sum(demoras_entrada) / len(demoras_entrada) if demoras_entrada else 0.0
    espera_total = tiempo_espera + retraso_entrada
    # Promedio simple entre vehículos (no ponderado por distancia), en km/h
    velocidad = (sum(velocidades) / len(velocidades)) * 3.6 if velocidades else None

    longitud_max_fila = _calcular_longitud_max_fila(archivo.parent / "queue.xml")
    resumen = _leer_resumen_ejecucion(archivo.parent)

    termino_completo = resumen.get("termino_completo")  # None si no hay resumen
    insertados = resumen.get("vehiculos_insertados")
    teletransportados = resumen.get("vehiculos_teletransportados")

    print("\n" + "=" * 50)
    print(" ESTADISTICAS DEL ESCENARIO")
    print("=" * 50)
    if insertados is not None:
        print(f"Vehículos insertados: {insertados} | completados: {n}")
    else:
        print(f"Vehículos completados: {n}")
    print(f"Composición: {dict(por_tipo)}")
    print(f"Tiempo promedio de recorrido: {tiempo_recorrido:.2f} s")
    print(f"Espera promedio (dentro de la red): {tiempo_espera:.2f} s")
    print(f"Espera para entrar a la red: {retraso_entrada:.2f} s | espera total: {espera_total:.2f} s")
    print(f"Tiempo perdido promedio (timeLoss, toda la red): {retraso_promedio:.2f} s")
    if velocidad is not None:
        print(f"Velocidad promedio: {velocidad:.2f} km/h")
    if longitud_max_fila is not None:
        print(f"Longitud máxima de fila: {longitud_max_fila:.2f} m")
    if termino_completo is False:
        print("AVISO: la simulación NO terminó completa; hay vehículos que no entran en estos promedios.")
    if teletransportados:
        print(f"AVISO: {teletransportados} vehículo(s) teletransportado(s) por atasco.")

    return {
        # --- Claves que lee el frontend ---
        "vehiculos_atendidos": n,
        "tiempo_promedio_espera": round(tiempo_espera, 2),
        "velocidad_promedio": round(velocidad, 2) if velocidad is not None else None,
        "longitud_max_fila": round(longitud_max_fila, 2) if longitud_max_fila is not None else None,
        # --- Adicionales ---
        "tiempo_promedio_recorrido": round(tiempo_recorrido, 2),
        "tiempo_perdido_promedio": round(retraso_promedio, 2),
        "retraso_entrada_promedio": round(retraso_entrada, 2),
        "espera_total_promedio": round(espera_total, 2),
        "vehiculos_insertados": insertados,
        "vehiculos_teletransportados": teletransportados,
        "termino_completo": termino_completo,
        "vehiculos_por_tipo": dict(por_tipo),
        "nivel_de_servicio": nivel_de_servicio(retraso_promedio),
    }


def _calcular_longitud_max_fila(ruta_queue):
    """
    Lee el queue.xml que genera SUMO con --queue-output y regresa la
    longitud de fila más larga (m) observada en CUALQUIER carril y en
    CUALQUIER instante de la simulación.

    Se usa "queueing_length" (hasta el último vehículo realmente detenido)
    y no "queueing_length_experimental", que SUMO marca como experimental.

    - Archivo inexistente o ilegible -> None (no se pudo medir; no se
      reporta un 0 falso).
    - Archivo válido sin ninguna fila -> 0.0 (sí se midió: no hubo colas).

    Se lee con iterparse y se libera cada elemento procesado, porque este
    archivo escribe todos los carriles en cada paso y puede pesar cientos
    de MB en simulaciones largas.
    """
    ruta_queue = Path(ruta_queue)
    if not ruta_queue.exists():
        print(f" No se encontró queue.xml en {ruta_queue}; no se pudo calcular longitud_max_fila.")
        return None

    longitud_maxima = 0.0
    try:
        for _, elem in ET.iterparse(ruta_queue, events=("end",)):
            if elem.tag == "lane":
                longitud = float(elem.get("queueing_length", 0))
                if longitud > longitud_maxima:
                    longitud_maxima = longitud
            elem.clear()
    except ET.ParseError as e:
        print(f" No se pudo parsear queue.xml: {e}")
        return None

    return longitud_maxima