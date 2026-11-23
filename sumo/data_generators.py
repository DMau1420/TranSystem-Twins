import pathlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import time
import requests
import sumolib
import random


def cargar_escenario():

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


def descargar_red(bbox, carpeta_salida, archivo_osm="red_vial.osm"):
    """
    carpeta_salida: Path ya resuelto (normalmente utils.carpeta_proyecto(id))
    donde se escribe el .osm. Antes esto usaba generar_ruta_salida(), que le
    pegaba un timestamp y siempre escribía en la misma carpeta plana
    data/ -- eso hacía que cada importación dejara un archivo nuevo para
    siempre, y que archivos de distintos proyectos vivieran revueltos.
    """
    osm_data = consulta_overpass(bbox)

    if osm_data:
        ruta_osm = carpeta_salida / archivo_osm

        with open(ruta_osm, "w", encoding="utf-8") as f:
            f.write(osm_data)
        print("¡Descargado!")

        return ruta_osm

def conversor_osm_to_netxml(netconvertBinary, archivo_osm, carpeta_salida, archivo_red_vial="red_base.net.xml"):

    ruta_red_vial = carpeta_salida / archivo_red_vial
    
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
        "--tls.default-type", "static",
        "--tls.cycle.time", "90",

        # --- Proyección explícita  ---
        "--proj.utm",

        # --- Precisión numérica alta ---
        "--precision", "3",
        "--precision.geo", "6",

        # Traer el nombre de las calles
        "--output.street-names", "true",


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

def conversor_net_to_geojson(ruta_net_xml, carpeta_salida, nombre_archivo="red_base.geojson"):
    """Convierte una red de SUMO a GeoJSON con coordenadas geográficas REALES"""

    print(f" Leyendo red desde: {ruta_net_xml}")
    red = sumolib.net.readNet(ruta_net_xml, withInternal=True, withPrograms=True)
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
    # OJO: antes esto iteraba red.getNodes() filtrando por tipo de nodo, y
    # buscaba el programa con red.getTLSSecure(nodo.getID()). El bug: el id
    # de un <tlLogic> (y el que aparece en el atributo "tl" de cada
    # <connection>) NO siempre es igual al id del nodo/junction -- sobre
    # todo cuando netconvert fusiona varios nodos OSM en un solo "cluster"
    # (--junctions.join). getTLSSecure(), si no encuentra ese id exacto en
    # su tabla interna, en vez de fallar CREA SILENCIOSAMENTE un TLS vacío
    # (así se llama "Secure": nunca lanza excepción). Por eso los semáforos
    # salían con "programas": {} -- ninguno estaba mal calculado por SUMO,
    # el bug era de lookup en este archivo.
    #
    # La forma correcta es iterar los TLS reales (red.getTrafficLights()),
    # que sumolib ya construyó bien indexados por su id verdadero al leer
    # el <tlLogic> del net.xml. De cada TLS sacamos sus conexiones
    # (inLane, outLane, linkNo) para inferir: el nodo real que controla
    # (para la coordenada del marcador) y las calles entrantes/salientes.
    #
    # Además, tls.getID() es EL MISMO id que usa <tlLogic id="..."> en el
    # .tll.xml -- es el que hay que mandar de vuelta al editar fases desde
    # el frontend, o _aplicar_modificaciones_semaforos nunca va a encontrar
    # coincidencia (aunque los programas ya se vean bien en el mapa).
    #
    # Efecto colateral esperado y correcto: los semáforos que netconvert
    # reportó como "does not control any links; it will not be build" no
    # tienen conexiones ni programa, así que no aparecen en
    # red.getTrafficLights() y ya no se listan aquí. Antes sí aparecían
    # como marcador fantasma sin nada editable; ahora simplemente no se
    # dibujan, que es más honesto con lo que SUMO en verdad construyó.
    total_nodos_tls = 0
    for tls in red.getTrafficLights():
        conexiones = tls.getConnections()
        if not conexiones:
            continue

        edges_entrantes = {c[0].getEdge() for c in conexiones}
        edges_salientes = {c[1].getEdge() for c in conexiones}

        # Nodo real controlado por este TLS: el nodo "to" de cualquiera de
        # sus edges entrantes (todas las conexiones de un mismo TLS
        # convergen en el mismo junction o cluster).
        nodo_control = next(iter(edges_entrantes)).getToNode()
        x, y = nodo_control.getCoord()
        lon, lat = red.convertXY2LonLat(x, y)

        programas = {}
        for prog_id, programa in tls.getPrograms().items():
            programas[prog_id] = [
                {"duracion": f.duration, "estado": f.state}
                for f in programa.getPhases()
            ]

        total_nodos_tls += 1
        features.append({
            "type": "Feature",
            "properties": {
                "tipo_elemento": "semaforo",
                # IMPORTANTE: este id es el mismo que usa el <tlLogic> real
                # en el .tll.xml -- es el que hay que mandar de vuelta al
                # editar fases, o _aplicar_modificaciones_semaforos no va a
                # encontrar coincidencia.
                "tls_id": tls.getID(),
                "tipo_control": nodo_control.getType(),
                "calles_entrantes": [e.getID() for e in edges_entrantes if e.getFunction() != "internal"],
                "calles_salientes": [e.getID() for e in edges_salientes if e.getFunction() != "internal"],
                "programas": programas,
            },
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        })

    print(f" Total semáforos incluidos: {total_nodos_tls}")

    if not features:
        raise ValueError(f"No se encontraron elementos válidos en: {ruta_net_xml}")

    geojson_data = {"type": "FeatureCollection", "features": features}

    ruta_geojson = carpeta_salida / nombre_archivo
    with ruta_geojson.open("w", encoding="utf-8") as f:
        json.dump(geojson_data, f, ensure_ascii=False, indent=4)

    print(f" GeoJSON escrito en: {ruta_geojson}")

    return ruta_geojson

