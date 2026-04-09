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
        "generated_at_timezone": "America/Buenos_Aires",
        "generated_at_source": "Hora local de corrida",
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
    }


class ReportRenderTests(unittest.TestCase):
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

        self.assertIn("Senales nuevas", html)
        self.assertIn("Refuerzos persistentes", html)
        self.assertIn("Sin historial", html)

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


if __name__ == "__main__":
    unittest.main()
