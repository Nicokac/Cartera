import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
for _p in (str(SRC), str(SCRIPTS)):
    if _p not in sys.path:
        sys.path.append(_p)

from decision.action_constants import ACTION_REDUCIR, ACTION_REFUERZO
from report_sections_prediction import (
    build_prediction_section,
    build_prediction_signal_table,
)


def _prediction_row(
    ticker: str = "AAPL",
    direction: str = "up",
    confidence: float = 0.35,
    action: str = ACTION_REFUERZO,
    votes: object = None,
    outcome_date: str = "2026-05-01",
) -> dict[str, object]:
    return {
        "ticker": ticker,
        "direction": direction,
        "confidence": confidence,
        "consensus_raw": "x",
        "score_unificado": 0.1,
        "accion_sugerida_v2": action,
        "outcome_date": outcome_date,
        "signal_votes": votes if votes is not None else {"rsi": 1, "momentum_20d": 0},
    }


class BuildPredictionSignalTableTests(unittest.TestCase):
    def test_empty_dataframe_returns_empty_message(self) -> None:
        html = build_prediction_signal_table(pd.DataFrame())
        self.assertIn("empty", html)
        self.assertIn("Sin datos para mostrar.", html)

    def test_renders_vote_matrix_and_escapes_ticker(self) -> None:
        df = pd.DataFrame(
            [
                _prediction_row(
                    ticker="<T&K>",
                    direction="down",
                    votes="rsi:+1|momentum_20d:-1|adx:0",
                    action=ACTION_REDUCIR,
                )
            ]
        )
        html = build_prediction_signal_table(df)
        self.assertIn("&lt;T&amp;K&gt;", html)
        self.assertIn("Baja", html)
        self.assertIn("sig sig-pos", html)
        self.assertIn("sig sig-neg", html)
        self.assertIn("sig sig-neu", html)
        self.assertIn(ACTION_REDUCIR, html)
        self.assertIn("2026-05-01", html)
        self.assertIn('<th scope="col">Ticker</th>', html)
        self.assertIn('<th scope="col">Fecha objetivo</th>', html)

    def test_handles_invalid_votes_and_missing_confidence(self) -> None:
        df = pd.DataFrame(
            [
                _prediction_row(
                    ticker="BADDICT",
                    direction="up",
                    confidence=float("nan"),
                    votes={"rsi": "bad-number"},
                ),
                _prediction_row(
                    ticker="BADSTR",
                    direction="down",
                    confidence=0.25,
                    votes="rsi:abc|momentum_20d:+1",
                ),
            ]
        )
        html = build_prediction_signal_table(df)
        self.assertIn("<strong>BADDICT</strong>", html)
        self.assertIn("<strong>BADSTR</strong>", html)
        self.assertIn("<td>-</td>", html)
        self.assertIn("sig sig-neu", html)
        self.assertIn("sig sig-pos", html)


