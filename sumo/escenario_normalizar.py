"""
escenario_normalizar.py: decide el modo  de  la demanda del escenario y calcula su TIEMPO.

Ver GUIA_DEMANDA.md. En resumen:
- Hay dos modos que NO se mezclan: "aleatorio" (sin flujos) o "flujos".
- Todo el tiempo de entrada viene en segundos desde la medianoche (7:00 = 25200).
- La simulación arranca en el segundo 0. En modo flujos, el segundo 0 es la hora de
  inicio más temprana de todos los flujos (se "recorre el reloj").
- El tiempo se calcula AQUÍ y solo aquí: de aquí salen el fin de la demanda y el tope
  que se pasan al .sumocfg y al motor.

Este módulo no lee ni escribe archivos y no corre SUMO: solo valida y calcula.
Un escenario inválido lanza ValueError con el motivo  por lo tanto no se simula nada.
"""

import copy
import math

DIA_S = 86400
DRENAJE_S = 3600                     # tiempo extra después de la demanda para que terminen los últimos viajes


ALEATORIO_MIN_S, ALEATORIO_MAX_S = 3600, 10800     # 1 a 3 h
FLUJOS_MIN_S, FLUJOS_MAX_S = 3600, 28800           # 1 a 8 h (duración total: mayor hasta_s - menor desde_s)
VENTANA_FLUJO_MIN_S = 60                           # mínimo técnico de la ventana de UN flujo

CAMPOS_ALEATORIO = ("demanda_vehicular", "porcentaje_pesados", "duracion_segundos")
CAMPOS_OBSOLETOS = ("inicio_s", "fin_s")           # ya no existen: cada flujo trae sus desde_s / hasta_s


# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------
def _tiene_campo(escenario, campo):
    """Un campo con valor None cuenta como ausente (el frontend a veces manda los vacíos así)."""
    return escenario.get(campo) is not None


def _numero(valor, nombre):
    """Convierte a número (int si es exacto) o lanza ValueError. Rechaza booleanos, NaN e infinitos."""
    if isinstance(valor, bool):
        raise ValueError(f"{nombre} debe ser un número")
    try:
        x = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{nombre} debe ser un número (llegó {valor!r})") from None
    if not math.isfinite(x):
        raise ValueError(f"{nombre} debe ser un número finito")
    return int(x) if x.is_integer() else x


def _reloj_valido(valor):
    """Valida reloj_inicio_s (segundos desde la medianoche)."""
    reloj = _numero(valor, "reloj_inicio_s")
    if not 0 <= reloj < DIA_S:
        raise ValueError(f"reloj_inicio_s debe estar entre 0 y {DIA_S} s")
    return reloj


# ---------------------------------------------------------------------
# Modo
# ---------------------------------------------------------------------
def detectar_modo(escenario):
    """
    "flujos" si el escenario trae flujos; si no, "aleatorio".
    Mezclar los dos modos es un error: nada se ignora en silencio.
    """
    if not escenario.get("flujos"):
        return "aleatorio"
    sobran = [c for c in CAMPOS_ALEATORIO if _tiene_campo(escenario, c)]
    if sobran:
        raise ValueError(f"el escenario mezcla demanda aleatoria y flujos (sobran: {', '.join(sobran)}). "
                         "Usa solo uno de los dos modos.")
    return "flujos"


# ---------------------------------------------------------------------
# Cada modo
# ---------------------------------------------------------------------
def _normalizar_aleatorio(salida):
    """Valida los tres datos del modo aleatorio y fija el fin de la demanda."""
    faltan = [c for c in CAMPOS_ALEATORIO if not _tiene_campo(salida, c)]
    if faltan:
        raise ValueError(f"modo aleatorio: faltan {', '.join(faltan)}")

    demanda = _numero(salida["demanda_vehicular"], "demanda_vehicular")
    pesados = _numero(salida["porcentaje_pesados"], "porcentaje_pesados")
    duracion = _numero(salida["duracion_segundos"], "duracion_segundos")

    if demanda <= 0:
        raise ValueError("demanda_vehicular debe ser mayor que 0 (vehículos por hora)")
    if not 0 <= pesados <= 100:
        raise ValueError("porcentaje_pesados debe estar entre 0 y 100")
    if not ALEATORIO_MIN_S <= duracion <= ALEATORIO_MAX_S:
        raise ValueError(f"duracion_segundos debe estar entre {ALEATORIO_MIN_S} y {ALEATORIO_MAX_S} s "
                         f"(de 1 a 3 horas simuladas)")

    if _tiene_campo(salida, "reloj_inicio_s"):          # etiqueta opcional: no cambia la simulación
        salida["reloj_inicio_s"] = _reloj_valido(salida["reloj_inicio_s"])
    salida.update(demanda_vehicular=demanda, porcentaje_pesados=pesados, duracion_segundos=duracion,
                  fin_demanda_s=duracion)


