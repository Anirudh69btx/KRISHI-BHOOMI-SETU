"""
Comprehensive Unit Tests for FLIP Gateway Services & CRDT Engine
"""

import asyncio
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

from edge.gateway.services.inference_engine import InferenceEngine, VisionResult
from edge.gateway.services.voice_agent import VoiceAgent, Intent
from edge.gateway.services.siren_agent import SirenAgent
from edge.gateway.services.sync_agent import SyncAgent
from edge.gateway.services.health_monitor import HealthMonitor
from edge.gateway.services.connectivity_manager import ConnectivityManager, ConnectionType
from edge.gateway.services.ota_agent import OTAAgent
from edge.gateway.storage.crdt import LWWRegister, ORSet, LamportClock, CRDTEngine


class TestGatewayServices(unittest.TestCase):

    def test_crdt_lamport_clock(self):
        c1 = LamportClock("nodeA")
        c2 = LamportClock("nodeB")
        t1 = c1.tick()
        t2 = c2.update(t1[0], t1[1])
        self.assertGreater(t2[0], t1[0])

    def test_crdt_lww_register(self):
        reg1 = LWWRegister(value="alpha", timestamp=(100, "node1"))
        reg2 = LWWRegister(value="beta", timestamp=(200, "node2"))
        merged = reg1.merge(reg2)
        self.assertEqual(merged.value, "beta")
        self.assertEqual(merged.timestamp[0], 200)

    def test_crdt_or_set(self):
        s1 = ORSet("nodeA")
        s2 = ORSet("nodeB")

        s1.add("crop_cotton", "tag1")
        s2.add("crop_wheat", "tag2")

        merged = s1.merge(s2)
        self.assertIn("crop_cotton", merged.value())
        self.assertIn("crop_wheat", merged.value())

        merged.remove("crop_cotton")
        self.assertNotIn("crop_cotton", merged.value())
        self.assertIn("crop_wheat", merged.value())

    def test_crdt_engine_apply_and_merge(self):
        engine = CRDTEngine(node_id="test_node")
        engine.apply_local("advisory_01", "Spray Copper Oxychloride", crdt_type="lww")
        self.assertEqual(engine.get_state("advisory_01"), "Spray Copper Oxychloride")

        # Remote update with higher Lamport clock
        remote = {"value": "Harvest tomorrow", "timestamp": [99, "cloud"]}
        engine.merge_remote("advisory_01", remote, crdt_type="lww")
        self.assertEqual(engine.get_state("advisory_01"), "Harvest tomorrow")

    def test_inference_advisory(self):
        async def _test():
            engine = InferenceEngine(Path("edge/gateway/models"))
            await engine.start()

            vision = await engine.run("mock_leaf.jpg")
            self.assertEqual(vision["condition"], "early_blight")
            self.assertTrue(vision["pest_detected"])

            sensors = {"rh": 85.0, "temp_air": 29.0, "leaf_wet": 0.8}
            advisory = engine.generate_advisory(vision, sensors)
            self.assertEqual(advisory["urgency"], "HIGH")
            self.assertIn("NOW", advisory)
            self.assertIn("NEXT", advisory)
            self.assertIn("WHY", advisory)
            self.assertIn("hi", advisory["next_text"])
            self.assertIn("mr", advisory["next_text"])
            self.assertIn("en", advisory["next_text"])

        asyncio.run(_test())

    def test_voice_agent_intents(self):
        agent = VoiceAgent()
        res_water = agent.classify_intent("मुझे खेत में पानी कब देना चाहिए?")
        self.assertEqual(res_water["intent"], "QUERY_IRRIGATION")

        res_pest = agent.classify_intent("फसल में कीड़ा लग गया है कौन सा spray करें?")
        self.assertEqual(res_pest["intent"], "QUERY_PEST_DISEASE")

        res_weather = agent.classify_intent("आज का मौसम कैसा रहेगा?")
        self.assertEqual(res_weather["intent"], "QUERY_WEATHER")

    def test_health_monitor_collect(self):
        async def _test():
            monitor = HealthMonitor()
            stats = await monitor.collect()
            self.assertIn("cpu_temp", stats)
            self.assertIn("ram_usage", stats)
            self.assertIn("disk_usage", stats)
            self.assertIn("battery", stats)
            self.assertGreater(stats["battery"]["voltage_mv"], 10000)

        asyncio.run(_test())

    def test_connectivity_manager_types(self):
        async def _test():
            mgr = ConnectivityManager()
            self.assertEqual(mgr.get_current_type(), ConnectionType.OFFLINE)
            is_online = await mgr.is_online()
            self.assertFalse(is_online)

        asyncio.run(_test())

    def test_siren_trigger(self):
        async def _test():
            siren = SirenAgent(audio_device="default")
            await siren.trigger({"urgency": "HIGH"})
            self.assertFalse(siren.is_playing)

        asyncio.run(_test())

    def test_crdt_persist_and_reload(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = Path(tmpdir) / "test_gateway.db"
            engine1 = CRDTEngine(db_path=db_path, node_id="gw-01")
            engine1.apply_farmer_action("adv_001", {"action": "SPRAY_DONE", "operator": "Farmer Ram"})
            state1 = engine1.get_state("farmer_action:adv_001")
            self.assertEqual(state1["action"], "SPRAY_DONE")

            # Spin up a second engine with the same SQLite db file (simulating reboot)
            engine2 = CRDTEngine(db_path=db_path, node_id="gw-02")
            state2 = engine2.get_state("farmer_action:adv_001")
            self.assertIsNotNone(state2)
            self.assertEqual(state2["action"], "SPRAY_DONE")
            self.assertEqual(state2["operator"], "Farmer Ram")

    def test_crdt_farmer_action(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = Path(tmpdir) / "test_gateway.db"
            engine = CRDTEngine(db_path=db_path, node_id="gw-01")
            engine.apply_farmer_action("adv_999", {"action": "IRRIGATION_DONE"})
            pending = engine.get_pending_actions()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["advisory_id"], "adv_999")
            self.assertIsNone(pending[0]["synced_at"])

            engine.mark_action_synced("adv_999")
            pending_after = engine.get_pending_actions()
            self.assertEqual(len(pending_after), 0)

    def test_crdt_orset_sensor_buffer(self):
        engine1 = CRDTEngine(node_id="gw-01")
        engine1.add_sensor_reading("VWC", {"value": 35.2, "device_id": "sensor-01"})
        readings = engine1.get_sensor_buffer("VWC")
        self.assertEqual(len(readings), 1)
        self.assertEqual(readings[0]["value"], 35.2)

        cloud_clock = LamportClock("cloud-01", time=50)
        cloud_readings = [
            {"id": "cloud_r1", "value": 38.1, "device_id": "sensor-02"}
        ]
        engine1.merge_sensor_buffer("VWC", cloud_readings, cloud_clock)
        merged_readings = engine1.get_sensor_buffer("VWC")
        self.assertEqual(len(merged_readings), 2)

    def test_crdt_offline_sync_simulation(self):
        # 100 readings during a 14-day network blackout
        engine = CRDTEngine(node_id="gw-offline")
        for i in range(100):
            engine.add_sensor_reading("RH", {"reading_idx": i, "rh": 60.0 + (i % 30)})

        buffer = engine.get_sensor_buffer("RH")
        self.assertEqual(len(buffer), 100)

        # Merge with remote engine
        remote_engine = CRDTEngine(node_id="cloud-server")
        raw_set = engine.sets["sensor_buffer:RH"]
        remote_engine.sets["sensor_buffer:RH"] = ORSet(node_id="cloud-server").merge(raw_set)
        reconciled = remote_engine.get_sensor_buffer("RH")
        self.assertEqual(len(reconciled), 100)

    def test_inference_vision_pipeline(self):
        async def _test():
            engine = InferenceEngine(Path("edge/gateway/models"))
            await engine.start()
            res = await engine.run_vision_pipeline("mock_leaf.jpg")
            self.assertIsInstance(res, VisionResult)
            self.assertEqual(res.crop_type, "cotton")
            self.assertIn(res.primary_condition, res.disease_probs)
            self.assertGreater(res.latency_ms, 0.0)
            engine.shutdown()

        asyncio.run(_test())

    def test_inference_fusion_lite(self):
        engine = InferenceEngine(Path("edge/gateway/models"))
        sensor_vec = np.zeros(48, dtype=np.float32)
        sensor_vec[10] = 0.85
        stage_vec = np.array([4], dtype=np.int64)
        risk = engine.run_fusion_lite(sensor_vec, stage_vec)
        self.assertIsInstance(risk, float)
        self.assertGreaterEqual(risk, 0.0)
        self.assertLessEqual(risk, 1.0)

    def test_inference_microclimate(self):
        async def _test():
            engine = InferenceEngine(Path("edge/gateway/models"))
            history = np.zeros((24, 10), dtype=np.float32)
            history[:, 4] = 65.0
            res = await engine.run_microclimate(history)
            self.assertIn("canopy_rh", res)
            self.assertIn("lwd_hours", res)
            self.assertIsInstance(res["canopy_rh"], float)
            self.assertIsInstance(res["lwd_hours"], float)

        asyncio.run(_test())

    def test_voice_intent_extended(self):
        agent = VoiceAgent()
        r1 = agent.classify_intent("फसल कैसी है?")
        self.assertEqual(r1.intent, Intent.STATUS_QUERY)

        r2 = agent.classify_intent("खेत में कीड़ा दिख रहा है")
        self.assertIn(r2.intent, (Intent.PEST_REPORT, Intent.SPRAY_QUERY))

        r3 = agent.classify_intent("फसल की कटाई कब शुरू करें?")
        self.assertEqual(r3.intent, Intent.HARVEST_QUERY)

        r4 = agent.classify_intent("आज मंडी में क्या भाव चल रहा है?")
        self.assertEqual(r4.intent, Intent.MANDI_PRICE)

        r5 = agent.classify_intent("कीटनाशक का छिड़काव कब करें?")
        self.assertEqual(r5.intent, Intent.SPRAY_QUERY)

        r6 = agent.classify_intent("मिट्टी की जांच कब करानी चाहिए?")
        self.assertEqual(r6.intent, Intent.SOIL_QUERY)

    def test_sync_push_outbox_offline(self):
        async def _test():
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
                db_path = Path(tmpdir) / "test_gateway.db"
                schema_path = Path("edge/gateway/storage/schema.sql")
                if schema_path.exists():
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    try:
                        with open(schema_path, "r", encoding="utf-8") as f:
                            conn.executescript(f.read())
                    finally:
                        conn.close()

                sync = SyncAgent(
                    db_path=db_path,
                    nats_url="nats://127.0.0.1:4222",
                    farm_id="test-farm-01",
                )
                is_online = await sync.is_online()
                self.assertFalse(is_online)
                pushed = await sync.push_outbox()
                self.assertEqual(pushed, 0)

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
