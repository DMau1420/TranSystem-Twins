"""
Experimento: reducir carriles de una vía redirigiendo (no borrando) las conexiones.
Uso (desde sumo/):
    python probar_reduccion.py candidatas              # vías que llegan a un semáforo
    python probar_reduccion.py [via] [carriles_menos]
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from sumolib import checkBinary
from scenario_builder import _pertenece_a_via
from sumo.scripts_pruebas_modificacion.verificar_escenario import leer_red, comparar_calles, comparar_conexiones, comparar_semaforos

carpeta = Path("data/proyectos/3")
base = carpeta / "red_base.net.xml"


def candidatas():
    cuenta = Counter()
    for c in ET.parse(base).getroot().findall("connection"):
        if c.get("tl") and not c.get("from").startswith(":"):
            cuenta[c.get("from").lstrip("-").split("#")[0]] += 1
    print("Vías que llegan a un semáforo (id base: conexiones controladas):")
    for via, n in cuenta.most_common(10):
        print(f"  {via}: {n}")


def conexiones_de_via(ruta, via):
    root = ET.parse(ruta).getroot()
    return {(c.get("from"), c.get("fromLane"), c.get("to"), c.get("toLane"))
            for c in root.findall("connection")
            if not c.get("from").startswith(":") and not c.get("to").startswith(":")
            and (_pertenece_a_via(c.get("from"), via) or _pertenece_a_via(c.get("to"), via))}


def correr(comando, que):
    r = subprocess.run(comando, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"netconvert FALLÓ al {que}:\n{(r.stderr or r.stdout)[-1500:]}")
        sys.exit(1)
    return r


if len(sys.argv) > 1 and sys.argv[1] == "candidatas":
    candidatas()
    sys.exit()

VIA = sys.argv[1] if len(sys.argv) > 1 else "128255275"
MENOS = int(sys.argv[2]) if len(sys.argv) > 2 else 1

tmp = carpeta / "prueba_reduccion"
tmp.mkdir(exist_ok=True)
netconvert = checkBinary("netconvert")
prefijo = tmp / "plano"

# 1) Exportar la red base a archivos planos
correr([netconvert, "--sumo-net-file", str(base), "--plain-output-prefix", str(prefijo)], "exportar")

# 2) Reducir carriles por tramo (mínimo 1) y quitar los <lane> con índice fuera de rango
nuevos = {}   # tramo -> (carriles antes, carriles después)
arbol = ET.parse(f"{prefijo}.edg.xml")
for e in arbol.getroot().findall("edge"):
    if _pertenece_a_via(e.get("id"), VIA):
        antes = int(e.get("numLanes"))
        despues = max(1, antes - MENOS)
        nuevos[e.get("id")] = (antes, despues)
        e.set("numLanes", str(despues))
        for lane in list(e.findall("lane")):
            if int(lane.get("index", "0")) >= despues:
                e.remove(lane)
        aviso = "  (mínimo alcanzado)" if antes - MENOS < 1 else ""
        print(f"  {e.get('id')}: numLanes {antes} -> {despues}{aviso}")
arbol.write(f"{prefijo}.edg.xml", encoding="utf-8", xml_declaration=True)

# 3) Redirigir al carril más alto que queda las conexiones que usaban un carril eliminado
arbol = ET.parse(f"{prefijo}.con.xml")
raiz = arbol.getroot()
vistas, redirigidas, duplicadas, semaforos = set(), [], [], set()
for c in list(raiz.findall("connection")):
    o, d = c.get("from"), c.get("to")
    f, t = int(c.get("fromLane")), int(c.get("toLane"))
    nf = nuevos[o][1] - 1 if o in nuevos and f >= nuevos[o][1] else f
    nt = nuevos[d][1] - 1 if d in nuevos and t >= nuevos[d][1] else t
    if (nf, nt) != (f, t):
        redirigidas.append(((o, f, d, t), (o, nf, d, nt)))
        c.set("fromLane", str(nf))
        c.set("toLane", str(nt))
        if c.get("tl"):
            semaforos.add(c.get("tl"))
    clave = (o, c.get("fromLane"), d, c.get("toLane"))
    if clave in vistas:          # dos conexiones quedaron idénticas: se conserva una
        raiz.remove(c)
        duplicadas.append(clave)
        if c.get("tl"):
            semaforos.add(c.get("tl"))
    else:
        vistas.add(clave)
arbol.write(f"{prefijo}.con.xml", encoding="utf-8", xml_declaration=True)

print(f"\nConexiones redirigidas: {len(redirigidas)}")
for antes, despues in redirigidas:
    print(f"  {antes} -> {despues}")
print(f"Duplicadas eliminadas tras redirigir: {len(duplicadas)}")
print(f"Semáforos afectados por el cambio: {sorted(semaforos) or 'ninguno'}")

# 4) Reconstruir
salida = tmp / "red_prueba.net.xml"
cmd = [netconvert, "--node-files", f"{prefijo}.nod.xml", "--edge-files", f"{prefijo}.edg.xml",
       "--connection-files", f"{prefijo}.con.xml", "--output-file", str(salida)]
if Path(f"{prefijo}.tll.xml").exists():
    cmd += ["--tllogic-files", f"{prefijo}.tll.xml"]
r = correr(cmd, "reconstruir")
if r.stderr:
    print("\nAdvertencias de netconvert (últimas líneas):\n", r.stderr[-800:])

# 5) Verificar contra la base
b, p = leer_red(base), leer_red(salida)
print("\n--- Verificación ---")
comparar_calles(b, p)
comparar_conexiones(b, p)
comparar_semaforos(b, p)

cb, cp = conexiones_de_via(base, VIA), conexiones_de_via(salida, VIA)
print(f"\n--- Conexiones que tocan {VIA} ---")
print(f"Base: {len(cb)} | Prueba: {len(cp)}")
print("Eliminadas respecto a la base:")
for c in sorted(cb - cp):
    print("  ", c)
print("Nuevas respecto a la base:")
for c in sorted(cp - cb):
    print("  ", c)