from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

import config as project_config
from analytics.bond_analytics import (
    build_bond_local_subfamily_summary,
    build_bond_monitor_table,
    build_bond_subfamily_summary,
    enrich_bond_analytics,
)
from pipeline import build_dashboard_bundle, build_decision_bundle, build_portfolio_bundle, build_sizing_bundle


def build_mock_inputs() -> tuple[list[dict], dict, dict[str, float], float]:
    mep_real = 1250.0

    activos = [
        {
            "cantidad": 85,
            "ppc": 9800,
            "valorizado": 1187450,
            "gananciaDinero": 354450,
            "titulo": {
                "simbolo": "T",
                "descripcion": "Cedear AT&T",
                "tipo": "CEDEARS",
                "moneda": "peso_Argentino",
            },
        },
        {
            "cantidad": 25,
            "ppc": 30000,
            "valorizado": 1219000,
            "gananciaDinero": 469000,
            "titulo": {
                "simbolo": "VIST",
                "descripcion": "Cedear Vista",
                "tipo": "CEDEARS",
                "moneda": "peso_Argentino",
            },
        },
        {
            "cantidad": 12,
            "ppc": 15000,
            "valorizado": 165000,
            "gananciaDinero": -15000,
            "titulo": {
                "simbolo": "NVDA",
                "descripcion": "Cedear NVIDIA",
                "tipo": "CEDEARS",
                "moneda": "peso_Argentino",
            },
        },
        {
            "cantidad": 1000,
            "ppc": 82,
            "valorizado": 950,
            "gananciaDinero": 130,
            "titulo": {
                "simbolo": "GD30",
                "descripcion": "Bono GD30",
                "tipo": "TITULOS PUBLICOS",
                "moneda": "peso_Argentino",
            },
        },
        {
            "cantidad": 1,
            "ppc": 1,
            "valorizado": 300000,
            "gananciaDinero": 0,
            "titulo": {
                "simbolo": "ADBAICA",
                "descripcion": "FCI Cash Management",
                "tipo": "FCI",
                "moneda": "peso_Argentino",
            },
        },
        {
            "cantidad": 1,
            "ppc": 1,
            "valorizado": 500000,
            "gananciaDinero": 0,
            "titulo": {
                "simbolo": "CAU123",
                "descripcion": "Caucion colocada",
                "tipo": "CAUCION",
                "moneda": "peso_Argentino",
            },
        },
    ]

    estado_payload = {
        "totalEnPesos": 2800000,
        "cuentas": [
            {
                "moneda": "peso_Argentino",
                "disponible": 650000,
                "saldos": [
                    {"liquidacion": "inmediato", "disponible": 600000},
                    {"liquidacion": "48hs", "disponible": 50000},
                ],
            },
            {
                "moneda": "USD",
                "disponible": 160,
                "saldos": [
                    {"liquidacion": "inmediato", "disponible": 120},
                    {"liquidacion": "24hs", "disponible": 40},
                ],
            },
        ],
    }

    precios_iol = {
        "T": 13970.0,
        "VIST": 48760.0,
        "NVDA": 13750.0,
        "GD30": 95.0,
    }

    return activos, estado_payload, precios_iol, mep_real


def enrich_mock_cedears(df_cedears: pd.DataFrame, *, mep_real: float) -> pd.DataFrame:
    if df_cedears.empty:
        return df_cedears

    overlays = {
        "T": {"Perf Week": 1.2, "Perf Month": 3.8, "Perf YTD": 8.4, "Beta": 0.72, "P/E": 18.0},
        "VIST": {"Perf Week": 2.4, "Perf Month": 8.1, "Perf YTD": 21.0, "Beta": 1.48, "P/E": 11.5},
        "NVDA": {"Perf Week": -4.8, "Perf Month": -6.0, "Perf YTD": -12.0, "Beta": 1.86, "P/E": 42.0},
    }

    out = df_cedears.copy()
    out["Perf Week"] = out["Ticker_IOL"].map(lambda t: overlays.get(t, {}).get("Perf Week"))
    out["Perf Month"] = out["Ticker_IOL"].map(lambda t: overlays.get(t, {}).get("Perf Month"))
    out["Perf YTD"] = out["Ticker_IOL"].map(lambda t: overlays.get(t, {}).get("Perf YTD"))
    out["Beta"] = out["Ticker_IOL"].map(lambda t: overlays.get(t, {}).get("Beta"))
    out["P/E"] = out["Ticker_IOL"].map(lambda t: overlays.get(t, {}).get("P/E"))
    out["ROE"] = out["Ticker_IOL"].map(lambda t: {"T": 18.0, "VIST": 24.0, "NVDA": 31.0}.get(t))
    out["Profit Margin"] = out["Ticker_IOL"].map(lambda t: {"T": 15.0, "VIST": 19.0, "NVDA": 22.0}.get(t))
    out["MEP_Implicito"] = mep_real * pd.Series([0.995, 1.015, 1.055][: len(out)], index=out.index)
    return out


