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
class StrategyRulesTechnicalScoringTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

