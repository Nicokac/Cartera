#!/usr/bin/env bash
set -euo pipefail

BIND_HOST="${BIND_HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
DETAILED=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bind-host) BIND_HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --detailed) DETAILED=1; shift ;;
    *)
      echo "Uso: $0 [--bind-host HOST] [--port PORT] [--detailed]"
      exit 2
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_PATH="$ROOT_DIR/data/runtime/local_app.pid"
URL="http://$BIND_HOST:$PORT"
CHECKED_AT="$(date '+%Y-%m-%d %H:%M:%S')"

if [[ ! -f "$PID_PATH" ]]; then
  echo "status=stopped pid=none url=$URL checked_at=$CHECKED_AT"
  exit 0
fi

PID_VALUE="$(cat "$PID_PATH" 2>/dev/null || true)"
if [[ -z "${PID_VALUE:-}" ]]; then
  echo "status=stopped pid=none url=$URL checked_at=$CHECKED_AT"
  exit 0
fi

if kill -0 "$PID_VALUE" 2>/dev/null; then
  echo "status=running pid=$PID_VALUE url=$URL checked_at=$CHECKED_AT"
  if [[ "$DETAILED" -eq 1 ]]; then
    if command -v curl >/dev/null 2>&1; then
      curl -fsS --max-time 2 "$URL/status/detail" || echo "detail_error=No se pudo consultar /status/detail"
    else
      echo "detail_error=curl no disponible"
    fi
  fi
  exit 0
fi

rm -f "$PID_PATH"
echo "status=stopped pid=none url=$URL checked_at=$CHECKED_AT stale_pid=$PID_VALUE cleaned=true"
