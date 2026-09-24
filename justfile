# -*- mode: makefile -*-

# ============================================================
# FLIP v3.0 — Root Justfile (Command Runner)
# Usage: `just <command>` or `just --list`
# ============================================================

# --- Config ---
set shell := ["bash", "-euo", "pipefail"]
export SHELL := "/bin/bash"
export FLIP_ROOT := invocation_directory()
export FLIP_ENV ?= "local"

# --- Variables ---
DOCKER_COMPOSE_FILE := "docker-compose.yaml"
DOCKER_COMPOSE_OVERRIDE := if path_exists("docker-compose.override.yaml") == "true" { "-f docker-compose.override.yaml" } else { "" }
DC := "docker compose -f " + DOCKER_COMPOSE_FILE + " " + DOCKER_COMPOSE_OVERRIDE
PNPM := "pnpm"
TURBO := "pnpm turbo"
JUST := "just"
KUBECTL := "kubectl"
HELM := "helm"
HELMFILE := "helmfile"
ARGOCD := "argocd"
TILT := "tilt"
COSIGN := "cosign"
DVC := "dvc"
MLFLOW := "mlflow"

# --- Colors ---
GREEN := "\\033[0;32m"
YELLOW := "\\033[1;33m"
RED := "\\033[0;31m"
NC := "\\033[0m"

# ============================================================
# 🎯 MAIN ENTRY POINTS
# ============================================================

default:
	@just --list --unsorted

# 🚀 Bootstrap Everything (Local Dev)
up: verify-env gen-secrets bootstrap-local
	@echo -e "{{GREEN}}✅ FLIP Local Stack Running!{{NC}}"
	@echo "  Frontend:  http://localhost:5173"
	@echo "  GraphQL:   http://localhost:8000/graphql"
	@echo "  Tiles:     http://localhost:3000"
	@echo "  Grafana:   http://localhost:3001 (admin/admin)"
	@echo "  Temporal:  http://localhost:8233"
	@echo "  MLflow:    http://localhost:5000"
	@echo "  Keycloak:  http://localhost:8080 (admin/admin)"
	@echo "  MinIO:     http://localhost:9001 (minioadmin/minioadmin)"
	@echo "  EMQX:      http://localhost:18083 (admin/public)"
	@echo "  Mailhog:   http://localhost:8025"

# 🛑 Stop Everything (Keep Volumes)
down:
	@echo -e "{{YELLOW}}🛑 Stopping FLIP Local Stack...{{NC}}"
	@{{DC}} down
	@echo -e "{{GREEN}}✅ Stopped. Volumes preserved.{{NC}}"

# 🧹 Clean Everything (Deep clean)
clean: down
	@echo -e "{{RED}}🧹 Cleaning All Artifacts...{{NC}}"
	@{{DC}} down -v --remove-orphans 2>/dev/null || true
	@docker system prune -f --volumes 2>/dev/null || true
	@pnpm store prune 2>/dev/null || true
	@rm -rf .turbo
	@find . -name "node_modules" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".pytest_cache" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".mypy_cache" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".ruff_cache" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name "dist" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name "build" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".coverage" -delete 2>/dev/null || true
	@find . -name "htmlcov" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo -e "{{GREEN}}✅ Clean Complete.{{NC}}"

nuke: clean
	@rm -rf .venv
	@echo -e "{{GREEN}}✅ Full nuke completed.{{NC}}"

install-tools:
	@echo -e "{{YELLOW}}🔧 Installing Dev Tools...{{NC}}"
	@bash ./scripts/setup-dev-env.sh

# ============================================================
# 🐳 DOCKER COMPOSE (Local Stack)
# ============================================================

bootstrap-local:
	@echo -e "{{YELLOW}}🐳 Bootstrapping Local Stack...{{NC}}"
	@bash ./scripts/bootstrap-local.sh

up-minimal:
	@{{DC}} --profile minimal up -d --build

up-full:
	@{{DC}} --profile full up -d --build

up-gpu:
	@{{DC}} --profile gpu up -d --build

logs:
	@{{DC}} logs -f --tail=100

logs-api:
	@{{DC}} logs -f --tail=100 core-api

logs-web:
	@{{DC}} logs -f --tail=100 web

shell-web:
	@{{DC}} exec web sh

shell-api:
	@{{DC}} exec core-api bash

shell-db:
	@{{DC}} exec postgres psql -U postgres -d flip

