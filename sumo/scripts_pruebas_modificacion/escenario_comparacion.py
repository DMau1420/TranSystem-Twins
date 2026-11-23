"""
escenario_comparacion.py: compara escenarios contra una BASE.

Entrada: una lista de resultados, el primero (por defecto) es la base:
    [{"nombre": "A. Actual", "indicadores": {...de procesar_resultados...}, "cambios": {...reporte_cambios...}}, ...]

Salida: para cada indicador (global, por flujo y por semáforo) el valor en cada escenario, el cambio
contra la base y un veredicto: "mejora", "empeora" o "sin cambio significativo".

Un cambio es SIGNIFICATIVO si supera el 2 % de la base Y un mínimo absoluto (0.5 s, 2 m, 1 veh...).
Son umbrales de convención: con una sola corrida determinista no hay estadística. Medimos que el ruido de
reconstruir la red es de décimas de segundo (~1 % incluso con la vía saturada). Con repeticiones por
semilla, estos umbrales se reemplazan por intervalos de confianza.

El comparador NO inventa diferencias: si una intervención no cambia nada, lo dice y explica por qué.
"""
import json
from pathlib import Path

# (clave, etiqueta, unidad, qué es mejor, cambio mínimo absoluto)
INDICADORES_GLOBALES = [
    ("tiempo_promedio_recorrido", "Tiempo de recorrido promedio", "s", "menor", 0.5),
    ("tiempo_promedio_espera", "Espera promedio", "s", "menor", 0.5),
    ("velocidad_promedio", "Velocidad promedio", "km/h", "mayor", 0.5),
    ("longitud_max_fila", "Longitud máxima de fila", "m", "menor", 2.0),
    ("vehiculos_atendidos", "Vehículos completados", "veh", "mayor", 1),
]
INDICADORES_FLUJO = [
    ("tiempo_total_promedio", "Tiempo total", "s", "menor", 0.5),
    ("espera_promedio", "Espera", "s", "menor", 0.5),
    ("retraso_entrada_promedio", "Retraso de entrada", "s", "menor", 0.5),
    ("vehiculos_completados", "Completados", "veh", "mayor", 1),
]
INDICADOR_SEMAFORO = ("retraso_promedio_s", "Retraso", "s", "menor", 0.5)
UMBRAL_RELATIVO = 0.02


# =====================================================================
# PUNTO DE ENTRADA
# =====================================================================
def comparar(resultados, indice_base=0, umbral_relativo=UMBRAL_RELATIVO):
    """Regresa {"base", "escenarios", "filas", "resumen", "avisos"} (todo serializable a JSON)."""
    nombres = [r["nombre"] for r in resultados]
    filas = _filas_globales(resultados) + _filas_por_flujo(resultados) + _filas_semaforos(resultados)
    for fila in filas:
        fila["evaluacion"] = _evaluar(fila, indice_base, umbral_relativo)
    resumen = _resumir(filas, nombres, indice_base)
    avisos = _avisos(resultados, indice_base) + _aviso_sin_cambios(resumen, nombres, indice_base)
    return {"base": nombres[indice_base], "escenarios": nombres, "filas": filas,
            "resumen": resumen, "avisos": avisos}


# =====================================================================
# FILAS: qué se compara
# =====================================================================
def _fila(grupo, spec, valores):
    clave, etiqueta, unidad, mejor, minimo = spec
    return {"grupo": grupo, "etiqueta": etiqueta, "unidad": unidad, "mejor": mejor,
            "minimo": minimo, "valores": valores}


def _filas_globales(resultados):
    return [_fila("Global", spec, [(r["indicadores"] or {}).get(spec[0]) for r in resultados])
            for spec in INDICADORES_GLOBALES]


def _filas_por_flujo(resultados):
    ids = []
    for r in resultados:                         # unión de flujos, en orden de aparición
        for fid in ((r["indicadores"] or {}).get("flujos") or {}):
            if fid not in ids:
                ids.append(fid)
    filas = []
    for fid in ids:
        for spec in INDICADORES_FLUJO:
            valores = [(((r["indicadores"] or {}).get("flujos") or {}).get(fid) or {}).get(spec[0])
                       for r in resultados]
            filas.append(_fila(f"Flujo {fid}", spec, valores))
    return filas


def _filas_semaforos(resultados):
    """Solo semáforos con muestra suficiente (>= 30 vehículos) en algún escenario."""
    def semaforos(r):
        return (r["indicadores"] or {}).get("semaforos") or {}
    ids = []
    for r in resultados:
        for tl, s in semaforos(r).items():
            if s.get("muestra_suficiente") and tl not in ids:
                ids.append(tl)
    return [_fila(f"Semáforo {tl}", INDICADOR_SEMAFORO,
                  [(semaforos(r).get(tl) or {}).get("retraso_promedio_s")
                   if (semaforos(r).get(tl) or {}).get("muestra_suficiente") else None
                   for r in resultados])
            for tl in ids]


