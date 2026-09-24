import os
import json
import socketserver
from http.server import SimpleHTTPRequestHandler

from sumo_tools import cargar_herramientas_sumo
from main import importar_zona, simular_escenario

# ============================================================================
# NOTA: este servidor es un sustituto TEMPORAL del backend real de R1, solo
# para que puedas probar tu pipeline completo sin esperar a que su API esté
# lista. Guarda el estado en variables globales en memoria (no en una base
# de datos), así que se pierde cada vez que reinicias el servidor. Cuando
# R1 tenga su backend, esto se reemplaza por sus endpoints reales -- el
# contrato de datos (los mismos campos) no cambia.
# ============================================================================

PROYECTO = {
    "id": 3,
    "nombre": "Interseccion Av. Insurgentes",
    "geometria": {
        "id": "b3e33657-6c14-4c60-aeca-0fee5b22ca4a",
        "geoJson": {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-99.182682, 19.448788],
                    [-99.18045, 19.456395],
                    [-99.175816, 19.471448],
                    [-99.188347, 19.469505],
                    [-99.190407, 19.460442],
                    [-99.182682, 19.448788],
                ]]
            },
        },
    },
    "netxml_base_url": None,
    "geojson_url": None,
    "osm_file_url": None,
}

ESCENARIO = {
    "id": 12,
    "proyecto_id": PROYECTO["id"],
    "nombre": "Situacion actual",
    "modificaciones_edges": [],
    "modificaciones_semaforos": [],
    "demanda_vehicular": 100,   # TODO: pasar a "vehiculos_por_hora" explícito
    "duracion_segundos": 3600,
}

RED_BASE = None       # se llena la primera vez que se llama /simular
HERRAMIENTAS = None   # se llena al arrancar el servidor
ULTIMO_RESULTADO = None


