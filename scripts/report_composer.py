from __future__ import annotations

import pandas as pd

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
    build_prediction_section,
    build_sizing_section,
    build_summary_section,
)
from portfolio.operations import build_pending_trade_portfolio_rows

from decision.action_constants import NEUTRAL_ACTIONS


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
    tech_total = int(len(portfolio_bundle.get("df_cedears", pd.DataFrame())))
    tech_covered = int(technical_overlay[tech_available_cols].notna().any(axis=1).sum()) if tech_available_cols else 0
    tech_enabled = "Si" if tech_covered > 0 else "No"
    finviz_total = int(finviz_stats.get("cedears_total", tech_total))
    finviz_fund_covered = int(finviz_stats.get("fundamentals_covered", 0))
    finviz_ratings_covered = int(finviz_stats.get("ratings_covered", 0))

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
    pending_portfolio_rows = build_pending_trade_portfolio_rows(
        operations_bundle.get("recent_trades", pd.DataFrame()) if isinstance(operations_bundle, dict) else pd.DataFrame(),
        current_portfolio=df_total,
        prices_iol=prices_iol,
        vn_factor_map=vn_factor_map,
        mep_real=mep_real,
        total_portfolio_ars=float(kpis.get("total_ars", 0) or 0),
    )

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
        "bond_monitor": bond_monitor,
        "bond_subfamily_summary": bond_subfamily_summary,
        "bond_local_subfamily_summary": bond_local_subfamily_summary,
        "bonistas_macro": bonistas_macro,
        "ust_note": ust_note,
        "show_bonistas": show_bonistas,
        "tech_total": tech_total,
        "tech_covered": tech_covered,
        "tech_enabled": tech_enabled,
        "finviz_total": finviz_total,
        "finviz_fund_covered": finviz_fund_covered,
        "finviz_ratings_covered": finviz_ratings_covered,
        "decision_view": decision_view,
        "action_col": action_col,
        "motive_col": motive_col,
        "action_counts": action_counts,
        "neutrales": neutrales,
        "technical_view": technical_view,
        "price_history": price_history,
        "pending_portfolio_rows": pending_portfolio_rows,
        "family_summary": family_summary,
        "changed_actions": changed_actions,
        "changes_direction_summary": changes_direction_summary,
        "buy_focus": buy_focus,
        "sell_focus": sell_focus,
        "sizing_preview": sizing_preview,
        "active_flags_label": active_flags_label,
    }


def build_render_sections(
    context: dict[str, object],
    *,
    time_section,
) -> dict[str, object]:
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
