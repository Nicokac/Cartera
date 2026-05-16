from __future__ import annotations

import pandas as pd
from typing import TypedDict

from report_decision import (
    build_change_highlights,
    build_family_summary,
    select_decision_view,
)
from report_layout import (
    build_changes_section,
    build_decision_section,
    build_header_cards,
    build_integrity_section,
    build_integrity_strip,
    build_panorama_section,
    build_portfolio_section,
    build_quick_nav,
    build_regime_section,
    build_sizing_preview,
)
from report_operations import build_executive_summary, build_operations_summary
from report_sections import (
    build_bonistas_section,
    build_sizing_section,
    build_summary_section,
)
from report_sections_prediction import build_prediction_section
from portfolio.operations import build_pending_trade_portfolio_rows

import io

from decision.action_constants import NEUTRAL_ACTIONS

_CSV_EXPORT_COLUMNS = [
    "Ticker_IOL", "Tipo", "asset_family", "asset_subfamily",
    "Peso_%", "Valorizado_ARS", "Valor_USD", "Ganancia_%", "Ganancia_%_Cap",
    "score_unificado", "accion_sugerida_v2", "accion_previa",
    "score_delta_vs_dia_anterior", "dias_consecutivos_refuerzo", "dias_consecutivos_reduccion",
    "Tech_Trend", "RSI_14", "Momentum_20d_%", "Momentum_60d_%",
    "Dist_SMA200_%", "ADX_14", "Relative_Volume",
    "Perf Week", "Perf Month", "Perf YTD",
    "Beta", "P/E", "ROE", "Profit Margin", "MEP_Premium_%",
    "consenso", "total_ratings",
    "driver_1", "driver_2", "driver_3",
]


def _build_csv_export(final_decision: pd.DataFrame, generated_at_label: object) -> tuple[str, str]:
    available = [c for c in _CSV_EXPORT_COLUMNS if c in final_decision.columns]
    df = final_decision[available].copy()
    date_str = str(generated_at_label or "").split(" ")[0] or "export"
    filename = f"cartera_{date_str}.csv"
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8")
    return buf.getvalue(), filename


class RenderSections(TypedDict):
    primary_cards: str
    secondary_cards: str
    action_summary: str
    panorama_section: str
    changes_section: str
    regime_summary: str
    bonistas_section: str
    quick_nav: str
    operations_section: str
    prediction_section: str
    summary_section: str
    sizing_section: str
    decision_section: str
    portfolio_section: str
    integrity_section: str
    integrity_strip: str


class ReportBodyInputs(TypedDict):
    title: str
    generated_at_label: object
    headline: str
    lede: str
    integrity_strip: str
    quick_nav: str
    primary_cards: str
    secondary_cards: str
    action_summary: str
    panorama_section: str
    changes_section: str
    operations_section: str
    prediction_section: str
    regime_summary: str
    summary_section: str
    sizing_section: str
    tech_enabled: str
    tech_covered: int
    tech_total: int
    technical_view: pd.DataFrame
    price_history: dict[str, list[float]]
    bonistas_section: str
    decision_section: str
    portfolio_section: str
    integrity_section: str


def build_technical_view(technical_overlay: pd.DataFrame) -> pd.DataFrame:
    technical_cols = [
        col
        for col in [
            "Ticker_IOL",
            "Peso_%",
            "Tech_Trend",
            "RSI_14",
            "Momentum_20d_%",
            "Momentum_60d_%",
            "Dist_SMA20_%",
            "Dist_SMA50_%",
            "Dist_SMA200_%",
            "Dist_EMA20_%",
            "Dist_EMA50_%",
            "Dist_52w_High_%",
            "Dist_52w_Low_%",
            "Vol_20d_Anual_%",
            "Avg_Volume_20d",
            "Drawdown_desde_Max3m_%",
        ]
        if col in technical_overlay.columns
    ]
    if not isinstance(technical_overlay, pd.DataFrame) or technical_overlay.empty:
        return pd.DataFrame()

    technical_view = technical_overlay[technical_cols].copy()
    if "Momentum_20d_%" in technical_view.columns:
        technical_view = technical_view.sort_values("Momentum_20d_%", ascending=False)
    return technical_view


