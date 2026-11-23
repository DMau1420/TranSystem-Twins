"""
escenario_conexiones.py: CONEXIONES entre carriles y ENLACES de los semáforos.

Una conexión dice "el carril X del tramo A continúa en el carril Y del tramo B".
Viven en dos archivos planos:
  .con.xml  todas las conexiones
  .tll.xml  las que controla un semáforo (con tl="..." y linkIndex="N") + el programa de fases

Regla de oro: en cada fase, el `state` del semáforo tiene UN CARÁCTER POR ENLACE
(posición = linkIndex). Si se agrega un enlace, cada fase debe ganar un carácter.

AGREGAR carriles: el carril nuevo copia las conexiones de su vecino y el semáforo gana enlaces.
REDUCIR carriles: las conexiones del carril eliminado pasan al vecino y el semáforo se
reinterpreta (se borran enlaces duplicados, se renumeran los demás).

Convención: `nuevos` = {tramo: (carriles_antes, carriles_despues)}.
  agregar carriles  -> despues > antes     reducir carriles -> despues < antes
"""
import copy
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------
def dividir_cambios(nuevos):
    """Separa `nuevos` en (reducciones, adiciones)."""
    reducciones = {t: p for t, p in nuevos.items() if p[1] < p[0]}
    adiciones = {t: p for t, p in nuevos.items() if p[1] > p[0]}
    return reducciones, adiciones


def lane_destino(c, adiciones, k):
    """
    Carril de destino de la copia número k de la conexión `c`.
    Si el destino también crece y la conexión iba a su carril más alto, la copia va al
    carril nuevo correspondiente; si no, mantiene el mismo carril de destino.
    """
    destino, carril = c.get("to"), int(c.get("toLane"))
    if destino in adiciones and carril == adiciones[destino][0] - 1:
        return min(carril + k, adiciones[destino][1] - 1)
    return carril


def _es_del_carril_mas_alto(c, adiciones):
    """¿Esta conexión sale del carril más alto (original) de un tramo al que se agregan carriles?"""
    origen = c.get("from")
    return origen in adiciones and int(c.get("fromLane")) == adiciones[origen][0] - 1



# ---------------------------------------------------------------------
# .con.xml: copiar y redirigir conexiones
# ---------------------------------------------------------------------
def _redirigir_conexiones(raiz, reducciones):
    """
    REDUCIR: toda conexión que usaba un carril eliminado pasa al carril más alto que queda.
    Si dos conexiones quedan idénticas, se borra una. Regresa (vistas, redirigidas, duplicadas).
    """
    vistas, redirigidas, duplicadas = set(), 0, 0
    for c in list(raiz.findall("connection")):
        origen, destino = c.get("from"), c.get("to")
        f, t = int(c.get("fromLane")), int(c.get("toLane"))
        nf = min(f, reducciones[origen][1] - 1) if origen in reducciones else f
        nt = min(t, reducciones[destino][1] - 1) if destino in reducciones else t
        if (nf, nt) != (f, t):
            c.set("fromLane", str(nf))
            c.set("toLane", str(nt))
            redirigidas += 1
        clave = (origen, nf, destino, nt)
        if clave in vistas:
            raiz.remove(c)
            duplicadas += 1
        else:
            vistas.add(clave)
    return vistas, redirigidas, duplicadas


def _copiar_conexiones(raiz, adiciones, vistas):
    """
    AGREGAR: las conexiones del carril más alto se copian al carril nuevo.
    La copia no lleva tl/linkIndex (esos los agrega extender_semaforos). Regresa cuántas copió.
    """
    copiadas = 0
    for c in list(raiz.findall("connection")):
        if not _es_del_carril_mas_alto(c, adiciones):
            continue
        origen = c.get("from")
        for k in range(1, adiciones[origen][1] - adiciones[origen][0] + 1):
            nf = adiciones[origen][0] - 1 + k
            nt = lane_destino(c, adiciones, k)
            clave = (origen, nf, c.get("to"), nt)
            if clave in vistas:
                continue
            copia = dict(c.attrib)
            copia["fromLane"], copia["toLane"] = str(nf), str(nt)
            copia.pop("tl", None)
            copia.pop("linkIndex", None)
            ET.SubElement(raiz, "connection", copia)
            vistas.add(clave)
            copiadas += 1
    return copiadas


