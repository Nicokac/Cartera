import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
for _p in (str(SRC), str(SCRIPTS)):
    if _p not in sys.path:
        sys.path.append(_p)

from report_sections_risk import _build_risk_focus_block


def _risk_row(
    ticker: str = "AAPL",
    drawdown: float = -10.0,
    volatilidad: float = 1.5,
    retorno: float = 20.0,
    peso: float = 5.0,
    observaciones: int = 10,
    calidad: str = "Robusta",
) -> dict:
    return {
        "Ticker_IOL": ticker,
        "Tipo": "CEDEAR",
        "Bloque": "Growth",
        "Base_Riesgo": "Precio_ARS",
        "Drawdown_Max_%": drawdown,
        "Volatilidad_Diaria_%": volatilidad,
        "Retorno_Acum_%": retorno,
        "Peso_%": peso,
        "Observaciones": observaciones,
        "Calidad_Historia": calidad,
    }


class BuildRiskFocusBlockTests(unittest.TestCase):
    def test_empty_dataframe_returns_empty_message_div(self) -> None:
        html = _build_risk_focus_block(
            pd.DataFrame(),
            title="Riesgo de mercado",
            empty_message="Sin posiciones.",
        )
        self.assertIn("empty", html)
        self.assertIn("Sin posiciones.", html)
        self.assertNotIn("focus-columns", html)

    def test_non_empty_returns_risk_subsection_div(self) -> None:
        df = pd.DataFrame([_risk_row()])
        html = _build_risk_focus_block(df, title="Riesgo de mercado", empty_message="Sin posiciones.")
        self.assertIn("risk-subsection", html)

    def test_non_empty_contains_three_focus_columns(self) -> None:
        df = pd.DataFrame([_risk_row()])
        html = _build_risk_focus_block(df, title="Riesgo", empty_message="")
        self.assertIn("Mayores drawdowns", html)
        self.assertIn("Mayor volatilidad", html)
        self.assertIn("Mejor rendimiento", html)

    def test_title_appears_in_output(self) -> None:
        df = pd.DataFrame([_risk_row()])
        html = _build_risk_focus_block(df, title="Renta Variable", empty_message="")
        self.assertIn("Renta Variable", html)

    def test_title_is_html_escaped(self) -> None:
        df = pd.DataFrame([_risk_row()])
        html = _build_risk_focus_block(df, title="<script>", empty_message="")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_empty_message_is_html_escaped(self) -> None:
        html = _build_risk_focus_block(
            pd.DataFrame(),
            title="T",
            empty_message="<b>vacio</b>",
        )
        self.assertNotIn("<b>", html)
        self.assertIn("&lt;b&gt;", html)

    def test_ticker_with_worst_drawdown_appears_prominently(self) -> None:
        df = pd.DataFrame([
            _risk_row(ticker="BAD", drawdown=-40.0),
            _risk_row(ticker="OK", drawdown=-5.0),
        ])
        html = _build_risk_focus_block(df, title="T", empty_message="")
        drawdown_section_start = html.find("Mayores drawdowns")
        rendimiento_section_start = html.find("Mejor rendimiento")
        bad_in_drawdown = html.find("BAD", drawdown_section_start, rendimiento_section_start)
        self.assertGreater(bad_in_drawdown, -1, "Ticker con peor drawdown debe aparecer en la sección de drawdowns")

    def test_returns_string(self) -> None:
        html = _build_risk_focus_block(pd.DataFrame(), title="T", empty_message="vacio")
        self.assertIsInstance(html, str)


if __name__ == "__main__":
    unittest.main()
