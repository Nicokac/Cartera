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

from clients.finviz_client import fetch_finviz_bundle


class _FakeFinvizStock:
    def __init__(self, ticker: str) -> None:
        self.ticker = ticker

    def ticker_fundament(self):
        return {"P/E": 18.5, "ROE": 24.1}

    def ticker_outer_ratings(self):
        return pd.DataFrame([{"Date": "2026-04-08", "Rating": "Buy"}])

    def ticker_news(self):
        return pd.DataFrame([{"Date": "2026-04-08", "Headline": "Headline demo"}])

    def ticker_inside_trader(self):
        return pd.DataFrame([{"Date": "2026-04-08", "Insider": "Jane Doe"}])


class _FailingFinvizStock:
    def __init__(self, ticker: str) -> None:
        self.ticker = ticker

    def ticker_fundament(self):
        raise RuntimeError("fundamentals failed")

    def ticker_outer_ratings(self):
        raise RuntimeError("ratings failed")

    def ticker_news(self):
        raise RuntimeError("news failed")

    def ticker_inside_trader(self):
        raise RuntimeError("insiders failed")


class FinvizClientTests(unittest.TestCase):
    def test_fetch_finviz_bundle_returns_all_sections_when_source_works(self) -> None:
        fake_quote_module = types.SimpleNamespace(finvizfinance=_FakeFinvizStock)

        with patch.dict(sys.modules, {"finvizfinance.quote": fake_quote_module}):
            bundle = fetch_finviz_bundle("AAPL")

        self.assertEqual(bundle["ticker"], "AAPL")
        self.assertEqual(bundle["stock"].ticker, "AAPL")
        self.assertEqual(bundle["fundamentals"]["P/E"], 18.5)
        self.assertFalse(bundle["ratings"].empty)
        self.assertFalse(bundle["news"].empty)
        self.assertFalse(bundle["insiders"].empty)

    def test_fetch_finviz_bundle_falls_back_to_empty_sections_on_errors(self) -> None:
        fake_quote_module = types.SimpleNamespace(finvizfinance=_FailingFinvizStock)

        with patch.dict(sys.modules, {"finvizfinance.quote": fake_quote_module}):
            bundle = fetch_finviz_bundle("MSFT")

        self.assertEqual(bundle["ticker"], "MSFT")
        self.assertEqual(bundle["stock"].ticker, "MSFT")
        self.assertEqual(bundle["fundamentals"], {})
        self.assertTrue(bundle["ratings"].empty)
        self.assertTrue(bundle["news"].empty)
        self.assertTrue(bundle["insiders"].empty)


if __name__ == "__main__":
    unittest.main()