def reconectar(archivo_con, nuevos, reporte):
    """Reduce (redirige) y agrega (copia) conexiones en el .con.xml. Anota el resumen en el reporte."""
    reducciones, adiciones = dividir_cambios(nuevos)
    resumen = reporte["resumen"]
    if not reducciones and not adiciones:
        resumen.update(conexiones_copiadas=0, conexiones_redirigidas=0, conexiones_duplicadas_eliminadas=0)
        return

    arbol = ET.parse(archivo_con)
    raiz = arbol.getroot()
    vistas, redirigidas, duplicadas = _redirigir_conexiones(raiz, reducciones)
    copiadas = _copiar_conexiones(raiz, adiciones, vistas)
    arbol.write(archivo_con, encoding="utf-8", xml_declaration=True)

    resumen.update(conexiones_copiadas=copiadas, conexiones_redirigidas=redirigidas,
                   conexiones_duplicadas_eliminadas=duplicadas)


# ---------------------------------------------------------------------
# .tll.xml: extender el programa de los semáforos (solo al AGREGAR carriles)
# ---------------------------------------------------------------------
def _siguiente_link_index(conexiones):
    """{semáforo: primer linkIndex libre}."""
    siguiente = {}
    for c in conexiones:
        tl = c.get("tl")
        siguiente[tl] = max(siguiente.get(tl, 0), int(c.get("linkIndex")) + 1)
    return siguiente


def _agregar_enlaces(raiz, conexiones, adiciones):
    """
    Agrega al .tll.xml un enlace nuevo por cada conexión controlada que se copia al carril nuevo.
    Regresa {semáforo: [linkIndex de origen, en el orden en que se agregaron los nuevos]}.
    """
    siguiente = _siguiente_link_index(conexiones)
    existentes = {(c.get("from"), c.get("fromLane"), c.get("to"), c.get("toLane"), c.get("tl"))
                  for c in conexiones}
    copiar_de = {}
    for c in conexiones:
        if not _es_del_carril_mas_alto(c, adiciones):
            continue
        origen, tl = c.get("from"), c.get("tl")
        for k in range(1, adiciones[origen][1] - adiciones[origen][0] + 1):
            nf, nt = adiciones[origen][0] - 1 + k, lane_destino(c, adiciones, k)
            if (origen, str(nf), c.get("to"), str(nt), tl) in existentes:
                continue
            copia = dict(c.attrib)
            copia["fromLane"], copia["toLane"] = str(nf), str(nt)
            copia["linkIndex"] = str(siguiente[tl])
            siguiente[tl] += 1
            copiar_de.setdefault(tl, []).append(int(c.get("linkIndex")))
            ET.SubElement(raiz, "connection", copia)
    return copiar_de


def _extender_fases(raiz, copiar_de):
    """Cada fase gana un carácter por enlace nuevo, copiado del enlace del carril vecino."""
    for logica in raiz.findall("tlLogic"):
        extra = copiar_de.get(logica.get("id"), [])
        for fase in logica.findall("phase"):
            estado = fase.get("state")
            fase.set("state", estado + "".join(estado[i] for i in extra))


def extender_semaforos(archivo_tll, nuevos, reporte):
    """Extiende los semáforos que controlan carriles recién agregados. Anota el resumen en el reporte."""
    _, adiciones = dividir_cambios(nuevos)
    if not archivo_tll or not adiciones:
        reporte["resumen"]["enlaces_semaforo_nuevos"] = {}
        return

    arbol = ET.parse(archivo_tll)
    raiz = arbol.getroot()
    conexiones = raiz.findall("connection")      # solo las originales (antes de agregar)
    copiar_de = _agregar_enlaces(raiz, conexiones, adiciones)
    _extender_fases(raiz, copiar_de)
    arbol.write(archivo_tll, encoding="utf-8", xml_declaration=True)

    reporte["resumen"]["enlaces_semaforo_nuevos"] = {tl: len(v) for tl, v in copiar_de.items()}


# ---------------------------------------------------------------------
# .tll.xml: reinterpretar el semáforo al REDUCIR carriles
# ---------------------------------------------------------------------
# Idea: cuando desaparece un carril, el enlace que lo controlaba tiene que cambiar.
#   - Si al moverlo al carril que queda resulta IGUAL a un enlace que ya existía, se BORRA
#     (ese tráfico usa la luz del carril vecino).
#   - Si no, se MUEVE al carril que queda y conserva su luz.
#   - Por cada enlace borrado: cada fase pierde ese carácter y los enlaces siguientes se renumeran.
def _destino_reducido(c, reducciones):
    """(fromLane, toLane, nuevo fromLane, nuevo toLane) de una conexión tras la reducción."""
    origen, destino = c.get("from"), c.get("to")
    f, t = int(c.get("fromLane")), int(c.get("toLane"))
    nf = min(f, reducciones[origen][1] - 1) if origen in reducciones else f
    nt = min(t, reducciones[destino][1] - 1) if destino in reducciones else t
    return f, t, nf, nt


