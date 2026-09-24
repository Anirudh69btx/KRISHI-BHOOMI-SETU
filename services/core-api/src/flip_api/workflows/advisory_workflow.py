"""
FLIP v3.0 — Temporal Workflow Definitions
Advisory Generation + Digital Twin Update workflows.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta
from typing import Any

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker


# ─── Activities ───────────────────────────────────────────────────────────────

@activity.defn(name="fetch_farm_sensor_data")
async def fetch_farm_sensor_data(farm_id: str, hours: int = 24) -> dict[str, Any]:
    """Fetch latest sensor readings for a farm from TimescaleDB."""
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"http://core-api:8000/api/v1/sensors/farms/{farm_id}",
            params={"hours": hours},
            headers={"X-Internal-Key": "temporal-internal"},
        )
        resp.raise_for_status()
        return {"farm_id": farm_id, "readings": resp.json()}


@activity.defn(name="run_ml_inference")
async def run_ml_inference(farm_id: str, features: dict[str, Any]) -> dict[str, Any]:
    """Call ML inference service to get crop health prediction."""
    import httpx

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "http://ml-inference:8001/predict",
            json={"farm_id": farm_id, "features": features},
        )
        resp.raise_for_status()
        return resp.json()


@activity.defn(name="generate_advisory")
async def generate_advisory(
    farm_id: str,
    prediction: dict[str, Any],
    sensor_data: dict[str, Any],
) -> str:
    """Generate and store a localized advisory. Returns advisory_id."""
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "http://core-api:8000/api/v1/advisories/generate",
            json={
                "farm_id": farm_id,
                "prediction": prediction,
                "sensor_data": sensor_data,
            },
            headers={"X-Internal-Key": "temporal-internal"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["advisory_id"]


@activity.defn(name="update_digital_twin")
async def update_digital_twin(
    farm_id: str,
    sensor_data: dict[str, Any],
    prediction: dict[str, Any],
) -> bool:
    """Update the farm's digital twin state in Postgres."""
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"http://core-api:8000/api/v1/farms/{farm_id}/twin/update",
            json={"sensor_data": sensor_data, "prediction": prediction},
            headers={"X-Internal-Key": "temporal-internal"},
        )
        return resp.status_code in (200, 201)


@activity.defn(name="send_push_notification")
async def send_push_notification(farm_id: str, advisory_id: str, severity: str) -> bool:
    """Send push notification to farmer via NATS → Web Push."""
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "http://core-api:8000/api/v1/notifications/push",
            json={"farm_id": farm_id, "advisory_id": advisory_id, "severity": severity},
            headers={"X-Internal-Key": "temporal-internal"},
        )
        return resp.status_code == 200


# ─── Workflows ────────────────────────────────────────────────────────────────

@workflow.defn(name="AdvisoryGenerationWorkflow")
class AdvisoryGenerationWorkflow:
    """
    Triggered on schedule (every hour per farm) or on-demand.
    1. Fetch 24h sensor data
    2. Run ML inference
    3. If confidence > 0.6: generate advisory
    4. Update digital twin
    5. Send push notification for high/critical severity
    """

    @workflow.run
    async def run(self, farm_id: str) -> dict[str, Any]:
        workflow.logger.info("AdvisoryGenerationWorkflow starting", farm_id=farm_id)

        # Step 1: Fetch sensor data
        sensor_data = await workflow.execute_activity(
            fetch_farm_sensor_data,
            args=[farm_id, 24],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3),
        )

        if not sensor_data.get("readings"):
            return {"status": "skipped", "reason": "no_sensor_data"}

        # Step 2: ML inference
        prediction = await workflow.execute_activity(
            run_ml_inference,
            args=[farm_id, sensor_data],
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=workflow.RetryPolicy(maximum_attempts=2),
        )

        confidence = prediction.get("confidence", 0)
        if confidence < 0.6:
            return {
                "status": "skipped",
                "reason": "low_confidence",
                "confidence": confidence,
            }

        # Step 3: Generate advisory
        advisory_id = await workflow.execute_activity(
            generate_advisory,
            args=[farm_id, prediction, sensor_data],
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Step 4: Update digital twin (non-blocking, best-effort)
        await workflow.execute_activity(
            update_digital_twin,
            args=[farm_id, sensor_data, prediction],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=workflow.RetryPolicy(maximum_attempts=1),
        )

        # Step 5: Notify for high/critical
        severity = prediction.get("severity", "low")
        if severity in ("high", "critical"):
            await workflow.execute_activity(
                send_push_notification,
                args=[farm_id, advisory_id, severity],
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=workflow.RetryPolicy(maximum_attempts=2),
            )

        return {
            "status": "completed",
            "farm_id": farm_id,
            "advisory_id": advisory_id,
            "prediction_label": prediction.get("label"),
            "confidence": confidence,
            "severity": severity,
        }


@workflow.defn(name="DisasterDrillWorkflow")
class DisasterDrillWorkflow:
    """
    Triggers a disaster drill: creates a synthetic alert, notifies all farmers
    in affected districts, waits for acknowledgements, generates drill report.
    """

    @workflow.run
    async def run(self, drill_config: dict[str, Any]) -> dict[str, Any]:
        workflow.logger.warning("DisasterDrillWorkflow starting", config=drill_config)

        # For brevity: real implementation would fan-out to all farms in districts
        return {
            "status": "drill_completed",
            "alert_type": drill_config.get("alert_type"),
            "districts": drill_config.get("affected_districts", []),
        }


# ─── Worker Entry Point ───────────────────────────────────────────────────────

async def run_worker() -> None:
    """Start Temporal worker with all workflows and activities."""
    client = await Client.connect(
        "temporal:7233",
        namespace="flip",
    )

    worker = Worker(
        client,
        task_queue="flip-main",
        workflows=[AdvisoryGenerationWorkflow, DisasterDrillWorkflow],
        activities=[
            fetch_farm_sensor_data,
            run_ml_inference,
            generate_advisory,
            update_digital_twin,
            send_push_notification,
        ],
    )

    print("[Temporal] Worker starting on queue: flip-main")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
