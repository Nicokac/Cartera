import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from clients.bcra import get_rem_latest


class BcraClientTests(unittest.TestCase):
    def test_get_rem_latest_parses_monthly_inflation_expectation(self) -> None:
        html = """
        <html>
        <body>
        <h2>RESUMEN EJECUTIVO | FEBRERO DE 2026</h2>
        <p>En el segundo relevamiento del año, quienes participaron del REM estimaron una inflación mensual de 2,7% para febrero.</p>
        <p>Publicado el día 5 de marzo de 2026.</p>
        </body>
        </html>
        """

        with patch("clients.bcra._fetch_text", return_value=html):
            payload = get_rem_latest(base_url="https://www.bcra.gob.ar/relevamiento-expectativas-mercado-rem/")

        self.assertIsNotNone(payload)
        self.assertAlmostEqual(payload["inflacion_mensual_pct"], 2.7, places=2)
        self.assertEqual(payload["periodo"], "Febrero De 2026")
        self.assertEqual(payload["fecha_publicacion"], "5 de marzo de 2026")


if __name__ == "__main__":
    unittest.main()
