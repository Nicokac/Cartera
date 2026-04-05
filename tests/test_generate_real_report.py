import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from generate_real_report import build_real_bonistas_bundle


class GenerateRealReportTests(unittest.TestCase):
    def test_build_real_bonistas_bundle_accepts_mep_real_and_returns_bundle(self) -> None:
        df_bonos = pd.DataFrame(
            [
                {"Ticker_IOL": "GD30", "Tipo": "Bono", "Bloque": "Soberano AR", "asset_subfamily": "bond_sov_ar", "Peso_%": 3.62}
            ]
        )

        with patch("generate_real_report.get_bonds_for_portfolio", return_value=pd.DataFrame([{"bonistas_ticker": "GD30"}])), patch(
            "generate_real_report.get_macro_variables", return_value={"cer_diario": 738.025}
        ), patch("generate_real_report.enrich_bond_analytics", return_value=df_bonos.copy()) as enrich_mock, patch(
            "generate_real_report.build_bond_monitor_table", return_value=pd.DataFrame([{"Ticker_IOL": "GD30"}])
        ), patch(
            "generate_real_report.build_bond_subfamily_summary",
            return_value=pd.DataFrame([{"asset_subfamily": "bond_sov_ar", "Instrumentos": 1}]),
        ):
            bundle = build_real_bonistas_bundle(df_bonos, mep_real=1434.0)

        self.assertIn("bond_monitor", bundle)
        self.assertIn("bond_subfamily_summary", bundle)
        self.assertIn("macro_variables", bundle)
        self.assertEqual(bundle["macro_variables"]["cer_diario"], 738.025)
        enrich_mock.assert_called_once()
        self.assertEqual(enrich_mock.call_args.kwargs["mep_real"], 1434.0)


if __name__ == "__main__":
    unittest.main()
