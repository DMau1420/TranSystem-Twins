"""
Experimento: agregar carriles a una vía sin tocar el pipeline.
Uso (desde sumo/):  python probar_conexiones.py [via] [carriles_extra]
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from sumolib import checkBinary
from scenario_builder import _pertenece_a_via
from sumo.scripts_pruebas_modificacion.verificar_escenario import leer_red, comparar_calles, comparar_conexiones, comparar_control, comparar_semaforos

VIA = sys.argv[1] if len(sys.argv) > 1 else "128255275"
EXTRA = int(sys.argv[2]) if len(sys.argv) > 2 else 1

carpeta = Path("data/proyectos/3")
base = carpeta / "red_base.net.xml"
tmp = carpeta / "prueba_conexiones"
tmp.mkdir(exist_ok=True)
netconvert = checkBinary("netconvert")
prefijo = tmp / "plano"


def correr(comando, que):
    r = subprocess.run(comando, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"netconvert FALLÓ al {que}:\n{(r.stderr or r.stdout)[-1500:]}")
        sys.exit(1)
    return r


# 1) Exportar la red base a archivos planos
correr([netconvert, "--sumo-net-file", str(base), "--plain-output-prefix", str(prefijo)], "exportar")
# 2) Agregar carriles (nunca se reduce) y recordar cuántos tenía cada tramo
viejos = {}
arbol = ET.parse(f"{prefijo}.edg.xml")
for e in arbol.getroot().findall("edge"):
    if _pertenece_a_via(e.get("id"), VIA):
        viejos[e.get("id")] = int(e.get("numLanes"))
        e.set("numLanes", str(viejos[e.get("id")] + EXTRA))
        print(f"  {e.get('id')}: numLanes {viejos[e.get('id')]} -> {viejos[e.get('id')] + EXTRA}")
arbol.write(f"{prefijo}.edg.xml", encoding="utf-8", xml_declaration=True)

# 3) Conservar TODAS las conexiones de la base. Solo se agregan las del carril nuevo,
#    copiando las del carril de mayor índice de cada tramo de la vía.
arbol = ET.parse(f"{prefijo}.con.xml")
raiz = arbol.getroot()
nuevas = 0
for c in list(raiz.findall("connection")):
    origen = c.get("from")
    if origen not in viejos or int(c.get("fromLane")) != viejos[origen] - 1:
        continue
    for k in range(1, EXTRA + 1):
        copia = dict(c.attrib)
        copia["fromLane"] = str(viejos[origen] - 1 + k)
        destino = c.get("to")
        if destino in viejos and int(c.get("toLane")) == viejos[destino] - 1:
            copia["toLane"] = str(viejos[destino] - 1 + k)
        copia.pop("tl", None)          # que netconvert asigne el enlace del semáforo
        copia.pop("linkIndex", None)
        ET.SubElement(raiz, "connection", copia)
        nuevas += 1
arbol.write(f"{prefijo}.con.xml", encoding="utf-8", xml_declaration=True)
print(f"  Conexiones nuevas (copiadas del carril vecino): {nuevas}")


# 4) Reconstruir
salida = tmp / "red_prueba.net.xml"
cmd = [netconvert, "--node-files", f"{prefijo}.nod.xml", "--edge-files", f"{prefijo}.edg.xml",
       "--connection-files", f"{prefijo}.con.xml", "--output-file", str(salida)]
if Path(f"{prefijo}.tll.xml").exists():
    cmd += ["--tllogic-files", f"{prefijo}.tll.xml"]
r = correr(cmd, "reconstruir")
if r.stderr:
    print("Advertencias de netconvert (últimas líneas):\n", r.stderr[-800:])

# 5) Verificar contra la base
b, p = leer_red(base), leer_red(salida)
print("\n--- Verificación ---")
comparar_calles(b, p)
comparar_conexiones(b, p)


def conexiones_de_via(ruta, via):
    """Conexiones entre calles (se ignoran las internas de intersección, que empiezan con ':')."""
    root = ET.parse(ruta).getroot()
    return {(c.get("from"), c.get("fromLane"), c.get("to"), c.get("toLane"))
            for c in root.findall("connection")
            if not c.get("from").startswith(":") and not c.get("to").startswith(":")
            and (_pertenece_a_via(c.get("from"), via) or _pertenece_a_via(c.get("to"), via))}


cb, cp = conexiones_de_via(base, VIA), conexiones_de_via(salida, VIA)
print(f"\n--- Conexiones que tocan {VIA} ---")
print(f"Base: {len(cb)} | Prueba: {len(cp)}")
print("Eliminadas respecto a la base:")
for c in sorted(cb - cp):
    print("  ", c)
print("Nuevas respecto a la base:")
for c in sorted(cp - cb):
    print("  ", c)

comparar_control(b, p)

print("\n--- Semáforos (consistencia state/enlaces) ---")
comparar_semaforos(b, p)