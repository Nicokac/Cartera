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
        n = 260
        close = pd.Series(np.linspace(100, 140, n))
        high = close * 1.01
        low = close * 0.99
        open_ = close * 0.995
        volume = pd.Series(np.linspace(1_000_000, 2_000_000, n))
        hist = pd.DataFrame({"Close": close, "High": high, "Low": low, "Open": open_, "Volume": volume})

        with patch("analytics.technical.fetch_price_history", return_value=hist):
            out = build_technical_overlay(df_cedears)

        self.assertEqual(len(out), 1)
        row = out.iloc[0]
        for col in ["SMA_200", "Dist_SMA200_%", "High_52w", "Low_52w", "Dist_52w_High_%", "Dist_52w_Low_%", "Avg_Volume_20d"]:
            self.assertIn(col, out.columns)
            self.assertTrue(pd.notna(row[col]), f"{col} should be non-null")
        for col in ["ADX_14", "DI_plus_14", "DI_minus_14", "Relative_Volume", "Return_1d_%", "Return_intraday_%"]:
            self.assertIn(col, out.columns)
            self.assertTrue(pd.notna(row[col]), f"{col} should be non-null with valid OHLCV data")

    def test_build_technical_overlay_returns_nan_for_adx_when_high_low_missing(self) -> None:
        df_cedears = pd.DataFrame([{"Ticker_IOL": "AAPL", "Ticker_Finviz": "AAPL"}])
        close = pd.Series(np.linspace(100, 140, 260))
        volume = pd.Series(np.ones(260) * 1_000_000)
        hist = pd.DataFrame({"Close": close, "Volume": volume})

        with patch("analytics.technical.fetch_price_history", return_value=hist):
            out = build_technical_overlay(df_cedears)

        row = out.iloc[0]
        self.assertTrue(pd.isna(row["ADX_14"]))
        self.assertTrue(pd.isna(row["DI_plus_14"]))
        self.assertTrue(pd.isna(row["DI_minus_14"]))

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
