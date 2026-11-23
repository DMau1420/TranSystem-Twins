"""
escenario_demanda.py: DEMANDA como FLUJOS EXPLÍCITOS.

Un flujo dice: "de A a B pasan N vehículos por hora, y P % son pesados".
    {"id": "AB", "origen": "128250766#0", "destino": "128250766#3",
     "vehiculos_por_hora": 5000, "porcentaje_pesados": 10, "via": []}

- origen / destino / via: id de TRAMO de la red (los tramos de una vía se llaman "128250766#0", "#1"...).
- La ruta es el camino más corto por distancia entre los puntos (origen, via..., destino).
  Si el flujo lleva camiones, la ruta evita tramos donde no pueden circular.
- Los autos y los camiones salen como dos flujos separados, así el porcentaje es EXACTO:
  5000 veh/h con 10 % -> 4500 autos/h y 500 camiones/h.

Si el escenario no trae "flujos", se usa la demanda aleatoria de antes (data_generators.py).
Todo lo que no se puede aplicar queda en reporte_demanda.json con su motivo.
"""
import heapq
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

NO_VIALES = ("internal", "crossing", "walkingarea")

# Mismos valores que los tipos de data_generators.py
TIPOS_VEHICULO = {
    "auto":   {"vClass": "passenger", "length": "4.5", "width": "1.8",
               "maxSpeed": "33.33", "accel": "2.6", "decel": "4.5"},
    "camion": {"vClass": "truck", "length": "12", "width": "2.5",
               "maxSpeed": "25", "accel": "1.3", "decel": "4.0"},
}


# =====================================================================
# PUNTO DE ENTRADA
# =====================================================================
def generar_demanda(escenario, ruta_red, carpeta, herramientas):
    """Regresa la ruta del .rou.xml del escenario (flujos explícitos o, si no hay, viajes aleatorios)."""
    if not escenario.get("flujos"):
        from data_generators import generar_rutas_aleatorias
        return generar_rutas_aleatorias(
            herramientas["random_trips"], ruta_red, escenario["demanda_vehicular"], carpeta,
            porcentaje_pesados=escenario.get("porcentaje_pesados", 0))

    ruta_rou, _ = generar_flujos(
        escenario["flujos"], ruta_red, carpeta,
        inicio_s=escenario.get("inicio_s", 0), fin_s=escenario.get("fin_s", 3600),
        porcentaje_pesados_global=escenario.get("porcentaje_pesados", 0))
    return ruta_rou


def generar_flujos(flujos, ruta_red, carpeta, inicio_s=0, fin_s=3600, porcentaje_pesados_global=0,
                   nombre_archivo="demanda.rou.xml"):
    """Valida los flujos, calcula sus rutas y escribe el .rou.xml. Regresa (ruta_rou, reporte)."""
    carpeta = Path(carpeta)
    reporte = {"aplicados": [], "rechazados": []}
    red = _leer_red(ruta_red)

    usados = set()
    for flujo in flujos:
        plan = _planear_flujo(flujo, red, porcentaje_pesados_global, inicio_s, fin_s, usados, reporte)
        if plan:
            reporte["aplicados"].append(plan)

    _guardar_reporte(carpeta, reporte)
    _imprimir_reporte(reporte)
    if not reporte["aplicados"]:
        raise ValueError("Ningún flujo se pudo aplicar: "
                         + "; ".join(f"{r['id']}: {r['motivo']}" for r in reporte["rechazados"]))

    ruta_rou = carpeta / nombre_archivo
    _escribir_rou(reporte["aplicados"], inicio_s, fin_s, ruta_rou)
    return ruta_rou, reporte


