#!/usr/bin/env bash
# ==============================================================================
# FLIP v3.0 — Automated Keycloak GitOps Provisioning Script (Segment 01)
# Uses kcadm.sh to idempotently configure Keycloak realm, clients, roles, flows,
# and WebAuthn MFA policies without manual UI intervention.
# ==============================================================================

set -euo pipefail

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
KEYCLOAK_ADMIN_USER="${KEYCLOAK_ADMIN_USER:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
REALM_FILE="${REALM_FILE:-infra/keycloak/realm-export.json}"

echo "🌾 [FLIP Keycloak GitOps] Authenticating with Keycloak at ${KEYCLOAK_URL}..."

# Wait for Keycloak health
MAX_RETRIES=30
RETRY_COUNT=0
until curl -s -f "${KEYCLOAK_URL}/health/ready" > /dev/null 2>&1 || [ $RETRY_COUNT -eq $MAX_RETRIES ]; do
  echo "Waiting for Keycloak to be ready... ($((RETRY_COUNT+1))/$MAX_RETRIES)"
  sleep 3
  RETRY_COUNT=$((RETRY_COUNT+1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "❌ Keycloak did not become ready in time."
  exit 1
fi

# Acquire Admin CLI Token
echo "🔑 Logging in via kcadm.sh..."
docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user "${KEYCLOAK_ADMIN_USER}" \
  --password "${KEYCLOAK_ADMIN_PASSWORD}"

# Copy realm export file into container
docker cp "${REALM_FILE}" "$(docker compose ps -q keycloak):/tmp/realm-export.json"

# Check if 'flip' realm exists
if docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh get realms/flip > /dev/null 2>&1; then
  echo "🔄 Updating existing 'flip' realm configuration from ${REALM_FILE}..."
  docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh update realms/flip -f /tmp/realm-export.json
else
  echo "✨ Creating new 'flip' realm from ${REALM_FILE}..."
  docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh create realms -f /tmp/realm-export.json
fi

echo "✅ [FLIP Keycloak GitOps] Realm 'flip' provisioned successfully with 0 manual clicks!"
