"""
API interna de SUMO. Solo la consume el backend (este servicio no publica puertos).

Sin estado global de negocio: todo lo importante vive en disco, bajo data/
(que en docker-compose es un volumen), organizado por utils.carpeta_proyecto
y utils.carpeta_escenario.

Contrato:
    GET  /                          -> {"status": "ok"}
    POST /importar                  -> {osm_file_url, netxml_base_url, geojson_url}
    GET  /proyectos/{id}/red        -> GeoJSON de la red base (409 si no se ha importado)
    POST /simular                   -> {vehiculos_atendidos, tiempo_promedio_espera,
                                        velocidad_promedio, longitud_max_fila}

Los errores siempre regresan {"error": "..."} con su status HTTP; el backend
(services/sumo_client.py) lee esa llave.
"""
import json
import os
import re
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import traci

from main import importar_zona, simular_escenario
from sumo_tools import cargar_herramientas_sumo
from utils import carpeta_proyecto

PORT = int(os.environ.get("PORT", "8000"))

# netconvert y TraCI trabajan con procesos/conexiones globales: solo una tarea
# pesada a la vez. Las demás peticiones esperan su turno.
CANDADO = threading.Lock()

_herramientas = None


def herramientas():
    global _herramientas
    if _herramientas is None:
        _herramientas = cargar_herramientas_sumo()
    return _herramientas


def _serializar(o):
    # numpy (int64, float32...) no es serializable por json; .item() lo vuelve nativo
    if hasattr(o, "item"):
        return o.item()
    return str(o)  # Path y demás


def _cerrar_traci():
    try:
        traci.close()
    except Exception:
        pass


class ErrorHTTP(Exception):
    def __init__(self, status, mensaje):
        super().__init__(mensaje)
        self.status = status
        self.mensaje = mensaje


class Handler(BaseHTTPRequestHandler):
    # ---------- utilidades de respuesta ----------
    def _enviar(self, status, cuerpo: bytes):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, status, data):
        self._enviar(status, json.dumps(data, default=_serializar).encode())

    def _leer_body(self):
        largo = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(largo) or b"{}")
        except json.JSONDecodeError:
            raise ErrorHTTP(400, "El cuerpo no es JSON válido")

    def _ruta(self):
        return self.path.split("?")[0].rstrip("/") or "/"

    def _manejar_error(self, e):
        if isinstance(e, ErrorHTTP):
            self._json(e.status, {"error": e.mensaje})
        else:
            traceback.print_exc()
            self._json(500, {"error": str(e)})

    # ---------- rutas ----------
    def do_GET(self):
        ruta = self._ruta()
        try:
            if ruta == "/":
                return self._json(200, {"status": "ok", "servicio": "sumo"})
            m = re.fullmatch(r"/proyectos/(\d+)/red", ruta)
            if m:
                return self._red(int(m.group(1)))
            raise ErrorHTTP(404, f"Ruta no encontrada: {ruta}")
        except Exception as e:
            self._manejar_error(e)

    def do_POST(self):
        ruta = self._ruta()
        try:
            body = self._leer_body()
            if ruta == "/importar":
                return self._json(200, self._importar(body))
            if ruta == "/simular":
                return self._json(200, self._simular(body))
            raise ErrorHTTP(404, f"Ruta no encontrada: {ruta}")
        except Exception as e:
            self._manejar_error(e)

    # ---------- lógica ----------
    def _red(self, proyecto_id):
        archivo = next(carpeta_proyecto(proyecto_id).glob("*.geojson"), None)
        if archivo is None:
            raise ErrorHTTP(409, "La red de este proyecto todavía no se ha importado")
        self._enviar(200, archivo.read_bytes())

    def _importar(self, body):
        proyecto_id = body.get("proyecto_id")
        geometria = body.get("geometria")
        if proyecto_id is None or not geometria:
            raise ErrorHTTP(400, "Faltan proyecto_id o geometria")
        try:
            geometria["geoJson"]["geometry"]["coordinates"]
        except (KeyError, TypeError):
            raise ErrorHTTP(400, "La geometria debe traer geoJson.geometry.coordinates")

        # importar_zona (main.py) espera este dict; el backend solo manda id + geometria
        proyecto = {"id": proyecto_id, "nombre": f"Proyecto {proyecto_id}", "geometria": geometria}

        with CANDADO:
            try:
                urls = importar_zona(proyecto, herramientas())
            except Exception:
                _cerrar_traci()
                raise
        return {k: str(v) for k, v in urls.items()}

    def _simular(self, body):
        proyecto_id = body.get("proyecto_id")
        red_base = body.get("red_base")
        escenario = body.get("escenario")
        if proyecto_id is None or not red_base or not escenario:
            raise ErrorHTTP(400, "Faltan proyecto_id, red_base o escenario")
        if not red_base.get("netxml_base_url"):
            raise ErrorHTTP(409, "El proyecto no tiene red base importada")

        # simular_escenario (main.py) usa escenario["proyecto_id"]; el backend no lo manda dentro
        escenario = {**escenario, "proyecto_id": proyecto_id}

        with CANDADO:
            try:
                return simular_escenario(escenario, red_base, herramientas())
            except Exception:
                _cerrar_traci()
                raise


if __name__ == "__main__":
    print(f"Sumo escuchando en 0.0.0.0:{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()