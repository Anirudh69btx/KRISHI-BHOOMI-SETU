#!/usr/bin/env bash
# FLIP Gateway Field Commissioning Script
set -e

FARM_ID="${1}"
GATEWAY_ID="${2:-gw-001}"

if [ -z "$FARM_ID" ]; then
    echo "Usage: ./commission.sh <farm_uuid> [gateway_id]"
    exit 1
fi

echo "=== Commissioning FLIP Gateway ==="
echo "Farm UUID:   $FARM_ID"
echo "Gateway ID:  $GATEWAY_ID"

CONFIG_FILE="/etc/flip/gateway.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="../config/gateway.yaml"
fi

sed -i "s/farm_id:.*/farm_id: \"$FARM_ID\"/" "$CONFIG_FILE"
sed -i "s/gateway_id:.*/gateway_id: \"$GATEWAY_ID\"/" "$CONFIG_FILE"

# Initialize SQLite database
sqlite3 /data/gateway.db < ../storage/schema.sql

echo "✅ Gateway commissioned for farm $FARM_ID"
if command -v systemctl &> /dev/null; then
    sudo systemctl restart flip-gateway.service || true
fi
