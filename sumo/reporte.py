"""
reporte_pdf.py: genera el reporte técnico en PDF que compara escenarios.

Entrada: indicadores de cada escenario (un dict por escenario) y el nombre del escenario base.
Salida:  PDF con descripción, tabla, gráficas, puntos críticos (semáforos), conclusiones automáticas,
         advertencias y notas.
"""
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from comparar_escenarios import comparar_escenarios
from indicadores import nivel_de_servicio

AZUL = colors.HexColor("#1F3A5F")
GRIS = colors.HexColor("#F2F4F7")
VERDE, ROJO, GRIS_TXT = "#1B7F3B", "#B3261E", "#777777"
UMBRAL_RETRASO_ENTRADA_S = 5      # a partir de aquí se avisa que la cola salió de la red modelada

# --- Puntos críticos (semáforos) ---
TOP_SEMAFOROS = 5                 # cuántos semáforos salen en la tabla
MIN_VEH_SEMAFORO = 10             # con menos vehículos el promedio no es confiable y no entra al ranking
ZONA_APROXIMACION_M = 100         # debe coincidir con zona_aproximacion_m de simulation_engine.py

_e = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=_e["Heading1"], textColor=AZUL, fontSize=20, spaceAfter=4)
H2 = ParagraphStyle("H2", parent=_e["Heading2"], textColor=AZUL, fontSize=13, spaceBefore=14, spaceAfter=6, keepWithNext=1)
TXT = ParagraphStyle("TXT", parent=_e["Normal"], fontSize=10, leading=14)
CELDA = ParagraphStyle("CELDA", parent=TXT, fontSize=9, leading=11)
CELDA_C = ParagraphStyle("CELDA_C", parent=CELDA, alignment=1)
CELDA_H = ParagraphStyle("CELDA_H", parent=CELDA_C, textColor=colors.white, fontName="Helvetica-Bold")
PEQ = ParagraphStyle("PEQ", parent=TXT, fontSize=8.5, leading=11, textColor=colors.HexColor("#555555"))
AVISO = ParagraphStyle("AVISO", parent=TXT, fontSize=9.5, leading=13, textColor=colors.HexColor("#8A4B00"))


# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------
def _num(v):
    return "N/D" if v is None else f"{v:,.1f}".rstrip("0").rstrip(".")


def _fmt(v, unidad=""):
    if v is None:
        return "N/D"
    texto = _num(v)
    return f"{texto} {unidad}".strip()


def _clave_principal(resultados):
    """La espera total si todos los escenarios la traen; si no, la espera que reporta SUMO."""
    if all(r.get("espera_total_promedio") is not None for r in resultados.values()):
        return "espera_total_promedio"
    return "tiempo_promedio_espera"


def _mejora(fila, n):
    cambio = fila["cambio_pct_vs_base"].get(n)
    if cambio is None:
        return None
    return cambio if fila["mas_es_mejor"] else -cambio


# ---------------------------------------------------------------------
# Semáforos (puntos críticos)
# ---------------------------------------------------------------------
def _etiqueta_semaforo(tls_id, datos):
    """Celda de la tabla: nombre de la calle y el id en chico debajo (solo el id si no hay nombre)."""
    nombre = escape(datos.get("nombre") or "")
    if not nombre:
        return escape(tls_id)
    return f'<b>{nombre}</b><br/><font size="7" color="{GRIS_TXT}">{escape(tls_id)}</font>'


def _descripcion_semaforo(tls_id, datos):
    """Para frases: 'el semáforo <b>Calle</b> (id)' o solo el id si no hay nombre."""
    nombre = escape(datos.get("nombre") or "")
    return f"<b>{nombre}</b> ({escape(tls_id)})" if nombre else f"<b>{escape(tls_id)}</b>"


def _semaforo_valido(res, tls_id):
    """Datos del semáforo en ese escenario, o None si no existe o tuvo muy poco tráfico."""
    d = (res.get("semaforos") or {}).get(tls_id)
    if d is None or d.get("vehiculos", 0) < MIN_VEH_SEMAFORO:
        return None
    return d


def _semaforos_criticos(res):
    """[(tls_id, datos)] del escenario, de mayor a menor retraso promedio, solo con tráfico suficiente."""
    validos = [(t, d) for t, d in (res.get("semaforos") or {}).items() if _semaforo_valido(res, t)]
    return sorted(validos, key=lambda x: -x[1]["retraso_promedio_s"])


