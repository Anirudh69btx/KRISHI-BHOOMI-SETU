"""
FLIP Core API — NATS JetStream Client
Canonical Architecture:
  Subject ≠ Stream name
  JetStream Streams persist & filter subjects into durable storage.
  
Canonical Event Subjects (Master Requirement):
  - farm.{farm_id}.sensor.raw           → raw sensor telemetry from edge nodes
  - farm.{farm_id}.advisory.generated   → AI advisory generated for farm
  - farm.{farm_id}.twin.updated         → digital twin CRDT state update
  - region.{district_id}.outbreak.detected → pest/disease/weather outbreak in region
  - model.registry.updated              → ML model registry release/update

Canonical JetStream Streams:
  - FARM_EVENTS:   subjects ["farm.*.sensor.raw", "farm.*.advisory.generated", "farm.*.twin.updated"]
  - REGION_EVENTS: subjects ["region.*.outbreak.detected"]
  - MODEL_EVENTS:  subjects ["model.registry.updated"]
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import nats
import structlog
from nats.aio.client import Client as NATSConn
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from nats.js.api import (
    AckPolicy,
    ConsumerConfig,
    DeliverPolicy,
    RetentionPolicy,
    StorageType,
    StreamConfig,
)

logger = structlog.get_logger(__name__)

# Type alias for NATS message handler
MsgHandler = Callable[[Msg], Awaitable[None]]

# ---- Canonical Stream Definitions -----------------------------------------------

FARM_EVENTS_STREAM = StreamConfig(
    name="FARM_EVENTS",
    subjects=[
        "farm.*.sensor.raw",
        "farm.*.advisory.generated",
        "farm.*.twin.updated",
        "farm.*.profile.synced",
    ],
    retention=RetentionPolicy.LIMITS,
    storage=StorageType.FILE,
    max_msgs=10_000_000,
    max_age=30 * 24 * 3600,  # 30 days
    num_replicas=1,
    description="Persistent stream for all farm-level telemetry, advisories, and digital twin events",
)

REGION_EVENTS_STREAM = StreamConfig(
    name="REGION_EVENTS",
    subjects=[
        "region.*.outbreak.detected",
    ],
    retention=RetentionPolicy.LIMITS,
    storage=StorageType.FILE,
    max_msgs=500_000,
    max_age=365 * 24 * 3600,  # 1 year
    num_replicas=1,
    description="Persistent stream for regional disaster, pest, and disease outbreak alerts",
)

MODEL_EVENTS_STREAM = StreamConfig(
    name="MODEL_EVENTS",
    subjects=[
        "model.registry.updated",
    ],
    retention=RetentionPolicy.LIMITS,
    storage=StorageType.FILE,
    max_msgs=50_000,
    max_age=180 * 24 * 3600,  # 180 days
    num_replicas=1,
    description="Persistent stream for ML model registry releases and continual learning triggers",
)

ALL_STREAMS = [
    FARM_EVENTS_STREAM,
    REGION_EVENTS_STREAM,
    MODEL_EVENTS_STREAM,
]


# ---- Client -------------------------------------------------------------------


@dataclass
class NATSClient:
    """
    Managed NATS JetStream client for FLIP Core API.

    Usage:
        client = NATSClient(nats_url="nats://localhost:4222")
        await client.connect()
        await client.ensure_streams()
        await client.publish_sensor_raw("farm-001", {"value": 32.4})
        await client.close()
    """

    nats_url: str
    _nc: NATSConn = field(init=False, repr=False)
    _js: JetStreamContext = field(init=False, repr=False)
    _connected: bool = field(default=False, init=False, repr=False)
    _subscriptions: list[Any] = field(default_factory=list, init=False, repr=False)

    async def connect(self) -> None:
        """Establish NATS connection with automatic reconnect."""
        self._nc = await nats.connect(
            self.nats_url,
            name="flip-core-api",
            reconnect_time_wait=2,
            max_reconnect_attempts=-1,  # infinite reconnect
            error_cb=self._on_error,
            disconnected_cb=self._on_disconnect,
            reconnected_cb=self._on_reconnect,
            closed_cb=self._on_close,
        )
        self._js = self._nc.jetstream()
        self._connected = True
        logger.info("NATS connected", url=self.nats_url)

    async def close(self) -> None:
        """Gracefully drain and close NATS connection."""
        if self._connected:
            await self._nc.drain()
            self._connected = False
            logger.info("NATS connection drained and closed")

    @property
    def js(self) -> JetStreamContext:
        """Expose JetStream context for advanced usage."""
        if not self._connected:
            raise RuntimeError("NATS not connected. Call connect() first.")
        return self._js

    # ---- Stream Management ------------------------------------------------

    async def ensure_streams(self) -> None:
        """Idempotently create or update all canonical FLIP JetStream streams."""
        for stream_cfg in ALL_STREAMS:
            try:
                await self._js.add_stream(stream_cfg)
                logger.info("NATS stream created", stream=stream_cfg.name)
            except nats.js.errors.BadRequestError:
                # Stream already exists — update configuration
                await self._js.update_stream(stream_cfg)
                logger.info("NATS stream updated", stream=stream_cfg.name)
            except Exception as exc:
                logger.error(
                    "NATS stream setup failed",
                    stream=stream_cfg.name,
                    error=str(exc),
                )
                raise

    # ---- Generic Publishing -----------------------------------------------

    async def publish(
        self,
        subject: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> None:
        """Publish a JSON payload to a JetStream subject."""
        raw = json.dumps(payload).encode()
        try:
            ack = await self._js.publish(subject, raw, headers=headers)
            logger.debug(
                "NATS published",
                subject=subject,
                stream=ack.stream,
                seq=ack.seq,
            )
        except Exception as exc:
            logger.error("NATS publish failed", subject=subject, error=str(exc))
            raise

    # ---- Canonical Publishers Matching Master Requirements ----------------

    async def publish_sensor_raw(
        self,
        farm_id: str,
        reading: dict[str, Any],
    ) -> None:
        """Publish raw sensor telemetry to subject: farm.{farm_id}.sensor.raw"""
        subject = f"farm.{farm_id}.sensor.raw"
        await self.publish(subject, reading)

    async def publish_advisory_generated(
        self,
        farm_id: str,
        advisory: dict[str, Any],
    ) -> None:
        """Publish generated advisory to subject: farm.{farm_id}.advisory.generated"""
        subject = f"farm.{farm_id}.advisory.generated"
        await self.publish(subject, advisory)

    async def publish_twin_updated(
        self,
        farm_id: str,
        twin_event: dict[str, Any],
    ) -> None:
        """Publish digital twin state event to subject: farm.{farm_id}.twin.updated"""
        subject = f"farm.{farm_id}.twin.updated"
        await self.publish(subject, twin_event)

    async def publish_outbreak_detected(
        self,
        district_id: str,
        outbreak: dict[str, Any],
    ) -> None:
        """Publish outbreak alert to subject: region.{district_id}.outbreak.detected"""
        subject = f"region.{district_id}.outbreak.detected"
        await self.publish(subject, outbreak)

    async def publish_model_registry_updated(
        self,
        metadata: dict[str, Any],
    ) -> None:
        """Publish model registry event to subject: model.registry.updated"""
        subject = "model.registry.updated"
        await self.publish(subject, metadata)

    # ---- Canonical Subscriptions ------------------------------------------

    async def subscribe(
        self,
        subject: str,
        durable: str | None = None,
        handler: MsgHandler | None = None,
        queue_group: str | None = None,
        deliver_policy: DeliverPolicy = DeliverPolicy.NEW,
    ) -> Any:
        """Subscribe to a JetStream subject with an explicit durable consumer."""
        consumer_cfg = ConsumerConfig(
            durable_name=durable,
            ack_policy=AckPolicy.EXPLICIT,
            deliver_policy=deliver_policy,
            filter_subject=subject,
        )
        if durable:
            sub = await self._js.subscribe(
                subject,
                durable=durable,
                cb=handler,
                config=consumer_cfg,
                queue=queue_group,
            )
        else:
            sub = await self._js.subscribe(subject, cb=handler)

        self._subscriptions.append(sub)
        logger.info("NATS subscribed", subject=subject, durable=durable)
        return sub

    async def subscribe_farm_sensor_raw(
        self,
        farm_id: str,
        handler: MsgHandler,
        durable: str | None = None,
    ) -> Any:
        """Subscribe to raw sensor telemetry for a farm."""
        subject = f"farm.{farm_id}.sensor.raw"
        return await self.subscribe(
            subject=subject,
            durable=durable or f"core-api-sensor-{farm_id}",
            handler=handler,
        )

    async def subscribe_region_outbreaks(
        self,
        district_id: str,
        handler: MsgHandler,
        durable: str | None = None,
    ) -> Any:
        """Subscribe to regional outbreak detections."""
        subject = f"region.{district_id}.outbreak.detected"
        return await self.subscribe(
            subject=subject,
            durable=durable or f"core-api-outbreak-{district_id}",
            handler=handler,
        )

    # ---- Request/Reply (Synchronous RPC over Core NATS) -------------------

    async def request(
        self,
        subject: str,
        payload: dict[str, Any],
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        """Synchronous request/reply over NATS."""
        raw = json.dumps(payload).encode()
        msg = await self._nc.request(subject, raw, timeout=timeout)
        return json.loads(msg.data.decode())

    # ---- Callbacks --------------------------------------------------------

    async def _on_error(self, error: Exception) -> None:
        logger.error("NATS error", error=str(error))

    async def _on_disconnect(self) -> None:
        self._connected = False
        logger.warning("NATS disconnected — attempting reconnect...")

    async def _on_reconnect(self) -> None:
        self._connected = True
        logger.info("NATS reconnected")

    async def _on_close(self) -> None:
        logger.info("NATS connection closed")

    # ---- pg_notify → NATS Bridge ------------------------------------------

    async def listen_pg_notify(self, postgres_dsn: str) -> None:
        """
        Open a dedicated asyncpg connection and listen on the 'nats_bridge'
        pg_notify channel.  When a NOTIFY arrives (emitted by notify_nats_event()
        DB trigger on advisories / twin_events / farmer_actions), the payload
        is deserialized and published to the appropriate NATS JetStream subject.

        This coroutine runs indefinitely as a background task.  It reconnects
        automatically on transient connection failures.

        Args:
            postgres_dsn: asyncpg-compatible DSN
                e.g. postgresql://user:pass@host:5432/dbname
        """
        import asyncpg  # lazy import — not needed outside this method

        # Strip the asyncpg driver prefix SQLAlchemy uses
        dsn = postgres_dsn.replace("postgresql+asyncpg://", "postgresql://")

        while True:
            conn: asyncpg.Connection | None = None
            try:
                conn = await asyncpg.connect(dsn)

                async def _handler(
                    connection: asyncpg.Connection,  # noqa: ARG001
                    pid: int,  # noqa: ARG001
                    channel: str,  # noqa: ARG001
                    payload: str,
                ) -> None:
                    await self._pg_notify_handler(payload)

                await conn.add_listener("nats_bridge", _handler)
                logger.info("pg_notify_listener_started", channel="nats_bridge")

                # Keep alive — asyncpg fires the listener callback automatically
                while True:
                    await asyncio.sleep(60)  # heartbeat; real events arrive async

            except asyncio.CancelledError:
                logger.info("pg_notify_listener_cancelled")
                break
            except Exception as exc:
                logger.error(
                    "pg_notify_listener_error", error=str(exc)
                )
                await asyncio.sleep(5)  # back-off before reconnect
            finally:
                if conn is not None:
                    try:
                        await conn.close()
                    except Exception:
                        pass

    async def _pg_notify_handler(self, raw_payload: str) -> None:
        """
        Deserialize a pg_notify payload and publish to NATS JetStream.
        Expected payload shape (from notify_nats_event() trigger):
        {
            "table": "advisories",
            "operation": "INSERT",
            "record": {...},
            "old_record": null | {...},
            "timestamp": "..."
        }
        """
        try:
            event: dict[str, Any] = json.loads(raw_payload)
            table = event.get("table", "generic")
            operation = event.get("operation", "insert").lower()
            record = event.get("record") or {}

            farm_id = (
                record.get("farm_id")
                or (event.get("old_record") or {}).get("farm_id")
                or "unknown"
            )

            subject = self._table_to_subject(table, farm_id, operation)
            if subject is None:
                logger.debug(
                    "pg_notify_no_subject_mapped",
                    table=table,
                    operation=operation,
                )
                return

            await self.publish(subject, event)
            logger.debug(
                "pg_notify_forwarded",
                table=table,
                operation=operation,
                subject=subject,
            )

        except json.JSONDecodeError as exc:
            logger.error("pg_notify_invalid_json", error=str(exc))
        except Exception as exc:
            logger.error("pg_notify_handler_error", error=str(exc))

    def _table_to_subject(
        self, table: str, farm_id: str, operation: str
    ) -> str | None:
        """
        Map a DB table + operation to the canonical NATS subject.
        Returns None for tables that should not be forwarded.
        """
        mapping: dict[str, str] = {
            "advisories":     f"farm.{farm_id}.advisory.generated",
            "twin_events":    f"farm.{farm_id}.twin.updated",
            "farmer_actions": f"farm.{farm_id}.sensor.raw",  # action event
            "profiles":       f"farm.{farm_id}.profile.synced",
        }
        return mapping.get(table)

