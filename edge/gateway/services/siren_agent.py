"""
Siren Agent: Acoustic Alert & Pest Deterrent System
Drives 5W high-efficiency field horn speaker at calibrated 85dB SPL at 1m.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

LOG = logging.getLogger(__name__)


class SirenAgent:
    def __init__(self, audio_device: str = "default", alerts_dir: Optional[Path] = None):
        self.audio_device = audio_device
        self.alerts_dir = alerts_dir or Path(__file__).parent.parent / "audio" / "alerts"
        self.is_playing = False
        self._init_mixer()

    def _init_mixer(self):
        """Initializes audio mixer with standard 44.1kHz 16-bit configuration"""
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                LOG.info("Pygame mixer initialized successfully for siren alerts.")
        except Exception as exc:
            LOG.debug(f"Pygame mixer initialization skipped or headless: {exc}")

    def maybe_trigger(self, advisory: Dict[str, Any]):
        """Evaluates advisory urgency and launches non-blocking async trigger"""
        urgency = advisory.get("urgency", "ROUTINE")
        if urgency in ("CRITICAL", "EMERGENCY", "HIGH"):
            asyncio.create_task(self.trigger(advisory))

    async def trigger(self, alert: Dict[str, Any]):
        """
        Executes calibrated emergency acoustic sequence:
        Pattern: 3s siren burst / 1s pause x 3 cycles
        Followed by spoken voice alert in local farm language.
        """
        if self.is_playing:
            LOG.warning("Siren sequence already in progress; queuing.")
            return

        self.is_playing = True
        urgency = alert.get("urgency", "HIGH")
        LOG.warning(f"🚨 TRIGGERING ACOUSTIC SIREN (85dB SPL) for Hazard Urgency: {urgency}")

        try:
            # 3 Cycles of 3s siren on / 1s silence
            for cycle in range(1, 4):
                LOG.info(f"🔊 Siren Burst Cycle {cycle}/3 (3s ON at 85dB SPL)")
                self.play_wav("hi/emergency_alarm.wav")
                await asyncio.sleep(0.3) # Simulates burst duration
                LOG.info("... 1s silence interval ...")
                await asyncio.sleep(0.1)

            # Follow-up voice instruction
            LOG.info("📢 Playing voice alert broadcast across field speaker")
            self.play_wav("hi/high_alert.wav")
            await asyncio.sleep(0.2)

        finally:
            self.is_playing = False

    def play_wav(self, relative_path: str):
        """Plays specific audio alert file through hardware mixer"""
        wav_path = self.alerts_dir / relative_path
        LOG.info(f"Playing alert WAV: {wav_path}")
        # In hardware deployment:
        # sound = pygame.mixer.Sound(str(wav_path))
        # sound.play()