def _cambio_semaforo(d_base, d):
    """Cambio porcentual del retraso promedio respecto al base (None si el base es 0)."""
    base = d_base["retraso_promedio_s"]
    if not base:
        return None
    return (d["retraso_promedio_s"] - base) / base * 100


def _tabla_semaforos(resultados, nombres, id_base):
    """Top de semáforos del escenario base y cómo cambian en los demás. None si no hay datos."""
    ranking = _semaforos_criticos(resultados[id_base])[:TOP_SEMAFOROS]
    if not ranking:
        return None

    un_solo = len(nombres) == 1
    ancho_id = 5 * cm
    ancho_col = (17.5 * cm - ancho_id) / len(nombres)

    encabezado = [Paragraph("Semáforo", CELDA_H)] + [
        Paragraph(n + (" (base)" if n == id_base and not un_solo else ""), CELDA_H) for n in nombres]
    datos = [encabezado]

    for tls_id, d_base in ranking:
        celdas = [Paragraph(_etiqueta_semaforo(tls_id, d_base), CELDA)]
        for n in nombres:
            d = _semaforo_valido(resultados[n], tls_id)
            if d is None:
                celdas.append(Paragraph("N/D", CELDA_C))
                continue
            ret = d["retraso_promedio_s"]
            texto = f"{_num(ret)} s (nivel {nivel_de_servicio(ret)})<br/>{d['vehiculos']} veh"
            if n != id_base:
                cambio = _cambio_semaforo(d_base, d)
                if cambio is not None and abs(cambio) >= 0.05:
                    color = VERDE if cambio < 0 else ROJO      # menos retraso = mejora
                    texto += f'<br/><font color="{color}" size="8">{cambio:+.1f} %</font>'
            celdas.append(Paragraph(texto, CELDA_C))
        datos.append(celdas)

    t = Table(datos, colWidths=[ancho_id] + [ancho_col] * len(nombres), repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9CED6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def _frase_semaforos(resultados, nombres, id_base):
    """Una frase: cuál es el semáforo más crítico del base y cómo cambia en cada alternativa."""
    ranking = _semaforos_criticos(resultados[id_base])
    if not ranking:
        return None
    tls_id, d_base = ranking[0]
    ret = d_base["retraso_promedio_s"]
    texto = (f"En <b>{id_base}</b> el punto más crítico es el semáforo {_descripcion_semaforo(tls_id, d_base)}, con un retraso promedio de "
             f"{_num(ret)} s en la zona de aproximación (nivel {nivel_de_servicio(ret)}).")
    for n in nombres:
        if n == id_base:
            continue
        d = _semaforo_valido(resultados[n], tls_id)
        if d is None:
            texto += f" En <b>{n}</b> ese semáforo no tiene tráfico suficiente para compararse."
            continue
        cambio = _cambio_semaforo(d_base, d)
        if cambio is None or abs(cambio) < 0.5:
            texto += f" En <b>{n}</b> se mantiene prácticamente igual."
        else:
            verbo = "baja" if cambio < 0 else "sube"
            texto += f" En <b>{n}</b> {verbo} a {_num(d['retraso_promedio_s'])} s ({cambio:+.0f} %)."
    return texto


# ---------------------------------------------------------------------
# Texto automático
# ---------------------------------------------------------------------
def _frase_escenario(comp, resultados, escenario, principal):
    """Resume qué mejoró y qué empeoró (todos los indicadores clave)."""
    nombres = {principal: "la espera total" if principal == "espera_total_promedio" else "la espera",
               "tiempo_promedio_espera": "la espera dentro de la red",
               "longitud_max_fila": "la longitud máxima de fila",
               "velocidad_promedio": "la velocidad promedio"}
    mejoras, empeoras = [], []
    for fila in comp["filas"]:
        if fila["clave"] not in nombres:
            continue
        cambio = fila["cambio_pct_vs_base"].get(escenario)
        if cambio is None or abs(cambio) < 0.05:
            continue
        texto = f"{'aumentó' if cambio > 0 else 'redujo'} {nombres[fila['clave']]} en {abs(cambio):.0f} %"
        (mejoras if _mejora(fila, escenario) > 0 else empeoras).append(texto)

    def unir(partes):
        return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]

    if mejoras and empeoras:
        frase = f"El escenario <b>{escenario}</b> {unir(mejoras)}, pero {unir(empeoras)}."
    elif mejoras:
        frase = f"El escenario <b>{escenario}</b> {unir(mejoras)}."
    elif empeoras:
        frase = f"El escenario <b>{escenario}</b> <b>empeoró</b> frente al base: {unir(empeoras)}."
    else:
        frase = f"El escenario <b>{escenario}</b> no muestra diferencias claras frente al base."
    return frase


