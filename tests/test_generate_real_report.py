import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from generate_real_report import (
    build_real_bonistas_bundle,
    load_local_env,
    prompt_money_ars,
    prompt_yes_no,
    resolve_iol_credentials,
)


class GenerateRealReportTests(unittest.TestCase):
    def test_load_local_env_parses_simple_env_file_without_overriding_existing_env(self) -> None:
        env_path = ROOT / "tests" / "snapshots" / "tmp_test.env"
        env_path.write_text(
            "# comment\n"
            "IOL_USERNAME=usuario@example.com\n"
            "IOL_PASSWORD='secret-pass'\n",
            encoding="utf-8",
        )
        self.addCleanup(lambda: env_path.unlink(missing_ok=True))

        with patch.dict("os.environ", {"IOL_USERNAME": "prioridad@env.com"}, clear=False):
            loaded = load_local_env(env_path)
            self.assertEqual(loaded["IOL_USERNAME"], "usuario@example.com")
            self.assertEqual(loaded["IOL_PASSWORD"], "secret-pass")
            self.assertEqual(resolve_iol_credentials()[0], "prioridad@env.com")

    def test_resolve_iol_credentials_uses_prompt_as_fallback(self) -> None:
        with patch("generate_real_report.load_local_env", return_value={}), patch.dict("os.environ", {}, clear=True), patch(
            "builtins.input", return_value="prompt-user@example.com"
        ), patch("generate_real_report.getpass", return_value="prompt-pass"):
            username, password = resolve_iol_credentials()

        self.assertEqual(username, "prompt-user@example.com")
        self.assertEqual(password, "prompt-pass")

    def test_prompt_yes_no_retries_until_valid_answer(self) -> None:
        with patch("builtins.input", side_effect=["quizas", "s"]), patch("builtins.print") as print_mock:
            result = prompt_yes_no("Confirmar?", default=False)

        self.assertTrue(result)
        print_mock.assert_called_with("Respuesta invalida. Ingresa 's' o 'n'.")

    def test_prompt_money_ars_retries_on_invalid_and_negative_values(self) -> None:
        with patch("builtins.input", side_effect=["abc", "-5", "$600.000"]), patch("builtins.print") as print_mock:
            result = prompt_money_ars("Monto")

        self.assertEqual(result, 600000.0)
        self.assertEqual(print_mock.call_count, 2)

    def test_build_real_bonistas_bundle_accepts_mep_real_and_returns_bundle(self) -> None:
        df_bonos = pd.DataFrame(
            [
                {"Ticker_IOL": "GD30", "Tipo": "Bono", "Bloque": "Soberano AR", "asset_subfamily": "bond_sov_ar", "Peso_%": 3.62}
            ]
        )

        with patch("generate_real_report.get_bonds_for_portfolio", return_value=pd.DataFrame([{"bonistas_ticker": "GD30"}])), patch(
            "generate_real_report.get_macro_variables", return_value={"cer_diario": 738.025}
        ), patch(
            "generate_real_report.get_riesgo_pais_latest", return_value={"valor": 765.0, "fecha": "2026-04-05"}
        ), patch(
            "generate_real_report.get_rem_latest",
            return_value={
                "inflacion_mensual_pct": 2.7,
                "inflacion_12m_pct": 24.6,
                "periodo": "Febrero De 2026",
                "fecha_publicacion": "5 de marzo de 2026",
            },
        ), patch(
            "generate_real_report.get_bcra_monetary_context",
            return_value={
                "reservas_bcra_musd": 28384.0,
                "a3500_mayorista": 1387.72,
                "badlar": 28.31,
                "tamar": 26.31,
            },
        ), patch(
            "generate_real_report.get_ust_latest",
            return_value={
                "ust_date": "2026-04-08",
                "ust_5y_pct": 3.95,
                "ust_10y_pct": 4.33,
                "ust_spread_10y_5y_pct": 0.38,
            },
        ), patch(
            "generate_real_report.get_bond_volume_context",
            return_value=pd.DataFrame(
                [
                    {
                        "Ticker_IOL": "GD30",
                        "bonistas_volume_last": 1500000.0,
                        "bonistas_volume_avg_20d": 1200000.0,
                        "bonistas_volume_ratio": 1.25,
                        "bonistas_liquidity_bucket": "alta",
                    }
                ]
            ),
        ), patch("generate_real_report.enrich_bond_analytics", return_value=df_bonos.copy()) as enrich_mock, patch(
            "generate_real_report.build_bond_monitor_table", return_value=pd.DataFrame([{"Ticker_IOL": "GD30"}])
        ), patch(
            "generate_real_report.build_bond_subfamily_summary",
            return_value=pd.DataFrame([{"asset_subfamily": "bond_sov_ar", "Instrumentos": 1}]),
        ), patch(
            "generate_real_report.build_bond_local_subfamily_summary",
            return_value=pd.DataFrame([{"bonistas_local_subfamily": "bond_hard_dollar", "Instrumentos": 1}]),
        ):
            bundle = build_real_bonistas_bundle(df_bonos, mep_real=1434.0)

        self.assertIn("bond_monitor", bundle)
        self.assertIn("bond_subfamily_summary", bundle)
        self.assertIn("bond_local_subfamily_summary", bundle)
        self.assertIn("macro_variables", bundle)
        self.assertEqual(bundle["macro_variables"]["cer_diario"], 738.025)
        self.assertEqual(bundle["macro_variables"]["riesgo_pais_bps"], 765.0)
        self.assertEqual(bundle["macro_variables"]["rem_inflacion_mensual_pct"], 2.7)
        self.assertEqual(bundle["macro_variables"]["rem_inflacion_12m_pct"], 24.6)
        self.assertEqual(bundle["macro_variables"]["reservas_bcra_musd"], 28384.0)
        self.assertEqual(bundle["macro_variables"]["a3500_mayorista"], 1387.72)
        self.assertEqual(bundle["macro_variables"]["badlar"], 28.31)
        self.assertEqual(bundle["macro_variables"]["tamar"], 26.31)
        self.assertEqual(bundle["macro_variables"]["ust_status"], "ok")
        enrich_mock.assert_called_once()
        self.assertEqual(enrich_mock.call_args.kwargs["mep_real"], 1434.0)

    def test_build_real_bonistas_bundle_marks_ust_status_when_fred_fails(self) -> None:
        df_bonos = pd.DataFrame(
            [
                {"Ticker_IOL": "GD30", "Tipo": "Bono", "Bloque": "Soberano AR", "asset_subfamily": "bond_sov_ar", "Peso_%": 3.62}
            ]
        )

        with patch("generate_real_report.get_bonds_for_portfolio", return_value=pd.DataFrame([{"bonistas_ticker": "GD30"}])), patch(
            "generate_real_report.get_macro_variables", return_value={"cer_diario": 738.025}
        ), patch(
            "generate_real_report.get_riesgo_pais_latest", return_value=None
        ), patch(
            "generate_real_report.get_rem_latest", return_value=None
        ), patch(
            "generate_real_report.get_bcra_monetary_context", return_value={}
        ), patch(
            "generate_real_report.get_ust_latest", side_effect=RuntimeError("FRED caido")
        ), patch(
            "generate_real_report.get_bond_volume_context", return_value=pd.DataFrame()
        ), patch("generate_real_report.enrich_bond_analytics", return_value=df_bonos.copy()), patch(
            "generate_real_report.build_bond_monitor_table", return_value=pd.DataFrame()
        ), patch(
            "generate_real_report.build_bond_subfamily_summary", return_value=pd.DataFrame()
        ), patch(
            "generate_real_report.build_bond_local_subfamily_summary", return_value=pd.DataFrame()
        ):
            bundle = build_real_bonistas_bundle(df_bonos, mep_real=1434.0)

        self.assertEqual(bundle["macro_variables"]["ust_status"], "error")
        self.assertIn("FRED caido", bundle["macro_variables"]["ust_error"])

    def test_real_report_bond_context_columns_include_bcra_macro_fields(self) -> None:
        bond_analytics = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "GD30",
                    "bonistas_local_subfamily": "bond_hard_dollar",
                    "bonistas_tir_pct": 7.8,
                    "bonistas_paridad_pct": 87.2,
                    "bonistas_md": 2.05,
                    "bonistas_days_to_maturity": 1556,
                    "bonistas_tir_vs_avg_365d_pct": -2.7,
                    "bonistas_parity_gap_pct": -12.8,
                    "bonistas_put_flag": False,
                    "bonistas_riesgo_pais_bps": 609.0,
                    "bonistas_reservas_bcra_musd": 43381.0,
                    "bonistas_a3500_mayorista": 1387.72,
                    "bonistas_rem_inflacion_mensual_pct": 2.7,
                    "bonistas_rem_inflacion_12m_pct": 22.2,
                    "bonistas_ust_5y_pct": 3.94,
                    "bonistas_ust_10y_pct": 4.31,
                    "bonistas_spread_vs_ust_pct": 3.9,
                }
            ]
        )
        final_decision = pd.DataFrame([{"Ticker_IOL": "GD30"}])
        bond_context_cols = [
            "Ticker_IOL",
            "bonistas_local_subfamily",
            "bonistas_tir_pct",
            "bonistas_paridad_pct",
            "bonistas_md",
            "bonistas_days_to_maturity",
            "bonistas_tir_vs_avg_365d_pct",
            "bonistas_parity_gap_pct",
            "bonistas_put_flag",
            "bonistas_riesgo_pais_bps",
            "bonistas_reservas_bcra_musd",
            "bonistas_a3500_mayorista",
            "bonistas_rem_inflacion_mensual_pct",
            "bonistas_rem_inflacion_12m_pct",
            "bonistas_ust_5y_pct",
            "bonistas_ust_10y_pct",
            "bonistas_spread_vs_ust_pct",
        ]

        merged = final_decision.merge(
            bond_analytics[[col for col in bond_context_cols if col in bond_analytics.columns]].copy(),
            on="Ticker_IOL",
            how="left",
        )

        self.assertEqual(merged.loc[0, "bonistas_reservas_bcra_musd"], 43381.0)
        self.assertAlmostEqual(merged.loc[0, "bonistas_a3500_mayorista"], 1387.72, places=2)


if __name__ == "__main__":
    unittest.main()
