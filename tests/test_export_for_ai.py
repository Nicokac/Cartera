from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pandas as pd

from scripts import export_for_ai


class ExportForAiTests(unittest.TestCase):
    def test_find_latest_date_uses_latest_snapshot_file(self) -> None:
        original_dir = export_for_ai.SNAPSHOTS_DIR
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "2026-04-20_real_decision_table.csv").write_text("Ticker_IOL\nAAPL\n", encoding="utf-8")
            (tmp_path / "2026-04-22_real_decision_table.csv").write_text("Ticker_IOL\nMSFT\n", encoding="utf-8")
            (tmp_path / "ignore.csv").write_text("x\n", encoding="utf-8")
            export_for_ai.SNAPSHOTS_DIR = tmp_path
            try:
                self.assertEqual(export_for_ai.find_latest_date(), "2026-04-22")
            finally:
                export_for_ai.SNAPSHOTS_DIR = original_dir

    def test_build_curated_omits_missing_columns(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "run_date": "2026-04-22",
                    "Ticker_IOL": "AAPL",
                    "Tipo": "CEDEAR",
                    "score_unificado": 0.12,
                    "extra": "ignored",
                }
            ]
        )

        with redirect_stdout(StringIO()):
            curated = export_for_ai.build_curated(df)

        self.assertEqual(curated.columns.tolist(), ["run_date", "Ticker_IOL", "Tipo", "score_unificado"])
        self.assertEqual(curated.loc[0, "Ticker_IOL"], "AAPL")

    def test_enrich_with_predictions_handles_empty_history(self) -> None:
        df = pd.DataFrame([{"Ticker_IOL": "AAPL"}])

        enriched = export_for_ai.enrich_with_predictions(df, pd.DataFrame())

        self.assertIn("pred_direction", enriched.columns)
        self.assertIn("pred_confidence", enriched.columns)
        self.assertIn("pred_conviction_label", enriched.columns)
        self.assertIsNone(enriched.loc[0, "pred_direction"])

    def test_enrich_with_context_preserves_existing_regime_flags_when_boolean_columns_are_missing(self) -> None:
        df = pd.DataFrame([{"Ticker_IOL": "AAPL", "market_regime_flags": "inflacion_alta"}])

        enriched = export_for_ai.enrich_with_context(
            df,
            {"mep_real": 1415.0, "total_ars": 1000.0},
            {"liquidez_desplegable_total_ars": 250.0},
            "2026-04-22",
        )

        self.assertEqual(enriched.loc[0, "market_regime_flags"], "inflacion_alta")
        self.assertEqual(enriched.loc[0, "mep_real"], 1415.0)

    def test_enrich_with_context_marks_missing_regime_sources(self) -> None:
        df = pd.DataFrame([{"Ticker_IOL": "AAPL"}])

        enriched = export_for_ai.enrich_with_context(df, {}, {}, "2026-04-22")

        self.assertEqual(enriched.loc[0, "market_regime_flags"], "sin_columnas_regimen")


if __name__ == "__main__":
    unittest.main()
