
import xml.etree.ElementTree as ET # Libreria para abrir XML

def procesar_resultados(archivo):
    """
    Procesa los resultados SOLO después de verificar el archivo
    """
    
    try:
        tree = ET.parse(archivo)
        root = tree.getroot()

        print("\n" + "="*50)
        print(" ESTADISTICAS DEL ESCENARIO")
        print("="*50)

        vehiculos = root.findall("tripinfo")
        
        if len(vehiculos) == 0:
            print("No se encontraron vehículos en la simulación")
            return

        duraciones = []
        for v in root.findall("tripinfo"):
            duraciones.append(float(v.attrib["duration"]))

        promedio = sum(duraciones) / len(duraciones)

        espera = []
        for v in root.findall("tripinfo"):
            espera.append(float(v.attrib["waitingTime"]))

        """
        print(f"Vehículos simulados: {len(vehiculos)}")
        print(f"Tiempo promedio de recorrido: {promedio:.2f} segundos")
        print(f"Espera promedio: {sum(espera) / len(espera):.2f} segundos")
        print("="*50 + "\n")
        """

        espera_promedio  = sum(espera) / len(espera)

        return {
            "vehiculos_simulados": len(vehiculos),
            "tiempo_promedio_recorrido": promedio,
            "espera_promedio" : espera_promedio,
        }

    
        
    except ET.ParseError as e:
        print(f"ERROR: No se pudo parsear tripinfo.xml: {e}")
    except Exception as e:
        print(f"ERROR inesperado: {e}")

