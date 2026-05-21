from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

import config as project_config
from prediction.calibration import calibrate_prediction_weights, save_prediction_weights
from prediction.store import (
    DEFAULT_PREDICTION_HISTORY_RETENTION_DAYS,
    apply_prediction_history_retention,
    load_prediction_history,
    save_prediction_history,
)
from prediction.verifier import verify_prediction_history


def _completed_signature(history: pd.DataFrame) -> str:
    if history is None or history.empty:
        return ""
    required = ["run_date", "ticker", "outcome", "outcome_date"]
    frame = history.copy()
    for col in required:
        if col not in frame.columns:
            frame[col] = ""
    stable = (
        frame[required]
        .fillna("")
        .astype(str)
        .sort_values(required)
        .reset_index(drop=True)
    )
    raw = stable.to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def run_prediction_cycle(*, today: object | None = None) -> dict[str, object]:
    """Mantiene el historial existente de predicciones.

    Este runner no genera predicciones nuevas. Las observaciones nuevas se crean
    durante las corridas de reporte (`generate_real_report.py` o smoke) y luego
    este ciclo se usa para verificar outcomes vencidos y recalibrar pesos.
    """
    history = load_prediction_history()
    verified_history = verify_prediction_history(history, today=today)
    retention_days = int(project_config.PREDICTION_WEIGHTS.get("history_retention_days", DEFAULT_PREDICTION_HISTORY_RETENTION_DAYS))
    verified_history = apply_prediction_history_retention(
        verified_history,
        retention_days=retention_days,
        today=today,
    )
    save_prediction_history(verified_history)

    completed_mask = verified_history.get("outcome", pd.Series(dtype=object)).fillna("").astype(str).str.strip() != ""
    completed = verified_history.loc[completed_mask].copy()
    current_signature = _completed_signature(completed)
    current_weights = project_config.PREDICTION_WEIGHTS
    calibration_state = (current_weights.get("calibration_state", {}) or {}) if isinstance(current_weights, dict) else {}
    previous_signature = str(calibration_state.get("completed_signature", "") or "")

    recalibration_skipped = previous_signature == current_signature and bool(current_signature)
    if recalibration_skipped:
        updated_weights = current_weights
        calibration_summary = pd.DataFrame(
            [
                {
                    "signal": "-",
                    "samples": int(len(completed)),
                    "ic": None,
                    "previous_weight": None,
                    "new_weight": None,
                    "status": "skipped_no_new_completed_outcomes",
                    "scope": "global",
                    "asset_family": "global",
                }
            ]
        )
    else:
        updated_weights, calibration_summary = calibrate_prediction_weights(verified_history, current_weights)

    updated_weights = dict(updated_weights or {})
    updated_weights["calibration_state"] = {
        "completed_signature": current_signature,
        "completed_rows": int(len(completed)),
        "history_rows": int(len(verified_history)),
        "last_run_date_utc": pd.Timestamp.utcnow().isoformat(),
    }
    save_prediction_weights(updated_weights)

    recalibrated = 0
    if isinstance(calibration_summary, pd.DataFrame) and not calibration_summary.empty and "status" in calibration_summary.columns:
        recalibrated = int((calibration_summary["status"] == "recalibrated").sum())

    return {
        "history_rows": int(len(verified_history)),
        "completed_rows": int(len(completed)),
        "pending_rows": int((~completed_mask).sum()) if len(verified_history) else 0,
        "recalibrated_signals": recalibrated,
        "recalibration_skipped": bool(recalibration_skipped),
        "weights_path": str((project_config.MAPPINGS_DIR / "prediction_weights.json").resolve()),
        "history_path": str((ROOT / "data" / "runtime" / "prediction_history.csv").resolve()),
        "calibration_summary": calibration_summary,
    }


def main() -> None:
    result = run_prediction_cycle()
    printable = {key: value for key, value in result.items() if key != "calibration_summary"}
    print("Prediction Cycle")
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    calibration_summary = result.get("calibration_summary", pd.DataFrame())
    if isinstance(calibration_summary, pd.DataFrame) and not calibration_summary.empty:
        print("\nCalibration Summary")
        print(calibration_summary.to_string(index=False))


if __name__ == "__main__":
    main()
