#!/usr/bin/env bash
# ============================================================
# FLIP v3.0 — Bootstrap Local Dev Stack
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log() { echo -e "${GREEN}[BOOTSTRAP]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }

log "Starting FLIP local dev bootstrap..."

# 1. Generate secrets if missing
if [[ ! -f .env.local ]]; then
    log "Generating .env.local secrets..."
    bash ./scripts/generate-secrets.sh
fi

# 2. Start infrastructure (minimal profile)
log "Starting Docker Compose (profile: minimal)..."
docker compose -f docker-compose.yaml --profile minimal up -d --build

# 3. Wait for Postgres
log "Waiting for Postgres to be healthy..."
for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U postgres -d flip >/dev/null 2>&1; then
        log "Postgres is ready."
        break
    fi
    echo -n "."
    sleep 2
done

# 4. Run migrations in order
log "Applying DB migrations..."
for migration in infra/db/migrations/0001_*.sql \
                 infra/db/migrations/0002_*.sql \
                 infra/db/migrations/0003_*.sql \
                 infra/db/migrations/0004_*.sql \
                 infra/db/migrations/0005_*.sql \
                 infra/db/migrations/0006_*.sql \
                 infra/db/migrations/0007_*.sql; do
    if [[ -f "$migration" ]]; then
        log "Running: $migration"
        docker compose exec -T postgres psql -U postgres -d flip -f "/docker-entrypoint-initdb.d/$(basename $migration)" 2>/dev/null || \
        docker compose exec -T postgres psql -U postgres -d flip < "$migration"
    fi
done

# 5. Seed dev data
log "Seeding development data..."
docker compose exec -T postgres psql -U postgres -d flip < infra/db/migrations/seed_dev.sql 2>/dev/null || \
    warn "Seed already applied or error (idempotent — safe to ignore)."

# 6. Wait for Keycloak
log "Waiting for Keycloak to be healthy..."
for i in {1..40}; do
    if curl -sf http://localhost:8080/health/ready >/dev/null 2>&1; then
        log "Keycloak is ready."
        break
    fi
    echo -n "."
    sleep 3
done

log "✅ Bootstrap complete!"
log "  Frontend:     http://localhost:5173"
log "  API / GraphQL: http://localhost:8000/graphql (via Kong)"
log "  Keycloak:     http://localhost:8080 (admin/admin)"
log "  MinIO:        http://localhost:9001 (minioadmin/minioadmin)"
