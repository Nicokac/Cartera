import os
import signal
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "reports"
STATIC_DIR = ROOT / "static"
SCRIPT = ROOT / "scripts" / "generate_real_report.py"
LOG_PATH = ROOT / "data" / "runtime" / "server_run.log"
RUN_PID_PATH = ROOT / "data" / "runtime" / "server_run.pid"
VERSION_FILE = ROOT / "version.txt"

app = FastAPI(title="Cartera")

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


class RunParams(BaseModel):
    username: str = ""
    password: str = ""
    usar_liquidez_iol: bool = True
    aporte_externo_ars: float = 0.0


def _parse_ts(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _read_log_tail(limit: int = 1200) -> str:
    try:
        if not LOG_PATH.exists():
            return ""
        return LOG_PATH.read_text(encoding="utf-8")[-limit:]
    except Exception:
        return ""


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


def _watch_process() -> None:
    global _process, _cancel_requested
    if _process is None:
        return
    _process.wait()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
                text = LOG_PATH.read_text(encoding="utf-8")[-800:]
            except Exception:
                text = f"Código de salida: {_process.returncode}"
            _state["status"] = "error"
            _state["finished_at"] = ts
            _state["error"] = text
        _process = None
        _cancel_requested = False
        _clear_run_pid()


@app.get("/", response_class=HTMLResponse)
def get_index() -> HTMLResponse:
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=503, detail="Frontend no encontrado")
    return HTMLResponse(content=index.read_text(encoding="utf-8"))


@app.post("/run")
def post_run(params: RunParams) -> JSONResponse:
    global _process, _cancel_requested
    with _lock:
        if _state["status"] == "running":
            raise HTTPException(status_code=409, detail="Ya hay un reporte en progreso.")
        liquidity_flag = "--use-iol-liquidity" if params.usar_liquidez_iol else "--no-use-iol-liquidity"
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--non-interactive",
            liquidity_flag,
            "--aporte-externo-ars",
            str(params.aporte_externo_ars),
        ]
        username = params.username.strip()
        password = params.password.strip()
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
def post_cancel() -> JSONResponse:
    global _cancel_requested
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
    uptime_seconds = None
    if started_dt is not None:
        uptime_seconds = max(0, int((datetime.now() - started_dt).total_seconds()))

    pid = None
    if _process is not None:
        pid = getattr(_process, "pid", None)

    payload = {
        **_state,
        "pid": pid,
        "uptime_seconds": uptime_seconds,
        "log_path": str(LOG_PATH),
        "last_log_mtime": _read_log_mtime(),
        "log_tail": _read_log_tail(),
    }
    return JSONResponse(payload)


@app.get("/health")
def get_health() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "cartera-local-app"})


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


@app.on_event("startup")
def on_startup() -> None:
    _recover_orphan_run()


app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")


if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