def _extract_bonistas_context(bonistas_bundle: dict[str, object]) -> dict[str, object]:
    bond_monitor = bonistas_bundle.get("bond_monitor", pd.DataFrame())
    bond_subfamily_summary = bonistas_bundle.get("bond_subfamily_summary", pd.DataFrame())
    bond_local_subfamily_summary = bonistas_bundle.get("bond_local_subfamily_summary", pd.DataFrame())
    bonistas_macro = bonistas_bundle.get("macro_variables", {}) or {}
    ust_status = str(bonistas_macro.get("ust_status") or "").strip().lower()
    ust_note = "<span>UST source: <strong>FRED no disponible</strong></span>" if ust_status == "error" else ""
    show_bonistas = (
        (isinstance(bond_monitor, pd.DataFrame) and not bond_monitor.empty)
        or (isinstance(bond_subfamily_summary, pd.DataFrame) and not bond_subfamily_summary.empty)
        or (isinstance(bond_local_subfamily_summary, pd.DataFrame) and not bond_local_subfamily_summary.empty)
        or bool(bonistas_macro)
    )
    return {
        "bond_monitor": bond_monitor,
        "bond_subfamily_summary": bond_subfamily_summary,
        "bond_local_subfamily_summary": bond_local_subfamily_summary,
        "bonistas_macro": bonistas_macro,
        "ust_note": ust_note,
        "show_bonistas": show_bonistas,
    }


def _extract_coverage_context(
    *,
    technical_overlay: pd.DataFrame,
    portfolio_bundle: dict[str, object],
    finviz_stats: dict[str, object],
) -> dict[str, object]:
    tech_metric_cols = [
        "Dist_SMA20_%",
        "Dist_SMA50_%",
        "Dist_SMA200_%",
        "Dist_EMA20_%",
        "Dist_EMA50_%",
        "Dist_52w_High_%",
        "Dist_52w_Low_%",
        "RSI_14",
        "Momentum_20d_%",
        "Momentum_60d_%",
        "Vol_20d_Anual_%",
        "Avg_Volume_20d",
        "Drawdown_desde_Max3m_%",
    ]
    tech_available_cols = [col for col in tech_metric_cols if col in technical_overlay.columns]
    df_cedears_len = int(len(portfolio_bundle.get("df_cedears", pd.DataFrame())))
    df_us = portfolio_bundle.get("df_us", pd.DataFrame())
    df_us_with_finviz = int((df_us["Ticker_Finviz"].notna()).sum()) if not df_us.empty and "Ticker_Finviz" in df_us.columns else 0
    tech_total = df_cedears_len + df_us_with_finviz
    tech_covered = int(technical_overlay[tech_available_cols].notna().any(axis=1).sum()) if tech_available_cols else 0
    tech_enabled = "Si" if tech_covered > 0 else "No"
    finviz_total = int(finviz_stats.get("cedears_total", tech_total))
    finviz_fund_covered = int(finviz_stats.get("fundamentals_covered", 0))
    finviz_ratings_covered = int(finviz_stats.get("ratings_covered", 0))
    return {
        "tech_total": tech_total,
        "tech_covered": tech_covered,
        "tech_enabled": tech_enabled,
        "finviz_total": finviz_total,
        "finviz_fund_covered": finviz_fund_covered,
        "finviz_ratings_covered": finviz_ratings_covered,
    }


def _extract_decision_context(
    *,
    final_decision: pd.DataFrame,
    propuesta: pd.DataFrame,
    technical_overlay: pd.DataFrame,
    market_regime: dict[str, object],
    asignacion_final: pd.DataFrame,
) -> dict[str, object]:
    decision_view, action_col, motive_col = select_decision_view(final_decision, propuesta)
    action_counts = decision_view[action_col].value_counts(dropna=False).to_dict()
    neutrales = sum(int(action_counts.get(action_name, 0)) for action_name in NEUTRAL_ACTIONS)
    technical_view = build_technical_view(technical_overlay)
    family_summary = build_family_summary(decision_view)
    changed_actions, changes_direction_summary, buy_focus, sell_focus = build_change_highlights(
        decision_view,
        action_col=action_col,
        motive_col=motive_col,
    )
    sizing_preview = build_sizing_preview(asignacion_final)
    active_flags_label = ", ".join(str(flag) for flag in (market_regime.get("active_flags", []) or [])) if market_regime else "Ninguno"
    return {
        "decision_view": decision_view,
        "action_col": action_col,
        "motive_col": motive_col,
        "action_counts": action_counts,
        "neutrales": neutrales,
        "technical_view": technical_view,
        "family_summary": family_summary,
        "changed_actions": changed_actions,
        "changes_direction_summary": changes_direction_summary,
        "buy_focus": buy_focus,
        "sell_focus": sell_focus,
        "sizing_preview": sizing_preview,
        "active_flags_label": active_flags_label,
    }


