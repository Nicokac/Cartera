import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from clients.market_data import _normalize_history_frame, fetch_price_history


class _FakeTicker:
    def __init__(self, data: pd.DataFrame) -> None:
        self._data = data

    def history(self, period: str, interval: str, auto_adjust: bool) -> pd.DataFrame:
        return self._data.copy()


class MarketDataClientTests(unittest.TestCase):
    def test_normalize_history_frame_handles_multiindex_columns(self) -> None:
        idx = pd.to_datetime(["2026-04-07", "2026-04-08"])
        data = pd.DataFrame(
            {
                ("Close", "SPY"): [100.0, 101.0],
                ("Open", "SPY"): [99.0, 100.0],
                ("Volume", "SPY"): [10, 20],
            },
            index=idx,
        )

        normalized = _normalize_history_frame(data, "SPY")

        self.assertEqual(list(normalized.columns), ["Close", "Open", "Volume"])
        self.assertEqual(normalized.iloc[-1]["Close"], 101.0)

    def test_fetch_price_history_uses_ticker_history_fallback(self) -> None:
        idx = pd.to_datetime(["2026-04-07", "2026-04-08"])
        fallback_df = pd.DataFrame(
            {
                "close": [50.0, 51.0],
                "open": [49.0, 50.0],
                "volume": [1000, 1200],
            },
            index=idx,
        )

        fake_yf = types.SimpleNamespace(
            download=lambda *args, **kwargs: pd.DataFrame(),
            Ticker=lambda ticker: _FakeTicker(fallback_df),
            set_tz_cache_location=lambda path: None,
        )

        with patch.dict(sys.modules, {"yfinance": fake_yf}):
            df = fetch_price_history("QQQ")

        self.assertFalse(df.empty)
        self.assertEqual(list(df.columns), ["Close", "Open", "Volume"])
        self.assertEqual(df.iloc[-1]["Close"], 51.0)

    def test_fetch_price_history_returns_empty_when_all_attempts_fail(self) -> None:
        fake_yf = types.SimpleNamespace(
            download=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("download failed")),
            Ticker=lambda ticker: _FakeTicker(pd.DataFrame()),
            set_tz_cache_location=lambda path: None,
        )

        with patch.dict(sys.modules, {"yfinance": fake_yf}):
            df = fetch_price_history("QQQ")

        self.assertTrue(df.empty)


if __name__ == "__main__":
    unittest.main()
