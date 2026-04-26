import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from decision.actions import assign_action_v2, assign_base_action, enrich_decision_explanations
from decision.scoring import (
    apply_base_scores,
    apply_technical_overlay_scores,
    build_market_regime_summary,
    build_decision_base,
    build_technical_overlay_scores,
    consensus_to_score,
    rank_score,
)
class StrategyRulesTaxonomyTests(unittest.TestCase):
    def test_asset_taxonomy_is_propagated_to_decision_base(self) -> None:
        df_total = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "SPY",
                    "Tipo": "CEDEAR",
                    "Bloque": "Core",
                    "Peso_%": 4.8,
                    "Valorizado_ARS": 1000.0,
                    "Valor_USD": 1.0,
                    "Ganancia_ARS": 50.0,
                    "Cantidad_Real": 1.0,
                    "PPC_ARS": 950.0,
                },
                {
                    "Ticker_IOL": "KO",
                    "Tipo": "CEDEAR",
                    "Bloque": "Dividendos",
                    "Peso_%": 2.0,
                    "Valorizado_ARS": 1000.0,
                    "Valor_USD": 1.0,
                    "Ganancia_ARS": 50.0,
                    "Cantidad_Real": 1.0,
                    "PPC_ARS": 950.0,
                },
                {
                    "Ticker_IOL": "GD30",
                    "Tipo": "Bono",
                    "Bloque": "Soberano AR",
                    "Peso_%": 3.0,
                    "Valorizado_ARS": 1000.0,
                    "Valor_USD": 1.0,
                    "Ganancia_ARS": 50.0,
                    "Cantidad_Real": 1.0,
                    "PPC_ARS": 950.0,
                },
                {
                    "Ticker_IOL": "CAUCION",
                    "Tipo": "Liquidez",
                    "Bloque": "Liquidez",
                    "Peso_%": 10.0,
                    "Valorizado_ARS": 1000.0,
                    "Valor_USD": 1.0,
                    "Ganancia_ARS": 0.0,
                    "Cantidad_Real": 1.0,
                    "PPC_ARS": 1.0,
                },
            ]
        )
        df_cedears = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "SPY",
                    "Ticker_Finviz": "SPY",
                    "asset_family": "etf",
                    "asset_subfamily": "etf_core",
                    "is_etf": True,
                    "is_core_etf": True,
                },
                {
                    "Ticker_IOL": "KO",
                    "Ticker_Finviz": "KO",
                    "asset_family": None,
                    "asset_subfamily": None,
                    "is_etf": False,
                    "is_core_etf": False,
                },
            ]
        )

        decision = build_decision_base(df_total, df_cedears, pd.DataFrame(), mep_real=1000.0)

        spy = decision.loc[decision["Ticker_IOL"] == "SPY"].iloc[0]
        ko = decision.loc[decision["Ticker_IOL"] == "KO"].iloc[0]
        gd30 = decision.loc[decision["Ticker_IOL"] == "GD30"].iloc[0]
        caucion = decision.loc[decision["Ticker_IOL"] == "CAUCION"].iloc[0]

        self.assertEqual(spy["asset_family"], "etf")
        self.assertEqual(spy["asset_subfamily"], "etf_core")
        self.assertEqual(ko["asset_family"], "stock")
        self.assertEqual(ko["asset_subfamily"], "stock_defensive_dividend")
        self.assertEqual(gd30["asset_family"], "bond")
        self.assertEqual(gd30["asset_subfamily"], "bond_sov_ar")
        self.assertEqual(caucion["asset_family"], "liquidity")
        self.assertEqual(caucion["asset_subfamily"], "liquidity_other")


    def test_stock_taxonomy_assigns_subfamily_from_block(self) -> None:
        df_total = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AAPL",
                    "Tipo": "CEDEAR",
                    "Bloque": "Growth",
                    "Peso_%": 4.0,
                    "Valorizado_ARS": 1000.0,
                    "Valor_USD": 1.0,
                    "Ganancia_ARS": 50.0,
                    "Cantidad_Real": 1.0,
                    "PPC_ARS": 950.0,
                },
                {
                    "Ticker_IOL": "KO",
                    "Tipo": "CEDEAR",
                    "Bloque": "Dividendos",
                    "Peso_%": 2.0,
                    "Valorizado_ARS": 1000.0,
                    "Valor_USD": 1.0,
                    "Ganancia_ARS": 50.0,
                    "Cantidad_Real": 1.0,
                    "PPC_ARS": 950.0,
                },
                {
                    "Ticker_IOL": "VIST",
                    "Tipo": "CEDEAR",
                    "Bloque": "Commodities",
                    "Peso_%": 1.2,
                    "Valorizado_ARS": 1000.0,
                    "Valor_USD": 1.0,
                    "Ganancia_ARS": 50.0,
                    "Cantidad_Real": 1.0,
                    "PPC_ARS": 950.0,
                },
                {
                    "Ticker_IOL": "LOMA",
                    "Tipo": "Acción Local",
                    "Bloque": "Argentina",
                    "Peso_%": 1.0,
                    "Valorizado_ARS": 1000.0,
                    "Valor_USD": 1.0,
                    "Ganancia_ARS": 50.0,
                    "Cantidad_Real": 1.0,
                    "PPC_ARS": 950.0,
                },
            ]
        )
        df_cedears = pd.DataFrame(
            [
                {"Ticker_IOL": "AAPL", "Ticker_Finviz": "AAPL", "is_etf": False, "is_core_etf": False},
                {"Ticker_IOL": "KO", "Ticker_Finviz": "KO", "is_etf": False, "is_core_etf": False},
                {"Ticker_IOL": "VIST", "Ticker_Finviz": "VIST", "is_etf": False, "is_core_etf": False},
            ]
        )

        decision = build_decision_base(df_total, df_cedears, pd.DataFrame(), mep_real=1000.0)
        mapping = dict(zip(decision["Ticker_IOL"], decision["asset_subfamily"]))

        self.assertEqual(mapping["AAPL"], "stock_growth")
        self.assertEqual(mapping["KO"], "stock_defensive_dividend")
        self.assertEqual(mapping["VIST"], "stock_commodity")
        self.assertEqual(mapping["LOMA"], "stock_argentina")


    def test_bond_taxonomy_assigns_subfamily_from_block(self) -> None:
        df_total = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "GD30",
                    "Tipo": "Bono",
                    "Bloque": "Soberano AR",
                    "Peso_%": 3.0,
                    "Valorizado_ARS": 1000.0,
                    "Valor_USD": 1.0,
                    "Ganancia_ARS": 50.0,
                    "Cantidad_Real": 1.0,
                    "PPC_ARS": 950.0,
                },
                {
                    "Ticker_IOL": "TZX26",
                    "Tipo": "Bono",
                    "Bloque": "CER",
                    "Peso_%": 3.0,
                    "Valorizado_ARS": 1000.0,
                    "Valor_USD": 1.0,
                    "Ganancia_ARS": 50.0,
                    "Cantidad_Real": 1.0,
                    "PPC_ARS": 950.0,
                },
                {
                    "Ticker_IOL": "BPOC7",
                    "Tipo": "Bono",
                    "Bloque": "Bopreal",
                    "Peso_%": 3.0,
                    "Valorizado_ARS": 1000.0,
                    "Valor_USD": 1.0,
                    "Ganancia_ARS": 50.0,
                    "Cantidad_Real": 1.0,
                    "PPC_ARS": 950.0,
                },
                {
                    "Ticker_IOL": "TZXM7",
                    "Tipo": "Bono",
                    "Bloque": "Sin clasificar",
                    "Peso_%": 3.0,
                    "Valorizado_ARS": 1000.0,
                    "Valor_USD": 1.0,
                    "Ganancia_ARS": 50.0,
                    "Cantidad_Real": 1.0,
                    "PPC_ARS": 950.0,
                },
            ]
        )

        decision = build_decision_base(df_total, pd.DataFrame(), pd.DataFrame(), mep_real=1000.0)

        mapping = dict(zip(decision["Ticker_IOL"], decision["asset_subfamily"]))
        self.assertEqual(mapping["GD30"], "bond_sov_ar")
        self.assertEqual(mapping["TZX26"], "bond_cer")
        self.assertEqual(mapping["BPOC7"], "bond_bopreal")
        self.assertEqual(mapping["TZXM7"], "bond_other")


    def test_build_decision_base_handles_empty_portfolio_master_without_required_columns(self) -> None:
        decision = build_decision_base(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), mep_real=1000.0)

        self.assertTrue(decision.empty)
        self.assertIn("Ticker_IOL", decision.columns)
        self.assertIn("Tipo", decision.columns)
        self.assertIn("Peso_%", decision.columns)
        self.assertIn("Consensus_Final", decision.columns)


    def test_country_region_etf_needs_more_support_for_refuerzo(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "EWZ",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Es_ETF": True,
                    "Es_Core_ETF": False,
                    "asset_subfamily": "etf_country_region",
                    "Peso_%": 1.9,
                    "Perf Week": 4.0,
                    "Perf Month": 2.0,
                    "Perf YTD": 20.0,
                    "Beta": 0.7,
                    "P/E": None,
                    "ROE": None,
                    "Profit Margin": None,
                    "MEP_Premium_%": -98.0,
                    "Consensus_Final": 0.5,
                    "Ganancia_%": 30.0,
                    "Ganancia_ARS": 100.0,
                    "total_ratings": 0.0,
                },
                {
                    "Ticker_IOL": "XLU",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Es_ETF": True,
                    "Es_Core_ETF": False,
                    "asset_subfamily": "etf_sector",
                    "Peso_%": 1.9,
                    "Perf Week": 4.0,
                    "Perf Month": 2.0,
                    "Perf YTD": 20.0,
                    "Beta": 0.7,
                    "P/E": None,
                    "ROE": None,
                    "Profit Margin": None,
                    "MEP_Premium_%": -98.0,
                    "Consensus_Final": 0.5,
                    "Ganancia_%": 30.0,
                    "Ganancia_ARS": 100.0,
                    "total_ratings": 0.0,
                },
            ]
        )

        scored = apply_base_scores(
            df,
            scoring_rules={
                "score_refuerzo_weights": {
                    "low_weight": 0.16,
                    "momentum": 0.18,
                    "consensus_good": 0.14,
                    "beta_ok": 0.08,
                    "mep_ok": 0.08,
                    "pe_ok": 0.08,
                    "big_gain_inverse": 0.08,
                    "concentration_room": 0.1,
                    "quality": 0.1,
                },
                "etf_adjustments": {
                    "quality_floor": 0.55,
                    "pe_expensive_discount": 0.4,
                    "low_quality_discount": 0.35,
                    "concentration_pressure_discount": 0.85,
                    "core_concentration_pressure_discount": 0.65,
                    "core_momentum_reduccion_discount": 0.85,
                },
                "asset_subfamily_adjustments": {
                    "etf_country_region": {"refuerzo_penalty": 0.03, "sparse_data_penalty": 0.03},
                    "etf_sector": {"refuerzo_penalty": 0.0, "sparse_data_penalty": 0.0},
                },
            },
        )

        self.assertLess(scored.loc[0, "score_refuerzo"], scored.loc[1, "score_refuerzo"])


    def test_bond_other_gets_less_refuerzo_than_similar_sov_bond(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "TZXM7",
                    "Es_Liquidez": False,
                    "Es_Bono": True,
                    "asset_subfamily": "bond_other",
                    "Peso_%": 0.6,
                    "Perf Week": None,
                    "Perf Month": None,
                    "Perf YTD": None,
                    "Beta": None,
                    "P/E": None,
                    "ROE": None,
                    "Profit Margin": None,
                    "MEP_Premium_%": None,
                    "Consensus_Final": 0.5,
                    "Ganancia_%": 0.2,
                    "Ganancia_ARS": 100.0,
                },
                {
                    "Ticker_IOL": "GD35",
                    "Es_Liquidez": False,
                    "Es_Bono": True,
                    "asset_subfamily": "bond_sov_ar",
                    "Peso_%": 0.6,
                    "Perf Week": None,
                    "Perf Month": None,
                    "Perf YTD": None,
                    "Beta": None,
                    "P/E": None,
                    "ROE": None,
                    "Profit Margin": None,
                    "MEP_Premium_%": None,
                    "Consensus_Final": 0.5,
                    "Ganancia_%": 0.2,
                    "Ganancia_ARS": 100.0,
                },
            ]
        )

        scored = apply_base_scores(
            df,
            scoring_rules={
                "asset_subfamily_adjustments": {
                    "bond_other": {
                        "refuerzo_penalty": 0.07,
                        "sparse_data_penalty": 0.02,
                        "reduccion_boost": 0.02,
                    },
                    "bond_sov_ar": {"refuerzo_penalty": 0.0},
                }
            },
        )

        self.assertLess(scored.loc[0, "score_refuerzo"], scored.loc[1, "score_refuerzo"])
        self.assertGreater(scored.loc[0, "score_reduccion"], scored.loc[1, "score_reduccion"])


    def test_sov_bond_with_extended_gain_gets_extra_reduction_pressure(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "GD30",
                    "Es_Liquidez": False,
                    "Es_Bono": True,
                    "asset_subfamily": "bond_sov_ar",
                    "Peso_%": 3.6,
                    "Perf Week": None,
                    "Perf Month": None,
                    "Perf YTD": None,
                    "Beta": None,
                    "P/E": None,
                    "ROE": None,
                    "Profit Margin": None,
                    "MEP_Premium_%": None,
                    "Consensus_Final": 0.5,
                    "Ganancia_%": 150.0,
                    "Ganancia_ARS": 1000.0,
                },
                {
                    "Ticker_IOL": "AL30",
                    "Es_Liquidez": False,
                    "Es_Bono": True,
                    "asset_subfamily": "bond_sov_ar",
                    "Peso_%": 3.6,
                    "Perf Week": None,
                    "Perf Month": None,
                    "Perf YTD": None,
                    "Beta": None,
                    "P/E": None,
                    "ROE": None,
                    "Profit Margin": None,
                    "MEP_Premium_%": None,
                    "Consensus_Final": 0.5,
                    "Ganancia_%": 20.0,
                    "Ganancia_ARS": 1000.0,
                },
            ]
        )

        scored = apply_base_scores(
            df,
            scoring_rules={
                "asset_subfamily_adjustments": {
                    "bond_sov_ar": {
                        "reduccion_boost": 0.02,
                        "high_gain_reduccion_boost": 0.05,
                        "high_gain_threshold_pct": 80.0,
                    }
                }
            },
        )

        self.assertGreater(scored.loc[0, "score_reduccion"], scored.loc[1, "score_reduccion"])


    def test_stock_subfamily_adjustments_make_growth_more_demanding_than_defensive(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AMD",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Es_ETF": False,
                    "Es_Core_ETF": False,
                    "asset_subfamily": "stock_growth",
                    "Peso_%": 1.0,
                    "Perf Week": 3.0,
                    "Perf Month": 5.0,
                    "Perf YTD": 8.0,
                    "Beta": 0.75,
                    "P/E": 18.0,
                    "ROE": 20.0,
                    "Profit Margin": 18.0,
                    "MEP_Premium_%": -98.0,
                    "Consensus_Final": 0.7,
                    "Ganancia_%": 20.0,
                    "Ganancia_ARS": 100.0,
                    "total_ratings": 10.0,
                },
                {
                    "Ticker_IOL": "KO",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Es_ETF": False,
                    "Es_Core_ETF": False,
                    "asset_subfamily": "stock_defensive_dividend",
                    "Peso_%": 1.0,
                    "Perf Week": 3.0,
                    "Perf Month": 5.0,
                    "Perf YTD": 8.0,
                    "Beta": 0.75,
                    "P/E": 18.0,
                    "ROE": 20.0,
                    "Profit Margin": 18.0,
                    "MEP_Premium_%": -98.0,
                    "Consensus_Final": 0.7,
                    "Ganancia_%": 20.0,
                    "Ganancia_ARS": 100.0,
                    "total_ratings": 10.0,
                },
            ]
        )

        scored = apply_base_scores(
            df,
            scoring_rules={
                "asset_subfamily_adjustments": {
                    "stock_growth": {"refuerzo_penalty": 0.02, "reduccion_boost": 0.02},
                    "stock_defensive_dividend": {"refuerzo_boost": 0.02, "reduccion_boost": -0.02},
                }
            },
        )

        self.assertLess(scored.loc[0, "score_refuerzo"], scored.loc[1, "score_refuerzo"])
        self.assertGreater(scored.loc[0, "score_reduccion"], scored.loc[1, "score_reduccion"])


if __name__ == "__main__":
    unittest.main()

