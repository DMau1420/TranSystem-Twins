import sys
import xml.etree.ElementTree as ET
from pathlib import Path

escenario, edge = sys.argv[1], sys.argv[2]
carpeta = Path("data/proyectos/3")
redes = {
    "BASE": carpeta / "red_base.net.xml",
    "ESCENARIO": carpeta / "escenarios" / escenario / "red_escenario.net.xml",
}

for nombre, ruta in redes.items():
    root = ET.parse(ruta).getroot()
    carriles = [l.get("id") for e in root.findall("edge") if e.get("id") == edge for l in e.findall("lane")]
    print(f"\n=== {nombre}: {edge} tiene {len(carriles)} carriles ===")
    for i in range(len(carriles)):
        sal = [f"{c.get('to')}_{c.get('toLane')}" for c in root.findall("connection")
               if c.get("from") == edge and c.get("fromLane") == str(i)]
        ent = [f"{c.get('from')}_{c.get('fromLane')}" for c in root.findall("connection")
               if c.get("to") == edge and c.get("toLane") == str(i)]
        print(f"  carril {i}: sale hacia {sal or 'NADA'} | recibe de {ent or 'NADA'}")