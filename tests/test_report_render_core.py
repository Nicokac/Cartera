import unittest

import pandas as pd

from tests.report_render_test_utils import build_minimal_result as _build_minimal_result, render_report


class ReportRenderCoreTests(unittest.TestCase):
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

        self.assertIn("Régimen de mercado", html)
        self.assertIn("Sin activación", html)
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


    def test_render_report_shows_pending_portfolio_rows_for_unconsolidated_trades(self) -> None:
        result = _build_minimal_result()
        result["mep_real"] = 1419.0
        result["precios_iol"] = {"S31G6": 117.0}
        result["operations_bundle"] = {
            "recent_trades": pd.DataFrame(
                [
                    {
                        "simbolo": "S31G6",
                        "tipo": "Compra",
                        "estado": "terminada",
                        "cantidad_final": 102127,
                        "precio_final": 117.0,
                        "monto_final": 119008.59,
                        "operation_currency": "ARS",
                    }
                ]
            ),
            "recent_operations": pd.DataFrame(),
            "recent_events": pd.DataFrame(),
            "symbol_summary": pd.DataFrame(),
            "stats": {"total": 1, "trading": 1, "events": 0, "completed": 1},
        }

        html = render_report(result)

        self.assertIn("Ver tenencias pendientes de consolidacion", html)
        self.assertIn("S31G6", html)
        self.assertIn("Pendiente de consolidacion", html)


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


    def test_render_report_shows_historical_risk_block_when_bundle_has_data(self) -> None:
        result = _build_minimal_result()
        result["risk_bundle"] = {
            "portfolio_summary": {
                "desde": "2026-04-20",
                "hasta": "2026-04-23",
                "snapshots": 4,
                "retorno_acum_pct": 10.67,
                "volatilidad_diaria_pct": 4.12,
                "drawdown_max_pct": -12.5,
                "pasos_estables": 3,
                "pasos_totales": 3,
                "coverage_prev_promedio_pct": 96.0,
                "coverage_curr_promedio_pct": 95.0,
                "nota_estabilidad": None,
            },
            "position_risk": pd.DataFrame(
                [
                    {
                        "Ticker_IOL": "AAPL",
                        "Tipo": "CEDEAR",
                        "Bloque": "Growth",
                        "Peso_%": 5.2,
                        "Base_Riesgo": "Precio_ARS",
                        "Calidad_Historia": "Robusta",
                        "Retorno_Acum_%": 20.0,
                        "Volatilidad_Diaria_%": 13.4,
                        "Drawdown_Max_%": -18.18,
                        "Observaciones": 4,
                    },
                    {
                        "Ticker_IOL": "GD30",
                        "Tipo": "Bono",
                        "Bloque": "Soberano AR",
                        "Peso_%": 3.7,
                        "Base_Riesgo": "Precio_ARS",
                        "Calidad_Historia": "Robusta",
                        "Retorno_Acum_%": 2.5,
                        "Volatilidad_Diaria_%": 0.4,
                        "Drawdown_Max_%": -1.19,
                        "Observaciones": 4,
                    }
                ]
            ),
        }

        html = render_report(result)

        self.assertIn("Riesgo historico", html)
        self.assertIn("Riesgo de mercado", html)
        self.assertIn("Riesgo de renta fija", html)
        self.assertIn("Universo comparable", html)
        self.assertIn("Pasos estables", html)
        self.assertIn("Ver tabla completa de riesgo", html)
        self.assertIn("Max drawdown cartera", html)
        self.assertIn("AAPL", html)
        self.assertIn("GD30", html)
        self.assertIn("Calidad_Historia", html)
        self.assertIn("Robusta", html)
        self.assertIn("risk-history-table", html)
        self.assertIn("risk-history-filter", html)
        self.assertIn("risk-history-type-filter", html)
        self.assertIn("Solo robusta", html)
        self.assertIn("Solo CEDEAR", html)
        self.assertIn("cell-quality-robusta", html)
        self.assertIn("-18.18%", html)



if __name__ == "__main__":
    unittest.main()
