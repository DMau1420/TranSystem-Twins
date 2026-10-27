import traci
from sumo_tools import verificar_archivo_salida


def ejecutar_simulacion(sumo_binary, config_file, carpeta_salida, archivo_resultados="tripinfo.xml", duracion_segundos=7200, on_progress=None):
    """
    Ejecuta la simulación de un escenario ya construido (red + rutas + config
    ya generados por construir_red_escenario y generar_rutas_aleatorias).
    """
    ruta_resultados = carpeta_salida / archivo_resultados
    ruta_queue = carpeta_salida / "queue.xml"
    try:
        traci.start([
            sumo_binary,
            "-c", config_file,
            "--tripinfo-output", ruta_resultados,
            "--start",
            "--quit-on-end",
            "--no-step-log",
            "--queue-output", ruta_queue,
        ])
    except Exception as e:
        print(f"Error al iniciar SUMO: {e}")
        return False

    try:
        step = 0
        print(f"Iniciando simulación por hasta {duracion_segundos} pasos...")
        if on_progress:
            on_progress(60, f"Simulación iniciada: 0/{duracion_segundos}s")

        intervalo_reporte = max(10, min(50, duracion_segundos // 40))
        while traci.simulation.getMinExpectedNumber() > 0 and step < duracion_segundos:
            traci.simulationStep()

            if step % intervalo_reporte == 0 or step == 1:
                veh_count = traci.vehicle.getIDCount()
                print(f"  Paso {step} - Vehículos activos: {veh_count}")
                if on_progress:
                    pct = min(94, int(60 + (step / max(1, duracion_segundos)) * 34))
                    on_progress(pct, f"Paso {step}/{duracion_segundos}s · {veh_count} vehículos activos")

            step += 1

        print(f"Simulación completada en {step} pasos ({step // 60} minutos simulados)")
        if on_progress:
            on_progress(95, f"Simulación completada ({step} pasos). Procesando métricas...")
        traci.close()
        return verificar_archivo_salida(ruta_resultados)

    except Exception as e:
        print(f"Error durante la simulación: {e}")
        try:
            traci.close()
        except Exception:
            pass
        return False