def generar_rutas_aleatorias(random_trips, archivo_red_vial, demanda_vehicular, carpeta_salida,
                            nombre_archivo="demanda.rou.xml", semilla=42, tiempo_insercion=3600,
                            porcentaje_pesados=0.0):
    """
    Genera viajes aleatorios con randomTrips.py y los guarda en un .rou.xml.
    - demanda_vehicular: vehículos POR HORA.
    Regresa la ruta del .rou.xml, o None si algo falló.
    """
    if demanda_vehicular is None or demanda_vehicular <= 0:
        print("Error: la demanda vehicular debe ser mayor que 0 (veh/h).")
        return None

    carpeta_salida = pathlib.Path(carpeta_salida)
    ruta_salida = carpeta_salida / nombre_archivo
    ruta_viajes = carpeta_salida / "viajes.trips.xml"

    # demanda en veh/h -> un vehículo cada (3600 / demanda) segundos
    periodo = 3600 / demanda_vehicular
    esperados = round(demanda_vehicular * tiempo_insercion / 3600)

    comando = [
        sys.executable, str(random_trips),
        "-n", str(archivo_red_vial),
        "-b", "0",
        "-e", str(tiempo_insercion),
        "-p", f"{periodo:.4f}",
        "-o", str(ruta_viajes), 
        "--route-file", str(ruta_salida),
        "--seed", str(semilla),
        "--validate",
    ]

    try:
        resultado = subprocess.run(comando, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print("Error durante la creación de rutas (randomTrips):")
        print(e.stderr or e.stdout)
        return None
    except FileNotFoundError as e:
        print(f"No se encontró randomTrips.py o el intérprete de Python: {e}")
        return None

    if resultado.stderr:
        print("Advertencias de randomTrips:\n", resultado.stderr[-500:])

    # Contar cuántos viajes quedaron realmente después de --validate
    try:
        root = ET.parse(ruta_salida).getroot()
    except (ET.ParseError, FileNotFoundError) as e:
        print(f"No se pudo leer el archivo de rutas generado: {e}")
        return None

    generados = len(root.findall("vehicle")) + len(root.findall("trip"))
    print(f"Rutas generadas en: {ruta_salida} (semilla {semilla})")
    print(f"  Vehículos esperados: {esperados} | generados: {generados}")
    if generados < 0.95 * esperados:
        print("  AVISO: --validate descartó más del 5% de los viajes; "
            "la demanda real es menor a la pedida.")


    composicion = asignar_tipos_vehiculo(ruta_salida, porcentaje_pesados, semilla)
    print(f"Composicion vehicular: {composicion}")
    return ruta_salida


# ===============================================================
#           TIPOS DE VEHICULO
# ===============================================================

def asignar_tipos_vehiculo(ruta_rou, porcentaje_pesados=0.0, semilla=42):
    """Define los vType (auto y camión) dentro de un archivo .rou.xml de SUMO

    y asigna a cada viaje uno de los dos tipos de forma aleatoria reproducible.

    Regresa un diccionario con el conteo final: {"auto": n, "camion": n}.
    """


    if not 0 <= porcentaje_pesados <= 100:
        raise ValueError("porcentaje_pesados debe estar entre 0 y 100")

    #  Cargar y parsear el archivo XML
    tree = ET.parse(ruta_rou)
    root = tree.getroot()

    #  Obtener y contar todos los viajes (<vehicle> y <trip>)
    viajes = root.findall("vehicle") + root.findall("trip")
    total_viajes = len(viajes)


    n_pesados = round(total_viajes * porcentaje_pesados / 100)
    generador = random.Random(semilla)
    # Definir que vehciulos seran  de tipo pesado
    indices_pesados = set(generador.sample(range(total_viajes), n_pesados))

    #  Asignar los tipos recorriendo la lista de viajes
    for idx, viaje in enumerate(viajes):
        viaje.set("type", "camion" if idx in indices_pesados else "auto")

    # 6. Definición de configuraciones para SUMO
    TIPOS_VEHICULO = {
        "auto": {
            "vClass": "passenger", "length": "4.5", "width": "1.8",
            "maxSpeed": "33.33", "accel": "2.6", "decel": "4.5",
            "guiShape": "passenger", "color": "0,114,178",
        },
        "camion": {
            "vClass": "truck", "length": "12", "width": "2.5",
            "maxSpeed": "25", "accel": "1.3", "decel": "4.0",
            "guiShape": "truck", "color": "213,94,0",
        },
    }

    # 7. Limpiar vTypes antiguos e inyectar los nuevos al inicio del archivo
    for viejo in root.findall("vType"):
        root.remove(viejo)
        
    for posicion, (id_tipo, atributos) in enumerate(TIPOS_VEHICULO.items()):
        root.insert(posicion, ET.Element("vType", id=id_tipo, **atributos))

    # 8. Formatear estéticamente y guardar el archivo
    ET.indent(tree, space="    ", level=0)
    tree.write(ruta_rou, encoding="utf-8", xml_declaration=True)

    # 9. Retornar el resumen de vehículos generados
    return {"auto": total_viajes - n_pesados, "camion": n_pesados}


def crear_sumo_config(net, rou, carpeta_salida, nombre_config="simulacion.sumocfg",
                    tiempo_maximo=7200, paso=1.0, semilla=42, tiempo_teleport=300):
    """
    Genera el .sumocfg del escenario con los parámetros de simulación
    explícitos (así quedan documentados y no dependen de los valores por
    defecto de SUMO).

    - tiempo_maximo: segundo en que SUMO se detiene. Debe ser MAYOR que la
    ventana de inserción de la demanda, para que los últimos vehículos
    alcancen a terminar su viaje.
    - paso: step-length en segundos.
    - semilla: semilla del generador aleatorio de SUMO (afecta, por ejemplo,
    la imperfección de los conductores).
    - tiempo_teleport: segundos que un vehículo puede estar atascado antes de
    que SUMO lo teletransporte. 300 es el valor por defecto de SUMO; se deja
    explícito para documentarlo. Con -1 se desactiva.
    """
    root = ET.Element("configuration")
    ruta_config = pathlib.Path(carpeta_salida) / nombre_config

    input_node = ET.SubElement(root, "input")
    ET.SubElement(input_node, "net-file", value=str(pathlib.Path(net).resolve()))
    ET.SubElement(input_node, "route-files", value=str(pathlib.Path(rou).resolve()))

    time_node = ET.SubElement(root, "time")
    ET.SubElement(time_node, "begin", value="0")
    ET.SubElement(time_node, "end", value=str(tiempo_maximo))
    ET.SubElement(time_node, "step-length", value=str(paso))

    processing_node = ET.SubElement(root, "processing")
    ET.SubElement(processing_node, "time-to-teleport", value=str(tiempo_teleport))

    random_node = ET.SubElement(root, "random_number")
    ET.SubElement(random_node, "seed", value=str(semilla))

    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ", level=0)
    tree.write(ruta_config, encoding="utf-8", xml_declaration=True)
    print(f" Archivo de configuración creado con éxito: {ruta_config}")

    return ruta_config