def _extract_run_quality_context(
    *,
    finviz_total: int,
    finviz_fund_covered: int,
    finviz_ratings_covered: int,
    prediction_bundle: dict[str, object],
) -> dict[str, object]:
    finviz_degraded = finviz_total > 0 and (finviz_fund_covered == 0 or finviz_ratings_covered == 0)
    accuracy = prediction_bundle.get("accuracy", {}) if isinstance(prediction_bundle, dict) else {}
    health = accuracy.get("health", {}) if isinstance(accuracy, dict) else {}
    pending_due_verifiable = int(health.get("verifiable_pending_due", 0) or 0)
    if finviz_degraded:
        status = "Degradada"
        detail = f"Finviz {finviz_fund_covered}/{finviz_total} | ratings {finviz_ratings_covered}/{finviz_total}"
        recommendation = "Restaurar capa Finviz (fundamentals/ratings) antes de usar la corrida como referencia táctica."
    elif pending_due_verifiable > 20:
        status = "Crítica"
        detail = f"{pending_due_verifiable} vencidos verificables"
        recommendation = "Priorizar cierre de vencidos verificables (top ticker backlog) hasta bajar de 20."
    elif pending_due_verifiable > 0:
        status = "Atención"
        detail = f"{pending_due_verifiable} vencidos verificables"
        recommendation = "Reducir vencidos verificables a 0 para estabilizar métricas históricas."
    else:
        status = "OK"
        detail = "Sin vencidos verificables"
        recommendation = "Calidad operativa estable. Mantener monitoreo diario."
    return {
        "run_quality_status": status,
        "run_quality_detail": detail,
        "run_quality_recommendation": recommendation,
    }


def _build_pending_portfolio_rows(
    *,
    operations_bundle: dict[str, object],
    df_total: pd.DataFrame,
    prices_iol: dict[str, object],
    vn_factor_map: dict[str, object],
    mep_real: float,
    kpis: dict[str, object],
) -> pd.DataFrame:
    return build_pending_trade_portfolio_rows(
        operations_bundle.get("recent_trades", pd.DataFrame()) if isinstance(operations_bundle, dict) else pd.DataFrame(),
        current_portfolio=df_total,
        prices_iol=prices_iol,
        vn_factor_map=vn_factor_map,
        mep_real=mep_real,
        total_portfolio_ars=float(kpis.get("total_ars", 0) or 0),
    )


def prepare_render_context(result: dict[str, object]) -> dict[str, object]:
    mep_real = float(result["mep_real"])
    generated_at_label = result.get("generated_at_label")
    portfolio_bundle = result["portfolio_bundle"]
    dashboard_bundle = result["dashboard_bundle"]
    decision_bundle = result["decision_bundle"]
    sizing_bundle = result["sizing_bundle"]
    technical_overlay = result.get("technical_overlay", pd.DataFrame())
    price_history: dict[str, list[float]] = result.get("price_history", {}) or {}
    finviz_stats = result.get("finviz_stats", {}) or {}
    bonistas_bundle = result.get("bonistas_bundle", {}) or {}
    operations_bundle = result.get("operations_bundle", {}) or {}
    prediction_bundle = result.get("prediction_bundle", {}) or {}
    risk_bundle = result.get("risk_bundle", {}) or {}
    prices_iol = result.get("precios_iol", {}) or {}
    vn_factor_map = result.get("vn_factor_map", {}) or {}
    decision_memory = decision_bundle.get("decision_memory", {}) or {}
    market_regime = decision_bundle.get("market_regime", {}) or {}

    df_total = portfolio_bundle["df_total"].copy()
    current_tickers = set(df_total.get("Ticker_IOL", pd.Series(dtype=object)).dropna().astype(str).tolist())
    integrity_report = portfolio_bundle["integrity_report"].copy()
    final_decision = decision_bundle["final_decision"].copy()
    propuesta = sizing_bundle.get("propuesta", pd.DataFrame()).copy()
    asignacion_final = sizing_bundle["asignacion_final"].copy()
    resumen_tipos = dashboard_bundle["resumen_tipos"].copy()
    kpis = dashboard_bundle["kpis"]
    bonistas_context = _extract_bonistas_context(bonistas_bundle)
    coverage_context = _extract_coverage_context(
        technical_overlay=technical_overlay,
        portfolio_bundle=portfolio_bundle,
        finviz_stats=finviz_stats,
    )
    decision_context = _extract_decision_context(
        final_decision=final_decision,
        propuesta=propuesta,
        technical_overlay=technical_overlay,
        market_regime=market_regime,
        asignacion_final=asignacion_final,
    )
    run_quality_context = _extract_run_quality_context(
        finviz_total=int(coverage_context["finviz_total"]),
        finviz_fund_covered=int(coverage_context["finviz_fund_covered"]),
        finviz_ratings_covered=int(coverage_context["finviz_ratings_covered"]),
        prediction_bundle=prediction_bundle,
    )
    pending_portfolio_rows = _build_pending_portfolio_rows(
        operations_bundle=operations_bundle,
        df_total=df_total,
        prices_iol=prices_iol,
        vn_factor_map=vn_factor_map,
        mep_real=mep_real,
        kpis=kpis,
    )

    csv_data, csv_filename = _build_csv_export(final_decision, generated_at_label)

    return {
        "mep_real": mep_real,
        "generated_at_label": generated_at_label,
        "sizing_bundle": sizing_bundle,
        "operations_bundle": operations_bundle,
        "decision_memory": decision_memory,
        "market_regime": market_regime,
        "prediction_bundle": prediction_bundle,
        "risk_bundle": risk_bundle,
        "df_total": df_total,
        "current_tickers": current_tickers,
        "integrity_report": integrity_report,
        "asignacion_final": asignacion_final,
        "resumen_tipos": resumen_tipos,
        "kpis": kpis,
        **bonistas_context,
        **coverage_context,
        **decision_context,
        **run_quality_context,
        "price_history": price_history,
        "pending_portfolio_rows": pending_portfolio_rows,
        "csv_data": csv_data,
        "csv_filename": csv_filename,
    }


