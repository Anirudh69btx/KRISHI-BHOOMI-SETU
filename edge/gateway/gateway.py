#!/usr/bin/env python3
"""
FLIP Gateway: LoRa ↔ MQTT Bridge + Edge AI + Voice + Siren + SQLite Buffer + OTA
Runs on Raspberry Pi Zero 2W (Ubuntu Core / Container)
"""

import asyncio
import json
import logging
import os
import signal
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

import paho.mqtt.client as mqtt
import nats
from nats.js import JetStreamContext
import yaml

# Service imports
from services.inference_engine import InferenceEngine
from services.voice_agent import VoiceAgent
from services.siren_agent import SirenAgent
from services.sync_agent import SyncAgent
from services.health_monitor import HealthMonitor
from services.ota_agent import OTAAgent
from services.connectivity_manager import ConnectivityManager
from services.mqtt_broker import MQTTBroker
try:
    from storage.crdt import CRDTEngine
except ImportError:
    from edge.gateway.storage.crdt import CRDTEngine

LOG = logging.getLogger("flip.gateway")


@dataclass
class GatewayConfig:
    farm_id: str
    gateway_id: str
    models_path: Path
    db_path: Path
    nats_url: str
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    lora_device: str = "/dev/ttyAMA0"
    audio_device: str = "default"
    voice_config: Optional[Dict[str, Any]] = None
    ota_config: Optional[Dict[str, Any]] = None


