#!/usr/bin/env bash
set -euo pipefail
log() { echo -e "\033[0;32m[SECRETS]\033[0m $*"; }

ENV_FILE=".env.local"
if [[ -f "$ENV_FILE" ]]; then
    read -r -p "$ENV_FILE already exists. Overwrite? (y/N) " ans
    [[ "$ans" == "y" || "$ans" == "Y" ]] || { log "Aborted."; exit 0; }
fi

POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
MINIO_ROOT_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
KEYCLOAK_ADMIN_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
VAULT_ROOT_TOKEN=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
JWT_SECRET=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-64)
ENCRYPTION_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)

cat > "$ENV_FILE" <<EOF
# FLIP v3.0 — Local Dev Secrets (GITIGNORED)
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

FLIP_ENV=local
FLIP_DOMAIN=localhost
FLIP_API_URL=http://localhost:8000
FLIP_WS_URL=ws://localhost:8000/ws
FLIP_WEB_URL=http://localhost:5173
FLIP_TILE_URL=http://localhost:3000

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=flip
POSTGRES_USER=postgres
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
DATABASE_URL=postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@localhost:5432/flip
DATABASE_URL_SYNC=postgresql://postgres:${POSTGRES_PASSWORD}@localhost:5432/flip

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=${MINIO_ROOT_PASSWORD}
MINIO_BUCKET_MODELS=flip-models
MINIO_BUCKET_IMAGES=flip-images
MINIO_BUCKET_TILES=flip-tiles
MINIO_BUCKET_FIRMWARE=flip-firmware
MINIO_BUCKET_ASSETS=flip-assets

NATS_URL=nats://localhost:4222
NATS_JETSTREAM_DOMAIN=flip

EMQX_HOST=localhost
EMQX_PORT=1883
EMQX_MQTTS_PORT=8883
EMQX_DASHBOARD_PORT=18083

KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=flip
KEYCLOAK_CLIENT_ID=flip-web
KEYCLOAK_CLIENT_SECRET=dev-secret
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD}

TEMPORAL_ADDRESS=localhost:7233
TEMPORAL_NAMESPACE=flip

MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_S3_ENDPOINT_URL=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=${MINIO_ROOT_PASSWORD}
MLFLOW_ARTIFACT_ROOT=s3://flip-models/mlflow

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
PROMETHEUS_URL=http://localhost:9090
LOKI_URL=http://localhost:3100
TEMPO_URL=http://localhost:3200

IMD_API_KEY=dev_mock
OPEN_METEO_URL=https://api.open-meteo.com
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+15551234567
WHATSAPP_TOKEN=dev_token
WHATSAPP_PHONE_NUMBER_ID=123456789
FCM_SERVER_KEY=dev_key
VAPID_PUBLIC_KEY=placeholder_run_npx_web-push_generate-vapid-keys
VAPID_PRIVATE_KEY=placeholder_run_npx_web-push_generate-vapid-keys
SENTRY_DSN=

JWT_SECRET=${JWT_SECRET}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=${VAULT_ROOT_TOKEN}

ENABLE_WASM_VOICE=true
ENABLE_WASM_COPILOT=true
ENABLE_3D_FARM=true
ENABLE_DISASTER_SIREN=true

VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
VITE_TILE_URL=http://localhost:3000
VITE_KEYCLOAK_URL=http://localhost:8080
VITE_KEYCLOAK_REALM=flip
VITE_KEYCLOAK_CLIENT_ID=flip-web
VITE_ENABLE_WASM_VOICE=true
VITE_ENABLE_WASM_COPILOT=true
VITE_ENABLE_3D_FARM=true
VITE_ENABLE_DISASTER_SIREN=true
EOF

chmod 600 "$ENV_FILE"
log "✅ $ENV_FILE generated."
log "Run: direnv allow  (to load env vars automatically)"
