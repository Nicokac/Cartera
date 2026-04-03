import math
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from analytics.dashboard import build_executive_dashboard_data


class DashboardKpiTests(unittest.TestCase):
    def test_dashboard_exposes_iol_style_total_without_usd_liquidity(self) -> None:
        df_total = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "SPY",
                    "Tipo": "CEDEAR",
                    "Bloque": "Core",
                    "Moneda": "ARS",
                    "Valorizado_ARS": 1000.0,
                    "Valor_USD": 1.0,
                    "Ganancia_ARS": 100.0,
                    "PPC_ARS": 900.0,
                    "Cantidad_Real": 1.0,
                    "Peso_%": 50.0,
                },
                {
                    "Ticker_IOL": "CASH_USD",
                    "Tipo": "Liquidez",
                    "Bloque": "Liquidez",
                    "Moneda": "USD",
                    "Valorizado_ARS": 500.0,
                    "Valor_USD": 0.5,
                    "Ganancia_ARS": 0.0,
                    "PPC_ARS": None,
                    "Cantidad_Real": None,
                    "Peso_%": 25.0,
                },
                {
                    "Ticker_IOL": "CAUCION",
                    "Tipo": "Liquidez",
                    "Bloque": "Liquidez",
                    "Moneda": "ARS",
                    "Valorizado_ARS": 500.0,
                    "Valor_USD": 0.5,
                    "Ganancia_ARS": 0.0,
                    "PPC_ARS": None,
                    "Cantidad_Real": None,
                    "Peso_%": 25.0,
                },
            ]
        )

        bundle = build_executive_dashboard_data(df_total, mep_real=1000.0)
        kpis = bundle["kpis"]

        self.assertTrue(math.isclose(kpis["total_ars"], 2000.0, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(kpis["liquidez_usd_ars"], 500.0, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(kpis["total_ars_iol"], 1500.0, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(kpis["liquidez_ars_iol"], 500.0, rel_tol=0, abs_tol=0.01))


if __name__ == "__main__":
    unittest.main()
