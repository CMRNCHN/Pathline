#!/usr/bin/env bash
#
# Bounded Runtime Probe Script
# Deterministically validates the IVR assessor runtime.
# Scope constraints: operational validation only.

set -euo pipefail

# Config
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$DIR/docker-compose.yml"
API_URL="http://localhost:8081"
MAX_START_WAIT=60

log() { echo "[probe] $*"; }
err() { echo "[probe] ERROR: $*" >&2; exit 1; }

cd "$DIR"

# 1. Stale-runtime detection
log "Detecting stale runtime..."
if docker compose -f "$COMPOSE_FILE" ps -q api 2>/dev/null | grep -q .; then
    log "Stale runtime found. Executing bounded restart/cleanup..."
    docker compose -f "$COMPOSE_FILE" down --volumes --remove-orphans || err "Failed to teardown stale runtime"
fi

# 2. Startup ordering & bounded restart
log "Starting runtime stack..."
docker compose -f "$COMPOSE_FILE" up -d

# 3. Runtime readiness
log "Polling for runtime readiness ($MAX_START_WAIT s bounded wait)..."
START_TIME=$(date +%s)
READY=0

while true; do
    NOW=$(date +%s)
    if (( NOW - START_TIME > MAX_START_WAIT )); then
        break
    fi

    if curl -sf "$API_URL/healthz" >/dev/null; then
        READY=1
        break
    fi
    sleep 2
done

if [[ $READY -eq 0 ]]; then
    docker compose -f "$COMPOSE_FILE" logs api
    err "Runtime failed to reach readiness within ${MAX_START_WAIT}s"
fi
log "Runtime is ready."

# 4. Metrics availability & Queue/Checkpoint visibility
log "Validating metrics availability and queue/checkpoint visibility..."
METRICS_JSON=$(curl -sf "$API_URL/runtime-metrics") || err "Failed to fetch /runtime-metrics"

if ! echo "$METRICS_JSON" | grep -q '"uptime_s"'; then
    err "Metrics missing 'uptime_s'"
fi
if ! echo "$METRICS_JSON" | grep -q '"lifecycle_events"'; then
    err "Metrics missing 'lifecycle_events' (queue/checkpoint visibility)"
fi
log "Metrics and checkpoints verified."

# 5. Websocket reachability
log "Validating websocket reachability (/stream)..."
# We expect 101 Switching Protocols, 403 Forbidden, 400 Bad Request, or similar WebSocket rejection
WS_RESPONSE=$(curl -i -s 
    -H "Connection: Upgrade" 
    -H "Upgrade: websocket" 
    -H "Sec-WebSocket-Version: 13" 
    -H "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==" 
    "$API_URL/stream" | head -n 1 | tr -d '')

if echo "$WS_RESPONSE" | grep -qE "HTTP/1.1 (101|403|400)"; then
    log "Websocket endpoint reached (Response: $WS_RESPONSE)"
else
    err "Websocket unreachable or unexpected response: $WS_RESPONSE"
fi

# 6. Cleanup sequencing
log "Validating cleanup sequencing..."
docker compose -f "$COMPOSE_FILE" down || err "Cleanup sequencing failed"
log "Cleanup sequenced correctly."

log "PROBE SUCCESS: Runtime environment is stable and operationally verified."