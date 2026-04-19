import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

import src
from pipeline import (
    build_dashboard_bundle,
    build_decision_bundle,
    build_portfolio_bundle,
    build_prediction_bundle,
    build_sizing_bundle,
)
from smoke_run import run_smoke_pipeline


class PipelineSmokeTests(unittest.TestCase):
    def test_pipeline_exports_are_importable(self) -> None:
        self.assertTrue(callable(build_portfolio_bundle))
        self.assertTrue(callable(build_dashboard_bundle))
        self.assertTrue(callable(build_decision_bundle))
        self.assertTrue(callable(build_prediction_bundle))
        self.assertTrue(callable(build_sizing_bundle))

    def test_src_package_exports_are_importable(self) -> None:
        self.assertTrue(callable(src.build_portfolio_bundle))
        self.assertTrue(callable(src.build_dashboard_bundle))
        self.assertTrue(callable(src.build_decision_bundle))
        self.assertTrue(callable(src.build_prediction_bundle))
        self.assertTrue(callable(src.build_sizing_bundle))

    def test_smoke_pipeline_returns_coherent_bundles(self) -> None:
        result = run_smoke_pipeline()

        self.assertIn("portfolio_bundle", result)
        self.assertIn("decision_bundle", result)
        self.assertIn("sizing_bundle", result)
        self.assertIn("dashboard_bundle", result)
        self.assertIn("prediction_bundle", result)

        df_total = result["portfolio_bundle"]["df_total"]
        final_decision = result["decision_bundle"]["final_decision"]
        asignacion_final = result["sizing_bundle"]["asignacion_final"]
        predictions = result["prediction_bundle"]["predictions"]

        self.assertFalse(df_total.empty)
        self.assertFalse(final_decision.empty)
        self.assertFalse(predictions.empty)
        self.assertIn("Ticker_IOL", df_total.columns)
        self.assertIn("accion_sugerida_v2", final_decision.columns)
        self.assertIn("ticker", predictions.columns)
        self.assertIn("direction", predictions.columns)
        self.assertGreater(df_total["Valorizado_ARS"].sum(), 0)
        self.assertAlmostEqual(float(df_total["Peso_%"].sum()), 100.0, delta=0.5)
        self.assertTrue(
            ("Ticker_IOL" in asignacion_final.columns and not asignacion_final.empty)
            or asignacion_final.empty
        )


if __name__ == "__main__":
    unittest.main()