def build_render_sections(
    context: dict[str, object],
    *,
    time_section,
) -> RenderSections:
    executive_summary = time_section(
        "executive_summary",
        lambda: build_executive_summary(
            action_counts=context["action_counts"],
            decision_memory=context["decision_memory"],
            changed_actions=context["changed_actions"],
            operations_bundle=context["operations_bundle"],
            asignacion_final=context["asignacion_final"] if isinstance(context["asignacion_final"], pd.DataFrame) else pd.DataFrame(),
            current_tickers=context["current_tickers"],
        ),
    )
    primary_cards, secondary_cards, action_summary = time_section(
        "header_cards",
        lambda: build_header_cards(
            generated_at_label=context["generated_at_label"],
            kpis=context["kpis"],
            mep_real=float(context["mep_real"]),
            action_counts=context["action_counts"],
            neutrales=int(context["neutrales"]),
            tech_covered=int(context["tech_covered"]),
            tech_total=int(context["tech_total"]),
            finviz_fund_covered=int(context["finviz_fund_covered"]),
            finviz_total=int(context["finviz_total"]),
            finviz_ratings_covered=int(context["finviz_ratings_covered"]),
            run_quality_status=str(context["run_quality_status"]),
            run_quality_detail=str(context["run_quality_detail"]),
        ),
    )
    panorama_section = time_section(
        "panorama",
        lambda: build_panorama_section(
            executive_summary=executive_summary,
            market_regime=context["market_regime"],
            active_flags_label=str(context["active_flags_label"]),
            tech_enabled=str(context["tech_enabled"]),
            changed_actions=context["changed_actions"],
            sell_focus=context["sell_focus"],
            sizing_bundle=context["sizing_bundle"],
            sizing_preview=str(context["sizing_preview"]),
        ),
    )
    changes_section = time_section(
        "changes",
        lambda: build_changes_section(
            decision_memory=context["decision_memory"],
            changes_direction_summary=str(context["changes_direction_summary"]),
            finviz_fund_covered=int(context["finviz_fund_covered"]),
            finviz_total=int(context["finviz_total"]),
            finviz_ratings_covered=int(context["finviz_ratings_covered"]),
            tech_covered=int(context["tech_covered"]),
            tech_total=int(context["tech_total"]),
            run_quality_status=str(context["run_quality_status"]),
            run_quality_detail=str(context["run_quality_detail"]),
            run_quality_recommendation=str(context["run_quality_recommendation"]),
        ),
    )
    regime_summary = build_regime_section(context["market_regime"])
    bonistas_section = build_bonistas_section(
        show_bonistas=bool(context["show_bonistas"]),
        bond_monitor=context["bond_monitor"],
        bond_subfamily_summary=context["bond_subfamily_summary"],
        bond_local_subfamily_summary=context["bond_local_subfamily_summary"],
        bonistas_macro=context["bonistas_macro"],
        ust_note=context["ust_note"],
    )
    quick_nav = time_section(
        "quick_nav",
        lambda: build_quick_nav(
            show_bonistas=bool(context["show_bonistas"]),
            show_operations=bool(context["operations_bundle"]),
            show_prediction=bool(context["prediction_bundle"]) and not context["prediction_bundle"].get("predictions", pd.DataFrame()).empty,
            csv_filename=str(context.get("csv_filename", "")),
            csv_data=str(context.get("csv_data", "")),
        ),
    )
    operations_section = time_section(
        "operations",
        lambda: (
            build_operations_summary(
                context["operations_bundle"],
                current_tickers=context["current_tickers"],
                current_portfolio=context["df_total"],
            )
            if context["operations_bundle"]
            else ""
        ),
    )
    prediction_section = time_section("prediction", lambda: build_prediction_section(context["prediction_bundle"]))
    summary_section = time_section(
        "summary",
        lambda: build_summary_section(
            kpis=context["kpis"],
            resumen_tipos=context["resumen_tipos"],
            family_summary=context["family_summary"],
            finviz_fund_covered=int(context["finviz_fund_covered"]),
            finviz_total=int(context["finviz_total"]),
            finviz_ratings_covered=int(context["finviz_ratings_covered"]),
            decision_view=context["decision_view"],
            action_col=str(context["action_col"]),
            risk_bundle=context.get("risk_bundle", {}),
        ),
    )
    sizing_section = time_section(
        "sizing",
        lambda: build_sizing_section(
            context["sizing_bundle"],
            context["asignacion_final"],
            df_total=context["df_total"],
            total_ars=float(context["kpis"].get("total_ars", 0) or 0),
        ),
    )
    decision_section = time_section(
        "decision",
        lambda: build_decision_section(
            decision_view=context["decision_view"],
            action_col=str(context["action_col"]),
            motive_col=str(context["motive_col"]),
            action_summary=str(action_summary),
        ),
    )
    portfolio_section = time_section(
        "portfolio",
        lambda: build_portfolio_section(
            context["df_total"],
            pending_rows=context.get("pending_portfolio_rows", pd.DataFrame()),
        ),
    )
    integrity_section = time_section("integrity", lambda: build_integrity_section(context["integrity_report"]))
    integrity_strip = build_integrity_strip(context["integrity_report"], context["generated_at_label"])
    return {
        "primary_cards": primary_cards,
        "secondary_cards": secondary_cards,
        "action_summary": action_summary,
        "panorama_section": panorama_section,
        "changes_section": changes_section,
        "regime_summary": regime_summary,
        "bonistas_section": bonistas_section,
        "quick_nav": quick_nav,
        "operations_section": operations_section,
        "prediction_section": prediction_section,
        "summary_section": summary_section,
        "sizing_section": sizing_section,
        "decision_section": decision_section,
        "portfolio_section": portfolio_section,
        "integrity_section": integrity_section,
        "integrity_strip": integrity_strip,
    }


