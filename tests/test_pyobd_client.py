import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from clients.pyobd_client import get_bond_volume_context


class _FakePyOBD:
    def get_current_quote(self, ticker: str):
        if ticker == "GD30":
            return pd.DataFrame([{"symbol": "GD30", "tradeVolume": 1500000}])
        if ticker == "AL30":
            return [{"symbol": "AL30", "tradeVolume": 80000}]
        return pd.DataFrame()

    def get_daily_history(self, ticker: str, from_date: str, to_date: str):
        if ticker == "GD30":
            return pd.DataFrame(
                [
                    {"date": "2026-03-31", "volume": 1000000},
                    {"date": "2026-04-01", "volume": 1500000},
                ]
            )
        if ticker == "AL30":
            return [
                {"date": "2026-03-31", "Volume": 50000},
                {"date": "2026-04-01", "Volume": 80000},
            ]
        return pd.DataFrame()


class PyOBDClientTests(unittest.TestCase):
    def test_get_bond_volume_context_builds_volume_metrics(self) -> None:
        with patch("clients.pyobd_client._get_pyobd_client", return_value=_FakePyOBD()):
            df = get_bond_volume_context(["GD30", "AL30"])

        self.assertEqual(set(df["Ticker_IOL"].tolist()), {"GD30", "AL30"})
        gd30 = df.loc[df["Ticker_IOL"] == "GD30"].iloc[0]
        al30 = df.loc[df["Ticker_IOL"] == "AL30"].iloc[0]

        self.assertAlmostEqual(gd30["bonistas_volume_last"], 1500000.0, places=2)
        self.assertAlmostEqual(gd30["bonistas_volume_avg_20d"], 1250000.0, places=2)
        self.assertAlmostEqual(gd30["bonistas_volume_ratio"], 1.2, places=2)
        self.assertEqual(gd30["bonistas_liquidity_bucket"], "alta")
        self.assertEqual(al30["bonistas_liquidity_bucket"], "baja")
        self.assertAlmostEqual(al30["bonistas_volume_last"], 80000.0, places=2)


if __name__ == "__main__":
    unittest.main()
