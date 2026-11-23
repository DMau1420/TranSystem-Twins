"""
Experimento: reducir carriles en una vía QUE LLEGA A UN SEMÁFORO, reinterpretando sus enlaces.
Uso (desde sumo/):  python probar_reduccion_semaforo.py 128250766 1
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from escenario_conexiones import _redirigir_conexiones, dividir_cambios
from scenario_builder import _pertenece_a_via


def reducir_en_tll(raiz, reducciones):
    """
    Reinterpreta los enlaces del semáforo cuando desaparecen carriles.
    1. Cada enlace que usaba un carril eliminado se redirige al carril más alto que queda.
    2. Si al redirigir queda IGUAL a un enlace que ya existía, se borra (el tráfico usa la luz del vecino).
    3. Por cada enlace borrado, cada fase pierde ese carácter y los enlaces siguientes se renumeran.
    Regresa (redirigidos, borrados) para poder explicar qué pasó.
    """
    conexiones = raiz.findall("connection")

    def destino_nuevo(c):
        o, d = c.get("from"), c.get("to")
        f, t = int(c.get("fromLane")), int(c.get("toLane"))
        nf = min(f, reducciones[o][1] - 1) if o in reducciones else f
        nt = min(t, reducciones[d][1] - 1) if d in reducciones else t
        return f, t, nf, nt

    # Enlaces que NO cambian: sirven para detectar duplicados
    vistas = set()
    for c in conexiones:
        f, t, nf, nt = destino_nuevo(c)
        if (f, t) == (nf, nt):
            vistas.add((c.get("tl"), c.get("from"), f, c.get("to"), t))

    redirigidos, borrados = [], {}       # borrados: {semáforo: {linkIndex borrados}}
    for c in conexiones:
        f, t, nf, nt = destino_nuevo(c)
        if (f, t) == (nf, nt):
            continue
        tl, o, d = c.get("tl"), c.get("from"), c.get("to")
        clave = (tl, o, nf, d, nt)
        if clave in vistas:                          # queda igual a uno existente -> se borra
            borrados.setdefault(tl, set()).add(int(c.get("linkIndex")))
            raiz.remove(c)
            redirigidos.append((tl, o, f, d, t, "BORRADO (duplicado)"))
        else:                                        # se mueve, conserva su luz
            c.set("fromLane", str(nf))
            c.set("toLane", str(nt))
            vistas.add(clave)
            redirigidos.append((tl, o, f, d, t, f"-> {o} {nf} / {d} {nt}"))

    for tl, indices in borrados.items():
        for c in raiz.findall("connection"):         # renumerar los enlaces que quedan
            if c.get("tl") == tl:
                li = int(c.get("linkIndex"))
                c.set("linkIndex", str(li - sum(1 for b in indices if b < li)))
        for logica in raiz.findall("tlLogic"):       # quitar el carácter de cada fase
            if logica.get("id") == tl:
                for fase in logica.findall("phase"):
                    estado = fase.get("state")
                    fase.set("state", "".join(ch for i, ch in enumerate(estado) if i not in indices))
    return redirigidos, borrados


def main():
    from sumolib import checkBinary
    from sumo.scripts_pruebas_modificacion.verificar_escenario import (leer_red, comparar_calles, comparar_conexiones,
                                     comparar_control, comparar_semaforos)

    via = sys.argv[1] if len(sys.argv) > 1 else "128250766"
    menos = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    carpeta = Path("data/proyectos/3")
    base = carpeta / "red_base.net.xml"
    tmp = carpeta / "prueba_reduccion_semaforo"
    tmp.mkdir(exist_ok=True)
    netconvert = checkBinary("netconvert")
    prefijo = tmp / "plano"

    def correr(comando, que):
        r = subprocess.run(comando, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"netconvert FALLÓ al {que}:\n{(r.stderr or r.stdout)[-1500:]}")
            sys.exit(1)
        return r

    correr([netconvert, "--sumo-net-file", str(base), "--plain-output-prefix", str(prefijo)], "exportar")

    # 1) Quitar carriles en el .edg.xml
    nuevos = {}
    arbol = ET.parse(f"{prefijo}.edg.xml")
    for e in arbol.getroot().findall("edge"):
        if _pertenece_a_via(e.get("id"), via):
            antes = int(e.get("numLanes"))
            despues = max(1, antes - menos)
            if despues == antes:
                continue
            nuevos[e.get("id")] = (antes, despues)
            e.set("numLanes", str(despues))
            for lane in list(e.findall("lane")):
                if int(lane.get("index", "0")) >= despues:
                    e.remove(lane)
            print(f"  {e.get('id')}: numLanes {antes} -> {despues}")
    arbol.write(f"{prefijo}.edg.xml", encoding="utf-8", xml_declaration=True)
    reducciones, _ = dividir_cambios(nuevos)

    # 2) .con.xml: redirigir (ya probado)
    arbol = ET.parse(f"{prefijo}.con.xml")
    _, redirigidas, duplicadas = _redirigir_conexiones(arbol.getroot(), reducciones)
    arbol.write(f"{prefijo}.con.xml", encoding="utf-8", xml_declaration=True)
    print(f"  .con.xml: {redirigidas} redirigidas, {duplicadas} duplicadas eliminadas")

    # 3) .tll.xml: reinterpretar enlaces del semáforo (lo nuevo)
    arbol = ET.parse(f"{prefijo}.tll.xml")
    redirigidos, borrados = reducir_en_tll(arbol.getroot(), reducciones)
    arbol.write(f"{prefijo}.tll.xml", encoding="utf-8", xml_declaration=True)
    print(f"\n  .tll.xml: {len(redirigidos)} enlaces afectados")
    for r in redirigidos:
        print("    ", r)
    print(f"  Enlaces borrados por semáforo: { {tl: sorted(v) for tl, v in borrados.items()} or 'ninguno' }")

    # 4) Reconstruir
    salida = tmp / "red_prueba.net.xml"
    r = correr([netconvert, "--node-files", f"{prefijo}.nod.xml", "--edge-files", f"{prefijo}.edg.xml",
                "--connection-files", f"{prefijo}.con.xml", "--tllogic-files", f"{prefijo}.tll.xml",
                "--output-file", str(salida)], "reconstruir")
    if r.stderr:
        print("\nAdvertencias de netconvert (últimas líneas):\n", r.stderr[-600:])

    # 5) Verificar
    b, p = leer_red(base), leer_red(salida)
    print("\n--- Verificación ---")
    comparar_calles(b, p)
    comparar_conexiones(b, p)
    comparar_control(b, p)
    comparar_semaforos(b, p)


if __name__ == "__main__":
    main()