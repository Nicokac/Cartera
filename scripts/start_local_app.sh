#!/usr/bin/env bash
set -euo pipefail

BIND_HOST="${BIND_HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
NO_BROWSER=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bind-host) BIND_HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --no-browser) NO_BROWSER=1; shift ;;
    *)
      echo "Uso: $0 [--bind-host HOST] [--port PORT] [--no-browser]"
      exit 2
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/data/runtime"
PID_PATH="$RUNTIME_DIR/local_app.pid"
OUT_LOG="$RUNTIME_DIR/local_app.out.log"
ERR_LOG="$RUNTIME_DIR/local_app.err.log"
mkdir -p "$RUNTIME_DIR"

if [[ -f "$PID_PATH" ]]; then
  EXISTING_PID="$(cat "$PID_PATH" 2>/dev/null || true)"
  if [[ -n "${EXISTING_PID:-}" ]] && kill -0 "$EXISTING_PID" 2>/dev/null; then
    echo "Local app ya esta corriendo (PID=$EXISTING_PID) en http://$BIND_HOST:$PORT"
    if [[ "$NO_BROWSER" -eq 0 ]]; then
      if command -v xdg-open >/dev/null 2>&1; then xdg-open "http://$BIND_HOST:$PORT" >/dev/null 2>&1 || true; fi
      if command -v open >/dev/null 2>&1; then open "http://$BIND_HOST:$PORT" >/dev/null 2>&1 || true; fi
    fi
    exit 0
  fi
fi

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_EXE="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_EXE="python3"
else
  PYTHON_EXE="python"
fi

(
  cd "$ROOT_DIR"
  nohup "$PYTHON_EXE" -m uvicorn server:app --host "$BIND_HOST" --port "$PORT" >>"$OUT_LOG" 2>>"$ERR_LOG" &
  echo $! >"$PID_PATH"
)

sleep 1
PID_VALUE="$(cat "$PID_PATH" 2>/dev/null || true)"
if [[ -z "${PID_VALUE:-}" ]] || ! kill -0 "$PID_VALUE" 2>/dev/null; then
  echo "No se pudo iniciar la app local. Revisa:"
  echo "  $ERR_LOG"
  exit 1
fi

echo "App local iniciada (PID=$PID_VALUE) en http://$BIND_HOST:$PORT"
echo "Para detenerla: ./scripts/stop_local_app.sh"

if [[ "$NO_BROWSER" -eq 0 ]]; then
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "http://$BIND_HOST:$PORT" >/dev/null 2>&1 || true; fi
  if command -v open >/dev/null 2>&1; then open "http://$BIND_HOST:$PORT" >/dev/null 2>&1 || true; fi
fi
