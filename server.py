import os
import re
import signal
import subprocess
import sys
import threading
import uuid
import json
import csv
import shutil
from datetime import datetime
from pathlib import Path
import time
import requests
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
import uvicorn

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
STATIC_DIR = ROOT / "static"
SCRIPT = ROOT / "scripts" / "generate_real_report.py"
LOG_PATH = ROOT / "data" / "runtime" / "server_run.log"
RUN_PID_PATH = ROOT / "data" / "runtime" / "server_run.pid"
SESSION_FILE = ROOT / "data" / "runtime" / "session.txt"
RUN_HISTORY_FILE = ROOT / "data" / "runtime" / "run_history.jsonl"
VERSION_FILE = ROOT / "version.txt"
DECISION_HISTORY_FILE = ROOT / "data" / "runtime" / "decision_history.csv"
PREDICTION_HISTORY_FILE = ROOT / "data" / "runtime" / "prediction_history.csv"
RUNTIME_CORRUPT_DIR = ROOT / "data" / "runtime" / "corrupt"

def on_startup() -> None:
    _validate_runtime_csvs_on_startup()
    _recover_orphan_run()
    _ensure_session_token()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    on_startup()
    yield


app = FastAPI(title="Cartera", lifespan=_lifespan)

_state: dict = {
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "error": None,
    "params": None,
}
_process: subprocess.Popen | None = None
_lock = threading.Lock()
_cancel_requested = False
_session_token = ""
_run_request_timestamps: list[float] = []
_RUN_RATE_LIMIT_WINDOW_SECONDS = 60.0
_RUN_RATE_LIMIT_MAX_REQUESTS = 3
_RUN_COMPLETION_WEBHOOK_TIMEOUT_SECONDS = 2.0
_API_HEALTH_CIRCUIT_THRESHOLD = 3
_API_HEALTH_CIRCUIT_COOLDOWN_SECONDS = 300.0
_api_health_failures: dict[str, int] = {}
_api_health_opened_at: dict[str, float] = {}

_DECISION_HISTORY_REQUIRED_COLUMNS = {
    "run_date",
    "Ticker_IOL",
    "asset_subfamily",
    "score_unificado",
    "accion_sugerida_v2",
}
_PREDICTION_HISTORY_REQUIRED_COLUMNS = {
    "run_date",
    "ticker",
    "direction",
    "confidence",
    "horizon_days",
    "outcome_date",
}


class RunParams(BaseModel):
    username: str = Field(default="", max_length=200)
    password: str = Field(default="", max_length=200)
    usar_liquidez_iol: bool = True
    aporte_externo_ars: float = 0.0

    @field_validator("aporte_externo_ars")
    @classmethod
    def validate_aporte_externo_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("aporte_externo_ars debe ser mayor o igual a 0")
        return value


def _parse_ts(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _read_log_tail(limit: int = 3000) -> str:
    try:
        if not LOG_PATH.exists():
            return ""
        return LOG_PATH.read_text(encoding="utf-8")[-limit:]
    except Exception:
        return ""


def _count_log_lines() -> int:
    try:
        if not LOG_PATH.exists():
            return 0
        return len(LOG_PATH.read_text(encoding="utf-8").splitlines())
    except Exception:
        return 0


_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\b(IOL_USERNAME|IOL_PASSWORD)\b\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"(?i)\b(username|password)\b\s*[:=]\s*([^\s,;]+)"),
)


def _sanitize_secrets(text: str) -> str:
    if not text:
        return text
    sanitized = text
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub(lambda m: f"{m.group(1)}=<redacted>", sanitized)
    return sanitized


def _summarize_process_error(log_text: str, returncode: int) -> str:
    text = str(log_text or "")
    if "401 Client Error: Unauthorized" in text and "invertironline.com/token" in text:
        return "Credenciales IOL invalidas. Verifica usuario/password e intenta nuevamente."
    if "429" in text and "invertironline.com" in text:
        return "IOL rechazo temporalmente la solicitud (429). Reintenta en unos minutos."
    stripped = text.strip()
    if stripped:
        return stripped[-800:]
    return f"Codigo de salida: {returncode}"


