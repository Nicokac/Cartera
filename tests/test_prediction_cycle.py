import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from run_prediction_cycle import run_prediction_cycle


class PredictionCycleTests(unittest.TestCase):
    def test_run_prediction_cycle_verifies_and_recalibrates_history(self) -> None:
        history = pd.DataFrame(
            [
                {
                    "run_date": "2026-04-16",
                    "ticker": "XLV",
                    "direction": "up",
                    "confidence": 0.7,
                    "consensus_raw": 0.7,
                    "signal_votes": "{\"rsi\": 1}",
                    "horizon_days": 5,
                    "outcome_date": "2026-04-24",
                    "outcome": "",
                    "correct": pd.NA,
                }
            ]
        )
        verified = history.copy()
        verified.loc[0, "outcome"] = "up"
        verified.loc[0, "correct"] = True
        calibration_summary = pd.DataFrame(
            [
                {
                    "signal": "rsi",
                    "samples": 30,
                    "ic": 0.4,
                    "previous_weight": 0.8,
                    "new_weight": 0.4,
                    "status": "recalibrated",
                }
            ]
        )

        with patch("run_prediction_cycle.load_prediction_history", return_value=history), patch(
            "run_prediction_cycle.verify_prediction_history",
            return_value=verified,
        ) as verify_mock, patch(
            "run_prediction_cycle.apply_prediction_history_retention",
            return_value=verified,
        ) as retention_mock, patch(
            "run_prediction_cycle.calibrate_prediction_weights",
            return_value=({"signals": {"rsi": {"weight": 0.4}}}, calibration_summary),
        ) as calibrate_mock, patch("run_prediction_cycle.save_prediction_history") as save_history_mock, patch(
            "run_prediction_cycle.save_prediction_weights"
        ) as save_weights_mock:
            result = run_prediction_cycle(today="2026-04-24")

        verify_mock.assert_called_once()
        retention_mock.assert_called_once()
        calibrate_mock.assert_called_once()
        save_history_mock.assert_called_once_with(verified)
        save_weights_mock.assert_called_once()
        self.assertEqual(result["history_rows"], 1)
        self.assertEqual(result["completed_rows"], 1)
        self.assertEqual(result["pending_rows"], 0)
        self.assertEqual(result["recalibrated_signals"], 1)


if __name__ == "__main__":
    unittest.main()
