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
class StrategyRulesNarrativeTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

