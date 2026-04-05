import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from decision.actions import assign_action_v2, enrich_decision_explanations
from decision.scoring import (
    apply_base_scores,
    apply_technical_overlay_scores,
    build_decision_base,
    build_technical_overlay_scores,
    consensus_to_score,
)


class StrategyRulesTests(unittest.TestCase):
    def test_consensus_taxonomy_can_be_overridden_from_external_rules(self) -> None:
        default_score = consensus_to_score("accumulate")
        custom_score = consensus_to_score(
            "accumulate",
            scoring_rules={
                "consensus_taxonomy": {
                    "positive_terms": ["accumulate"],
                    "negative_terms": [],
                    "neutral_terms": [],
                }
            },
        )

        self.assertEqual(default_score, 0.5)
        self.assertEqual(custom_score, 1.0)

    def test_action_thresholds_can_be_overridden_from_external_rules(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "CRM",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "score_refuerzo_v2": 0.55,
                    "score_reduccion_v2": 0.20,
                    "score_despliegue_liquidez": 0.0,
                }
            ]
        )

        default_result = assign_action_v2(df)
        custom_result = assign_action_v2(
            df,
            action_rules={
                "refuerzo_threshold": 0.50,
                "reduccion_threshold": 0.60,
                "score_gap_min": 0.10,
                "despliegue_liquidez_threshold": 0.55,
            },
        )

        self.assertEqual(default_result.loc[0, "accion_sugerida_v2"], "Mantener / Neutral")
        self.assertEqual(custom_result.loc[0, "accion_sugerida_v2"], "Refuerzo")

    def test_block_label_no_longer_changes_scores(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "SPY",
                    "Bloque": "Core",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Peso_%": 4.0,
                    "Perf Week": 1.0,
                    "Perf Month": 2.0,
                    "Perf YTD": 3.0,
                    "Beta": 1.0,
                    "P/E": 20.0,
                    "MEP_Premium_%": 1.0,
                    "Consensus_Final": 0.5,
                    "Ganancia_%": 10.0,
                    "Ganancia_ARS": 100.0,
                },
                {
                    "Ticker_IOL": "SPY",
                    "Bloque": "Growth",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Peso_%": 4.0,
                    "Perf Week": 1.0,
                    "Perf Month": 2.0,
                    "Perf YTD": 3.0,
                    "Beta": 1.0,
                    "P/E": 20.0,
                    "MEP_Premium_%": 1.0,
                    "Consensus_Final": 0.5,
                    "Ganancia_%": 10.0,
                    "Ganancia_ARS": 100.0,
                },
            ]
        )

        scored = apply_base_scores(
            df,
            scoring_rules={
                "score_reduccion_weights": {
                    "high_weight": 0.2,
                    "momentum": 0.14,
                    "beta_risk": 0.14,
                    "mep_premium": 0.08,
                    "consensus_bad": 0.08,
                    "pe_expensive": 0.08,
                    "big_gain": 0.08,
                    "concentration_pressure": 0.1,
                    "low_quality": 0.1,
                },
                "etf_adjustments": {
                    "quality_floor": 0.55,
                    "pe_expensive_discount": 0.4,
                    "low_quality_discount": 0.35,
                    "concentration_pressure_discount": 0.85,
                    "core_concentration_pressure_discount": 0.65,
                    "core_momentum_reduccion_discount": 0.85,
                },
            },
        )

        self.assertEqual(scored.loc[0, "score_refuerzo"], scored.loc[1, "score_refuerzo"])
        self.assertEqual(scored.loc[0, "score_reduccion"], scored.loc[1, "score_reduccion"])

    def test_technical_overlay_is_blended_when_present(self) -> None:
        decision = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "CRM",
                    "score_refuerzo": 0.40,
                    "score_reduccion": 0.30,
                }
            ]
        )
        technical_overlay = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "CRM",
                    "Dist_SMA20_%": 8.0,
                    "Dist_SMA50_%": 10.0,
                    "Dist_EMA20_%": 7.0,
                    "Dist_EMA50_%": 9.0,
                    "RSI_14": 55.0,
                    "Momentum_20d_%": 12.0,
                    "Momentum_60d_%": 18.0,
                    "Vol_20d_Anual_%": 18.0,
                    "Drawdown_desde_Max3m_%": -4.0,
                    "Tech_Trend": "Alcista fuerte",
                }
            ]
        )

        with_tech = build_technical_overlay_scores(decision, technical_overlay)
        blended = apply_technical_overlay_scores(with_tech)

        self.assertIn("tech_refuerzo", blended.columns)
        self.assertIn("score_refuerzo_v2", blended.columns)
        self.assertIn("score_reduccion_v2", blended.columns)
        self.assertGreater(blended.loc[0, "tech_refuerzo"], 0.5)
        self.assertGreater(blended.loc[0, "score_refuerzo_v2"], blended.loc[0, "score_refuerzo"])

    def test_concentration_and_quality_change_base_scores(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "LOWW",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Peso_%": 1.5,
                    "Perf Week": 3.0,
                    "Perf Month": 5.0,
                    "Perf YTD": 9.0,
                    "Beta": 1.0,
                    "P/E": 18.0,
                    "ROE": 22.0,
                    "Profit Margin": 18.0,
                    "MEP_Premium_%": 0.5,
                    "Consensus_Final": 0.6,
                    "Ganancia_%": 8.0,
                    "Ganancia_ARS": 100.0,
                },
                {
                    "Ticker_IOL": "HIGHW",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Peso_%": 6.5,
                    "Perf Week": 3.0,
                    "Perf Month": 5.0,
                    "Perf YTD": 9.0,
                    "Beta": 1.0,
                    "P/E": 18.0,
                    "ROE": 5.0,
                    "Profit Margin": 3.0,
                    "MEP_Premium_%": 0.5,
                    "Consensus_Final": 0.6,
                    "Ganancia_%": 8.0,
                    "Ganancia_ARS": 100.0,
                },
            ]
        )

        scored = apply_base_scores(
            df,
            scoring_rules={
                "score_reduccion_weights": {
                    "high_weight": 0.2,
                    "momentum": 0.14,
                    "beta_risk": 0.14,
                    "mep_premium": 0.08,
                    "consensus_bad": 0.08,
                    "pe_expensive": 0.08,
                    "big_gain": 0.08,
                    "concentration_pressure": 0.1,
                    "low_quality": 0.1,
                },
                "etf_adjustments": {
                    "quality_floor": 0.55,
                    "pe_expensive_discount": 0.4,
                    "low_quality_discount": 0.35,
                    "concentration_pressure_discount": 0.85,
                    "core_concentration_pressure_discount": 0.65,
                    "core_momentum_reduccion_discount": 0.85,
                },
            },
        )

        self.assertGreater(scored.loc[0, "s_concentration_room"], scored.loc[1, "s_concentration_room"])
        self.assertGreater(scored.loc[0, "s_quality"], scored.loc[1, "s_quality"])
        self.assertGreater(scored.loc[0, "score_refuerzo"], scored.loc[1, "score_refuerzo"])
        self.assertLess(scored.loc[0, "score_reduccion"], scored.loc[1, "score_reduccion"])

    def test_core_etf_gets_softer_reduction_pressure_than_stock(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "SPY",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Es_ETF": True,
                    "Es_Core_ETF": True,
                    "Peso_%": 4.8,
                    "Perf Week": -2.0,
                    "Perf Month": -3.0,
                    "Perf YTD": -4.0,
                    "Beta": 1.0,
                    "P/E": 22.0,
                    "ROE": None,
                    "Profit Margin": None,
                    "MEP_Premium_%": 3.0,
                    "Consensus_Final": 0.5,
                    "Ganancia_%": 12.0,
                    "Ganancia_ARS": 100.0,
                },
                {
                    "Ticker_IOL": "AAPL",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Es_ETF": False,
                    "Es_Core_ETF": False,
                    "Peso_%": 4.8,
                    "Perf Week": -2.0,
                    "Perf Month": -3.0,
                    "Perf YTD": -4.0,
                    "Beta": 1.0,
                    "P/E": 22.0,
                    "ROE": None,
                    "Profit Margin": None,
                    "MEP_Premium_%": 3.0,
                    "Consensus_Final": 0.5,
                    "Ganancia_%": 12.0,
                    "Ganancia_ARS": 100.0,
                },
            ]
        )

        scored = apply_base_scores(
            df,
            scoring_rules={
                "score_reduccion_weights": {
                    "high_weight": 0.2,
                    "momentum": 0.14,
                    "beta_risk": 0.14,
                    "mep_premium": 0.08,
                    "consensus_bad": 0.08,
                    "pe_expensive": 0.08,
                    "big_gain": 0.08,
                    "concentration_pressure": 0.1,
                    "low_quality": 0.1,
                },
                "etf_adjustments": {
                    "quality_floor": 0.55,
                    "pe_expensive_discount": 0.4,
                    "low_quality_discount": 0.35,
                    "concentration_pressure_discount": 0.85,
                    "core_concentration_pressure_discount": 0.65,
                    "core_momentum_reduccion_discount": 0.85,
                },
            },
        )

        self.assertLess(
            scored.loc[0, "s_concentration_pressure_effective"],
            scored.loc[1, "s_concentration_pressure_effective"],
        )
        self.assertLess(scored.loc[0, "score_reduccion"], scored.loc[1, "score_reduccion"])

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

    def test_stock_refuerzo_comment_mentions_quality_or_beta_support(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "VIST",
                    "Tipo": "CEDEAR",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_subfamily": None,
                    "accion_sugerida_v2": "Refuerzo",
                    "Peso_%": 1.2,
                    "Beta": 0.75,
                    "P/E": 11.0,
                    "ROE": 30.0,
                    "Profit Margin": 25.0,
                    "Consensus_Final": 0.8,
                    "Momentum_Refuerzo": 0.8,
                    "Momentum_Reduccion_Effective": 0.2,
                    "Ganancia_%_Cap": 50.0,
                    "MEP_Premium_%": -98.0,
                    "Tech_Trend": "Alcista",
                    "score_despliegue_liquidez": 0.0,
                    "s_consensus_good": 0.8,
                    "s_consensus_bad": 0.2,
                    "s_low_weight": 0.9,
                    "s_high_weight": 0.1,
                    "s_beta_ok": 0.8,
                    "s_beta_risk": 0.2,
                    "s_mep_ok": 0.9,
                    "s_mep_premium": 0.1,
                    "s_pe_ok": 0.8,
                    "s_pe_expensive": 0.2,
                }
            ]
        )

        explained = enrich_decision_explanations(df)
        comment = explained.loc[0, "motivo_accion"]
        score_comment = explained.loc[0, "motivo_score"]

        self.assertIn("Refuerzo por", comment)
        self.assertTrue(("beta controlada" in comment) or ("ROE alto" in comment) or ("margen alto" in comment))
        self.assertIn("calidad", score_comment)

    def test_stock_reduction_comment_mentions_pressure_sources(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "MELI",
                    "Tipo": "CEDEAR",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_subfamily": None,
                    "accion_sugerida_v2": "Reducir",
                    "Peso_%": 4.5,
                    "Beta": 1.5,
                    "P/E": 44.0,
                    "ROE": 12.0,
                    "Profit Margin": 7.0,
                    "Consensus_Final": 0.5,
                    "Momentum_Refuerzo": 0.3,
                    "Momentum_Reduccion_Effective": 0.75,
                    "Ganancia_%_Cap": 20.0,
                    "MEP_Premium_%": -95.0,
                    "Tech_Trend": "Bajista",
                    "score_despliegue_liquidez": 0.0,
                    "s_consensus_good": 0.5,
                    "s_consensus_bad": 0.5,
                    "s_low_weight": 0.2,
                    "s_high_weight": 0.8,
                    "s_beta_ok": 0.2,
                    "s_beta_risk": 0.8,
                    "s_mep_ok": 0.8,
                    "s_mep_premium": 0.2,
                    "s_pe_ok": 0.1,
                    "s_pe_expensive": 0.9,
                }
            ]
        )

        explained = enrich_decision_explanations(df)
        comment = explained.loc[0, "motivo_accion"]

        self.assertIn("Reduccion por", comment)
        self.assertTrue(("valuacion exigente" in comment) or ("momentum debil" in comment) or ("beta alta" in comment))

    def test_country_region_etf_neutral_comment_mentions_limited_support(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "EWZ",
                    "Tipo": "CEDEAR",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_subfamily": "etf_country_region",
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "Peso_%": 1.9,
                    "Beta": 0.7,
                    "P/E": None,
                    "ROE": None,
                    "Profit Margin": None,
                    "Consensus_Final": 0.5,
                    "Momentum_Refuerzo": 0.9,
                    "Momentum_Reduccion_Effective": 0.2,
                    "Ganancia_%_Cap": 35.0,
                    "MEP_Premium_%": -98.0,
                    "Tech_Trend": "Alcista",
                    "has_fundamental_support": False,
                    "score_despliegue_liquidez": 0.0,
                    "s_consensus_good": 0.5,
                    "s_consensus_bad": 0.5,
                    "s_low_weight": 0.8,
                    "s_high_weight": 0.2,
                    "s_beta_ok": 0.8,
                    "s_beta_risk": 0.2,
                    "s_mep_ok": 0.9,
                    "s_mep_premium": 0.1,
                    "s_pe_ok": 0.5,
                    "s_pe_expensive": 0.5,
                }
            ]
        )

        explained = enrich_decision_explanations(df)
        comment = explained.loc[0, "motivo_accion"]

        self.assertIn("soporte fundamental limitado", comment)

    def test_growth_stock_neutral_comment_mentions_growth_context(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AMD",
                    "Tipo": "CEDEAR",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_subfamily": "stock_growth",
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "Peso_%": 0.2,
                    "Beta": 1.9,
                    "P/E": 80.0,
                    "ROE": 7.0,
                    "Profit Margin": 12.0,
                    "Consensus_Final": 0.8,
                    "Momentum_Refuerzo": 0.8,
                    "Momentum_Reduccion_Effective": 0.4,
                    "Ganancia_%_Cap": 30.0,
                    "MEP_Premium_%": -98.0,
                    "Tech_Trend": "Alcista",
                    "score_despliegue_liquidez": 0.0,
                    "s_consensus_good": 0.8,
                    "s_consensus_bad": 0.2,
                    "s_low_weight": 0.9,
                    "s_high_weight": 0.1,
                    "s_beta_ok": 0.1,
                    "s_beta_risk": 0.9,
                    "s_mep_ok": 0.9,
                    "s_mep_premium": 0.1,
                    "s_pe_ok": 0.0,
                    "s_pe_expensive": 1.0,
                }
            ]
        )

        explained = enrich_decision_explanations(df)
        comment = explained.loc[0, "motivo_accion"]
        score_comment = explained.loc[0, "motivo_score"]

        self.assertIn("Growth en monitoreo", comment)
        self.assertIn("growth", score_comment.lower())

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

    def test_stock_commodity_mixed_technical_and_high_gain_gets_extra_brake(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "NEM",
                    "asset_subfamily": "stock_commodity",
                    "score_refuerzo": 0.59,
                    "score_reduccion": 0.43,
                    "tech_refuerzo": 0.63,
                    "Tech_Trend": "Mixta",
                    "Ganancia_%_Cap": 103.0,
                },
                {
                    "Ticker_IOL": "VIST",
                    "asset_subfamily": "stock_commodity",
                    "score_refuerzo": 0.59,
                    "score_reduccion": 0.43,
                    "tech_refuerzo": 0.63,
                    "Tech_Trend": "Alcista",
                    "Ganancia_%_Cap": 103.0,
                },
            ]
        )

        blended = apply_technical_overlay_scores(
            df,
            scoring_rules={
                "technical_overlay": {"blend_base": 0.75, "blend_tech": 0.25},
                "asset_subfamily_adjustments": {
                    "stock_commodity": {
                        "technical_mixed_high_gain_refuerzo_penalty": 0.02,
                        "technical_mixed_high_gain_reduccion_boost": 0.01,
                        "technical_mixed_gain_threshold_pct": 80.0,
                        "technical_mixed_trends": ["Mixta"],
                    }
                },
            },
        )

        self.assertLess(blended.loc[0, "score_refuerzo_v2"], blended.loc[1, "score_refuerzo_v2"])
        self.assertGreater(blended.loc[0, "score_reduccion_v2"], blended.loc[1, "score_reduccion_v2"])
        self.assertLess(blended.loc[0, "score_unificado_v2"], blended.loc[1, "score_unificado_v2"])


if __name__ == "__main__":
    unittest.main()
