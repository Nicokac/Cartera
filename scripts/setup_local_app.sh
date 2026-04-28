#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"

INSTALL_TEST_DEPS=0
SKIP_BOOTSTRAP=0

for arg in "$@"; do
  case "$arg" in
    --install-test-deps) INSTALL_TEST_DEPS=1 ;;
    --skip-bootstrap) SKIP_BOOTSTRAP=1 ;;
    *)
      echo "Uso: $0 [--install-test-deps] [--skip-bootstrap]"
      exit 2
      ;;
  esac
done

if [[ ! -x "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PY_LAUNCHER="python3"
  elif command -v python >/dev/null 2>&1; then
    PY_LAUNCHER="python"
  else
    echo "No se encontro Python. Instala Python 3.12+ y reintenta."
    exit 1
  fi
  echo "[setup] creando entorno virtual en .venv ..."
  "$PY_LAUNCHER" -m venv "$VENV_DIR"
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "No se pudo crear el entorno virtual en .venv."
  exit 1
fi

echo "[setup] actualizando pip ..."
"$PYTHON_BIN" -m pip install --upgrade pip

echo "[setup] instalando dependencias base ..."
"$PYTHON_BIN" -m pip install -r "$ROOT_DIR/requirements.txt"

if [[ "$INSTALL_TEST_DEPS" -eq 1 ]]; then
  echo "[setup] instalando dependencias extra de test ..."
  "$PYTHON_BIN" -m pip install "httpx>=0.27,<1"
fi

if [[ "$SKIP_BOOTSTRAP" -eq 0 ]]; then
  echo "[setup] ejecutando bootstrap de configuracion ..."
  "$PYTHON_BIN" "$ROOT_DIR/scripts/bootstrap_example_config.py"
fi

if [[ ! -f "$ROOT_DIR/.env" && -f "$ROOT_DIR/.env.example" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "[setup] se creo .env desde .env.example (completa tus claves)."
fi

echo
echo "Setup finalizado."
echo "Siguientes pasos:"
echo "  1) Editar .env con tus credenciales/API keys (si aplica)."
echo "  2) Iniciar app local: ./scripts/start_local_app.sh"
echo "  3) Smoke rapido: ./scripts/smoke_local_app.sh"
