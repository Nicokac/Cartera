#!/usr/bin/env bash
set -euo pipefail

BIND_HOST="${BIND_HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/data/runtime"
ERR_LOG="$RUNTIME_DIR/local_app.err.log"
OUT_LOG="$RUNTIME_DIR/local_app.out.log"

show_menu() {
  echo
  echo "=== Cartera Local App ==="
  echo "1) Start"
  echo "2) Status"
  echo "3) Stop"
  echo "4) Open Browser"
  echo "5) Tail Error Log"
  echo "6) Tail Output Log"
  echo "7) Exit"
}

while true; do
  show_menu
  read -r -p "Selecciona una opcion: " choice
  case "$choice" in
    1) bash "$ROOT_DIR/scripts/start_local_app.sh" --bind-host "$BIND_HOST" --port "$PORT" ;;
    2) bash "$ROOT_DIR/scripts/status_local_app.sh" --bind-host "$BIND_HOST" --port "$PORT" ;;
    3) bash "$ROOT_DIR/scripts/stop_local_app.sh" ;;
    4)
      if command -v xdg-open >/dev/null 2>&1; then xdg-open "http://$BIND_HOST:$PORT" >/dev/null 2>&1 || true; fi
      if command -v open >/dev/null 2>&1; then open "http://$BIND_HOST:$PORT" >/dev/null 2>&1 || true; fi
      echo "Browser abierto en http://$BIND_HOST:$PORT"
      ;;
    5)
      if [[ -f "$ERR_LOG" ]]; then tail -f "$ERR_LOG"; else echo "No existe $ERR_LOG"; fi
      ;;
    6)
      if [[ -f "$OUT_LOG" ]]; then tail -f "$OUT_LOG"; else echo "No existe $OUT_LOG"; fi
      ;;
    7) break ;;
    *) echo "Opcion invalida." ;;
  esac
done
