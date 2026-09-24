#!/usr/bin/env bash
# Usage: source scripts/activate-venv.sh [service]
# Services: dev, core-api, copilot-rag, dialogue-manager/actions, tile-server, api-gateway, ml, edge/gateway, scripts

SERVICE=${1:-dev}
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case $SERVICE in
    dev) VENV_DIR=".venv-dev" ;;
    ml) VENV_DIR="ml/.venv" ;;
    edge/gateway) VENV_DIR="edge/gateway/.venv" ;;
    scripts) VENV_DIR="scripts/.venv" ;;
    *) VENV_DIR="services/$SERVICE/.venv" ;;
esac

ACTIVATE_PATH=""
if [ -f "$ROOT_DIR/$VENV_DIR/bin/activate" ]; then
    ACTIVATE_PATH="$ROOT_DIR/$VENV_DIR/bin/activate"
elif [ -f "$ROOT_DIR/$VENV_DIR/Scripts/activate" ]; then
    ACTIVATE_PATH="$ROOT_DIR/$VENV_DIR/Scripts/activate"
fi

if [ -z "$ACTIVATE_PATH" ]; then
    echo "❌ Venv not found: $VENV_DIR. Run setup-venv.sh first."
    return 1 2>/dev/null || exit 1
fi

source "$ACTIVATE_PATH"
echo "✅ Activated $SERVICE venv ($VENV_DIR)"
