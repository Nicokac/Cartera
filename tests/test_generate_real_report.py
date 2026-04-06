import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from generate_real_report import build_real_bonistas_bundle, load_local_env, resolve_iol_credentials


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
        enrich_mock.assert_called_once()
        self.assertEqual(enrich_mock.call_args.kwargs["mep_real"], 1434.0)


if __name__ == "__main__":
    unittest.main()
