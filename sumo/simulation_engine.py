"""
simulation_engine.py: corre UNA simulación de SUMO por TraCI y mide cosas
que solo existen mientras la conexión está viva (retraso por semáforo y
trayectorias de los vehículos).

Archivos que escribe en la carpeta del escenario:
    tripinfo.xml            salida cruda de SUMO (un registro por viaje)
    queue.xml               salida cruda de SUMO (longitud de filas)
    resumen_ejecucion.json  diagnóstico: cómo corrió la simulación
    trayectorias.json       "grabación" para la animación del frontend

El retraso por semáforo NO se guarda aquí: se devuelve a quien llama
(main.py) para que lo integre en indicadores.json.
"""
import json
import uuid
from pathlib import Path

import traci
import traci.constants as tc

from sumo_tools import verificar_archivo_salida


# Variables que se piden a SUMO por cada vehículo (suscripción de TraCI)
VARIABLES_VEHICULO = [tc.VAR_LANE_ID, tc.VAR_LANEPOSITION, tc.VAR_SPEED,
                      tc.VAR_POSITION, tc.VAR_TYPE]


# ---------------------------------------------------------------------------
# Retraso por semáforo
# ---------------------------------------------------------------------------

MAX_CALLES_NOMBRE = 3     # cuántas calles distintas se nombran por semáforo


def _nombre_calle(conn, lane):
    """Nombre de la calle de un carril ("" si la red no trae nombres o la calle no tiene)."""
    try:
        return conn.edge.getStreetName(conn.lane.getEdgeID(lane)).strip()
    except Exception:
        return ""


def _preparar_semaforos(conn):
    """
    Regresa dos diccionarios:
      carriles: {carril: {"longitud", "vmax", "tls": [ids]}} con los carriles de
                entrada de cada semáforo que SÍ existe en la red (los que
                netconvert no construyó no aparecen).
      nombres:  {tls_id: "Calle A / Calle B"} con las calles que llegan al
                semáforo ("" si la red no trae nombres).
    """
    carriles = {}
    nombres = {}
    for tls_id in conn.trafficlight.getIDList():
        calles = set()
        for lane in set(conn.trafficlight.getControlledLanes(tls_id)):
            if lane not in carriles:
                carriles[lane] = {
                    "longitud": conn.lane.getLength(lane),
                    "vmax": conn.lane.getMaxSpeed(lane),
                    "tls": [],
                }
            carriles[lane]["tls"].append(tls_id)

            nombre = _nombre_calle(conn, lane)
            if nombre:
                calles.add(nombre)
        nombres[tls_id] = " / ".join(sorted(calles)[:MAX_CALLES_NOMBRE])
    return carriles, nombres


def _medir_retraso(conn, carriles, acumulado, dt, zona_m):
    """
    Por cada vehículo suscrito que esté en la zona de aproximación (últimos
    zona_m metros antes de la línea de alto) de un semáforo, acumula el
    tiempo perdido del paso: dt * (1 - velocidad / velocidad permitida).
    """
    for vid, r in conn.vehicle.getAllSubscriptionResults().items():
        info = carriles.get(r[tc.VAR_LANE_ID])
        if info is None or info["vmax"] <= 0:
            continue
        if info["longitud"] - r[tc.VAR_LANEPOSITION] > zona_m:
            continue
        perdida = dt * max(0.0, 1.0 - r[tc.VAR_SPEED] / info["vmax"])
        for tls_id in info["tls"]:
            d = acumulado[tls_id]
            d["retraso_s"] += perdida
            d["vehiculos"].add(vid)


def _resumir_semaforos(acumulado, nombres):
    """Convierte lo acumulado en {tls_id: {nombre, vehiculos, retraso_total_s, retraso_promedio_s}}."""
    resumen = {}
    for tls_id, d in acumulado.items():
        n = len(d["vehiculos"])
        if n > 0:
            resumen[tls_id] = {
                "nombre": nombres.get(tls_id, ""),
                "vehiculos": n,
                "retraso_total_s": round(d["retraso_s"], 2),
                "retraso_promedio_s": round(d["retraso_s"] / n, 2),
            }
    return resumen


# ---------------------------------------------------------------------------
# Trayectorias (para la animación)
# ---------------------------------------------------------------------------

