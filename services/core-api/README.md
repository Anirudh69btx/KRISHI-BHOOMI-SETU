# FLIP Core API (`flip-api`)

Central backend service for the **Farm Level Intelligence Platform (FLIP / KRISHI BHOOMI SETU)**.

The Core API provides high-performance REST and GraphQL interfaces for farm geospatial mapping, IoT sensor telemetry ingestion, automated agronomic advisories, disaster alert orchestration, and AI copilot services.

---

## Architecture Overview

- **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/) with asynchronous request handlers.
- **GraphQL:** [Strawberry GraphQL](https://strawberry.rocks/) federation-ready schema.
- **Database & Persistence:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (asyncio) + [asyncpg](https://github.com/MagicStack/asyncpg) connecting to PostgreSQL / TimescaleDB with PostGIS and `pgvector`.
- **Event Messaging:** [NATS JetStream](https://nats.io/) (`nats-py`) for high-throughput distributed event streaming and notifications.
- **Durable Orchestration:** [Temporal.io](https://temporal.io/) Python SDK for resilient, long-running agronomic workflows.
- **Authentication:** Keycloak OAuth2 / OpenID Connect JWT validation.
- **Observability:** Prometheus metrics (`/metrics`), OpenTelemetry tracing, Sentry error tracking, and structured JSON logging via `structlog`.

---

## Directory Structure

```text
services/core-api/
â”œâ”€â”€ src/
â”‚   â””â”€â”€ flip_api/
â”‚       â”œâ”€â”€ auth/           # Keycloak JWT verification and RBAC
â”‚       â”œâ”€â”€ events/         # NATS JetStream publisher & subscriber clients
â”‚       â”œâ”€â”€ graphql/        # Strawberry GraphQL schema, queries, mutations
â”‚       â”œâ”€â”€ middleware/     # Request timing, logging, security middleware
â”‚       â”œâ”€â”€ models/         # SQLAlchemy ORM models (spatial, timeseries)
â”‚       â”œâ”€â”€ repositories/   # Async data access patterns
â”‚       â”œâ”€â”€ routers/        # FastAPI API route modules (farms, sensors, disaster, etc.)
â”‚       â”œâ”€â”€ workflows/      # Temporal.io workflow and activity definitions
â”‚       â”œâ”€â”€ config.py       # Pydantic Settings application configuration
â”‚       â”œâ”€â”€ database.py     # Engine, sessionmaker, and connection lifecycle
â”‚       â””â”€â”€ main.py         # FastAPI application entry point and lifespan
â”œâ”€â”€ tests/                 # Unit, integration, and e2e test suites
â”œâ”€â”€ Dockerfile             # Multi-stage container build
â””â”€â”€ pyproject.toml         # PEP 621 package metadata and Hatchling build configuration
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ (with TimescaleDB, PostGIS, and pgvector extensions)
- NATS Server with JetStream enabled (`-js`)
- Keycloak (for authenticated endpoints)

### Local Installation

From the monorepo root or package directory:

```bash
cd services/core-api
python -m pip install --upgrade pip hatchling
python -m pip install -e ".[dev]"
```

### Running the API Server

```bash
uvicorn flip_api.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- GraphQL Playground: `http://localhost:8000/graphql`
- Prometheus Metrics: `http://localhost:8000/metrics`

---

## Testing & Code Quality

```bash
# Run test suite
pytest

# Lint and format checks
ruff check .
mypy src
```
