"""
Prueba del ajuste de semáforo: ¿alargar o acortar el verde de la vía mueve los resultados?

Dos flujos cruzan el MISMO semáforo:
  - "vía":     recorre la vía completa (la que se ajusta)
  - "lateral": entra desde una calle lateral a la vía (compite por el verde)
Se simula la base (tiempo fijo) y variantes de la duración del verde de la vía, con la misma
demanda y semilla. Alargar el verde alarga el ciclo y las demás fases no cambian.

Uso (desde sumo/):
    python probar_semaforo.py [verdes] [demandas_via] [demanda_lateral]
    python probar_semaforo.py 25,35,50 1500,2000,2500 400
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from sumo.scripts_pruebas_modificacion.probar_flujo import BASE, CARPETA, SALIDA, tramos_de_la_via, simular

VIA = "128250766"


# ---------------------------------------------------------------------
# Preparación
# ---------------------------------------------------------------------
def analizar_cruce(ruta_net, tramos):
    """
    Encuentra el semáforo entre tramos[0] y tramos[1], una calle lateral que entra a tramos[1],
    y qué fases dan verde a cada movimiento.
    """
    raiz = ET.parse(ruta_net).getroot()
    todas = raiz.findall("connection")
    pares = {(c.get("from"), c.get("to")) for c in todas}
    controladas = [c for c in todas if c.get("tl") and not c.get("from").startswith(":")]

    de_la_via = [c for c in controladas if c.get("from") == tramos[0] and c.get("to") == tramos[1]]
    if not de_la_via:
        sys.exit(f"No hay semáforo entre {tramos[0]} y {tramos[1]}: esta prueba necesita un cruce semaforizado.")
    tl = de_la_via[0].get("tl")
    links_via = {int(c.get("linkIndex")) for c in de_la_via if c.get("tl") == tl}

    lateral = next((c.get("from") for c in sorted(controladas, key=lambda c: int(c.get("linkIndex")))
                    if c.get("tl") == tl and c.get("to") == tramos[1] and c.get("from") not in tramos
                    and (c.get("from"), c.get("to")) in pares), None)
    links_lat = {int(c.get("linkIndex")) for c in controladas
                 if c.get("tl") == tl and c.get("from") == lateral and c.get("to") == tramos[1]}

    logica = next(l for l in raiz.findall("tlLogic") if l.get("id") == tl)
    fases = [(int(float(p.get("duration"))), p.get("state")) for p in logica.findall("phase")]
    return {"tl": tl, "lateral": lateral, "fases": fases,
            "verdes_via": [i for i, (_, s) in enumerate(fases) if any(s[l] == "G" for l in links_via)],
            "verdes_lat": [i for i, (_, s) in enumerate(fases) if any(s[l] in "Gg" for l in links_lat)]}


def escribir_demanda(tramos, lateral, demanda_via, demanda_lateral, ruta):
    """Flujo "via" por la vía completa y, si hay calle lateral, flujo "lat" que entra a la vía en tramos[1]."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    lat = ""
    if lateral and demanda_lateral > 0:
        lat = (f'<route id="r1" edges="{lateral} {" ".join(tramos[1:])}"/>\n'
               f'    <flow id="lat" type="auto" route="r1" begin="0" end="3600" vehsPerHour="{demanda_lateral}" '
               f'departLane="free" departSpeed="max"/>')
    ruta.write_text(f"""<routes>
    <vType id="auto" vClass="passenger" length="4.5" width="1.8" maxSpeed="33.33" accel="2.6" decel="4.5"/>
    <route id="r0" edges="{' '.join(tramos)}"/>
    {lat}
    <flow id="via" type="auto" route="r0" begin="0" end="3600" vehsPerHour="{demanda_via}"
          departLane="free" departSpeed="max"/>
</routes>
""", encoding="utf-8")


