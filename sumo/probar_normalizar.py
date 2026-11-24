"""
probar_normalizar.py: pruebas de escenario_normalizar con los ejemplos de GUIA_DEMANDA.md.
No corre SUMO. Uso:  python probar_normalizar.py
"""
import copy

from escenario_normalizar import normalizar_escenario

BASE = {"id": 1, "proyecto_id": 3, "nombre": "x", "modificaciones_edges": [], "modificaciones_semaforos": []}

ALEATORIO = {**BASE, "demanda_vehicular": 800, "porcentaje_pesados": 10, "duracion_segundos": 3600}

FLUJOS = {**BASE, "flujos": [
    {"id": "via", "origen": "8640976#9", "destino": "126678383#0",
     "vehiculos_por_hora": 800, "porcentaje_pesados": 10, "desde_s": 28800, "hasta_s": 32400},
    {"id": "lateral", "origen": "843659372", "destino": "126678383#0",
     "vehiculos_por_hora": 400, "porcentaje_pesados": 5, "desde_s": 30600, "hasta_s": 32400},
]}


def con(esc, **cambios):
    """Copia del escenario con campos cambiados."""
    nuevo = copy.deepcopy(esc)
    nuevo.update(cambios)
    return nuevo


def con_flujo(esc, i, **cambios):
    nuevo = copy.deepcopy(esc)
    nuevo["flujos"][i].update(cambios)
    return nuevo


def debe_fallar(esc, fragmento):
    """El escenario debe ser rechazado y el motivo debe contener `fragmento`."""
    try:
        normalizar_escenario(esc)
    except ValueError as e:
        assert fragmento in str(e), f"motivo inesperado: {e}"
        return
    raise AssertionError(f"debió fallar con '{fragmento}'")


