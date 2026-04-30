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
                },
                "config": {"horizon_days": 10},
                "accuracy": {
                    "global": {"completed": 12, "accuracy_pct": 58.33},
                    "by_family": [
                        {"asset_family": "stock", "completed": 8, "accuracy_pct": 62.5},
                        {"asset_family": "bond", "completed": 4, "accuracy_pct": 50.0},
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
        self.assertIn("10 ruedas", html)
        self.assertIn("Se", html)
        self.assertIn("signal-table", html)
        self.assertIn("Acierto histórico (global)", html)
        self.assertIn("Acierto por familia", html)
        self.assertIn("58.33%", html)
        self.assertIn("stock", html)

    def test_warns_when_action_contradicts_direction(self) -> None:
        predictions = pd.DataFrame(
            [
                _prediction_row("AAA", "down", 0.40, ACTION_REFUERZO, "rsi:+1|momentum_20d:-1"),
                _prediction_row("BBB", "up", 0.30, ACTION_REDUCIR, {"rsi": 1}),
                _prediction_row("CCC", "neutral", 0.20, ACTION_REFUERZO, "-"),
            ]
        )
        html = build_prediction_section({"predictions": predictions, "summary": {}, "config": {}})

        self.assertTrue(("\u26a0 Refuerzo" in html) or ("âš\xa0 Refuerzo" in html))
        self.assertTrue(("\u26a0 Reducir" in html) or ("âš\xa0 Reducir" in html))

    def test_keeps_placeholder_action_without_warning(self) -> None:
        predictions = pd.DataFrame(
            [
                _prediction_row("AAA", "up", 0.25, "-", {"rsi": 1}),
            ]
        )
        html = build_prediction_section({"predictions": predictions, "summary": {}, "config": {}})
        self.assertIn("<td>-</td>", html)
        self.assertNotIn("\u26a0 -", html)


if __name__ == "__main__":
    unittest.main()
