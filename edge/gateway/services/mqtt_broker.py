"""
MQTT Broker Service: Manages and monitors local Mosquitto MQTT broker on Gateway
"""

import asyncio
import logging
import socket
import subprocess
from typing import Optional

LOG = logging.getLogger(__name__)


class MQTTBroker:
    def __init__(self, host: str = "localhost", port: int = 1883):
        self.host = host
        self.port = port
        self.proc: Optional[subprocess.Popen] = None
        self.running = False

    async def start(self) -> bool:
        """Verifies if Mosquitto is active or launches local instance"""
        self.running = True
        if self._is_port_open():
            LOG.info(f"Local MQTT broker already active on {self.host}:{self.port}")
            return True

        LOG.info(f"Starting embedded mosquitto on port {self.port}...")
        try:
            # Try launching mosquitto daemon
            self.proc = subprocess.Popen(
                ["mosquitto", "-p", str(self.port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Wait for socket to bind
            for _ in range(10):
                await asyncio.sleep(0.2)
                if self._is_port_open():
                    LOG.info("Embedded mosquitto broker started successfully.")
                    return True
        except FileNotFoundError:
            LOG.warning("mosquitto binary not found on host; operating in simulated/external broker mode.")

        return True

    def _is_port_open(self) -> bool:
        try:
            with socket.create_connection((self.host, self.port), timeout=1.0):
                return True
        except (OSError, ConnectionRefusedError):
            return False

    async def stop(self):
        self.running = False
        if self.proc:
            LOG.info("Stopping embedded mosquitto broker...")
            self.proc.terminate()
            self.proc.wait()
            self.proc = None
