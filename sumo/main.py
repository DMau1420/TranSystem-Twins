import sys
import traci
from sumo_tools import cargar_herramientas_sumo
from data_generators import conversor_osm_to_netxml
from data_generators import generar_rutas_aleatorias
from data_generators import crear_sumo_config
from data_generators import cargar_escenario
from data_generators import descargar_red
from simulation_engine import ejecutar_simulacion
from result_analyzer import procesar_resultados
from pathlib import Path
import requests

def main():

    try:
    
        #print("Cargando escenario...")
        #escenario = cargar_escenario()
        #print(escenario)
    
        print("Configurando SUMO...")

        herramientas = cargar_herramientas_sumo()
        sumoBinary = herramientas['sumo']

        netconvertBinary =  herramientas['netconvert']
        random_trips  =   herramientas['random_trips']


        # Temporal para la prueba
        escenario = {

        "proyecto_id": 3,

        "nombre": "Interseccion Av. Insurgentes",

        "bbox": (19.4020, -99.1710, 19.4050, -99.1680), 

        "demanda_vehicular": 100
        
        }

        bbox = escenario["bbox"]
        print(bbox)

        archivo_osm  = descargar_red(bbox)
        archivo_red_vial = conversor_osm_to_netxml(netconvertBinary, archivo_osm)
        archivo_rutas = generar_rutas_aleatorias(random_trips, archivo_red_vial,escenario["demanda_vehicular"])
        archivo_config = crear_sumo_config(archivo_red_vial, archivo_rutas)
        archivo_resultados = ejecutar_simulacion(sumoBinary, archivo_config)
        indicadores = procesar_resultados(archivo_resultados)
        print(indicadores)


        payload = {
            "proyecto_id": escenario.get("proyecto_id"),  # pídele que lo incluya en el GET si no lo trae
            **indicadores
        }

        BASE_URL = "https://transystemtwins.com"
        respuesta = requests.post(f"{BASE_URL}/resultado-sumo", json=payload)
        print(f"Resultado enviado, status: {respuesta.status_code}")


        # Agrega esto mau de tu lado para recibir los resultados
        """
        @app.post("/resultado-sumo")
        def recibir_resultado(datos: dict):
            print(datos)
            return {"status": "recibido"}
        """

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

