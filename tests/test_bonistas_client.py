import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from clients.bonistas_client import (
    _infer_bonistas_subfamily,
    _parse_instrument_html,
    get_macro_variables,
    get_bonds_for_portfolio,
    normalize_bonistas_ticker,
)


class BonistasClientTests(unittest.TestCase):
    def test_normalize_bonistas_ticker_defaults_to_uppercase(self) -> None:
        self.assertEqual(normalize_bonistas_ticker("gd30"), "GD30")
        self.assertEqual(normalize_bonistas_ticker("  al30 "), "AL30")

    def test_get_bonds_for_portfolio_returns_canonical_columns(self) -> None:
        fake_rows = [
            {
                "bonistas_ticker": "GD30",
                "bonistas_source_url": "https://bonistas.com/bono-cotizacion-rendimiento-precio-hoy/GD30",
                "bonistas_source_section": "instrument",
                "bonistas_parse_status": "ok",
                "bonistas_tir_pct": 12.0,
                "bonistas_paridad_pct": 60.0,
                "bonistas_md": 4.5,
                "bonistas_fecha_vencimiento": "09/01/2030",
                "bonistas_valor_tecnico": 100.0,
                "bonistas_put_flag": False,
                "bonistas_fetched_at": "2026-04-05T00:00:00+00:00",
            },
            {
                "bonistas_ticker": "BPOC7",
                "bonistas_source_url": "https://bonistas.com/bono-cotizacion-rendimiento-precio-hoy/BPOC7",
                "bonistas_source_section": "instrument",
                "bonistas_parse_status": "ok",
                "bonistas_tir_pct": 9.0,
                "bonistas_paridad_pct": 80.0,
                "bonistas_md": 2.0,
                "bonistas_fecha_vencimiento": "31/10/2027",
                "bonistas_valor_tecnico": 100.0,
                "bonistas_put_flag": True,
                "bonistas_fetched_at": "2026-04-05T00:00:00+00:00",
            },
        ]

        with patch("clients.bonistas_client.get_instrument_data", side_effect=fake_rows):
            df = get_bonds_for_portfolio(["GD30", "BPOC7"], use_cache=False)

        expected = {
            "bonistas_ticker",
            "bonistas_source_url",
            "bonistas_source_section",
            "bonistas_parse_status",
            "bonistas_tir_pct",
            "bonistas_paridad_pct",
            "bonistas_md",
            "bonistas_fecha_vencimiento",
            "bonistas_valor_tecnico",
            "bonistas_put_flag",
            "bonistas_fetched_at",
        }

        self.assertEqual(len(df), 2)
        self.assertTrue(expected.issubset(df.columns))
        self.assertSetEqual(set(df["bonistas_ticker"]), {"GD30", "BPOC7"})

    def test_infer_bonistas_subfamily_from_ticker_prefix(self) -> None:
        self.assertEqual(_infer_bonistas_subfamily("GD30"), "bond_hard_dollar")
        self.assertEqual(_infer_bonistas_subfamily("AL30"), "bond_hard_dollar")
        self.assertEqual(_infer_bonistas_subfamily("TZX26"), "bond_cer")
        self.assertEqual(_infer_bonistas_subfamily("BPOC7"), "bond_bopreal")
        self.assertEqual(_infer_bonistas_subfamily("TTM26"), "bond_dual")

    def test_parse_instrument_html_extracts_priority_fields(self) -> None:
        html = """
        <h1>GD30C</h1>
        <div>Precio</div><div>59.69</div>
        <div>Variación diaria</div><div>-1.71%</div>
        <div>TIR</div><div>10.36%</div>
        <div>Paridad</div><div>82.77%</div>
        <div>MD</div><div>2.02</div>
        <div>Fecha Emisión</div><div>4/9/2020</div>
        <div>Fecha Vencimiento</div><div>9/7/2030</div>
        <div>Valor Técnico</div><div>72.11</div>
        <div>TIR Promedio (en 365 días)</div><div>12.03%</div>
        <div>TIR Min (en 365 días)</div><div>8.30%</div>
        <div>TIR Max (en 365 días)</div><div>27.67%</div>
        <div>TIR-1</div><div>+2.0%</div>
        <div>TIR+1</div><div>-1.9%</div>
        """

        parsed = _parse_instrument_html("GD30", html)

        self.assertEqual(parsed["bonistas_ticker"], "GD30")
        self.assertEqual(parsed["bonistas_subfamily"], "bond_hard_dollar")
        self.assertEqual(parsed["bonistas_parse_status"], "ok")
        self.assertEqual(parsed["bonistas_tir_pct"], 10.36)
        self.assertEqual(parsed["bonistas_paridad_pct"], 82.77)
        self.assertEqual(parsed["bonistas_md"], 2.02)
        self.assertEqual(parsed["bonistas_fecha_vencimiento"], "9/7/2030")
        self.assertEqual(parsed["bonistas_valor_tecnico"], 72.11)

    def test_get_macro_variables_parses_reference_values_from_variables_page(self) -> None:
        html = """
        <h1>Variables de Referencia</h1>
        <div>CER</div><div>738.0250</div>
        <div>TAMAR</div><div>26.31%</div>
        <div>BADLAR</div><div>25.37%</div>
        <div>Inflacion Mensual</div><div>2.90%</div>
        <div>Inflacion Interanual</div><div>33.10%</div>
        <div>Inflacion Esperada (REM)</div><div>22.30%</div>
        """

        with patch("clients.bonistas_client._fetch_html", return_value=html):
            payload = get_macro_variables(use_cache=False)

        self.assertEqual(payload["bonistas_parse_status"], "ok")
        self.assertAlmostEqual(payload["cer_diario"], 738.025, places=3)
        self.assertAlmostEqual(payload["tamar"], 26.31, places=2)
        self.assertAlmostEqual(payload["badlar"], 25.37, places=2)

    def test_get_macro_variables_discards_implausible_badlar_value(self) -> None:
        html = """
        <h1>Variables de Referencia</h1>
        <div>CER</div><div>738.0250</div>
        <div>TAMAR</div><div>26.31%</div>
        <div>BADLAR</div><div>1.00%</div>
        """

        with patch("clients.bonistas_client._fetch_html", return_value=html):
            payload = get_macro_variables(use_cache=False)

        self.assertAlmostEqual(payload["cer_diario"], 738.025, places=3)
        self.assertAlmostEqual(payload["tamar"], 26.31, places=2)
        self.assertIsNone(payload["badlar"])


if __name__ == "__main__":
    unittest.main()