def _muestrear_trayectorias(conn, t_sim, trayectorias, bbox):
    """
    Agrega un punto [lon, lat, velocidad] por cada vehículo en la red y
    actualiza la bbox. Modifica `trayectorias` y `bbox` directamente.
    """
    for vid, r in conn.vehicle.getAllSubscriptionResults().items():
        x, y = r[tc.VAR_POSITION]
        lon, lat = conn.simulation.convertGeo(x, y)      # regresa (lon, lat)

        bbox[0] = min(bbox[0], lat)     # s
        bbox[1] = min(bbox[1], lon)     # w
        bbox[2] = max(bbox[2], lat)     # n
        bbox[3] = max(bbox[3], lon)     # e

        tr = trayectorias.get(vid)
        if tr is None:
            es_camion = 1 if r[tc.VAR_TYPE] == "camion" else 0
            tr = trayectorias[vid] = [t_sim, es_camion, []]
        tr[2].append([round(lon, 5), round(lat, 5), round(r[tc.VAR_SPEED], 1)])


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _construir_comando(sumo_binary, config_file, ruta_resultados, ruta_queue,
                       gui, retraso_gui_ms, semilla):
    comando = [
        str(sumo_binary),
        "-c", str(config_file),
        "--tripinfo-output", str(ruta_resultados),
        "--queue-output", str(ruta_queue),
        "--no-step-log",
    ]
    if gui:
        comando += [
            "--start",                          # arranca sin tener que dar clic en "Play"
            "--quit-on-end",                    # cierra la ventana al terminar
            "--delay", str(retraso_gui_ms),     # ms entre pasos; 0 = lo más rápido posible
        ]
    if semilla is not None:
        comando += ["--seed", str(semilla)]
    return comando


