from __future__ import annotations

import logging
from typing import Any

import pandas as pd

try:
    from .analytics.dashboard import build_executive_dashboard_data
    from .decision.actions import assign_action_v2, assign_base_action, enrich_decision_explanations
    from .decision.scoring import (
        apply_base_scores,
        apply_technical_overlay_scores,
        build_market_regime_summary,
        build_technical_overlay_scores,
        build_decision_base,
        finalize_unified_score,
    )
    from .decision.sizing import build_dynamic_allocation, build_operational_proposal, build_prudent_allocation
    from .portfolio.checks import build_integrity_report
    from .portfolio.classify import classify_iol_portfolio
    from .portfolio.liquidity import rebuild_liquidity
    from .portfolio.valuation import build_bonos_df, build_cedears_df, build_local_df, build_portfolio_master
    from .prediction.predictor import predict
    from .prediction.store import build_prediction_observation, resolve_prediction_outcome_date
except ImportError:
    from analytics.dashboard import build_executive_dashboard_data
    from decision.actions import assign_action_v2, assign_base_action, enrich_decision_explanations
    from decision.scoring import (
        apply_base_scores,
        apply_technical_overlay_scores,
        build_market_regime_summary,
        build_technical_overlay_scores,
        build_decision_base,
        finalize_unified_score,
    )
    from decision.sizing import build_dynamic_allocation, build_operational_proposal, build_prudent_allocation
    from portfolio.checks import build_integrity_report
    from portfolio.classify import classify_iol_portfolio
    from portfolio.liquidity import rebuild_liquidity
    from portfolio.valuation import build_bonos_df, build_cedears_df, build_local_df, build_portfolio_master
    from prediction.predictor import predict
    from prediction.store import build_prediction_observation, resolve_prediction_outcome_date


logger = logging.getLogger(__name__)


def build_portfolio_bundle(
    *,
    activos: list[dict[str, Any]],
    estado_payload: dict[str, Any],
    precios_iol: dict[str, float],
    mep_real: float | None,
    finviz_map: dict[str, str],
    block_map: dict[str, str],
    argentina_equity_map: dict[str, dict[str, Any]],
    instrument_profile_map: dict[str, dict[str, Any]],
    vn_factor_map: dict[str, float | int],
    ratios: dict[str, float | int],
    fci_cash_management: set[str],
) -> dict[str, Any]:
    clasificado = classify_iol_portfolio(
        activos,
        finviz_map=finviz_map,
        block_map=block_map,
        argentina_equity_map=argentina_equity_map,
        vn_factor_map=vn_factor_map,
    )
    df_liquidez, liquidity_contract, liquidez_rows = rebuild_liquidity(
        activos,
        estado_payload,
        mep_real=mep_real,
        fci_cash_management=fci_cash_management,
    )
    df_cedears = build_cedears_df(clasificado["PORTAFOLIO"], precios_iol, ratios=ratios)
    if not df_cedears.empty and instrument_profile_map:
        profiles = pd.DataFrame.from_dict(instrument_profile_map, orient="index").reset_index()
        profiles = profiles.rename(columns={"index": "Ticker_IOL"})
        df_cedears = df_cedears.merge(profiles, on="Ticker_IOL", how="left")
        if "asset_family" not in df_cedears.columns:
            df_cedears["asset_family"] = None
        if "asset_subfamily" not in df_cedears.columns:
            df_cedears["asset_subfamily"] = None
        df_cedears["is_etf"] = df_cedears.get("is_etf", False).fillna(False).astype(bool)
        df_cedears["is_core_etf"] = df_cedears.get("is_core_etf", False).fillna(False).astype(bool)
    df_local = build_local_df(clasificado["ACCIONES_LOCALES"], precios_iol)
    df_bonos = build_bonos_df(clasificado["BONOS"], precios_iol)
    df_total = build_portfolio_master(df_cedears, df_local, df_bonos, df_liquidez, mep_real=mep_real)
    portfolio_liquidity_count = len(clasificado["LIQUIDEZ"])
    rendered_liquidity_count = 0 if df_liquidez is None else len(df_liquidez)
    synthetic_liquidity_count = max(0, rendered_liquidity_count - portfolio_liquidity_count)
    logger.info(
        "Portfolio liquidity reconciliation: portfolio=%s synthetic_cash=%s rendered=%s cash_operativo_ars=%s",
        portfolio_liquidity_count,
        synthetic_liquidity_count,
        rendered_liquidity_count,
        liquidity_contract.get("cash_operativo_ars") if liquidity_contract else None,
    )
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


