from sumolib import checkBinary
import os
import sys
import time

def cargar_herramientas_sumo():
    if 'SUMO_HOME' not in os.environ:
        sys.exit(" ERROR: Declara la variable 'SUMO_HOME'")
    
    tools_path = os.path.join(os.environ['SUMO_HOME'], 'tools')
    if tools_path not in sys.path:
        sys.path.append(tools_path)
    

    try:
        herramientas = {
            # Binarios principales
            'sumo': checkBinary('sumo'),           # Motor sin GUI
            'sumo_gui': checkBinary('sumo-gui'),   
            'netconvert': checkBinary('netconvert'), # Convertidor de redes
            'netedit': checkBinary('netedit'),     # Editor visual de redes
            'duarouter': checkBinary('duarouter'), # Enrutador de viajes
            'jtrrouter': checkBinary('jtrrouter'), # Enrutador con tráfico
            'activitygen': checkBinary('activitygen'), # Generador de actividades
            
            # Scripts de python para sumo
            'random_trips': os.path.join(tools_path, 'randomTrips.py'),
            'route2trips': os.path.join(tools_path, 'route2trips.py'),
            'flowrouter': os.path.join(tools_path, 'flowrouter.py'),
            
            # Directorios útiles
            'tools_dir': tools_path,
            'sumo_home': os.environ['SUMO_HOME'],
        }
        
        print(" -> Herramientas SUMO cargadas correctamente")
        return herramientas
        
    except Exception as e:
        sys.exit(f" -> Error al cargar herramientas SUMO: {e}")

def verificar_archivo_salida(archivo, timeout=10):
    start_time = time.time()
    size = -1
    
    while time.time() - start_time < timeout:
        if os.path.exists(archivo):
            new_size = os.path.getsize(archivo)
            if new_size > 0 and new_size == size:
                print(f"Archivo {archivo} listo (tamaño: {new_size} bytes)")
                return os.path.abspath(archivo)
            size = new_size
        time.sleep(0.1)
    
    print(f"ADVERTENCIA: No se pudo verificar {archivo}")
    return None
