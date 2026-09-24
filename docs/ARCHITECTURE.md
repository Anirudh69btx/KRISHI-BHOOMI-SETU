# FLIP v3.0 — Architecture Decision Records

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](adr/001-single-supabase-postgres-cluster.md) | Single Supabase/Postgres Cluster | Accepted | 2025-01-15 |
| [ADR-002](adr/002-edge-gateway-mandatory.md) | Edge Gateway Mandatory | Accepted | 2025-01-15 |
| [ADR-003](adr/003-nats-jetstream-messaging.md) | NATS JetStream as Primary Messaging Bus | Accepted | 2025-01-20 |
| [ADR-004](adr/004-pwa-offline-first.md) | PWA Offline-First Architecture | Accepted | 2025-01-20 |
| [ADR-005](adr/005-strawberry-graphql-federation.md) | Strawberry GraphQL Federation | Accepted | 2025-01-25 |
| [ADR-006](adr/006-keycloak-oidc-pkce.md) | Keycloak OIDC + PKCE for All Clients | Accepted | 2025-01-25 |
| [ADR-007](adr/007-timescaledb-sensor-storage.md) | TimescaleDB for Sensor Time-Series | Accepted | 2025-02-01 |
| [ADR-008](adr/008-postgis-spatial-queries.md) | PostGIS for All Spatial Queries | Accepted | 2025-02-01 |
| [ADR-009](adr/009-pgvector-rag-embeddings.md) | pgvector for RAG Embeddings | Accepted | 2025-02-05 |
| [ADR-010](adr/010-minio-object-storage.md) | MinIO S3-Compatible Object Storage | Accepted | 2025-02-05 |
| [ADR-011](adr/011-temporal-workflow-orchestration.md) | Temporal for Workflow Orchestration | Accepted | 2025-02-10 |
| [ADR-012](adr/012-mlflow-model-registry.md) | MLflow for Model Registry | Accepted | 2025-02-10 |
| [ADR-013](adr/013-3d-terrain-deckgl.md) | deck.gl + MapLibre for 3D Terrain | Accepted | 2025-02-15 |
| [ADR-014](adr/014-10-indian-language-support.md) | 10 Indian Languages + Whisper Voice | Accepted | 2025-02-15 |
| [ADR-015](adr/015-zephyr-rtos-sensor-node.md) | Zephyr RTOS for Sensor Nodes | Accepted | 2025-02-20 |

---

## Quick Reference

```
FLIP v3.0 Architecture
═══════════════════════════════════════════════════════════════════
  Browser (PWA)          Edge Node            Cloud Services
  ─────────────          ─────────            ──────────────
  React + Vite           Raspberry Pi 4       Postgres (Timescale
  MapLibre GL            gateway.py           +PostGIS+pgvector)
  deck.gl 3D             mTLS MQTT client     ──────────────
  Workbox SW             NATS bridge          NATS JetStream
  Whisper WASM           ──────────           EMQX MQTT Broker
  i18next (10 langs)     Zephyr RTOS node     ──────────────
  Zustand store          sensors: DHT22,      Kong API Gateway
  oidc-client-ts         NPK, pH, camera      Keycloak OIDC
                                              ──────────────
                                              FastAPI Core API
                                              GraphQL (Strawberry)
                                              Temporal Workflows
                                              ──────────────
                                              MLflow Registry
                                              MinIO Object Store
                                              Martin Tile Server
                                              Rasa Dialogue Mgr
                                              ──────────────
                                              Prometheus+Grafana
                                              Loki+Tempo (OTEL)
═══════════════════════════════════════════════════════════════════
```

## Key Data Flows

### Sensor → Cloud (ADR-002, ADR-003)
```
Sensor Node (Zephyr) → MQTT over mTLS → EMQX Broker
  → NATS JetStream (farm.<id>.sensor.raw)
  → Core API consumer → TimescaleDB
  → ML Inference → NATS (farm.<id>.sensor.processed)
  → WebSocket → Browser
```

### Advisory Generation (Closed-Loop)
```
TimescaleDB sensor data
  → Temporal Workflow → ML Fusion Model
  → Advisory generated → Postgres
  → Push notification → Farmer
  → Farmer acknowledges + logs action
  → Training sample recorded → MLflow
  → Next model iteration improved
```

### Offline Operation (ADR-004)
```
Browser loses connectivity
  → Workbox SW serves cached app shell
  → IndexedDB + Zustand persist store
  → Manual entries queued in pendingActions
  → Background Sync API drains on reconnect
  → CRDT merge resolves conflicts server-side
```

### Identity & Access Management Flow (Segment 01 / ADR-006, ADR-015)
```
Farmer "Login with OTP":
  Farmer PWA → Keycloak custom 'otp-sms-provider' SPI
    → Twilio Verify API (or dev mock) sends 6-digit SMS OTP
    → Farmer submits OTP to Keycloak
    → Keycloak verifies code & returns authorization_code (PKCE)
    → PWA exchanges code with Keycloak for access_token + refresh_token
    → PWA triggers POST /api/v1/auth/sync-profile (Bearer access_token)
    → Core API validates JWT via Keycloak JWKS cache
    → Core API upserts PostgreSQL 'profiles' (keycloak_sub, role, phone)
    → Core API returns profile + bound farms
    → PWA renders dashboard with role badge & farm digital twin

Expert "Password + MFA":
  Agronomist/Admin → Keycloak hosted login page
    → Password + WebAuthn/TOTP challenge
    → PKCE token exchange → Profile synced with role=agronomist
    → Route guards permit access to /expert and advisory queue
```
