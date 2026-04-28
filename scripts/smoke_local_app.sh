#!/usr/bin/env bash
set -euo pipefail

BIND_HOST="${BIND_HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
BASE_URL="http://$BIND_HOST:$PORT"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
START_SCRIPT="$ROOT_DIR/scripts/start_local_app.sh"
STATUS_SCRIPT="$ROOT_DIR/scripts/status_local_app.sh"
STOP_SCRIPT="$ROOT_DIR/scripts/stop_local_app.sh"

wait_for_endpoint() {
  local url="$1"
  local max_seconds="${2:-20}"
  local start_ts
  start_ts="$(date +%s)"
  while true; do
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
      curl -fsS --max-time 2 "$url"
      return 0
    fi
    if (( "$(date +%s)" - start_ts >= max_seconds )); then
      echo "Timeout esperando endpoint: $url" >&2
      return 1
    fi
    sleep 0.4
  done
}

echo "[smoke] start local app..."
bash "$START_SCRIPT" --bind-host "$BIND_HOST" --port "$PORT" --no-browser

cleanup() {
  echo "[smoke] stopping local app..."
  bash "$STOP_SCRIPT" || true
}
trap cleanup EXIT

echo "[smoke] status script output:"
bash "$STATUS_SCRIPT" --bind-host "$BIND_HOST" --port "$PORT"

echo "[smoke] waiting for /status endpoint..."
STATUS_PAYLOAD="$(wait_for_endpoint "$BASE_URL/status" 20)"
echo "[smoke] /status payload: $STATUS_PAYLOAD"
echo "$STATUS_PAYLOAD" | grep -Eq '"status"\s*:\s*"(idle|running|done|error|interrupted)"'

echo "[smoke] waiting for /status/detail endpoint..."
DETAIL_PAYLOAD="$(wait_for_endpoint "$BASE_URL/status/detail" 20)"
echo "[smoke] /status/detail payload: $DETAIL_PAYLOAD"
echo "$DETAIL_PAYLOAD" | grep -Eq '"log_path"\s*:'

echo "[smoke] local app health OK"
