
import random
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import time
from utils import generar_ruta_salida
import requests

# Temporalmente desactivada hasta que ya  nos conectemos bien los 3 modulos

def cargar_escenario():

    """
    with open('test.json', 'r', encoding='utf-8') as archivo:
        data = json.load(archivo)
    return data
    """

    BASE_URL = "https://transystemtwins.com"
    res = requests.get(f"{BASE_URL}/get-sumo-json")
    escenario = res.json()
    return escenario

def consulta_overpass(bbox, intentos_max=3):
    """Descarga la red vial en formato XML (.osm) garantizando geometrías completas.

    Maneja timeouts y reintentos en servidores de respaldo.
    """
    min_lat, min_lon, max_lat, max_lon = bbox

    # Query Overpass 
    query = f"""
    [out:xml][timeout:90];
    (
    way["highway"]({min_lat},{min_lon},{max_lat},{max_lon});
    );
    (._; >;);
    out body;
    """

    # Lista de servidores 
    servidores = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]

    headers = {
        "User-Agent": "TranSytemTwins/1.0 (github.com/DanielMtz)",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    for intento in range(1, intentos_max + 1):
        # Alterna servidor en cada intento si hay problemas
        url_api = servidores[(intento - 1) % len(servidores)]

        try:
            print(
                f" Intento {intento}/{intentos_max} conectando a {url_api}..."
            )

            response = requests.post(
                url_api,
                data={"data": query.strip()},
                timeout=100,
                headers=headers,
            )

            if response.status_code == 200:
                return response.text
            elif response.status_code in (429, 504):
                print(
                    f" Servidor saturado (HTTP {response.status_code}). Esperando antes de reintentar..."
                )
                time.sleep(5 * intento)  
            else:
                print(f" Error devuelto por la API: HTTP {response.status_code}")
                break

        except requests.exceptions.Timeout:
            print(" Timeout de red alcanzado en Python. Reintentando...")
            time.sleep(3)
        except requests.exceptions.RequestException as e:
            print(f" Error de conexión: {e}")
            break

    return None


def descargar_red(bbox, archivo_osm = "red_vial.osm"):
    osm_data = consulta_overpass(bbox)

    if osm_data:

        ruta_osm = generar_ruta_salida(archivo_osm)

        with open(ruta_osm, "w", encoding="utf-8") as f:
            f.write(osm_data)
        print("¡Descargado!")

        return ruta_osm

def conversor_osm_to_netxml(netconvertBinary, archivo_osm, archivo_red_vial = "map_net.net.xml"):

    ruta_red_vial = generar_ruta_salida(archivo_red_vial)
    
    command = [
        netconvertBinary,
        "--osm-files", archivo_osm,
        "--output-file", ruta_red_vial,
        "--junctions.join",
        "--roundabouts.guess",  
        "--ramps.guess" 
    ]

    try:
        print(f"Iniciando conversión de {archivo_osm}...")
        resultado = subprocess.run(
            command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        print("¡Conversión completada con éxito!")
        print("Reporte de netconvert:\n", resultado.stdout) 
        
        return ruta_red_vial

    except subprocess.CalledProcessError as e:
        print("Error durante la ejecución de netconvert:", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        return None

def generar_rutas_aleatorias(random_trips,archivo_red_vial,demanda_vehicular, nombre_archivo= "cross.rou.xml"):

    ruta_salida = generar_ruta_salida(nombre_archivo)

    begin_time = 0
    tiempo_simulacion = 3600
    #  Calcular el periodo para tener exactamente 'demanda_vehicular' vehículos
    periodo = tiempo_simulacion / demanda_vehicular
    
    comando = [
        "python", random_trips,
        "-n", archivo_red_vial,
        "-b", str(begin_time),        
        "-e", str(tiempo_simulacion),   
        "-p", str(periodo),             
        "--route-file", ruta_salida,
        "--validate",                   
        "--random"                       
    ]
    try:
        subprocess.run(comando, check=True)
        print(f" Rutas vehiculares generadas en : {ruta_salida}")
        
        return ruta_salida

    except subprocess.CalledProcessError as e:
        print("Error durante la creacion de rutas:" +  "\n Error:" ,{e})
        print(e.stderr, file=sys.stderr)
        return None

def crear_sumo_config(net, rou, nombre_config = "simulacion.sumocfg"):
    # Crear el elemento raíz
    root = ET.Element("configuration")

    ruta_config = generar_ruta_salida(nombre_config)
    # Sección de entrada 
    input_node = ET.SubElement(root, "input")
    ET.SubElement(input_node, "net-file", value=str(net))
    ET.SubElement(input_node, "route-files", value=str(rou))
    
    # Sección de tiempo
    time_node = ET.SubElement(root, "time")
    ET.SubElement(time_node, "begin", value="0")
    ET.SubElement(time_node, "end", value="3600")
    
    # Guardar el archivo XML formateado
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ", level=0)
    tree.write(ruta_config, encoding="utf-8", xml_declaration=True)
    print(f" Archivo de configuración creado con éxito: {ruta_config}")

    return ruta_config


