"""
gestion_reportes.py: guarda el resultado de cada escenario simulado y genera el reporte PDF a partir de ellos.

    guardar_escenario(...)   se llama al terminar una simulación: deja indicadores.json en la carpeta del escenario
    generar_reporte(...)     lee esos archivos y arma el PDF (1 escenario = ficha, 2 o más = comparación),
                            sin volver a correr SUMO

indicadores.json guarda cada dato UNA sola vez:
    semilla, generado   metadatos de la corrida
    escenario           el escenario tal como se simuló (id, nombre, duración, flujos, modificaciones...)
    indicadores         KPIs, flujos y semáforos
La configuración en texto para el PDF se genera al armar el reporte, a partir de "escenario".
"""

import json
from datetime import datetime
from pathlib import Path

from reporte import generar_reporte_pdf
from utils import carpeta_escenario, carpeta_proyecto

ARCHIVO = "indicadores.json"


def describir_configuracion(escenario):

    """Líneas de texto con la configuración del escenario (para el reporte)."""


    lineas = []

    flujos = escenario.get("flujos")

    if flujos:
        for f in flujos:
            porcentaje = f.get("porcentaje_pesados", escenario.get("porcentaje_pesados", 0))
            lineas.append(f"Flujo '{f.get('id', '?')}': de {f.get('origen')} a {f.get('destino')}, "
                        f"{f.get('vehiculos_por_hora', 0):g} veh/h ({porcentaje:g} % pesados).")

    elif escenario.get("demanda_vehicular") is not None:
        lineas.append(f"Demanda aleatoria de {escenario['demanda_vehicular']} veh/h ({escenario.get('porcentaje_pesados', 0):g} % pesados).")

    if escenario.get("duracion_segundos"):
        lineas.append(f"Duración simulada: {escenario['duracion_segundos'] / 60:.0f} min.")

    for m in escenario.get("modificaciones_edges") or []:

        donde = f"tramos {', '.join(m['tramos'])}" if m.get("tramos") else f"vía {m.get('edge_id')} (todos sus tramos)"

        cambios = []

        if m.get("carriles_extra"):
            cambios.append(f"{m['carriles_extra']:+d} carril(es)")

        elif m.get("carriles") is not None:
            cambios.append(f"{m['carriles']} carriles")

        if m.get("velocidad_max") is not None:
            cambios.append(f"velocidad máxima {m['velocidad_max']:g} km/h")

        lineas.append(f"Calle: {donde}: {', '.join(cambios) or 'sin cambios'}.")


    for m in escenario.get("modificaciones_semaforos") or []:

        for fase in m.get("fases", []):

            cambio = []

            if fase.get("duracion") is not None:
                cambio.append(f"duración {fase['duracion']} s")

            if fase.get("estado") is not None:
                cambio.append(f"estado {fase['estado']}")

            lineas.append(f"Semáforo {m.get('tls_id')}: fase {fase.get('indice')}: {', '.join(cambio)}.")

    if not (escenario.get("modificaciones_edges") or escenario.get("modificaciones_semaforos")):

        lineas.append("Sin modificaciones: red base.")

    return lineas



def guardar_escenario(escenario, indicadores, semilla, carpeta):
    """Guarda escenario + indicadores en <carpeta>/indicadores.json. Regresa la ruta."""

    ruta = Path(carpeta) / ARCHIVO

    contenido = {
        "semilla": semilla,
        "generado": datetime.now().isoformat(timespec="seconds"),
        "escenario": escenario,
        "indicadores": indicadores,
    }

    ruta.write_text(json.dumps(contenido, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return ruta


def cargar_resultado(proyecto_id, escenario_id):
    ruta = Path(carpeta_escenario(proyecto_id, escenario_id)) / ARCHIVO
    if not ruta.exists():
        raise FileNotFoundError(f"El escenario {escenario_id} no tiene resultados guardados ({ruta}). Simúlalo primero.")
    return json.loads(ruta.read_text(encoding="utf-8"))


def generar_reporte(proyecto_id, ids, ruta_pdf=None, titulo=None, zona=None):
    """
    ids: lista de ids de escenario YA simulados. El primero es el base de la comparación.
    Regresa la ruta del PDF. Con un solo id genera la ficha del escenario.
    """

    if not ids:
        raise ValueError("Falta al menos un escenario para el reporte")

    guardados = [cargar_resultado(proyecto_id, i) for i in ids]

    resultados, configuraciones = {}, {}

    for g in guardados:

        esc = g["escenario"]
        nombre = esc.get("nombre") or f"Escenario {esc.get('id')}"

        if nombre in resultados:                      # los nombres son las llaves: deben ser únicos
            nombre = f"{nombre} ({esc.get('id')})"

        resultados[nombre] = g["indicadores"]
        configuraciones[nombre] = describir_configuracion(esc)

    nombres = list(resultados)

    if ruta_pdf is None:

        if len(ids) == 1:
            ruta_pdf = Path(carpeta_escenario(proyecto_id, ids[0])) / "reporte.pdf"

        else:
            carpeta = Path(carpeta_proyecto(proyecto_id)) / "reportes"
            carpeta.mkdir(parents=True, exist_ok=True)
            ruta_pdf = carpeta / f"comparacion_{'_'.join(str(i) for i in ids)}.pdf"

    semillas = {g["semilla"] for g in guardados}

    return generar_reporte_pdf(
        resultados, nombres[0], ruta_pdf, titulo=titulo, configuraciones=configuraciones, zona=zona,
        semilla=semillas.pop() if len(semillas) == 1 else None,
        duracion_s=guardados[0]["escenario"].get("duracion_segundos"))