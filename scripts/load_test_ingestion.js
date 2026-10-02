/**
 * FLIP k6 Load Test — Ingestion Pipeline
 * =======================================
 * Target: 20,000 msg/sec, P99 latency < 50ms, 0% errors
 *
 * Usage:
 *   k6 run scripts/load_test_ingestion.js --vus 100 --duration 5m
 *   k6 run scripts/load_test_ingestion.js --vus 200 --duration 2m --env API_URL=http://core-api:8000
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Histogram, Rate } from "k6/metrics";
import { uuidv4 } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

// ── Custom metrics ──────────────────────────────────────────────────────────
const insertedCounter = new Counter("flip_readings_inserted");
const rejectedCounter = new Counter("flip_readings_rejected");
const latencyHist     = new Histogram("flip_ingestion_latency_ms");
const errorRate       = new Rate("flip_error_rate");

// ── Config ──────────────────────────────────────────────────────────────────
const API_URL   = __ENV.API_URL   || "http://localhost:8000";
const FARM_ID   = __ENV.FARM_ID   || "00000000-0000-0000-0000-000000000001";
const DEVICE_ID = __ENV.DEVICE_ID || "00000000-0000-0000-0000-000000000002";
const ST_ID     = __ENV.ST_ID     || "00000000-0000-0000-0000-000000000003";
const BATCH_SZ  = parseInt(__ENV.BATCH_SIZE || "50");

export const options = {
  scenarios: {
    // Ramp up to 200 VUs, sustain, then ramp down
    ramp_and_sustain: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 50  },   // warm up
        { duration: "30s", target: 200 },   // ramp to peak
        { duration: "4m",  target: 200 },   // sustain peak load
        { duration: "30s", target: 0   },   // ramp down
      ],
    },
  },
  thresholds: {
    http_req_duration:         ["p(99)<50"],      // P99 < 50ms SLA
    http_req_failed:           ["rate<0.001"],    // < 0.1% HTTP errors
    flip_error_rate:           ["rate<0.001"],
    flip_ingestion_latency_ms: ["p(99)<50"],
  },
};

// ── Reading factory ──────────────────────────────────────────────────────────
function makeReadings(count) {
  const now = new Date().toISOString();
  const readings = [];
  const sensors = [
    { code: "VWC",       min: 10,  max: 80  },
    { code: "TEMP_AIR",  min: 15,  max: 45  },
    { code: "RH",        min: 30,  max: 95  },
    { code: "TEMP_SOIL", min: 18,  max: 40  },
    { code: "PAR",       min: 0,   max: 2000},
  ];
  for (let i = 0; i < count; i++) {
    const sensor = sensors[i % sensors.length];
    readings.push({
      farm_id:        FARM_ID,
      device_id:      DEVICE_ID,
      sensor_type_id: ST_ID,
      time:           now,
      value:          sensor.min + Math.random() * (sensor.max - sensor.min),
      quality_flag:   "RAW",
      sensor_code:    sensor.code,
      metadata: {
        battery_mv: Math.floor(3200 + Math.random() * 600),
        rssi:       Math.floor(-110 + Math.random() * 50),
        firmware:   "3.0.0",
      },
    });
  }
  return readings;
}

// ── Main test function ───────────────────────────────────────────────────────
export default function () {
  const readings  = makeReadings(BATCH_SZ);
  const batchId   = uuidv4();
  const payload   = JSON.stringify({ readings, batch_id: batchId });

  const headers = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${__ENV.SERVICE_TOKEN || "test-token"}`,
  };

  const t0       = Date.now();
  const response = http.post(
    `${API_URL}/api/v1/telemetry/bulk`,
    payload,
    { headers, timeout: "5s" }
  );
  const elapsed  = Date.now() - t0;

  latencyHist.add(elapsed);

  const ok = check(response, {
    "status 200":           (r) => r.status === 200,
    "latency < 50ms":       (_) => elapsed < 50,
    "has inserted field":   (r) => r.json("inserted") !== undefined,
    "no server error":      (r) => r.status !== 500,
  });

  if (!ok || response.status !== 200) {
    errorRate.add(1);
  } else {
    const body = response.json();
    insertedCounter.add(body.inserted || 0);
    rejectedCounter.add(body.rejected || 0);
  }

  // No sleep — maximize throughput
  sleep(0.001);
}

// ── Summary handler ──────────────────────────────────────────────────────────
export function handleSummary(data) {
  const throughput = data.metrics.iterations?.values?.rate || 0;
  const p99        = data.metrics.http_req_duration?.values?.["p(99)"] || 0;
  const errorPct   = (data.metrics.http_req_failed?.values?.rate || 0) * 100;

  console.log("\n═══════════════════════════════════════════");
  console.log("  FLIP Ingestion Load Test — Summary");
  console.log("═══════════════════════════════════════════");
  console.log(`  Iterations/sec : ${throughput.toFixed(0)}`);
  console.log(`  Msg/sec        : ${(throughput * BATCH_SZ).toFixed(0)} (batch=${BATCH_SZ})`);
  console.log(`  P99 latency    : ${p99.toFixed(2)}ms  (target: <50ms)`);
  console.log(`  Error rate     : ${errorPct.toFixed(3)}%  (target: <0.1%)`);
  console.log(`  Target 20k/s   : ${throughput * BATCH_SZ >= 20000 ? "✅ PASS" : "❌ FAIL"}`);
  console.log(`  P99 SLA        : ${p99 < 50 ? "✅ PASS" : "❌ FAIL"}`);
  console.log(`  Error SLA      : ${errorPct < 0.1 ? "✅ PASS" : "❌ FAIL"}`);
  console.log("═══════════════════════════════════════════\n");

  return {
    "scripts/load_test_results.json": JSON.stringify(data, null, 2),
  };
}
