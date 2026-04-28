import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch
import zipfile
import requests

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from clients.bcra import discover_tamar_variable_ids, get_bcra_monetary_context, get_rem_latest


class BcraClientTests(unittest.TestCase):
    def test_fetch_json_retries_on_timeout(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}

        with patch("clients.bcra.requests.get", side_effect=[requests.Timeout("timeout"), response]) as get_mock, patch(
            "clients.bcra.time.sleep"
        ) as sleep_mock:
            from clients.bcra import _fetch_json

            payload = _fetch_json("https://api.bcra.gob.ar/test")

        self.assertEqual(payload, {"ok": True})
        self.assertEqual(get_mock.call_count, 2)
        sleep_mock.assert_called_once()

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

    def test_get_rem_latest_returns_none_when_monthly_pattern_is_missing(self) -> None:
        html = """
        <html>
        <body>
        <h2>RESUMEN EJECUTIVO | FEBRERO DE 2026</h2>
        <p>Contenido sin patron de inflacion mensual reconocible.</p>
        </body>
        </html>
        """

        with patch("clients.bcra._fetch_text", return_value=html):
            payload = get_rem_latest(base_url="https://www.bcra.gob.ar/relevamiento-expectativas-mercado-rem/")

        self.assertIsNone(payload)

    def test_get_rem_latest_parses_12m_inflation_from_excel(self) -> None:
        html = """
        <html>
        <body>
        <h2>RESUMEN EJECUTIVO | FEBRERO DE 2026</h2>
        <p>En el segundo relevamiento del año, quienes participaron del REM estimaron una inflación mensual de 2,7% para febrero.</p>
        <p>Publicado el día 5 de marzo de 2026.</p>
        </body>
        </html>
        """
        workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Indicadores Principales" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""
        workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
        shared_strings = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="2" uniqueCount="2">
  <si><t>Precios minoristas (IPC-GBA; INDEC); var. % i.a. próx. 12 meses</t></si>
  <si><t>Mediana</t></si>
</sst>"""
        sheet_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="16"><c r="A16" t="s"><v>0</v></c></row>
    <row r="17"><c r="A17" t="s"><v>1</v></c><c r="C17"><v>24.6</v></c></row>
  </sheetData>
</worksheet>"""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("xl/workbook.xml", workbook_xml)
            zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            zf.writestr("xl/sharedStrings.xml", shared_strings)
            zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)

        with patch("clients.bcra._fetch_text", return_value=html), patch(
            "clients.bcra._fetch_bytes", return_value=buffer.getvalue()
        ):
            payload = get_rem_latest(
                base_url="https://www.bcra.gob.ar/relevamiento-expectativas-mercado-rem/",
                xlsx_url="https://www.bcra.gob.ar/archivos/Pdfs/Estadisticas/Base%20de%20Resultados%20del%20REM%20web.xlsx",
            )

        self.assertIsNotNone(payload)
        self.assertAlmostEqual(payload["inflacion_12m_pct"], 24.6, places=2)

    def test_discover_tamar_variable_ids_finds_private_bank_tna_and_tea(self) -> None:
        catalog = {
            "results": [
                {"idVariable": 136, "descripcion": "TAMAR en pesos de bancos privados (en % n.a.)", "categoria": "Series.xlsm"},
                {"idVariable": 44, "descripcion": "Tasa de interes TAMAR de bancos privados (en % n.a.)", "categoria": "Principales Variables"},
                {"idVariable": 137, "descripcion": "TAMAR en pesos de bancos privados (en % e.a.)", "categoria": "Series.xlsm"},
                {"idVariable": 45, "descripcion": "Tasa de interés TAMAR de bancos privados (en % e.a.)", "categoria": "Principales Variables"},
                {"idVariable": 77, "descripcion": "BADLAR en pesos de bancos privados (en % n.a.)"},
            ]
        }

        with patch("clients.bcra._fetch_json", return_value=catalog):
            payload = discover_tamar_variable_ids(base_url="https://api.bcra.gob.ar/estadisticas/v4.0/monetarias")

        self.assertEqual(payload["tamar_tna_id"], 44)
        self.assertEqual(payload["tamar_tea_id"], 45)

    def test_get_bcra_monetary_context_returns_reservas_a3500_badlar_and_tamar(self) -> None:
        def fake_fetch_json(url: str, *, timeout: int = 10):
            if "limit=3000" in url:
                return {
                    "results": [
                        {"idVariable": 1, "descripcion": "Reservas internacionales", "categoria": "Principales Variables", "ultFechaInformada": "2026-04-04", "ultValorInformado": 28384},
                        {"idVariable": 5, "descripcion": "Tipo de cambio mayorista de referencia", "categoria": "Principales Variables", "ultFechaInformada": "2026-04-04", "ultValorInformado": 1387.72},
                        {"idVariable": 7, "descripcion": "Tasa de interés BADLAR de bancos privados", "categoria": "Principales Variables", "ultFechaInformada": "2026-04-04", "ultValorInformado": 28.31},
                        {"idVariable": 35, "descripcion": "Tasa de interés BADLAR de bancos privados", "categoria": "Principales Variables", "ultFechaInformada": "2026-04-04", "ultValorInformado": 32.44},
                        {"idVariable": 44, "descripcion": "Tasa de interes TAMAR de bancos privados (en % n.a.)", "categoria": "Principales Variables", "ultFechaInformada": "2026-04-04", "ultValorInformado": 26.31},
                        {"idVariable": 45, "descripcion": "Tasa de interés TAMAR de bancos privados (en % e.a.)", "categoria": "Principales Variables", "ultFechaInformada": "2026-04-04", "ultValorInformado": 30.11},
                    ]
                }
            raise AssertionError(f"URL inesperada: {url}")

        with patch("clients.bcra._fetch_json", side_effect=fake_fetch_json):
            payload = get_bcra_monetary_context(
                base_url="https://api.bcra.gob.ar/estadisticas/v4.0/monetarias",
                reservas_id=1,
                a3500_id=5,
                badlar_tna_id=7,
                badlar_tea_id=35,
            )

        self.assertAlmostEqual(payload["reservas_bcra_musd"], 28384.0, places=2)
        self.assertAlmostEqual(payload["a3500_mayorista"], 1387.72, places=2)
        self.assertAlmostEqual(payload["badlar"], 28.31, places=2)
        self.assertAlmostEqual(payload["badlar_tea"], 32.44, places=2)
        self.assertAlmostEqual(payload["tamar"], 26.31, places=2)
        self.assertAlmostEqual(payload["tamar_tea"], 30.11, places=2)
        self.assertEqual(payload["tamar_tna_id"], 44)
        self.assertEqual(payload["tamar_tea_id"], 45)


if __name__ == "__main__":
    unittest.main()
