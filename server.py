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


class RunParams(BaseModel):
    usar_liquidez_iol: bool = False
    aporte_externo_ars: float = 0.0


def _watch_process() -> None:
    global _process
    if _process is None:
        return
    _process.wait()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _lock:
        if _process.returncode == 0:
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


@app.get("/", response_class=HTMLResponse)
def get_index() -> HTMLResponse:
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=503, detail="Frontend no encontrado")
    return HTMLResponse(content=index.read_text(encoding="utf-8"))


@app.post("/run")
def post_run(params: RunParams) -> JSONResponse:
    global _process
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
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        log_file = LOG_PATH.open("w", encoding="utf-8")
        try:
            _process = subprocess.Popen(cmd, cwd=str(ROOT), stdout=log_file, stderr=log_file)
        finally:
            # Parent process should close its file handle after spawning subprocess.
            log_file.close()
        _state["status"] = "running"
        _state["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _state["finished_at"] = None
        _state["error"] = None
        _state["params"] = params.model_dump()

    threading.Thread(target=_watch_process, daemon=True).start()
    return JSONResponse({"status": "started"})


@app.get("/status")
def get_status() -> JSONResponse:
    return JSONResponse(_state)


@app.get("/health")
def get_health() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "cartera-local-app"})


app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")


if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
