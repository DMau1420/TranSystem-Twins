import sys
import traci
from sumo_tools import cargar_herramientas_sumo
from data_generators import conversor_osm_to_netxml
from data_generators import generar_rutas_aleatorias
from data_generators import crear_sumo_config
from simulation_engine import ejecutar_simulacion
from result_analyzer import procesar_resultados
from pathlib import Path


def main():

    try:
        """
        print("Cargando escenario...")
        escenario = cargar_escenario()
        

        print("Generando rutas...")
        if not generar_rutas(escenario):
            print("Error al generar rutas. Abortando.")
            return 1
        """
        print("Configurando SUMO...")

        herramientas = cargar_herramientas_sumo()
        sumoBinary = herramientas['sumo']

        netconvertBinary =  herramientas['netconvert']
        random_trips  =   herramientas['random_trips']

        BASE_DIR = Path(__file__).resolve().parent
        archivo_osm = BASE_DIR / "data" / "red_vial_20260817_131434.osm"

        archivo_red_vial = conversor_osm_to_netxml(netconvertBinary, archivo_osm)
        archivo_rutas = generar_rutas_aleatorias(random_trips, archivo_red_vial)
        archivo_config = crear_sumo_config(archivo_red_vial, archivo_rutas)
        archivo_resultados = ejecutar_simulacion(sumoBinary, archivo_config)
        procesar_resultados(archivo_resultados)

    except KeyboardInterrupt:
        print("\nSimulación interrumpida por el usuario")
        try:
            traci.close()
        except:
            pass
        return 1
        
    except Exception as e:
        print(f"Error fatal: {e}")
        try:
            traci.close()
        except:
            pass
        return 1
    
if __name__ == "__main__":
    sys.exit(main())