def _recomendacion(comp, resultados, principal):
    fila = next(f for f in comp["filas"] if f["clave"] == principal)
    base = comp["base"]
    validos = {n: v for n, v in fila["valores"].items() if v is not None}
    if base not in validos:
        return None
    orden = sorted((n for n in validos if n != base), key=validos.get)
    if not orden or validos[orden[0]] >= validos[base]:
        return "Ninguna alternativa mejora la espera del escenario base."
    mejor = orden[0]
    texto = (f"Con el criterio de menor tiempo de espera, la alternativa con mejor desempeño es <b>{mejor}</b>. ")
    return texto + "La decisión final debe considerar también el costo y la factibilidad de cada intervención."


def avisos_de(res, principal="espera_total_promedio"):
    """Advertencias de calidad de un escenario (lista de textos)."""
    avisos = []
    if res.get("termino_completo") is False:
        avisos.append("la simulación no terminó completa: hay vehículos que no entran en los promedios.")
    tele = res.get("vehiculos_teletransportados") or 0
    if tele > 0:
        detalle = f"({tele:g} vehículo(s) en la corrida)"
        avisos.append(f"SUMO teletransportó vehículos por atasco {detalle}: hay congestión severa "
                      f"y los promedios son poco confiables.")
    ret = res.get("retraso_entrada_promedio") or 0
    if ret >= UMBRAL_RETRASO_ENTRADA_S:
        avisos.append(f"los vehículos esperaron en promedio {ret:.0f} s para entrar a la red: la cola rebasó el tramo "
                      f"modelado. La longitud máxima de fila es solo un mínimo y la 'espera total' es la medida "
                      f"más representativa.")
    return avisos


