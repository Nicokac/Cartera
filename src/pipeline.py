from __future__ import annotations

from typing import Any

import pandas as pd

try:
    from .analytics.dashboard import build_executive_dashboard_data
    from .decision.actions import assign_action_v2, assign_base_action, enrich_decision_explanations
    from .decision.scoring import (
        apply_base_scores,
        apply_technical_overlay_scores,
        build_decision_base,
        finalize_unified_score,
    )
    from .decision.sizing import build_dynamic_allocation, build_operational_proposal, build_prudent_allocation
    from .portfolio.checks import build_integrity_report
    from .portfolio.classify import classify_iol_portfolio
    from .portfolio.liquidity import rebuild_liquidity
    from .portfolio.valuation import build_bonos_df, build_cedears_df, build_local_df, build_portfolio_master
except ImportError:
    from analytics.dashboard import build_executive_dashboard_data
    from decision.actions import assign_action_v2, assign_base_action, enrich_decision_explanations
    from decision.scoring import (
        apply_base_scores,
        apply_technical_overlay_scores,
        build_decision_base,
        finalize_unified_score,
    )
    from decision.sizing import build_dynamic_allocation, build_operational_proposal, build_prudent_allocation
    from portfolio.checks import build_integrity_report
    from portfolio.classify import classify_iol_portfolio
    from portfolio.liquidity import rebuild_liquidity
    from portfolio.valuation import build_bonos_df, build_cedears_df, build_local_df, build_portfolio_master


def build_portfolio_bundle(
    *,
    activos: list[dict[str, Any]],
    estado_payload: dict[str, Any],
    precios_iol: dict[str, float],
    mep_real: float | None,
    finviz_map: dict[str, str],
    block_map: dict[str, str],
    vn_factor_map: dict[str, float | int],
    ratios: dict[str, float | int],
    fci_cash_management: set[str],
) -> dict[str, Any]:
    clasificado = classify_iol_portfolio(
        activos,
        finviz_map=finviz_map,
        block_map=block_map,
        vn_factor_map=vn_factor_map,
    )
    df_liquidez, liquidity_contract, liquidez_rows = rebuild_liquidity(
        activos,
        estado_payload,
        mep_real=mep_real,
        fci_cash_management=fci_cash_management,
    )
    df_cedears = build_cedears_df(clasificado["PORTAFOLIO"], precios_iol, ratios=ratios)
    df_local = build_local_df(clasificado["ACCIONES_LOCALES"], precios_iol)
    df_bonos = build_bonos_df(clasificado["BONOS"], precios_iol)
    df_total = build_portfolio_master(df_cedears, df_local, df_bonos, df_liquidez, mep_real=mep_real)
    integrity_report, integrity_summary = build_integrity_report(df_total) if not df_total.empty else (
        pd.DataFrame(),
        {},
    )
    return {
        "clasificado": clasificado,
        "df_cedears": df_cedears,
        "df_local": df_local,
        "df_bonos": df_bonos,
        "df_liquidez": df_liquidez,
        "df_total": df_total,
        "liquidity_contract": liquidity_contract,
        "liquidez_rows": liquidez_rows,
        "integrity_report": integrity_report,
        "integrity_summary": integrity_summary,
    }


def build_dashboard_bundle(df_total: pd.DataFrame, *, mep_real: float | None) -> dict[str, Any]:
    return build_executive_dashboard_data(df_total, mep_real=mep_real)


def build_decision_bundle(
    *,
    df_total: pd.DataFrame,
    df_cedears: pd.DataFrame,
    df_ratings_res: pd.DataFrame,
    decision_tech: pd.DataFrame | None = None,
    mep_real: float | None,
    scoring_rules: dict[str, Any] | None = None,
    action_rules: dict[str, Any] | None = None,
) -> dict[str, pd.DataFrame]:
    decision = build_decision_base(
        df_total,
        df_cedears,
        df_ratings_res,
        mep_real=mep_real,
        scoring_rules=scoring_rules,
    )
    decision = apply_base_scores(decision, scoring_rules=scoring_rules)
    decision = assign_base_action(decision, action_rules=action_rules)

    if decision_tech is None:
        decision_tech = decision.copy()

    decision_tech = apply_technical_overlay_scores(decision_tech)
    if "score_refuerzo_v2" not in decision_tech.columns:
        # Fallback: sin overlay tecnico, reutilizar el score base como variante v2.
        decision_tech["score_refuerzo_v2"] = decision_tech["score_refuerzo"]
        decision_tech["score_reduccion_v2"] = decision_tech["score_reduccion"]
        decision_tech["score_unificado_v2"] = (
            decision_tech["score_refuerzo_v2"] - decision_tech["score_reduccion_v2"]
        ).round(3)
    decision_tech = assign_action_v2(decision_tech, action_rules=action_rules)
    final_decision = finalize_unified_score(decision_tech)
    final_decision = enrich_decision_explanations(final_decision)

    return {
        "decision": decision,
        "decision_tech": decision_tech,
        "final_decision": final_decision,
    }


def build_sizing_bundle(
    *,
    final_decision: pd.DataFrame,
    mep_real: float | None,
    bucket_weights: dict[str, float],
    usar_liquidez_iol: bool = True,
    aporte_externo_ars: float = 0.0,
    action_rules: dict[str, Any] | None = None,
    sizing_rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    operational_bundle = build_operational_proposal(
        final_decision,
        mep_real=mep_real,
        usar_liquidez_iol=usar_liquidez_iol,
        aporte_externo_ars=aporte_externo_ars,
        action_rules=action_rules,
        sizing_rules=sizing_rules,
    )
    candidatos_refuerzo = build_prudent_allocation(
        operational_bundle["propuesta"],
        monto_fondeo_ars=operational_bundle["monto_fondeo_ars"],
        monto_fondeo_usd=operational_bundle["monto_fondeo_usd"],
        mep_real=mep_real,
        bucket_weights=bucket_weights,
        sizing_rules=sizing_rules,
    )
    asignacion_final = build_dynamic_allocation(
        operational_bundle["top_reforzar_final"],
        monto_fondeo_ars=operational_bundle["monto_fondeo_ars"],
        monto_fondeo_usd=operational_bundle["monto_fondeo_usd"],
        mep_real=mep_real,
        bucket_weights=bucket_weights,
        sizing_rules=sizing_rules,
    )
    return {
        **operational_bundle,
        "candidatos_refuerzo": candidatos_refuerzo,
        "asignacion_final": asignacion_final,
    }
