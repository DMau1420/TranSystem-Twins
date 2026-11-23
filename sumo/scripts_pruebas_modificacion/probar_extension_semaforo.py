"""
Experimento: agregar carriles a una vía que llega a un semáforo, extendiendo su programa.
Uso (desde sumo/):  python probar_extension_semaforo.py 128250766 1
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from sumolib import checkBinary
from scenario_builder import _pertenece_a_via
from sumo.scripts_pruebas_modificacion.verificar_escenario import (leer_red, comparar_calles, comparar_conexiones,
                                 comparar_control, comparar_semaforos)

VIA = sys.argv[1] if len(sys.argv) > 1 else "128250766"
EXTRA = int(sys.argv[2]) if len(sys.argv) > 2 else 1

carpeta = Path("data/proyectos/3")
base = carpeta / "red_base.net.xml"
tmp = carpeta / "prueba_extension"
tmp.mkdir(exist_ok=True)
netconvert = checkBinary("netconvert")
prefijo = tmp / "plano"


def correr(comando, que):
    r = subprocess.run(comando, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"netconvert FALLÓ al {que}:\n{(r.stderr or r.stdout)[-1500:]}")
        sys.exit(1)
    return r


def destino_nuevo(c, viejos, k):
    """toLane del carril copiado: si el destino también es de la vía y era su carril más alto, se desplaza."""
    d = c.get("to")
    if d in viejos and int(c.get("toLane")) == viejos[d] - 1:
        return str(viejos[d] - 1 + k)
    return c.get("toLane")


# 1) Exportar
correr([netconvert, "--sumo-net-file", str(base), "--plain-output-prefix", str(prefijo)], "exportar")

# 2) Agregar carriles a los tramos de la vía
viejos = {}
arbol = ET.parse(f"{prefijo}.edg.xml")
for e in arbol.getroot().findall("edge"):
    if _pertenece_a_via(e.get("id"), VIA):
        viejos[e.get("id")] = int(e.get("numLanes"))
        e.set("numLanes", str(viejos[e.get("id")] + EXTRA))
        print(f"  {e.get('id')}: numLanes {viejos[e.get('id')]} -> {viejos[e.get('id')] + EXTRA}")
arbol.write(f"{prefijo}.edg.xml", encoding="utf-8", xml_declaration=True)

# 3) .con.xml: copiar las conexiones del carril más alto al carril nuevo (igual que la opción C)
arbol = ET.parse(f"{prefijo}.con.xml")
raiz = arbol.getroot()
copiadas_con = 0
for c in list(raiz.findall("connection")):
    o = c.get("from")
    if o not in viejos or int(c.get("fromLane")) != viejos[o] - 1:
        continue
    for k in range(1, EXTRA + 1):
        copia = dict(c.attrib)
        copia["fromLane"] = str(viejos[o] - 1 + k)
        copia["toLane"] = destino_nuevo(c, viejos, k)
        copia.pop("tl", None)
        copia.pop("linkIndex", None)
        ET.SubElement(raiz, "connection", copia)
        copiadas_con += 1
arbol.write(f"{prefijo}.con.xml", encoding="utf-8", xml_declaration=True)
print(f"  Conexiones copiadas en .con.xml: {copiadas_con}")

# 4) .tll.xml: las conexiones controladas del carril nuevo reciben linkIndex nuevo,
#    y cada fase gana un carácter por enlace nuevo, copiado del enlace de origen
arbol = ET.parse(f"{prefijo}.tll.xml")
raiz = arbol.getroot()
conexiones = raiz.findall("connection")
siguiente = {}
for c in conexiones:
    tl = c.get("tl")
    siguiente[tl] = max(siguiente.get(tl, 0), int(c.get("linkIndex")) + 1)

copiar_de = {}   # tl -> [linkIndex de origen, en el orden en que se agregan los nuevos]
for c in conexiones:
    o = c.get("from")
    if o not in viejos or int(c.get("fromLane")) != viejos[o] - 1:
        continue
    tl = c.get("tl")
    for k in range(1, EXTRA + 1):
        copia = dict(c.attrib)
        copia["fromLane"] = str(viejos[o] - 1 + k)
        copia["toLane"] = destino_nuevo(c, viejos, k)
        copia["linkIndex"] = str(siguiente[tl])
        siguiente[tl] += 1
        copiar_de.setdefault(tl, []).append(int(c.get("linkIndex")))
        ET.SubElement(raiz, "connection", copia)

for logica in raiz.findall("tlLogic"):
    extra = copiar_de.get(logica.get("id"), [])
    if not extra:
        continue
    for fase in logica.findall("phase"):
        estado = fase.get("state")
        fase.set("state", estado + "".join(estado[i] for i in extra))
    print(f"  Semáforo {logica.get('id')}: +{len(extra)} enlaces (cada fase ganó {len(extra)} carácter(es))")
arbol.write(f"{prefijo}.tll.xml", encoding="utf-8", xml_declaration=True)
if not copiar_de:
    print("  AVISO: ninguna conexión del carril más alto está controlada por un semáforo; "
          "esta vía no sirve para este experimento.")

# 5) Reconstruir
salida = tmp / "red_prueba.net.xml"
cmd = [netconvert, "--node-files", f"{prefijo}.nod.xml", "--edge-files", f"{prefijo}.edg.xml",
       "--connection-files", f"{prefijo}.con.xml", "--tllogic-files", f"{prefijo}.tll.xml",
       "--output-file", str(salida)]
r = correr(cmd, "reconstruir")
if r.stderr:
    print("\nAdvertencias de netconvert (últimas líneas):\n", r.stderr[-800:])

# 6) Verificar
b, p = leer_red(base), leer_red(salida)
print("\n--- Verificación ---")
comparar_calles(b, p)
comparar_conexiones(b, p)
comparar_control(b, p)
comparar_semaforos(b, p)
nuevas = sorted(p["controladas"] - b["controladas"])
print(f"\nCarriles que ahora están bajo control semafórico y antes no: {nuevas}")