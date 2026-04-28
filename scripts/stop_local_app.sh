#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_PATH="$ROOT_DIR/data/runtime/local_app.pid"

if [[ ! -f "$PID_PATH" ]]; then
  echo "No hay PID file. La app local no parece estar corriendo."
  exit 0
fi

PID_VALUE="$(cat "$PID_PATH" 2>/dev/null || true)"
if [[ -z "${PID_VALUE:-}" ]]; then
  rm -f "$PID_PATH"
  echo "PID file vacio, limpiado."
  exit 0
fi

if kill -0 "$PID_VALUE" 2>/dev/null; then
  kill "$PID_VALUE" 2>/dev/null || true
  sleep 1
  if kill -0 "$PID_VALUE" 2>/dev/null; then
    kill -9 "$PID_VALUE" 2>/dev/null || true
  fi
  echo "App local detenida (PID=$PID_VALUE)."
else
  echo "No existe proceso activo con PID=$PID_VALUE."
fi

rm -f "$PID_PATH"
