import importlib
import json
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from prediction.calibration import (
    calibrate_prediction_weights,
    compute_signal_ic,
    extract_signal_vote_frame,
    outcome_to_numeric,
    save_prediction_weights,
)


class PredictionCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        project_config = importlib.import_module("config")
        project_config.clear_config_cache()
        cls.weights = project_config.PREDICTION_WEIGHTS

    def test_outcome_to_numeric_maps_ternary_outcomes(self) -> None:
        self.assertEqual(outcome_to_numeric("up"), 1.0)
        self.assertEqual(outcome_to_numeric("neutral"), 0.0)
        self.assertEqual(outcome_to_numeric("down"), -1.0)
        self.assertIsNone(outcome_to_numeric("pending"))

    def test_extract_signal_vote_frame_keeps_only_completed_outcomes(self) -> None:
        history = pd.DataFrame(
            [
                {"ticker": "AAPL", "run_date": "2026-04-20", "outcome": "up", "signal_votes": "{\"rsi\": 1, \"momentum_20d\": 1}"},
                {"ticker": "MSFT", "run_date": "2026-04-20", "outcome": "", "signal_votes": "{\"rsi\": -1}"},
            ]
        )

        frame = extract_signal_vote_frame(history)

        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.loc[0, "ticker"], "AAPL")
        self.assertEqual(frame.loc[0, "outcome_numeric"], 1.0)
        self.assertEqual(frame.loc[0, "signal_votes"]["rsi"], 1.0)

    def test_compute_signal_ic_returns_positive_correlation(self) -> None:
        vote_frame = pd.DataFrame(
            [
                {"signal_votes": {"rsi": 1}, "outcome_numeric": 1.0},
                {"signal_votes": {"rsi": 1}, "outcome_numeric": 1.0},
                {"signal_votes": {"rsi": -1}, "outcome_numeric": -1.0},
                {"signal_votes": {"rsi": -1}, "outcome_numeric": -1.0},
            ]
        )

        stats = compute_signal_ic(vote_frame, "rsi")

        self.assertEqual(stats["samples"], 4)
        self.assertAlmostEqual(float(stats["ic"]), 1.0, places=6)

    def test_calibrate_prediction_weights_recalibrates_with_sufficient_samples(self) -> None:
        custom_weights = json.loads(json.dumps(self.weights))
        custom_weights["calibration"]["min_samples"] = 4
        custom_weights["calibration"]["min_weight"] = 0.1
        custom_weights["calibration"]["max_weight"] = 1.0

        history = pd.DataFrame(
            [
                {"ticker": "AAPL", "run_date": "2026-04-20", "outcome": "up", "signal_votes": "{\"rsi\": 1, \"momentum_20d\": -1}"},
                {"ticker": "MSFT", "run_date": "2026-04-21", "outcome": "up", "signal_votes": "{\"rsi\": 1, \"momentum_20d\": -1}"},
                {"ticker": "KO", "run_date": "2026-04-22", "outcome": "down", "signal_votes": "{\"rsi\": -1, \"momentum_20d\": 1}"},
                {"ticker": "V", "run_date": "2026-04-23", "outcome": "down", "signal_votes": "{\"rsi\": -1, \"momentum_20d\": 1}"},
            ]
        )

        updated, summary = calibrate_prediction_weights(history, custom_weights)

        rsi_row = summary.loc[summary["signal"] == "rsi"].iloc[0]
        momentum_row = summary.loc[summary["signal"] == "momentum_20d"].iloc[0]

        self.assertEqual(rsi_row["status"], "recalibrated")
        self.assertEqual(momentum_row["status"], "recalibrated")
        self.assertAlmostEqual(float(updated["signals"]["rsi"]["weight"]), 1.0, places=6)
        self.assertAlmostEqual(float(updated["signals"]["momentum_20d"]["weight"]), 0.0, places=6)

    def test_calibrate_prediction_weights_turns_negative_ic_signal_off(self) -> None:
        custom_weights = json.loads(json.dumps(self.weights))
        custom_weights["calibration"]["min_samples"] = 4
        custom_weights["calibration"]["min_weight"] = 0.1
        custom_weights["calibration"]["max_weight"] = 1.0

        history = pd.DataFrame(
            [
                {"ticker": "AAPL", "run_date": "2026-04-20", "outcome": "up", "signal_votes": "{\"rsi\": -1}"},
                {"ticker": "MSFT", "run_date": "2026-04-21", "outcome": "up", "signal_votes": "{\"rsi\": -1}"},
                {"ticker": "KO", "run_date": "2026-04-22", "outcome": "down", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "V", "run_date": "2026-04-23", "outcome": "down", "signal_votes": "{\"rsi\": 1}"},
            ]
        )

        updated, summary = calibrate_prediction_weights(history, custom_weights)
        rsi_row = summary.loc[summary["signal"] == "rsi"].iloc[0]

        self.assertEqual(rsi_row["status"], "recalibrated")
        self.assertAlmostEqual(float(rsi_row["ic"]), -1.0, places=6)
        self.assertAlmostEqual(float(updated["signals"]["rsi"]["weight"]), 0.0, places=6)

    def test_calibrate_prediction_weights_preserves_weight_when_samples_are_insufficient(self) -> None:
        custom_weights = json.loads(json.dumps(self.weights))
        custom_weights["calibration"]["min_samples"] = 5

        history = pd.DataFrame(
            [
                {"ticker": "AAPL", "run_date": "2026-04-20", "outcome": "up", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "MSFT", "run_date": "2026-04-21", "outcome": "down", "signal_votes": "{\"rsi\": -1}"},
            ]
        )

        updated, summary = calibrate_prediction_weights(history, custom_weights)
        rsi_row = summary.loc[summary["signal"] == "rsi"].iloc[0]

        self.assertEqual(rsi_row["status"], "insufficient_samples")
        self.assertAlmostEqual(
            float(updated["signals"]["rsi"]["weight"]),
            float(custom_weights["signals"]["rsi"]["weight"]),
            places=6,
        )

    def test_save_prediction_weights_persists_json_file(self) -> None:
        path = ROOT / "tmp_prediction_weights.json"
        if path.exists():
            path.unlink()
        self.addCleanup(lambda: path.unlink() if path.exists() else None)

        saved = save_prediction_weights(self.weights, path=path)
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(saved, path)
        self.assertIn("signals", payload)
        self.assertIn("calibration", payload)


if __name__ == "__main__":
    unittest.main()
