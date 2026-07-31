from sumolib import checkBinary  
import traci  
import json
import os
import sys
import optparse
import random

# Libreria para abrir XML
import xml.etree.ElementTree as ET

def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option("--nogui", action="store_true",
        default=False, help="run the commandline version of sumo")
    options, args = optParser.parse_args()
    return options

def cargar_sumo():

    # Existe SUMO en el entorno
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        sys.exit("please declare environment variable 'SUMO_HOME'")

    # Opciones de ejecucion disponibles GUI o Terminal
    options = get_options()


    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    return sumoBinary

def cargar_escenario():
    with open('test.json', 'r', encoding='utf-8') as archivo:
        data = json.load(archivo)
    return  data


def generar_rutas(escenario):

    # La semilla nos ayuda a que siempre sean los mismos numeros aleatorios
    # y de esta manera los resultados sean reproducibles
    random.seed(escenario["simulacion"]["seed"]) 
    N =  escenario["simulacion"]["duracion"]

    # demand per second from different directions
    pWE = escenario["demanda"]["we"] #Probability West → East (probabilidad de que aparezca un vehículo de oeste a este).
    pEW = escenario["demanda"]["ew"] # Probability East → West.
    pNS = escenario["demanda"]["ns"] # Probability North → South.

    # Crear el archivo de rutas
    with open("data/cross.rou.xml", "w") as routes:
        print("""<routes>
        <vType id="typeWE" accel="0.8" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="16.67" \
guiShape="passenger"/>
        <vType id="typeNS" accel="0.8" decel="4.5" sigma="0.5" length="7" minGap="3" maxSpeed="25" guiShape="bus"/>

        <route id="right" edges="51o 1i 2o 52i" />
        <route id="left" edges="52o 2i 1o 51i" />
        <route id="down" edges="54o 4i 3o 53i" />""", file=routes)
        vehNr = 0
        for i in range(N):
            if random.uniform(0, 1) < pWE:
                print('    <vehicle id="right_%i" type="typeWE" route="right" depart="%i" />' % (
                    vehNr, i), file=routes)
                vehNr += 1
            if random.uniform(0, 1) < pEW:
                print('    <vehicle id="left_%i" type="typeWE" route="left" depart="%i" />' % (
                    vehNr, i), file=routes)
                vehNr += 1
            if random.uniform(0, 1) < pNS:
                print('    <vehicle id="down_%i" type="typeNS" route="down" depart="%i" color="1,0,0"/>' % (
                    vehNr, i), file=routes)
                vehNr += 1
        print("</routes>", file=routes)

def ejecutar_simulacion(sumoBinary,escenario):
    
    traci.start([
        sumoBinary,
        "-c", "data/cross.sumocfg",
        "--tripinfo-output", "tripinfo.xml",
        "--start"
    ])


    """execute the TraCI control loop"""


    # 1. Obtener el estado completo del semáforo con id "0"
    logica_actual = traci.trafficlight.getAllProgramLogics("0")[0]
    fases = logica_actual.phases

    for i, fase in enumerate(escenario["semaforo"]["fases"]):
        fases[i].duration = fase["duracion"]
        fases[i].state =  fase["estado"]

    #traci.trafficlight.setProgramLogic(tls_id, logica_actual)
    traci.trafficlight.setProgramLogic("0", logica_actual)

    traci.trafficlight.setPhase("0", 2)


    while traci.simulation.getMinExpectedNumber() > 0:
        print("Avanzando un paso")
        traci.simulationStep()
        if traci.trafficlight.getPhase("0") == 2:
            # we are not already switching
            if traci.inductionloop.getLastStepVehicleNumber("0") > 0:
                # there is a vehicle from the north, switch
                traci.trafficlight.setPhase("0", 3)
            else:
                # otherwise try to keep green for EW
                traci.trafficlight.setPhase("0", 2)
    traci.close()
    sys.stdout.flush()

def procesar_resultados():
    tree = ET.parse('tripinfo.xml')
    root = tree.getroot()

    # Ahora puedes acceder a los datos
    print(f"Elemento raíz: {root.tag}")

    print(" ESTADISTICAS DE ESTE ESCENARIO")

    #  Número de vehículos
    vehiculos = root.findall("tripinfo")


    # Tiempo promedio de viaje
    duraciones = []
    for v in root.findall("tripinfo"):
        duraciones.append(float(v.attrib["duration"]))

    promedio = sum(duraciones) / len(duraciones)
    

    # Tiempo de espera promedio
    espera = []
    for v in root.findall("tripinfo"):
        espera.append(float(v.attrib["waitingTime"]))


    print(f"Vehículos simulados: {len(vehiculos)}")
    print(f"Tiempo promedio de recorrido:  {promedio}")
    print(f"Espera promedio: {sum(espera) / len(espera)}")


if __name__ == "__main__":

    escenario  = cargar_escenario()
    generar_rutas(escenario)
    sumoBinary  = cargar_sumo()
    ejecutar_simulacion(sumoBinary,escenario)
    procesar_resultados()

















