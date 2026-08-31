import traci
from sumo_tools import verificar_archivo_salida
from utils import generar_ruta_salida


def configurar_semaforo(escenario):
    """
    Configura el semáforo según el escenario proporcionado
    
    Args:
        escenario (dict): Configuración con fases del semáforo
        
    Returns:
        bool: True si se configuró correctamente
    """
    try:
        logica_actual = traci.trafficlight.getAllProgramLogics("0")[0]
        fases = logica_actual.phases

        for i, fase in enumerate(escenario["semaforo"]["fases"]):
            fases[i].duration = fase["duracion"]
            fases[i].state = fase["estado"]

        traci.trafficlight.setProgramLogic("0", logica_actual)
        traci.trafficlight.setPhase("0", 2)
        return True
        
    except Exception as e:
        print(f"Error al configurar semáforo: {e}")
        return False


def controlar_semaforo(step=None):
    """
    Controla la lógica del semáforo basada en detección de vehículos
    """

    # Si el semáforo está en fase 2 (verde para un eje) y hay vehículos esperando
    if traci.trafficlight.getPhase("0") == 2:
        if traci.inductionloop.getLastStepVehicleNumber("0") > 0:
            traci.trafficlight.setPhase("0", 3)  # Cambiar a ámbar
        else:
            traci.trafficlight.setPhase("0", 2)  # Mantener verde si no hay vehículos
    
    # ===== FUTURAS EXTENSIONES =====
    
    #  Ejemplo 1: Cambio a modo nocturno a una hora específica
    # if step and step == 3600:  # después de 1 hora (3600 segundos)
    #     print("Activando modo nocturno")
    #     traci.trafficlight.setProgram("0", "night_mode")
    #     traci.trafficlight.setPhase("0", "blink")
    
    #  Ejemplo 2: Registrar estadísticas cada cierto tiempo
    # if step and step % 500 == 0:
    #     with open("semaforo_log.txt", "a") as log:
    #         log.write(f"Paso {step}: Fase {traci.trafficlight.getPhase('0')}, "
    #                  f"Vehículos esperando: {traci.inductionloop.getLastStepVehicleNumber('0')}\n")
    
    #  Ejemplo 3: Adaptación al tráfico cada cierto intervalo
    # if step and step % 100 == 0 and step > 0:
    #     vehiculos_esperando = traci.inductionloop.getLastStepVehicleNumber("0")
    #     if vehiculos_esperando > 10:  # Si hay muchos vehículos esperando
    #         # Extender el tiempo de verde
    #         pass
    
    #  Ejemplo 4: Cambios según hora del día
    # if step and step == 7200:  # 2 horas (ej. 8:00 AM)
    #     print(" Hora punta mañana - Aumentando flujo")
    #     # Cambiar a programa de hora punta
    # 
    # if step and step == 64800:  # 18:00 (6:00 PM)
    #     print(" Hora punta tarde - Ajustando semáforos")
    #     # Cambiar a programa de hora punta tarde


def ejecutar_simulacion(sumo_binary, config_file, escenario=None, modo="generic", archivo_resultados="tripinfo.xml"):
    
    ruta_resultados = generar_ruta_salida(archivo_resultados)

    try:
        traci.start([
            sumo_binary,
            "-c", config_file,
            "--tripinfo-output", ruta_resultados,
            "--start",
            "--quit-on-end",
            "--no-step-log"
        ])
    except Exception as e:
        print(f"Error al iniciar SUMO: {e}")
        return False
    
    try:
        # CONFIGURAR SEMÁFORO (MODO TUTORIAL de runner.py) 
        if modo == "tutorial" and escenario:
            print(" Modo Tutorial: Configurando semáforo desde escenario...")
            if not configurar_semaforo(escenario):
                return False
        else:
            print(" Modo Genérico: Usando configuración predeterminada")
        
        # BUCLE PRINCIPAL DE SIMULACIÓN 
        # Nota ->  step: Contador de pasos (1 step = 1 segundo simulado)
        step = 0
        max_steps = escenario["simulacion"]["duracion"] * 2 if escenario else 7200  # 2 horas por defecto
        
        print(f" Iniciando simulación por {max_steps} pasos máximos...")
        
        while traci.simulation.getMinExpectedNumber() > 0 and step < max_steps:
            # Avanzar un paso en el tiempo (1 segundo)
            traci.simulationStep()
            
            # Control de semáforos (solo en modo tutorial por ahora)
            if modo == "tutorial" and escenario:
                controlar_semaforo(step)  # Se pasa step para futuras funcionalidades
            
            # Mostrar progreso cada 100 pasos
            if step % 100 == 0:
                print(f"  Paso {step} - Vehículos activos: {traci.vehicle.getIDCount()}")
            
            step += 1
        
        print(f" Simulación completada en {step} pasos ({step//60} minutos simulados)")
        traci.close()
        return verificar_archivo_salida(ruta_resultados)
        
    except Exception as e:
        print(f" Error durante la simulación: {e}")
        try:
            traci.close()
        except:
            pass
        return False