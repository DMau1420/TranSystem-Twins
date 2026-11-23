"""
scenario_builder.py: construye la red de SUMO de un escenario a partir de la red base.

    FLUJO
    1. Exportar la red base a archivos de texto planos      -> este archivo
    2. Cambiar carriles y velocidad de los tramos           -> escenario_calles.py
    3. Reconectar carriles (copiar o redirigir conexiones)  -> escenario_conexiones.py
    4. Ajustar semáforos: extender (agregar) o reinterpretar (quitar) -> escenario_conexiones.py
    5. Cambiar la duración de fases de un semáforo          -> escenario_semaforos.py
    6. Guardar y mostrar el reporte (aplicado / rechazado)  -> este archivo
    7. Reconstruir la red con netconvert                    -> este archivo

    Guía para la construccion de escenarios: GUIA_SCENARIO_BUILDER.md
"""
import json
import subprocess
from pathlib import Path

import escenario_calles as calles
import escenario_conexiones as conexiones
import escenario_semaforos as semaforos

# Los scripts de prueba (probar_conexiones.py, etc.) importan este nombre desde aquí
_pertenece_a_via = calles.pertenece_a_via


# =====================================================================
# PUNTO DE ENTRADA
# =====================================================================
def construir_red_escenario(netconvertBinary, ruta_net_base_proyecto, carpeta_escenario,
                            modificaciones_edges=None, modificaciones_semaforos=None,
                            nombre_salida="red_escenario.net.xml"):
    """
    Misma firma y mismo valor de retorno de siempre (la ruta de la red), para no romper main.py.
    El reporte queda en <carpeta_escenario>/reporte_cambios.json.
    """
    ruta, _ = construir_red_escenario_con_reporte(
        netconvertBinary, ruta_net_base_proyecto, carpeta_escenario,
        modificaciones_edges, modificaciones_semaforos, nombre_salida)
    return ruta


def construir_red_escenario_con_reporte(netconvertBinary, ruta_net_base_proyecto, carpeta_escenario,
                                        modificaciones_edges=None, modificaciones_semaforos=None,
                                        nombre_salida="red_escenario.net.xml"):
    """
    Regresa (ruta_de_la_red, reporte). Si nada se pudo aplicar, la ruta es la de la red base.

    modificaciones_edges:      [{"edge_id": "128255275", "carriles_extra": 1, "velocidad_max": 60}]
                                carriles_extra: +N agrega, -N quita (por tramo). "carriles" (absoluto) sigue aceptado.
    modificaciones_semaforos:  [{"tls_id": "...", "fases": [{"indice": 0, "duracion": 45}]}]
    semaforos_fijos:           True pasa TODOS los semáforos a tiempo fijo (sirve para una base comparable)
    reporte:                   {"aplicados": [...], "rechazados": [{"tipo","id","motivo"}], "resumen": {...}}
    """
    modificaciones_edges = modificaciones_edges or []
    modificaciones_semaforos = modificaciones_semaforos or []
    reporte = {"aplicados": [], "rechazados": [], "resumen": {}}

    if not modificaciones_edges and not modificaciones_semaforos:
        print("Escenario sin modificaciones: se usa directamente la red base del proyecto.")
        return ruta_net_base_proyecto, reporte

    # Ruta absoluta: SUMO resuelve las rutas relativas del .sumocfg contra la carpeta del .sumocfg
    carpeta = Path(carpeta_escenario).resolve()
    carpeta.mkdir(parents=True, exist_ok=True)

    # 1) Exportar
    archivos = _exportar_red_base(netconvertBinary, ruta_net_base_proyecto, carpeta)
    archivo_tll = archivos["tll"] if Path(archivos["tll"]).exists() else None

    # 2-4) Calles, conexiones y enlaces de semáforo
    if modificaciones_edges:
        nuevos = calles.aplicar_cambios_en_calles(archivos["edg"], archivo_tll, modificaciones_edges, reporte)
        conexiones.reconectar(archivos["con"], nuevos, reporte)
        conexiones.extender_semaforos(archivo_tll, nuevos, reporte)
        conexiones.reducir_semaforos(archivo_tll, nuevos, reporte)

    # 5) Duración de fases
    if modificaciones_semaforos:
        semaforos.aplicar_modificaciones(archivo_tll, modificaciones_semaforos, reporte)

    # 6) Reporte
    _guardar_reporte(carpeta, reporte)
    _imprimir_reporte(reporte)
    if not reporte["aplicados"]:
        print("Ningún cambio se pudo aplicar: se usa la red base.")
        return ruta_net_base_proyecto, reporte

    # 7) Reconstruir
    ruta_red = carpeta / nombre_salida
    _reconstruir_red(netconvertBinary, archivos, archivo_tll, ruta_red)
    return ruta_red, reporte


# =====================================================================
# netconvert y reporte
# =====================================================================
def _exportar_red_base(netconvert, ruta_net_base, carpeta):
    """Exporta la red base a archivos planos. Regresa {"edg","nod","con","tll"} con sus rutas."""
    prefijo = carpeta / "plano"
    print(f"Exportando red base ({ruta_net_base}) a formato plano...")
    _correr_netconvert([netconvert, "--sumo-net-file", str(ruta_net_base),
                        "--plain-output-prefix", str(prefijo)], "exportar la red base a formato plano")
    return {ext: f"{prefijo}.{ext}.xml" for ext in ("edg", "nod", "con", "tll")}


def _reconstruir_red(netconvert, archivos, archivo_tll, ruta_red):
    """Arma el .net.xml del escenario a partir de los archivos planos ya modificados."""

    comando = [netconvert, 
            "--node-files", archivos["nod"], 
            "--edge-files", archivos["edg"],
            "--connection-files", archivos["con"], 
            "--output-file", str(ruta_red), 
            "--output.street-names", "true" ]
    
    
    if archivo_tll:
        comando += ["--tllogic-files", archivo_tll]
    print("Reconstruyendo la red del escenario...")
    _correr_netconvert(comando, "reconstruir el .net.xml del escenario")
    print(f" Red del escenario generada en: {ruta_red}")


def _correr_netconvert(comando, que):
    try:
        return subprocess.run(comando, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"STDERR de netconvert ({que}):\n", e.stderr)
        raise RuntimeError(f"netconvert falló al {que} (exit code {e.returncode}). "
                        f"Detalle:\n{e.stderr or e.stdout}") from e


def _guardar_reporte(carpeta, reporte):
    with open(Path(carpeta) / "reporte_cambios.json", "w", encoding="utf-8") as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)


def _imprimir_reporte(reporte):
    print("--- Reporte de cambios del escenario ---")
    for a in reporte["aplicados"]:
        print(f"  APLICADO   {a['tipo']} {a['id']}: { {k: v for k, v in a.items() if k not in ('tipo', 'id')} }")
    for r in reporte["rechazados"]:
        print(f"  RECHAZADO  {r['tipo']} {r['id']}: {r['motivo']}")
    if reporte["resumen"]:
        print(f"  Resumen: {reporte['resumen']}")