# =====================================================================
# PLANEAR: validar un flujo y calcular su ruta
# =====================================================================
def _planear_flujo(f, red, pct_global, inicio_s, fin_s, usados, reporte):
    """Regresa el plan del flujo (dict) o None si se rechaza (y lo anota en el reporte)."""
    origen, destino = f.get("origen"), f.get("destino")
    fid = _limpiar_id(f.get("id") or f"{origen}_{destino}")
    rechazar = lambda motivo: reporte["rechazados"].append({"id": fid, "motivo": motivo})

    if fid in usados:
        return rechazar("el id del flujo está repetido")
    usados.add(fid)

    try:
        total = float(f["vehiculos_por_hora"])
        pct = float(f.get("porcentaje_pesados", pct_global))
    except (KeyError, TypeError, ValueError):
        return rechazar("faltan o no son números 'vehiculos_por_hora' / 'porcentaje_pesados'")
    if total <= 0:
        return rechazar("vehiculos_por_hora debe ser mayor que 0")
    if not 0 <= pct <= 100:
        return rechazar("porcentaje_pesados debe estar entre 0 y 100")
    if fin_s <= inicio_s:
        return rechazar("el fin de la ventana debe ser posterior al inicio")

    puntos = [origen, *f.get("via", []), destino]
    faltantes = [p for p in puntos if p not in red["largo"]]
    if faltantes:
        return rechazar(f"estos tramos no existen en la red: {faltantes}")
    if origen == destino:
        return rechazar("el origen y el destino son el mismo tramo")

    camiones_h = round(total * pct / 100)
    autos_h = total - camiones_h
    vclass = "truck" if camiones_h > 0 else "passenger"
    ruta, problema = _ruta_por_puntos(red, puntos, vclass)
    if ruta is None:
        return rechazar(problema)

    return {"id": fid, "origen": origen, "destino": destino, "ruta": ruta,
            "vehiculos_por_hora": total, "porcentaje_pesados": pct,
            "autos_por_hora": autos_h, "camiones_por_hora": camiones_h,
            "esperados": round(total * (fin_s - inicio_s) / 3600)}


def _limpiar_id(texto):
    """Solo letras, números y guion bajo (el id forma parte del id de cada vehículo)."""
    return re.sub(r"[^A-Za-z0-9_]", "_", str(texto))


# =====================================================================
# RED Y RUTAS (sin depender de la versión de sumolib)
# =====================================================================
def _leer_red(ruta_red):
    """De la .net.xml saca: largo de cada tramo, a qué tramos sigue, y qué clases de vehículo admite."""
    raiz = ET.parse(ruta_red).getroot()
    largo, admite = {}, {"truck": set(), "passenger": set()}
    for e in raiz.findall("edge"):
        if e.get("function") in NO_VIALES:
            continue
        lanes = e.findall("lane")
        largo[e.get("id")] = float(lanes[0].get("length"))
        for clase in admite:
            if any(_lane_admite(l, clase) for l in lanes):
                admite[clase].add(e.get("id"))
    salientes = {}
    for c in raiz.findall("connection"):
        if c.get("from") in largo and c.get("to") in largo:
            salientes.setdefault(c.get("from"), set()).add(c.get("to"))
    return {"largo": largo, "salientes": salientes, "admite": admite}


def _lane_admite(lane, clase):
    if lane.get("allow") is not None:
        return clase in lane.get("allow").split()
    if lane.get("disallow") is not None:
        return clase not in lane.get("disallow").split()
    return True


def _ruta_por_puntos(red, puntos, vclass):
    """Camino más corto que pasa por los puntos en orden. Regresa (lista_de_tramos, None) o (None, motivo)."""
    ruta = [puntos[0]]
    for a, b in zip(puntos, puntos[1:]):
        camino = _camino_mas_corto(red, a, b, vclass)
        if camino is None:
            quien = "para camiones" if vclass == "truck" else "para autos"
            return None, f"no hay ruta {quien} entre {a} y {b}"
        ruta += camino[1:]
    return ruta, None