def _derive_integrity_status(integrity_report: object) -> str:
    if not isinstance(integrity_report, pd.DataFrame) or integrity_report.empty or "estado" not in integrity_report.columns:
        return "ok"
    estados = integrity_report["estado"].str.upper()
    if (estados == "ERROR").any():
        return "error"
    if estados.isin({"WARN", "ERROR"}).any():
        return "warn"
    return "ok"


def compose_report_body_inputs(
    *,
    context: dict[str, object],
    sections: RenderSections,
    title: str,
    headline: str,
    lede: str,
) -> ReportBodyInputs:
    return {
        "title": title,
        "generated_at_label": context.get("generated_at_label"),
        "total_ars": float(context["kpis"].get("total_ars", 0) or 0),
        "total_usd": float(context["kpis"].get("total_usd", 0) or 0),
        "integrity_status": _derive_integrity_status(context["integrity_report"]),
        "headline": headline,
        "lede": lede,
        "integrity_strip": sections.get("integrity_strip", ""),
        "quick_nav": sections["quick_nav"],
        "primary_cards": sections["primary_cards"],
        "secondary_cards": sections["secondary_cards"],
        "action_summary": sections["action_summary"],
        "panorama_section": sections["panorama_section"],
        "changes_section": sections["changes_section"],
        "operations_section": sections["operations_section"],
        "prediction_section": sections["prediction_section"],
        "regime_summary": sections["regime_summary"],
        "summary_section": sections["summary_section"],
        "sizing_section": sections["sizing_section"],
        "tech_enabled": str(context["tech_enabled"]),
        "tech_covered": int(context["tech_covered"]),
        "tech_total": int(context["tech_total"]),
        "technical_view": context["technical_view"],
        "price_history": context.get("price_history", {}),
        "bonistas_section": sections["bonistas_section"],
        "decision_section": sections["decision_section"],
        "portfolio_section": sections["portfolio_section"],
        "integrity_section": sections["integrity_section"],
    }
