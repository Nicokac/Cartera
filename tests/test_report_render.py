import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from generate_smoke_report import render_report


def _build_minimal_result(
    *,
    bonistas_bundle: dict[str, object] | None = None,
    decision_memory: dict[str, int] | None = None,
) -> dict[str, object]:
    df_total = pd.DataFrame(
        [
            {
                "Ticker_IOL": "GD30",
                "Tipo": "Bono",
                "Bloque": "Soberano AR",
                "Valorizado_ARS": 1000.0,
                "Valor_USD": 1.0,
                "Ganancia_ARS": 10.0,
                "Peso_%": 1.0,
            }
        ]
    )
    final_decision = pd.DataFrame(
        [
            {
                "Ticker_IOL": "GD30",
                "Tipo": "Bono",
                "asset_family": "bond",
                "asset_subfamily": "bond_sov_ar",
                "Peso_%": 1.0,
                "score_unificado": -0.1,
                "accion_sugerida_v2": "Mantener / monitorear",
                "motivo_accion": "Mantener y monitorear evolucion.",
                "motivo_score": "Score de bono calculado con sesgo prudencial y control de rebalanceo.",
                "driver_1": "peso",
                "driver_2": "momentum",
                "driver_3": "consenso",
                "accion_previa": "Reducir",
                "score_delta_vs_dia_anterior": 0.015,
                "dias_consecutivos_refuerzo": 0,
                "dias_consecutivos_reduccion": 0,
                "dias_consecutivos_mantener": 2,
            }
        ]
    )
    return {
        "mep_real": 1200.0,
        "generated_at_label": "2026-04-08 09:30:00",
        "portfolio_bundle": {
            "df_total": df_total,
            "integrity_report": pd.DataFrame([{"check": "peso_total", "estado": "OK", "detalle": "100%"}]),
            "df_cedears": pd.DataFrame(),
        },
        "dashboard_bundle": {
            "resumen_tipos": pd.DataFrame(
                [{"Tipo": "Bono", "Instrumentos": 1, "Valorizado_ARS": 1000.0, "Valor_USD": 1.0, "Ganancia_ARS": 10.0, "Peso_%": 1.0}]
            ),
            "kpis": {
                "total_ars": 1000.0,
                "total_ars_iol": 1000.0,
                "total_usd": 1.0,
                "ganancia_total": 10.0,
                "n_instrumentos": 1,
                "liquidez_broker_ars": 0.0,
                "liquidez_ars": 0.0,
                "liquidez_usd_ars": 0.0,
            },
        },
        "decision_bundle": {
            "final_decision": final_decision,
            "decision_memory": decision_memory or {},
            "market_regime": {
                "flags": {
                    "stress_soberano_local": False,
                    "inflacion_local_alta": False,
                    "tasas_ust_altas": False,
                },
                "active_flags": [],
                "any_active": False,
            },
        },
        "sizing_bundle": {
            "propuesta": pd.DataFrame(),
            "asignacion_final": pd.DataFrame(),
            "fuente_fondeo": "Liquidez disponible",
            "usar_liquidez_iol": True,
            "aporte_externo_ars": 0.0,
            "pct_fondeo": 0.0,
            "monto_fondeo_ars": 0.0,
        },
        "technical_overlay": pd.DataFrame(),
        "finviz_stats": {},
        "bonistas_bundle": bonistas_bundle or {},
        "operations_bundle": {},
        "prediction_bundle": {},
    }


