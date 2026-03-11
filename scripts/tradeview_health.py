"""
TradeView MQTT Health Publisher
Publishes service health to tradeview/health/{node}/{service} every 60s.
Deploy as systemd service on each TradeView node.
"""

import json
import os
import socket
import time
import subprocess
import logging

import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MQTT_HOST = os.environ.get("MQTT_HOST", "otto.local")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
PUBLISH_INTERVAL = int(os.environ.get("PUBLISH_INTERVAL", 60))
HOSTNAME = socket.gethostname().replace(".local", "")

SERVICES = {
    "milo": ["tradeview-api", "tradeview-valkey"],
    "otto": ["tradeview-timescaledb", "tradeview-fetcher"],
    "pete": ["tradeview-ml"],
}


def get_container_status(name: str) -> str:
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", name],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() or "not_found"
    except Exception:
        try:
            result = subprocess.run(
                ["podman", "inspect", "--format", "{{.State.Status}}", name],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() or "not_found"
        except Exception:
            return "unknown"


def build_payload() -> dict:
    services = SERVICES.get(HOSTNAME, [])
    statuses = {svc: get_container_status(svc) for svc in services}
    all_ok = all(s == "running" for s in statuses.values())
    return {
        "hostname": HOSTNAME,
        "status": "ok" if all_ok else "degraded",
        "services": statuses,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def run():
    client = mqtt.Client(client_id=f"tradeview-health-{HOSTNAME}")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    while True:
        payload = build_payload()
        topic = f"tradeview/health/{HOSTNAME}/services"
        client.publish(topic, json.dumps(payload), retain=True)
        logger.info(f"Published to {topic}: {payload['status']}")
        time.sleep(PUBLISH_INTERVAL)


if __name__ == "__main__":
    run()
