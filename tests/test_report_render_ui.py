import unittest

import pandas as pd

from tests.report_render_test_utils import build_minimal_result as _build_minimal_result, render_report


class ReportRenderUiTests(unittest.TestCase):
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

        self.assertIn("Más fuertes", html)
        self.assertIn("Más débiles", html)
        self.assertIn("Cerca de máximos 52w", html)
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
        self.assertIn("Taxonomía local", html)


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
        self.assertIn("Ticker", html)
        self.assertIn("Bucket de prudencia", html)


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
        self.assertIn("Otros", html)
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