shell-nats:
	@{{DC}} exec nats nats --server=nats://localhost:4222

shell-temporal:
	@{{DC}} exec temporal temporal

# ============================================================
# 🗄️ DATABASE (Supabase/Postgres + Timescale + PostGIS)
# ============================================================

db-migrate:
	@echo -e "{{YELLOW}}🗄️ Running DB Migrations (0001-0011)...{{NC}}"
	@powershell -ExecutionPolicy Bypass -File ./infra/db/run_migrations.ps1 -SkipSeed

db-migrate-create name:
	@echo -e "{{YELLOW}}Use infra/db/migrations/ numbered SQL files for migrations{{NC}}"

db-seed:
	@echo -e "{{YELLOW}}🌱 Seeding Dev Data + Refreshing MATVIEW...{{NC}}"
	@powershell -ExecutionPolicy Bypass -File ./infra/db/run_migrations.ps1 -SeedOnly
	@docker exec -u postgres flip-postgres psql -d flip -c "REFRESH MATERIALIZED VIEW CONCURRENTLY farm_digital_twin;"

db-reset:
	@echo -e "{{RED}}⚠️  THIS WILL DESTROY ALL LOCAL DATA. Continue? (y/N){{NC}}" && read ans && [ "$$ans" = "y" ]
	@{{DC}} exec postgres psql -U postgres -d flip -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	@just db-migrate
	@just db-seed

db-shell:
	@{{DC}} exec postgres psql -U postgres -d flip

db-backup:
	@mkdir -p backups
	@{{DC}} exec postgres pg_dump -U postgres -Fc flip > backups/flip_$$(date +%Y%m%d_%H%M%S).dump
	@echo -e "{{GREEN}}✅ Backup saved to backups/{{NC}}"

db-restore file:
	@{{DC}} exec postgres pg_restore -U postgres -d flip --clean --if-exists "/backups/{{file}}"

# ============================================================
# 🏗️ BUILD & TEST (Turborepo)
# ============================================================

build:
	@echo -e "{{YELLOW}}🏗️ Building All Packages...{{NC}}"
	@{{TURBO}} run build

build-web:
	@{{TURBO}} run build --filter=web

build-api:
	@{{TURBO}} run build --filter=core-api

test:
	@echo -e "{{YELLOW}}🧪 Testing All Packages...{{NC}}"
	@{{TURBO}} run test

test-watch:
	@{{TURBO}} run test:watch

test-web:
	@{{TURBO}} run test --filter=web

test-api:
	@{{TURBO}} run test --filter=core-api

test-e2e:
	@{{TURBO}} run test:e2e --filter=web

lint:
	@echo -e "{{YELLOW}}🔍 Linting All Packages...{{NC}}"
	@{{TURBO}} run lint

format:
	@echo -e "{{YELLOW}}✨ Formatting All Packages...{{NC}}"
	@{{TURBO}} run format

typecheck:
	@echo -e "{{YELLOW}}🔍 Type Checking All Packages...{{NC}}"
	@{{TURBO}} run typecheck

# ============================================================
# 🤖 ML / AI PIPELINE
# ============================================================

ml-train:
	@echo -e "{{YELLOW}}🤖 Starting ML Training Pipeline (DVC)...{{NC}}"
	@cd ml && {{DVC}} repro

ml-train-gpu:
	@echo -e "{{YELLOW}}🤖 Starting GPU Training (Argo Workflow)...{{NC}}"
	@kubectl create -f ml/pipelines/train_fusion.yaml -n ml

ml-eval:
	@cd ml && python -m evaluation.metrics

ml-export:
	@cd ml && python -m models.fusion.export

ml-register:
	@cd ml && mlflow run . -P stage=Production

ml-benchmark-edge:
	@echo -e "{{YELLOW}}📊 Benchmarking on Edge Hardware (SSH)...{{NC}}"
	@cd ml && python -m evaluation.edge_bench --host flip-gateway-1.local

# ============================================================
# 📦 EDGE / IOT
# ============================================================

edge-build-gateway:
	@echo -e "{{YELLOW}}📦 Building Gateway Image (ARM64)...{{NC}}"
	@docker buildx build --platform linux/arm64 -t ghcr.io/flip/gateway:latest -f edge/gateway/Dockerfile edge/gateway --push

