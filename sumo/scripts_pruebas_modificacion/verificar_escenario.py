"""
Compara la red base contra la red de un escenario y reporta qué cambió de verdad.

Uso (desde la carpeta sumo/):
    python verificar_escenario.py <escenario_id> [proyecto_id]
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

FUNCIONES_NO_VIALES = ("internal", "crossing", "walkingarea")


def leer_red(ruta):
    root = ET.parse(ruta).getroot()

    edges = {}
    for e in root.findall("edge"):
        if e.get("function") in FUNCIONES_NO_VIALES:
            continue
        lanes = e.findall("lane")
        edges[e.get("id")] = {
            "carriles": len(lanes),
            "velocidades": sorted({round(float(l.get("speed")) * 3.6, 1) for l in lanes}),
        }

    # Conexiones por carril (salientes y entrantes) y número de enlaces por semáforo
    salientes, entrantes, enlaces = {}, {}, {}
    controladas = set()   # carriles con alguna conexión saliente que el semáforo controla
    for c in root.findall("connection"):
        origen, destino = c.get("from"), c.get("to")
        if origen in edges:
            k = (origen, int(c.get("fromLane")))
            salientes[k] = salientes.get(k, 0) + 1

        if c.get("tl") and origen in edges:
            controladas.add((origen, int(c.get("fromLane"))))

        if destino in edges:
            k = (destino, int(c.get("toLane")))
            entrantes[k] = entrantes.get(k, 0) + 1
        tl = c.get("tl")
        if tl and c.get("linkIndex") is not None:
            enlaces[tl] = max(enlaces.get(tl, 0), int(c.get("linkIndex")) + 1)

    tls = {}
    for t in root.findall("tlLogic"):
        tls[t.get("id")] = {
            "tipo": t.get("type"),
            "fases": [(int(float(p.get("duration"))), p.get("state")) for p in t.findall("phase")],
        }
    return {"edges": edges, "salientes": salientes, "entrantes": entrantes,
            "enlaces": enlaces, "tls": tls, "controladas": controladas}


def comparar_calles(base, esc):
    print("=== CALLES ===")
    cambios = 0
    for eid, e in esc["edges"].items():
        b = base["edges"].get(eid)
        if b is None:
            print(f"  {eid}: NUEVA (no existe en la base)")
            cambios += 1
            continue
        if e["carriles"] != b["carriles"] or e["velocidades"] != b["velocidades"]:
            cambios += 1
            print(f"  {eid}: carriles {b['carriles']} -> {e['carriles']} | "
            f"velocidad {b['velocidades']} -> {e['velocidades']} km/h")
    for eid in base["edges"]:
        if eid not in esc["edges"]:
            print(f"  {eid}: DESAPARECIÓ en el escenario")
            cambios += 1
    if cambios == 0:
        print("  Sin diferencias.")

def comparar_conexiones(base, esc):
    print("\n=== CONEXIONES (contra la base) ===")
    problemas = 0
    for eid, e in esc["edges"].items():
        b = base["edges"].get(eid)
        if b is None:
            continue
        for i in range(e["carriles"]):
            for sentido, clave in (("salida", "salientes"), ("entrada", "entrantes")):
                antes = base[clave].get((eid, i), 0) if i < b["carriles"] else None
                ahora = esc[clave].get((eid, i), 0)
                if antes is None and ahora == 0:
                    print(f"  {eid} carril {i}: carril NUEVO sin conexión de {sentido} "
                        f"(si es 'entrada' en el borde de la red, puede ser normal)")
                    problemas += 1
                elif antes and ahora == 0:
                    print(f"  {eid} carril {i}: DAÑO, tenía {antes} conexión(es) de {sentido} y ahora ninguna")
                    problemas += 1
    if problemas == 0:
        print("  Sin problemas de conexiones.")


def comparar_control(base, esc):
    """
    Marca los carriles que tienen conexiones pero no control semafórico, cuando:
    - son nuevos (no existían en la base), o
    - sí estaban controlados en la base.
    Solo se revisan tramos que tienen al menos un carril controlado.
    """
    print("\n=== CONTROL SEMAFÓRICO (contra la base) ===")
    problemas = 0
    for eid, e in esc["edges"].items():
        if not any((eid, i) in esc["controladas"] for i in range(e["carriles"])):
            continue
        b = base["edges"].get(eid)
        carriles_base = b["carriles"] if b else 0
        for i in range(e["carriles"]):
            if esc["salientes"].get((eid, i), 0) == 0 or (eid, i) in esc["controladas"]:
                continue
            if i >= carriles_base:
                print(f"  PROBLEMA {eid} carril {i}: carril NUEVO con conexiones pero SIN control "
                    f"semafórico (sus vecinos sí): los vehículos no respetarían el semáforo")
                problemas += 1
            elif (eid, i) in base["controladas"]:
                print(f"  PROBLEMA {eid} carril {i}: PERDIÓ el control semafórico que tenía en la base")
                problemas += 1
    if problemas == 0:
        print("  Sin problemas de control semafórico.")


def comparar_semaforos(base, esc):
    print("\n=== SEMÁFOROS ===")
    cambios = 0
    for tid, t in esc["tls"].items():
        b = base["tls"].get(tid)
        if b is None:
            print(f"  {tid}: NUEVO (no existe en la base)")
            cambios += 1
            continue
        dur_b = [d for d, _ in b["fases"]]
        dur_e = [d for d, _ in t["fases"]]
        est_b = [s for _, s in b["fases"]]
        est_e = [s for _, s in t["fases"]]
        if t["tipo"] != b["tipo"] or dur_b != dur_e or est_b != est_e:
            cambios += 1
            print(f"  {tid}: tipo {b['tipo']} -> {t['tipo']}")
            print(f"      duraciones {dur_b} (ciclo {sum(dur_b)} s) -> {dur_e} (ciclo {sum(dur_e)} s)")
            if est_b != est_e:
                print("      AVISO: cambiaron los estados de las fases")
    if cambios == 0:
        print("  Sin diferencias.")

    # Consistencia: cada fase debe tener un carácter por enlace que controla el semáforo
    problemas = 0
    for tid, t in esc["tls"].items():
        n = esc["enlaces"].get(tid)
        largos = {len(s) for _, s in t["fases"]}
        if n is not None and largos != {n}:
            problemas += 1
            print(f"  PROBLEMA en {tid}: el semáforo controla {n} enlaces pero sus fases "
                f"tienen estados de longitud {sorted(largos)}")
    if problemas == 0:
        print("  Consistencia state/enlaces: OK en todos los semáforos.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit()

    escenario_id = sys.argv[1]
    proyecto_id = sys.argv[2] if len(sys.argv) > 2 else "3"
    carpeta = Path("data/proyectos") / proyecto_id
    ruta_base = carpeta / "red_base.net.xml"
    ruta_esc = carpeta / "escenarios" / escenario_id / "red_escenario.net.xml"

    if not ruta_esc.exists():
        sys.exit(f"No existe {ruta_esc}. Si el escenario no tenía modificaciones, "
                f"usó la red base directamente y no hay nada que comparar.")

    base = leer_red(ruta_base)
    esc = leer_red(ruta_esc)
    print(f"Comparando {ruta_base.name} contra {ruta_esc}\n")
    comparar_calles(base, esc)
    comparar_conexiones(base, esc)
    comparar_control(base, esc)
    comparar_semaforos(base, esc)