def build_dashboard_bundle(
    df_total: pd.DataFrame,
    *,
    mep_real: float | None,
    liquidity_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    broker_total_ars = None
    broker_cash_ars = None
    broker_cash_committed_ars = None
    if liquidity_contract:
        broker_total_ars = liquidity_contract.get("total_broker_en_pesos")
        broker_cash_ars = liquidity_contract.get("cash_operativo_ars")
        broker_cash_committed_ars = liquidity_contract.get("cash_comprometido_ars")
    return build_executive_dashboard_data(
        df_total,
        mep_real=mep_real,
        broker_total_ars=broker_total_ars,
        broker_cash_ars=broker_cash_ars,
        broker_cash_committed_ars=broker_cash_committed_ars,
    )


def build_decision_bundle(
    *,
    df_total: pd.DataFrame,
    df_cedears: pd.DataFrame,
    df_ratings_res: pd.DataFrame,
    decision_tech: pd.DataFrame | None = None,
    mep_real: float | None,
    market_context: dict[str, Any] | None = None,
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
    decision = apply_base_scores(decision, scoring_rules=scoring_rules, market_context=market_context)
    decision = assign_base_action(decision, action_rules=action_rules)

    if decision_tech is None:
        decision_tech = decision.copy()

    decision_tech = build_technical_overlay_scores(decision, decision_tech, scoring_rules=scoring_rules)
    decision_tech = apply_technical_overlay_scores(decision_tech, scoring_rules=scoring_rules)
    if "score_refuerzo_v2" not in decision_tech.columns:
        # Fallback: sin overlay tecnico, reutilizar el score base como variante v2.
        decision_tech["score_refuerzo_v2"] = decision_tech["score_refuerzo"]
        decision_tech["score_reduccion_v2"] = decision_tech["score_reduccion"]
        decision_tech["score_unificado_v2"] = (
            decision_tech["score_refuerzo_v2"] - decision_tech["score_reduccion_v2"]
        ).round(3)
    decision_tech = assign_action_v2(decision_tech, action_rules=action_rules)
    final_decision = finalize_unified_score(decision_tech)
    final_decision = enrich_decision_explanations(final_decision, scoring_rules=scoring_rules)
    regime_summary = build_market_regime_summary(market_context, scoring_rules=scoring_rules)

    return {
        "decision": decision,
        "decision_tech": decision_tech,
        "final_decision": final_decision,
        "market_regime": regime_summary,
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


def build_prediction_bundle(
    *,
    final_decision: pd.DataFrame,
    weights: dict[str, Any] | None,
    run_date: object,
    market_regime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    weights = dict(weights or {})
    horizon_days = int(weights.get("horizon_days", 0) or 0)
    direction_threshold = float(weights.get("direction_threshold", 0.15) or 0.15)
    market_regime = dict(market_regime or {})

    if final_decision.empty:
        empty_predictions = pd.DataFrame(
            columns=[
                "ticker",
                "direction",
                "confidence",
                "consensus_raw",
                "agreement_ratio",
                "net_strength",
                "signal_votes",
                "horizon_days",
                "outcome_date",
                "asset_family",
                "asset_subfamily",
                "accion_sugerida_v2",
                "score_unificado",
            ]
        )
        return {
            "predictions": empty_predictions,
            "history_observation": build_prediction_observation(
                empty_predictions,
                run_date=run_date,
                horizon_days=horizon_days,
            ),
            "summary": {
                "total": 0,
                "up": 0,
                "down": 0,
                "neutral": 0,
                "mean_confidence": 0.0,
                "mean_agreement_ratio": 0.0,
                },
            "config": {
                "horizon_days": horizon_days,
                "direction_threshold": direction_threshold,
            },
        }

    active_flags = market_regime.get("active_flags", []) or []
    active_flags_text = ",".join(str(flag).strip() for flag in active_flags if str(flag).strip())
    any_active = bool(market_regime.get("any_active", False))
    rows: list[dict[str, Any]] = []

    for row in final_decision.to_dict(orient="records"):
        ticker = str(row.get("Ticker_IOL") or "").strip().upper()
        if not ticker:
            continue
        if str(row.get("asset_family") or "").strip().lower() == "liquidity":
            continue

        predictor_row = dict(row)
        regime_any_active = predictor_row.get("market_regime_any_active")
        if regime_any_active is None or pd.isna(regime_any_active):
            predictor_row["market_regime_any_active"] = any_active
        if not str(predictor_row.get("market_regime_active_flags") or "").strip():
            predictor_row["market_regime_active_flags"] = active_flags_text
        prediction = predict(predictor_row, weights)
        rows.append(
            {
                "ticker": ticker,
                "direction": prediction["direction"],
                "confidence": prediction["confidence"],
                "consensus_raw": prediction["consensus_raw"],
                "agreement_ratio": prediction.get("agreement_ratio"),
                "net_strength": prediction.get("net_strength"),
                "signal_votes": prediction["votes"],
                "horizon_days": horizon_days,
                "outcome_date": resolve_prediction_outcome_date(run_date, horizon_days=horizon_days),
                "asset_family": row.get("asset_family"),
                "asset_subfamily": row.get("asset_subfamily"),
                "accion_sugerida_v2": row.get("accion_sugerida_v2"),
                "score_unificado": row.get("score_unificado"),
            }
        )

    predictions = pd.DataFrame(rows)
    if not predictions.empty:
        predictions = predictions.sort_values(
            ["confidence", "consensus_raw", "ticker"],
            ascending=[False, False, True],
        ).reset_index(drop=True)

    history_observation = build_prediction_observation(
        predictions,
        run_date=run_date,
        horizon_days=horizon_days,
    )
    direction_counts = predictions.get("direction", pd.Series(dtype=object)).value_counts()
    mean_confidence = (
        float(pd.to_numeric(predictions.get("confidence"), errors="coerce").fillna(0.0).mean())
        if not predictions.empty
        else 0.0
    )
    mean_agreement_ratio = (
        float(pd.to_numeric(predictions.get("agreement_ratio"), errors="coerce").fillna(0.0).mean())
        if not predictions.empty
        else 0.0
    )
    return {
        "predictions": predictions,
        "history_observation": history_observation,
        "summary": {
            "total": int(len(predictions)),
            "up": int(direction_counts.get("up", 0)),
            "down": int(direction_counts.get("down", 0)),
            "neutral": int(direction_counts.get("neutral", 0)),
            "mean_confidence": round(mean_confidence, 6),
            "mean_agreement_ratio": round(mean_agreement_ratio, 6),
        },
        "config": {
            "horizon_days": horizon_days,
            "direction_threshold": direction_threshold,
        },
    }
