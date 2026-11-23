"""comparar_escenarios.py: compara escenarios contra uno base."""

# (clave, etiqueta, unidad, ¿más es mejor?)
INDICADORES = [
    ("tiempo_promedio_espera",  "Tiempo promedio de espera",            "s",    False),
    ("espera_total_promedio",   "Espera total (incluye esperar para entrar)", "s", False),
    ("longitud_max_fila",       "Longitud máxima de fila",              "m",    False),
    ("velocidad_promedio",      "Velocidad promedio",                   "km/h", True),
    ("vehiculos_atendidos",     "Vehículos atendidos",                  "veh",  True),
    ("tiempo_perdido_promedio", "Tiempo perdido promedio",              "s",    False),
]


# cambio de porcentaje?
def _cambio_pct(base, valor):
    if base in (None, 0) or valor is None:
        return None
    return round((valor - base) / base * 100, 1)


def comparar_escenarios(resultados, id_base):
    """
    resultados: {"Actual": {indicadores}, ...}; id_base: escenario contra el que se compara.
    Regresa {"base", "filas", "mejor_por_indicador"}. Los indicadores que ningún escenario trae se omiten.
    """
    base = resultados[id_base]
    filas, mejores = [], {}
    for clave, etiqueta, unidad, mas_es_mejor in INDICADORES:
        valores = {n: r.get(clave) for n, r in resultados.items()}
        validos = {n: v for n, v in valores.items() if v is not None}
        if not validos:
            continue
        mejores[clave] = (max if mas_es_mejor else min)(validos, key=validos.get)
        filas.append({"clave": clave, "etiqueta": etiqueta, "unidad": unidad, "mas_es_mejor": mas_es_mejor,
                        "valores": valores,
                        "cambio_pct_vs_base": {n: _cambio_pct(base.get(clave), v) for n, v in valores.items()}})
    return {"base": id_base, "filas": filas, "mejor_por_indicador": mejores}