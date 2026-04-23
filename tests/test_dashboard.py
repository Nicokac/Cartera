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
        self.assertTrue(math.isclose(kpis["liquidez_broker_ars"], 1000.0, rel_tol=0, abs_tol=0.01))

    def test_dashboard_prioritizes_broker_total_when_estado_cuenta_is_available(self) -> None:
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
            ]
        )

        bundle = build_executive_dashboard_data(df_total, mep_real=1000.0, broker_total_ars=1750.0)
        kpis = bundle["kpis"]

        self.assertTrue(math.isclose(kpis["total_ars_model"], 1500.0, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(kpis["total_ars"], 1750.0, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(kpis["total_ars_iol"], 1250.0, rel_tol=0, abs_tol=0.01))

    def test_dashboard_exposes_broker_cash_when_available(self) -> None:
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
                {
                    "Ticker_IOL": "ADBAICA",
                    "Tipo": "Liquidez",
                    "Bloque": "Liquidez",
                    "Moneda": "ARS",
                    "Valorizado_ARS": 250.0,
                    "Valor_USD": 0.25,
                    "Ganancia_ARS": 0.0,
                    "PPC_ARS": None,
                    "Cantidad_Real": None,
                    "Peso_%": 12.5,
                },
            ]
        )

        bundle = build_executive_dashboard_data(
            df_total,
            mep_real=1000.0,
            broker_total_ars=1750.0,
            broker_cash_ars=300.0,
            broker_cash_committed_ars=50.0,
        )
        kpis = bundle["kpis"]

        self.assertTrue(math.isclose(kpis["liquidez_ars"], 750.0, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(kpis["liquidez_broker_ars"], 300.0, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(kpis["liquidez_broker_comprometida_ars"], 50.0, rel_tol=0, abs_tol=0.01))

    def test_dashboard_does_not_count_fci_as_liquidity_without_explicit_flag(self) -> None:
        df_total = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "IOLPORA",
                    "Tipo": "FCI",
                    "Bloque": "FCI",
                    "Moneda": "ARS",
                    "Valorizado_ARS": 800.0,
                    "Valor_USD": 0.8,
                    "Ganancia_ARS": 80.0,
                    "PPC_ARS": None,
                    "Cantidad_Real": None,
                    "Peso_%": 40.0,
                    "Es_Liquidez": False,
                },
                {
                    "Ticker_IOL": "CAUCION",
                    "Tipo": "Liquidez",
                    "Bloque": "Liquidez",
                    "Moneda": "ARS",
                    "Valorizado_ARS": 200.0,
                    "Valor_USD": 0.2,
                    "Ganancia_ARS": 0.0,
                    "PPC_ARS": None,
                    "Cantidad_Real": None,
                    "Peso_%": 10.0,
                    "Es_Liquidez": True,
                },
            ]
        )

        bundle = build_executive_dashboard_data(df_total, mep_real=1000.0)
        kpis = bundle["kpis"]

        self.assertTrue(math.isclose(kpis["invertido_ars"], 800.0, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(kpis["liquidez_ars"], 200.0, rel_tol=0, abs_tol=0.01))

    def test_dashboard_handles_object_dtype_liquidity_flags(self) -> None:
        df_total = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "IOLPORA",
                    "Tipo": "FCI",
                    "Bloque": "FCI",
                    "Moneda": "ARS",
                    "Valorizado_ARS": 800.0,
                    "Valor_USD": 0.8,
                    "Ganancia_ARS": 80.0,
                    "PPC_ARS": None,
                    "Cantidad_Real": None,
                    "Peso_%": 80.0,
                    "Es_Liquidez": False,
                },
                {
                    "Ticker_IOL": "CAUCION",
                    "Tipo": "Liquidez",
                    "Bloque": "Liquidez",
                    "Moneda": "ARS",
                    "Valorizado_ARS": 200.0,
                    "Valor_USD": 0.2,
                    "Ganancia_ARS": 0.0,
                    "PPC_ARS": None,
                    "Cantidad_Real": None,
                    "Peso_%": 20.0,
                    "Es_Liquidez": True,
                },
            ]
        )
        df_total["Es_Liquidez"] = df_total["Es_Liquidez"].astype(object)

        bundle = build_executive_dashboard_data(df_total, mep_real=1000.0)
        kpis = bundle["kpis"]

        self.assertTrue(math.isclose(kpis["invertido_ars"], 800.0, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(kpis["liquidez_ars"], 200.0, rel_tol=0, abs_tol=0.01))


if __name__ == "__main__":
    unittest.main()