def _camino_mas_corto(red, a, b, vclass):
    """Dijkstra por distancia, solo por tramos que admiten la clase de vehículo."""
    admite = red["admite"][vclass]
    if a not in admite or b not in admite:
        return None
    dist, previo, cola = {a: 0.0}, {}, [(0.0, a)]
    while cola:
        d, u = heapq.heappop(cola)
        if u == b:
            camino = [b]
            while camino[-1] != a:
                camino.append(previo[camino[-1]])
            return camino[::-1]
        if d > dist[u]:
            continue
        for v in red["salientes"].get(u, ()):
            if v in admite and d + red["largo"][v] < dist.get(v, float("inf")):
                dist[v] = d + red["largo"][v]
                previo[v] = u
                heapq.heappush(cola, (dist[v], v))
    return None


# =====================================================================
# ESCRIBIR EL .rou.xml
# =====================================================================
def _escribir_rou(planes, inicio_s, fin_s, ruta_rou):
    lineas = ["<routes>"]
    for nombre, atributos in TIPOS_VEHICULO.items():
        lineas.append(f'    <vType id="{nombre}" ' + " ".join(f'{k}="{v}"' for k, v in atributos.items()) + "/>")
    for p in planes:
        lineas.append(f'    <route id="r_{p["id"]}" edges="{" ".join(p["ruta"])}"/>')
    for p in planes:
        for tipo, por_hora in (("auto", p["autos_por_hora"]), ("camion", p["camiones_por_hora"])):
            if por_hora > 0:
                lineas.append(f'    <flow id="{p["id"]}__{tipo}" type="{tipo}" route="r_{p["id"]}" '
                              f'begin="{inicio_s}" end="{fin_s}" vehsPerHour="{por_hora:g}" '
                              f'departLane="free" departSpeed="max"/>')
    lineas.append("</routes>")
    Path(ruta_rou).write_text("\n".join(lineas) + "\n", encoding="utf-8")


# =====================================================================
# RESULTADOS POR FLUJO
# =====================================================================
def indicadores_por_flujo(ruta_tripinfo):
    """
    Indicadores de cada flujo a partir de tripinfo.xml (el reporte_demanda.json está en la misma carpeta).
    tiempo_total = recorrido + espera para poder entrar a la red (por eso no se pierde la cola de entrada).
    """
    carpeta = Path(ruta_tripinfo).parent
    with open(carpeta / "reporte_demanda.json", encoding="utf-8") as f:
        planes = {p["id"]: p for p in json.load(f)["aplicados"]}

    viajes = {fid: [] for fid in planes}
    for v in ET.parse(ruta_tripinfo).getroot().findall("tripinfo"):
        fid = v.get("id").rsplit(".", 1)[0].rsplit("__", 1)[0]
        if fid in viajes:
            viajes[fid].append(v)

    resultado = {}
    for fid, plan in planes.items():
        vs, n = viajes[fid], len(viajes[fid])
        prom = lambda f: round(sum(f(v) for v in vs) / n, 2) if n else None
        resultado[fid] = {
            "origen": plan["origen"], "destino": plan["destino"],
            "vehiculos_esperados": plan["esperados"], "vehiculos_completados": n,
            "camiones_completados": sum(1 for v in vs if v.get("vType") == "camion"),
            "tiempo_total_promedio": prom(lambda v: float(v.get("duration")) + float(v.get("departDelay"))),
            "espera_promedio": prom(lambda v: float(v.get("waitingTime"))),
            "retraso_entrada_promedio": prom(lambda v: float(v.get("departDelay"))),
        }
    return resultado


# =====================================================================
# REPORTE
# =====================================================================
def _guardar_reporte(carpeta, reporte):
    with open(Path(carpeta) / "reporte_demanda.json", "w", encoding="utf-8") as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)


def _imprimir_reporte(reporte):
    print("--- Reporte de demanda ---")
    for p in reporte["aplicados"]:
        print(f"  FLUJO {p['id']}: {p['origen']} -> {p['destino']} | {p['vehiculos_por_hora']:g} veh/h "
              f"({p['autos_por_hora']:g} autos + {p['camiones_por_hora']:g} camiones) | ruta de {len(p['ruta'])} tramos")
    for r in reporte["rechazados"]:
        print(f"  RECHAZADO {r['id']}: {r['motivo']}")