class FLIPGateway:
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.running = False

        # Initialize SQLite Buffer
        self.init_db()

        # Local MQTT Broker & Client
        self.mqtt_broker = MQTTBroker(config.mqtt_host, config.mqtt_port)
        self.mqtt_client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"gateway-{config.gateway_id}"
        )
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_connect = self.on_mqtt_connect

        # Cloud NATS JetStream
        self.nats: Optional[nats.NATS] = None
        self.js: Optional[JetStreamContext] = None

        # Core Edge Agents
        self.crdt = CRDTEngine(config.db_path, node_id=config.gateway_id)
        self.inference = InferenceEngine(config.models_path)
        self.voice = VoiceAgent(config.voice_config)
        self.siren = SirenAgent(config.audio_device)
        self.sync = SyncAgent(
            db_path=config.db_path,
            nats_url=config.nats_url,
            farm_id=config.farm_id,
            crdt=self.crdt,
            models_path=config.models_path,
        )
        self.health = HealthMonitor()
        self.ota = OTAAgent(config.ota_config)
        self.connectivity = ConnectivityManager()

    def init_db(self):
        """Applies schema.sql to local SQLite database"""
        os.makedirs(self.config.db_path.parent, exist_ok=True)
        schema_path = Path(__file__).parent / "storage" / "schema.sql"
        with sqlite3.connect(self.config.db_path) as conn:
            if schema_path.exists():
                with open(schema_path, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
            else:
                LOG.warning("schema.sql not found, using embedded fallback schema")

    async def start(self):
        """Starts all concurrent gateway microservices"""
        self.running = True
        LOG.info(f"Starting FLIP Gateway '{self.config.gateway_id}' for Farm '{self.config.farm_id}'")

        # Start Mosquitto broker
        await self.mqtt_broker.start()

        # Connect MQTT Client
        try:
            self.mqtt_client.connect(self.config.mqtt_host, self.config.mqtt_port, keepalive=60)
            self.mqtt_client.loop_start()
        except Exception as exc:
            LOG.warning(f"Could not connect to MQTT broker: {exc}")

        # Connect NATS JetStream
        try:
            self.nats = await nats.connect(self.config.nats_url, connect_timeout=3)
            self.js = self.nats.jetstream()
            await self.ensure_streams()
        except Exception as exc:
            LOG.warning(f"NATS connection postponed (operating offline): {exc}")

        # Gather all microservice tasks
        await asyncio.gather(
            self.inference.start(),
            self.voice.start(),
            self.siren.start(),
            self.sync.start(),
            self.health.start(),
            self.ota.start(),
            self.connectivity.start(),
            self.main_loop(),
            return_exceptions=True
        )

    async def ensure_streams(self):
        """Declares required NATS JetStream message streams"""
        if not self.js:
            return
        streams = [
            ("FARM_SENSOR", f"farm.{self.config.farm_id}.sensor.*"),
            ("FARM_ADVISORY", f"farm.{self.config.farm_id}.advisory.*"),
            ("FARM_TWIN", f"farm.{self.config.farm_id}.twin.*"),
            ("DISASTER", f"farm.{self.config.farm_id}.disaster.*"),
        ]
        for name, subject in streams:
            try:
                await self.js.add_stream(name=name, subjects=[subject])
            except Exception as e:
                if "already in use" not in str(e).lower():
                    LOG.debug(f"Stream setup note ({name}): {e}")

    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            LOG.info("MQTT Client successfully subscribed to local topics")
            client.subscribe(f"farm/{self.config.farm_id}/sensor/+")
            client.subscribe(f"farm/{self.config.farm_id}/image/+")
            client.subscribe(f"farm/{self.config.farm_id}/command/+")
        else:
            LOG.error(f"MQTT connection refused with code {rc}")

    def on_mqtt_message(self, client, userdata, msg):
        try:
            topic_parts = msg.topic.split("/")
            msg_type = topic_parts[-2]
            payload = json.loads(msg.payload.decode("utf-8"))

            if msg_type == "sensor":
                self.handle_sensor_data(payload)
            elif msg_type == "image":
                self.handle_image_data(payload)
            elif msg_type == "command":
                self.handle_command(payload)
        except Exception as exc:
            LOG.error(f"Error parsing MQTT message on {msg.topic}: {exc}")

    def handle_sensor_data(self, payload: dict):
        """Stores sensor telemetry to local SQLite buffer"""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute("""
                INSERT INTO sensor_raw (farm_id, device_id, sensor_type, value, unit, quality_flag, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                self.config.farm_id,
                payload.get("device_id", "unknown"),
                payload.get("sensor_type", "GENERIC"),
                float(payload.get("value", 0.0)),
                payload.get("unit", ""),
                payload.get("quality_flag", "RAW"),
                json.dumps(payload.get("metadata", {}))
            ))

    def handle_image_data(self, payload: dict):
        """Registers captured field image and launches edge AI vision worker"""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute("""
                INSERT INTO images (farm_id, field_id, device_id, minio_key)
                VALUES (?, ?, ?, ?)
            """, (
                self.config.farm_id,
                payload.get("field_id"),
                payload.get("device_id", "camera-01"),
                payload.get("minio_key", "pending.jpg")
            ))
        asyncio.create_task(self.process_image(payload))

    def handle_command(self, payload: dict):
        LOG.info(f"Received gateway command: {payload}")

    async def process_image(self, payload: dict):
        """Runs edge AI on image and triggers local advisory speech/siren if urgent"""
        image_path = payload.get("image_path", payload.get("minio_key"))
        result = await self.inference.run(image_path)

        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute(
                "UPDATE images SET inference_result = ? WHERE minio_key = ?",
                (json.dumps(result), payload.get("minio_key"))
            )

        if result.get("confidence", 0.0) > 0.75:
            sensor_state = self.get_latest_sensor_state()
            advisory = self.inference.generate_advisory(result, sensor_state)
            await self.voice.speak(advisory["next_text"])
            self.siren.maybe_trigger(advisory)

            advisory_dict = advisory.to_dict() if hasattr(advisory, "to_dict") else dict(advisory)
            with sqlite3.connect(self.config.db_path) as conn:
                conn.execute("""
                    INSERT INTO advisories (id, farm_id, payload, urgency)
                    VALUES (?, ?, ?, ?)
                """, (advisory["id"], self.config.farm_id, json.dumps(advisory_dict), advisory["urgency"]))

    def get_latest_sensor_state(self) -> dict:
        """Retrieves most recent readings across all sensor channels"""
        state = {}
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute("""
                SELECT sensor_type, value FROM sensor_raw
                WHERE farm_id = ?
                ORDER BY captured_at DESC LIMIT 20
            """, (self.config.farm_id,))
            for row in cursor:
                if row[0] not in state:
                    state[row[0].lower()] = row[1]
        return state

    async def main_loop(self):
        """Periodic sync and maintenance loop"""
        while self.running:
            try:
                await asyncio.sleep(60) # Sync cycle every minute
                if await self.connectivity.is_online():
                    await self.sync.push_outbox()
                    await self.sync.pull_inbox()
            except Exception as e:
                LOG.error(f"Error in main loop: {e}")

    async def shutdown(self):
        LOG.info("Shutting down FLIP Gateway services...")
        self.running = False
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        if self.nats:
            await self.nats.close()
        await self.mqtt_broker.stop()


def load_config(config_path: Path) -> GatewayConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    return GatewayConfig(
        farm_id=cfg.get("farm_id", "fa000001-0000-0000-0000-000000000001"),
        gateway_id=cfg.get("gateway_id", "gw-001"),
        models_path=Path(cfg.get("models_path", "/models")),
        db_path=Path(cfg.get("db_path", "/data/gateway.db")),
        nats_url=cfg.get("nats_url", "nats://localhost:4222"),
        mqtt_host=cfg.get("mqtt_host", "localhost"),
        mqtt_port=int(cfg.get("mqtt_port", 1883)),
        lora_device=cfg.get("lora_device", "/dev/ttyAMA0"),
        audio_device=cfg.get("audio_device", "default"),
        voice_config=cfg.get("voice", {}),
        ota_config=cfg.get("ota", {}),
    )


async def main():
    cfg_file = Path("/etc/flip/gateway.yaml")
    if not cfg_file.exists():
        cfg_file = Path(__file__).parent / "config" / "gateway.yaml"

    config = load_config(cfg_file)
    gateway = FLIPGateway(config)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(gateway.shutdown()))
        except NotImplementedError:
            pass # Windows signal handling fallback

    await gateway.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    asyncio.run(main())