class BuildPredictionSectionTests(unittest.TestCase):
    def test_returns_empty_when_predictions_are_missing_or_empty(self) -> None:
        self.assertEqual(build_prediction_section({}), "")
        self.assertEqual(build_prediction_section({"predictions": pd.DataFrame()}), "")

    def test_renders_summary_focus_and_signal_table(self) -> None:
        predictions = pd.DataFrame(
            [
                _prediction_row("AAA", "up", 0.40, ACTION_REFUERZO, {"rsi": 1, "adx": 1}),
                _prediction_row("BBB", "down", 0.30, ACTION_REDUCIR, {"rsi": -1}),
                _prediction_row("CCC", "neutral", 0.20, ACTION_REFUERZO, "-"),
            ]
        )
        html = build_prediction_section(
            {
                "predictions": predictions,
                "summary": {
                    "total": 3,
                    "up": 1,
                    "down": 1,
                    "neutral": 1,
                    "mean_confidence": 0.30,
                    "previous_directional_mean_confidence": 0.25,
                    "previous_directional_run_date": "2026-04-30",
                    "classifier_b_agreement_pct": 66.67,
                    "classifier_b_agreement_delta": 6.67,
                    "previous_classifier_b_run_date": "2026-04-30",
                    "direction_count_delta_up": 2,
                    "direction_count_delta_down": -1,
                    "direction_count_delta_neutral": -1,
                    "previous_direction_counts_run_date": "2026-04-30",
                },
                "config": {"horizon_days": 10},
                "accuracy": {
                    "global": {"completed": 12, "accuracy_pct": 58.33},
                    "by_family": [
                        {"asset_family": "stock", "completed": 8, "accuracy_pct": 62.5},
                        {"asset_family": "bond", "completed": 4, "accuracy_pct": 50.0},
                    ],
                    "by_score_band": [
                        {"score_band": "Alto (>= 0.15)", "completed": 6, "accuracy_pct": 66.67},
                        {"score_band": "Neutro (-0.15 a 0.15)", "completed": 4, "accuracy_pct": 50.0},
                    ],
                    "by_horizon": [
                        {"horizon_days": 5, "completed": 9, "accuracy_pct": 55.56},
                        {"horizon_days": 10, "completed": 3, "accuracy_pct": 66.67},
                    ],
                    "calibration_readiness": [
                        {"asset_family": "stock", "up": 12, "down": 8, "neutral": 10, "min_count": 8, "required": 30, "ready": False},
                    ],
                },
            }
        )

        self.assertIn('id="prediccion"', html)
        self.assertIn("Total: <strong>3</strong>", html)
        self.assertIn("Suba: <strong>1</strong>", html)
        self.assertIn("Baja: <strong>1</strong>", html)
        self.assertIn("Neutral: <strong>1</strong>", html)
        self.assertIn("30.00%", html)
        self.assertIn("Confianza media suba: <strong>40.00%</strong>", html)
        self.assertIn("Confianza media baja: <strong>30.00%</strong>", html)
        self.assertIn("Confianza media dir (up/down): <strong>35.00%</strong>", html)
        self.assertIn("Δ confianza dir vs previa: <strong class=\"money-positive\">+10.00 pp</strong> (2026-04-30)", html)
        self.assertIn("66.67%", html)
        self.assertIn("Δ clasificador B vs previa: <strong class=\"money-positive\">+6.67 pp</strong> (2026-04-30)", html)
        self.assertIn(
            "Δ conteo dir vs previa: Suba <strong class=\"money-positive\">+2</strong> | Baja <strong class=\"money-negative\">-1</strong> | Neutral <strong class=\"money-negative\">-1</strong> (2026-04-30)",
            html,
        )
        self.assertIn("10 ruedas", html)
        self.assertIn("Se\u00f1ales de suba", html)
        self.assertIn("signal-table", html)
        self.assertIn("Acierto hist\u00f3rico (global)", html)
        self.assertIn("Acierto por familia", html)
        self.assertIn("58.33%", html)
        self.assertIn("stock", html)
        self.assertIn("Acierto por banda de score", html)
        self.assertIn("Alto (&gt;= 0.15)", html)
        self.assertIn("Acierto por horizonte", html)
        self.assertIn("5 ruedas", html)
        self.assertIn("Preparaci\u00f3n calibraci\u00f3n por familia", html)
        self.assertIn("Pendiente", html)
        self.assertIn("conviction-chip conviction-alta", html)
        self.assertIn("40.00%", html)
        self.assertIn("No impacta la calidad operativa", html)

    def test_warns_when_action_contradicts_direction(self) -> None:
        predictions = pd.DataFrame(
            [
                _prediction_row("AAA", "down", 0.40, ACTION_REFUERZO, "rsi:+1|momentum_20d:-1"),
                _prediction_row("BBB", "up", 0.30, ACTION_REDUCIR, {"rsi": 1}),
                _prediction_row("CCC", "neutral", 0.20, ACTION_REFUERZO, "-"),
            ]
        )
        html = build_prediction_section({"predictions": predictions, "summary": {}, "config": {}})

        self.assertIn("⚠ Refuerzo", html)
        self.assertIn("⚠ Reducir", html)

    def test_keeps_placeholder_action_without_warning(self) -> None:
        predictions = pd.DataFrame(
            [
                _prediction_row("AAA", "up", 0.25, "-", {"rsi": 1}),
            ]
        )
        html = build_prediction_section({"predictions": predictions, "summary": {}, "config": {}})
        self.assertIn("<td>-</td>", html)
        self.assertNotIn("\u26a0 -", html)

    def test_directional_mean_confidence_shows_dash_without_up_or_down(self) -> None:
        predictions = pd.DataFrame(
            [
                _prediction_row("AAA", "neutral", 0.25, "-", {"rsi": 0}),
                _prediction_row("BBB", "neutral", 0.10, "-", {"rsi": 0}),
            ]
        )
        html = build_prediction_section(
            {
                "predictions": predictions,
                "summary": {"total": 2, "up": 0, "down": 0, "neutral": 2, "mean_confidence": 0.175},
                "config": {"horizon_days": 5},
            }
        )
        self.assertIn("Confianza media suba: <strong>-</strong>", html)
        self.assertIn("Confianza media baja: <strong>-</strong>", html)
        self.assertIn("Confianza media dir (up/down): <strong>-</strong>", html)
        self.assertIn("Δ confianza dir vs previa: <strong class=\"money-neutral\">-</strong>", html)
        self.assertIn("Δ clasificador B vs previa: <strong class=\"money-neutral\">-</strong>", html)
        self.assertIn(
            "Δ conteo dir vs previa: Suba <strong class=\"money-neutral\">-</strong> | Baja <strong class=\"money-neutral\">-</strong> | Neutral <strong class=\"money-neutral\">-</strong>",
            html,
        )


if __name__ == "__main__":
    unittest.main()
