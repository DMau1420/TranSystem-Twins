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


def calcular_bbox(polygon):
    """Calcula bbox desde un polígono GeoJSON."""
    coords = polygon["coordinates"][0]  # anillo exterior
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return (min(lats), min(lons), max(lats), max(lons))


def main():

    try:
    
        print("Cargando escenario...")
        escenario = cargar_escenario()
        print(escenario)
    
        print("Configurando SUMO...")

        herramientas = cargar_herramientas_sumo()
        sumoBinary = herramientas['sumo']

        netconvertBinary =  herramientas['netconvert']
        random_trips  =   herramientas['random_trips']


        # Temporal para la prueba

        """
        escenario = {
            "proyecto_id": 3,
            "nombre": "Interseccion Av. Insurgentes",
            "geometria": {
                "id": "b3e33657-6c14-4c60-aeca-0fee5b22ca4a",
                "lat": 0.0,
                "lng": 0.0,
                "geoJson": {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [-99.182682, 19.448788],
                            [-99.18045, 19.456395],
                            [-99.175816, 19.471448],
                            [-99.188347, 19.469505],
                            [-99.190407, 19.460442],
                            [-99.182682, 19.448788]
                        ]]
                    }
                },
                "street": "algo",
                "displayName": "otro algo"
            },
            "demanda_vehicular": 100
        }
        """

        polygon = escenario["geometria"]["geoJson"]["geometry"]
        bbox = calcular_bbox(polygon)
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

        base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        if not base_url.startswith("http"):
            base_url = f"http://{base_url}"
        respuesta = requests.post(f"{base_url}/resultado-sumo", json=payload)
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

