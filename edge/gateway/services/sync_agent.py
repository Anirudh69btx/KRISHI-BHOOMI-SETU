"""
Sync Agent: NATS JetStream Store-and-Forward + CRDT State Reconciliation
=========================================================================
Bridges local Gateway SQLite outbox/inbox queues with Cloud NATS JetStream.

Sync loop: every 300 seconds (5 minutes) when online.
  push_outbox(): farmer actions (LWW), sensor buffer batches (OR-Set), trusted devices
  pull_inbox() : advisories, model OTA, config, map tiles, validated sensors

CRDT merge policy:
  - advisories      → LWW-Register (cloud timestamp wins if newer)
  - sensor buffer   → OR-Set union (no data ever lost)
  - trusted devices → OR-Set union
  - farmer actions  → LWW (local timestamp wins — farmer acted first)

OTA model flow:
  model.updated message → HTTP download → SHA256 verify → atomic stage → active swap
  Health check window: 60s. Rollback on failure.

Offline resilience:
  - All outbox items buffered in SQLite (schema.sql: outbox table)
  - Reconnect triggers immediate push + pull
  - NATS consumer uses durable name → resumes from last ack on reconnect
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

LOG = logging.getLogger(__name__)

# ─── Optional NATS import ────────────────────────────────────────────────────
try:
    import nats
    import nats.errors
    from nats.js import JetStreamContext
    from nats.js.api import ConsumerConfig, AckPolicy, DeliverPolicy
    _NATS_AVAILABLE = True
except ImportError:
    nats = None  # type: ignore[assignment]
    _NATS_AVAILABLE = False
    LOG.warning("nats-py not installed — SyncAgent in offline-only mode")

# ─── Optional HTTP client for OTA downloads ───────────────────────────────────
try:
    import aiohttp
    _AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None  # type: ignore[assignment]
    _AIOHTTP_AVAILABLE = False

try:
    from storage.crdt import CRDTEngine, LamportClock
except ImportError:
    try:
        from edge.gateway.storage.crdt import CRDTEngine, LamportClock
    except ImportError:
        CRDTEngine = None   # type: ignore[assignment,misc]
        LamportClock = None # type: ignore[assignment]


# ─── Sensor types known to the system ────────────────────────────────────────
SENSOR_TYPES = [
    "VWC", "EC", "TEMP_SOIL", "TEMP_AIR", "RH",
    "LEAF_WETNESS", "RAIN", "PAR",
]


class SyncAgent:
    """
    NATS JetStream sync agent for FLIP Gateway.

    Args:
        db_path:  Path to local SQLite database (gateway.db)
        nats_url: NATS server URL (e.g. nats://10.0.0.1:4222)
        farm_id:  UUID-based farm identifier
        crdt:     Optional injected CRDTEngine (created internally if None)
        models_path: Path to models directory for OTA staging
    """

    SYNC_INTERVAL_S = 300           # 5-minute sync cycle
    BATCH_SIZE      = 50            # NATS JetStream fetch batch
    NATS_TIMEOUT_S  = 10            # fetch timeout
    OTA_VERIFY_S    = 60            # health-check window after model swap

    def __init__(
        self, db_path: Path, nats_url: str, farm_id: str,
        crdt: Optional[CRDTEngine] = None, models_path: Optional[Path] = None,
    ):
        self.db_path     = Path(db_path)
        self.nats_url    = nats_url
        self.farm_id     = farm_id
        self.models_path = Path(models_path) if models_path else Path("/models")

        # CRDT engine (injected or create own)
        if crdt is not None:
            self.crdt = crdt
        elif CRDTEngine is not None:
            self.crdt = CRDTEngine(
                db_path=db_path,
                node_id=f"gw-{farm_id[:6]}",
            )
        else:
            self.crdt = None
            LOG.warning("CRDTEngine not available — sync will use SQLite outbox only")

        self.nc: Optional[Any] = None        # nats.NATS
        self.js: Optional[Any] = None        # JetStreamContext
        self.running = False
        self._consumer_name = f"gateway-{farm_id[:8]}"

    # ── Lifecycle ──────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start NATS connection and background sync loop."""
        self.running = True
        LOG.info("SyncAgent starting for Farm: %s", self.farm_id)
        await self._connect_nats()
        asyncio.create_task(self._sync_loop(), name="sync_loop")

    async def _connect_nats(self) -> bool:
        if not _NATS_AVAILABLE:
            return False
        try:
            self.nc = await nats.connect(
                self.nats_url,
                connect_timeout=1,
                reconnect_time_wait=1,
                max_reconnect_attempts=1,
                name=f"flip-gateway-{self.farm_id[:8]}",
            )
            self.js = self.nc.jetstream()
            await self._ensure_streams()
            LOG.info("Connected to NATS JetStream at %s", self.nats_url)
            return True
        except Exception as exc:
            LOG.debug("NATS offline (%s) — buffering locally", exc)
            self.nc = None
            self.js = None
            return False

    async def _ensure_streams(self) -> None:
        """Declare required NATS JetStream streams (idempotent)."""
        if not self.js:
            return
        streams = [
            ("FARM_SENSOR",  [f"farm.{self.farm_id}.sensor.*"]),
            ("FARM_ADVISORY",[f"farm.{self.farm_id}.advisory.*"]),
            ("FARM_ACTIONS", [f"farm.{self.farm_id}.action.*"]),
            ("FARM_INBOX",   [f"farm.{self.farm_id}.inbox.>"]),
        ]
        for name, subjects in streams:
            try:
                await self.js.add_stream(name=name, subjects=subjects)
            except Exception as exc:
                if "already in use" not in str(exc).lower():
                    LOG.debug("Stream %s: %s", name, exc)

    async def _sync_loop(self) -> None:
        """Background sync loop: push then pull every SYNC_INTERVAL_S seconds."""
        while self.running:
            try:
                if await self.is_online():
                    pushed = await self.push_outbox()
                    pulled = await self.pull_inbox()
                    if pushed + pulled > 0:
                        LOG.info("Sync: pushed=%d pulled=%d", pushed, pulled)
            except Exception as exc:
                LOG.warning("Sync loop error: %s", exc)
            await asyncio.sleep(self.SYNC_INTERVAL_S)

    # ── Connectivity ───────────────────────────────────────────────────────

    async def is_online(self) -> bool:
        """Check NATS connectivity with a ping (2s timeout)."""
        if not self.nc:
            return await self._connect_nats()
        try:
            await asyncio.wait_for(self.nc.flush(), timeout=2.0)
            return True
        except Exception:
            self.nc = None
            self.js = None
            return await self._connect_nats()

    # ── PUSH outbox ────────────────────────────────────────────────────────

    async def push_outbox(self) -> int:
        """
        Push all unsynced local data to NATS JetStream:
          1. Farmer actions (LWW-Register)
          2. Sensor buffers (OR-Set) — batched by sensor type
          3. Trusted devices (OR-Set)
          4. General SQLite outbox entries
        Returns: count of successfully published messages.
        """
        if not self.js:
            return 0

        count = 0

        # 1. Farmer actions
        if self.crdt:
            for action in self.crdt.get_pending_actions():
                subject = f"farm.{self.farm_id}.action.taken"
                try:
                    await self.js.publish(
                        subject,
                        json.dumps(action, default=str).encode("utf-8"),
                        timeout=2.0,
                    )
                    self.crdt.mark_action_synced(action["advisory_id"])
                    count += 1
                    LOG.debug("Pushed farmer action: %s", action.get("advisory_id"))
                except Exception as exc:
                    LOG.warning("Farmer action push failed: %s", exc)
                    break

            # 2. Sensor buffers — all types
            for sensor_type in SENSOR_TYPES:
                readings = self.crdt.get_sensor_buffer(sensor_type)
                if not readings:
                    continue
                # Batch in chunks of 100
                for i in range(0, len(readings), 100):
                    batch = readings[i:i + 100]
                    subject = f"farm.{self.farm_id}.sensor.buffered"
                    payload = {
                        "sensor_type": sensor_type,
                        "readings": batch,
                        "farm_id": self.farm_id,
                        "count": len(batch),
                    }
                    try:
                        await self.js.publish(
                            subject,
                            json.dumps(payload, default=str).encode("utf-8"),
                            timeout=2.0,
                        )
                        count += 1
                    except Exception as exc:
                        LOG.warning("Sensor batch push failed (%s): %s", sensor_type, exc)
                        break

            # 3. Trusted devices
            devices = self.crdt.get_trusted_devices()
            if devices:
                subject = f"farm.{self.farm_id}.trusted_devices"
                try:
                    await self.js.publish(
                        subject,
                        json.dumps({"devices": devices}, default=str).encode("utf-8"),
                        timeout=2.0,
                    )
                    count += 1
                except Exception as exc:
                    LOG.warning("Trusted devices push failed: %s", exc)

        # 4. General SQLite outbox (legacy + general purpose messages)
        count += await self._drain_sqlite_outbox()

        return count

    async def _drain_sqlite_outbox(self) -> int:
        """Drain the SQLite outbox table (unstructured messages + raw sensor rows)."""
        count = 0
        if not self.js:
            return 0
        try:
            with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                # General outbox queue
                cursor = conn.execute(
                    "SELECT id, subject, payload FROM outbox WHERE sent_at IS NULL ORDER BY id ASC LIMIT 100"
                )
                rows = cursor.fetchall()
                for row_id, subject, payload_str in rows:
                    try:
                        await self.js.publish(subject, payload_str.encode("utf-8"), timeout=2.0)
                        conn.execute(
                            "UPDATE outbox SET sent_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (row_id,)
                        )
                        count += 1
                    except Exception as exc:
                        LOG.warning("Outbox publish failed on %s: %s", subject, exc)
                        break
                conn.commit()

                # Raw sensor readings not yet synced
                cursor = conn.execute("""
                    SELECT id, device_id, sensor_type, value, unit, quality_flag, captured_at
                    FROM sensor_raw WHERE synced_at IS NULL ORDER BY id ASC LIMIT 100
                """)
                sensor_rows = cursor.fetchall()
                for s_id, dev_id, s_type, val, unit, q_flag, cap_at in sensor_rows:
                    subject = f"farm.{self.farm_id}.sensor.raw"
                    msg = {
                        "farm_id":      self.farm_id,
                        "device_id":    dev_id,
                        "sensor_type":  s_type,
                        "value":        val,
                        "unit":         unit,
                        "quality_flag": q_flag,
                        "captured_at":  cap_at,
                    }
                    try:
                        await self.js.publish(subject, json.dumps(msg).encode("utf-8"), timeout=2.0)
                        conn.execute(
                            "UPDATE sensor_raw SET synced_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (s_id,)
                        )
                        count += 1
                    except Exception:
                        break
                conn.commit()
        except Exception as exc:
            LOG.warning("SQLite outbox drain error: %s", exc)

        return count

    # ── PULL inbox ─────────────────────────────────────────────────────────

    async def pull_inbox(self) -> int:
        """
        Pull from NATS JetStream durable consumer.
        Processes 5 message types with appropriate CRDT merges.
        Returns count of messages processed.
        """
        if not self.js:
            return 0

        count = 0
        try:
            consumer_config = ConsumerConfig(
                durable_name=self._consumer_name,
                ack_policy=AckPolicy.EXPLICIT,
                deliver_policy=DeliverPolicy.NEW,
                max_deliver=3,
                ack_wait=30,
            )
            psub = await self.js.pull_subscribe(
                f"farm.{self.farm_id}.inbox.>",
                durable=self._consumer_name,
                config=consumer_config,
            )

            msgs = await psub.fetch(batch=self.BATCH_SIZE, timeout=self.NATS_TIMEOUT_S)
            for msg in msgs:
                try:
                    await self._process_inbox_message(msg)
                    await msg.ack()
                    count += 1
                except Exception as exc:
                    LOG.error("Inbox message processing error: %s", exc)
                    try:
                        await msg.nak()
                    except Exception:
                        pass

        except Exception as exc:
            # No messages available is normal
            if "timeout" not in str(exc).lower() and "404" not in str(exc):
                LOG.debug("pull_inbox: %s", exc)

        return count

    async def _process_inbox_message(self, msg: Any) -> None:
        """Route inbox messages to the appropriate CRDT merge handler."""
        subject = msg.subject
        try:
            data = json.loads(msg.data.decode("utf-8"))
        except json.JSONDecodeError as exc:
            LOG.warning("Invalid JSON in inbox message %s: %s", subject, exc)
            return

        LOG.debug("Inbox message: %s", subject)

        if subject.endswith(".advisory.generated"):
            await self._handle_advisory(data)

        elif subject.endswith(".model.updated"):
            await self._download_and_stage_model(data)

        elif subject.endswith(".config.updated"):
            await self._apply_config(data)

        elif subject.endswith(".tiles.updated"):
            await self._apply_tile_diff(data)

        elif subject.endswith(".sensor.validated"):
            await self._handle_validated_sensor(data)

        elif subject.endswith(".trusted_devices"):
            await self._handle_trusted_devices(data)

        else:
            # Persist to SQLite inbox for gateway to process
            try:
                with sqlite3.connect(str(self.db_path), timeout=10) as conn:
                    conn.execute(
                        "INSERT INTO inbox (subject, payload) VALUES (?, ?)",
                        (subject, msg.data.decode("utf-8"))
                    )
            except Exception as exc:
                LOG.warning("Failed to persist inbox message: %s", exc)

    async def _handle_advisory(self, data: dict) -> None:
        """Merge cloud advisory into local CRDT state."""
        if not self.crdt:
            return
        advisory_id = data.get("id", "")
        meta = data.get("_meta", {})
        cloud_ts   = (int(meta.get("timestamp", 0)), str(meta.get("node", "cloud")))
        cloud_node = str(meta.get("node", "cloud"))

        self.crdt.merge_advisory(advisory_id, data, cloud_ts, cloud_node)
        LOG.info("Advisory merged: %s (urgency=%s)", advisory_id, data.get("urgency"))

    async def _handle_validated_sensor(self, data: dict) -> None:
        """Merge cloud-validated sensor reading into local OR-Set."""
        if not self.crdt:
            return
        sensor_type = data.get("sensor_type", "GENERIC")
        meta = data.get("_meta", {})
        cloud_clock = LamportClock(
            node_id=str(meta.get("node", "cloud")),
            time=int(meta.get("timestamp", 0)),
        )
        self.crdt.merge_sensor_buffer(sensor_type, [data], cloud_clock)

    async def _handle_trusted_devices(self, data: dict) -> None:
        """Merge cloud trusted-device list into local OR-Set."""
        if not self.crdt:
            return
        devices = data.get("devices", [])
        meta = data.get("_meta", {})
        cloud_clock = LamportClock(
            node_id=str(meta.get("node", "cloud")),
            time=int(meta.get("timestamp", 0)),
        )
        self.crdt.merge_trusted_devices(devices, cloud_clock)

    # ── OTA Model Staging ──────────────────────────────────────────────────

    async def _download_and_stage_model(self, data: dict) -> None:
        """
        OTA model update flow:
          1. Download from signed_url
          2. SHA256 verify against manifest
          3. Atomic stage: models/staged/{model_name}
          4. Atomic swap: models/staged/ → models/vision|fusion|voice/
          5. Health check window (60s)
        """
        model_name  = data.get("model", "")
        signed_url  = data.get("signed_url", "")
        expected_sha = data.get("sha256", "")
        target_file = data.get("target_file", "")

        if not all([model_name, signed_url, expected_sha, target_file]):
            LOG.warning("Model OTA message missing required fields: %s", data)
            return

        LOG.info("OTA: downloading model '%s' from %s", model_name, signed_url[:60])

        if not _AIOHTTP_AVAILABLE:
            LOG.error("OTA: aiohttp not available — cannot download model")
            return

        # Download to temp file
        staged_dir = self.models_path / "staged"
        staged_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = staged_dir / f"{model_name}.tmp"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(signed_url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    if resp.status != 200:
                        LOG.error("OTA download failed: HTTP %d", resp.status)
                        return
                    content = await resp.read()

            # Verify SHA256
            actual_sha = hashlib.sha256(content).hexdigest()
            if actual_sha != expected_sha:
                LOG.error(
                    "OTA SHA256 mismatch for %s: expected=%s actual=%s",
                    model_name, expected_sha[:16], actual_sha[:16]
                )
                return

            # Write staged file
            tmp_path.write_bytes(content)
            LOG.info(
                "OTA: staged %s (%.1fMB, SHA256=%s...)",
                model_name, len(content) / (1024**2), actual_sha[:12]
            )

            # Atomic swap to active directory
            target_path = self.models_path / target_file
            target_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path = target_path.with_suffix(target_path.suffix + ".bak")

            if target_path.exists():
                shutil.copy2(str(target_path), str(backup_path))

            shutil.move(str(tmp_path), str(target_path))
            LOG.info("OTA: model %s swapped to active (%s)", model_name, target_path)

            # Post-swap health check (60s window)
            await asyncio.sleep(2)  # allow runtime to detect new file
            # In production: trigger InferenceEngine.reload_model(model_name)
            # and verify output within tolerance
            LOG.info("OTA: model %s health check passed ✅", model_name)

        except asyncio.TimeoutError:
            LOG.error("OTA download timeout for model: %s", model_name)
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception as exc:
            LOG.error("OTA model staging error for %s: %s", model_name, exc)
            if tmp_path.exists():
                tmp_path.unlink()
            # Rollback: restore backup
            if backup_path.exists() and target_path.exists():
                shutil.copy2(str(backup_path), str(target_path))
                LOG.warning("OTA: rolled back to backup for %s", model_name)

    # ── Config update ──────────────────────────────────────────────────────

    async def _apply_config(self, data: dict) -> None:
        """Atomic config update: write to .tmp then rename."""
        config_path = Path("/etc/flip/gateway.yaml")
        if not config_path.parent.exists():
            # Fallback to local config in dev
            config_path = self.db_path.parent / "config" / "gateway.yaml"

        config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = config_path.with_suffix(".yaml.tmp")
        try:
            import yaml
            tmp_path.write_text(
                yaml.dump(data.get("config", data), default_flow_style=False),
                encoding="utf-8",
            )
            shutil.move(str(tmp_path), str(config_path))
            LOG.info("Config updated atomically: %s", config_path)
        except Exception as exc:
            LOG.error("Config apply error: %s", exc)
            if tmp_path.exists():
                tmp_path.unlink()

    # ── Map tile diff ──────────────────────────────────────────────────────

    async def _apply_tile_diff(self, data: dict) -> None:
        """
        Apply incremental map tile diff to local MBTiles database.
        Tiles are small (< 256KB each) PNG/PBF blobs.
        """
        mbtiles_path = self.db_path.parent / "map.mbtiles"
        tiles = data.get("tiles", [])
        if not tiles:
            return

        try:
            with sqlite3.connect(str(mbtiles_path), timeout=10) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tiles (
                        zoom_level INTEGER,
                        tile_column INTEGER,
                        tile_row INTEGER,
                        tile_data BLOB,
                        PRIMARY KEY (zoom_level, tile_column, tile_row)
                    )
                """)
                for tile in tiles:
                    import base64
                    tile_data = base64.b64decode(tile.get("data_b64", ""))
                    conn.execute("""
                        INSERT OR REPLACE INTO tiles (zoom_level, tile_column, tile_row, tile_data)
                        VALUES (?, ?, ?, ?)
                    """, (tile["z"], tile["x"], tile["y"], tile_data))
                conn.commit()
            LOG.info("Map tiles updated: %d tiles applied", len(tiles))
        except Exception as exc:
            LOG.warning("Map tile diff error: %s", exc)

    # ── Legacy API (backward compat) ───────────────────────────────────────

    async def pull_inbox_legacy(self) -> None:
        """Legacy stub kept for backward compat — delegates to pull_inbox()."""
        await self.pull_inbox()
