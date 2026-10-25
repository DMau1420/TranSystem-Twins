"""
simulador_vehiculos.py
-----------------------
Simulador de flujo vehicular por minuto.

Genera un número aleatorio de vehículos (0–12) cada intervalo aleatorio
de 0 a 60 segundos y lo publica vía MQTT al tópico
'transystem/vehiculos_por_minuto'.

Puede ejecutarse de forma standalone o importarse como módulo.

Uso standalone:
    python simulador_vehiculos.py
"""

import asyncio
import json
import logging
import random
from datetime import datetime

import paho.mqtt.client as mqtt

# ── Configuración ──────────────────────────────────────────────────────────────
BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC = "transystem/vehiculos_por_minuto"
CLIENT_ID = "simulador_vehiculos_publisher"

MIN_VEHICULOS = 0
MAX_VEHICULOS = 12
MIN_INTERVALO = 0    # segundos
MAX_INTERVALO = 60   # segundos (1 minuto)

# Silencia paho-mqtt
logging.getLogger("paho").setLevel(logging.CRITICAL)


# ── Cliente MQTT ───────────────────────────────────────────────────────────────

def crear_cliente_mqtt() -> mqtt.Client:
    """Crea y configura el cliente MQTT publicador (sin callbacks verbosos)."""
    client = mqtt.Client(
        client_id=CLIENT_ID,
        protocol=mqtt.MQTTv5,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    return client


# ── Bucle de simulación ────────────────────────────────────────────────────────

async def bucle_simulacion(client: mqtt.Client) -> None:
    """Genera y publica datos de vehículos en intervalos aleatorios."""
    while True:
        vehiculos = random.randint(MIN_VEHICULOS, MAX_VEHICULOS)
        intervalo = random.uniform(MIN_INTERVALO, MAX_INTERVALO)

        payload = json.dumps({
            "vehiculos_por_minuto": vehiculos,
            "timestamp": datetime.now().isoformat(),
        })

        client.publish(TOPIC, payload, qos=1)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚗 {vehiculos} vehículo(s) — esperando {intervalo:.1f}s")

        await asyncio.sleep(intervalo)


# ── Función principal ──────────────────────────────────────────────────────────

async def iniciar_simulador() -> None:
    """Conecta al broker con reintentos y lanza el bucle de simulación."""
    client = crear_cliente_mqtt()

    # Reintentos con backoff exponencial hasta 30s
    reintento = 0
    while True:
        try:
            client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            break
        except (ConnectionRefusedError, OSError):
            espera = min(2 ** reintento, 30)
            print(f"Broker no disponible. Reintentando en {espera}s...")
            reintento += 1
            await asyncio.sleep(espera)

    client.loop_start()

    try:
        await bucle_simulacion(client)
    except asyncio.CancelledError:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(iniciar_simulador())
    except KeyboardInterrupt:
        print("\nSimulador detenido.")
