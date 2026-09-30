import xml.etree.ElementTree as ET  # Libreria para abrir XML
from pathlib import Path

def procesar_resultados(archivo):
    """
    Procesa los resultados SOLO después de verificar el archivo.
    """

    try:
        tree = ET.parse(archivo)
        root = tree.getroot()

        print("\n" + "=" * 50)
        print(" ESTADISTICAS DEL ESCENARIO")
        print("=" * 50)

        vehiculos = root.findall("tripinfo")

        if len(vehiculos) == 0:
            print("No se encontraron vehículos en la simulación")
            return None

        duraciones = []
        espera = []
        velocidades = []  # m/s, una por vehículo: routeLength / duration

        for v in vehiculos:
            duracion = float(v.attrib["duration"])
            duraciones.append(duracion)
            espera.append(float(v.attrib["waitingTime"]))

            # routeLength viene en metros; si algún tripinfo llegara con
            # duration=0 (no debería pasar, pero por seguridad) se descarta
            # para no dividir entre cero.
            largo_ruta = float(v.attrib.get("routeLength", 0))
            if duracion > 0:
                velocidades.append(largo_ruta / duracion)

        tiempo_promedio_recorrido = sum(duraciones) / len(duraciones)
        tiempo_promedio_espera = sum(espera) / len(espera)

        # m/s -> km/h
        velocidad_promedio = (
            (sum(velocidades) / len(velocidades)) * 3.6 if velocidades else None
        )

        # queue.xml vive junto a tripinfo.xml en la misma carpeta del
        longitud_max_fila = _calcular_longitud_max_fila(Path(archivo).parent / "queue.xml")

        print(f"Vehículos simulados: {len(vehiculos)}")
        print(f"Tiempo promedio de recorrido: {tiempo_promedio_recorrido:.2f} segundos")
        print(f"Espera promedio: {tiempo_promedio_espera:.2f} segundos")
        if velocidad_promedio is not None:
            print(f"Velocidad promedio: {velocidad_promedio:.2f} km/h")
        print("=" * 50 + "\n")

        return {
            "vehiculos_atendidos": len(vehiculos),
            "tiempo_promedio_espera": round(tiempo_promedio_espera, 2),
            "velocidad_promedio": round(velocidad_promedio, 2) if velocidad_promedio is not None else None,
            # TODO: "longitud máxima de fila" (cola de vehículos detenidos)
            # NO se puede calcular a partir de tripinfo.xml -- ese archivo
            # solo tiene datos agregados por viaje YA TERMINADO, no el
            # estado de la simulación en el tiempo. Para calcular esto de
            # verdad hace falta que simulation_engine.py corra SUMO con
            # --queue-output (o detectores E2 de ocupación) y que aquí se
            # parsee ese archivo aparte para sacar el máximo histórico.
            # Por ahora se regresa None explícitamente -- el frontend ya
            # maneja ese caso mostrando "-".
            "longitud_max_fila": round(longitud_max_fila, 2) if longitud_max_fila is not None else None,
            # Se conserva por si algo más del sistema todavía lo usa,
            # aunque el frontend actual no lo lee.
            "tiempo_promedio_recorrido": round(tiempo_promedio_recorrido, 2),
        }

    except ET.ParseError as e:
        print(f"ERROR: No se pudo parsear tripinfo.xml: {e}")
        return None
    except Exception as e:
        print(f"ERROR inesperado: {e}")
        return None



def _calcular_longitud_max_fila(ruta_queue):
    """
    Lee el queue.xml que genera SUMO con --queue-output y regresa la
    longitud de fila más larga observada en CUALQUIER carril, en
    CUALQUIER momento de la simulación.

    Formato real del archivo (confirmado en la documentación oficial de
    SUMO, Simulation/Output/QueueOutput):
        <queue-export>
        <data timestep="120.00">
            <lanes>
            <lane id="..." queueing_time="8.0" queueing_length="35.2"
                    queueing_length_experimental="41.0"/>
            ...
            </lanes>
        </data>
        ...
        </queue-export>

    Se usa "queueing_length" (metros, medida desde el final del carril
    hasta el último vehículo REALMENTE detenido) y NO
    "queueing_length_experimental" -- esta segunda es más permisiva
    (incluye vehículos que van a menos de 5 km/h, no solo los parados) y
    el propio SUMO la marca como experimental. Para un indicador de
    reporte técnico conviene la métrica estable, no la experimental.

    Distingue dos casos que NO son lo mismo:
    - El archivo no existe (algo falló al generarlo) -> None: no se
        pudo medir, no se debe reportar un 0 falso.
    - El archivo existe pero nunca se formó ninguna fila (tráfico
        fluido, sin congestión) -> 0.0: SÍ se midió, y el resultado real
        es que no hubo colas.
    """
    ruta_queue = Path(ruta_queue)
    if not ruta_queue.exists():
        print(f" No se encontró queue.xml en {ruta_queue} -- no se pudo calcular longitud_max_fila.")
        return None

    try:
        tree = ET.parse(ruta_queue)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f" No se pudo parsear queue.xml: {e}")
        return None

    longitud_maxima = 0.0
    for lane_el in root.iter("lane"):
        longitud = float(lane_el.get("queueing_length", 0))
        if longitud > longitud_maxima:
            longitud_maxima = longitud

    return longitud_maxima