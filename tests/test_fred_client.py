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

from clients.fred_client import get_ust_latest, get_ust_series


class _FakeFred:
    def __init__(self, *, api_key: str) -> None:
        self.api_key = api_key

    def get_series(self, series_id: str) -> pd.Series:
        idx = pd.to_datetime(["2026-04-03", "2026-04-04"])
        if series_id == "DGS5":
            return pd.Series([4.01, 4.05], index=idx)
        if series_id == "DGS10":
            return pd.Series([4.22, 4.25], index=idx)
        return pd.Series(dtype=float)


class FredClientTests(unittest.TestCase):
    def test_get_ust_series_builds_dataframe_and_spread(self) -> None:
        fake_module = types.SimpleNamespace(Fred=_FakeFred)

        with patch.dict(sys.modules, {"fredapi": fake_module}), patch.dict("os.environ", {"FRED_API_KEY": "demo-key"}, clear=False):
            df = get_ust_series()

        self.assertEqual(df.iloc[-1]["ust_5y_pct"], 4.05)
        self.assertEqual(df.iloc[-1]["ust_10y_pct"], 4.25)
        self.assertAlmostEqual(df.iloc[-1]["ust_spread_10y_5y_pct"], 0.20, places=2)

    def test_get_ust_latest_returns_last_observation_payload(self) -> None:
        fake_module = types.SimpleNamespace(Fred=_FakeFred)

        with patch.dict(sys.modules, {"fredapi": fake_module}), patch.dict("os.environ", {"FRED_API_KEY": "demo-key"}, clear=False):
            payload = get_ust_latest()

        self.assertIsNotNone(payload)
        self.assertEqual(payload["ust_date"], "2026-04-04")
        self.assertAlmostEqual(payload["ust_5y_pct"], 4.05, places=2)
        self.assertAlmostEqual(payload["ust_10y_pct"], 4.25, places=2)
        self.assertAlmostEqual(payload["ust_spread_10y_5y_pct"], 0.20, places=2)

    def test_get_ust_series_requires_api_key(self) -> None:
        fake_module = types.SimpleNamespace(Fred=_FakeFred)

        with patch.dict(sys.modules, {"fredapi": fake_module}), patch.dict("os.environ", {}, clear=True), patch(
            "clients.fred_client._load_local_env", return_value={}
        ):
            with self.assertRaises(ValueError):
                get_ust_series()

    def test_get_ust_latest_returns_none_when_series_are_empty(self) -> None:
        class _EmptyFred:
            def __init__(self, *, api_key: str) -> None:
                self.api_key = api_key

            def get_series(self, series_id: str) -> pd.Series:
                return pd.Series(dtype=float)

        fake_module = types.SimpleNamespace(Fred=_EmptyFred)

        with patch.dict(sys.modules, {"fredapi": fake_module}), patch.dict("os.environ", {"FRED_API_KEY": "demo-key"}, clear=False):
            payload = get_ust_latest()

        self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()
