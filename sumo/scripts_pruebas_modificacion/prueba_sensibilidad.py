"""
Pruebas de validación del pipeline de escenarios contra server.py.

Uso (desde la carpeta sumo/, con server.py corriendo):
    python prueba_sensibilidad.py fases     # muestra el plan del semáforo y la vía de control
    python prueba_sensibilidad.py correr    # corre los 4 escenarios y los compara
"""
import json
import sys
import xml.etree.ElementTree as ET

import requests

URL = "http://localhost:8000"
RUTA_NET = "data/proyectos/3/red_base.net.xml"

DEMANDA = 900            # veh/h
PESADOS = 10             # % de camiones
TLS_ID = "cluster_11514661659_372948820_372948824"   # semáforo con ~218 veh en la corrida base
EDGE_CONTROL = "128255275"                           # vía para el control de reconstrucción
VERDE_MALO_S = 5         # duración de cada fase verde en el escenario de sensibilidad


def _pertenece_a_via(edge_id, id_base):
    # Misma regla que scenario_builder.py
    if edge_id == id_base or edge_id == f"-{id_base}":
        return True
    return edge_id.startswith(f"{id_base}#") or edge_id.startswith(f"-{id_base}#")


def leer_fases(tls_id):
    root = ET.parse(RUTA_NET).getroot()
    for tl in root.findall("tlLogic"):
        if tl.get("id") == tls_id:
            fases = [(i, int(float(p.get("duration"))), p.get("state"))
                     for i, p in enumerate(tl.findall("phase"))]
            return tl.get("type"), fases
    raise SystemExit(f"No encontré el semáforo {tls_id} en {RUTA_NET}")


def leer_via(id_base):
    root = ET.parse(RUTA_NET).getroot()
    segmentos = []
    for e in root.findall("edge"):
        lanes = e.findall("lane")
        if e.get("function") == "internal" or not lanes:
            continue
        if _pertenece_a_via(e.get("id"), id_base):
            segmentos.append((e.get("id"), len(lanes), round(float(lanes[0].get("speed")) * 3.6, 2)))
    return segmentos


def vias_uniformes():
    """
    Vías (id base, ambos sentidos) cuyos segmentos tienen todos el mismo
    número de carriles y la misma velocidad. Sirven como vía de control,
    porque reaplicar sus propios valores no cambia nada.
    Regresa [(id_base, carriles, km/h, largo_total_m)], de mayor a menor largo.
    """
    root = ET.parse(RUTA_NET).getroot()
    grupos = {}
    for e in root.findall("edge"):
        lanes = e.findall("lane")
        if e.get("function") == "internal" or not lanes:
            continue
        base = e.get("id").lstrip("-").split("#")[0]
        g = grupos.setdefault(base, {"firmas": set(), "largo": 0.0})
        g["firmas"].add((len(lanes), round(float(lanes[0].get("speed")) * 3.6, 2)))
        g["largo"] += float(lanes[0].get("length", 0))

    candidatas = [
        (base, next(iter(g["firmas"]))[0], next(iter(g["firmas"]))[1], g["largo"])
        for base, g in grupos.items()
        if len(g["firmas"]) == 1 and next(iter(g["firmas"]))[0] >= 2
    ]
    return sorted(candidatas, key=lambda c: -c[3])


def mostrar():
    tipo, fases = leer_fases(TLS_ID)
    print(f"Semáforo {TLS_ID} (tipo {tipo}):")
    for i, dur, estado in fases:
        print(f"  fase {i}: {dur:>3} s  {estado}")
    print(f"\nVía {EDGE_CONTROL}:")
    segmentos = leer_via(EDGE_CONTROL)
    if not segmentos:
        print("  No se encontraron segmentos con ese id.")
    for seg_id, carriles, vel in segmentos:
        print(f"  {seg_id}: {carriles} carriles, {vel} km/h")


def post(ruta, cuerpo=None):
    r = requests.post(URL + ruta, json=cuerpo or {}, timeout=3600)
    r.raise_for_status()
    return r.json()


def patch(ruta, cuerpo):
    r = requests.patch(URL + ruta, json=cuerpo, timeout=60)
    r.raise_for_status()
    return r.json()


def correr_escenario(id_, nombre, edges=None, fases_tls=None):
    post("/escenario/reset")
    post("/escenario", {"id": id_, "nombre": nombre,
                        "demanda_vehicular": DEMANDA, "porcentaje_pesados": PESADOS})
    for e in edges or []:
        patch(f"/infraestructura/{e['edge_id']}",
              {"carriles": e["carriles"], "velocidad_max": e["velocidad_max"]})
    if fases_tls:
        patch(f"/semaforo/{TLS_ID}", {"fases": fases_tls})
    print(f"\n>>> Simulando: {nombre} (id {id_})")
    return post("/simular")


def main_correr():
    _, fases = leer_fases(TLS_ID)
    plan_original = [{"indice": i, "duracion": d} for i, d, _ in fases]
    plan_malo = [{"indice": i,
                  "duracion": VERDE_MALO_S if any(c in "Gg" for c in estado) else d}
                 for i, d, estado in fases]

    segmentos = leer_via(EDGE_CONTROL)
    if segmentos and len({(n, v) for _, n, v in segmentos}) == 1:
        id_control = EDGE_CONTROL
    else:
        candidatas = vias_uniformes()
        if not candidatas:
            raise SystemExit("No hay ninguna vía con segmentos uniformes para usar como control.")
        id_control, _, _, largo = candidatas[0]
        print(f"La vía {EDGE_CONTROL} no es uniforme; se usa {id_control} como control "
              f"({largo:.0f} m de longitud total).")
        segmentos = leer_via(id_control)
    _, carriles, vel = segmentos[0]
    edge_control = {"edge_id": id_control, "carriles": carriles, "velocidad_max": vel}
    print(f"Vía de control: {id_control} ({carriles} carriles, {vel} km/h)")
    
    resultados = [
        ("E1 Base", correr_escenario(21, "E1 Base")),
        ("E2 Control reconstruccion", correr_escenario(22, "E2 Control reconstruccion", edges=[edge_control])),
        ("E3 Control estatico", correr_escenario(23, "E3 Control estatico", fases_tls=plan_original)),
        ("E4 Sensibilidad", correr_escenario(24, "E4 Sensibilidad", fases_tls=plan_malo)),
    ]

    with open("resultados_prueba.json", "w", encoding="utf-8") as f:
        json.dump(dict(resultados), f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 100)
    print(f"{'Escenario':<27}{'Veh':>5}{'Espera':>8}{'Vel':>8}{'Fila':>8}{'Perdido':>9}"
          f"{'Veh@TLS':>9}{'Retr@TLS':>10}")
    print("=" * 100)
    for nombre, r in resultados:
        s = (r.get("semaforos") or {}).get(TLS_ID, {})
        print(f"{nombre:<27}{r['vehiculos_atendidos']:>5}{r['tiempo_promedio_espera']:>8}"
              f"{r['velocidad_promedio']:>8}{r['longitud_max_fila']:>8}{r['tiempo_perdido_promedio']:>9}"
              f"{s.get('vehiculos', '-'):>9}{s.get('retraso_promedio_s', '-'):>10}")
    print("=" * 100)
    print("Resultados completos guardados en resultados_prueba.json")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fases":
        mostrar()
    elif len(sys.argv) > 1 and sys.argv[1] == "correr":
        main_correr()
    else:
        print(__doc__)