"""
escenario_semaforos.py: cambios en la DURACIÓN de las fases de un semáforo (.tll.xml).

Un semáforo tiene un programa de fases; cada fase tiene una duración y un `state`
(un carácter por enlace: G verde, r rojo, y amarillo).
    <tlLogic id="T" type="actuated"><phase duration="30" state="GG"/>...</tlLogic>

Todo lo que no es válido se RECHAZA con un motivo en vez de ignorarse en silencio.
"""
import xml.etree.ElementTree as ET


def _rechazar(reporte, tls_id, motivo):
    reporte["rechazados"].append({"tipo": "semaforo", "id": tls_id, "motivo": motivo})


def _cambiar_duracion(fase_el, duracion, indice, tls_id, reporte):
    """Cambia la duración si es válida (>= 1 s). Regresa 1 si cambió, 0 si no."""
    if int(duracion) < 1:
        _rechazar(reporte, tls_id, f"fase {indice}: la duración debe ser de al menos 1 s")
        return 0
    fase_el.set("duration", str(int(duracion)))
    return 1


def _cambiar_estado(fase_el, estado, indice, tls_id, reporte):
    """Cambia el state si tiene un carácter por enlace. Regresa 1 si cambió, 0 si no."""
    esperados = len(fase_el.get("state"))
    if len(estado) != esperados:
        _rechazar(reporte, tls_id, f"fase {indice}: el estado debe tener {esperados} caracteres")
        return 0
    fase_el.set("state", estado)
    return 1


def _aplicar_fases(logica, tls_id, fases_pedidas, reporte):
    """Aplica los cambios pedidos a las fases de un semáforo. Regresa cuántos cambios se hicieron."""
    fases = logica.findall("phase")
    cambiadas = 0
    for pedida in fases_pedidas:
        i = pedida.get("indice")
        if not isinstance(i, int) or not 0 <= i < len(fases):
            _rechazar(reporte, tls_id, f"la fase {i} no existe (el programa tiene {len(fases)} fases)")
            continue
        if pedida.get("duracion") is not None:
            cambiadas += _cambiar_duracion(fases[i], pedida["duracion"], i, tls_id, reporte)
        if pedida.get("estado") is not None:
            cambiadas += _cambiar_estado(fases[i], pedida["estado"], i, tls_id, reporte)
    return cambiadas


def aplicar_modificaciones(archivo_tll, modificaciones, reporte):
    """
    Aplica las modificaciones de semáforos y las anota en el reporte.
    Un semáforo editado pasa de "actuado" a tiempo fijo: lo que se escribe es lo que corre.
    """
    if not archivo_tll:
        for m in modificaciones:
            _rechazar(reporte, m.get("tls_id"), "la red no tiene semáforos")
        return

    arbol = ET.parse(archivo_tll)
    por_id = {t.get("id"): t for t in arbol.getroot().findall("tlLogic")}

    for cambio in modificaciones:
        tls_id = cambio["tls_id"]
        logica = por_id.get(tls_id)
        if logica is None:
            _rechazar(reporte, tls_id,
                    "no existe en la red (netconvert no construye semáforos que no controlan ningún enlace)")
            continue
        cambiadas = _aplicar_fases(logica, tls_id, cambio.get("fases", []), reporte)
        if cambiadas:
            logica.set("type", "static")
            reporte["aplicados"].append({"tipo": "semaforo", "id": tls_id, "cambios": cambiadas,
                                        "nota": "pasa a tiempo fijo"})

    arbol.write(archivo_tll, encoding="utf-8", xml_declaration=True)
