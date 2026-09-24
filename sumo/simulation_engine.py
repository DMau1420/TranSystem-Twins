import traci
from sumo_tools import verificar_archivo_salida
from utils import generar_ruta_salida


def ejecutar_simulacion(sumo_binary, config_file, archivo_resultados="tripinfo.xml", duracion_segundos=7200):
    """
    Ejecuta la simulación de un escenario ya construido (red + rutas + config
    ya generados por construir_red_escenario y generar_rutas_aleatorias).
    """
    ruta_resultados = generar_ruta_salida(archivo_resultados)

    try:
        traci.start([
            sumo_binary,
            "-c", config_file,
            "--tripinfo-output", ruta_resultados,
            "--start",
            "--quit-on-end",
            "--no-step-log",
        ])
    except Exception as e:
        print(f"Error al iniciar SUMO: {e}")
        return False

    try:
        step = 0
        print(f"Iniciando simulación por hasta {duracion_segundos} pasos...")

        while traci.simulation.getMinExpectedNumber() > 0 and step < duracion_segundos:
            traci.simulationStep()

            if step % 100 == 0:
                print(f"  Paso {step} - Vehículos activos: {traci.vehicle.getIDCount()}")

            step += 1

        print(f"Simulación completada en {step} pasos ({step // 60} minutos simulados)")
        traci.close()
        return verificar_archivo_salida(ruta_resultados)

    except Exception as e:
        print(f"Error durante la simulación: {e}")
        try:
            traci.close()
        except Exception:
            pass
        return False

