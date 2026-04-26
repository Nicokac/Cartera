import unittest

import pandas as pd

from tests.report_render_test_utils import build_minimal_result as _build_minimal_result, render_report


class ReportRenderOperationsTests(unittest.TestCase):
    def test_render_report_shows_operations_section_when_bundle_has_data(self) -> None:
        result = _build_minimal_result()
        result["portfolio_bundle"]["df_total"] = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "GOOGL",
                    "Tipo": "CEDEAR",
                    "Bloque": "Growth",
                    "Valorizado_ARS": 118160.0,
                    "Valor_USD": 98.47,
                    "Ganancia_ARS": 100.0,
                    "Peso_%": 2.0,
                }
            ]
        )
        result["operations_bundle"] = {
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
                        "simbolo": "GOOGL",
                        "tipo": "Compra",
                        "fecha_evento": pd.Timestamp("2026-04-16 12:54:19"),
                        "monto_final": 118160,
                        "cantidad_final": 14,
                        "estado": "terminada",
                        "plazo": "a24horas",
                    }
                ]
            ),
            "recent_events": pd.DataFrame(
                [
                    {
                        "simbolo": "DIA US$",
                        "tipo": "Pago de Dividendos",
                        "operation_bucket": "evento",
                        "fecha_evento": pd.Timestamp("2026-04-13 15:39:56"),
                        "monto_final": 0.06,
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
            "position_transitions": {
                "items": [
                    {
                        "kicker": "GOOGL",
                        "title": "Posición ampliada",
                        "detail": "GOOGL paso de 20 a 34 unidades. Peso actual 2.00%. Se alinea con una compra reciente del 2026-04-16 12:54 por $118,160.",
                        "badge": "Compra",
                    }
                ],
                "summary": pd.DataFrame(
                    [
                        {
                            "simbolo": "GOOGL",
                            "cambio": "aumento_posicion",
                            "detalle": "GOOGL paso de 20 a 34 unidades. Peso actual 2.00%. Se alinea con una compra reciente del 2026-04-16 12:54 por $118,160.",
                        }
                    ]
                ),
            },
            "previous_snapshot_date": "2026-04-15",
            "stats": {"total": 2, "trading": 1, "events": 1, "completed": 2},
        }

        html = render_report(result)

        self.assertIn('href="#operaciones"', html)
        self.assertIn(">Operaciones<", html)
        self.assertIn("Operaciones recientes", html)
        self.assertIn("Lectura operacional", html)
        self.assertIn("Compras y ventas recientes", html)
        self.assertIn("Dividendos y amortizaciones", html)
        self.assertIn("Ver tabla completa de operaciones", html)
        self.assertIn("Moneda", html)
        self.assertIn("Precio final", html)
        self.assertIn("Monto final", html)
        self.assertIn("Ver resumen por símbolo", html)
        self.assertIn("Snapshot previo", html)
        self.assertIn("Ver cambios contra snapshot previo", html)
        self.assertIn("Impacto en cartera", html)
        self.assertNotIn("Compra reciente ya visible en cartera", html)


    def test_render_report_builds_operational_panorama_summary_when_inputs_are_available(self) -> None:
        result = _build_minimal_result()
        result["portfolio_bundle"]["df_total"] = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "GOOGL",
                    "Tipo": "CEDEAR",
                    "Bloque": "Growth",
                    "Valorizado_ARS": 118160.0,
                    "Valor_USD": 98.47,
                    "Ganancia_ARS": 100.0,
                    "Peso_%": 2.0,
                }
            ]
        )
        result["decision_bundle"]["final_decision"] = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "XLV",
                    "Tipo": "CEDEAR",
                    "asset_family": "etf",
                    "asset_subfamily": "etf_sector",
                    "Peso_%": 0.54,
                    "score_unificado": 0.248,
                    "accion_sugerida_v2": "Refuerzo",
                    "motivo_accion": "Refuerzo sectorial.",
                    "motivo_score": "Score.",
                    "driver_1": "peso",
                    "driver_2": "beta",
                    "driver_3": "mep",
                    "accion_previa": "Mantener / Neutral",
                    "score_delta_vs_dia_anterior": 0.035,
                    "dias_consecutivos_refuerzo": 1,
                    "dias_consecutivos_reduccion": 0,
                    "dias_consecutivos_mantener": 0,
                }
            ]
        )
        result["sizing_bundle"]["asignacion_final"] = pd.DataFrame(
            [{"Ticker_IOL": "XLV", "Peso_Fondeo_%": 100.0, "Monto_ARS": 100000.0, "Monto_USD": 80.0}]
        )
        result["operations_bundle"] = {
            "recent_operations": pd.DataFrame(),
            "recent_trades": pd.DataFrame(
                [
                    {"simbolo": "S31G6", "tipo": "Compra", "fecha_evento": pd.Timestamp("2026-04-16 12:54:19"), "monto_final": 119008.59, "cantidad_final": 102127}
                ]
            ),
            "recent_events": pd.DataFrame(),
            "symbol_summary": pd.DataFrame(),
            "position_transitions": {
                "items": [],
                "summary": pd.DataFrame(
                    [{"simbolo": "GOOGL", "cambio": "aumento_posicion", "detalle": "GOOGL paso de 20 a 34 unidades."}]
                ),
            },
            "stats": {"total": 1, "trading": 1, "events": 0, "completed": 1},
        }

        html = render_report(result)

        self.assertIn("Cambios de señal en XLV.", html)
        self.assertIn("Movimientos ya visibles en cartera: GOOGL.", html)
        self.assertIn("Pendiente de consolidación en cartera: S31G6.", html)
        self.assertIn("Sizing activo en XLV.", html)


    def test_render_report_formats_usd_passive_events_in_operations(self) -> None:
        result = _build_minimal_result()
        result["operations_bundle"] = {
            "recent_operations": pd.DataFrame(
                [
                    {
                        "numero": 1,
                        "fecha_evento": pd.Timestamp("2026-04-13 15:39:56"),
                        "tipo": "Pago de Dividendos",
                        "estado": "terminada",
                        "mercado": "BCBA",
                        "simbolo": "DIA US$",
                        "operation_currency": "USD",
                        "cantidad_final": None,
                        "precio_final": None,
                        "monto_final": 0.06,
                        "plazo": "inmediata",
                    }
                ]
            ),
            "recent_trades": pd.DataFrame(),
            "recent_events": pd.DataFrame(
                [
                    {
                        "simbolo": "DIA US$",
                        "tipo": "Pago de Dividendos",
                        "fecha_evento": pd.Timestamp("2026-04-13 15:39:56"),
                        "monto_final": 0.06,
                        "operation_currency": "USD",
                        "estado": "terminada",
                    }
                ]
            ),
            "symbol_summary": pd.DataFrame(),
            "stats": {"total": 1, "trading": 0, "events": 1, "completed": 1},
        }

        html = render_report(result)

        self.assertIn("USD 0.06", html)


    def test_render_report_explains_recent_trade_missing_from_current_portfolio(self) -> None:
        result = _build_minimal_result()
        result["operations_bundle"] = {
            "recent_operations": pd.DataFrame(
                [
                    {
                        "numero": 1,
                        "fecha_evento": pd.Timestamp("2026-04-16 12:54:19"),
                        "tipo": "Compra",
                        "operation_bucket": "trading",
                        "estado": "terminada",
                        "mercado": "BCBA",
                        "simbolo": "S31G6",
                        "operation_currency": "ARS",
                        "cantidad_final": 102127,
                        "precio_final": 116.53,
                        "monto_final": 119008.59,
                        "plazo": "a24horas",
                    }
                ]
            ),
            "recent_trades": pd.DataFrame(
                [
                    {
                        "simbolo": "S31G6",
                        "tipo": "Compra",
                        "fecha_evento": pd.Timestamp("2026-04-16 12:54:19"),
                        "monto_final": 119008.59,
                        "cantidad_final": 102127,
                        "operation_currency": "ARS",
                        "estado": "terminada",
                    }
                ]
            ),
            "recent_events": pd.DataFrame(),
            "symbol_summary": pd.DataFrame(),
            "stats": {"total": 1, "trading": 1, "events": 0, "completed": 1},
        }

        html = render_report(result)

        self.assertIn("Operaciones recientes fuera de cartera actual", html)
        self.assertIn("S31G6", html)
        self.assertIn("Pendientes de consolidación", html)
        self.assertIn("Revisar S31G6 si la operación ya ejecutó pero aún no impactó /portafolio.", html)


    def test_render_report_hides_old_generic_visible_trade_from_operational_reading(self) -> None:
        result = _build_minimal_result()
        result["portfolio_bundle"]["df_total"] = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "TZXM7",
                    "Tipo": "Bono",
                    "Bloque": "Sin clasificar",
                    "Valorizado_ARS": 153201.0,
                    "Valor_USD": 109.11,
                    "Ganancia_ARS": 4654.0,
                    "Peso_%": 0.63,
                }
            ]
        )
        result["operations_bundle"] = {
            "recent_operations": pd.DataFrame(
                [
                    {
                        "numero": 170860257,
                        "fecha_evento": pd.Timestamp("2026-04-16 12:55:00"),
                        "tipo": "Compra",
                        "operation_bucket": "trading",
                        "estado": "terminada",
                        "mercado": "BCBA",
                        "simbolo": "S31G6",
                        "operation_currency": "ARS",
                        "cantidad_final": 102127,
                        "precio_final": 116.53,
                        "monto_final": 119008.59,
                        "plazo": "a24horas",
                    },
                    {
                        "numero": 169199872,
                        "fecha_evento": pd.Timestamp("2026-04-01 14:06:00"),
                        "tipo": "Compra",
                        "operation_bucket": "trading",
                        "estado": "terminada",
                        "mercado": "BCBA",
                        "simbolo": "TZXM7",
                        "operation_currency": "ARS",
                        "cantidad_final": 74460,
                        "precio_final": 199.5,
                        "monto_final": 148547.7,
                        "plazo": "a24horas",
                    },
                ]
            ),
            "recent_trades": pd.DataFrame(
                [
                    {
                        "simbolo": "S31G6",
                        "tipo": "Compra",
                        "fecha_evento": pd.Timestamp("2026-04-16 12:55:00"),
                        "monto_final": 119008.59,
                        "cantidad_final": 102127,
                        "operation_currency": "ARS",
                        "estado": "terminada",
                    },
                    {
                        "simbolo": "TZXM7",
                        "tipo": "Compra",
                        "fecha_evento": pd.Timestamp("2026-04-01 14:06:00"),
                        "monto_final": 148547.7,
                        "cantidad_final": 74460,
                        "operation_currency": "ARS",
                        "estado": "terminada",
                    },
                ]
            ),
            "recent_events": pd.DataFrame(),
            "symbol_summary": pd.DataFrame(),
            "position_transitions": {"items": [], "summary": pd.DataFrame()},
            "previous_snapshot_date": "2026-04-15",
            "stats": {"total": 2, "trading": 2, "events": 0, "completed": 2},
        }

        html = render_report(result)

        self.assertIn("Pendientes de consolidación", html)
        self.assertIn("Revisar S31G6 si la operación ya ejecutó pero aún no impactó /portafolio.", html)
        self.assertNotIn("Compra reciente ya visible en cartera | 2026-04-01 14:06", html)


    def test_render_report_hides_old_passive_event_from_operational_reading(self) -> None:
        result = _build_minimal_result()
        result["operations_bundle"] = {
            "recent_operations": pd.DataFrame(
                [
                    {
                        "numero": 170443236,
                        "fecha_evento": pd.Timestamp("2026-04-13 15:39:56"),
                        "tipo": "Pago de Dividendos",
                        "operation_bucket": "evento",
                        "estado": "terminada",
                        "mercado": "BCBA",
                        "simbolo": "DIA US$",
                        "operation_currency": "USD",
                        "cantidad_final": None,
                        "precio_final": None,
                        "monto_final": 0.06,
                        "plazo": "inmediata",
                    },
                    {
                        "numero": 168958842,
                        "fecha_evento": pd.Timestamp("2026-03-31 13:23:04"),
                        "tipo": "Pago de Dividendos",
                        "operation_bucket": "evento",
                        "estado": "terminada",
                        "mercado": "BCBA",
                        "simbolo": "XLU US$",
                        "operation_currency": "USD",
                        "cantidad_final": None,
                        "precio_final": None,
                        "monto_final": 0.37,
                        "plazo": "inmediata",
                    },
                ]
            ),
            "recent_trades": pd.DataFrame(),
            "recent_events": pd.DataFrame(
                [
                    {
                        "simbolo": "DIA US$",
                        "tipo": "Pago de Dividendos",
                        "fecha_evento": pd.Timestamp("2026-04-13 15:39:56"),
                        "monto_final": 0.06,
                        "operation_currency": "USD",
                        "estado": "terminada",
                    },
                    {
                        "simbolo": "XLU US$",
                        "tipo": "Pago de Dividendos",
                        "fecha_evento": pd.Timestamp("2026-03-31 13:23:04"),
                        "monto_final": 0.37,
                        "operation_currency": "USD",
                        "estado": "terminada",
                    },
                ]
            ),
            "recent_events": pd.DataFrame(
                [
                    {
                        "simbolo": "DIA US$",
                        "tipo": "Pago de Dividendos",
                        "fecha_evento": pd.Timestamp("2026-04-13 15:39:56"),
                        "monto_final": 0.06,
                        "operation_currency": "USD",
                        "estado": "terminada",
                    },
                    {
                        "simbolo": "XLU US$",
                        "tipo": "Pago de Dividendos",
                        "fecha_evento": pd.Timestamp("2026-03-31 13:23:04"),
                        "monto_final": 0.37,
                        "operation_currency": "USD",
                        "estado": "terminada",
                    },
                ]
            ),
            "symbol_summary": pd.DataFrame(),
            "position_transitions": {"items": [], "summary": pd.DataFrame()},
            "previous_snapshot_date": "2026-04-15",
            "stats": {"total": 2, "trading": 0, "events": 2, "completed": 2},
        }

        html = render_report(result)

        self.assertIn("Eventos recientes", html)
        self.assertIn("Eventos visibles en DIA US$.", html)
        self.assertNotIn("Eventos visibles en DIA US$, XLU US$.", html)



if __name__ == "__main__":
    unittest.main()