# ---------------------------------------------------------------------
# Bloques del documento
# ---------------------------------------------------------------------
def _tabla(comp, resultados, nombres):
    ancho_ind = 5 * cm
    ancho_col = (17.5 * cm - ancho_ind) / len(nombres)
    datos = [[Paragraph("Indicador", CELDA_H)] +
             [Paragraph(n + (" (base)" if n == comp["base"] else ""), CELDA_H) for n in nombres]]
    for fila in comp["filas"]:
        celdas = [Paragraph(fila["etiqueta"], CELDA)]
        for n in nombres:
            texto = _fmt(fila["valores"][n], fila["unidad"])
            mejora = _mejora(fila, n)
            if n != comp["base"] and mejora is not None and abs(mejora) >= 0.05:
                color = VERDE if mejora > 0 else ROJO
                texto += f'<br/><font color="{color}" size="8">{fila["cambio_pct_vs_base"][n]:+.1f} %</font>'
            celdas.append(Paragraph(texto, CELDA_C))
        datos.append(celdas)
    if any(resultados[n].get("nivel_de_servicio") for n in nombres):
        datos.append([Paragraph("Nivel de servicio (aprox.)", CELDA)] +
                     [Paragraph(resultados[n].get("nivel_de_servicio") or "N/D", CELDA_C) for n in nombres])
    t = Table(datos, colWidths=[ancho_ind] + [ancho_col] * len(nombres), repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9CED6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def _grafica(titulo, unidad, valores, nombres, color):
    d = Drawing(8.5 * cm, 6 * cm)
    d.add(String(4.25 * cm, 5.5 * cm, f"{titulo} ({unidad})", fontSize=9, textAnchor="middle",
                 fontName="Helvetica-Bold"))
    g = VerticalBarChart()
    g.x, g.y, g.width, g.height = 1.2 * cm, 1.4 * cm, 6.9 * cm, 3.7 * cm
    g.data = [[valores[n] or 0 for n in nombres]]
    g.categoryAxis.categoryNames = [n if len(n) <= 14 else n[:13] + "." for n in nombres]
    g.categoryAxis.labels.fontSize = 7
    g.categoryAxis.labels.dy = -2
    g.valueAxis.labels.fontSize = 7
    g.valueAxis.valueMin = 0
    g.bars[0].fillColor = color
    g.barLabelFormat = "%s"
    g.barLabels.fontSize = 7
    g.barLabels.nudge = 6
    d.add(g)
    return d


def _graficas(comp, nombres, principal):
    por_clave = {f["clave"]: f for f in comp["filas"]}
    pares = []
    for clave, color in ((principal, AZUL), ("longitud_max_fila", colors.HexColor("#D9822B"))):
        if clave in por_clave:
            f = por_clave[clave]
            pares.append(_grafica(f["etiqueta"] if clave != principal else "Espera", f["unidad"],
                                  f["valores"], nombres, color))
    t = Table([pares], colWidths=[8.75 * cm] * len(pares))
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t


def _ruta_escribible(ruta):
    """Si el PDF está abierto (visor, OneDrive), lo guarda con la hora en el nombre en lugar de fallar."""
    try:
        with open(ruta, "ab"):
            return ruta
    except PermissionError:
        p = Path(ruta)
        alterna = p.with_name(f"{p.stem}_{datetime.now():%H%M%S}{p.suffix}")
        print(f"AVISO: no se pudo escribir {ruta} (¿está abierto?). Se guarda como {alterna}")
        return alterna


def _pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(2 * cm, 1.2 * cm, "Plataforma de Gemelos Digitales - Reporte técnico")
    canvas.drawRightString(letter[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------------
# PUNTO DE ENTRADA
# ---------------------------------------------------------------------
def _resumen_individual(res, principal):
    """Texto de un escenario solo: qué registró y qué tan congestionado está."""
    partes = []
    esp_tot, esp_red, ret = res.get("espera_total_promedio"), res.get("tiempo_promedio_espera"), res.get("retraso_entrada_promedio")
    if esp_tot is not None and esp_red is not None and ret:
        partes.append(f"una espera total promedio de {_num(esp_tot)} s ({_num(esp_red)} s dentro de la red y "
                      f"{_num(ret)} s esperando para entrar)")
    elif esp_red is not None:
        partes.append(f"una espera promedio de {_num(esp_red)} s")
    if res.get("velocidad_promedio") is not None:
        partes.append(f"una velocidad promedio de {_num(res['velocidad_promedio'])} km/h")
    if res.get("longitud_max_fila") is not None:
        partes.append(f"una longitud máxima de fila de {_num(res['longitud_max_fila'])} m")
    if res.get("vehiculos_atendidos") is not None:
        partes.append(f"{_num(res['vehiculos_atendidos'])} vehículos atendidos")
    if not partes:
        return "No hay indicadores suficientes para resumir el escenario."
    texto = "El escenario registró " + (partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]) + "."
    los = res.get("nivel_de_servicio")
    if los:
        desc = "operación fluida" if los in "ABC" else ("operación con demoras" if los == "D" else "operación congestionada")
        texto += f" El nivel de servicio aproximado es <b>{los}</b> ({desc})."
    return texto


def generar_reporte_pdf(resultados, id_base, ruta_pdf, titulo=None, descripciones=None, configuraciones=None,
                        semilla=None, duracion_s=None, zona=None):
    """
    resultados:      {"Actual": {indicadores}, ...}. Con UN escenario sale una ficha; con varios, una comparación.
    id_base:         escenario contra el que se compara (con uno solo, ese mismo)
    descripciones:   {"Actual": "texto corto"} (opcional)
    configuraciones: {"Actual": ["Flujo ...", "Semáforo ..."]} (opcional; ver gestion_reportes.describir_configuracion)
    semilla:         semilla de la corrida
    Regresa la ruta final del PDF (puede cambiar si el archivo estaba abierto).
    """
    if id_base not in resultados:
        raise ValueError(f"El escenario base '{id_base}' no está en los resultados")
    un_solo = len(resultados) == 1
    titulo = titulo or ("Reporte técnico del escenario" if un_solo else "Evaluación de escenarios de operación vial")
    descripciones, configuraciones = descripciones or {}, configuraciones or {}
    comp = comparar_escenarios(resultados, id_base)
    nombres = [id_base] + [n for n in resultados if n != id_base]
    principal = _clave_principal(resultados)
    num = iter(range(1, 20))

    ruta_pdf = _ruta_escribible(ruta_pdf)
    doc = SimpleDocTemplate(str(ruta_pdf), pagesize=letter, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title=titulo,
                            author="Plataforma de Gemelos Digitales")
    h = [Paragraph(titulo, H1)]
    sub = [f"Generado el {datetime.now():%d/%m/%Y %H:%M}"] + ([f"Zona de estudio: {zona}"] if zona else [])
    h += [Paragraph(" | ".join(sub), PEQ), Spacer(1, 10)]

    h.append(Paragraph(f"{next(num)}. {'Escenario analizado' if un_solo else 'Escenarios analizados'}", H2))
    for n in nombres:
        etiqueta = " (escenario base)" if (n == id_base and not un_solo) else ""
        desc = descripciones.get(n)
        h.append(Paragraph(f"<b>{n}</b>{etiqueta}" + (f": {desc}" if desc else ""), TXT))
        for linea in configuraciones.get(n, []):
            h.append(Paragraph("- " + linea, PEQ))
        h.append(Spacer(1, 5))

    h.append(Paragraph(f"{next(num)}. {'Indicadores' if un_solo else 'Comparación de indicadores'}", H2))
    h.append(_tabla(comp, resultados, nombres))
    if un_solo:
        leyenda = "Indicadores de una simulación del escenario."
    else:
        leyenda = (f"Los porcentajes son el cambio respecto a <b>{id_base}</b>. "
                   f'<font color="{VERDE}">Verde</font> = mejora, <font color="{ROJO}">rojo</font> = empeora.')
    h.append(Paragraph(leyenda, PEQ))

    if not un_solo:
        h += [Paragraph(f"{next(num)}. Gráficas", H2), _graficas(comp, nombres, principal)]

    # --- Puntos críticos: solo aparece si algún semáforo tuvo tráfico suficiente ---
    tabla_semaforos = _tabla_semaforos(resultados, nombres, id_base)
    if tabla_semaforos is not None:
        h += [Paragraph(f"{next(num)}. Puntos críticos (semáforos)", H2), tabla_semaforos]
        leyenda = (f"Los {TOP_SEMAFOROS} semáforos con mayor retraso promedio"
                   f"{'' if un_solo else f' en {id_base}'}. Solo se consideran semáforos con al menos "
                   f"{MIN_VEH_SEMAFORO} vehículos.")
        if not un_solo:
            leyenda += (f' Los porcentajes son el cambio respecto a <b>{id_base}</b>: '
                        f'<font color="{VERDE}">verde</font> = menos retraso, <font color="{ROJO}">rojo</font> = más.')
        h.append(Paragraph(leyenda, PEQ))
        h += [Spacer(1, 4), Paragraph(_frase_semaforos(resultados, nombres, id_base), TXT)]

    h.append(Paragraph(f"{next(num)}. {'Resumen' if un_solo else 'Conclusiones'}", H2))
    if un_solo:
        h.append(Paragraph(_resumen_individual(resultados[id_base], principal), TXT))
    else:
        for n in nombres:
            if n != id_base:
                h += [Paragraph(_frase_escenario(comp, resultados, n, principal), TXT), Spacer(1, 3)]
        rec = _recomendacion(comp, resultados, principal)
        if rec:
            h += [Spacer(1, 4), Paragraph(rec, TXT)]

    avisos = [(n, a) for n in nombres for a in avisos_de(resultados[n], principal)]
    if avisos:
        h.append(Paragraph(f"{next(num)}. Advertencias de calidad", H2))
        for n, a in avisos:
            h.append(Paragraph(f"- <b>{n}</b>: {a}", AVISO))
        h.append(Spacer(1, 2))

    h.append(Paragraph(f"{next(num)}. Notas metodológicas", H2))
    notas = ["Los resultados provienen de simulación microscópica con SUMO a partir de una red importada de OpenStreetMap.",
             "El nivel de servicio se estima con el tiempo perdido promedio de todo el recorrido, no solo en la intersección; "
             "es una aproximación a los umbrales del HCM.",
             "'Espera total' suma la espera dentro de la red y la espera para poder entrar a ella (cola fuera del tramo modelado)."]
    if tabla_semaforos is not None:
        notas.append(f"El retraso por semáforo se mide en los últimos {ZONA_APROXIMACION_M} m antes de la línea de alto "
                     f"(tiempo perdido respecto a la velocidad permitida), y su nivel de servicio es una aproximación "
                     f"a los umbrales del HCM. Los identificadores son los de la red importada.")
    if semilla is not None:
        notas.append(f"Semilla aleatoria: {semilla}. Una sola corrida por escenario: diferencias pequeñas pueden "
                     f"deberse a variación aleatoria.")
    if duracion_s:
        notas.append(f"Duración simulada: {duracion_s / 60:.0f} min.")
    h += [Paragraph("- " + t, PEQ) for t in notas]

    doc.build(h, onFirstPage=_pie, onLaterPages=_pie)
    return ruta_pdf