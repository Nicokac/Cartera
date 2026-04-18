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

from report_operations import (
    build_executive_summary,
    build_operations_explanations,
    build_operations_summary,
)


class ReportOperationsTests(unittest.TestCase):
    def test_build_operations_explanations_returns_empty_for_empty_frame(self) -> None:
        items = build_operations_explanations(pd.DataFrame(), current_portfolio=pd.DataFrame())

        self.assertEqual(items, [])

    def test_build_operations_explanations_detects_unresolved_symbol(self) -> None:
        recent_operations = pd.DataFrame(
            [
                {
                    "simbolo": "S31G6",
                    "tipo": "Compra",
                    "operation_bucket": "trading",
                    "fecha_evento": pd.Timestamp("2026-04-16 12:55:00"),
                    "monto_final": 119009,
                    "operation_currency": "ARS",
                }
            ]
        )

        items = build_operations_explanations(recent_operations, current_portfolio=pd.DataFrame())

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["kicker"], "S31G6")
        self.assertIn("no reflejado", items[0]["title"])
        self.assertIn("/portafolio actual", items[0]["detail"])

    def test_build_executive_summary_includes_transition_symbols(self) -> None:
        summary = build_executive_summary(
            action_counts={},
            decision_memory={},
            changed_actions=[],
            operations_bundle={
                "position_transitions": {
                    "summary": pd.DataFrame([{"simbolo": "AL30"}, {"simbolo": "GOOGL"}])
                },
                "recent_trades": pd.DataFrame([{"simbolo": "S31G6"}]),
            },
            asignacion_final=pd.DataFrame([{"Ticker_IOL": "XLU"}]),
            current_tickers={"AL30", "GOOGL"},
        )

        self.assertIn("AL30, GOOGL", summary)
        self.assertIn("S31G6", summary)
        self.assertIn("XLU", summary)

    def test_build_operations_summary_renders_stats_and_snapshot(self) -> None:
        html = build_operations_summary(
            {
                "recent_operations": pd.DataFrame(
                    [
                        {
                            "numero": 1,
                            "fecha_evento": pd.Timestamp("2026-04-16 12:54:19"),
                            "tipo": "Compra",
                            "estado": "terminada",
                            "mercado": "BCBA",
                            "simbolo": "GOOGL",
                            "operation_bucket": "trading",
                            "operation_currency": "ARS",
                            "cantidad_final": 14,
                            "precio_final": 8440,
                            "monto_final": 118160,
                            "plazo": "a24horas",
                        }
                    ]
                ),
                "recent_trades": pd.DataFrame(
                    [
                        {
                            "simbolo": "S31G6",
                            "tipo": "Compra",
                            "fecha_evento": pd.Timestamp("2026-04-16 12:55:00"),
                            "monto_final": 119009,
                            "operation_currency": "ARS",
                            "cantidad_final": 102127,
                            "estado": "terminada",
                        }
                    ]
                ),
                "recent_events": pd.DataFrame(
                    [
                        {
                            "simbolo": "DIA US$",
                            "tipo": "Pago de Dividendos",
                            "fecha_evento": pd.Timestamp("2026-04-13 15:39:00"),
                            "monto_final": 0.06,
                            "operation_currency": "USD",
                            "estado": "terminada",
                        }
                    ]
                ),
                "symbol_summary": pd.DataFrame(
                    [
                        {
                            "simbolo": "GOOGL",
                            "tipo": "Compra",
                            "operaciones": 1,
                            "ultima_fecha": pd.Timestamp("2026-04-16 12:54:19"),
                            "monto_total": 118160,
                            "cantidad_total": 14,
                        }
                    ]
                ),
                "position_transitions": {"items": [], "summary": pd.DataFrame()},
                "stats": {"total": 2, "trading": 1, "events": 1, "completed": 2},
                "previous_snapshot_date": "2026-04-15",
            },
            current_tickers={"GOOGL"},
            current_portfolio=pd.DataFrame(),
        )

        self.assertIn("Total: <strong>2</strong>", html)
        self.assertIn("Snapshot previo: <strong>2026-04-15</strong>", html)
        self.assertIn("Operaciones recientes fuera de cartera actual", html)
        self.assertIn("S31G6", html)
        self.assertIn("Ver tabla completa de operaciones", html)


if __name__ == "__main__":
    unittest.main()