class ReportRenderTests(unittest.TestCase):
    def test_render_report_filters_non_material_neutral_to_neutral_changes(self) -> None:
        result = _build_minimal_result()
        result["decision_bundle"]["final_decision"] = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AL30",
                    "Tipo": "Bono",
                    "asset_family": "bond",
                    "asset_subfamily": "bond_sov_ar",
                    "Peso_%": 1.0,
                    "score_unificado": 0.01,
                    "accion_sugerida_v2": "Mantener / monitorear",
                    "motivo_accion": "Cambio menor.",
                    "motivo_score": "Score.",
                    "driver_1": "peso",
                    "driver_2": "momentum",
                    "driver_3": "consenso",
                    "accion_previa": "Mantener / Neutral",
                    "score_delta_vs_dia_anterior": 0.001,
                    "dias_consecutivos_refuerzo": 0,
                    "dias_consecutivos_reduccion": 0,
                    "dias_consecutivos_mantener": 2,
                }
            ]
        )

        html = render_report(result)

        self.assertIn("Cambios de accion", html)
        self.assertIn("Sin cambios de accion respecto de la corrida previa.", html)
        self.assertNotIn("Mantener / Neutral -&gt; Mantener / monitorear", html)

    def test_render_report_hides_bonistas_section_when_bundle_is_empty(self) -> None:
        html = render_report(_build_minimal_result())

        self.assertNotIn('href="#bonistas"', html)
        self.assertNotIn('<section class="panel" id="bonistas">', html)

    def test_render_report_shows_bonistas_section_when_bundle_has_data(self) -> None:
        html = render_report(
            _build_minimal_result(
                bonistas_bundle={
                    "bond_monitor": pd.DataFrame([{"Ticker_IOL": "GD30"}]),
                    "bond_subfamily_summary": pd.DataFrame([{"asset_subfamily": "bond_sov_ar", "Instrumentos": 1}]),
                    "macro_variables": {"cer_diario": 1.2, "reservas_bcra_musd": 28384.0, "a3500_mayorista": 1387.72},
                }
            )
        )

        self.assertIn('href="#bonistas"', html)
        self.assertIn('<section class="panel" id="bonistas">', html)
        self.assertIn("Bonos Locales", html)
        self.assertIn("Reservas BCRA", html)
        self.assertIn("A3500", html)

    def test_render_report_shows_temporal_memory_strip_when_available(self) -> None:
        html = render_report(
            _build_minimal_result(
                decision_memory={
                    "senales_nuevas": 2,
                    "persistentes_refuerzo": 1,
                    "persistentes_reduccion": 0,
                    "sin_historial": 3,
                }
            )
        )

        self.assertIn("Cambios materiales", html)
        self.assertIn("Refuerzos persistentes", html)
        self.assertIn("Sin historial", html)
        self.assertIn("Suben de conviccion", html)
        self.assertIn("Bajan a reduccion", html)
        self.assertIn("Vuelven a monitoreo", html)

    def test_render_report_shows_run_timestamp_in_buenos_aires(self) -> None:
        html = render_report(_build_minimal_result())

        self.assertIn("2026-04-08 09:30:00", html)
        self.assertIn("Corrida", html)
        self.assertNotIn("Zona horaria", html)
        self.assertNotIn("Fuente horaria", html)

    def test_render_report_shows_temporal_columns_in_decision_table(self) -> None:
        html = render_report(_build_minimal_result())

        self.assertIn("Accion previa", html)
        self.assertIn("Δ Score", html)
        self.assertIn("Racha", html)
        self.assertIn("Reducir", html)
        self.assertIn("+0.015", html)

    def test_render_report_shows_market_regime_panel(self) -> None:
        html = render_report(_build_minimal_result())

        self.assertIn("Regimen de mercado", html)
        self.assertIn("Sin activacion", html)
        self.assertIn("stress_soberano_local", html)
        self.assertIn("tasas_ust_altas", html)

    def test_render_report_shows_phase_one_sections(self) -> None:
        html = render_report(_build_minimal_result())

        self.assertIn("Panorama", html)
        self.assertIn("Cambios", html)
        self.assertIn("Sizing activo", html)
        self.assertIn("Cambios de accion", html)
        self.assertIn("Liquidez broker", html)
        self.assertIn("Liquidez ampliada", html)
        self.assertIn("Vuelve a monitoreo desde reduccion", html)
        self.assertIn("Antes: Reducir. Ahora: Mantener / monitorear.", html)

    def test_render_report_shows_prediction_section_when_bundle_has_data(self) -> None:
        result = _build_minimal_result()
        result["prediction_bundle"] = {
            "summary": {"total": 2, "up": 1, "down": 1, "neutral": 0, "mean_confidence": 0.625},
            "config": {"horizon_days": 5, "direction_threshold": 0.15},
            "predictions": pd.DataFrame(
                [
                    {
                        "ticker": "XLV",
                        "direction": "up",
                        "confidence": 0.75,
                        "consensus_raw": 0.75,
                        "score_unificado": 0.248,
                        "accion_sugerida_v2": "Refuerzo",
                        "outcome_date": "2026-04-24",
                        "signal_votes": {"rsi": 1, "momentum_20d": 1, "sma_trend": 0},
                    },
                    {
                        "ticker": "MELI",
                        "direction": "down",
                        "confidence": 0.50,
                        "consensus_raw": -0.50,
                        "score_unificado": -0.186,
                        "accion_sugerida_v2": "Reducir",
                        "outcome_date": "2026-04-24",
                        "signal_votes": {"rsi": -1, "momentum_20d": 0, "sma_trend": -1},
                    },
                ]
            ),
        }

        html = render_report(result)

        self.assertIn('href="#prediccion"', html)
        self.assertIn('<section class="panel" id="prediccion">', html)
        self.assertIn("Ver tabla completa de prediccion", html)
        self.assertIn("Confianza media", html)
        self.assertIn("XLV", html)
        self.assertIn("MELI", html)
        self.assertIn('sig sig-pos', html)
        self.assertIn('sig sig-neg', html)

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
                        "title": "Posicion ampliada",
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
        self.assertIn("Posicion ampliada", html)
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
        self.assertIn("Movimiento reciente aun no reflejado en cartera", html)

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

        self.assertIn("Movimiento reciente aun no reflejado en cartera", html)
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

        self.assertIn("Cobro o acreditacion reciente | 2026-04-13 15:39", html)
        self.assertNotIn("Cobro o acreditacion reciente | 2026-03-31 13:23", html)

    def test_render_report_shows_priority_decision_board(self) -> None:
        html = render_report(_build_minimal_result())

        self.assertIn("Convicciones alcistas", html)
        self.assertIn("Riesgos a recortar", html)
        self.assertIn("Monitoreo destacado", html)
        self.assertIn("Ver tabla completa de decision", html)

    def test_render_report_deduplicates_new_signals_from_neutral_board(self) -> None:
        html = render_report(_build_minimal_result())

        self.assertIn("Monitoreo destacado", html)
        self.assertIn("Sin convicciones alcistas destacadas.", html)

    def test_render_report_excludes_liquidity_from_risk_board_and_neutral_from_bullish_board(self) -> None:
        result = _build_minimal_result()
        result["decision_bundle"]["final_decision"] = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "XLV",
                    "Tipo": "CEDEAR",
                    "asset_family": "etf",
                    "asset_subfamily": "etf_sector",
                    "Peso_%": 0.5,
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
                },
                {
                    "Ticker_IOL": "EEM",
                    "Tipo": "CEDEAR",
                    "asset_family": "etf",
                    "asset_subfamily": "etf_country_region",
                    "Peso_%": 2.0,
                    "score_unificado": 0.232,
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "motivo_accion": "Neutral con score alto.",
                    "motivo_score": "Score.",
                    "driver_1": "momentum",
                    "driver_2": "beta",
                    "driver_3": "mep",
                    "accion_previa": "Refuerzo",
                    "score_delta_vs_dia_anterior": -0.002,
                    "dias_consecutivos_refuerzo": 0,
                    "dias_consecutivos_reduccion": 0,
                    "dias_consecutivos_mantener": 1,
                },
                {
                    "Ticker_IOL": "CASH_ARS",
                    "Tipo": "Liquidez",
                    "asset_family": "liquidity",
                    "asset_subfamily": "liquidity_other",
                    "Peso_%": 25.0,
                    "score_unificado": -0.285,
                    "accion_sugerida_v2": "Mantener liquidez bloqueada",
                    "motivo_accion": "Liquidez bloqueada.",
                    "motivo_score": "Score.",
                    "driver_1": "peso",
                    "driver_2": "liquidez",
                    "driver_3": "momentum",
                    "accion_previa": "Desplegar liquidez",
                    "score_delta_vs_dia_anterior": 0.0,
                    "dias_consecutivos_refuerzo": 0,
                    "dias_consecutivos_reduccion": 0,
                    "dias_consecutivos_mantener": 0,
                },
                {
                    "Ticker_IOL": "GD30",
                    "Tipo": "Bono",
                    "asset_family": "bond",
                    "asset_subfamily": "bond_sov_ar",
                    "Peso_%": 3.7,
                    "score_unificado": -0.191,
                    "accion_sugerida_v2": "Rebalancear / tomar ganancia",
                    "motivo_accion": "Tomar ganancia parcial.",
                    "motivo_score": "Score.",
                    "driver_1": "peso",
                    "driver_2": "momentum",
                    "driver_3": "consenso",
                    "accion_previa": "Mantener / Neutral",
                    "score_delta_vs_dia_anterior": -0.003,
                    "dias_consecutivos_refuerzo": 0,
                    "dias_consecutivos_reduccion": 0,
                    "dias_consecutivos_mantener": 0,
                },
            ]
        )

        html = render_report(result)

        self.assertIn("Convicciones alcistas", html)
        self.assertIn("Riesgos a recortar", html)
        self.assertIn("Monitoreo destacado", html)
        self.assertIn("XLV", html)
        self.assertIn("GD30", html)

    def test_render_report_shows_technical_summary_layer(self) -> None:
        result = _build_minimal_result()
        result["portfolio_bundle"]["df_cedears"] = pd.DataFrame([{"Ticker_IOL": "SPY"}])
        result["technical_overlay"] = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "SPY",
                    "Tech_Trend": "Alcista",
                    "Momentum_20d_%": 4.2,
                    "Dist_52w_High_%": -2.1,
                    "Dist_SMA200_%": 5.5,
                }
            ]
        )

        html = render_report(result)

        self.assertIn("Mas fuertes", html)
        self.assertIn("Mas debiles", html)
        self.assertIn("Cerca de maximos 52w", html)
        self.assertIn("Por debajo de SMA200", html)

    def test_render_report_shows_bond_summary_layer(self) -> None:
        html = render_report(
            _build_minimal_result(
                bonistas_bundle={
                    "bond_monitor": pd.DataFrame([{"Ticker_IOL": "GD30"}]),
                    "bond_subfamily_summary": pd.DataFrame(
                        [{"asset_subfamily": "bond_sov_ar", "Instrumentos": 1, "TIR_Promedio": 12.4, "Paridad_Promedio": 77.8, "MD_Promedio": 3.2}]
                    ),
                    "bond_local_subfamily_summary": pd.DataFrame(
                        [{"bonistas_local_subfamily": "bond_hard_dollar", "Instrumentos": 1, "TIR_Promedio": 12.4, "Paridad_Promedio": 77.8, "MD_Promedio": 3.2}]
                    ),
                    "macro_variables": {"cer_diario": 1.2, "reservas_bcra_musd": 28384.0, "a3500_mayorista": 1387.72, "ust_5y_pct": 4.0, "ust_10y_pct": 4.2},
                }
            )
        )

        self.assertIn("Contexto macro", html)
        self.assertIn("Subfamilias", html)
        self.assertIn("Taxonomia local", html)

    def test_render_report_shows_collapsible_detail_layers(self) -> None:
        html = render_report(_build_minimal_result())

        self.assertIn("Ver tabla completa de decision", html)
        self.assertIn("Ver cartera completa", html)
        self.assertIn("Ver chequeos de integridad", html)

    def test_render_report_shows_sticky_nav_active_hook(self) -> None:
        html = render_report(_build_minimal_result())

        self.assertIn("quick-nav", html)
        self.assertIn("classList.toggle('active'", html)

    def test_render_report_escapes_untrusted_decision_and_macro_text(self) -> None:
        result = _build_minimal_result(
            bonistas_bundle={
                "bond_monitor": pd.DataFrame([{"Ticker_IOL": "GD30"}]),
                "bond_subfamily_summary": pd.DataFrame([{"asset_subfamily": "bond_sov_ar", "Instrumentos": 1}]),
                "macro_variables": {"cer_diario": '<script>alert("x")</script>'},
            }
        )
        result["decision_bundle"]["final_decision"].loc[0, "motivo_accion"] = '<img src=x onerror=alert("m")>'
        result["decision_bundle"]["final_decision"].loc[0, "driver_1"] = "<b>peso</b>"

        html = render_report(result)

        self.assertNotIn('<script>alert("x")</script>', html)
        self.assertNotIn('<img src=x onerror=alert("m")>', html)
        self.assertNotIn("<b>peso</b>", html)
        self.assertIn("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;", html)
        self.assertIn("&lt;img src=x onerror=alert(&quot;m&quot;)&gt;", html)
        self.assertIn("&lt;b&gt;peso&lt;/b&gt;", html)

    def test_render_report_tolerates_partial_sizing_frame_without_alloc_columns(self) -> None:
        result = _build_minimal_result()
        result["sizing_bundle"]["asignacion_final"] = pd.DataFrame([{"Ticker_IOL": "XLU"}])

        html = render_report(result)

        self.assertIn("Sizing", html)
        self.assertIn("Ticker_IOL", html)
        self.assertIn("Bucket_Prudencia", html)

    def test_render_report_shows_fred_unavailable_note_when_ust_source_fails(self) -> None:
        html = render_report(
            _build_minimal_result(
                bonistas_bundle={
                    "bond_monitor": pd.DataFrame([{"Ticker_IOL": "GD30"}]),
                    "bond_subfamily_summary": pd.DataFrame([{"asset_subfamily": "bond_sov_ar", "Instrumentos": 1}]),
                    "macro_variables": {"ust_status": "error"},
                }
            )
        )

        self.assertIn("FRED no disponible", html)

    def test_render_report_hides_score_criteria_behind_inline_detail(self) -> None:
        html = render_report(_build_minimal_result())

        self.assertIn("Ver criterios generales de score", html)
        self.assertIn("Score de bono calculado con sesgo prudencial y control de rebalanceo.", html)

    def test_render_report_preserves_fci_identity_and_specific_narrative(self) -> None:
        result = _build_minimal_result()
        result["portfolio_bundle"]["df_total"] = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "IOLPORA",
                    "Tipo": "FCI",
                    "Bloque": "FCI",
                    "Valorizado_ARS": 842426.0,
                    "Valor_USD": 595.40,
                    "Ganancia_ARS": 241053.0,
                    "Peso_%": 3.43,
                    "Es_Liquidez": False,
                }
            ]
        )
        result["dashboard_bundle"]["resumen_tipos"] = pd.DataFrame(
            [
                {
                    "Tipo": "FCI",
                    "Instrumentos": 1,
                    "Valorizado_ARS": 842426.0,
                    "Valor_USD": 595.40,
                    "Ganancia_ARS": 241053.0,
                    "Peso_%": 3.43,
                }
            ]
        )
        result["dashboard_bundle"]["kpis"] = {
            "total_ars": 842426.0,
            "total_ars_iol": 842426.0,
            "total_usd": 595.40,
            "ganancia_total": 241053.0,
            "n_instrumentos": 1,
            "liquidez_broker_ars": 0.0,
            "liquidez_ars": 0.0,
            "liquidez_usd_ars": 0.0,
        }
        result["decision_bundle"]["final_decision"] = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "IOLPORA",
                    "Tipo": "FCI",
                    "asset_family": "fund",
                    "asset_subfamily": "fund_other",
                    "Peso_%": 3.43,
                    "score_unificado": 0.0,
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "motivo_accion": "FCI en monitoreo: vehiculo diversificado sin senal tactica dominante.",
                    "motivo_score": "FCI mantenido en neutral por mandato diversificado y sin scoring tactico direccional.",
                    "driver_1": "peso",
                    "driver_2": "momentum",
                    "driver_3": "consenso",
                    "accion_previa": "Mantener / Neutral",
                    "score_delta_vs_dia_anterior": 0.09,
                    "dias_consecutivos_refuerzo": 0,
                    "dias_consecutivos_reduccion": 0,
                    "dias_consecutivos_mantener": 12,
                }
            ]
        )

        html = render_report(result)

        self.assertIn(">IOLPORA<", html)
        self.assertIn(">FCI<", html)
        self.assertIn("fund_other", html)
        self.assertIn(
            "FCI mantenido en neutral por mandato diversificado y sin scoring tactico direccional.",
            html,
        )
        self.assertIn(
            "FCI en monitoreo: vehiculo diversificado sin senal tactica dominante.",
            html,
        )
        self.assertNotIn(">Liquidez<", html)
        self.assertNotIn("liquidity_other", html)

    def test_render_report_flags_neutral_prediction_with_directional_action(self) -> None:
        result = _build_minimal_result()
        result["prediction_bundle"] = {
            "summary": {"total": 1, "up": 0, "down": 0, "neutral": 1, "mean_confidence": 0.1143},
            "config": {"horizon_days": 5, "direction_threshold": 0.15},
            "predictions": pd.DataFrame(
                [
                    {
                        "ticker": "BABA",
                        "direction": "neutral",
                        "confidence": 0.1143,
                        "consensus_raw": 0.1143,
                        "score_unificado": 0.213,
                        "accion_sugerida_v2": "Refuerzo",
                        "outcome_date": "2026-04-24",
                        "signal_votes": {"rsi": -1, "momentum_20d": 1, "momentum_60d": -1},
                    }
                ]
            ),
        }

        html = render_report(result)

        self.assertIn("⚠ Refuerzo", html)


if __name__ == "__main__":
    unittest.main()

