import subprocess
import sys
import xml.etree.ElementTree as ET
import time
from utils import generar_ruta_salida
import requests
import sumolib
import json

def cargar_escenario():

    """
    with open('test.json', 'r', encoding='utf-8') as archivo:
        data = json.load(archivo)
    return data
    """

    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    if not backend_url.startswith("http"):
        backend_url = f"http://{backend_url}"
    res = requests.get(f"{backend_url}/points/prueba")
    escenario = res.json()
    return escenario

def consulta_overpass(bbox, intentos_max=3):
    """Descarga la red vial en formato XML (.osm) garantizando geometrías completas"""
    min_lat, min_lon, max_lat, max_lon = bbox

    # Query Overpass 
    query = f"""
    [out:xml][timeout:90];
    (
    way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|living_street|service)$"]({min_lat},{min_lon},{max_lat},{max_lon});
    );
    (._; >;);
    out body;
    """

    servidores = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]

    headers = {
        "User-Agent": "TranSytemTwins/1.0 (github.com/DanielMtz)",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    for intento in range(1, intentos_max + 1):
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
        "--junctions.join-dist", "10",

        # --- Rotondas y rampas: respeta lo que ya viene en OSM ---
        "--roundabouts.guess",
        "--ramps.guess",
        "--ramps.no-split",

        # --- Limpieza mínima ---
        "--remove-edges.isolated",

        # --- Semáforos: conservar info real de OSM ---
        "--tls.guess-signals",
        "--tls.default-type", "actuated",
        "--tls.cycle.time", "90",

        # --- Proyección explícita  ---
        "--proj.utm",

        # --- Precisión numérica alta ---
        "--precision", "3",
        "--precision.geo", "6",


        # --- Detalle visual/físico en nodos complejos (glorietas, intercambios) ---
        "--junctions.corner-detail", "5",
        "--junctions.internal-link-detail", "5",
        "--check-lane-foes.roundabout",

        # --- Diagnóstico: conservar info extra para depurar después ---
        "--osm.all-attributes",
        "--verbose",
    ]

    try:
        print(f"Iniciando conversión de {archivo_osm}...")
        resultado = subprocess.run(
            command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        print("¡Conversión completada con éxito!")
        print("Reporte de netconvert:\n", resultado.stdout)
        if resultado.stderr:
            print(" Advertencias de netconvert:\n", resultado.stderr)
        return ruta_red_vial

    except subprocess.CalledProcessError as e:
        print("Error durante la ejecución de netconvert:", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        return None

def conversor_net_to_geojson(ruta_net_xml, nombre_archivo="map_net.geojson"):
    """Convierte una red de SUMO a GeoJSON con coordenadas geográficas REALES"""

    print(f" Leyendo red desde: {ruta_net_xml}")
    red = sumolib.net.readNet(ruta_net_xml, withInternal=True)
    print(f" Total edges en la red (sin filtrar): {len(red.getEdges(withInternal=True))}")

    # ---------- CONECTORES DE ANILLO EN GLORIETAS ----------
    # OJO: un nodo de rotonda no solo continúa el círculo, también puede tener
    # una salida/entrada hacia una calle externa (rampa). Marcar TODO conector
    # interno que sale de un nodo de glorieta (como se hacía antes) incluye por
    # error esos conectores de rampa, que al dibujarse junto al conector real
    # del anillo se cruzan entre sí (efecto "zigzag"/"bowtie" en el mapa).
    # Aquí se identifica, para cada glorieta, únicamente el conector que une
    # cada edge del anillo con el SIGUIENTE edge del mismo anillo (en orden),
    # que es el único que realmente dibuja el contorno circular.
    conectores_anillo = set()
    for glorieta in red.getRoundabouts():
        edges_anillo = glorieta.getEdges()
        n = len(edges_anillo)
        for i in range(n):
            edge_a = red.getEdge(edges_anillo[i])
            edge_b = red.getEdge(edges_anillo[(i + 1) % n])
            for conexion in edge_a.getConnections(edge_b):
                via_lane = conexion.getViaLaneID()  # p.ej. ':61422324_2_0'
                if via_lane:
                    conectores_anillo.add(via_lane.rsplit('_', 1)[0])  # -> ':61422324_2'
    print(f" Conectores internos que forman el anillo de alguna glorieta: {len(conectores_anillo)}")

    features = []
    contador_descartados = {"sin_forma": 0, "muy_largo": 0}
    LONGITUD_MAXIMA = 10000  # metros — filtro de seguridad contra edges corruptas

    for edge in red.getEdges(withInternal=True):
        forma = edge.getShape()
        if not forma:
            contador_descartados["sin_forma"] += 1
            continue

        longitud = edge.getLength()

        # Ya NO se descartan edges cortas: netconvert genera legítimamente
        # micro-segmentos (0.2-0.5m) en junctions complejas para resolver giros.
        # Descartarlos por longitud rompe la continuidad visual de la calle.
        if longitud > LONGITUD_MAXIMA:
            contador_descartados["muy_largo"] += 1
            continue

        coordenadas = [list(red.convertXY2LonLat(x, y)) for x, y in forma]

        es_interna = edge.getFunction() == "internal"
        nodo_destino = edge.getToNode()
        tiene_semaforo = (not es_interna) and nodo_destino.getType() in (
            "traffic_light", "traffic_light_unregulated", "traffic_light_right_on_red",
        )

        # Un conector interno pertenece a una glorieta solo si es exactamente
        # el que continúa el anillo (no cualquier conector que salga del nodo).
        pertenece_a_glorieta = edge.getID() in conectores_anillo

        features.append({
            "type": "Feature",
            "properties": {
                "tipo_elemento": "conector_interno" if es_interna else "calle",
                "edge_id": edge.getID(),
                "nombre_calle": (edge.getName() or edge.getID()) if not es_interna else None,
                "carriles": edge.getLaneNumber(),
                "velocidad_max": round(edge.getSpeed() * 3.6, 1),
                "longitud": round(longitud, 2),
                "tipo": edge.getType() or "desconocido",
                "editable": not es_interna,
                "controlado_por_semaforo": tiene_semaforo,
                "tls_id": nodo_destino.getID() if tiene_semaforo else None,
                "pertenece_a_glorieta": pertenece_a_glorieta,
            },
            "geometry": {"type": "LineString", "coordinates": coordenadas},
        })

    print(f"Descartados: {contador_descartados}")
    print(f" Total features (calles + conectores): {len(features)}")

    # ---------- POLÍGONOS DE INTERSECCIÓN (para cerrar visualmente los huecos) ----------
    # netconvert reserva el área de cada junction como un polígono propio
    # (--junctions.corner-detail) y recorta las edges para que terminen justo
    # en su borde, no en el punto original del OSM. Ese hueco normalmente se
    # rellena con los internal lanes, pero los excluimos a propósito (arriba)
    # para no generar la maraña de giros cruzados en cada cruce. En su lugar,
    # rellenamos el polígono real de la junction (nodo.getShape()) con un
    # color acorde al tipo de vía dominante que llega, para "cerrar" la calle
    # visualmente sin tener que dibujar cada movimiento de giro por separado.
    features_interseccion = []
    for nodo in red.getNodes():
        forma_nodo = nodo.getShape()
        if not forma_nodo or len(forma_nodo) < 3:
            continue
        if nodo.getType() == "dead_end":
            continue

        edges_incidentes = [
            e for e in (nodo.getIncoming() + nodo.getOutgoing())
            if e.getFunction() != "internal"
        ]
        tipos_incidentes = [(e.getType() or "") for e in edges_incidentes]

        if any("motorway" in t or "trunk" in t for t in tipos_incidentes):
            tipo_dominante = "principal"
        elif any("link" in t for t in tipos_incidentes):
            tipo_dominante = "rampa"
        else:
            tipo_dominante = "calle"

        coords_nodo = [list(red.convertXY2LonLat(x, y)) for x, y in forma_nodo]
        if coords_nodo[0] != coords_nodo[-1]:
            coords_nodo.append(coords_nodo[0])

        features_interseccion.append({
            "type": "Feature",
            "properties": {
                "tipo_elemento": "interseccion",
                "nodo_id": nodo.getID(),
                "tipo": tipo_dominante,
            },
            "geometry": {"type": "Polygon", "coordinates": [coords_nodo]},
        })

    print(f" Polígonos de intersección generados: {len(features_interseccion)}")

    # Van AL PRINCIPIO de la lista para que Leaflet los dibuje primero
    # (y las calles queden encima, tapando la mayor parte del relleno).
    features = features_interseccion + features

    # ---------- SEMÁFOROS ----------
    total_nodos_tls = 0
    for nodo in red.getNodes():
        if nodo.getType() not in (
            "traffic_light", "traffic_light_unregulated", "traffic_light_right_on_red",
        ):
            continue

        total_nodos_tls += 1
        x, y = nodo.getCoord()
        lon, lat = red.convertXY2LonLat(x, y)

        programas = {}
        try:
            tls = red.getTLSSecure(nodo.getID())
            for prog_id, programa in tls.getPrograms().items():
                programas[prog_id] = [
                    {"duracion": f.duration, "estado": f.state}
                    for f in programa.getPhases()
                ]
        except Exception as e:
            print(f" No se pudo leer lógica TLS de {nodo.getID()}: {e}")

        features.append({
            "type": "Feature",
            "properties": {
                "tipo_elemento": "semaforo",
                "tls_id": nodo.getID(),
                "tipo_control": nodo.getType(),
                "calles_entrantes": [e.getID() for e in nodo.getIncoming() if e.getFunction() != "internal"],
                "calles_salientes": [e.getID() for e in nodo.getOutgoing() if e.getFunction() != "internal"],
                "programas": programas,
            },
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        })

    print(f" Total semáforos incluidos: {total_nodos_tls}")

    if not features:
        raise ValueError(f"No se encontraron elementos válidos en: {ruta_net_xml}")

    geojson_data = {"type": "FeatureCollection", "features": features}

    ruta_geojson = generar_ruta_salida(nombre_archivo)
    with ruta_geojson.open("w", encoding="utf-8") as f:
        json.dump(geojson_data, f, ensure_ascii=False, indent=4)

    print(f" GeoJSON escrito en: {ruta_geojson}")

    return ruta_geojson

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