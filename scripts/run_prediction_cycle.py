from __future__ import annotations

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
from prediction.store import load_prediction_history, save_prediction_history
from prediction.verifier import verify_prediction_history


def run_prediction_cycle(*, today: object | None = None) -> dict[str, object]:
    """Mantiene el historial existente de predicciones.

    Este runner no genera predicciones nuevas. Las observaciones nuevas se crean
    durante las corridas de reporte (`generate_real_report.py` o smoke) y luego
    este ciclo se usa para verificar outcomes vencidos y recalibrar pesos.
    """
    history = load_prediction_history()
    verified_history = verify_prediction_history(history, today=today)
    save_prediction_history(verified_history)

    completed_mask = verified_history.get("outcome", pd.Series(dtype=object)).fillna("").astype(str).str.strip() != ""
    completed = verified_history.loc[completed_mask].copy()
    updated_weights, calibration_summary = calibrate_prediction_weights(verified_history, project_config.PREDICTION_WEIGHTS)
    save_prediction_weights(updated_weights)

    recalibrated = 0
    if isinstance(calibration_summary, pd.DataFrame) and not calibration_summary.empty and "status" in calibration_summary.columns:
        recalibrated = int((calibration_summary["status"] == "recalibrated").sum())

    return {
        "history_rows": int(len(verified_history)),
        "completed_rows": int(len(completed)),
        "pending_rows": int((~completed_mask).sum()) if len(verified_history) else 0,
        "recalibrated_signals": recalibrated,
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