def main():
    # 1. Modo flujos: el ejemplo de la guía (sección 6)
    n = normalizar_escenario(FLUJOS)
    assert n["modo"] == "flujos"
    assert n["reloj_inicio_s"] == 28800
    assert (n["flujos"][0]["desde_s"], n["flujos"][0]["hasta_s"]) == (0, 3600)
    assert (n["flujos"][1]["desde_s"], n["flujos"][1]["hasta_s"]) == (1800, 3600)
    assert n["fin_demanda_s"] == 3600 and n["tope_s"] == 7200
    print("1. flujos (8:00 a 9:00): OK")

    # 2. Mismo escenario a otra hora: SUMO simula lo mismo (solo cambia reloj_inicio_s)
    otro = copy.deepcopy(FLUJOS)
    for f in otro["flujos"]:
        f["desde_s"] -= 3600
        f["hasta_s"] -= 3600
    m = normalizar_escenario(otro)
    assert m["reloj_inicio_s"] == 25200
    assert [(f["desde_s"], f["hasta_s"]) for f in m["flujos"]] == [(0, 3600), (1800, 3600)]
    assert m["tope_s"] == n["tope_s"]
    print("2. misma simulación a las 7:00: OK")

    # 3. Modo aleatorio: el ejemplo de la guía (sección 6)
    a = normalizar_escenario(ALEATORIO)
    assert a["modo"] == "aleatorio" and a["fin_demanda_s"] == 3600 and a["tope_s"] == 7200
    assert "reloj_inicio_s" not in a
    print("3. aleatorio: OK")

    # 4. Aleatorio con etiqueta de reloj opcional
    assert normalizar_escenario(con(ALEATORIO, reloj_inicio_s=25200))["reloj_inicio_s"] == 25200
    debe_fallar(con(ALEATORIO, reloj_inicio_s=90000), "reloj_inicio_s")
    print("4. etiqueta de reloj: OK")

    # 5. No se mezclan los modos
    debe_fallar(con(FLUJOS, demanda_vehicular=800), "mezcla")
    debe_fallar(con(FLUJOS, duracion_segundos=3600), "mezcla")
    debe_fallar(con(FLUJOS, porcentaje_pesados=10), "mezcla")
    print("5. mezcla de modos rechazada: OK")

    # 6. None cuenta como ausente
    sin_mezcla = con(FLUJOS, demanda_vehicular=None, duracion_segundos=None, porcentaje_pesados=None,
                     inicio_s=None, fin_s=None)
    assert normalizar_escenario(sin_mezcla)["modo"] == "flujos"
    print("6. campos None = ausentes: OK")

    # 7. inicio_s / fin_s ya no existen
    debe_fallar(con(ALEATORIO, inicio_s=0), "ya no se usan")
    debe_fallar(con(FLUJOS, fin_s=3600), "ya no se usan")
    print("7. campos obsoletos rechazados: OK")

    # 8. Aleatorio: faltantes y rangos
    for campo in ("demanda_vehicular", "porcentaje_pesados", "duracion_segundos"):
        debe_fallar(con(ALEATORIO, **{campo: None}), campo)
    debe_fallar(con(ALEATORIO, duracion_segundos=3599), "entre 3600 y 10800")
    debe_fallar(con(ALEATORIO, duracion_segundos=10801), "entre 3600 y 10800")
    assert normalizar_escenario(con(ALEATORIO, duracion_segundos=10800))["tope_s"] == 14400
    debe_fallar(con(ALEATORIO, demanda_vehicular=0), "mayor que 0")
    debe_fallar(con(ALEATORIO, porcentaje_pesados=101), "entre 0 y 100")
    debe_fallar(con(ALEATORIO, demanda_vehicular="mucho"), "número")
    debe_fallar(con(ALEATORIO, demanda_vehicular=True), "número")
    assert normalizar_escenario(con(ALEATORIO, demanda_vehicular="800"))["demanda_vehicular"] == 800
    print("8. aleatorio: faltantes y rangos: OK")

    # 9. Flujos: ventana inválida invalida el escenario
    debe_fallar(con_flujo(FLUJOS, 0, desde_s=None), "falta desde_s")
    debe_fallar(con_flujo(FLUJOS, 0, hasta_s=28800), "mayor que desde_s")
    debe_fallar(con_flujo(FLUJOS, 1, desde_s=32390), "al menos 60 s")
    debe_fallar(con_flujo(FLUJOS, 0, desde_s=-1), "entre 0 y 86400")
    debe_fallar(con_flujo(FLUJOS, 0, hasta_s=90000), "entre 0 y 86400")
    print("9. ventanas inválidas: OK")

    # 10. Flujos: duración total de 1 a 8 h
    corto = con_flujo(con_flujo(FLUJOS, 0, hasta_s=31000), 1, hasta_s=31000, desde_s=30000)
    debe_fallar(corto, "entre 3600 y 28800")
    largo = con_flujo(FLUJOS, 0, desde_s=21600, hasta_s=50400)          # 8 h exactas
    assert normalizar_escenario(largo)["tope_s"] == 28800 + 3600
    debe_fallar(con_flujo(FLUJOS, 0, desde_s=21600, hasta_s=50401), "entre 3600 y 28800")
    print("10. duración total de flujos: OK")

    # 11. Lo que es de UN flujo no invalida el escenario (lo rechaza escenario_demanda después)
    sin_pesados = copy.deepcopy(FLUJOS)
    del sin_pesados["flujos"][0]["porcentaje_pesados"]
    assert normalizar_escenario(sin_pesados)["modo"] == "flujos"
    print("11. porcentaje_pesados del flujo se valida después: OK")

    # 12. El escenario original no se modifica
    original = copy.deepcopy(FLUJOS)
    normalizar_escenario(FLUJOS)
    assert FLUJOS == original
    print("12. el original no se toca: OK")

    # 13. Un flujo que no es objeto da un error claro, no un crash
    debe_fallar(con(FLUJOS, flujos=["via"]), "debe ser un objeto")
    print("13. flujo mal formado: OK")

    print("\nTodo bien.")


if __name__ == "__main__":
    main()