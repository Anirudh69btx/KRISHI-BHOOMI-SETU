"""
FLIP Core API — Segment 05: Temporal.io Anomaly Detection Workflow
===================================================================
Runs every 15 minutes per farm:
  1. Isolation Forest inference on last 4h data
  2. Persist anomalies to sensor_anomalies hypertable
  3. Emit NATS farm.{farm_id}.sensor.anomaly events
  4. Update sensor health scores
  5. Check / create maintenance tickets

Daily retraining at 02:00 UTC.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta, datetime, timezone
from typing import Any

import structlog
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

logger = structlog.get_logger(__name__)

# ── Activity definitions ──────────────────────────────────────────────────────

@activity.defn(name="run_isolation_forest")
async def run_isolation_forest_activity(farm_id: str) -> list[dict]:
    """Run IF inference for a single farm. Returns anomaly list."""
    from flip_api.database import get_session
    from flip_api.services.anomaly_service import AnomalyService

    async with get_session() as session:
        svc = AnomalyService(session=session, nats_client=None)
        return await svc.run_inference(farm_id)


@activity.defn(name="persist_anomaly")
async def persist_anomaly_activity(anomaly: dict) -> None:
    """Persist a single anomaly event to TimescaleDB."""
    from flip_api.database import get_session
    from flip_api.services.anomaly_service import AnomalyService

    async with get_session() as session:
        svc = AnomalyService(session=session, nats_client=None)
        await svc.persist_anomaly(anomaly)
        await session.commit()


@activity.defn(name="emit_nats_anomaly")
async def emit_nats_anomaly_activity(farm_id: str, anomaly: dict) -> None:
    """Publish anomaly event to NATS."""
    try:
        from flip_api.main import nats_client  # type: ignore[attr-defined]
        if nats_client:
            await nats_client.publish(
                f"farm.{farm_id}.sensor.anomaly", anomaly
            )
    except Exception as exc:
        logger.warning("nats_emit_failed", error=str(exc))


@activity.defn(name="update_sensor_health")
async def update_sensor_health_activity(farm_id: str) -> list[dict]:
    """Recompute health scores for all devices on a farm."""
    from flip_api.database import get_session
    from flip_api.services.health_scoring_service import HealthScoringService

    try:
        from flip_api.main import nats_client  # type: ignore[attr-defined]
    except Exception:
        nats_client = None

    async with get_session() as session:
        svc = HealthScoringService(session=session, nats_client=nats_client)
        results = await svc.run_farm(farm_id)
        await session.commit()
        return results


@activity.defn(name="retrain_isolation_forest")
async def retrain_isolation_forest_activity(farm_id: str) -> bool:
    """Daily retrain: fit IF on 30-day data window."""
    from flip_api.database import get_session
    from flip_api.services.anomaly_service import AnomalyService

    async with get_session() as session:
        svc = AnomalyService(session=session, nats_client=None)
        success = await svc.train(farm_id)
        return success


# ── Workflow definitions ──────────────────────────────────────────────────────

@workflow.defn(name="AnomalyDetectionWorkflow")
class AnomalyDetectionWorkflow:
    """
    Long-running workflow: one instance per farm.
    Loops every 15 minutes: inference → persist → NATS → health scores.
    """

    @workflow.run
    async def run(self, farm_id: str) -> None:
        logger.info("anomaly_workflow_started", farm_id=farm_id)

        while True:
            # Wait for next 15-minute window
            await asyncio.sleep(15 * 60)  # Temporal converts to workflow.sleep

            # 1. Run Isolation Forest inference
            anomalies: list[dict] = await workflow.execute_activity(
                run_isolation_forest_activity,
                farm_id,
                start_to_close_timeout=timedelta(minutes=5),
            )

            # 2. Persist + emit each anomaly
            for anomaly in anomalies:
                await workflow.execute_activity(
                    persist_anomaly_activity,
                    anomaly,
                    start_to_close_timeout=timedelta(seconds=30),
                )
                await workflow.execute_activity(
                    emit_nats_anomaly_activity,
                    farm_id,
                    anomaly,
                    start_to_close_timeout=timedelta(seconds=10),
                )

            # 3. Update sensor health scores
            await workflow.execute_activity(
                update_sensor_health_activity,
                farm_id,
                start_to_close_timeout=timedelta(minutes=2),
            )

            logger.info(
                "anomaly_workflow_cycle_done",
                farm_id=farm_id,
                anomalies_found=len(anomalies),
            )


@workflow.defn(name="DailyRetrainWorkflow")
class DailyRetrainWorkflow:
    """
    Daily workflow: retrain all farm Isolation Forest models at 02:00 UTC.
    """

    @workflow.run
    async def run(self, farm_ids: list[str]) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for farm_id in farm_ids:
            ok: bool = await workflow.execute_activity(
                retrain_isolation_forest_activity,
                farm_id,
                start_to_close_timeout=timedelta(minutes=30),
            )
            results[farm_id] = ok
        return results


# ── Worker bootstrap ──────────────────────────────────────────────────────────

async def run_worker(
    temporal_url: str = "localhost:7233",
    task_queue: str = "flip-anomaly-queue",
) -> None:
    """Start Temporal worker. Run as a standalone process or alongside FastAPI."""
    client = await Client.connect(temporal_url)
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[AnomalyDetectionWorkflow, DailyRetrainWorkflow],
        activities=[
            run_isolation_forest_activity,
            persist_anomaly_activity,
            emit_nats_anomaly_activity,
            update_sensor_health_activity,
            retrain_isolation_forest_activity,
        ],
    )
    logger.info("temporal_worker_started", task_queue=task_queue)
    await worker.run()


# ── CLI entry-point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    temporal_url = sys.argv[1] if len(sys.argv) > 1 else "localhost:7233"
    asyncio.run(run_worker(temporal_url=temporal_url))