edge-build-sensor:
	@echo -e "{{YELLOW}}📦 Building Sensor Node Firmware (Zephyr)...{{NC}}"
	@docker buildx build --platform linux/amd64 -t ghcr.io/flip/zephyr-builder:latest -f edge/sensor-node/Dockerfile.build edge/sensor-node
	@docker run --rm -v {{FLIP_ROOT}}/edge/sensor-node:/src ghcr.io/flip/zephyr-builder:latest west build -b esp32c3_devkitm /src/zephyr/app

edge-provision:
	@echo -e "{{YELLOW}}📦 Provisioning Edge Gateway (Ansible)...{{NC}}"
	@cd infra/ansible && ansible-playbook -i inventory/edge playbooks/provision.yml --ask-vault-pass

edge-ota-sign artifact:
	@{{COSIGN}} sign --yes {{artifact}}

edge-ota-verify artifact:
	@{{COSIGN}} verify --certificate-oidc-issuer https://token.actions.githubusercontent.com --certificate-identity-regexp ".*" {{artifact}}

# ============================================================
# 🚀 DEPLOYMENT (GitOps / ArgoCD)
# ============================================================

deploy-staging:
	@echo -e "{{YELLOW}}🚀 Deploying to Staging (ArgoCD)...{{NC}}"
	@argocd app sync flip-staging --prune --auto-prune

deploy-prod:
	@echo -e "{{RED}}🚀 Deploying to PRODUCTION (ArgoCD)...{{NC}}"
	@read -p "Type 'PROD' to confirm: " confirm && [ "$$confirm" = "PROD" ]
	@argocd app sync flip-production --prune --auto-prune

deploy-edge:
	@echo -e "{{YELLOW}}🚀 Deploying to Edge Fleet (ArgoCD App of Apps)...{{NC}}"
	@argocd app sync flip-edge-fleet --prune --auto-prune

# ============================================================
# 📚 DOCUMENTATION
# ============================================================

docs-serve:
	@cd docs && pip install -r requirements.txt && mkdocs serve --dev-addr=0.0.0.0:8001

docs-build:
	@cd docs && mkdocs build --strict --site-dir ../site

docs-deploy:
	@cd docs && mkdocs gh-deploy --force

# ============================================================
# 🔐 SECURITY / SECRETS
# ============================================================

gen-secrets:
	@echo -e "{{YELLOW}}🔐 Generating Local Secrets (.env.local)...{{NC}}"
	@bash ./scripts/generate-secrets.sh

vault-unseal:
	@echo -e "{{YELLOW}}🔓 Unsealing Vault...{{NC}}"
	@kubectl exec -n vault vault-0 -- vault operator unseal $$(cat .vault-keys/key1.txt)
	@kubectl exec -n vault vault-0 -- vault operator unseal $$(cat .vault-keys/key2.txt)
	@kubectl exec -n vault vault-0 -- vault operator unseal $$(cat .vault-keys/key3.txt)

# ============================================================
# 🛠️ UTILITIES
# ============================================================

verify-env:
	@echo -e "{{YELLOW}}🔍 Verifying Environment...{{NC}}"
	@bash ./scripts/verify-env.sh

graphql-generate:
	@echo -e "{{YELLOW}}📝 Generating GraphQL Types (Client + Server)...{{NC}}"
	@cd packages/graphql-types && pnpm codegen

i18n-extract:
	@echo -e "{{YELLOW}}🌐 Extracting i18n Keys...{{NC}}"
	@cd apps/web && pnpm i18n:extract

tiles-download:
	@echo -e "{{YELLOW}}🗺️ Downloading Map Tiles (MBTiles)...{{NC}}"
	@bash ./scripts/download-tiles.sh

wasm-download:
	@echo -e "{{YELLOW}}📦 Downloading Voice & Copilot WASM binaries...{{NC}}"
	@bash ./scripts/download-wasm.sh

simulate-sensor:
	@echo -e "{{YELLOW}}📡 Simulating Sensor Data (MQTT -> NATS -> Twin -> WebSocket)...{{NC}}"
	@python scripts/simulate_sensor.py --farm-id dev-farm-1 --interval 5

# ============================================================
# 🎯 SEGMENT TARGETS
# ============================================================

segment-00: up
	@echo -e "{{GREEN}}✅ Segment 00 Complete: Foundation Scaffolding Ready.{{NC}}"

segment-01:
	@echo "🎯 Segment 01: Implement Sensor Ingestion (EMQX -> NATS -> Core API -> Timescale), Device Registry, Twin Event Sourcing."