# =====================================================================
# EVALUAR: cambio contra la base y veredicto
# =====================================================================
def _evaluar(fila, indice_base, umbral_relativo):
    base = fila["valores"][indice_base]
    evaluacion = []
    for i, valor in enumerate(fila["valores"]):
        if i == indice_base:
            evaluacion.append(None)
        elif valor is None or base is None:
            evaluacion.append({"veredicto": "sin dato"})
        else:
            cambio = valor - base
            significativo = abs(cambio) >= max(fila["minimo"], umbral_relativo * abs(base))
            if not significativo:
                veredicto = "sin cambio significativo"
            else:
                veredicto = "mejora" if (cambio < 0) == (fila["mejor"] == "menor") else "empeora"
            evaluacion.append({"cambio": round(cambio, 2),
                               "cambio_pct": round(cambio / base * 100, 1) if base else None,
                               "veredicto": veredicto})
    return evaluacion


def _resumir(filas, nombres, indice_base):
    """Por escenario: cuántos indicadores mejoran, empeoran o no cambian contra la base."""
    resumen = {}
    for i, nombre in enumerate(nombres):
        if i == indice_base:
            continue
        veredictos = [f["evaluacion"][i]["veredicto"] for f in filas]
        resumen[nombre] = {"mejoran": veredictos.count("mejora"), "empeoran": veredictos.count("empeora"),
                           "sin_cambio": veredictos.count("sin cambio significativo")}
    return resumen


# =====================================================================
# AVISOS: cuándo NO fiarse de la comparación
# =====================================================================
def _avisos(resultados, indice_base):
    avisos = []
    base_flujos = _flujos_esperados(resultados[indice_base])
    for i, r in enumerate(resultados):
        nombre, ind = r["nombre"], r["indicadores"]
        if ind is None:
            avisos.append(f"{nombre}: la simulación no produjo resultados.")
            continue
        if ind.get("termino_completo") is False:
            avisos.append(f"{nombre}: no terminó antes del tope; los promedios excluyen a los vehículos que no terminaron.")
        if ind.get("vehiculos_teletransportados"):
            avisos.append(f"{nombre}: SUMO teletransportó {ind['vehiculos_teletransportados']} vehículo(s) por atasco.")
        if _flujos_esperados(r) != base_flujos:
            avisos.append(f"{nombre}: sus flujos no coinciden con los de la base; la comparación no es válida.")
        for fid, f in (ind.get("flujos") or {}).items():
            if f["vehiculos_completados"] < f["vehiculos_esperados"]:
                avisos.append(f"{nombre}: del flujo {fid} terminaron {f['vehiculos_completados']} de {f['vehiculos_esperados']}.")
        cambios = r.get("cambios") or {}
        for rechazo in cambios.get("rechazados", []):
            avisos.append(f"{nombre}: cambio RECHAZADO en {rechazo['id']}: {rechazo['motivo']}")
        if i != indice_base and "cambios" in r and not cambios.get("aplicados"):
            avisos.append(f"{nombre}: no se aplicó ningún cambio; equivale a la base.")
    return avisos


def _flujos_esperados(resultado):
    flujos = (resultado["indicadores"] or {}).get("flujos") or {}
    return {fid: (f["origen"], f["destino"], f["vehiculos_esperados"]) for fid, f in flujos.items()}


def _aviso_sin_cambios(resumen, nombres, indice_base):
    if resumen and all(r["mejoran"] + r["empeoran"] == 0 for r in resumen.values()):
        return ["Ninguna intervención cambió los resultados de forma significativa. Suele pasar cuando la demanda "
                "está por debajo de la capacidad de lo que se modificó, o cuando ningún flujo cruza lo modificado. "
                "No es un error del sistema."]
    return []


# =====================================================================
# SALIDA
# =====================================================================
def _celda(valor, ev):
    if valor is None:
        return "-"
    if ev is None:
        return f"{valor:g}"
    if "cambio_pct" not in ev:
        return f"{valor:g}"
    marca = {"mejora": "mejora", "empeora": "EMPEORA", "sin cambio significativo": "="}[ev["veredicto"]]
    detalle = f"{ev['cambio_pct']:+.1f}% {marca}" if ev["cambio_pct"] is not None else marca
    return f"{valor:g} ({detalle})"


def imprimir_comparacion(c, ancho=26):
    nombres = c["escenarios"]
    print("\n" + "=" * (36 + ancho * len(nombres)))
    print(f"{'COMPARACIÓN (base: ' + c['base'] + ')':<36}" + "".join(f"{n:<{ancho}}" for n in nombres))
    print("=" * (36 + ancho * len(nombres)))
    grupo = None
    for fila in c["filas"]:
        if fila["grupo"] != grupo:
            grupo = fila["grupo"]
            print(f"\n[{grupo}]")
        celdas = "".join(f"{_celda(v, e):<{ancho}}" for v, e in zip(fila["valores"], fila["evaluacion"]))
        print(f"  {fila['etiqueta'] + ' (' + fila['unidad'] + ')':<34}{celdas}")
    print("\nResumen (indicadores que cambian de forma significativa):")
    for nombre, r in c["resumen"].items():
        print(f"  {nombre}: {r['mejoran']} mejoran, {r['empeoran']} empeoran, {r['sin_cambio']} sin cambio")
    for aviso in c["avisos"]:
        print(f"  AVISO: {aviso}")


def guardar_comparacion(c, ruta):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(c, indent=2, ensure_ascii=False), encoding="utf-8")