def _ventana_de(flujo, nombre):
    """(desde_s, hasta_s) de un flujo, validada. Una ventana mala invalida el escenario: define el tiempo."""
    if not isinstance(flujo, dict):
        raise ValueError(f"flujo {nombre}: debe ser un objeto")
    for campo in ("desde_s", "hasta_s"):
        if not _tiene_campo(flujo, campo):
            raise ValueError(f"flujo {nombre}: falta {campo}")
    desde = _numero(flujo["desde_s"], f"flujo {nombre}: desde_s")
    hasta = _numero(flujo["hasta_s"], f"flujo {nombre}: hasta_s")

    if desde < 0 or hasta > DIA_S:
        raise ValueError(f"flujo {nombre}: desde_s y hasta_s deben estar entre 0 y {DIA_S} s")
    if hasta <= desde:
        raise ValueError(f"flujo {nombre}: hasta_s debe ser mayor que desde_s")
    if hasta - desde < VENTANA_FLUJO_MIN_S:
        raise ValueError(f"flujo {nombre}: la ventana debe durar al menos {VENTANA_FLUJO_MIN_S} s")
    return desde, hasta


def _normalizar_flujos(salida):
    """Recorre el reloj: el inicio más temprano pasa a ser el segundo 0. Fija reloj_inicio_s y fin_demanda_s."""
    flujos = salida["flujos"]
    ventanas = [_ventana_de(f, f.get("id", f"#{i + 1}") if isinstance(f, dict) else f"#{i + 1}")
                for i, f in enumerate(flujos)]

    inicio = min(d for d, _ in ventanas)
    fin = max(h for _, h in ventanas)
    duracion = fin - inicio
    if not FLUJOS_MIN_S <= duracion <= FLUJOS_MAX_S:
        raise ValueError(f"la duración total de los flujos debe estar entre {FLUJOS_MIN_S} y {FLUJOS_MAX_S} s "
                         f"(de 1 a 8 horas); los flujos cubren {duracion} s")

    for flujo, (desde, hasta) in zip(flujos, ventanas):
        flujo["desde_s"], flujo["hasta_s"] = desde - inicio, hasta - inicio

    salida["reloj_inicio_s"] = inicio        # en modo flujos siempre se calcula (se sobreescribe el que llegue)
    salida["fin_demanda_s"] = duracion


# ---------------------------------------------------------------------
# PUNTO DE ENTRADA
# ---------------------------------------------------------------------
def normalizar_escenario(escenario):
    """
    Regresa una COPIA del escenario con el modo y el tiempo ya calculados (el original no se toca):
        modo             "aleatorio" | "flujos"
        fin_demanda_s    segundo en que termina la demanda (la simulación empieza en 0)
        tope_s           fin_demanda_s + DRENAJE_S
        reloj_inicio_s   hora del día (segundos desde la medianoche) que corresponde al segundo 0;
                         en modo flujos los desde_s / hasta_s de cada flujo quedan RECORRIDOS (relativos a ese 0).
                         En modo aleatorio es opcional y solo es una etiqueta.
    Lanza ValueError con el motivo si el escenario no es válido.

    Lo que NO se valida aquí (lo hace escenario_demanda al planear cada flujo, y se rechaza el flujo, no el
    escenario): que existan los tramos, que haya ruta, vehiculos_por_hora y porcentaje_pesados del flujo.
    """
    obsoletos = [c for c in CAMPOS_OBSOLETOS if _tiene_campo(escenario, c)]

    if obsoletos:
        raise ValueError(f"campos que ya no se usan: {', '.join(obsoletos)}. La duración sale de desde_s / hasta_s "
                         "de cada flujo (modo flujos) o de duracion_segundos (modo aleatorio).")

    modo = detectar_modo(escenario)
    salida = copy.deepcopy(escenario)
    salida["modo"] = modo

    if modo == "aleatorio":
        _normalizar_aleatorio(salida)
    else:
        _normalizar_flujos(salida)

    salida["tope_s"] = salida["fin_demanda_s"] + DRENAJE_S
    return salida