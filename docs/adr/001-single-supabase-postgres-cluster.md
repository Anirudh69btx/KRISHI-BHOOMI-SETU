# ADR-001: Single Supabase/Postgres Cluster

- **Status**: Accepted
- **Date**: 2025-01-15
- **Deciders**: Platform Team

## Context

FLIP needs a database that can handle:
1. Relational data (farms, farmers, advisories)
2. Time-series (sensor readings at 10Hz per node)
3. Geospatial (farm boundaries, shelter locations, disaster zones)
4. Vector similarity (RAG embeddings for Copilot)
5. Scheduled jobs (cron-based advisory generation)
6. Row-Level Security for multi-tenant isolation

## Decision

Use a **single Postgres 16 cluster** with the following extensions:
- **TimescaleDB** — hypertables for `sensor_readings`, `twin_events`, `training_samples`
- **PostGIS** — geometry/geography columns for farm boundaries, shelters, disaster zones
- **pgvector** — `vector(1536)` columns for Copilot RAG embeddings
- **pg_cron** — scheduled advisory generation, data retention, twin refresh
- **Row-Level Security (RLS)** — farmer-owned data isolated by `farmer_id`

Self-hosted via **Supabase Community Edition** in production (same API, local control).

## Consequences

**Positive:**
- Single connection string, single backup target
- Supabase RLS + JWT auth natively supported
- TimescaleDB compression reduces sensor storage 20x
- PostGIS enables sub-millisecond geofencing queries
- pgvector enables ANN search without separate vector DB

**Negative:**
- Extension upgrades require careful coordination
- TimescaleDB and PostGIS have separate version matrices
- Single point of failure (mitigated by streaming replication in prod)

## Alternatives Considered

- ClickHouse for time-series (rejected: no PostGIS, separate ops)
- Pinecone for vectors (rejected: data residency, cost)
- MongoDB (rejected: no TimescaleDB, poor SQL compatibility)