def build_mock_ratings() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Ticker_Finviz": "T", "consenso": "buy", "consenso_n": 12, "total_ratings": 15},
            {"Ticker_Finviz": "VIST", "consenso": "buy", "consenso_n": 8, "total_ratings": 10},
            {"Ticker_Finviz": "NVDA", "consenso": "hold", "consenso_n": 4, "total_ratings": 11},
        ]
    ).set_index("Ticker_Finviz")


def build_mock_bonistas(df_bonds: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    if df_bonds.empty:
        return pd.DataFrame(), {}

    rows = []
    for ticker in df_bonds["Ticker_IOL"].tolist():
        if ticker == "GD30":
            rows.append(
                {
                    "bonistas_ticker": "GD30",
                    "bonistas_tir_pct": 12.4,
                    "bonistas_paridad_pct": 77.8,
                    "bonistas_md": 3.2,
                    "bonistas_volume_last": 1500000.0,
                    "bonistas_volume_avg_20d": 1200000.0,
                    "bonistas_volume_ratio": 1.25,
                    "bonistas_liquidity_bucket": "alta",
                    "bonistas_fecha_vencimiento": "09/07/2030",
                    "bonistas_fecha_emision": "04/09/2020",
                    "bonistas_valor_tecnico": 72.1,
                    "bonistas_tir_avg_365d_pct": 13.8,
                    "bonistas_put_flag": False,
                    "bonistas_subfamily": "bond_hard_dollar",
                }
            )
    macro = {
        "cer_diario": 1.2,
        "tamar": 31.5,
        "tamar_tea": 37.9,
        "badlar": 29.1,
        "badlar_tea": 33.2,
        "reservas_bcra_musd": 28350.0,
        "a3500_mayorista": 1387.72,
        "riesgo_pais_bps": 720.0,
        "rem_inflacion_mensual_pct": 2.7,
        "rem_inflacion_12m_pct": 24.6,
        "ust_5y_pct": 4.05,
        "ust_10y_pct": 4.25,
        "ust_spread_10y_5y_pct": 0.20,
        "ust_date": "2026-04-04",
    }
    return pd.DataFrame(rows), macro


def print_section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def run_smoke_pipeline() -> dict[str, object]:
    activos, estado_payload, precios_iol, mep_real = build_mock_inputs()

    portfolio_bundle = build_portfolio_bundle(
        activos=activos,
        estado_payload=estado_payload,
        precios_iol=precios_iol,
        mep_real=mep_real,
        finviz_map=project_config.FINVIZ_MAP,
        block_map=project_config.BLOCK_MAP,
        instrument_profile_map=project_config.INSTRUMENT_PROFILE_MAP,
        vn_factor_map=project_config.VN_FACTOR_MAP,
        ratios=project_config.RATIOS,
        fci_cash_management=project_config.FCI_CASH_MANAGEMENT,
    )

    df_total = portfolio_bundle["df_total"]
    df_bonistas, bonistas_macro = build_mock_bonistas(portfolio_bundle["df_bonos"])
    bond_monitor = pd.DataFrame()
    bond_subfamily_summary = pd.DataFrame()
    bond_local_subfamily_summary = pd.DataFrame()
    if not portfolio_bundle["df_bonos"].empty:
        bond_analytics = enrich_bond_analytics(
            portfolio_bundle["df_bonos"],
            df_bonistas,
            reference_date="2026-04-05",
            macro_variables=bonistas_macro,
            mep_real=mep_real,
        )
        bond_context_cols = [
            "Ticker_IOL",
            "bonistas_local_subfamily",
            "bonistas_tir_pct",
            "bonistas_paridad_pct",
            "bonistas_md",
            "bonistas_volume_last",
            "bonistas_volume_avg_20d",
            "bonistas_volume_ratio",
            "bonistas_liquidity_bucket",
            "bonistas_days_to_maturity",
            "bonistas_tir_vs_avg_365d_pct",
            "bonistas_parity_gap_pct",
            "bonistas_put_flag",
            "bonistas_riesgo_pais_bps",
            "bonistas_reservas_bcra_musd",
            "bonistas_a3500_mayorista",
            "bonistas_rem_inflacion_mensual_pct",
            "bonistas_rem_inflacion_12m_pct",
            "bonistas_ust_5y_pct",
            "bonistas_ust_10y_pct",
            "bonistas_spread_vs_ust_pct",
        ]
        bond_context = bond_analytics[[col for col in bond_context_cols if col in bond_analytics.columns]].copy()
        bond_monitor = build_bond_monitor_table(bond_analytics)
        bond_subfamily_summary = build_bond_subfamily_summary(bond_analytics)
        bond_local_subfamily_summary = build_bond_local_subfamily_summary(bond_analytics)
    else:
        bond_context = pd.DataFrame()
    df_cedears = enrich_mock_cedears(portfolio_bundle["df_cedears"], mep_real=mep_real)
    df_ratings_res = build_mock_ratings()
    finviz_stats = {
        "cedears_total": int(len(df_cedears)),
        "fundamentals_covered": int(df_cedears[["Perf Week", "Perf Month", "Perf YTD", "Beta", "P/E", "ROE", "Profit Margin"]].notna().any(axis=1).sum()),
        "ratings_covered": int(len(df_ratings_res)),
        "coverage_by_field": {
            col: int(df_cedears[col].notna().sum())
            for col in ["Perf Week", "Perf Month", "Perf YTD", "Beta", "P/E", "ROE", "Profit Margin"]
        },
        "errors": [],
    }

    decision_bundle = build_decision_bundle(
        df_total=df_total,
        df_cedears=df_cedears,
        df_ratings_res=df_ratings_res,
        mep_real=mep_real,
        scoring_rules=project_config.SCORING_RULES,
        action_rules=project_config.ACTION_RULES,
    )
    if not bond_context.empty:
        decision_bundle["final_decision"] = decision_bundle["final_decision"].merge(
            bond_context,
            on="Ticker_IOL",
            how="left",
        )
    final_decision = decision_bundle["final_decision"]

    sizing_bundle = build_sizing_bundle(
        final_decision=final_decision,
        mep_real=mep_real,
        bucket_weights=project_config.BUCKET_WEIGHTS,
        action_rules=project_config.ACTION_RULES,
        sizing_rules=project_config.SIZING_RULES,
    )

    dashboard_bundle = build_dashboard_bundle(df_total, mep_real=mep_real)

    return {
        "mep_real": mep_real,
        "portfolio_bundle": portfolio_bundle,
        "dashboard_bundle": dashboard_bundle,
        "decision_bundle": decision_bundle,
        "sizing_bundle": sizing_bundle,
        "finviz_stats": finviz_stats,
        "bonistas_bundle": {
            "bond_monitor": bond_monitor,
            "bond_subfamily_summary": bond_subfamily_summary,
            "bond_local_subfamily_summary": bond_local_subfamily_summary,
            "macro_variables": bonistas_macro,
        },
    }


def main() -> None:
    result = run_smoke_pipeline()
    mep_real = float(result["mep_real"])
    portfolio_bundle = result["portfolio_bundle"]
    dashboard_bundle = result["dashboard_bundle"]
    decision_bundle = result["decision_bundle"]
    sizing_bundle = result["sizing_bundle"]

    df_total = portfolio_bundle["df_total"]
    final_decision = decision_bundle["final_decision"]

    print_section("Smoke Run")
    print(f"MEP usado: ${mep_real:,.2f}")
    print(f"Instrumentos totales: {len(df_total)}")
    print(f"Total ARS: ${df_total['Valorizado_ARS'].sum():,.0f}")
    print(f"Total USD: USD {df_total['Valor_USD'].sum():,.2f}")
    print(f"Peso total: {df_total['Peso_%'].sum():.2f}%")

    print_section("Integridad")
    print(portfolio_bundle["integrity_report"].to_string(index=False))

    print_section("Dashboard")
    print(pd.Series(dashboard_bundle["kpis"]).to_string())

    print_section("Decision")
    cols = ["Ticker_IOL", "Tipo", "score_unificado", "accion_sugerida_v2", "motivo_accion"]
    print(final_decision[cols].sort_values("score_unificado", ascending=False).to_string(index=False))

    print_section("Sizing")
    print(f"Fuente de fondeo: {sizing_bundle['fuente_fondeo']}")
    print(f"Pct fondeo: {sizing_bundle['pct_fondeo']:.0%}")
    print(f"Monto fondeo ARS: ${sizing_bundle['monto_fondeo_ars']:,.0f}")
    asignacion = sizing_bundle["asignacion_final"]
    if asignacion.empty:
        print("Sin asignacion final generada.")
    else:
        cols = ["Ticker_IOL", "Bucket_Prudencia", "Peso_Fondeo_%", "Monto_ARS", "Monto_USD"]
        print(asignacion[cols].to_string(index=False))


if __name__ == "__main__":
    main()
