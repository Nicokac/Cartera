import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from generate_smoke_report import render_report

def build_minimal_result(
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
        "precios_iol": {},
        "vn_factor_map": {},
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
        "risk_bundle": {},
    }
