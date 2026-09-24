#!/usr/bin/env python3
"""
FLIP Gateway Simulator for CI Pipeline
Tests MQTT ingestion, local buffer database, and Edge AI trigger workflows.
"""

import argparse
import asyncio
import json
import logging
import sqlite3
import sys
import tempfile
from pathlib import Path

# Ensure workspace root and edge/gateway are in python path
ROOT = Path(__file__).resolve().parent.parent
GATEWAY_DIR = ROOT / "edge" / "gateway"
for p in [str(ROOT), str(GATEWAY_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ci_gateway_sim")


async def run_ci_gateway_test(farm_id: str, db_path: Path):
    logger.info(f"=== Starting FLIP Gateway CI Test Harness for Farm: {farm_id} ===")

    # 1. Initialize SQLite Buffer Database
    schema_path = Path("edge/gateway/storage/schema.sql")
    with sqlite3.connect(db_path) as conn:
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            logger.info("✅ SQLite buffer schema initialized successfully.")
        else:
            logger.error("schema.sql not found!")
            return False

    # 2. Simulate Ingesting Sensor Telemetry
    test_packets = [
        {"sensor_type": "TEMP_AIR", "value": 29.5, "unit": "°C"},
        {"sensor_type": "HUMIDITY", "value": 72.0, "unit": "%"},
        {"sensor_type": "VWC", "value": 31.8, "unit": "%"},
        {"sensor_type": "RAIN_MM", "value": 0.4, "unit": "mm"},
    ]

    with sqlite3.connect(db_path) as conn:
        for pkt in test_packets:
            conn.execute("""
                INSERT INTO sensor_raw (farm_id, device_id, sensor_type, value, unit, quality_flag)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (farm_id, "node-test-01", pkt["sensor_type"], pkt["value"], pkt["unit"], "RAW"))
        conn.commit()

        cursor = conn.execute("SELECT COUNT(*) FROM sensor_raw WHERE farm_id = ?", (farm_id,))
        count = cursor.fetchone()[0]
        assert count == 4, f"Expected 4 records, got {count}"
        logger.info(f"✅ Telemetry buffer validated: {count} packets stored.")

    # 3. Test Edge AI Multimodal Advisory Generation
    from edge.gateway.services.inference_engine import InferenceEngine
    engine = InferenceEngine(Path("edge/gateway/models"))
    await engine.start()

    dummy_vision = {"condition": "early_blight", "confidence": 0.89, "pest_detected": False}
    dummy_sensors = {"rh": 78.0, "temp_air": 28.0}
    advisory = engine.generate_advisory(dummy_vision, dummy_sensors)

    assert advisory["urgency"] == "HIGH", "Expected HIGH urgency for early_blight with high RH"
    assert "सावधान" in advisory["next_text"]["hi"]
    logger.info(f"✅ Multimodal Edge AI Advisory verified: Urgency={advisory['urgency']}")

    # 4. Test CRDT State Resolution
    from edge.gateway.storage.crdt import StateSynchronizer
    crdt = StateSynchronizer("gw-ci")
    local_val, local_clock = "VAL_A", 5
    remote_val, remote_clock = "VAL_B", 8
    resolved_val, resolved_clock = crdt.resolve_field(local_val, local_clock, remote_val, remote_clock)
    assert resolved_val == "VAL_B" and resolved_clock == 8
    logger.info("✅ CRDT Lamport clock state merge verified.")

    logger.info("=== All Gateway CI Verification Tests PASSED! ===")
    return True


def main():
    parser = argparse.ArgumentParser(description="FLIP Gateway CI Simulator")
    parser.add_argument("--farm-id", default="fa000001-0000-0000-0000-000000000001")
    args = parser.parse_args()

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = Path(tmp.name)
    tmp.close()

    try:
        success = asyncio.run(run_ci_gateway_test(args.farm_id, db_path))
        if not success:
            sys.exit(1)
    finally:
        import gc
        gc.collect()
        try:
            if db_path.exists():
                db_path.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    main()
