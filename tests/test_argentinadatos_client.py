import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from clients.argentinadatos import get_dollar_series, get_mep_real, get_riesgo_pais_latest


class ArgentinaDatosClientTests(unittest.TestCase):
    def test_get_dollar_series_requires_list_payload(self) -> None:
        with patch("clients.argentinadatos._get_json_payload", return_value={"unexpected": True}):
            with self.assertRaises(ValueError):
                get_dollar_series(casa="mep", base_url="https://api.example/{casa}")

    def test_get_mep_real_returns_average_and_date(self) -> None:
        payload = [
            {"compra": "1400.5", "venta": "1450.5", "fecha": "2026-04-08"},
        ]
        with patch("clients.argentinadatos._get_json_payload", return_value=payload):
            mep = get_mep_real(casa="mep", base_url="https://api.example/{casa}")

        self.assertIsNotNone(mep)
        self.assertAlmostEqual(mep["compra"], 1400.5, places=2)
        self.assertAlmostEqual(mep["venta"], 1450.5, places=2)
        self.assertAlmostEqual(mep["promedio"], 1425.5, places=2)
        self.assertEqual(mep["fecha"], "2026-04-08")

    def test_get_mep_real_returns_none_on_empty_series(self) -> None:
        with patch("clients.argentinadatos._get_json_payload", return_value=[]):
            mep = get_mep_real(casa="mep", base_url="https://api.example/{casa}")

        self.assertIsNone(mep)

    def test_get_riesgo_pais_latest_requires_dict_payload(self) -> None:
        with patch("clients.argentinadatos._get_json_payload", return_value=[]):
            with self.assertRaises(ValueError):
                get_riesgo_pais_latest(base_url="https://api.example/riesgo")

    def test_get_riesgo_pais_latest_returns_none_when_valor_missing(self) -> None:
        with patch("clients.argentinadatos._get_json_payload", return_value={"fecha": "2026-04-08"}):
            payload = get_riesgo_pais_latest(base_url="https://api.example/riesgo")

        self.assertIsNone(payload)

    def test_get_riesgo_pais_latest_returns_float_payload(self) -> None:
        with patch(
            "clients.argentinadatos._get_json_payload",
            return_value={"valor": "610", "fecha": "2026-04-08"},
        ):
            payload = get_riesgo_pais_latest(base_url="https://api.example/riesgo")

        self.assertIsNotNone(payload)
        self.assertAlmostEqual(payload["valor"], 610.0, places=2)
        self.assertEqual(payload["fecha"], "2026-04-08")


if __name__ == "__main__":
    unittest.main()
