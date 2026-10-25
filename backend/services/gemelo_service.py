"""
gemelo_service.py
-----------------
Servicio de gemelo digital (Digital Twin) que actúa como suscriptor MQTT.
Recibe el número de vehículos por minuto publicado por el simulador
en el tópico 'transystem/vehiculos_por_minuto'.

Uso:
    python services/gemelo_service.py
"""

import json
import logging
from datetime import datetime

import paho.mqtt.client as mqtt

# ── Configuración ──────────────────────────────────────────────────────────────
BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC = "transystem/vehiculos_por_minuto"
CLIENT_ID = "gemelo_digital_subscriber"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [GEMELO] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Historial en memoria (podría conectarse a BD en el futuro) ─────────────────
historial_vehiculos: list[dict] = []


# ── Callbacks MQTT ─────────────────────────────────────────────────────────────

def on_connect(client: mqtt.Client, userdata, flags, reason_code, properties=None):
    """Callback al establecer conexión con el broker."""
    if reason_code == 0:
        logger.info("✅ Conectado al broker MQTT en %s:%d", BROKER_HOST, BROKER_PORT)
        client.subscribe(TOPIC)
        logger.info("📡 Suscrito al tópico: %s", TOPIC)
    else:
        logger.error("❌ Falló la conexión. Código de razón: %s", reason_code)


def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    """Callback al recibir un mensaje en el tópico suscrito."""
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        vehiculos = payload.get("vehiculos_por_minuto")
        timestamp = payload.get("timestamp", datetime.now().isoformat())

        registro = {
            "timestamp": timestamp,
            "vehiculos_por_minuto": vehiculos,
        }
        historial_vehiculos.append(registro)

        logger.info(
            "🚗 Vehículos recibidos: %d  |  Timestamp: %s  |  Tópico: %s",
            vehiculos,
            timestamp,
            msg.topic,
        )

    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("⚠️  Mensaje inválido recibido: %s — Error: %s", msg.payload, exc)


def on_disconnect(client: mqtt.Client, userdata, flags, reason_code, properties=None):
    """Callback al desconectarse del broker."""
    logger.warning("🔌 Desconectado del broker. Código: %s", reason_code)


# ── Función principal ──────────────────────────────────────────────────────────

def iniciar_gemelo():
    """Inicializa y ejecuta el cliente MQTT suscriptor del gemelo digital."""
    client = mqtt.Client(
        client_id=CLIENT_ID,
        protocol=mqtt.MQTTv5,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    logger.info("🔄 Conectando al broker MQTT en %s:%d ...", BROKER_HOST, BROKER_PORT)
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("🛑 Gemelo detenido manualmente.")
    finally:
        client.disconnect()
        logger.info("📊 Total de registros almacenados: %d", len(historial_vehiculos))


if __name__ == "__main__":
    iniciar_gemelo()