def _read_log_mtime() -> str | None:
    try:
        if not LOG_PATH.exists():
            return None
        return datetime.fromtimestamp(LOG_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _read_run_pid() -> int | None:
    try:
        if not RUN_PID_PATH.exists():
            return None
        raw = RUN_PID_PATH.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        return int(raw)
    except Exception:
        return None


def _write_run_pid(pid: int) -> None:
    RUN_PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUN_PID_PATH.write_text(str(pid), encoding="utf-8")


def _clear_run_pid() -> None:
    try:
        if RUN_PID_PATH.exists():
            RUN_PID_PATH.unlink()
    except Exception:
        pass


def _is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _terminate_pid(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


def _recover_orphan_run() -> None:
    orphan_pid = _read_run_pid()
    if orphan_pid is None:
        return
    alive = _is_process_alive(orphan_pid)
    if alive:
        _terminate_pid(orphan_pid)
    _clear_run_pid()
    _state["status"] = "interrupted"
    _state["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _state["error"] = "Corrida previa interrumpida por reinicio del servidor."
    _append_run_history(
        {
            "status": "interrupted",
            "started_at": None,
            "finished_at": _state["finished_at"],
            "username": None,
            "usar_liquidez_iol": None,
            "aporte_externo_ars": None,
            "error": _state["error"],
        }
    )


def _ensure_session_token() -> str:
    global _session_token
    try:
        if SESSION_FILE.exists():
            existing = SESSION_FILE.read_text(encoding="utf-8").strip()
            if existing:
                _session_token = existing
                return _session_token
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        _session_token = str(uuid.uuid4())
        SESSION_FILE.write_text(_session_token, encoding="utf-8")
        return _session_token
    except Exception:
        _session_token = _session_token or str(uuid.uuid4())
        return _session_token


def _append_run_history(entry: dict[str, object]) -> None:
    try:
        RUN_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with RUN_HISTORY_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _read_recent_runs(limit: int = 5) -> list[dict[str, object]]:
    try:
        if not RUN_HISTORY_FILE.exists():
            return []
        rows: list[dict[str, object]] = []
        for line in RUN_HISTORY_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                if isinstance(payload, dict):
                    rows.append(payload)
            except json.JSONDecodeError:
                continue
        return rows[-limit:][::-1]
    except Exception:
        return []


def _notify_run_completion(payload: dict[str, object]) -> None:
    webhook_url = str(os.environ.get("RUN_COMPLETION_WEBHOOK_URL", "")).strip()
    if not webhook_url:
        return
    try:
        requests.post(
            webhook_url,
            json=payload,
            timeout=_RUN_COMPLETION_WEBHOOK_TIMEOUT_SECONDS,
        )
    except Exception:
        return


def _quarantine_runtime_csv(path: Path) -> None:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    RUNTIME_CORRUPT_DIR.mkdir(parents=True, exist_ok=True)
    target = RUNTIME_CORRUPT_DIR / f"{path.name}.{ts}.corrupt"
    shutil.move(str(path), str(target))


def _validate_runtime_csv_schema(path: Path, required_columns: set[str]) -> bool:
    if not path.exists():
        return True
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
        if not header:
            _quarantine_runtime_csv(path)
            return False
        header_set = {str(col).strip() for col in header if str(col).strip()}
        if not required_columns.issubset(header_set):
            _quarantine_runtime_csv(path)
            return False
        return True
    except Exception:
        _quarantine_runtime_csv(path)
        return False


def _validate_runtime_csvs_on_startup() -> None:
    _validate_runtime_csv_schema(DECISION_HISTORY_FILE, _DECISION_HISTORY_REQUIRED_COLUMNS)
    _validate_runtime_csv_schema(PREDICTION_HISTORY_FILE, _PREDICTION_HISTORY_REQUIRED_COLUMNS)


def _watch_process() -> None:
    global _process, _cancel_requested
    if _process is None:
        return
    _process.wait()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    webhook_payload: dict[str, object] | None = None
    with _lock:
        if _cancel_requested:
            _state["status"] = "interrupted"
            _state["finished_at"] = ts
            _state["error"] = None
        elif _process.returncode == 0:
            _state["status"] = "done"
            _state["finished_at"] = ts
        else:
            try:
                text = LOG_PATH.read_text(encoding="utf-8")
            except Exception:
                text = f"Código de salida: {_process.returncode}"
            _state["status"] = "error"
            _state["finished_at"] = ts
            _state["error"] = _summarize_process_error(text, int(_process.returncode))
        _process = None
        _cancel_requested = False
        _clear_run_pid()
        webhook_payload = {
            "status": _state.get("status"),
            "started_at": _state.get("started_at"),
            "finished_at": _state.get("finished_at"),
            "username": ((_state.get("params") or {}).get("username") if isinstance(_state.get("params"), dict) else None),
            "usar_liquidez_iol": ((_state.get("params") or {}).get("usar_liquidez_iol") if isinstance(_state.get("params"), dict) else None),
            "aporte_externo_ars": ((_state.get("params") or {}).get("aporte_externo_ars") if isinstance(_state.get("params"), dict) else None),
            "error": _sanitize_secrets(str(_state.get("error") or ""))[:300],
        }
        _append_run_history(webhook_payload)
    if webhook_payload is not None:
        _notify_run_completion(webhook_payload)


@app.get("/", response_class=HTMLResponse)
def get_index() -> HTMLResponse:
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=503, detail="Frontend no encontrado")
    return HTMLResponse(content=index.read_text(encoding="utf-8"))


@app.post("/run")
def post_run(params: RunParams, x_session_token: str = Header(default="")) -> JSONResponse:
    global _process, _cancel_requested, _run_request_timestamps
    if not _session_token or x_session_token != _session_token:
        raise HTTPException(status_code=401, detail="Token de sesion invalido.")
    with _lock:
        now_ts = time.time()
        cutoff = now_ts - _RUN_RATE_LIMIT_WINDOW_SECONDS
        _run_request_timestamps = [ts for ts in _run_request_timestamps if ts >= cutoff]
        if len(_run_request_timestamps) >= _RUN_RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(status_code=429, detail="Rate limit excedido en /run. Reintenta en unos segundos.")
        _run_request_timestamps.append(now_ts)
        if _state["status"] == "running":
            raise HTTPException(status_code=409, detail="Ya hay un reporte en progreso.")
        username = params.username.strip()
        password = params.password.strip()
        if not username or not password:
            raise HTTPException(status_code=422, detail="Usuario y password IOL son obligatorios.")
        liquidity_flag = "--use-iol-liquidity" if params.usar_liquidez_iol else "--no-use-iol-liquidity"
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--non-interactive",
            liquidity_flag,
            "--aporte-externo-ars",
            str(params.aporte_externo_ars),
        ]
        child_env = os.environ.copy()
        if username:
            child_env["IOL_USERNAME"] = username
        if password:
            child_env["IOL_PASSWORD"] = password
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        log_file = LOG_PATH.open("w", encoding="utf-8")
        try:
            _process = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=log_file,
                stderr=log_file,
                env=child_env,
            )
            _write_run_pid(_process.pid)
        except Exception as exc:
            _process = None
            raise HTTPException(
                status_code=500,
                detail=f"No se pudo iniciar la corrida: {exc}",
            ) from exc
        finally:
            # Parent process should close its file handle after spawning subprocess.
            log_file.close()
        _state["status"] = "running"
        _state["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _state["finished_at"] = None
        _state["error"] = None
        _state["params"] = {
            "username": username,
            "usar_liquidez_iol": params.usar_liquidez_iol,
            "aporte_externo_ars": params.aporte_externo_ars,
        }
        _cancel_requested = False

    threading.Thread(target=_watch_process, daemon=True).start()
    return JSONResponse({"status": "started"})


@app.post("/cancel")
def post_cancel(x_session_token: str = Header(default="")) -> JSONResponse:
    global _cancel_requested
    if not _session_token or x_session_token != _session_token:
        raise HTTPException(status_code=401, detail="Token de sesion invalido.")
    with _lock:
        if _state["status"] != "running" or _process is None:
            raise HTTPException(status_code=409, detail="No hay una corrida en progreso para cancelar.")
        if _process.poll() is not None:
            raise HTTPException(status_code=409, detail="La corrida ya finalizo.")
        _cancel_requested = True
        _process.terminate()
    return JSONResponse({"status": "cancelling"})


@app.get("/status")
def get_status() -> JSONResponse:
    return JSONResponse(_state)


@app.get("/status/detail")
def get_status_detail() -> JSONResponse:
    started_dt = _parse_ts(_state.get("started_at"))
    finished_dt = _parse_ts(_state.get("finished_at"))
    uptime_seconds = None
    if started_dt is not None and _state.get("status") == "running":
        uptime_seconds = max(0, int((datetime.now() - started_dt).total_seconds()))
    elapsed_seconds = None
    if started_dt is not None:
        end_dt = finished_dt or datetime.now()
        elapsed_seconds = max(0, int((end_dt - started_dt).total_seconds()))

    pid = None
    if _process is not None:
        pid = getattr(_process, "pid", None)

    payload = {
        **_state,
        "pid": pid,
        "uptime_seconds": uptime_seconds,
        "elapsed_seconds": elapsed_seconds,
        "log_path": str(LOG_PATH),
        "last_log_mtime": _read_log_mtime(),
        "log_lines": _count_log_lines(),
        "log_tail": _sanitize_secrets(_read_log_tail()),
    }
    if isinstance(payload.get("error"), str):
        payload["error"] = _sanitize_secrets(payload["error"])
    return JSONResponse(payload)


@app.get("/health")
def get_health() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "cartera-local-app"})