def resumir_por_grupo(tripinfo):
    """Promedios por vehículo, separados por flujo: {"via": {...}, "lat": {...}}."""
    grupos = {"via": [], "lat": []}
    for v in ET.parse(tripinfo).getroot().findall("tripinfo"):
        grupos["lat" if v.get("id").startswith("lat") else "via"].append(v)
    resumen = {}
    for nombre, viajes in grupos.items():
        n = len(viajes)
        if n == 0:
            resumen[nombre] = None
            continue
        resumen[nombre] = {
            "n": n,
            "total": sum(float(v.get("duration")) + float(v.get("departDelay")) for v in viajes) / n,
            "espera": sum(float(v.get("waitingTime")) for v in viajes) / n}
    return resumen


def _fila(g):
    return f"{g['n']:>6}{g['total']:>9.1f}{g['espera']:>8.1f}" if g else f"{'-':>6}{'-':>9}{'-':>8}"


# ---------------------------------------------------------------------
def main():
    from sumolib import checkBinary
    from scenario_builder import construir_red_escenario_con_reporte

    verdes = [int(v) for v in (sys.argv[1] if len(sys.argv) > 1 else "25,35,50").split(",")]
    demandas = [int(d) for d in (sys.argv[2] if len(sys.argv) > 2 else "1500,2000,2500").split(",")]
    demanda_lat = int(sys.argv[3]) if len(sys.argv) > 3 else 400
    netconvert, sumo = checkBinary("netconvert"), checkBinary("sumo")

    tramos = tramos_de_la_via(BASE, VIA)
    cruce = analizar_cruce(BASE, tramos)
    if not cruce["verdes_via"]:
        sys.exit("No encontré ninguna fase que dé verde a la vía en ese cruce.")
    if cruce["lateral"] is None:
        print("AVISO: no encontré calle lateral que entre a la vía en este cruce; se simula solo el flujo de la vía.")
        demanda_lat = 0

    print(f"Semáforo del cruce: {cruce['tl']}")
    print(f"Fases (duración, state): {cruce['fases']}")
    print(f"Fases con verde para la vía: {cruce['verdes_via']} | para la calle lateral ({cruce['lateral']}): {cruce['verdes_lat']}")
    fase = max(cruce["verdes_via"], key=lambda i: cruce["fases"][i][0])
    base_dur = cruce["fases"][fase][0]
    ciclo_base = sum(d for d, _ in cruce["fases"])
    print(f"Se ajusta la fase {fase} (verde de la vía): {base_dur} s, ciclo de {ciclo_base} s\n")

    variantes = []
    for k, dur in enumerate(sorted(set(verdes) | {base_dur})):
        ruta, reporte = construir_red_escenario_con_reporte(
            netconvert, BASE, CARPETA / "escenarios" / str(9201 + k), [],
            [{"tls_id": cruce["tl"], "fases": [{"indice": fase, "duracion": dur}]}])
        if reporte["rechazados"]:
            sys.exit(f"No se pudo aplicar el cambio: {reporte['rechazados']}")
        etiqueta = f"Verde {dur} s" + (" (base)" if dur == base_dur else "")
        variantes.append((etiqueta, ruta, ciclo_base - base_dur + dur))

    for demanda in demandas:
        rou = SALIDA / f"semaforo_{demanda}_{demanda_lat}.rou.xml"
        escribir_demanda(tramos, cruce["lateral"], demanda, demanda_lat, rou)
        print("\n" + "=" * 100 + f"\nDEMANDA: vía {demanda} veh/h | calle lateral {demanda_lat} veh/h\n" + "=" * 100)
        print(f"{'':<20}{'Ciclo':>6}  |{'VÍA: veh':>10}{'T.total':>9}{'Espera':>8}  |{'LATERAL: veh':>14}{'T.total':>9}{'Espera':>8}  |{'Pend.':>6}")
        for i, (nombre, ruta, ciclo) in enumerate(variantes):
            carpeta = SALIDA / f"semaforo_{demanda}" / f"v{i}"
            tripinfo, pendientes, _, _ = simular(sumo, ruta, rou, carpeta, f"sem_{demanda}_{i}", [tramos[0]])
            r = resumir_por_grupo(tripinfo)
            print(f"{nombre:<20}{ciclo:>6}  |{_fila(r['via'])}  |{_fila(r['lat'])}  |{pendientes:>6}")


if __name__ == "__main__":
    main()