def _mover_o_borrar_enlaces(raiz, conexiones, reducciones):
    """Mueve o borra los enlaces afectados. Regresa (movidos {tl: n}, borrados {tl: {linkIndex}})."""
    vistas = set()                                   # enlaces que NO cambian: para detectar duplicados
    for c in conexiones:
        f, t, nf, nt = _destino_reducido(c, reducciones)
        if (f, t) == (nf, nt):
            vistas.add((c.get("tl"), c.get("from"), f, c.get("to"), t))

    movidos, borrados = {}, {}
    for c in conexiones:
        f, t, nf, nt = _destino_reducido(c, reducciones)
        if (f, t) == (nf, nt):
            continue
        tl = c.get("tl")
        clave = (tl, c.get("from"), nf, c.get("to"), nt)
        if clave in vistas:                          # duplicado -> se borra
            borrados.setdefault(tl, set()).add(int(c.get("linkIndex")))
            raiz.remove(c)
        else:                                        # se mueve y conserva su luz
            c.set("fromLane", str(nf))
            c.set("toLane", str(nt))
            vistas.add(clave)
            movidos[tl] = movidos.get(tl, 0) + 1
    return movidos, borrados


def _renumerar_enlaces(raiz, borrados):
    """Los enlaces que quedan bajan de número tantas posiciones como enlaces borrados haya antes."""
    for tl, indices in borrados.items():
        for c in raiz.findall("connection"):
            if c.get("tl") == tl:
                li = int(c.get("linkIndex"))
                c.set("linkIndex", str(li - sum(1 for b in indices if b < li)))


def _quitar_caracteres_de_fases(raiz, borrados):
    """Cada fase pierde el carácter de cada enlace borrado."""
    for logica in raiz.findall("tlLogic"):
        indices = borrados.get(logica.get("id"), set())
        if not indices:
            continue
        for fase in logica.findall("phase"):
            estado = fase.get("state")
            fase.set("state", "".join(ch for i, ch in enumerate(estado) if i not in indices))


def _reinterpretar_enlaces(raiz, reducciones):
    """Hace los tres pasos sobre el .tll.xml en memoria. Regresa (movidos, borrados)."""
    movidos, borrados = _mover_o_borrar_enlaces(raiz, raiz.findall("connection"), reducciones)
    _renumerar_enlaces(raiz, borrados)
    _quitar_caracteres_de_fases(raiz, borrados)
    return movidos, borrados


def _incoherencias(raiz, semaforos):
    """Revisa los semáforos tocados: números de enlace repetidos o fuera del largo del state."""
    problemas = []
    for logica in raiz.findall("tlLogic"):
        tl = logica.get("id")
        if tl not in semaforos:
            continue
        indices = [int(c.get("linkIndex")) for c in raiz.findall("connection") if c.get("tl") == tl]
        if len(indices) != len(set(indices)):
            problemas.append(f"{tl}: dos enlaces quedarían con el mismo número")
        largo = min(len(f.get("state")) for f in logica.findall("phase"))
        if indices and max(indices) >= largo:
            problemas.append(f"{tl}: un enlace quedaría fuera del largo del state")
    return problemas


def problemas_al_reducir(raiz_tll, reducciones):
    """
    PROTECCIÓN: prueba la reinterpretación en una COPIA del .tll.xml (no toca nada) y regresa
    la lista de motivos por los que el semáforo quedaría incoherente (vacía si todo cuadra).
    """
    copia = copy.deepcopy(raiz_tll)
    movidos, borrados = _reinterpretar_enlaces(copia, reducciones)
    return _incoherencias(copia, set(movidos) | set(borrados))


def reducir_semaforos(archivo_tll, nuevos, reporte):
    """Reinterpreta los semáforos afectados por una reducción de carriles. Anota el resumen."""
    reducciones, _ = dividir_cambios(nuevos)
    resumen = reporte["resumen"]
    if not archivo_tll or not reducciones:
        resumen.update(enlaces_semaforo_movidos={}, enlaces_semaforo_borrados={})
        return

    arbol = ET.parse(archivo_tll)
    movidos, borrados = _reinterpretar_enlaces(arbol.getroot(), reducciones)
    arbol.write(archivo_tll, encoding="utf-8", xml_declaration=True)
    resumen.update(enlaces_semaforo_movidos=movidos,
                   enlaces_semaforo_borrados={tl: len(v) for tl, v in borrados.items()})