def _escribir_json(ruta, datos, compacto=False):
    if compacto:
        texto = json.dumps(datos, separators=(",", ":"))
    else:
        texto = json.dumps(datos, indent=2)
    Path(ruta).write_text(texto, encoding="utf-8")


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def ejecutar_simulacion(sumo_binary, config_file, carpeta_salida, archivo_resultados="tripinfo.xml",
                        duracion_segundos=3600, tiempo_drenaje=3600, semilla=None, etiqueta=None,
                        gui=None, retraso_gui_ms=0, zona_aproximacion_m=100, paso_trayectoria=2):
    """
    Ejecuta la simulación de un escenario.

    - duracion_segundos: ventana de demanda (los vehículos entran en este lapso).
    - tiempo_drenaje: tiempo extra para que los últimos vehículos terminen su
        viaje. La simulación se detiene al llegar a duracion_segundos +
        tiempo_drenaje, o antes si ya no queda ningún vehículo por terminar.
    - semilla: si se da, sobrescribe la del .sumocfg (para repeticiones).
    - etiqueta: nombre único de la conexión TraCI. Permite correr varias
        simulaciones a la vez sin que se pisen. Si no se da, se genera una.
    - gui: True/False. Si es None, se detecta por el nombre del binario
        (sumo-gui). En modo GUI la simulación arranca sola y la ventana se
        cierra al terminar.
    - retraso_gui_ms: milisegundos entre pasos en modo GUI (0 = máxima velocidad).

    Regresa un dict, o None si algo falló:
        {
          "archivo_resultados": ruta del tripinfo.xml (None si no es válido),
          "semaforos": {tls_id: {vehiculos, retraso_total_s, retraso_promedio_s}},
        }
    El diagnóstico de la corrida NO se regresa: queda en resumen_ejecucion.json
    y calcular_indicadores lo lee de ahí (una sola fuente).
    """
    carpeta_salida = Path(carpeta_salida)
    ruta_resultados = carpeta_salida / archivo_resultados
    ruta_queue = carpeta_salida / "queue.xml"
    ruta_resumen = carpeta_salida / "resumen_ejecucion.json"
    ruta_trayectorias = carpeta_salida / "trayectorias.json"

    tiempo_maximo = duracion_segundos + tiempo_drenaje
    etiqueta = etiqueta or f"sim_{uuid.uuid4().hex[:8]}"

    if gui is None:
        gui = "gui" in Path(str(sumo_binary)).name.lower()

    comando = _construir_comando(sumo_binary, config_file, ruta_resultados, ruta_queue,
                                 gui, retraso_gui_ms, semilla)

    try:
        traci.start(comando, label=etiqueta)
        conn = traci.getConnection(etiqueta)
    except Exception as e:
        print(f"Error al iniciar SUMO: {e}")
        return None

    conexion_abierta = True
    try:
        print(f"Iniciando simulación (ventana de demanda {duracion_segundos} s, "
              f"tope {tiempo_maximo} s, {'GUI' if gui else 'sin GUI'})...")

        # --- Contadores de la corrida ---
        insertados = 0
        completados = 0
        teletransportados = 0
        ultimo_reporte = -1

        # --- Retraso por semáforo ---
        carriles, nombres_semaforos = _preparar_semaforos(conn)
        acumulado = {t: {"retraso_s": 0.0, "vehiculos": set()} for c in carriles.values() for t in c["tls"]}
        dt = conn.simulation.getDeltaT()

        # --- Trayectorias ---
        # Se usa el reloj de SUMO (no un contador de pasos), así el ciclo es
        # correcto aunque el step-length no sea 1 s.
        trayectorias = {}                 # vid -> [t0, es_camion, [[lon, lat, v], ...]]   (vid -> vehicle_id)
        proximo_muestreo = 0.0
        bbox = [float("inf"), float("inf"), float("-inf"), float("-inf")]   # s, w, n, e
        t_max_traj = 0.0

        # --- Ciclo principal ---
        while conn.simulation.getMinExpectedNumber() > 0 and conn.simulation.getTime() < tiempo_maximo:
            conn.simulationStep()
            t_sim = conn.simulation.getTime()

            insertados += conn.simulation.getDepartedNumber()
            completados += conn.simulation.getArrivedNumber()
            teletransportados += conn.simulation.getStartingTeleportNumber()

            for vid in conn.simulation.getDepartedIDList():
                conn.vehicle.subscribe(vid, VARIABLES_VEHICULO)

            _medir_retraso(conn, carriles, acumulado, dt, zona_aproximacion_m)

            if t_sim + 1e-6 >= proximo_muestreo:
                proximo_muestreo = (int(t_sim // paso_trayectoria) + 1) * paso_trayectoria
                t_max_traj = t_sim
                _muestrear_trayectorias(conn, t_sim, trayectorias, bbox)

            t = int(t_sim)
            if t % 100 == 0 and t != ultimo_reporte:
                ultimo_reporte = t
                print(f"  t={t} s - Vehículos en la red: {conn.vehicle.getIDCount()}")

        # Se lee el estado ANTES de cerrar la conexión
        pendientes = conn.simulation.getMinExpectedNumber()
        en_red = conn.vehicle.getIDCount()
        tiempo_final = conn.simulation.getTime()

        conn.close()
        conexion_abierta = False

        # --- Armar resultados ---
        semaforos = _resumir_semaforos(acumulado, nombres_semaforos)

        resumen = {
            "vehiculos_insertados": insertados,
            "vehiculos_completados": completados,
            "vehiculos_teletransportados": teletransportados,
            "vehiculos_en_red_al_final": en_red,
            "vehiculos_pendientes": pendientes,   # incluye los que ni siquiera alcanzaron a entrar
            "termino_completo": pendientes == 0,
            "zona_aproximacion_m": zona_aproximacion_m,
            "tiempo_final_s": tiempo_final,
            "tiempo_maximo_s": tiempo_maximo,
        }
        _escribir_json(ruta_resumen, resumen)

        if trayectorias:
            _escribir_json(ruta_trayectorias, {
                "t_max": t_max_traj,
                "paso": paso_trayectoria,
                "bbox": bbox,
                "veh": list(trayectorias.values()),
            }, compacto=True)

        _imprimir_resumen(resumen, semaforos)

        return {
            "archivo_resultados": verificar_archivo_salida(ruta_resultados) or None,
            "semaforos": semaforos,
        }

    except Exception as e:
        print(f"Error durante la simulación: {e}")
        return None

    finally:
        if conexion_abierta:
            try:
                conn.close()
            except Exception:
                pass


def _imprimir_resumen(resumen, semaforos):
    """
    Cierre de la corrida + top de semáforos. Los conteos de vehículos y los
    avisos (truncada, teletransportes) los imprime calcular_indicadores.
    """
    print(f"Simulación terminada en t={resumen['tiempo_final_s']:.0f} s.")
    print(f"  Semáforos con tráfico: {len(semaforos)}")
    for tls_id, s in sorted(semaforos.items(), key=lambda x: -x[1]["vehiculos"])[:10]:
        etiqueta = f"{s['nombre']} ({tls_id})" if s.get("nombre") else tls_id
        print(f"    {etiqueta}: {s['vehiculos']} veh | retraso prom. {s['retraso_promedio_s']} s")