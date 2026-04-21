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


class StrategyRulesTests(unittest.TestCase):
    def test_rank_score_returns_neutral_for_single_name_cohort(self) -> None:
        score = rank_score(pd.Series([42.0]))

        self.assertEqual(score.iloc[0], 0.5)

    def test_rank_score_reduces_confidence_for_two_name_cohort(self) -> None:
        higher = rank_score(pd.Series([10.0, 20.0]), higher_is_better=True)
        lower = rank_score(pd.Series([10.0, 20.0]), higher_is_better=False)

        self.assertEqual(higher.round(3).tolist(), [0.5, 0.75])
        self.assertEqual(lower.round(3).tolist(), [0.5, 0.25])

    def test_rank_score_reduces_extremes_for_three_name_cohort(self) -> None:
        score = rank_score(pd.Series([10.0, 20.0, 30.0]), higher_is_better=True)

        self.assertEqual(score.round(3).tolist(), [0.389, 0.611, 0.833])

    def test_rank_score_three_name_cohort_uses_expected_damping_formula(self) -> None:
        score = rank_score(pd.Series([10.0, 20.0, 30.0]), higher_is_better=True)

        # ranks pct=True => [0.333..., 0.666..., 1.0]
        # damping N=3 => (3-1)/3 = 2/3
        # out = ((relative - 0.5) * damping) + 0.5
        expected = [0.3889, 0.6111, 0.8333]
        self.assertEqual(score.round(4).tolist(), expected)

    def test_rank_score_three_name_cohort_uses_expected_damping_formula_when_lower_is_better(self) -> None:
        score = rank_score(pd.Series([10.0, 20.0, 30.0]), higher_is_better=False)

        expected = [0.6111, 0.3889, 0.1667]
        self.assertEqual(score.round(4).tolist(), expected)

    def test_rank_score_reduces_extremes_for_four_name_cohort(self) -> None:
        score = rank_score(pd.Series([10.0, 20.0, 30.0, 40.0]), higher_is_better=True)

        self.assertEqual(score.round(4).tolist(), [0.3125, 0.5, 0.6875, 0.875])

    def test_rank_score_four_name_cohort_uses_expected_damping_formula(self) -> None:
        score = rank_score(pd.Series([10.0, 20.0, 30.0, 40.0]), higher_is_better=True)

        # ranks pct=True => [0.25, 0.5, 0.75, 1.0]
        # damping N=4 => (4-1)/4 = 0.75
        expected = [0.3125, 0.5, 0.6875, 0.875]
        self.assertEqual(score.round(4).tolist(), expected)

    def test_rank_score_four_name_cohort_uses_expected_damping_formula_when_lower_is_better(self) -> None:
        score = rank_score(pd.Series([10.0, 20.0, 30.0, 40.0]), higher_is_better=False)

        expected = [0.6875, 0.5, 0.3125, 0.125]
        self.assertEqual(score.round(4).tolist(), expected)

    def test_rank_score_is_fully_relative_for_five_name_cohort(self) -> None:
        score = rank_score(pd.Series([10.0, 20.0, 30.0, 40.0, 50.0]), higher_is_better=True)

        self.assertEqual(score.round(3).tolist(), [0.2, 0.4, 0.6, 0.8, 1.0])

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

    def test_base_and_v2_action_assignment_share_the_same_logic(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "KO",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "score_refuerzo": 0.65,
                    "score_reduccion": 0.20,
                    "score_refuerzo_v2": 0.65,
                    "score_reduccion_v2": 0.20,
                    "score_despliegue_liquidez": 0.0,
                },
                {
                    "Ticker_IOL": "CAUCION",
                    "Es_Liquidez": True,
                    "Es_Bono": False,
                    "score_refuerzo": 0.10,
                    "score_reduccion": 0.10,
                    "score_refuerzo_v2": 0.10,
                    "score_reduccion_v2": 0.10,
                    "score_despliegue_liquidez": 0.60,
                },
                {
                    "Ticker_IOL": "PAMP",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Tipo": "AcciÃ³n Local",
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

        base_result = assign_base_action(df)
        v2_result = assign_action_v2(df)

        self.assertListEqual(
            base_result["accion_sugerida"].tolist(),
            v2_result["accion_sugerida_v2"].tolist(),
        )

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
                    "Dist_SMA200_%": 12.0,
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

    def test_technical_overlay_passes_prediction_columns_through_to_decision(self) -> None:
        decision = pd.DataFrame(
            [{"Ticker_IOL": "AAPL", "score_refuerzo": 0.40, "score_reduccion": 0.30}]
        )
        technical_overlay = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AAPL",
                    "Dist_SMA20_%": 3.0,
                    "Dist_SMA50_%": 5.0,
                    "Dist_SMA200_%": 8.0,
                    "Dist_EMA20_%": 2.0,
                    "Dist_EMA50_%": 4.0,
                    "RSI_14": 45.0,
                    "Momentum_20d_%": 3.0,
                    "Momentum_60d_%": 6.0,
                    "Vol_20d_Anual_%": 20.0,
                    "Drawdown_desde_Max3m_%": -2.0,
                    "Tech_Trend": "Alcista",
                    "ADX_14": 24.0,
                    "DI_plus_14": 28.0,
                    "DI_minus_14": 16.0,
                    "Relative_Volume": 1.8,
                    "Return_1d_%": 0.9,
                    "Return_intraday_%": 0.5,
                }
            ]
        )

        out = build_technical_overlay_scores(decision, technical_overlay)

        for col in ["ADX_14", "DI_plus_14", "DI_minus_14", "Relative_Volume", "Return_1d_%", "Return_intraday_%"]:
            self.assertIn(col, out.columns, f"{col} should be passed through to the merged output")
            self.assertAlmostEqual(float(out.loc[0, col]), float(technical_overlay.loc[0, col]), places=6)

    def test_build_decision_base_treats_zero_mep_as_missing_for_premium(self) -> None:
        df_total = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AAPL",
                    "Tipo": "CEDEAR",
                    "Bloque": "Growth",
                    "Peso_%": 1.0,
                    "Valorizado_ARS": 1000.0,
                    "Valor_USD": 1.0,
                    "Ganancia_ARS": 10.0,
                    "Cantidad_Real": 1.0,
                    "PPC_ARS": 900.0,
                }
            ]
        )
        df_cedears = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AAPL",
                    "Ticker_Finviz": "AAPL",
                    "instrument_class": "stock",
                    "asset_family": "stock",
                    "asset_subfamily": "stock_growth",
                    "is_etf": False,
                    "is_core_etf": False,
                    "Perf Week": 1.0,
                    "Perf Month": 2.0,
                    "Perf YTD": 3.0,
                    "Beta": 1.1,
                    "P/E": 20.0,
                    "ROE": 25.0,
                    "Profit Margin": 22.0,
                    "MEP_Implicito": 1200.0,
                }
            ]
        )

        decision = build_decision_base(
            df_total,
            df_cedears,
            pd.DataFrame(),
            mep_real=0.0,
        )

        self.assertTrue(pd.isna(decision.loc[0, "MEP_Premium_%"]))

    def test_technical_reduction_is_not_mechanical_inverse_of_refuerzo(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "CRM",
                    "score_refuerzo": 0.40,
                    "score_reduccion": 0.30,
                    "tech_refuerzo": 0.45,
                    "ts_above_sma20": 0.45,
                    "ts_above_sma50": 0.55,
                    "ts_above_ema20": 0.50,
                    "ts_above_ema50": 0.60,
                    "ts_rsi": 0.50,
                    "ts_mom20": 0.40,
                    "ts_mom60": 0.35,
                    "ts_drawdown": 0.70,
                    "ts_volatility": 0.80,
                }
            ]
        )

        blended = apply_technical_overlay_scores(df)

        self.assertNotAlmostEqual(blended.loc[0, "tech_reduccion"], 1 - blended.loc[0, "tech_refuerzo"], places=6)

    def test_technical_ranges_can_be_overridden_from_external_rules(self) -> None:
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
                    "Dist_SMA200_%": 12.0,
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

        default_overlay = build_technical_overlay_scores(decision, technical_overlay)
        custom_overlay = build_technical_overlay_scores(
            decision,
            technical_overlay,
            scoring_rules={
                "technical_overlay": {
                    "ranges": {
                        "dist_sma20_pct": {"min": -20.0, "max": 20.0},
                        "momentum_20d_pct": {"min": -30.0, "max": 30.0},
                    }
                }
            },
        )

        self.assertLess(custom_overlay.loc[0, "ts_above_sma20"], default_overlay.loc[0, "ts_above_sma20"])
        self.assertLess(custom_overlay.loc[0, "ts_mom20"], default_overlay.loc[0, "ts_mom20"])

    def test_technical_rsi_reduction_prefers_overbought_over_oversold(self) -> None:
        decision = pd.DataFrame(
            [
                {"Ticker_IOL": "OVERSOLD", "score_refuerzo": 0.40, "score_reduccion": 0.30},
                {"Ticker_IOL": "OVERBOUGHT", "score_refuerzo": 0.40, "score_reduccion": 0.30},
            ]
        )
        technical_overlay = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "OVERSOLD",
                    "Dist_SMA20_%": 0.0,
                    "Dist_SMA50_%": 0.0,
                    "Dist_SMA200_%": 0.0,
                    "Dist_EMA20_%": 0.0,
                    "Dist_EMA50_%": 0.0,
                    "RSI_14": 25.0,
                    "Momentum_20d_%": 0.0,
                    "Momentum_60d_%": 0.0,
                    "Vol_20d_Anual_%": 25.0,
                    "Drawdown_desde_Max3m_%": -10.0,
                    "Tech_Trend": "Mixta",
                },
                {
                    "Ticker_IOL": "OVERBOUGHT",
                    "Dist_SMA20_%": 0.0,
                    "Dist_SMA50_%": 0.0,
                    "Dist_SMA200_%": 0.0,
                    "Dist_EMA20_%": 0.0,
                    "Dist_EMA50_%": 0.0,
                    "RSI_14": 80.0,
                    "Momentum_20d_%": 0.0,
                    "Momentum_60d_%": 0.0,
                    "Vol_20d_Anual_%": 25.0,
                    "Drawdown_desde_Max3m_%": -10.0,
                    "Tech_Trend": "Mixta",
                },
            ]
        )

        blended = apply_technical_overlay_scores(build_technical_overlay_scores(decision, technical_overlay))

        self.assertLess(blended.loc[0, "ts_rsi_reduccion"], blended.loc[1, "ts_rsi_reduccion"])
        self.assertLess(blended.loc[0, "tech_reduccion"], blended.loc[1, "tech_reduccion"])

    def test_sma200_can_softly_improve_or_worsen_technical_scores(self) -> None:
        decision = pd.DataFrame(
            [
                {"Ticker_IOL": "ABOVE", "score_refuerzo": 0.40, "score_reduccion": 0.30},
                {"Ticker_IOL": "BELOW", "score_refuerzo": 0.40, "score_reduccion": 0.30},
            ]
        )
        technical_overlay = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "ABOVE",
                    "Dist_SMA20_%": 1.0,
                    "Dist_SMA50_%": 1.0,
                    "Dist_SMA200_%": 20.0,
                    "Dist_EMA20_%": 1.0,
                    "Dist_EMA50_%": 1.0,
                    "RSI_14": 55.0,
                    "Momentum_20d_%": 2.0,
                    "Momentum_60d_%": 4.0,
                    "Vol_20d_Anual_%": 20.0,
                    "Drawdown_desde_Max3m_%": -4.0,
                    "Tech_Trend": "Alcista",
                },
                {
                    "Ticker_IOL": "BELOW",
                    "Dist_SMA20_%": 1.0,
                    "Dist_SMA50_%": 1.0,
                    "Dist_SMA200_%": -20.0,
                    "Dist_EMA20_%": 1.0,
                    "Dist_EMA50_%": 1.0,
                    "RSI_14": 55.0,
                    "Momentum_20d_%": 2.0,
                    "Momentum_60d_%": 4.0,
                    "Vol_20d_Anual_%": 20.0,
                    "Drawdown_desde_Max3m_%": -4.0,
                    "Tech_Trend": "Alcista",
                },
            ]
        )

        blended = apply_technical_overlay_scores(build_technical_overlay_scores(decision, technical_overlay))

        self.assertGreater(blended.loc[0, "ts_above_sma200"], blended.loc[1, "ts_above_sma200"])
        self.assertGreater(blended.loc[0, "tech_refuerzo"], blended.loc[1, "tech_refuerzo"])
        self.assertLess(blended.loc[0, "tech_reduccion"], blended.loc[1, "tech_reduccion"])

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

    def test_absolute_scoring_can_penalize_uniformly_expensive_names(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "EXP1",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Peso_%": 1.0,
                    "Perf Week": 1.0,
                    "Perf Month": 1.0,
                    "Perf YTD": 1.0,
                    "Beta": 1.0,
                    "P/E": 35.0,
                    "ROE": 18.0,
                    "Profit Margin": 18.0,
                    "MEP_Premium_%": -95.0,
                    "Consensus_Final": 0.6,
                    "Ganancia_%": 10.0,
                    "Ganancia_ARS": 100.0,
                },
                {
                    "Ticker_IOL": "EXP2",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Peso_%": 1.0,
                    "Perf Week": 1.0,
                    "Perf Month": 1.0,
                    "Perf YTD": 1.0,
                    "Beta": 1.0,
                    "P/E": 40.0,
                    "ROE": 18.0,
                    "Profit Margin": 18.0,
                    "MEP_Premium_%": -95.0,
                    "Consensus_Final": 0.6,
                    "Ganancia_%": 10.0,
                    "Ganancia_ARS": 100.0,
                },
            ]
        )

        relative_only = apply_base_scores(df)
        with_absolute = apply_base_scores(
            df,
            scoring_rules={
                "absolute_scoring": {
                    "enabled": True,
                    "relative_weight": 0.0,
                    "absolute_weight": 1.0,
                    "metrics": {
                        "pe": {"good_max": 18.0, "bad_min": 30.0},
                        "beta": {"good_max": 0.8, "bad_min": 1.5},
                        "roe": {"good_min": 20.0, "bad_max": 5.0},
                        "profit_margin": {"good_min": 20.0, "bad_max": 5.0},
                        "mep_premium_pct": {"good_max": -90.0, "bad_min": 10.0},
                        "ganancia_pct_cap": {"good_max": 10.0, "bad_min": 80.0, "bad_loss_max": -20.0},
                    },
                }
            },
        )

        self.assertGreater(relative_only.loc[0, "s_pe_ok"], with_absolute.loc[0, "s_pe_ok"])
        self.assertLessEqual(with_absolute.loc[0, "s_pe_ok"], 0.01)
        self.assertLessEqual(with_absolute.loc[1, "s_pe_ok"], 0.01)

    def test_absolute_scoring_can_reward_absolute_quality_even_if_relative_gap_is_small(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "Q1",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Peso_%": 1.0,
                    "Perf Week": 1.0,
                    "Perf Month": 1.0,
                    "Perf YTD": 1.0,
                    "Beta": 0.7,
                    "P/E": 18.0,
                    "ROE": 24.0,
                    "Profit Margin": 22.0,
                    "MEP_Premium_%": -95.0,
                    "Consensus_Final": 0.6,
                    "Ganancia_%": 10.0,
                    "Ganancia_ARS": 100.0,
                },
                {
                    "Ticker_IOL": "Q2",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Peso_%": 1.0,
                    "Perf Week": 1.0,
                    "Perf Month": 1.0,
                    "Perf YTD": 1.0,
                    "Beta": 0.75,
                    "P/E": 19.0,
                    "ROE": 23.0,
                    "Profit Margin": 21.0,
                    "MEP_Premium_%": -95.0,
                    "Consensus_Final": 0.6,
                    "Ganancia_%": 10.0,
                    "Ganancia_ARS": 100.0,
                },
            ]
        )

        with_absolute = apply_base_scores(
            df,
            scoring_rules={
                "absolute_scoring": {
                    "enabled": True,
                    "relative_weight": 0.5,
                    "absolute_weight": 0.5,
                }
            },
        )

        self.assertGreaterEqual(with_absolute["s_quality"].min(), 0.7)
        self.assertGreaterEqual(with_absolute["s_beta_ok"].min(), 0.5)

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

    def test_refuerzo_comment_can_surface_up_to_three_positive_signals(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "TRIPLE",
                    "Tipo": "CEDEAR",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_subfamily": None,
                    "accion_sugerida_v2": "Refuerzo",
                    "Peso_%": 1.0,
                    "Beta": 0.7,
                    "P/E": 15.0,
                    "ROE": 24.0,
                    "Profit Margin": 23.0,
                    "Consensus_Final": 0.8,
                    "Momentum_Refuerzo": 0.8,
                    "Momentum_Reduccion_Effective": 0.2,
                    "Ganancia_%_Cap": 20.0,
                    "MEP_Premium_%": -95.0,
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

        self.assertIn("peso bajo", comment)
        self.assertIn("beta controlada", comment)
        self.assertIn("valuacion razonable", comment)

    def test_narrative_can_use_relative_quality_when_absolute_threshold_is_not_met(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "RELQ",
                    "Tipo": "CEDEAR",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_subfamily": "stock_growth",
                    "accion_sugerida_v2": "Refuerzo",
                    "Peso_%": 0.4,
                    "Beta": 1.0,
                    "P/E": 26.0,
                    "ROE": 12.0,
                    "Profit Margin": 11.0,
                    "Consensus_Final": 0.6,
                    "Momentum_Refuerzo": 0.62,
                    "Momentum_Reduccion_Effective": 0.3,
                    "Ganancia_%_Cap": 8.0,
                    "MEP_Premium_%": -95.0,
                    "Tech_Trend": "Mixta",
                    "score_despliegue_liquidez": 0.0,
                    "s_consensus_good": 0.6,
                    "s_consensus_bad": 0.4,
                    "s_low_weight": 0.9,
                    "s_high_weight": 0.1,
                    "s_beta_ok": 0.72,
                    "s_beta_risk": 0.28,
                    "s_mep_ok": 0.9,
                    "s_mep_premium": 0.1,
                    "s_pe_ok": 0.73,
                    "s_pe_expensive": 0.27,
                    "s_quality_effective": 0.78,
                    "s_low_quality_effective": 0.22,
                }
            ]
        )

        comment = enrich_decision_explanations(df).loc[0, "motivo_accion"]

        self.assertIn("calidad relativa", comment)

    def test_explanations_follow_overridden_absolute_metric_thresholds(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "SAFE",
                    "Tipo": "CEDEAR",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_subfamily": "stock_defensive_dividend",
                    "accion_sugerida_v2": "Refuerzo",
                    "Peso_%": 1.5,
                    "Beta": 0.9,
                    "P/E": 14.0,
                    "ROE": 18.0,
                    "Profit Margin": 18.0,
                    "Consensus_Final": 0.75,
                    "Momentum_Refuerzo": 0.7,
                    "Momentum_Reduccion_Effective": 0.2,
                    "Ganancia_%_Cap": 30.0,
                    "MEP_Premium_%": -95.0,
                    "Tech_Trend": "Mixta",
                    "score_despliegue_liquidez": 0.0,
                    "s_consensus_good": 0.8,
                    "s_consensus_bad": 0.2,
                    "s_low_weight": 0.8,
                    "s_high_weight": 0.2,
                    "s_beta_ok": 0.7,
                    "s_beta_risk": 0.3,
                    "s_mep_ok": 0.8,
                    "s_mep_premium": 0.2,
                    "s_pe_ok": 0.8,
                    "s_pe_expensive": 0.2,
                }
            ]
        )

        default_comment = enrich_decision_explanations(df).loc[0, "motivo_accion"]
        custom_comment = enrich_decision_explanations(
            df,
            scoring_rules={
                "absolute_scoring": {
                    "metrics": {
                        "beta": {"good_max": 1.0, "bad_min": 1.6},
                        "pe": {"good_max": 15.0, "bad_min": 28.0},
                        "roe": {"good_min": 18.0, "bad_max": 5.0},
                        "profit_margin": {"good_min": 18.0, "bad_max": 5.0},
                        "mep_premium_pct": {"good_max": -90.0, "bad_min": 10.0},
                        "ganancia_pct_cap": {"good_max": 10.0, "bad_min": 80.0, "bad_loss_max": -20.0},
                    }
                }
            },
        ).loc[0, "motivo_accion"]

        self.assertNotIn("beta controlada", default_comment)
        self.assertIn("beta controlada", custom_comment)

    def test_explanations_follow_overridden_narrative_thresholds(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "GAIN",
                    "Tipo": "CEDEAR",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_subfamily": "stock_growth",
                    "accion_sugerida_v2": "Reducir",
                    "Peso_%": 3.0,
                    "Beta": 1.2,
                    "P/E": 25.0,
                    "ROE": 12.0,
                    "Profit Margin": 12.0,
                    "Consensus_Final": 0.5,
                    "Momentum_Refuerzo": 0.3,
                    "Momentum_Reduccion_Effective": 0.7,
                    "Ganancia_%_Cap": 70.0,
                    "MEP_Premium_%": -95.0,
                    "Tech_Trend": "Mixta",
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

        default_comment = enrich_decision_explanations(df).loc[0, "motivo_accion"]
        custom_comment = enrich_decision_explanations(
            df,
            scoring_rules={"narrative_thresholds": {"negative": {"ganancia_pct_cap_min": 60.0}}},
        ).loc[0, "motivo_accion"]

        self.assertNotIn("ganancia extendida", default_comment)
        self.assertIn("ganancia extendida", custom_comment)

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

    def test_refuerzo_comment_can_mention_proximity_to_52w_high(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "EWZ",
                    "Tipo": "CEDEAR",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_subfamily": "etf_country_region",
                    "accion_sugerida_v2": "Refuerzo",
                    "Peso_%": 1.2,
                    "Beta": 0.8,
                    "P/E": None,
                    "ROE": None,
                    "Profit Margin": None,
                    "Consensus_Final": 0.5,
                    "Momentum_Refuerzo": 0.9,
                    "Momentum_Reduccion_Effective": 0.2,
                    "Ganancia_%_Cap": 20.0,
                    "MEP_Premium_%": -98.0,
                    "Dist_52w_High_%": -1.5,
                    "Tech_Trend": "Alcista",
                    "score_despliegue_liquidez": 0.0,
                    "s_consensus_good": 0.5,
                    "s_consensus_bad": 0.5,
                    "s_low_weight": 0.9,
                    "s_high_weight": 0.1,
                    "s_beta_ok": 0.8,
                    "s_beta_risk": 0.2,
                    "s_mep_ok": 0.9,
                    "s_mep_premium": 0.1,
                    "s_pe_ok": 0.5,
                    "s_pe_expensive": 0.5,
                }
            ]
        )

        comment = enrich_decision_explanations(df).loc[0, "motivo_accion"]

        self.assertIn("cerca de maximos anuales", comment)

    def test_neutral_comment_can_mention_distance_from_52w_high(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "MELI",
                    "Tipo": "CEDEAR",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_subfamily": "stock_growth",
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "Peso_%": 1.0,
                    "Beta": 1.4,
                    "P/E": 40.0,
                    "ROE": 10.0,
                    "Profit Margin": 8.0,
                    "Consensus_Final": 0.45,
                    "Momentum_Refuerzo": 0.35,
                    "Momentum_Reduccion_Effective": 0.7,
                    "Ganancia_%_Cap": 15.0,
                    "MEP_Premium_%": -95.0,
                    "Dist_52w_High_%": -32.0,
                    "Tech_Trend": "Mixta",
                    "score_despliegue_liquidez": 0.0,
                    "s_consensus_good": 0.45,
                    "s_consensus_bad": 0.55,
                    "s_low_weight": 0.8,
                    "s_high_weight": 0.2,
                    "s_beta_ok": 0.2,
                    "s_beta_risk": 0.8,
                    "s_mep_ok": 0.8,
                    "s_mep_premium": 0.2,
                    "s_pe_ok": 0.1,
                    "s_pe_expensive": 0.9,
                    "s_quality_effective": 0.3,
                    "s_low_quality_effective": 0.8,
                }
            ]
        )

        comment = enrich_decision_explanations(df).loc[0, "motivo_accion"]

        self.assertIn("lejos de maximos anuales", comment)

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

    def test_stock_commodity_mixed_technical_gets_soft_brake_even_without_high_gain(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "NEM",
                    "asset_subfamily": "stock_commodity",
                    "score_refuerzo": 0.59,
                    "score_reduccion": 0.43,
                    "tech_refuerzo": 0.63,
                    "Tech_Trend": "Mixta",
                    "Ganancia_%_Cap": 40.0,
                },
                {
                    "Ticker_IOL": "VIST",
                    "asset_subfamily": "stock_commodity",
                    "score_refuerzo": 0.59,
                    "score_reduccion": 0.43,
                    "tech_refuerzo": 0.63,
                    "Tech_Trend": "Alcista",
                    "Ganancia_%_Cap": 40.0,
                },
            ]
        )

        blended = apply_technical_overlay_scores(
            df,
            scoring_rules={
                "technical_overlay": {"blend_base": 0.75, "blend_tech": 0.25},
                "asset_subfamily_adjustments": {
                    "stock_commodity": {
                        "technical_mixed_refuerzo_penalty": 0.01,
                        "technical_mixed_reduccion_boost": 0.005,
                        "technical_mixed_trends": ["Mixta"],
                    }
                },
            },
        )

        self.assertLess(blended.loc[0, "score_refuerzo_v2"], blended.loc[1, "score_refuerzo_v2"])
        self.assertGreater(blended.loc[0, "score_reduccion_v2"], blended.loc[1, "score_reduccion_v2"])
        self.assertLess(blended.loc[0, "score_unificado_v2"], blended.loc[1, "score_unificado_v2"])

    def test_absolute_refuerzo_gate_caps_non_bullish_negative_momentum_names(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "GOOGL",
                    "asset_family": "stock",
                    "asset_subfamily": "stock_growth",
                    "score_refuerzo": 0.60,
                    "score_reduccion": 0.40,
                    "tech_refuerzo": 0.80,
                    "Tech_Trend": "Mixta",
                    "Momentum_20d_%": -1.0,
                },
                {
                    "Ticker_IOL": "EEM",
                    "asset_family": "etf",
                    "asset_subfamily": "etf_country_region",
                    "score_refuerzo": 0.60,
                    "score_reduccion": 0.40,
                    "tech_refuerzo": 0.80,
                    "Tech_Trend": "Alcista",
                    "Momentum_20d_%": -1.0,
                },
            ]
        )

        blended = apply_technical_overlay_scores(
            df,
            scoring_rules={
                "technical_overlay": {"blend_base": 0.75, "blend_tech": 0.25},
                "absolute_scoring": {
                    "refuerzo_gate": {
                        "enabled": True,
                        "momentum_20d_max": 0.0,
                        "max_score": 0.58,
                        "allowed_trends": ["Alcista", "Alcista fuerte"],
                        "excluded_families": ["bond", "liquidity"],
                    }
                },
            },
        )

        self.assertAlmostEqual(blended.loc[0, "score_refuerzo_v2"], 0.58, places=3)
        self.assertGreater(blended.loc[1, "score_refuerzo_v2"], 0.58)

    def test_market_regime_can_penalize_local_equity_and_help_hard_currency_bonds(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "LOMA",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_family": "stock",
                    "asset_subfamily": "stock_argentina",
                    "Peso_%": 1.0,
                    "Perf Week": 1.0,
                    "Perf Month": 2.0,
                    "Perf YTD": 3.0,
                    "Beta": 0.9,
                    "P/E": 10.0,
                    "ROE": 18.0,
                    "Profit Margin": 15.0,
                    "MEP_Premium_%": -95.0,
                    "Consensus_Final": 0.6,
                    "Ganancia_%": 10.0,
                    "Ganancia_ARS": 100.0,
                },
                {
                    "Ticker_IOL": "GD30",
                    "Es_Liquidez": False,
                    "Es_Bono": True,
                    "asset_family": "bond",
                    "asset_subfamily": "bond_sov_ar",
                    "Peso_%": 1.0,
                    "Perf Week": None,
                    "Perf Month": None,
                    "Perf YTD": None,
                    "Beta": None,
                    "P/E": None,
                    "ROE": None,
                    "Profit Margin": None,
                    "MEP_Premium_%": None,
                    "Consensus_Final": 0.5,
                    "Ganancia_%": 10.0,
                    "Ganancia_ARS": 100.0,
                },
            ]
        )

        base = apply_base_scores(df)
        stressed = apply_base_scores(
            df,
            market_context={"riesgo_pais_bps": 950.0},
            scoring_rules={
                "market_regime": {
                    "enabled": True,
                    "flags": {"stress_soberano_local": {"riesgo_pais_bps_min": 800.0}},
                    "adjustments": {
                        "stress_soberano_local": {
                            "stock_argentina": {"refuerzo_delta": -0.03, "reduccion_delta": 0.03},
                            "bond_sov_ar": {"refuerzo_delta": 0.02, "reduccion_delta": -0.02},
                        }
                    },
                }
            },
        )

        self.assertLess(stressed.loc[0, "score_refuerzo"], base.loc[0, "score_refuerzo"])
        self.assertGreater(stressed.loc[0, "score_reduccion"], base.loc[0, "score_reduccion"])
        self.assertGreater(stressed.loc[1, "score_refuerzo"], base.loc[1, "score_refuerzo"])
        self.assertLess(stressed.loc[1, "score_reduccion"], base.loc[1, "score_reduccion"])

    def test_market_regime_can_penalize_growth_when_ust_rates_are_high(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AMD",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_family": "stock",
                    "asset_subfamily": "stock_growth",
                    "Peso_%": 1.0,
                    "Perf Week": 3.0,
                    "Perf Month": 5.0,
                    "Perf YTD": 8.0,
                    "Beta": 1.2,
                    "P/E": 28.0,
                    "ROE": 20.0,
                    "Profit Margin": 18.0,
                    "MEP_Premium_%": -95.0,
                    "Consensus_Final": 0.7,
                    "Ganancia_%": 10.0,
                    "Ganancia_ARS": 100.0,
                },
                {
                    "Ticker_IOL": "KO",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_family": "stock",
                    "asset_subfamily": "stock_defensive_dividend",
                    "Peso_%": 1.0,
                    "Perf Week": 3.0,
                    "Perf Month": 5.0,
                    "Perf YTD": 8.0,
                    "Beta": 0.7,
                    "P/E": 18.0,
                    "ROE": 20.0,
                    "Profit Margin": 18.0,
                    "MEP_Premium_%": -95.0,
                    "Consensus_Final": 0.7,
                    "Ganancia_%": 10.0,
                    "Ganancia_ARS": 100.0,
                },
            ]
        )

        base = apply_base_scores(df)
        regime = apply_base_scores(
            df,
            market_context={"ust_10y_pct": 4.6},
            scoring_rules={
                "market_regime": {
                    "enabled": True,
                    "flags": {"tasas_ust_altas": {"ust_10y_pct_min": 4.5, "ust_5y_pct_min": 4.25}},
                    "adjustments": {
                        "tasas_ust_altas": {
                            "stock_growth": {"refuerzo_delta": -0.02, "reduccion_delta": 0.02},
                            "stock_defensive_dividend": {"refuerzo_delta": 0.02, "reduccion_delta": -0.01},
                        }
                    },
                }
            },
        )

        self.assertLess(regime.loc[0, "score_refuerzo"], base.loc[0, "score_refuerzo"])
        self.assertGreater(regime.loc[0, "score_reduccion"], base.loc[0, "score_reduccion"])
        self.assertGreater(regime.loc[1, "score_refuerzo"], base.loc[1, "score_refuerzo"])

    def test_market_regime_summary_stays_inactive_with_current_real_macro_baseline(self) -> None:
        summary = build_market_regime_summary(
            {
                "riesgo_pais_bps": 609.0,
                "rem_inflacion_mensual_pct": 2.7,
                "rem_inflacion_12m_pct": 22.2,
                "ust_5y_pct": 3.99,
                "ust_10y_pct": 4.35,
            },
            scoring_rules={
                "market_regime": {
                    "enabled": True,
                    "flags": {
                        "stress_soberano_local": {"riesgo_pais_bps_min": 800.0},
                        "inflacion_local_alta": {
                            "rem_inflacion_12m_pct_min": 30.0,
                            "rem_inflacion_mensual_pct_min": 3.0,
                        },
                        "tasas_ust_altas": {"ust_10y_pct_min": 4.5, "ust_5y_pct_min": 4.25},
                    },
                }
            },
        )

        self.assertFalse(summary["any_active"])
        self.assertEqual(summary["active_flags"], [])

    def test_market_regime_summary_can_be_forced_for_calibration_by_lowering_thresholds(self) -> None:
        summary = build_market_regime_summary(
            {
                "riesgo_pais_bps": 609.0,
                "rem_inflacion_mensual_pct": 2.7,
                "rem_inflacion_12m_pct": 22.2,
                "ust_5y_pct": 3.99,
                "ust_10y_pct": 4.35,
            },
            scoring_rules={
                "market_regime": {
                    "enabled": True,
                    "flags": {
                        "stress_soberano_local": {"riesgo_pais_bps_min": 600.0},
                        "inflacion_local_alta": {
                            "rem_inflacion_12m_pct_min": 22.0,
                            "rem_inflacion_mensual_pct_min": 2.5,
                        },
                        "tasas_ust_altas": {"ust_10y_pct_min": 4.3, "ust_5y_pct_min": 3.95},
                    },
                }
            },
        )

        self.assertTrue(summary["any_active"])
        self.assertIn("stress_soberano_local", summary["active_flags"])
        self.assertIn("inflacion_local_alta", summary["active_flags"])
        self.assertIn("tasas_ust_altas", summary["active_flags"])


if __name__ == "__main__":
    unittest.main()