def _check_url_health(
    name: str,
    url: str,
    *,
    expected_status_codes: set[int],
    timeout_seconds: float = 3.0,
) -> dict[str, object]:
    now_ts = time.time()
    fail_count = int(_api_health_failures.get(name, 0))
    opened_at = _api_health_opened_at.get(name)
    if fail_count >= _API_HEALTH_CIRCUIT_THRESHOLD and opened_at is not None:
        age_seconds = now_ts - float(opened_at)
        if age_seconds < _API_HEALTH_CIRCUIT_COOLDOWN_SECONDS:
            return {
                "name": name,
                "url": url,
                "ok": False,
                "status_code": None,
                "expected_status_codes": sorted(expected_status_codes),
                "latency_ms": 0,
                "circuit_open": True,
                "failure_count": fail_count,
                "cooldown_remaining_seconds": max(0, int(_API_HEALTH_CIRCUIT_COOLDOWN_SECONDS - age_seconds)),
            }

    started = time.perf_counter()
    try:
        response = requests.get(url, timeout=timeout_seconds)
        latency_ms = int((time.perf_counter() - started) * 1000)
        status_code = int(response.status_code)
        is_ok = status_code in expected_status_codes
        if is_ok:
            _api_health_failures[name] = 0
            _api_health_opened_at.pop(name, None)
        else:
            _api_health_failures[name] = fail_count + 1
            if _api_health_failures[name] >= _API_HEALTH_CIRCUIT_THRESHOLD:
                _api_health_opened_at[name] = now_ts
        return {
            "name": name,
            "url": url,
            "ok": is_ok,
            "status_code": status_code,
            "expected_status_codes": sorted(expected_status_codes),
            "latency_ms": latency_ms,
            "circuit_open": bool(_api_health_opened_at.get(name)),
            "failure_count": int(_api_health_failures.get(name, 0)),
        }
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _api_health_failures[name] = fail_count + 1
        if _api_health_failures[name] >= _API_HEALTH_CIRCUIT_THRESHOLD:
            _api_health_opened_at[name] = now_ts
        return {
            "name": name,
            "url": url,
            "ok": False,
            "status_code": None,
            "expected_status_codes": sorted(expected_status_codes),
            "latency_ms": latency_ms,
            "error": str(exc),
            "circuit_open": bool(_api_health_opened_at.get(name)),
            "failure_count": int(_api_health_failures.get(name, 0)),
        }


