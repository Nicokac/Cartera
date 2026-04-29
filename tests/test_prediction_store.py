import json
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from prediction.store import (
    apply_prediction_history_retention,
    PREDICTION_HISTORY_COLUMNS,
    build_prediction_observation,
    load_prediction_history,
    resolve_prediction_outcome_date,
    save_prediction_history,
    upsert_prediction_history,
)


class PredictionStoreTests(unittest.TestCase):
    def test_build_prediction_observation_normalizes_prediction_rows(self) -> None:
        predictions = pd.DataFrame(
            [
                {
                    "ticker": "aapl",
                    "direction": "up",
                    "confidence": 0.62,
                    "consensus_raw": 0.62,
                    "signal_votes": {"rsi": 1, "momentum_20d": 1, "sma_trend": -1},
                },
                {
                    "ticker": "msft",
                    "direction": "",
                    "confidence": 0.0,
                    "consensus_raw": 0.0,
                    "signal_votes": None,
                },
            ]
        )

        observation = build_prediction_observation(
            predictions,
            run_date="2026-04-20 15:30:00",
            horizon_days=5,
        )

        self.assertEqual(observation.columns.tolist(), PREDICTION_HISTORY_COLUMNS)
        self.assertEqual(observation.loc[0, "ticker"], "AAPL")
        self.assertEqual(observation.loc[0, "run_date"], "2026-04-20")
        self.assertEqual(observation.loc[0, "outcome_date"], "2026-04-27")
        self.assertEqual(observation.loc[0, "horizon_days"], 5)
        self.assertEqual(observation.loc[1, "direction"], "neutral")
        self.assertEqual(observation.loc[1, "signal_votes"], "{}")
        self.assertEqual(json.loads(observation.loc[0, "signal_votes"]), {"momentum_20d": 1, "rsi": 1, "sma_trend": -1})

    def test_upsert_prediction_history_replaces_same_run_ticker_and_horizon(self) -> None:
        history = pd.DataFrame(
            [
                {
                    "run_date": "2026-04-20",
                    "ticker": "AAPL",
                    "direction": "up",
                    "confidence": 0.40,
                    "consensus_raw": 0.40,
                    "signal_votes": "{\"rsi\": 1}",
                    "horizon_days": 5,
                    "outcome_date": "2026-04-27",
                    "outcome": "",
                    "correct": None,
                }
            ]
        )
        observation = pd.DataFrame(
            [
                {
                    "run_date": "2026-04-20",
                    "ticker": "AAPL",
                    "direction": "down",
                    "confidence": 0.55,
                    "consensus_raw": -0.55,
                    "signal_votes": "{\"rsi\": -1}",
                    "horizon_days": 5,
                    "outcome_date": "2026-04-27",
                    "outcome": "",
                    "correct": None,
                },
                {
                    "run_date": "2026-04-20",
                    "ticker": "MSFT",
                    "direction": "neutral",
                    "confidence": 0.05,
                    "consensus_raw": 0.05,
                    "signal_votes": "{}",
                    "horizon_days": 5,
                    "outcome_date": "2026-04-27",
                    "outcome": "",
                    "correct": None,
                },
            ]
        )

        merged = upsert_prediction_history(history, observation)

        self.assertEqual(len(merged), 2)
        aapl = merged.loc[merged["ticker"] == "AAPL"].iloc[0]
        self.assertEqual(aapl["direction"], "down")
        self.assertAlmostEqual(float(aapl["confidence"]), 0.55, places=6)
        self.assertAlmostEqual(float(aapl["consensus_raw"]), -0.55, places=6)

    def test_save_and_load_prediction_history_roundtrip(self) -> None:
        path = ROOT / "tmp_prediction_history.csv"
        if path.exists():
            path.unlink()
        self.addCleanup(lambda: path.unlink() if path.exists() else None)

        history = pd.DataFrame(
            [
                {
                    "run_date": "2026-04-20",
                    "ticker": "AAPL",
                    "direction": "up",
                    "confidence": 0.61,
                    "consensus_raw": 0.61,
                    "signal_votes": "{\"rsi\": 1}",
                    "horizon_days": 5,
                    "outcome_date": "2026-04-27",
                    "outcome": "",
                    "correct": None,
                }
            ]
        )

        saved_path = save_prediction_history(history, path=path)
        loaded = load_prediction_history(path=saved_path)

        self.assertEqual(saved_path, path)
        self.assertEqual(loaded.columns.tolist(), PREDICTION_HISTORY_COLUMNS)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded.loc[0, "ticker"], "AAPL")

    def test_resolve_prediction_outcome_date_uses_business_days(self) -> None:
        self.assertEqual(resolve_prediction_outcome_date("2026-04-17", horizon_days=1), "2026-04-20")
        self.assertEqual(resolve_prediction_outcome_date("2026-04-17", horizon_days=5), "2026-04-24")

    def test_apply_prediction_history_retention_keeps_recent_rows(self) -> None:
        history = pd.DataFrame(
            [
                {
                    "run_date": "2026-01-01",
                    "ticker": "AAPL",
                    "direction": "up",
                    "confidence": 0.4,
                    "conviction_label": "media",
                    "consensus_raw": 0.4,
                    "signal_votes": "{}",
                    "horizon_days": 5,
                    "outcome_date": "2026-01-08",
                    "outcome": "",
                    "correct": None,
                },
                {
                    "run_date": "2026-04-20",
                    "ticker": "MSFT",
                    "direction": "down",
                    "confidence": 0.5,
                    "conviction_label": "media",
                    "consensus_raw": -0.5,
                    "signal_votes": "{}",
                    "horizon_days": 5,
                    "outcome_date": "2026-04-27",
                    "outcome": "",
                    "correct": None,
                },
            ]
        )

        retained = apply_prediction_history_retention(
            history,
            retention_days=90,
            today="2026-04-29",
        )

        self.assertEqual(len(retained), 1)
        self.assertEqual(retained.loc[0, "ticker"], "MSFT")

    def test_apply_prediction_history_retention_rejects_invalid_days(self) -> None:
        with self.assertRaises(ValueError):
            apply_prediction_history_retention(pd.DataFrame(columns=PREDICTION_HISTORY_COLUMNS), retention_days=0)


if __name__ == "__main__":
    unittest.main()
