#!/usr/bin/env python3
"""
FLIP Enhanced Sensor Simulator
Generates high-fidelity agricultural telemetry across diurnal microclimate curves
Publishes to EMQX/Mosquitto MQTT broker in JSON or compact binary formats.
Usage: python scripts/simulate_sensor.py --farm-id farm-0001 --interval 5
"""

import argparse
import datetime
import json
import math
import os
import random
import sys
import time
import uuid
from typing import Dict, Any

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Please install paho-mqtt: pip install paho-mqtt")
    sys.exit(1)

# Agricultural sensor channels
CHANNELS = ["VWC", "EC", "TEMP_SOIL", "TEMP_AIR", "HUMIDITY", "LEAF_WETNESS", "RAIN_MM", "PAR_LIGHT", "BATTERY_MV"]


class MicroclimateSimulator:
    def __init__(self):
        self.seq_id = 0
        self.accumulated_rain = 0.0
        self.battery_mv = 3300 # LiFePO4 nominal

    def step(self, hour_of_day: float) -> Dict[str, float]:
        self.seq_id += 1
        
        # Diurnal solar curve: peaks at 13:00 (1 PM)
        solar_elevation = max(0.0, math.sin((hour_of_day - 6.0) * math.pi / 12.0))
        par_light = round(solar_elevation * 1600.0 + random.uniform(0, 50), 1)

        # Air Temperature: coldest at 05:00, hottest at 14:00 (22°C to 36°C)
        air_temp = round(22.0 + 14.0 * math.sin((hour_of_day - 8.0) * math.pi / 12.0) + random.uniform(-0.5, 0.5), 1)

        # Relative Humidity: inverted with temperature (90% at dawn, 40% at midday)
        rh = round(max(30.0, min(95.0, 90.0 - 45.0 * solar_elevation + random.uniform(-2, 2))), 1)

        # Soil Temperature: dampened and lagged behind air temp (24°C to 28°C)
        soil_temp = round(24.0 + 4.0 * math.sin((hour_of_day - 11.0) * math.pi / 12.0) + random.uniform(-0.2, 0.2), 1)

        # Soil VWC (30% to 35%)
        soil_vwc = round(32.5 + random.uniform(-0.3, 0.3), 1)

        # Electrical Conductivity (0.9 to 1.3 dS/m)
        ec = round(1.15 + random.uniform(-0.05, 0.05), 2)

        # Leaf Wetness: High during early morning dew (0.8 - 1.0), dry in day (0.0)
        leaf_wetness = round(max(0.0, min(1.0, (1.0 - solar_elevation * 1.5) + random.uniform(-0.05, 0.05))), 2)

        # Rain: Occasional light rain pulse
        rain_pulse = 0.2 if random.random() < 0.05 else 0.0
        self.accumulated_rain += rain_pulse

        # Battery slow discharge: ~3.25V with minor load fluctuation
        self.battery_mv = max(3000, self.battery_mv - random.choice([0, 1]))

        return {
            "TEMP_AIR": air_temp,
            "HUMIDITY": rh,
            "TEMP_SOIL": soil_temp,
            "VWC": soil_vwc,
            "EC": ec,
            "LEAF_WETNESS": leaf_wetness,
            "RAIN_MM": round(self.accumulated_rain, 1),
            "PAR_LIGHT": par_light,
            "BATTERY_MV": self.battery_mv,
        }


def run_simulator(args):
    broker_host = os.getenv("MQTT_HOST", args.host)
    broker_port = int(os.getenv("MQTT_PORT", args.port))

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"sim-node-{uuid.uuid4().hex[:6]}"
    )

    def on_connect(c, userdata, flags, rc, props=None):
        if rc == 0:
            print(f"✅ Connected to MQTT Broker at {broker_host}:{broker_port}")
        else:
            print(f"❌ Connection failed (code: {rc})")

    client.on_connect = on_connect

    try:
        client.connect(broker_host, broker_port, 60)
        client.loop_start()
    except Exception as exc:
        print(f"⚠️ Could not reach MQTT broker at {broker_host}:{broker_port}: {exc}")
        print("  Running in standalone simulation mode...")

    sim = MicroclimateSimulator()
    print(f"\n🌱 FLIP Sensor Simulation Started for Farm: {args.farm_id}")
    print(f"   Publishing to topic: farm/{args.farm_id}/sensor/raw every {args.interval}s")
    print("   Press Ctrl+C to terminate.\n")

    current_hour = 6.0
    try:
        while True:
            readings = sim.step(current_hour)
            ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

            for s_type, val in readings.items():
                payload = {
                    "timestamp": ts,
                    "seq_id": sim.seq_id,
                    "farm_id": args.farm_id,
                    "device_id": args.device_id,
                    "sensor_type": s_type,
                    "value": val,
                    "quality_flag": "RAW",
                    "metadata": {
                        "firmware": "v1.0.0-zephyr",
                        "battery_mv": readings["BATTERY_MV"],
                        "rssi": -72,
                        "snr": 9.5
                    }
                }
                topic = f"farm/{args.farm_id}/sensor/raw"
                try:
                    client.publish(topic, json.dumps(payload), qos=1)
                except Exception:
                    pass

            print(f"[{ts}] Seq={sim.seq_id:04d} | Air={readings['TEMP_AIR']:4.1f}°C RH={readings['HUMIDITY']:4.1f}% | VWC={readings['VWC']:4.1f}% EC={readings['EC']:.2f} | Bat={readings['BATTERY_MV']}mV")
            current_hour = (current_hour + 0.25) % 24.0
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopping sensor simulator.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FLIP High-Fidelity Sensor Simulator")
    parser.add_argument("--farm-id", default="fa000001-0000-0000-0000-000000000001")
    parser.add_argument("--device-id", default="node-001")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    run_simulator(args)
