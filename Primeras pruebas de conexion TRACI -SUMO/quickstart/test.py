import traci

# 1. Iniciar SUMO y conectar con TraCI 
traci.start(["sumo", "-c", "quicstart.sumocfg"])

paso = 0

#  Bucle principal de la simulación
while paso < 1000:
    traci.simulationStep()  # Avanza un paso en la simulación
    
    # Ejemplo de lógica: obtener la lista de vehículos activos en este paso
    vehiculos = traci.vehicle.getIDList()
    print(f"Paso {paso}: {len(vehiculos)} vehículos en la red.")
    
    paso += 1

# 3. Cerrar la conexión correctamente al terminar
traci.close()
