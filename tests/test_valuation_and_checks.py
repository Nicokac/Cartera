import warnings
import math
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from portfolio.checks import build_integrity_report
from portfolio.valuation import build_bonos_df, build_cedears_df, build_local_df, build_portfolio_master


class ValuationAndChecksTests(unittest.TestCase):
    def test_build_cedears_df_returns_zero_weight_when_total_is_zero(self) -> None:
        df_cedears = build_cedears_df(
            [("AAPL", "AAPL", "Tecnologia", 2, 1000)],
            {"AAPL": 0},
            ratios={"AAPL": 10},
        )

        self.assertEqual(float(df_cedears.loc[0, "Valorizado_ARS"]), 0.0)
        self.assertEqual(float(df_cedears.loc[0, "Peso_%"]), 0.0)

    def test_build_portfolio_master_recomputes_weight_over_all_assets(self) -> None:
        df_cedears = build_cedears_df(
            [("AAPL", "AAPL", "Tecnologia", 2, 1000)],
            {"AAPL": 1500},
            ratios={"AAPL": 10},
        )
        df_local = build_local_df(
            [("GGAL", "GGAL", "Finanzas", 10, 100)],
            {"GGAL": 120},
        )
        df_bonos = build_bonos_df(
            [("GD30", "Bonos", 1000, 80, 100)],
            {"GD30": 95},
        )
        df_liquidez = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "CASH_ARS",
                    "Descripcion": "Cash disponible broker ARS",
                    "Bloque": "Liquidez",
                    "Tipo": "Liquidez",
                    "Moneda": "ARS",
                    "Valorizado_ARS": 500,
                    "Valor_USD": 0.5,
                    "Ganancia_ARS": 0.0,
                    "Cantidad": 0.0,
                    "Cantidad_Real": 0.0,
                    "PPC_ARS": 0.0,
                    "Precio_ARS": 0.0,
                }
            ]
        )

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="The behavior of DataFrame concatenation with empty or all-NA entries is deprecated.",
                category=FutureWarning,
            )
            df_total = build_portfolio_master(df_cedears, df_local, df_bonos, df_liquidez, mep_real=1000)

        self.assertEqual(len(df_total), 4)
        self.assertTrue(math.isclose(df_total["Peso_%"].sum(), 100.0, rel_tol=0, abs_tol=0.05))
        aapl = df_total[df_total["Ticker_IOL"] == "AAPL"].iloc[0]
        self.assertEqual(aapl["Valorizado_ARS"], 3000)
        self.assertEqual(aapl["Valor_USD"], 3)

    def test_build_integrity_report_warns_on_missing_price_and_bad_weight(self) -> None:
        df_total = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AAPL",
                    "Tipo": "CEDEAR",
                    "Valorizado_ARS": 1000,
                    "Valor_USD": 1,
                    "Peso_%": 80,
                    "Precio_ARS": None,
                },
                {
                    "Ticker_IOL": "CASH_ARS",
                    "Tipo": "Liquidez",
                    "Valorizado_ARS": 1000,
                    "Valor_USD": 1,
                    "Peso_%": 10,
                    "Precio_ARS": None,
                },
            ]
        )

        report_df, summary = build_integrity_report(df_total)

        self.assertEqual(summary["warn_count"], 2)
        self.assertIn("AAPL", summary["faltan_precios"])
        self.assertFalse(summary["peso_ok"])
        self.assertEqual(report_df.loc[report_df["check"] == "peso_total", "estado"].iloc[0], "WARN")

    def test_build_portfolio_master_returns_zero_weight_when_total_valorizado_is_zero(self) -> None:
        df_total = build_portfolio_master(
            pd.DataFrame([{"Ticker_IOL": "AAPL", "Tipo": "CEDEAR", "Valorizado_ARS": 0.0}]),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            mep_real=1000,
        )

        self.assertEqual(float(df_total.loc[0, "Peso_%"]), 0.0)


if __name__ == "__main__":
    unittest.main()
