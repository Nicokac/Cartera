import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from clients.bonistas_client import get_bonds_for_portfolio, normalize_bonistas_ticker


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


if __name__ == "__main__":
    unittest.main()
