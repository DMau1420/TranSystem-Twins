
import random
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import time
from utils import generar_ruta_salida

# Temporalmente desactivada hasta que ya  nos conectemos bien los 3 modulos
"""
def cargar_escenario():
    with open('test.json', 'r', encoding='utf-8') as archivo:
        data = json.load(archivo)
    return data
"""

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

def generar_rutas_aleatorias(random_trips,archivo_red_vial, nombre_archivo= "cross.rou.xml" ):

    ruta_salida = generar_ruta_salida(nombre_archivo)

    comando = [
        "python", random_trips,
        "-n", archivo_red_vial,
        "-e", "3600",           # 1 hora
        "-p", "5.0",            # Cada 5 s
        "--route-file", ruta_salida,
        "--validate",           # Valida rutas
        "--random",             
        "--flows", "100"         
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


