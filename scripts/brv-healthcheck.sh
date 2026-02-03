#!/bin/bash
set -euo pipefail

ROOT_DIR="/Users/jeremy/Projects/Thanos"
LOG_FILE="$ROOT_DIR/logs/brv-healthcheck.log"
TMUX_SESSION="brv"
BRV_CMD="/opt/homebrew/bin/brv"
export BRV_FORCE_FILE_TOKEN_STORE=1

log() {
  echo "[$(date)] $*" >> "$LOG_FILE"
}

ensure_tmux() {
  if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    log "tmux session missing; starting ByteRover"
    tmux new-session -d -s "$TMUX_SESSION" "BRV_FORCE_FILE_TOKEN_STORE=1 $BRV_CMD"
    sleep 2
  fi
}

get_port() {
  python - <<'PY'
import json
from pathlib import Path
p = Path('/Users/jeremy/Projects/Thanos/.brv/instance.json')
if not p.exists():
    raise SystemExit(1)
try:
    data = json.loads(p.read_text())
    port = data.get('port')
    if not port:
        raise SystemExit(1)
    print(port)
except Exception:
    raise SystemExit(1)
PY
}

check_port_listening() {
  local port="$1"
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

check_status() {
  local status_json
  status_json=$("$BRV_CMD" status --format json 2>/dev/null | head -n 1 || true)
  if [ -z "$status_json" ]; then
    return 1
  fi
  python - <<'PY' "$status_json"
import json, sys
try:
    data = json.loads(sys.argv[1]).get('data', {})
    mcp = data.get('mcpStatus')
    auth = data.get('authStatus')
    ok = mcp in ('connected',) and auth in ('logged_in',)
    sys.exit(0 if ok else 1)
except Exception:
    sys.exit(1)
PY
}

restart_brv() {
  log "restarting ByteRover tmux session"
  tmux kill-session -t "$TMUX_SESSION" 2>/dev/null || true
  rm -f "$ROOT_DIR/.brv/instance.json"
  tmux new-session -d -s "$TMUX_SESSION" "BRV_FORCE_FILE_TOKEN_STORE=1 $BRV_CMD"
  sleep 2
}

main() {
  ensure_tmux

  local port
  if ! port=$(get_port 2>/dev/null); then
    log "instance.json missing or invalid; restarting"
    restart_brv
    return 0
  fi

  if ! check_port_listening "$port"; then
    log "port $port not listening; restarting"
    restart_brv
    return 0
  fi

  if ! check_status; then
    log "status check failed; restarting"
    restart_brv
    return 0
  fi
}

main "$@"
