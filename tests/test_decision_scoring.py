import sys
import math
import unittest
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from decision.scoring import (
    apply_base_scores,
    blend_scores,
    build_decision_base,
    consensus_to_score,
    finalize_unified_score,
    rank_score,
    threshold_score,
)


class RankScoreTests(unittest.TestCase):
    def test_higher_is_better_assigns_top_rank_to_max_value(self) -> None:
        s = pd.Series([10.0, 50.0, 30.0])
        out = rank_score(s, higher_is_better=True)
        self.assertEqual(out.idxmax(), 1)

    def test_lower_is_better_assigns_top_rank_to_min_value(self) -> None:
        s = pd.Series([10.0, 50.0, 30.0])
        out = rank_score(s, higher_is_better=False)
        self.assertEqual(out.idxmax(), 0)

    def test_single_value_returns_neutral(self) -> None:
        out = rank_score(pd.Series([42.0]), neutral=0.5)
        self.assertAlmostEqual(float(out.iloc[0]), 0.5, places=5)

    def test_all_nan_returns_neutral(self) -> None:
        out = rank_score(pd.Series([float("nan"), float("nan")]), neutral=0.5)
        self.assertTrue((out == 0.5).all())

    def test_small_cohort_damped_toward_neutral(self) -> None:
        s = pd.Series([1.0, 100.0])
        out = rank_score(s, higher_is_better=True, neutral=0.5)
        self.assertGreater(float(out.iloc[1]), 0.5)
        self.assertLess(float(out.iloc[1]), 1.0)

    def test_output_is_in_zero_one_range(self) -> None:
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        out = rank_score(s)
        self.assertTrue((out >= 0).all())
        self.assertTrue((out <= 1).all())


class ThresholdScoreTests(unittest.TestCase):
    def test_value_at_good_threshold_scores_one(self) -> None:
        s = pd.Series([20.0])
        out = threshold_score(s, good=20.0, bad=0.0, higher_is_better=True)
        self.assertAlmostEqual(float(out.iloc[0]), 1.0, places=5)

    def test_value_at_bad_threshold_scores_zero(self) -> None:
        s = pd.Series([0.0])
        out = threshold_score(s, good=20.0, bad=0.0, higher_is_better=True)
        self.assertAlmostEqual(float(out.iloc[0]), 0.0, places=5)

    def test_midpoint_scores_approximately_half(self) -> None:
        s = pd.Series([10.0])
        out = threshold_score(s, good=20.0, bad=0.0, higher_is_better=True)
        self.assertAlmostEqual(float(out.iloc[0]), 0.5, places=5)

    def test_lower_is_better_inverts_direction(self) -> None:
        s = pd.Series([1.0, 10.0])
        out = threshold_score(s, good=1.0, bad=10.0, higher_is_better=False)
        self.assertGreater(float(out.iloc[0]), float(out.iloc[1]))

    def test_all_nan_returns_neutral(self) -> None:
        out = threshold_score(pd.Series([float("nan")]), good=10.0, bad=0.0, higher_is_better=True, neutral=0.5)
        self.assertAlmostEqual(float(out.iloc[0]), 0.5, places=5)


class BlendScoresTests(unittest.TestCase):
    def test_equal_weights_return_average(self) -> None:
        a = pd.Series([0.8])
        b = pd.Series([0.4])
        out = blend_scores(a, b, relative_weight=0.5, absolute_weight=0.5)
        self.assertAlmostEqual(float(out.iloc[0]), 0.6, places=5)

    def test_full_relative_weight_returns_relative(self) -> None:
        a = pd.Series([0.9])
        b = pd.Series([0.1])
        out = blend_scores(a, b, relative_weight=1.0, absolute_weight=0.0)
        self.assertAlmostEqual(float(out.iloc[0]), 0.9, places=5)


