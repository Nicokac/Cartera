import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from decision.action_constants import (
    ACTION_DESPLEGAR_LIQUIDEZ,
    ACTION_MANTENER_NEUTRAL,
    ACTION_REDUCIR,
    ACTION_REFUERZO,
)
from decision.actions import assign_base_action, assign_action_v2, enrich_decision_explanations


def _row(
    *,
    ticker: str = "X",
    es_liquidez: bool = False,
    es_bono: bool = False,
    es_fci: bool = False,
    score_refuerzo: float = 0.5,
    score_reduccion: float = 0.5,
    score_despliegue: float = 0.0,
) -> dict:
    return {
        "Ticker_IOL": ticker,
        "Es_Liquidez": es_liquidez,
        "Es_Bono": es_bono,
        "Es_FCI": es_fci,
        "score_refuerzo": score_refuerzo,
        "score_reduccion": score_reduccion,
        "score_despliegue_liquidez": score_despliegue,
    }


class AssignBaseActionTests(unittest.TestCase):
    def _df(self, rows: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(rows)

    def test_refuerzo_assigned_when_score_and_gap_meet_threshold(self) -> None:
        df = self._df([_row(score_refuerzo=0.75, score_reduccion=0.60)])
        out = assign_base_action(df)
        self.assertEqual(out["accion_sugerida"].iloc[0], ACTION_REFUERZO)

    def test_reduccion_assigned_when_reduccion_score_dominates(self) -> None:
        df = self._df([_row(score_refuerzo=0.55, score_reduccion=0.70)])
        out = assign_base_action(df)
        self.assertEqual(out["accion_sugerida"].iloc[0], ACTION_REDUCIR)

    def test_neutral_when_scores_tied_within_gap(self) -> None:
        df = self._df([_row(score_refuerzo=0.68, score_reduccion=0.65)])
        out = assign_base_action(df)
        self.assertEqual(out["accion_sugerida"].iloc[0], ACTION_MANTENER_NEUTRAL)

    def test_neutral_when_score_below_threshold(self) -> None:
        df = self._df([_row(score_refuerzo=0.55, score_reduccion=0.40)])
        out = assign_base_action(df)
        self.assertEqual(out["accion_sugerida"].iloc[0], ACTION_MANTENER_NEUTRAL)

    def test_bono_cannot_get_refuerzo_or_reduccion(self) -> None:
        df = self._df([_row(es_bono=True, score_refuerzo=0.90, score_reduccion=0.20)])
        out = assign_base_action(df)
        self.assertEqual(out["accion_sugerida"].iloc[0], ACTION_MANTENER_NEUTRAL)

    def test_liquidez_cannot_get_refuerzo_or_reduccion(self) -> None:
        df = self._df([_row(es_liquidez=True, score_refuerzo=0.90, score_reduccion=0.20, score_despliegue=0.3)])
        out = assign_base_action(df)
        self.assertNotIn(out["accion_sugerida"].iloc[0], {ACTION_REFUERZO, ACTION_REDUCIR})

    def test_desplegar_liquidez_assigned_when_threshold_met(self) -> None:
        df = self._df([_row(es_liquidez=True, score_despliegue=0.65)])
        out = assign_base_action(df)
        self.assertEqual(out["accion_sugerida"].iloc[0], ACTION_DESPLEGAR_LIQUIDEZ)

    def test_custom_action_rules_override_thresholds(self) -> None:
        df = self._df([_row(score_refuerzo=0.70, score_reduccion=0.50)])
        rules = {"refuerzo_threshold": 0.80, "score_gap_min": 0.10}
        out = assign_base_action(df, action_rules=rules)
        self.assertEqual(out["accion_sugerida"].iloc[0], ACTION_MANTENER_NEUTRAL)

    def test_assign_action_v2_uses_v2_score_columns(self) -> None:
        df = pd.DataFrame([{
            "Ticker_IOL": "A",
            "Es_Liquidez": False,
            "Es_Bono": False,
            "score_refuerzo_v2": 0.80,
            "score_reduccion_v2": 0.55,
            "score_despliegue_liquidez": 0.0,
        }])
        out = assign_action_v2(df)
        self.assertIn("accion_sugerida_v2", out.columns)
        self.assertEqual(out["accion_sugerida_v2"].iloc[0], ACTION_REFUERZO)

    def test_multiple_rows_each_get_correct_action(self) -> None:
        df = self._df([
            _row(ticker="R", score_refuerzo=0.80, score_reduccion=0.50),
            _row(ticker="D", score_refuerzo=0.50, score_reduccion=0.80),
            _row(ticker="N", score_refuerzo=0.55, score_reduccion=0.55),
        ])
        out = assign_base_action(df).set_index("Ticker_IOL")
        self.assertEqual(out.loc["R", "accion_sugerida"], ACTION_REFUERZO)
        self.assertEqual(out.loc["D", "accion_sugerida"], ACTION_REDUCIR)
        self.assertEqual(out.loc["N", "accion_sugerida"], ACTION_MANTENER_NEUTRAL)


class EnrichDecisionExplanationsTests(unittest.TestCase):
    def _base_row(self, overrides: dict | None = None) -> dict:
        row = {
            "Ticker_IOL": "X",
            "Es_Liquidez": False,
            "Es_Bono": False,
            "Es_FCI": False,
            "asset_subfamily": "stock_growth",
            "accion_sugerida": ACTION_MANTENER_NEUTRAL,
            "accion_sugerida_v2": ACTION_MANTENER_NEUTRAL,
            "score_refuerzo": 0.5,
            "score_reduccion": 0.5,
            "score_despliegue_liquidez": 0.0,
            "Momentum_Refuerzo": 0.5,
            "Momentum_Reduccion": 0.5,
            "Momentum_Reduccion_Effective": 0.5,
            "s_consensus_good": 0.5,
            "s_consensus_bad": 0.5,
            "s_low_weight": 0.5,
            "s_high_weight": 0.5,
            "s_beta_ok": 0.5,
            "s_beta_risk": 0.5,
            "s_mep_ok": 0.5,
            "s_mep_premium": 0.5,
            "s_pe_ok": 0.5,
            "s_pe_expensive": 0.5,
        }
        if overrides:
            row.update(overrides)
        return row

    def _enrich(self, overrides: dict | None = None) -> pd.Series:
        df = pd.DataFrame([self._base_row(overrides)])
        return enrich_decision_explanations(df).iloc[0]

    def test_columns_motivo_score_and_motivo_accion_are_added(self) -> None:
        row = self._enrich()
        self.assertIn("motivo_score", row.index)
        self.assertIn("motivo_accion", row.index)

    def test_driver_columns_are_added(self) -> None:
        row = self._enrich()
        self.assertIn("driver_1", row.index)
        self.assertIn("driver_2", row.index)
        self.assertIn("driver_3", row.index)

    def test_motivo_score_for_fci_contains_fci_keyword(self) -> None:
        row = self._enrich({"Es_FCI": True})
        self.assertIn("FCI", row["motivo_score"])

    def test_motivo_score_for_bono_contains_bono_keyword(self) -> None:
        row = self._enrich({"Es_Bono": True})
        self.assertIn("bono", row["motivo_score"].lower())

    def test_motivo_accion_refuerzo_growth_mentions_refuerzo(self) -> None:
        row = self._enrich({
            "asset_subfamily": "stock_growth",
            "accion_sugerida_v2": ACTION_REFUERZO,
            "Momentum_Refuerzo": 0.75,
        })
        self.assertIn("Refuerzo", row["motivo_accion"])

    def test_motivo_accion_reduccion_mentions_reduccion(self) -> None:
        row = self._enrich({
            "asset_subfamily": "stock_growth",
            "accion_sugerida_v2": ACTION_REDUCIR,
            "Momentum_Reduccion_Effective": 0.70,
        })
        self.assertIn("Reduccion", row["motivo_accion"])

    def test_motivo_accion_desplegar_liquidez_mentions_liquidez(self) -> None:
        row = self._enrich({
            "Es_Liquidez": True,
            "accion_sugerida_v2": ACTION_DESPLEGAR_LIQUIDEZ,
        })
        self.assertIn("liquidez", row["motivo_accion"].lower())

    def test_motivo_accion_fci_neutral_mentions_fci(self) -> None:
        row = self._enrich({
            "Es_FCI": True,
            "accion_sugerida_v2": ACTION_MANTENER_NEUTRAL,
        })
        self.assertIn("FCI", row["motivo_accion"])

    def test_original_columns_are_preserved(self) -> None:
        df = pd.DataFrame([self._base_row()])
        out = enrich_decision_explanations(df)
        self.assertIn("Ticker_IOL", out.columns)
        self.assertIn("score_refuerzo", out.columns)


if __name__ == "__main__":
    unittest.main()
