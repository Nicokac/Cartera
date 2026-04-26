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
class StrategyRulesFundamentalsTests(unittest.TestCase):
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
                    "Tipo": "AcciÃƒÂ³n Local",
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


    def test_build_decision_base_classifies_fci_as_fund_not_liquidity(self) -> None:
        df_total = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "IOLPORA",
                    "Tipo": "FCI",
                    "Bloque": "FCI",
                    "Peso_%": 3.43,
                    "Valorizado_ARS": 842426.0,
                    "Valor_USD": 595.4,
                    "Ganancia_ARS": 241053.0,
                    "Cantidad_Real": None,
                    "PPC_ARS": None,
                    "Es_Liquidez": False,
                }
            ]
        )

        decision = build_decision_base(
            df_total,
            pd.DataFrame(),
            pd.DataFrame(),
            mep_real=1415.0,
        )

        self.assertFalse(bool(decision.loc[0, "Es_Liquidez"]))
        self.assertTrue(bool(decision.loc[0, "Es_FCI"]))
        self.assertEqual(decision.loc[0, "asset_family"], "fund")
        self.assertEqual(decision.loc[0, "asset_subfamily"], "fund_other")
        self.assertEqual(decision.loc[0, "Costo_ARS"], 0.0)
        self.assertTrue(pd.isna(decision.loc[0, "Ganancia_%"]))


    def test_explanations_render_specific_fci_narrative(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "IOLPORA",
                    "Tipo": "FCI",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Es_FCI": True,
                    "asset_family": "fund",
                    "asset_subfamily": "fund_other",
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "score_despliegue_liquidez": 0.0,
                }
            ]
        )

        explained = enrich_decision_explanations(df)

        self.assertEqual(
            explained.loc[0, "motivo_score"],
            "FCI mantenido en neutral por mandato diversificado y sin scoring tactico direccional.",
        )
        self.assertEqual(
            explained.loc[0, "motivo_accion"],
            "FCI en monitoreo: vehiculo diversificado sin senal tactica dominante.",
        )


if __name__ == "__main__":
    unittest.main()

