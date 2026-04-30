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

    def test_calibrate_with_lookback_uses_recent_window_when_sufficient(self) -> None:
        custom_weights = json.loads(json.dumps(self.weights))
        custom_weights["calibration"]["min_samples"] = 4
        custom_weights["calibration"]["min_weight"] = 0.1
        custom_weights["calibration"]["max_weight"] = 1.0
        custom_weights["calibration"]["lookback_samples"] = 4
        custom_weights["calibration"]["min_recent_samples"] = 4

        history = pd.DataFrame(
            [
                {"ticker": "OLD1", "run_date": "2026-01-01", "outcome": "up", "signal_votes": "{\"rsi\": -1}"},
                {"ticker": "OLD2", "run_date": "2026-01-02", "outcome": "up", "signal_votes": "{\"rsi\": -1}"},
                {"ticker": "OLD3", "run_date": "2026-01-03", "outcome": "down", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "OLD4", "run_date": "2026-01-04", "outcome": "down", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "NEW1", "run_date": "2026-04-20", "outcome": "up", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "NEW2", "run_date": "2026-04-21", "outcome": "up", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "NEW3", "run_date": "2026-04-22", "outcome": "down", "signal_votes": "{\"rsi\": -1}"},
                {"ticker": "NEW4", "run_date": "2026-04-23", "outcome": "down", "signal_votes": "{\"rsi\": -1}"},
            ]
        )

        updated, summary = calibrate_prediction_weights(history, custom_weights)
        rsi_row = summary.loc[summary["signal"] == "rsi"].iloc[0]

        self.assertEqual(rsi_row["status"], "recalibrated")
        self.assertAlmostEqual(float(rsi_row["ic"]), 1.0, places=6)
        self.assertAlmostEqual(float(updated["signals"]["rsi"]["weight"]), 1.0, places=6)

    def test_calibrate_with_lookback_falls_back_to_full_history_when_recent_window_insufficient(self) -> None:
        custom_weights = json.loads(json.dumps(self.weights))
        custom_weights["calibration"]["min_samples"] = 4
        custom_weights["calibration"]["min_weight"] = 0.1
        custom_weights["calibration"]["max_weight"] = 1.0
        custom_weights["calibration"]["lookback_samples"] = 4
        custom_weights["calibration"]["min_recent_samples"] = 5

        history = pd.DataFrame(
            [
                {"ticker": "OLD1", "run_date": "2026-01-01", "outcome": "up", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "OLD2", "run_date": "2026-01-02", "outcome": "up", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "OLD3", "run_date": "2026-01-03", "outcome": "down", "signal_votes": "{\"rsi\": -1}"},
                {"ticker": "OLD4", "run_date": "2026-01-04", "outcome": "down", "signal_votes": "{\"rsi\": -1}"},
                {"ticker": "NEW1", "run_date": "2026-04-20", "outcome": "up", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "NEW2", "run_date": "2026-04-21", "outcome": "up", "signal_votes": "{\"rsi\": 1}"},
            ]
        )

        updated, summary = calibrate_prediction_weights(history, custom_weights)
        rsi_row = summary.loc[summary["signal"] == "rsi"].iloc[0]

        self.assertEqual(rsi_row["status"], "recalibrated")
        self.assertEqual(rsi_row["samples"], 6)
        self.assertAlmostEqual(float(rsi_row["ic"]), 1.0, places=6)

    def test_calibrate_without_lookback_uses_full_history(self) -> None:
        custom_weights = json.loads(json.dumps(self.weights))
        custom_weights["calibration"]["min_samples"] = 4
        custom_weights["calibration"]["lookback_samples"] = 0

        history = pd.DataFrame(
            [
                {"ticker": "A", "run_date": "2026-01-01", "outcome": "up", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "B", "run_date": "2026-01-02", "outcome": "up", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "C", "run_date": "2026-01-03", "outcome": "down", "signal_votes": "{\"rsi\": -1}"},
                {"ticker": "D", "run_date": "2026-01-04", "outcome": "down", "signal_votes": "{\"rsi\": -1}"},
            ]
        )

        updated, summary = calibrate_prediction_weights(history, custom_weights)
        rsi_row = summary.loc[summary["signal"] == "rsi"].iloc[0]

        self.assertEqual(rsi_row["samples"], 4)
        self.assertEqual(rsi_row["status"], "recalibrated")

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

    def test_calibrate_prediction_weights_adds_family_overrides_when_enabled_and_ready(self) -> None:
        custom_weights = json.loads(json.dumps(self.weights))
        custom_weights["calibration"]["family_enabled"] = True
        custom_weights["calibration"]["family_min_samples"] = 4
        custom_weights["calibration"]["family_min_per_direction"] = 1
        custom_weights["calibration"]["min_weight"] = 0.1
        custom_weights["calibration"]["max_weight"] = 1.0

        history = pd.DataFrame(
            [
                {"ticker": "A1", "asset_family": "stock", "run_date": "2026-04-20", "outcome": "up", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "A2", "asset_family": "stock", "run_date": "2026-04-21", "outcome": "up", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "A3", "asset_family": "stock", "run_date": "2026-04-22", "outcome": "down", "signal_votes": "{\"rsi\": -1}"},
                {"ticker": "A4", "asset_family": "stock", "run_date": "2026-04-23", "outcome": "neutral", "signal_votes": "{\"rsi\": 0}"},
            ]
        )

        updated, summary = calibrate_prediction_weights(history, custom_weights)
        self.assertIn("family_overrides", updated)
        self.assertIn("stock", updated["family_overrides"])
        self.assertIn("signals", updated["family_overrides"]["stock"])
        self.assertIn("rsi", updated["family_overrides"]["stock"]["signals"])
        family_rows = summary.loc[(summary["scope"] == "family") & (summary["asset_family"] == "stock")]
        self.assertFalse(family_rows.empty)

    def test_calibrate_prediction_weights_family_not_ready_keeps_global_weight(self) -> None:
        custom_weights = json.loads(json.dumps(self.weights))
        custom_weights["calibration"]["family_enabled"] = True
        custom_weights["calibration"]["family_min_samples"] = 3
        custom_weights["calibration"]["family_min_per_direction"] = 2

        history = pd.DataFrame(
            [
                {"ticker": "B1", "asset_family": "bond", "run_date": "2026-04-20", "outcome": "up", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "B2", "asset_family": "bond", "run_date": "2026-04-21", "outcome": "up", "signal_votes": "{\"rsi\": 1}"},
                {"ticker": "B3", "asset_family": "bond", "run_date": "2026-04-22", "outcome": "down", "signal_votes": "{\"rsi\": -1}"},
            ]
        )

        updated, summary = calibrate_prediction_weights(history, custom_weights)
        bond_rsi = summary.loc[
            (summary["scope"] == "family")
            & (summary["asset_family"] == "bond")
            & (summary["signal"] == "rsi")
        ].iloc[0]
        self.assertEqual(bond_rsi["status"], "family_insufficient_samples")
        self.assertFalse(bool(bond_rsi["family_ready"]))
        self.assertAlmostEqual(
            float(updated["family_overrides"]["bond"]["signals"]["rsi"]["weight"]),
            float(custom_weights["signals"]["rsi"]["weight"]),
            places=6,
        )


if __name__ == "__main__":
    unittest.main()
