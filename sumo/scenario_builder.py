import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


def construir_red_escenario(netconvertBinary, ruta_net_base_proyecto, carpeta_escenario,
    modificaciones_edges=None, modificaciones_semaforos=None,
    nombre_salida="red_escenario.net.xml"):
    """
    Genera el .net.xml PROPIO de un escenario a partir de la red BASE del
    proyecto.

    - ruta_net_base_proyecto: red del proyecto, generada UNA sola vez cuando
        se creó el proyecto.
        Es de solo lectura aquí: netconvert la EXPORTA a archivos planos, nunca la sobreescribe.

    - carpeta_escenario: carpeta propia de este escenario (ej.
        "escenarios/<escenario_id>/"), donde se escriben todos los archivos
        intermedios y el .net.xml final del escenario. Nunca debe apuntar a
        la carpeta del proyecto.

    - modificaciones_edges: lista de dicts, ej:
        [{"edge_id": "128255275", "carriles": 4, "velocidad_max": 80}]

    - modificaciones_semaforos: lista de dicts, ej:
        [{
            "tls_id": "61422324",
            "fases": [
                {"indice": 0, "duracion": 45, "estado": "GGGgrrrrGGGgrrrr"},
                {"indice": 2, "duracion": 4,  "estado": "yyyGrrrryyyGrrrr"},
            ]
        }]
        "indice" es la posición de esa fase dentro del programa (0-based,
        mismo orden que en netedit / TraCI). Solo se tocan los índices que
        el usuario mandó; el resto del programa se deja tal cual.

    Regresa la ruta al .net.xml del escenario. Si NO hay ninguna
    modificación (ni edges ni semáforos), regresa directamente
    ruta_net_base_proyecto: no tiene caso duplicar la red si es idéntica
    a la del proyecto.
    """
    modificaciones_edges = modificaciones_edges or []
    modificaciones_semaforos = modificaciones_semaforos or []

    if not modificaciones_edges and not modificaciones_semaforos:
        print("Escenario sin modificaciones: se usa directamente la red base del proyecto.")
        return ruta_net_base_proyecto

    # IMPORTANTE: resolver a ruta absoluta aquí mismo. SUMO no interpreta
    # las rutas relativas del .sumocfg contra el directorio de trabajo del
    # proceso, sino contra la carpeta donde vive el propio .sumocfg -- si
    # carpeta_escenario se queda relativa (ej. "storage/proyectos/3/..."),
    # el .net.xml que reconstruimos aquí abajo se referencia mal cuando el
    # .sumocfg vive en otra carpeta (ej. "sumo/data/"), y SUMO lo busca
    # concatenado ahí y truena con "File ... is not accessible".
    carpeta_escenario = Path(carpeta_escenario).resolve()
    carpeta_escenario.mkdir(parents=True, exist_ok=True)
    prefijo_ruta = carpeta_escenario / "plano"

    # ---------- 1) Exportar la red BASE del proyecto a archivos planos ----------
    # Esto NUNCA toca ruta_net_base_proyecto: netconvert la lee y escribe
    # los archivos planos en la carpeta del escenario.
    comando_export = [
        netconvertBinary,
        "--sumo-net-file", str(ruta_net_base_proyecto),
        "--plain-output-prefix", str(prefijo_ruta),
    ]
    print(f"Exportando red base del proyecto ({ruta_net_base_proyecto}) a formato plano...")
    try:
        subprocess.run(comando_export, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        # check=True hace que la excepción se lance ANTES de que podamos
        # imprimir/leer e.stdout / e.stderr en el flujo normal. Si no se
        # capturan aquí y se re-lanzan con el mensaje real, quien reciba
        # esta excepción más arriba (server.py) solo ve "exit status 1"
        # sin ninguna pista de qué archivo o parámetro falló.
        print("STDOUT de netconvert (exportar a plano):\n", e.stdout)
        print("STDERR de netconvert (exportar a plano):\n", e.stderr)
        raise RuntimeError(
            f"netconvert falló al exportar la red base a formato plano "
            f"(exit code {e.returncode}). Detalle:\n{e.stderr or e.stdout}"
        ) from e

    archivo_edg = f"{prefijo_ruta}.edg.xml"
    archivo_nod = f"{prefijo_ruta}.nod.xml"
    archivo_con = f"{prefijo_ruta}.con.xml"
    archivo_tll = f"{prefijo_ruta}.tll.xml"

    # ---------- 2) Modificar carriles / velocidad en el .edg.xml ----------
    if modificaciones_edges:
        _aplicar_modificaciones_edges(archivo_edg, modificaciones_edges)

        # Reducir numLanes en el .edg.xml no actualiza el .con.xml: si una
        # <connection> sigue apuntando a un fromLane/toLane que ya no
        # existe, netconvert truena al reconstruir con "Lane index is
        # larger than number of lanes". Se limpian esas conexiones huérfanas
        # antes de seguir.
        _sanitizar_conexiones_por_cambio_carriles(archivo_con, modificaciones_edges)

    # ---------- 3) Modificar fases de semáforo en el .tll.xml ----------
    if modificaciones_semaforos:
        if not Path(archivo_tll).exists():
            print(" Se pidieron modificaciones de semáforo pero la red no generó .tll.xml "
                "(¿la red base tiene semáforos?). Se ignoran esos cambios.")
        else:
            _aplicar_modificaciones_semaforos(archivo_tll, modificaciones_semaforos)

    # ---------- 4) Reconstruir el .net.xml del escenario ----------
    ruta_red_escenario = carpeta_escenario / nombre_salida

    comando_rebuild = [
        netconvertBinary,
        "--node-files", archivo_nod,
        "--edge-files", archivo_edg,
        "--connection-files", archivo_con,
        "--output-file", str(ruta_red_escenario),
    ]
    if Path(archivo_tll).exists():
        comando_rebuild += ["--tllogic-files", archivo_tll]

    print("Reconstruyendo red del escenario con las modificaciones aplicadas...")
    try:
        resultado = subprocess.run(comando_rebuild, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print("STDOUT de netconvert (reconstrucción):\n", e.stdout)
        print("STDERR de netconvert (reconstrucción):\n", e.stderr)
        raise RuntimeError(
            f"netconvert falló al reconstruir el .net.xml del escenario "
            f"(exit code {e.returncode}). Detalle:\n{e.stderr or e.stdout}"
        ) from e

    if resultado.stderr:
        print("Advertencias de netconvert al reconstruir:\n", resultado.stderr)

    print(f" Red del escenario generada en: {ruta_red_escenario}")
    return ruta_red_escenario


def _pertenece_a_via(edge_id, id_base):
    """
    netconvert parte una sola vía de OSM en varios edges internos de SUMO:
    la vía "128255275" se convierte en "128255275#0", "128255275#1", etc.
    (y, si hay tramos en sentido contrario, a veces con un "-" al inicio,
    ej. "-128255275#0"). El usuario edita "una calle", así que su edge_id
    debe aplicarse a TODOS los segmentos internos que le pertenecen, no
    solo a una coincidencia exacta.
    """
    if edge_id == id_base or edge_id == f"-{id_base}":
        return True
    return edge_id.startswith(f"{id_base}#") or edge_id.startswith(f"-{id_base}#")


def _aplicar_modificaciones_edges(archivo_edg, modificaciones_edges):
    tree = ET.parse(archivo_edg)
    root = tree.getroot()

    ids_base_encontrados = set()
    total_segmentos_modificados = 0

    for edge_el in root.findall("edge"):
        edge_id = edge_el.get("id")

        # Un edge_id de SUMO puede pertenecer a como mucho una modificación
        # del usuario (los ids base no se traslapan entre sí).
        cambio = next(
            (m for m in modificaciones_edges if _pertenece_a_via(edge_id, m["edge_id"])),
            None,
        )
        if cambio is None:
            continue

        ids_base_encontrados.add(cambio["edge_id"])
        total_segmentos_modificados += 1

        if cambio.get("carriles") is not None:
            edge_el.set("numLanes", str(int(cambio["carriles"])))

        if cambio.get("velocidad_max") is not None:
            # Los archivos planos de SUMO guardan velocidad en m/s;
            # el panel de edición y el GeoJSON la manejan en km/h.
            velocidad_ms = float(cambio["velocidad_max"]) / 3.6
            edge_el.set("speed", f"{velocidad_ms:.2f}")

    tree.write(archivo_edg, encoding="utf-8", xml_declaration=True)

    ids_faltantes = {m["edge_id"] for m in modificaciones_edges} - ids_base_encontrados
    print(
        f"Carriles/velocidad aplicados: {len(ids_base_encontrados)}/{len(modificaciones_edges)} "
        f"vías encontradas ({total_segmentos_modificados} segmentos internos modificados en total)."
    )
    if ids_faltantes:
        print(f" No se encontraron estos edge_id en la red: {ids_faltantes}")


def _sanitizar_conexiones_por_cambio_carriles(archivo_con, modificaciones_edges):
    """
    Al reducir numLanes de un edge en el .edg.xml, el .con.xml puede seguir
    teniendo <connection> que apuntan a un fromLane/toLane que ya no
    existe. netconvert no lo tolera al reconstruir y truena con "Lane
    index is larger than number of lanes". Aquí se eliminan esas
    conexiones huérfanas antes de reconstruir la red -- decisión
    conservadora: se prefiere perder un movimiento de giro puntual antes
    que tronar toda la generación del escenario.

    Solo aplica cuando se REDUCEN carriles; aumentarlos nunca invalida un
    índice de carril ya existente.
    """
    cambios_por_id_base = {
        m["edge_id"]: m for m in modificaciones_edges if m.get("carriles") is not None
    }
    if not cambios_por_id_base:
        return

    tree = ET.parse(archivo_con)
    root = tree.getroot()

    conexiones_eliminadas = 0
    for conexion_el in list(root.findall("connection")):
        from_id = conexion_el.get("from")
        to_id = conexion_el.get("to")

        cambio_from = next(
            (m for id_base, m in cambios_por_id_base.items() if _pertenece_a_via(from_id, id_base)),
            None,
        )
        cambio_to = next(
            (m for id_base, m in cambios_por_id_base.items() if _pertenece_a_via(to_id, id_base)),
            None,
        )

        from_lane = int(conexion_el.get("fromLane", "0"))
        to_lane = int(conexion_el.get("toLane", "0"))

        excede = (
            (cambio_from is not None and from_lane >= int(cambio_from["carriles"])) or
            (cambio_to is not None and to_lane >= int(cambio_to["carriles"]))
        )
        if excede:
            root.remove(conexion_el)
            conexiones_eliminadas += 1

    if conexiones_eliminadas:
        print(f" Se removieron {conexiones_eliminadas} conexión(es) que ya no cabían tras reducir carriles.")

    tree.write(archivo_con, encoding="utf-8", xml_declaration=True)


def _aplicar_modificaciones_semaforos(archivo_tll, modificaciones_semaforos):
    tree = ET.parse(archivo_tll)
    root = tree.getroot()

    tls_por_id = {t.get("id"): t for t in root.findall("tlLogic")}
    tls_encontrados = set()

    for cambio in modificaciones_semaforos:
        tls_id = cambio["tls_id"]
        tl_logic_el = tls_por_id.get(tls_id)

        if tl_logic_el is None:
            print(f" No se encontró el semáforo con tls_id='{tls_id}' en la red.")
            continue

        fases_el = tl_logic_el.findall("phase")
        hubo_cambio_real = False

        for fase_cambio in cambio.get("fases", []):
            indice = fase_cambio["indice"]
            if indice >= len(fases_el):
                print(f" El semáforo '{tls_id}' no tiene una fase con índice {indice} " f"(tiene {len(fases_el)} fases). Se ignora ese cambio.")
                continue

            fase_el = fases_el[indice]
            if fase_cambio.get("duracion") is not None:
                fase_el.set("duration", str(int(fase_cambio["duracion"])))
                hubo_cambio_real = True
            if fase_cambio.get("estado") is not None:
                fase_el.set("state", fase_cambio["estado"])
                hubo_cambio_real = True

        # El usuario editó fases a mano: este semáforo deja de dejarle la
        # decisión a SUMO (actuated, dinámico según detectores) y pasa a
        # tiempo fijo, para que lo que escribió sea EXACTAMENTE lo que
        # corre en la simulación. Los semáforos que nadie tocó se quedan
        # tal cual venían (actuated), sin este cambio.
        if hubo_cambio_real:
            tl_logic_el.set("type", "static")
            tls_encontrados.add(tls_id)

    tree.write(archivo_tll, encoding="utf-8", xml_declaration=True)

    tls_faltantes = {c["tls_id"] for c in modificaciones_semaforos} - tls_encontrados
    print(f"Semáforos modificados: {len(tls_encontrados)}/{len(modificaciones_semaforos)} encontrados.")
    if tls_faltantes:
        print(f" No se encontraron estos tls_id en la red: {tls_faltantes}")