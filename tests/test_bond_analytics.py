import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from analytics.bond_analytics import (
    build_bond_local_subfamily_summary,
    build_bond_monitor_table,
    build_bond_subfamily_summary,
    enrich_bond_analytics,
)


class BondAnalyticsTests(unittest.TestCase):
    def test_enrich_bond_analytics_derives_duration_and_days_to_maturity(self) -> None:
        df_bonds = pd.DataFrame(
            [
                {"Ticker_IOL": "GD30", "Tipo": "Bono", "Bloque": "Soberano AR", "asset_subfamily": "bond_sov_ar", "Peso_%": 3.62},
                {"Ticker_IOL": "BPOC7", "Tipo": "Bono", "Bloque": "Bopreal", "asset_subfamily": "bond_bopreal", "Peso_%": 3.33},
            ]
        )
        df_bonistas = pd.DataFrame(
            [
                {
                    "bonistas_ticker": "GD30",
                    "bonistas_tir_pct": 12.5,
                    "bonistas_paridad_pct": 78.0,
                    "bonistas_md": 3.4,
                    "bonistas_fecha_vencimiento": "09/07/2030",
                    "bonistas_fecha_emision": "04/09/2020",
                    "bonistas_tir_avg_365d_pct": 14.0,
                },
                {
                    "bonistas_ticker": "BPOC7",
                    "bonistas_tir_pct": 9.2,
                    "bonistas_paridad_pct": 85.0,
                    "bonistas_md": 1.8,
                    "bonistas_fecha_vencimiento": "31/10/2027",
                    "bonistas_fecha_emision": "01/08/2024",
                    "bonistas_tir_avg_365d_pct": 10.1,
                    "bonistas_put_flag": True,
                },
            ]
        )

        enriched = enrich_bond_analytics(
            df_bonds,
            df_bonistas,
            reference_date="2026-04-05",
            macro_variables={
                "cer_diario": 1.23,
                "tamar": 32.0,
                "badlar": 28.0,
                "riesgo_pais_bps": 710.0,
                "rem_inflacion_mensual_pct": 2.7,
            },
        )

        gd30 = enriched.loc[enriched["Ticker_IOL"] == "GD30"].iloc[0]
        bpoc7 = enriched.loc[enriched["Ticker_IOL"] == "BPOC7"].iloc[0]

        self.assertEqual(gd30["bonistas_duration_bucket"], "larga")
        self.assertEqual(bpoc7["bonistas_duration_bucket"], "media")
        self.assertGreater(gd30["bonistas_days_to_maturity"], 0)
        self.assertAlmostEqual(gd30["bonistas_tir_vs_avg_365d_pct"], -1.5, places=2)
        self.assertAlmostEqual(gd30["bonistas_parity_gap_pct"], -22.0, places=2)
        self.assertEqual(gd30["bonistas_riesgo_pais_bps"], 710.0)
        self.assertEqual(gd30["bonistas_rem_inflacion_mensual_pct"], 2.7)
        self.assertTrue(bpoc7["bonistas_put_flag"])

    def test_enrich_bond_analytics_normalizes_hard_dollar_parity_with_mep(self) -> None:
        df_bonds = pd.DataFrame(
            [
                {"Ticker_IOL": "GD30", "Tipo": "Bono", "Bloque": "Soberano AR", "asset_subfamily": "bond_sov_ar", "Peso_%": 3.62},
            ]
        )
        df_bonistas = pd.DataFrame(
            [
                {
                    "bonistas_ticker": "GD30",
                    "bonistas_precio": 90250.0,
                    "bonistas_paridad_pct": 125120.44,
                    "bonistas_valor_tecnico": 72.13,
                }
            ]
        )

        enriched = enrich_bond_analytics(
            df_bonds,
            df_bonistas,
            reference_date="2026-04-05",
            mep_real=1434.0,
        )

        gd30 = enriched.iloc[0]
        self.assertAlmostEqual(gd30["bonistas_paridad_bruta_pct"], 125120.44, places=2)
        self.assertAlmostEqual(gd30["bonistas_paridad_pct"], 87.25, places=2)
        self.assertAlmostEqual(gd30["bonistas_parity_gap_pct"], -12.75, places=2)

    def test_enrich_bond_analytics_infers_asset_subfamily_from_block_when_missing(self) -> None:
        df_bonds = pd.DataFrame(
            [
                {"Ticker_IOL": "GD30", "Tipo": "Bono", "Bloque": "Soberano AR", "Peso_%": 3.62},
                {"Ticker_IOL": "TZX26", "Tipo": "Bono", "Bloque": "CER", "Peso_%": 2.84},
                {"Ticker_IOL": "BPOC7", "Tipo": "Bono", "Bloque": "Bopreal", "Peso_%": 3.33},
                {"Ticker_IOL": "TZXD6", "Tipo": "Bono", "Bloque": "Sin clasificar", "Peso_%": 0.60},
            ]
        )

        enriched = enrich_bond_analytics(df_bonds, reference_date="2026-04-05")

        by_ticker = enriched.set_index("Ticker_IOL")["asset_subfamily"].to_dict()
        self.assertEqual(by_ticker["GD30"], "bond_sov_ar")
        self.assertEqual(by_ticker["TZX26"], "bond_cer")
        self.assertEqual(by_ticker["BPOC7"], "bond_bopreal")
        self.assertEqual(by_ticker["TZXD6"], "bond_other")

    def test_enrich_bond_analytics_normalizes_bopreal_parity_with_mep(self) -> None:
        df_bonds = pd.DataFrame(
            [
                {"Ticker_IOL": "BPOC7", "Tipo": "Bono", "Bloque": "Bopreal", "asset_subfamily": "bond_bopreal", "Peso_%": 3.33},
            ]
        )
        df_bonistas = pd.DataFrame(
            [
                {
                    "bonistas_ticker": "BPOC7",
                    "bonistas_precio": 149600.0,
                    "bonistas_paridad_pct": 146310.0,
                    "bonistas_valor_tecnico": 102.167,
                }
            ]
        )

        enriched = enrich_bond_analytics(
            df_bonds,
            df_bonistas,
            reference_date="2026-04-05",
            mep_real=1434.0,
        )

        bpoc7 = enriched.iloc[0]
        self.assertAlmostEqual(bpoc7["bonistas_paridad_bruta_pct"], 146310.0, places=2)
        self.assertAlmostEqual(bpoc7["bonistas_paridad_pct"], 102.11, places=2)
        self.assertAlmostEqual(bpoc7["bonistas_parity_gap_pct"], 2.11, places=2)

    def test_build_bond_subfamily_summary_aggregates_core_metrics(self) -> None:
        df = pd.DataFrame(
            [
                {"Ticker_IOL": "GD30", "asset_subfamily": "bond_sov_ar", "bonistas_tir_pct": 12.0, "bonistas_paridad_pct": 78.0, "bonistas_md": 3.0, "bonistas_days_to_maturity": 1500},
                {"Ticker_IOL": "AL30", "asset_subfamily": "bond_sov_ar", "bonistas_tir_pct": 13.0, "bonistas_paridad_pct": 76.0, "bonistas_md": 2.8, "bonistas_days_to_maturity": 1400},
                {"Ticker_IOL": "BPOC7", "asset_subfamily": "bond_bopreal", "bonistas_tir_pct": 9.0, "bonistas_paridad_pct": 85.0, "bonistas_md": 1.5, "bonistas_days_to_maturity": 600},
            ]
        )

        summary = build_bond_subfamily_summary(df)

        self.assertEqual(len(summary), 2)
        sov = summary.loc[summary["asset_subfamily"] == "bond_sov_ar"].iloc[0]
        self.assertEqual(sov["Instrumentos"], 2)
        self.assertAlmostEqual(sov["TIR_Promedio"], 12.5, places=2)

    def test_enrich_bond_analytics_infers_local_subfamily_without_touching_operational_taxonomy(self) -> None:
        df_bonds = pd.DataFrame(
            [
                {"Ticker_IOL": "GD30", "Tipo": "Bono", "Bloque": "Soberano AR", "asset_subfamily": "bond_sov_ar"},
                {"Ticker_IOL": "BPOC7", "Tipo": "Bono", "Bloque": "Bopreal", "asset_subfamily": "bond_bopreal"},
                {"Ticker_IOL": "TZX26", "Tipo": "Bono", "Bloque": "CER", "asset_subfamily": "bond_cer"},
                {"Ticker_IOL": "TTJ26", "Tipo": "Bono", "Bloque": "Sin clasificar", "asset_subfamily": "bond_other"},
                {"Ticker_IOL": "TZV26", "Tipo": "Bono", "Bloque": "Sin clasificar", "asset_subfamily": "bond_other"},
                {"Ticker_IOL": "TMF27", "Tipo": "Bono", "Bloque": "Sin clasificar", "asset_subfamily": "bond_other"},
            ]
        )

        enriched = enrich_bond_analytics(df_bonds, reference_date="2026-04-05")
        local_map = enriched.set_index("Ticker_IOL")["bonistas_local_subfamily"].to_dict()
        operational_map = enriched.set_index("Ticker_IOL")["asset_subfamily"].to_dict()

        self.assertEqual(local_map["GD30"], "bond_hard_dollar")
        self.assertEqual(local_map["BPOC7"], "bond_bopreal")
        self.assertEqual(local_map["TZX26"], "bond_cer")
        self.assertEqual(local_map["TTJ26"], "bond_dual")
        self.assertEqual(local_map["TZV26"], "bond_dollar_linked")
        self.assertEqual(local_map["TMF27"], "bond_tamar")
        self.assertEqual(operational_map["TTJ26"], "bond_other")

    def test_build_bond_local_subfamily_summary_aggregates_local_taxonomy(self) -> None:
        df = pd.DataFrame(
            [
                {"Ticker_IOL": "GD30", "bonistas_local_subfamily": "bond_hard_dollar", "bonistas_tir_pct": 9.0, "bonistas_paridad_pct": 87.0, "bonistas_md": 2.0},
                {"Ticker_IOL": "AL30", "bonistas_local_subfamily": "bond_hard_dollar", "bonistas_tir_pct": 10.0, "bonistas_paridad_pct": 85.0, "bonistas_md": 2.2},
                {"Ticker_IOL": "BPOC7", "bonistas_local_subfamily": "bond_bopreal", "bonistas_tir_pct": 3.4, "bonistas_paridad_pct": 102.0, "bonistas_md": 1.2},
            ]
        )

        summary = build_bond_local_subfamily_summary(df)

        self.assertEqual(len(summary), 2)
        hard_dollar = summary.loc[summary["bonistas_local_subfamily"] == "bond_hard_dollar"].iloc[0]
        self.assertEqual(hard_dollar["Instrumentos"], 2)
        self.assertAlmostEqual(hard_dollar["TIR_Promedio"], 9.5, places=2)
        self.assertAlmostEqual(hard_dollar["Paridad_Promedio"], 86.0, places=2)

    def test_build_bond_monitor_table_returns_relevant_columns(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "GD30",
                    "Tipo": "Bono",
                    "Bloque": "Soberano AR",
                    "asset_subfamily": "bond_sov_ar",
                    "bonistas_local_subfamily": "bond_hard_dollar",
                    "Peso_%": 3.62,
                    "bonistas_tir_pct": 12.5,
                    "bonistas_paridad_pct": 78.0,
                    "bonistas_md": 3.4,
                    "bonistas_duration_bucket": "larga",
                    "bonistas_days_to_maturity": 1500,
                    "bonistas_tir_vs_avg_365d_pct": -1.5,
                    "bonistas_parity_gap_pct": -22.0,
                    "bonistas_put_flag": False,
                }
            ]
        )

        monitor = build_bond_monitor_table(df)

        self.assertEqual(len(monitor), 1)
        self.assertIn("bonistas_duration_bucket", monitor.columns)
        self.assertIn("bonistas_tir_pct", monitor.columns)
        self.assertIn("bonistas_local_subfamily", monitor.columns)


if __name__ == "__main__":
    unittest.main()