class ConsensusScoringTests(unittest.TestCase):
    def test_buy_returns_one(self) -> None:
        self.assertAlmostEqual(consensus_to_score("Buy"), 1.0)

    def test_sell_returns_zero(self) -> None:
        self.assertAlmostEqual(consensus_to_score("Sell"), 0.0)

    def test_hold_returns_half(self) -> None:
        self.assertAlmostEqual(consensus_to_score("Hold"), 0.5)

    def test_nan_returns_half(self) -> None:
        self.assertAlmostEqual(consensus_to_score(float("nan")), 0.5)

    def test_none_returns_half(self) -> None:
        self.assertAlmostEqual(consensus_to_score(None), 0.5)

    def test_outperform_returns_one(self) -> None:
        self.assertAlmostEqual(consensus_to_score("Outperform"), 1.0)

    def test_underperform_returns_zero(self) -> None:
        self.assertAlmostEqual(consensus_to_score("Underperform"), 0.0)

    def test_custom_taxonomy_overrides_defaults(self) -> None:
        rules = {"consensus_taxonomy": {"positive_terms": ["comprar"], "negative_terms": ["vender"], "neutral_terms": []}}
        self.assertAlmostEqual(consensus_to_score("Comprar", scoring_rules=rules), 1.0)
        self.assertAlmostEqual(consensus_to_score("Vender", scoring_rules=rules), 0.0)


class BuildDecisionBaseTests(unittest.TestCase):
    def test_infers_liquidity_flags_and_defaults_without_model_coverage(self) -> None:
        df_total = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "CAUCION",
                    "Tipo": "Liquidez",
                    "Bloque": "Liquidez",
                    "Peso_%": 20.0,
                    "Valorizado_ARS": 5000.0,
                    "Ganancia_ARS": 0.0,
                }
            ]
        )

        out = build_decision_base(
            df_total,
            pd.DataFrame(),
            pd.DataFrame(),
            mep_real=1200.0,
        )

        self.assertTrue(bool(out.loc[0, "Es_Liquidez"]))
        self.assertEqual(out.loc[0, "asset_family"], "liquidity")
        self.assertEqual(out.loc[0, "asset_subfamily"], "liquidity_other")
        self.assertEqual(out.loc[0, "Cobertura_Modelo"], "Parcial")
        self.assertAlmostEqual(float(out.loc[0, "Consensus_Final"]), 0.5, places=5)

    def test_merges_ratings_and_computes_consensus_and_mep_premium(self) -> None:
        df_total = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AAPL",
                    "Tipo": "CEDEAR",
                    "Bloque": "Growth",
                    "Peso_%": 10.0,
                    "Valorizado_ARS": 10000.0,
                    "Ganancia_ARS": 500.0,
                    "Cantidad_Real": 2.0,
                    "PPC_ARS": 4000.0,
                }
            ]
        )
        df_cedears = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AAPL",
                    "Ticker_Finviz": "AAPL",
                    "MEP_Implicito": 1100.0,
                }
            ]
        )
        df_ratings_res = pd.DataFrame(
            [{"consenso": "Acumular", "consenso_n": 4.0, "total_ratings": 5.0}],
            index=pd.Index(["AAPL"], name="Ticker_Finviz"),
        )

        out = build_decision_base(
            df_total,
            df_cedears,
            df_ratings_res,
            mep_real=1000.0,
            scoring_rules={
                "consensus_taxonomy": {
                    "positive_terms": ["acumular"],
                    "negative_terms": [],
                    "neutral_terms": [],
                }
            },
        )

        self.assertEqual(out.loc[0, "Cobertura_Modelo"], "Completa")
        self.assertAlmostEqual(float(out.loc[0, "MEP_Premium_%"]), 10.0, places=4)
        self.assertAlmostEqual(float(out.loc[0, "Consensus_Score"]), 1.0, places=5)
        self.assertAlmostEqual(float(out.loc[0, "Consensus_Strength"]), 0.8, places=5)
        self.assertAlmostEqual(float(out.loc[0, "Consensus_Final"]), 0.94, places=5)


