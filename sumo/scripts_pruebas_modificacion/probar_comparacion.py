"""
Compara los tres escenarios de la propuesta con FLUJOS EXPLÍCITOS, a dos niveles de demanda:
  A. Situación actual
  B. Semáforo ajustado (más verde para la vía)
  C. Carril adicional en la vía

Corre sin ventana de SUMO. Uso (desde sumo/):
    python probar_comparacion.py [demandas de la vía en veh/h, separadas por coma]
    python probar_comparacion.py 2000,3200
Guarda cada comparación en data/proyectos/3/comparaciones/comparacion_<demanda>.json
"""
import json
import sys
from pathlib import Path

PROYECTO_ID = 3
CARPETA = Path("data/proyectos/3")
VIA = "128250766"
SEMAFORO = "cluster_11514661659_372948820_372948824"
FASE_VERDE_VIA = 0            # la fase que da verde a la vía (la detectó probar_semaforo.py)
VERDE_AJUSTADO_S = 50
CALLE_LATERAL = "843659372"
DEMANDA_LATERAL = 400
PESADOS_VIA = 10


def armar_escenarios(demanda_via, numero):
    """Los tres escenarios con los MISMOS flujos; solo cambia la intervención."""
    flujos = [
        {"id": "via", "origen": f"{VIA}#0", "destino": f"{VIA}#3",
         "vehiculos_por_hora": demanda_via, "porcentaje_pesados": PESADOS_VIA},
        {"id": "lateral", "origen": CALLE_LATERAL, "destino": f"{VIA}#3",
         "vehiculos_por_hora": DEMANDA_LATERAL, "porcentaje_pesados": 0},
    ]
    base = {"proyecto_id": PROYECTO_ID, "flujos": flujos, "duracion_segundos": 3600,
            "modificaciones_edges": [], "modificaciones_semaforos": []}
    return [
        {**base, "id": 4000 + numero * 10 + 1, "nombre": "A. Actual"},
        {**base, "id": 4000 + numero * 10 + 2, "nombre": "B. Semaforo ajustado",
         "modificaciones_semaforos": [{"tls_id": SEMAFORO,
                                       "fases": [{"indice": FASE_VERDE_VIA, "duracion": VERDE_AJUSTADO_S}]}]},
        {**base, "id": 4000 + numero * 10 + 3, "nombre": "C. Carril adicional",
         "modificaciones_edges": [{"edge_id": VIA, "carriles_extra": 1}]},
    ]


def leer_reporte_de_cambios(escenario):
    """El reporte que dejó el constructor (qué se aplicó y qué se rechazó); {} si no hubo cambios."""
    ruta = CARPETA / "escenarios" / str(escenario["id"]) / "reporte_cambios.json"
    if not (escenario["modificaciones_edges"] or escenario["modificaciones_semaforos"]) or not ruta.exists():
        return {}
    return json.loads(ruta.read_text(encoding="utf-8"))


def main():
    from sumo_tools import cargar_herramientas_sumo
    from main import simular_escenario
    from sumo.scripts_pruebas_modificacion.escenario_comparacion import comparar, imprimir_comparacion, guardar_comparacion

    demandas = [int(d) for d in (sys.argv[1] if len(sys.argv) > 1 else "2000,3200").split(",")]
    herramientas = dict(cargar_herramientas_sumo())
    herramientas["sumo_gui"] = herramientas["sumo"]              # sin ventana, para que sea rápido
    red_base = {"osm_file_url": CARPETA / "red_vial.osm", "netxml_base_url": CARPETA / "red_base.net.xml",
                "geojson_url": CARPETA / "red_base.geojson"}

    for numero, demanda in enumerate(demandas):
        resultados = []
        for escenario in armar_escenarios(demanda, numero):
            print(f"\n######## {escenario['nombre']} | vía {demanda} veh/h ########")
            indicadores = simular_escenario(escenario, red_base, herramientas)
            resultados.append({"nombre": escenario["nombre"], "indicadores": indicadores,
                               "cambios": leer_reporte_de_cambios(escenario)})
        comparacion = comparar(resultados)
        print(f"\n\n>>>>>>>> DEMANDA DE LA VÍA: {demanda} veh/h | lateral {DEMANDA_LATERAL} veh/h")
        imprimir_comparacion(comparacion)
        guardar_comparacion(comparacion, CARPETA / "comparaciones" / f"comparacion_{demanda}.json")


if __name__ == "__main__":
    main()