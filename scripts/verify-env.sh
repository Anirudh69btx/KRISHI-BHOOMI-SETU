#!/usr/bin/env bash
set -euo pipefail
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log() { echo -e "${GREEN}[VERIFY]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err() { echo -e "${RED}[FAIL]${NC} $*" >&2; FAILURES=$((FAILURES+1)); }
FAILURES=0

check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        err "$1 not found in PATH"
    else
        local ver
        ver=$($1 --version 2>&1 | head -1)
        log "$1: $ver"
    fi
}

check_cmd git
check_cmd docker
check_cmd pnpm
check_cmd just
check_cmd python3
check_cmd node

# Check Docker daemon
if ! docker info >/dev/null 2>&1; then
    err "Docker daemon not running. Start Docker Desktop or Colima."
else
    log "Docker daemon: running"
fi

# Check .env.local
if [[ ! -f ".env.local" ]]; then
    warn ".env.local not found. Run: just gen-secrets"
else
    log ".env.local: present"
fi

# Check common port conflicts
PORTS=(5432 6432 9000 9001 4222 8222 1883 18083 8000 3000 3001 8080 5173 6379 7233 8233 5000)
for port in "${PORTS[@]}"; do
    if ss -tlnp "sport = :$port" 2>/dev/null | grep -q LISTEN; then
        warn "Port $port is already in use — may conflict."
    fi
done

if [[ $FAILURES -gt 0 ]]; then
    err "Verification failed with $FAILURES error(s)."
    exit 1
fi
log "✅ All checks passed."
