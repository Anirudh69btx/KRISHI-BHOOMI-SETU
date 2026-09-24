# FLIP v3.0 — Key Architectural Decisions Log

## 2026-09-10: Gateway Hardware Selection
- **Decision**: Raspberry Pi Zero 2W over RK3588 SOM
- **Reasoning**: 
  - **Cost**: ₹1,800 vs ₹5,000 (2.7x cheaper).
  - **Inference**: Sufficient for TFLite INT8 inference ($<200\text{ ms}$).
  - **Power Consumption**: Lower power (0.8W idle vs 5W) — critical for solar battery longevity in off-grid deployments.
  - **OS Ecosystem**: Native Ubuntu Core support, mature Linux ARM64 driver ecosystem.
- **Trade-off**: No YOLOv8 on device — pest detection via cloud fallback or trap camera images uploaded for cloud analysis.

---

## 2026-09-10: Satellite Imagery Strategy
- **Decision**: Sentinel-2 (Free, 10m resolution, 5-day revisit) via STAC API
- **Reasoning**:
  - Zero licensing cost, global agricultural coverage, open science data.
  - Sufficient resolution for field-level NDVI (Normalized Difference Vegetation Index), NDWI (Moisture Index), and canopy health tracking.
  - Standard STAC API (Planetary Computer / AWS Open Data) enables programmatic cloud ingestion.
- **Future Roadmap**: Integrate PlanetScope (3m, daily) for high-value export horticulture; on-demand drone orthomosaics for centimeter-level plot diagnostics.

---

## 2026-09-10: Retraining Trigger Thresholds
- **Decision**: Hybrid trigger — `min_samples >= 200` AND (`drift_detected` OR `days_since_last_train >= 30`)
- **Reasoning**:
  - Prevents over-retraining on transient noise.
  - Drift detection: Kolmogorov-Smirnov test $p < 0.01$ on input feature embeddings (evaluated per crop and disease class).
  - Monthly cadence ensures regular adaptation to seasonal micro-climates.
- **Implementation**: Temporal.io scheduled workflow checks metrics daily; Kubeflow pipeline triggered when condition is satisfied.

---

## 2026-09-10: APMC Mandi Price Source
- **Decision**: AGMARKNET Official API (Ministry of Agriculture & Farmers Welfare, GoI)
- **Reasoning**:
  - Legally authoritative, free, structured open data.
  - Covers all major APMC mandis, commodities, varieties, and daily modal prices.
  - Rate limits: 1,000 requests/day (sufficient for district-level aggregation).
- **Fallback**: Manual CSV batch upload interface for small rural rural *haats* not yet indexed on AGMARKNET.

---

## 2026-09-10: WhatsApp Business API
- **Decision**: Use WhatsApp for notifications and advisory alerts ONLY (not primary authentication channel)
- **Reasoning**:
  - Meta template approvals take 2–4 weeks — pre-registered 20 standard templates (advisory alert, disaster warning, verification prompt, mandi price alert, harvest notification).
  - Cost: ~₹0.50 per conversation — sustainable budget for 10,000 farmers ($\approx \text{₹}5,000/\text{month}$).
  - Avoids single-point vendor lock-in for authentication.
- **Backup**: SMS OTP via Twilio and IVR voice broadcasts remain authoritative and always active.

---

## 2026-09-10: Post-Quantum Cryptography (PQC)
- **Decision**: Document in ADR-017; adopt Hybrid X25519 + ML-KEM for future TLS certificates
- **Reasoning**:
  - NIST finalized Post-Quantum Cryptography standards in 2024 (FIPS 203 ML-KEM / Kyber, FIPS 204 ML-DSA / Dilithium).
  - Migration timeline: 5–10 years horizon.
  - No immediate code-level breaking changes required; roadmap established for long-term cryptographic agility.

---

## 2026-09-10: Multi-Region Disaster Recovery (DR)
- **Decision**: Active-Passive architecture (Primary: Mumbai `ap-south-1`, Secondary DR: Hyderabad `ap-south-2`)
- **RTO / RPO Targets**: **RTO** $< 1\text{ hour}$ | **RPO** $< 5\text{ minutes}$
- **Implementation**:
  - TimescaleDB / PostgreSQL native streaming replication (primary $\rightarrow$ standby replica).
  - MinIO Cross-Region Bucket Replication (S3 CRR).
  - ArgoCD app-of-apps synchronization maintaining mirror state on DR cluster.
  - Automated DNS health checks and failover routing via Route 53 / Cloudflare.

---

## 2026-09-10: Training Materials & Farmer Education
- **Decision**: 5-minute video guides + audio explainers in 10 languages accessible via PWA
- **Production Strategy**: Partner with local Krishi Vigyan Kendra (KVK) extension officers for dialect, contextual, and agronomic authenticity.
- **Budget**: $\approx \text{₹}2,00,000$ across 10 languages $\times$ 4 core modules (sensor care, camera capture, spray verification, disaster safety).
- **Delivery**: Embedded in PWA `/help` module with offline pre-caching capability (compressed WebM / MP3).

---

## 2026-09-10: Performance Baselines & Load Testing
- **Decision**: Automated k6 and Locust load test suites mandated as CI/CD quality gates before Segment 17 sign-off
- **Targets**:
  - 20,000 messages/sec ingestion capacity (10,000 farms $\times$ 3 nodes $\times$ 15s interval).
  - 10,000 concurrent active WebSocket connections.
  - $<200\text{ ms}$ p99 GraphQL advisory query latency under full load.
  - $<30\text{ s}$ end-to-end disaster alert broadcast (EMERGENCY classification).

---

## 2026-09-10: Cost Model Target
- **Decision**: Maintain total cost at $< \text{₹}500/\text{farm}/\text{year}$ (cloud infrastructure + edge hardware + telecommunications + SaaS)
- **Annual Cost Breakdown Target**:
  - **Cloud Infrastructure** (K8s, DB, GPU inference): ₹200
  - **Edge Hardware** (Pi Zero 2W Gateway + 2 ESP32 nodes amortized over 3 years): ₹150
  - **Telecommunications** (4G SIM + LoRa spectrum): ₹100
  - **SaaS & External APIs** (Twilio SMS, WhatsApp, weather data): ₹50
