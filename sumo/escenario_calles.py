"""
escenario_calles.py: cambios en las CALLES (carriles y velocidad).

Trabaja sobre el archivo plano .edg.xml, donde cada <edge> es un tramo de calle:
    <edge id="128255275#0" numLanes="3" speed="39.44" .../>

Flujo: PLANEAR (decidir qué se cambia y qué se rechaza, sin tocar nada)
    y luego APLICAR (escribir los cambios en el .edg.xml).
"""
import xml.etree.ElementTree as ET

from escenario_conexiones import problemas_al_reducir


# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------
def pertenece_a_via(edge_id, id_base):
    """
    ¿Este tramo pertenece a la vía `id_base`?
    netconvert parte una vía de OSM en tramos: "128255275" -> "128255275#0", "#1"...
    (con "-" al inicio en el sentido contrario). Una vía = todos sus tramos.
    """
    if edge_id == id_base or edge_id == f"-{id_base}":
        return True
    return edge_id.startswith(f"{id_base}#") or edge_id.startswith(f"-{id_base}#")


def delta_carriles(m, tramos, originales):
    """
    Cuántos carriles agregar (+) o quitar (-) en cada tramo.
    - "carriles_extra": ya viene relativo.
    - "carriles" (número absoluto, formato viejo del frontend): se convierte a relativo
        usando el primer tramo de la vía como referencia.
    """
    if m.get("carriles_extra") is not None:
        return int(m["carriles_extra"])
    if m.get("carriles") is not None:
        referencia = next((t for t in tramos if not t.startswith("-")), tramos[0])
        return int(m["carriles"]) - originales[referencia]
    return 0


def _rechazar(reporte, via, motivo):
    reporte["rechazados"].append({"tipo": "calle", "id": via, "motivo": motivo})


def _leer_tll(archivo_tll):
    """El .tll.xml completo en memoria (solo lectura), o None si la red no tiene semáforos."""
    return ET.parse(archivo_tll).getroot() if archivo_tll else None


# ---------------------------------------------------------------------
# PLANEAR (no modifica ningún archivo)
# ---------------------------------------------------------------------
def planear_cambios(modificaciones, originales, raiz_tll, reporte):
    """
    Regresa (nuevos, velocidades, detalle):
        nuevos     {tramo: (carriles_antes, carriles_despues)}
        velocidades{tramo: (vía, km/h)}
        detalle    {vía: info para el reporte}
    Las vías que no existen o que no se pueden cambiar se anotan como rechazadas.
    """
    nuevos, velocidades, detalle = {}, {}, {}
    for m in modificaciones:
        
        if m.get("tramos"):                      # tramos concretos: ["8640976#10"]
            via = "+".join(m["tramos"])          # etiqueta para el reporte
            faltan = [t for t in m["tramos"] if t not in originales]
            if faltan:
                _rechazar(reporte, via, f"estos tramos no existen en la red: {faltan}")
                continue
            tramos = sorted(m["tramos"])
        else:                                    # vía completa: "8640976"
            via = m["edge_id"]
            tramos = sorted(t for t in originales if pertenece_a_via(t, via))
            if not tramos:
                _rechazar(reporte, via, "esa vía no existe en la red")
                continue

        
        info = detalle.setdefault(via, {"tipo": "calle", "id": via})

        plan = _plan_de_carriles(m, tramos, originales, raiz_tll, via, reporte)
        if plan:
            nuevos.update(plan)
            info["tramos"] = {t: list(p) for t, p in plan.items()}
    return nuevos, velocidades, detalle


def _plan_de_carriles(m, tramos, originales, raiz_tll, via, reporte):
    """
    {tramo: (antes, despues)} para esta vía, o {} si no hay nada que cambiar o se rechaza.
    Regla de seguridad: reducir se rechaza SOLO si el semáforo quedaría incoherente.
    """
    delta = delta_carriles(m, tramos, originales)
    if delta == 0:
        return {}

    plan = {t: (originales[t], max(1, originales[t] + delta)) for t in tramos}   # mínimo 1 carril
    plan = {t: p for t, p in plan.items() if p[0] != p[1]}                       # quita tramos sin cambio
    if not plan:
        _rechazar(reporte, via, "la vía ya tiene el mínimo de carriles (1)")
        return {}

    if delta < 0 and raiz_tll is not None:
        problemas = problemas_al_reducir(raiz_tll, plan)
        if problemas:
            _rechazar(reporte, via,
                    "reducir carriles aquí dejaría incoherente el programa del semáforo ("
                    + "; ".join(problemas) + "). Los carriles de esta vía quedan sin cambios.")
            return {}
    return plan


# ---------------------------------------------------------------------
# APLICAR (escribe en el .edg.xml)
# ---------------------------------------------------------------------
def aplicar_carriles(tramos_por_id, nuevos):
    """Pone el nuevo numLanes y borra los <lane> sueltos que ya no existen."""
    for t, (antes, despues) in nuevos.items():
        tramo = tramos_por_id[t]
        tramo.set("numLanes", str(despues))
        for lane in list(tramo.findall("lane")):
            if int(lane.get("index", "0")) >= despues:
                tramo.remove(lane)


def aplicar_velocidades(tramos_por_id, velocidades, detalle):
    """Velocidad en km/h -> m/s (SUMO usa m/s). También en los <lane> con velocidad propia."""
    for t, (via, kmh) in velocidades.items():
        tramo = tramos_por_id[t]
        ms = kmh / 3.6
        if abs(float(tramo.get("speed", 0)) - ms) > 0.01:
            detalle[via]["velocidad_km_h"] = kmh                    # hubo cambio real
        tramo.set("speed", f"{ms:.2f}")
        for lane in tramo.findall("lane"):
            if lane.get("speed") is not None:                       # si no, pisaría la del tramo
                lane.set("speed", f"{ms:.2f}")


# ---------------------------------------------------------------------
# Función principal del módulo
# ---------------------------------------------------------------------
def aplicar_cambios_en_calles(archivo_edg, archivo_tll, modificaciones, reporte):
    """
    Planea y aplica los cambios de carriles/velocidad, y anota el resultado en el reporte.
    Regresa `nuevos` ({tramo: (antes, despues)}), que el siguiente paso usa para reconectar.
    """
    arbol = ET.parse(archivo_edg)
    tramos_por_id = {e.get("id"): e for e in arbol.getroot().findall("edge")}
    originales = {t: int(e.get("numLanes")) for t, e in tramos_por_id.items()}

    nuevos, velocidades, detalle = planear_cambios(
        modificaciones, originales, _leer_tll(archivo_tll), reporte)

    aplicar_carriles(tramos_por_id, nuevos)
    aplicar_velocidades(tramos_por_id, velocidades, detalle)
    arbol.write(archivo_edg, encoding="utf-8", xml_declaration=True)

    for info in detalle.values():
        if "tramos" in info or "velocidad_km_h" in info:
            reporte["aplicados"].append(info)
    return nuevos