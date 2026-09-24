#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Detect Python 3.11 executable
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null && python3 --version 2>&1 | grep -q "3\.11"; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null && python --version 2>&1 | grep -q "3\.11"; then
    PYTHON_CMD="python"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python 3.11 not found. Install Python 3.11.9"
    exit 1
fi

echo "🐍 Setting up Python 3.11 virtual environments using: $($PYTHON_CMD --version)..."

setup_venv() {
    local service_dir=$1
    local req_file=$2
    local venv_name=$3
    
    echo "📦 Setting up $venv_name ($service_dir)..."
    cd "$ROOT_DIR/$service_dir"
    
    if [ ! -d ".venv" ]; then
        "$PYTHON_CMD" -m venv .venv
    fi
    
    # Cross-platform activate path (Scripts for Windows, bin for POSIX)
    if [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate
    elif [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    else
        echo "❌ Cannot find activate script in $service_dir/.venv"
        exit 1
    fi

    pip install --upgrade pip setuptools wheel
    pip install -r "$req_file"
    deactivate
    echo "✅ $venv_name ready"
}

# Core services
setup_venv "services/core-api" "requirements.txt" "Core API"
setup_venv "services/copilot-rag" "requirements.txt" "Copilot RAG"
setup_venv "services/dialogue-manager/actions" "requirements.txt" "Rasa Actions"
setup_venv "services/tile-server" "requirements.txt" "Tile Server"
setup_venv "services/api-gateway" "requirements.txt" "API Gateway"

# ML (Training + Export separate)
setup_venv "ml" "requirements-train.txt" "ML Training"
# Note: requirements-export.txt used in CI only

# Edge
setup_venv "edge/gateway" "requirements.txt" "Gateway Edge"

# Scripts
setup_venv "scripts" "requirements.txt" "Utility Scripts"

# Root dev environment
echo "📦 Setting up root dev environment..."
cd "$ROOT_DIR"
if [ ! -d ".venv-dev" ]; then
    "$PYTHON_CMD" -m venv .venv-dev
fi

if [ -f ".venv-dev/Scripts/activate" ]; then
    source .venv-dev/Scripts/activate
elif [ -f ".venv-dev/bin/activate" ]; then
    source .venv-dev/bin/activate
else
    echo "❌ Cannot find activate script in .venv-dev"
    exit 1
fi

pip install --upgrade pip setuptools wheel
pip install -r requirements-dev.txt
deactivate

echo "🎉 All virtual environments ready!"
echo "Activate: source scripts/activate-venv.sh [service]"