class CORSRequestHandler(SimpleHTTPRequestHandler):

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        # El navegador manda esto antes de un PATCH real (preflight de CORS)
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path == '/red':
            self.servir_red()
        elif self.path == '/resultado':
            self.servir_ultimo_resultado()
        elif self.path == '/':
            self.path = '/index.html'
            super().do_GET()
        else:
            super().do_GET()

    def do_PATCH(self):
        if self.path.startswith('/infraestructura/'):
            self.guardar_modificacion_edge()
        elif self.path.startswith('/semaforo/'):
            self.guardar_modificacion_semaforo()
        else:
            self.responder_error(404, "Ruta no encontrada")

    def do_POST(self):
        if self.path == '/simular':
            self.disparar_simulacion()
        else:
            self.responder_error(404, "Ruta no encontrada")

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def servir_red(self):
        try:
            if PROYECTO["geojson_url"] is None:
                self.responder_error(
                    409,
                    "La zona todavía no se ha importado. Da clic en 'Simular escenario' "
                    "una primera vez para descargarla."
                )
                return

            with open(PROYECTO["geojson_url"], "r", encoding="utf-8") as f:
                red_geojson = json.load(f)

            self.responder_json(red_geojson)
            total = len(red_geojson.get("features", []))
            print(f"Respuesta /red enviada. Total de features: {total}")

        except Exception as e:
            print(f"ERROR EN /red: {e}")
            self.responder_error(500, str(e))

    def guardar_modificacion_edge(self):
        try:
            edge_id = self.path.rsplit('/', 1)[-1]
            largo = int(self.headers.get('Content-Length', 0))
            cuerpo = self.rfile.read(largo)
            datos = json.loads(cuerpo) if cuerpo else {}

            modificaciones = ESCENARIO["modificaciones_edges"]
            # Si ya existía una modificación para este edge, se reemplaza
            modificaciones[:] = [m for m in modificaciones if m["edge_id"] != edge_id]
            modificaciones.append({
                "edge_id": edge_id,
                "carriles": datos.get("carriles"),
                "velocidad_max": datos.get("velocidad_max"),
            })

            print(f"Modificación guardada -> edge {edge_id}: {datos}")
            self.responder_json({"ok": True, "edge_id": edge_id, "total_modificaciones": len(modificaciones)})

        except Exception as e:
            print(f"ERROR EN PATCH /infraestructura: {e}")
            self.responder_error(500, str(e))

    def guardar_modificacion_semaforo(self):
        """
        Body esperado, ej:
            {
                "fases": [
                    {"indice": 0, "duracion": 45},
                    {"indice": 2, "duracion": 4, "estado": "yyyGrrrryyyGrrrr"}
                ]
            }
        "estado" es opcional -- si no se manda, scenario_builder.py deja el
        state original de esa fase intacto y solo cambia la duración.
        """
        try:
            tls_id = self.path.rsplit('/', 1)[-1]
            largo = int(self.headers.get('Content-Length', 0))
            cuerpo = self.rfile.read(largo)
            datos = json.loads(cuerpo) if cuerpo else {}

            fases_entrada = datos.get("fases", [])
            fases_normalizadas = []
            for fase in fases_entrada:
                fases_normalizadas.append({
                    "indice": fase["indice"],
                    "duracion": fase.get("duracion"),
                    "estado": fase.get("estado"),
                })

            modificaciones = ESCENARIO["modificaciones_semaforos"]
            # Si ya existía una modificación para este semáforo, se reemplaza
            modificaciones[:] = [m for m in modificaciones if m["tls_id"] != tls_id]
            modificaciones.append({"tls_id": tls_id, "fases": fases_normalizadas})

            print(f"Modificación de semáforo guardada -> tls {tls_id}: {fases_normalizadas}")
            self.responder_json({"ok": True, "tls_id": tls_id, "total_modificaciones": len(modificaciones)})

        except Exception as e:
            print(f"ERROR EN PATCH /semaforo: {e}")
            self.responder_error(500, str(e))

    def disparar_simulacion(self):
        global RED_BASE, ULTIMO_RESULTADO
        try:
            if RED_BASE is None:
                print("Primera simulación de este proyecto: importando zona desde OSM...")
                RED_BASE = importar_zona(PROYECTO, HERRAMIENTAS)
                PROYECTO["netxml_base_url"] = RED_BASE["netxml_base_url"]
                PROYECTO["geojson_url"] = RED_BASE["geojson_url"]
                PROYECTO["osm_file_url"] = RED_BASE["osm_file_url"]
            else:
                print("Reutilizando la red base ya importada (no se vuelve a llamar a Overpass).")

            indicadores = simular_escenario(ESCENARIO, RED_BASE, HERRAMIENTAS)
            ULTIMO_RESULTADO = indicadores
            self.responder_json(indicadores)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.responder_error(500, f"Error al simular: {e}")

    def servir_ultimo_resultado(self):
        if ULTIMO_RESULTADO is None:
            self.responder_error(404, "Todavía no se ha corrido ninguna simulación")
        else:
            self.responder_json(ULTIMO_RESULTADO)

    # ------------------------------------------------------------------
    # Utilidades de respuesta
    # ------------------------------------------------------------------

    def responder_json(self, data, status=200):
        cuerpo = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(cuerpo)

    def responder_error(self, status, mensaje):
        self.responder_json({"error": mensaje}, status=status)


if __name__ == "__main__":
    PORT = 8000

    print("Cargando herramientas de SUMO...")
    HERRAMIENTAS = cargar_herramientas_sumo()

    print(f"Servidor iniciado en http://localhost:{PORT}")
    print("Rutas disponibles:")
    print("  GET  /                         -> index.html")
    print("  GET  /red                      -> geojson de la red del proyecto")
    print("  PATCH /infraestructura/<edge_id> -> guarda carriles/velocidad de una calle")
    print("  PATCH /semaforo/<tls_id>       -> guarda fases modificadas de un semáforo")
    print("  POST /simular                  -> corre el pipeline completo y regresa indicadores")
    print("  GET  /resultado                -> último resultado calculado")
    print("Presiona Ctrl+C para detener")

    with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido")