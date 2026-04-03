import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from decision.actions import assign_action_v2
from decision.scoring import apply_base_scores, apply_technical_overlay_scores, build_technical_overlay_scores, consensus_to_score


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

        scored = apply_base_scores(df)

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


if __name__ == "__main__":
    unittest.main()
