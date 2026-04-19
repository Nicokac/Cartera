import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from prediction.verifier import (
    build_verification_period,
    classify_outcome,
    resolve_close_on_or_after,
    verify_prediction_history,
)


class PredictionVerifierTests(unittest.TestCase):
    def test_classify_outcome_supports_up_down_and_neutral_band(self) -> None:
        self.assertEqual(classify_outcome(0.02, neutral_return_band=0.01), "up")
        self.assertEqual(classify_outcome(-0.02, neutral_return_band=0.01), "down")
        self.assertEqual(classify_outcome(0.005, neutral_return_band=0.01), "neutral")

    def test_build_verification_period_adds_buffer_and_has_minimum_window(self) -> None:
        self.assertEqual(build_verification_period("2026-04-20", "2026-04-27"), "30d")
        self.assertEqual(build_verification_period("2026-01-01", "2026-03-15"), "83d")

    def test_resolve_close_on_or_after_uses_first_available_close(self) -> None:
        history = pd.DataFrame(
            {"Close": [100.0, 101.5, 103.0]},
            index=pd.to_datetime(["2026-04-20", "2026-04-22", "2026-04-23"]),
        )

        self.assertEqual(resolve_close_on_or_after(history, "2026-04-20"), 100.0)
        self.assertEqual(resolve_close_on_or_after(history, "2026-04-21"), 101.5)
        self.assertIsNone(resolve_close_on_or_after(history, "2026-04-24"))

    def test_verify_prediction_history_updates_up_down_and_neutral_outcomes(self) -> None:
        history = pd.DataFrame(
            [
                {
                    "run_date": "2026-04-20",
                    "ticker": "AAPL",
                    "direction": "up",
                    "confidence": 0.6,
                    "consensus_raw": 0.6,
                    "signal_votes": "{}",
                    "horizon_days": 5,
                    "outcome_date": "2026-04-27",
                    "outcome": "",
                    "correct": None,
                },
                {
                    "run_date": "2026-04-20",
                    "ticker": "MSFT",
                    "direction": "down",
                    "confidence": 0.7,
                    "consensus_raw": -0.7,
                    "signal_votes": "{}",
                    "horizon_days": 5,
                    "outcome_date": "2026-04-27",
                    "outcome": "",
                    "correct": None,
                },
                {
                    "run_date": "2026-04-20",
                    "ticker": "KO",
                    "direction": "neutral",
                    "confidence": 0.1,
                    "consensus_raw": 0.0,
                    "signal_votes": "{}",
                    "horizon_days": 5,
                    "outcome_date": "2026-04-27",
                    "outcome": "",
                    "correct": None,
                },
            ]
        )

        frames = {
            "AAPL": pd.DataFrame({"Close": [100.0, 103.0]}, index=pd.to_datetime(["2026-04-20", "2026-04-27"])),
            "MSFT": pd.DataFrame({"Close": [100.0, 97.0]}, index=pd.to_datetime(["2026-04-20", "2026-04-27"])),
            "KO": pd.DataFrame({"Close": [100.0, 100.5]}, index=pd.to_datetime(["2026-04-20", "2026-04-27"])),
        }

        def fake_fetcher(ticker: str, **kwargs) -> pd.DataFrame:
            return frames[ticker]

        verified = verify_prediction_history(
            history,
            today="2026-04-28",
            neutral_return_band=0.01,
            price_fetcher=fake_fetcher,
        )

        aapl = verified.loc[verified["ticker"] == "AAPL"].iloc[0]
        msft = verified.loc[verified["ticker"] == "MSFT"].iloc[0]
        ko = verified.loc[verified["ticker"] == "KO"].iloc[0]

        self.assertEqual(aapl["outcome"], "up")
        self.assertTrue(bool(aapl["correct"]))
        self.assertEqual(msft["outcome"], "down")
        self.assertTrue(bool(msft["correct"]))
        self.assertEqual(ko["outcome"], "neutral")
        self.assertTrue(bool(ko["correct"]))

    def test_verify_prediction_history_leaves_pending_when_price_is_missing_or_not_due(self) -> None:
        history = pd.DataFrame(
            [
                {
                    "run_date": "2026-04-20",
                    "ticker": "AAPL",
                    "direction": "up",
                    "confidence": 0.6,
                    "consensus_raw": 0.6,
                    "signal_votes": "{}",
                    "horizon_days": 5,
                    "outcome_date": "2026-04-27",
                    "outcome": "",
                    "correct": None,
                },
                {
                    "run_date": "2026-04-20",
                    "ticker": "MSFT",
                    "direction": "down",
                    "confidence": 0.6,
                    "consensus_raw": -0.6,
                    "signal_votes": "{}",
                    "horizon_days": 5,
                    "outcome_date": "2026-05-01",
                    "outcome": "",
                    "correct": None,
                },
            ]
        )

        frames = {
            "AAPL": pd.DataFrame({"Close": [100.0]}, index=pd.to_datetime(["2026-04-20"])),
        }

        def fake_fetcher(ticker: str, **kwargs) -> pd.DataFrame:
            return frames.get(ticker, pd.DataFrame())

        verified = verify_prediction_history(
            history,
            today="2026-04-28",
            neutral_return_band=0.01,
            price_fetcher=fake_fetcher,
        )

        aapl = verified.loc[verified["ticker"] == "AAPL"].iloc[0]
        msft = verified.loc[verified["ticker"] == "MSFT"].iloc[0]

        self.assertEqual(aapl["outcome"], "")
        self.assertTrue(pd.isna(aapl["correct"]))
        self.assertEqual(msft["outcome"], "")
        self.assertTrue(pd.isna(msft["correct"]))


if __name__ == "__main__":
    unittest.main()
