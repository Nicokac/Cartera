import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import zipfile

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


if __name__ == "__main__":
    unittest.main()
