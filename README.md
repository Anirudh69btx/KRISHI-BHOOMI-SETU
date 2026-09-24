# 🚜 Farm Lifecycle Intelligence Platform (FLIP) v3.0
**Hyper-Localized, Offline-First, Closed-Loop Agri-AI OS — Website Only (PWA)**

> **"A farm's own brain: sees, speaks, learns, warns, earns."**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Build](https://img.shields.io/badge/Build-CI%2FCD-green.svg)](.github/workflows/ci.yaml)
[![Deploy-Staging](https://img.shields.io/badge/Deploy-Staging-green)](https://staging.flip.farm)
[![Deploy-Production](https://img.shields.io/badge/Deploy-Production-red)](https://flip.farm)
[![pnpm](https://img.shields.io/badge/pnpm-9.x-orange)](https://pnpm.io)
[![Turborepo](https://img.shields.io/badge/Turborepo-Latest-FF6B6B)](https://turbo.build/repo)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_Timescale_PostGIS-4169E1?logo=postgresql)](https://timescale.com)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-K3s_RKE2-326CE5?logo=kubernetes)](https://k3s.io)

---

## 🌟 Vision
**FLIP** transforms smallholder farming in India through a **hyper-localized, offline-first, closed-loop intelligence platform**.  
It fuses **camera vision, IoT sensors, weather, crop history, and market data** into a **Farm Digital Twin** that delivers **pre-symptomatic risk warnings, evidence-backed actionable advice (NOW/NEXT/WHY/CONFIDENCE), and verifiable outcomes** — all via a **stunning 3D Visual Farm PWA** that works on a ₹5,000 phone with **zero internet**.

**Core Loop:** `Sense → Detect → Predict → Recommend → Act → Verify → Learn → Harvest → Store → Sell`

---

## 🎯 Segment 00 Status: **Foundation & Scaffolding** ✅
This repository establishes the **entire developer platform**: Monorepo, CI/CD, Local Dev Stack, Database Schema, PWA Shell, GraphQL Federation, Edge OS Builder, ML Pipeline Skeleton, and Documentation Site.

**Next:** Segment 01 — IoT Hardware Abstraction & Sensor Ingestion Pipeline.

---

## 🚀 Quick Start (Antigravity Install)

### Prerequisites (Run Once)
```bash
# 1. Install System Deps (macOS/Linux/WSL2)
# Installs direnv, pnpm, just, docker, colima, kubectl, helm, cosign, dvc, mlflow
./scripts/setup-dev-env.sh

# 2. Allow Direnv (Loads .envrc -> PATH, PYTHONPATH, VITE_* vars)
direnv allow

# 3. Bootstrap Local Dev Environment (Docker Compose + DB Migrate + Seed)
just up
# OR: ./scripts/bootstrap-local.sh
```

### What `just up` Does (60-120s)
1. **Starts docker-compose.yaml** → Supabase (Postgres+Timescale+PostGIS+pgvector), MinIO, EMQX, NATS, Keycloak, Temporal, Martin, Rasa, Grafana, Loki, Tempo, Vault, Mailhog.
2. **Applies DB Migrations** (`infra/db/migrations/*.sql`) → Schema + Timescale Hypertables + RLS + Seed Data (1 District, 2 Crops, 5 Farms).
3. **Builds Frontend** (`apps/web`) → Vite Dev Server (HMR) on `http://localhost:5173`.
4. **Starts Backend** (`services/core-api`) → FastAPI/GraphQL on `http://localhost:8000/graphql`.
5. **Starts Tile Server** (`services/tile-server`) → Martin on `http://localhost:3000`.
6. **Starts Alert Engine** (`services/alert-engine`) → Fastify on `http://localhost:3001`.
7. **Configures Keycloak Realm** (`flip`) → Clients, Roles, Mappers, Test Users (`farmer@test.com` / `password`).
8. **Seeds MinIO Buckets** (`models`, `images`, `tiles`, `firmware`, `3d-assets`) + Sample 3D Farm GLTF.
9. **Opens Browser** → `http://localhost:5173` (Farmer Dashboard) + `http://localhost:3000/tiles/...` (Map).

### Verify It Works
```bash
# 1. Open http://localhost:5173 → Login as Farmer → See 3D Farm + Advisory Card + Copilot Fab
# 2. Query GraphQL:
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __typename }"}'

# 3. Check Grafana: http://localhost:3001 (admin/admin)
# 4. Check Temporal UI: http://localhost:8233
# 5. Check MLflow: http://localhost:5000
# 6. Simulate Sensor:
just simulate-sensor
# Publishes to EMQX -> NATS -> Core API -> Twin Update -> WebSocket -> 3D Farm Updates
```

### Stop & Clean
```bash
just down          # Stops Docker Compose, Keeps Volumes (DB Data)
just clean         # docker compose down -v + pnpm store prune + clean build caches
just nuke          # Nuclear reset (clean + docker prune + venv removal)
```

---

## 🧱 Monorepo Structure

```text
flip/
├── apps/web              # 🎯 Farmer PWA (React 18, R3F, MapLibre, Voice, Copilot, Workbox PWA)
├── services/
│   ├── core-api          # 🎯 FastAPI + Strawberry GraphQL (Federation), Timescale, NATS, Temporal
│   ├── api-gateway       # Kong Declarative Config (deck.yaml) + Plugins
│   ├── alert-engine      # Fastify / Node.js (Twilio, WhatsApp, FCM, WebPush)
│   ├── tile-server       # Martin (Rust PostGIS -> MVT)
│   ├── dialogue-manager  # Rasa Open Source (IVR/Voice Dialogue Management)
│   ├── copilot-rag       # Server RAG (FastAPI + LlamaIndex + Qdrant)
│   └── model-registry    # MLflow + MinIO S3 Backend
├── packages/             # Shared: UI components, Types, i18n, WASM binaries
├── ml/                   # Training, Export, Evaluation (PyTorch Lightning, ONNX, TFLite, Conformal)
├── edge/
│   ├── gateway/          # Ubuntu Core Snaps / Balena / Python Services (ARM64)
│   ├── sensor-node/      # Zephyr RTOS (ESP32-C3, LoRaWAN, MQTT-SN)
│   └── hardware/         # Master BoM, Schematics, Enclosure STEP/STL
├── infra/
│   ├── k8s/              # GitOps (Kustomize/Helmfile/ArgoCD)
│   ├── db/               # Migrations (0001-0007), Hypertables, Seed, Supabase Config
│   ├── terraform/        # Cloud Infra (VPC, K8s, DNS, IAM)
│   ├── ansible/          # Edge Provisioning
│   ├── monitoring/       # Grafana Dashboards, Prometheus Rules, Loki, Tempo
│   └── scripts/          # Cluster bootstrap, tile downloads, cosign setup
└── docs/                 # MkDocs Material (Architecture, ADRs, API, Ops, ML)
```

---

## 🔑 Key Environment Variables (`.env.local`)

Generate a fresh set of development credentials anytime with:
```bash
just gen-secrets
```

---

## 🧪 Testing Strategy

```bash
# Frontend
just test:web          # Vitest (Unit) + Playwright (E2E)
just storybook         # Component Library

# Backend
just test:api          # Pytest (Unit + Integration)
just test:graphql      # GraphQL Snapshot Tests

# ML
just ml:eval           # Conformal Coverage, Calibration Error (ECE)

# Quality & Typing
just lint              # Biome (Organize Imports, JSX, CSS)
just format            # Biome Format
just typecheck         # Strict TypeScript + Mypy Python
```

---

## 🛡️ Security Baseline
- **mTLS Everywhere**: EMQX, NATS, Kong, Temporal, Vault, Postgres client certs.
- **Zero Trust**: Kong + Keycloak (JWT RS256, JWKS Rotation), Cilium Network Policies.
- **Secrets Management**: HashiCorp Vault (KV v2, PKI, dynamic database credentials).
- **Supply Chain**: Sigstore/cosign keyless signing for containers, models, and firmware.
- **Row-Level Security**: Strict PostgreSQL RLS for multi-tenant organization isolation.

---

## 📜 License
Apache License 2.0 — See [LICENSE](LICENSE).
