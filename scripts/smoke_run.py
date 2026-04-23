from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

import config as project_config
from analytics.bond_analytics import (
    build_bond_local_subfamily_summary,
    build_bond_monitor_table,
    build_bond_subfamily_summary,
    enrich_bond_analytics,
)
from pipeline import (
    build_dashboard_bundle,
    build_decision_bundle,
    build_portfolio_bundle,
    build_prediction_bundle,
    build_sizing_bundle,
)
from portfolio.operations import build_operations_bundle, enrich_operations_bundle
from tests.fixtures.smoke_fixtures import (
    build_mock_bonistas,
    build_mock_inputs,
    build_mock_operations,
    build_mock_previous_portfolio,
    build_mock_ratings,
    enrich_mock_cedears,
)
from smoke_output import render_smoke_output


def run_smoke_pipeline() -> dict[str, object]:
    activos, estado_payload, precios_iol, mep_real = build_mock_inputs()
    operations_payload = build_mock_operations()

    portfolio_bundle = build_portfolio_bundle(
        activos=activos,
        estado_payload=estado_payload,
        precios_iol=precios_iol,
        mep_real=mep_real,
        finviz_map=project_config.FINVIZ_MAP,
        block_map=project_config.BLOCK_MAP,
        argentina_equity_map=project_config.ARGENTINA_EQUITY_MAP,
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
        market_context=bonistas_macro,
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
    prediction_bundle = build_prediction_bundle(
        final_decision=final_decision,
        weights=project_config.PREDICTION_WEIGHTS,
        run_date="2026-04-16",
        market_regime=decision_bundle.get("market_regime"),
    )

    sizing_bundle = build_sizing_bundle(
        final_decision=final_decision,
        mep_real=mep_real,
        bucket_weights=project_config.BUCKET_WEIGHTS,
        action_rules=project_config.ACTION_RULES,
        sizing_rules=project_config.SIZING_RULES,
    )

    dashboard_bundle = build_dashboard_bundle(
        df_total,
        mep_real=mep_real,
        liquidity_contract=portfolio_bundle.get("liquidity_contract"),
    )
    operations_bundle = enrich_operations_bundle(
        build_operations_bundle(operations_payload),
        current_portfolio=portfolio_bundle["df_total"],
        previous_portfolio=build_mock_previous_portfolio(),
        previous_snapshot_date="2026-04-15",
    )

    return {
        "mep_real": mep_real,
        "portfolio_bundle": portfolio_bundle,
        "dashboard_bundle": dashboard_bundle,
        "decision_bundle": decision_bundle,
        "sizing_bundle": sizing_bundle,
        "prediction_bundle": prediction_bundle,
        "finviz_stats": finviz_stats,
        "operations_bundle": operations_bundle,
        "bonistas_bundle": {
            "bond_monitor": bond_monitor,
            "bond_subfamily_summary": bond_subfamily_summary,
            "bond_local_subfamily_summary": bond_local_subfamily_summary,
            "macro_variables": bonistas_macro,
        },
    }


def main(*, dry_run: bool = False) -> None:
    result = run_smoke_pipeline()
    if dry_run:
        return
    render_smoke_output(result)


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
