"""
Prueba del scenario_builder SIN servidor.
Uso (desde sumo/):  python probar_builder.py
Corre 4 casos y pasa cada red resultante por los verificadores.
"""
from pathlib import Path

from sumolib import checkBinary
from scenario_builder import construir_red_escenario_con_reporte
from sumo.scripts_pruebas_modificacion.verificar_escenario import (leer_red, comparar_calles, comparar_conexiones,
                                comparar_control, comparar_semaforos)
from sumo.scripts_pruebas_modificacion.verificar_secuencias import verificar_secuencias, reducciones_de_via

BASE = Path("data/proyectos/3/red_base.net.xml")
CASOS = [
    ("1. Agregar 1 carril, vía SIN semáforo", 9001, "128255275", +1),
    ("2. Agregar 1 carril, vía CON semáforo", 9002, "128250766", +1),
    ("3. Reducir 1 carril, vía SIN semáforo", 9003, "128255275", -1),
    ("4. Reducir 1 carril, vía CON semáforo (se APLICA reinterpretando el semáforo)", 9004, "128250766", -1),
]

netconvert = checkBinary("netconvert")
base = leer_red(BASE)

for nombre, esc_id, via, delta in CASOS:
    print("\n" + "=" * 90 + f"\n{nombre}\n" + "=" * 90)
    carpeta = Path("data/proyectos/3/escenarios") / str(esc_id)
    ruta, reporte = construir_red_escenario_con_reporte(
        netconvert, BASE, carpeta, [{"edge_id": via, "carriles_extra": delta}], [])
    if Path(ruta).resolve() == BASE.resolve():
        print("\n>>> Se devolvió la red base (ningún cambio aplicado).")
        continue
    esc = leer_red(ruta)
    print("\n--- Verificación ---")
    comparar_calles(base, esc)
    comparar_conexiones(base, esc)
    comparar_control(base, esc)
    comparar_semaforos(base, esc)
    if delta < 0:                      # al reducir, también se comparan las luces de cada enlace
        verificar_secuencias(BASE, ruta, reducciones_de_via(BASE, via, -delta))