class ApplyBaseScoresTests(unittest.TestCase):
    def _minimal_df(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"Ticker_IOL": "AAPL", "Peso_%": 5.0, "Perf Week": 1.0, "Perf Month": 3.0, "Perf YTD": 10.0},
            {"Ticker_IOL": "KO",   "Peso_%": 3.0, "Perf Week": 0.5, "Perf Month": 1.0, "Perf YTD": 4.0},
            {"Ticker_IOL": "MELI", "Peso_%": 8.0, "Perf Week": 2.0, "Perf Month": 5.0, "Perf YTD": 20.0},
        ])

    def test_output_contains_score_refuerzo_and_score_reduccion(self) -> None:
        out = apply_base_scores(self._minimal_df())
        self.assertIn("score_refuerzo", out.columns)
        self.assertIn("score_reduccion", out.columns)

    def test_scores_are_clamped_between_zero_and_one(self) -> None:
        out = apply_base_scores(self._minimal_df())
        self.assertTrue((out["score_refuerzo"].between(0, 1)).all())
        self.assertTrue((out["score_reduccion"].between(0, 1)).all())

    def test_liquidez_gets_score_despliegue_liquidez_column(self) -> None:
        df = self._minimal_df()
        df["Es_Liquidez"] = [True, False, False]
        out = apply_base_scores(df)
        self.assertIn("score_despliegue_liquidez", out.columns)
        self.assertAlmostEqual(float(out.loc[~out["Es_Liquidez"], "score_despliegue_liquidez"].iloc[0]), 0.0)

    def test_input_dataframe_is_not_mutated(self) -> None:
        df = self._minimal_df()
        original_columns = set(df.columns)
        apply_base_scores(df)
        self.assertEqual(set(df.columns), original_columns)

    def test_absolute_scoring_changes_single_name_from_neutral_relative_baseline(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AAPL",
                    "Peso_%": 5.0,
                    "Perf Week": 1.0,
                    "Perf Month": 3.0,
                    "Perf YTD": 10.0,
                    "Beta": 2.0,
                    "P/E": 40.0,
                    "ROE": 1.0,
                    "Profit Margin": 1.0,
                    "MEP_Premium_%": 20.0,
                    "Consensus_Final": 0.5,
                    "Ganancia_%": 120.0,
                    "Ganancia_ARS": 500.0,
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "Es_ETF": False,
                    "Es_Core_ETF": False,
                    "Es_FCI": False,
                }
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
                }
            },
        )

        self.assertAlmostEqual(float(relative_only.loc[0, "s_beta_ok"]), 0.5, places=5)
        self.assertAlmostEqual(float(relative_only.loc[0, "s_beta_risk"]), 0.5, places=5)
        self.assertLess(float(with_absolute.loc[0, "s_beta_ok"]), 0.5)
        self.assertGreater(float(with_absolute.loc[0, "s_beta_risk"]), 0.5)
        self.assertLess(float(with_absolute.loc[0, "score_refuerzo"]), float(relative_only.loc[0, "score_refuerzo"]))
        self.assertGreater(float(with_absolute.loc[0, "score_reduccion"]), float(relative_only.loc[0, "score_reduccion"]))


class FinalizeUnifiedScoreTests(unittest.TestCase):
    def test_uses_base_scores_when_v2_absent(self) -> None:
        df = pd.DataFrame([{"score_refuerzo": 0.7, "score_reduccion": 0.3}])
        out = finalize_unified_score(df)
        self.assertAlmostEqual(float(out["score_unificado"].iloc[0]), 0.4, places=3)

    def test_uses_v2_scores_when_present(self) -> None:
        df = pd.DataFrame([{
            "score_refuerzo": 0.7,
            "score_reduccion": 0.3,
            "score_refuerzo_v2": 0.6,
            "score_reduccion_v2": 0.5,
            "score_unificado_v2": 0.1,
        }])
        out = finalize_unified_score(df)
        self.assertAlmostEqual(float(out["score_unificado"].iloc[0]), 0.1, places=3)

    def test_result_is_rounded_to_three_decimals(self) -> None:
        df = pd.DataFrame([{"score_refuerzo": 0.6667, "score_reduccion": 0.3333}])
        out = finalize_unified_score(df)
        value = float(out["score_unificado"].iloc[0])
        self.assertEqual(round(value, 3), value)


if __name__ == "__main__":
    unittest.main()
