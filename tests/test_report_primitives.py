import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from report_primitives import (
    badge_class,
    build_table,
    fmt_ars,
    metric_class,
    truncate_text,
)


class ReportPrimitivesTests(unittest.TestCase):
    def test_fmt_ars_formats_correctly(self) -> None:
        self.assertEqual(fmt_ars(1234.56), "$1,235")

    def test_fmt_ars_returns_dash_on_nan(self) -> None:
        self.assertEqual(fmt_ars(float("nan")), "-")

    def test_metric_class_rsi_zones(self) -> None:
        self.assertEqual(metric_class("RSI_14", 55), "metric metric-positive")
        self.assertEqual(metric_class("RSI_14", 72), "metric metric-warn")
        self.assertEqual(metric_class("RSI_14", 82), "metric metric-negative")

    def test_badge_class_maps_actions(self) -> None:
        self.assertEqual(badge_class("Refuerzo"), "badge badge-buy")
        self.assertEqual(badge_class("Reducir"), "badge badge-sell")
        self.assertEqual(badge_class("Desplegar liquidez"), "badge badge-fund")
        self.assertEqual(badge_class("Mantener / Neutral"), "badge badge-neutral")

    def test_build_table_returns_html_with_headers(self) -> None:
        html = build_table(pd.DataFrame([{"Ticker": "GOOGL", "Monto": "$1,000"}]))

        self.assertIn('<th scope="col">Ticker</th>', html)
        self.assertIn('<th scope="col">Monto</th>', html)
        self.assertIn("<td>GOOGL</td>", html)
        self.assertIn("<td>$1,000</td>", html)

    def test_truncate_text_respects_word_boundary(self) -> None:
        self.assertEqual(truncate_text("hola mundo cruel", 10), "hola...")
        self.assertEqual(truncate_text("corto", 10), "corto")


if __name__ == "__main__":
    unittest.main()