@app.get("/api-health")
def get_api_health() -> JSONResponse:
    checks = [
        ("iol", "https://api.invertironline.com/token", {400, 401, 403, 405}),
        ("argentinadatos", "https://api.argentinadatos.com/v1/cotizaciones/dolares/bolsa", {200}),
        ("bcra", "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias", {200}),
        ("bonistas", "https://bonistas.com", {200}),
        ("fred", "https://api.stlouisfed.org/fred/series?series_id=DGS10", {400}),
        ("finviz", "https://finviz.com/quote.ashx?t=AAPL", {200, 403}),
    ]
    results = [
        _check_url_health(name, url, expected_status_codes=expected_status_codes)
        for name, url, expected_status_codes in checks
    ]
    overall_ok = all(bool(item.get("ok")) for item in results)
    return JSONResponse({"ok": overall_ok, "apis": results})


@app.get("/version")
def get_version() -> JSONResponse:
    if VERSION_FILE.exists():
        return JSONResponse({"version": VERSION_FILE.read_text(encoding="utf-8").strip()})
    # Fallback para entorno de desarrollo: leer pyproject.toml
    import re
    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"), re.MULTILINE)
        if m:
            return JSONResponse({"version": m.group(1) + "-dev"})
    return JSONResponse({"version": "desconocida"})


@app.get("/session")
def get_session() -> JSONResponse:
    token = _ensure_session_token()
    return JSONResponse({"token": token})


@app.get("/reports/list")
def get_reports_list() -> JSONResponse:
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        rows = []
        for path in sorted(REPORTS_DIR.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True):
            rows.append(
                {
                    "name": path.name,
                    "url": f"/reports/{path.name}",
                    "size_bytes": path.stat().st_size,
                    "modified_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        return JSONResponse({"reports": rows})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo listar reportes: {exc}")


@app.get("/runs/recent")
def get_runs_recent() -> JSONResponse:
    return JSONResponse({"runs": _read_recent_runs(limit=5)})


REPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")


if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
