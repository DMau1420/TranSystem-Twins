"""
Prueba de flujo: ¿sirve el carril agregado?

Mete un flujo explícito de vehículos que recorre una vía completa (no viajes aleatorios por toda la
zona) y lo simula en tres redes, con la misma demanda y semilla:
  A. Red original (semáforos actuados)
  B. Base en tiempo fijo (reconstruida con el mismo método que los escenarios editados)
  C. Tiempo fijo + 1 carril agregado a la vía

Uso (desde sumo/):
    python probar_flujo.py [via] [demandas en veh/h separadas por coma]
    python probar_flujo.py 128250766 800,2000,3200
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CARPETA = Path("data/proyectos/3")
BASE = CARPETA / "red_base.net.xml"
SALIDA = CARPETA / "flujo_prueba"
TOPE_S = 10800            # la simulación se detiene aquí aunque queden vehículos
NO_VIALES = ("internal", "crossing", "walkingarea")


# ---------------------------------------------------------------------
# Preparación
# ---------------------------------------------------------------------
def tramos_de_la_via(ruta_net, via):
    """Tramos de la vía en el sentido normal (sin '-'), en orden: #0, #1, #2..."""
    from scenario_builder import _pertenece_a_via
    ids = [e.get("id") for e in ET.parse(ruta_net).getroot().findall("edge")
           if e.get("function") not in NO_VIALES and _pertenece_a_via(e.get("id"), via)
           and not e.get("id").startswith("-")]
    return sorted(ids, key=lambda t: int(t.split("#")[1]) if "#" in t else 0)


def construir_redes(netconvert, via):
    """Regresa [(nombre, ruta_de_la_red)] para las tres redes de la prueba."""
    from scenario_builder import construir_red_escenario_con_reporte
    redes = [("A. Original (actuada)", BASE)]
    ruta_b, _ = construir_red_escenario_con_reporte(
        netconvert, BASE, CARPETA / "escenarios" / "9101", [], [], semaforos_fijos=True)
    redes.append(("B. Tiempo fijo", ruta_b))
    ruta_c, reporte = construir_red_escenario_con_reporte(
        netconvert, BASE, CARPETA / "escenarios" / "9102",
        [{"edge_id": via, "carriles_extra": 1}], [], semaforos_fijos=True)
    if reporte["rechazados"]:
        sys.exit(f"No se pudo agregar el carril: {reporte['rechazados']}")
    redes.append(("C. Tiempo fijo + 1 carril", ruta_c))
    return redes


def escribir_demanda(tramos, demanda, ruta):
    """Un solo flujo de `demanda` veh/h durante 1 hora, recorriendo la vía de principio a fin."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(f"""<routes>
    <vType id="auto" vClass="passenger" length="4.5" width="1.8" maxSpeed="33.33" accel="2.6" decel="4.5"/>
    <route id="r0" edges="{' '.join(tramos)}"/>
    <flow id="f0" type="auto" route="r0" begin="0" end="3600" vehsPerHour="{demanda}"
          departLane="free" departSpeed="max"/>
</routes>
""", encoding="utf-8")


# ---------------------------------------------------------------------
# Simulación y resultados
# ---------------------------------------------------------------------
def simular(sumo, red, rou, carpeta, etiqueta, tramos_observados):
    """Corre SUMO con TraCI. Regresa (tripinfo, pendientes, tiempo_final, uso_de_carriles)."""
    import traci
    carpeta.mkdir(parents=True, exist_ok=True)
    tripinfo = carpeta / "tripinfo.xml"
    traci.start([str(sumo), "-n", str(Path(red).resolve()), "-r", str(rou.resolve()),
                 "--tripinfo-output", str(tripinfo.resolve()), "--time-to-teleport", "-1",
                 "--seed", "42", "--no-step-log", "--no-warnings"], label=etiqueta)
    conn = traci.getConnection(etiqueta)

    carriles = {t: [f"{t}_{i}" for i in range(conn.edge.getLaneNumber(t))] for t in tramos_observados}
    usados = {lane: set() for lanes in carriles.values() for lane in lanes}
    while conn.simulation.getMinExpectedNumber() > 0 and conn.simulation.getTime() < TOPE_S:
        conn.simulationStep()
        for lane in usados:
            usados[lane].update(conn.lane.getLastStepVehicleIDs(lane))
    pendientes = conn.simulation.getMinExpectedNumber()
    tiempo_final = conn.simulation.getTime()
    conn.close()

    uso = {t: [len(usados[lane]) for lane in lanes] for t, lanes in carriles.items()}
    return tripinfo, pendientes, tiempo_final, uso


def resumir(tripinfo):
    """Promedios por vehículo a partir de tripinfo.xml."""
    viajes = ET.parse(tripinfo).getroot().findall("tripinfo")
    n = len(viajes)
    if n == 0:
        return {"n": 0}
    media = lambda f: sum(f(v) for v in viajes) / n
    return {"n": n,
            "total": media(lambda v: float(v.get("duration")) + float(v.get("departDelay"))),
            "espera": media(lambda v: float(v.get("waitingTime"))),
            "entrada": media(lambda v: float(v.get("departDelay")))}


# ---------------------------------------------------------------------
def main():
    from sumolib import checkBinary
    via = sys.argv[1] if len(sys.argv) > 1 else "128250766"
    demandas = [int(d) for d in (sys.argv[2] if len(sys.argv) > 2 else "800,2000,3200").split(",")]
    netconvert, sumo = checkBinary("netconvert"), checkBinary("sumo")

    tramos = tramos_de_la_via(BASE, via)
    print(f"Ruta del flujo ({len(tramos)} tramos): {' -> '.join(tramos)}")
    redes = construir_redes(netconvert, via)

    for demanda in demandas:
        rou = SALIDA / f"demanda_{demanda}.rou.xml"
        escribir_demanda(tramos, demanda, rou)
        print("\n" + "=" * 96 + f"\nDEMANDA: {demanda} veh/h por la vía {via}\n" + "=" * 96)
        print(f"{'Red':<28}{'Veh':>6}{'T.total(s)':>12}{'Espera(s)':>11}{'Retr.entrada(s)':>17}{'Pendientes':>12}")
        detalle = []
        for i, (nombre, red) in enumerate(redes):
            carpeta = SALIDA / str(demanda) / f"red_{i}"
            tripinfo, pendientes, t_final, uso = simular(
                sumo, red, rou, carpeta, f"flujo_{demanda}_{i}", [tramos[0], tramos[-1]])
            r = resumir(tripinfo)
            if r["n"] == 0:
                print(f"{nombre:<28}{'0':>6}   (ningún vehículo terminó)")
            else:
                print(f"{nombre:<28}{r['n']:>6}{r['total']:>12.1f}{r['espera']:>11.1f}"
                      f"{r['entrada']:>17.1f}{pendientes:>12}")
            detalle.append((nombre, uso, pendientes, t_final))
        print("\n  Vehículos distintos que pasaron por cada carril (carril 0 = el más a la derecha):")
        for nombre, uso, pendientes, t_final in detalle:
            marca = "  <- NO TERMINÓ: quedaron vehículos al llegar al tope" if pendientes else ""
            print(f"    {nombre:<26}" + " | ".join(f"{t.split('#')[1] if '#' in t else t}: {u}" for t, u in uso.items()) + marca)


if __name__ == "__main__":
    main()