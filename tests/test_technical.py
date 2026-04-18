import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from analytics.technical import build_technical_overlay


class TechnicalOverlayTests(unittest.TestCase):
    def test_build_technical_overlay_exposes_yahoo_derived_market_metrics(self) -> None:
        df_cedears = pd.DataFrame(
            [
                {"Ticker_IOL": "AAPL", "Ticker_Finviz": "AAPL"},
            ]
        )
        close = pd.Series(np.linspace(100, 140, 260))
        volume = pd.Series(np.linspace(1_000_000, 2_000_000, 260))
        hist = pd.DataFrame({"Close": close, "Volume": volume})

        with patch("analytics.technical.fetch_price_history", return_value=hist):
            out = build_technical_overlay(df_cedears)

        self.assertEqual(len(out), 1)
        row = out.iloc[0]
        self.assertIn("SMA_200", out.columns)
        self.assertIn("Dist_SMA200_%", out.columns)
        self.assertIn("High_52w", out.columns)
        self.assertIn("Low_52w", out.columns)
        self.assertIn("Dist_52w_High_%", out.columns)
        self.assertIn("Dist_52w_Low_%", out.columns)
        self.assertIn("Avg_Volume_20d", out.columns)
        self.assertTrue(pd.notna(row["SMA_200"]))
        self.assertTrue(pd.notna(row["Dist_SMA200_%"]))
        self.assertTrue(pd.notna(row["High_52w"]))
        self.assertTrue(pd.notna(row["Low_52w"]))
        self.assertTrue(pd.notna(row["Dist_52w_High_%"]))
        self.assertTrue(pd.notna(row["Dist_52w_Low_%"]))
        self.assertTrue(pd.notna(row["Avg_Volume_20d"]))

    def test_build_technical_overlay_logs_failures_and_summary(self) -> None:
        df_cedears = pd.DataFrame([{"Ticker_IOL": "AAPL", "Ticker_Finviz": "AAPL"}])

        with patch("analytics.technical.fetch_price_history", side_effect=RuntimeError("boom")), patch(
            "analytics.technical.logger.warning"
        ) as warning_mock, patch("analytics.technical.logger.info") as info_mock:
            out = build_technical_overlay(df_cedears)

        self.assertEqual(out.loc[0, "Tech_Trend"], "Error: boom")
        warning_mock.assert_called_once()
        self.assertTrue(any("Technical overlay completed" in str(call.args[0]) for call in info_mock.call_args_list))


if __name__ == "__main__":
    unittest.main()
