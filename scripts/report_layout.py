from __future__ import annotations

import pandas as pd

from decision.action_constants import (
    ACTION_DESPLEGAR_LIQUIDEZ,
    ACTION_MANTENER_NEUTRAL,
    ACTION_REDUCIR,
    ACTION_REFUERZO,
)
from report_decision import build_decision_priority_board, build_decision_table
from report_layout_sections import (
    build_changes_section,
    build_header_cards,
    build_integrity_strip,
    build_panorama_section,
    build_quick_nav,
    build_regime_section,
    build_sizing_preview,
)
from report_page import build_report_page
from report_primitives import (
    build_collapsible,
    build_table,
    esc_text,
    fmt_ars,
    fmt_pct,
    fmt_quantity,
    fmt_label,
    fmt_usd,
)

def build_decision_section(
    *,
    decision_view: pd.DataFrame,
    action_col: str,
    motive_col: str,
    action_summary: str = "",
) -> str:
    return f"""
    <section class="panel" id="decision">
      <div class="panel-head">
      <h2>Decisi\u00f3n final</h2>
        <div class="filters">
          <input id="ticker-filter" type="search" placeholder="Filtrar ticker">
          <select id="action-filter">
            <option value="">Todas las acciones</option>
            <option value="{ACTION_REFUERZO}">{ACTION_REFUERZO}</option>
            <option value="{ACTION_REDUCIR}">{ACTION_REDUCIR}</option>
            <option value="{ACTION_DESPLEGAR_LIQUIDEZ}">{ACTION_DESPLEGAR_LIQUIDEZ}</option>
            <option value="{ACTION_MANTENER_NEUTRAL}">{ACTION_MANTENER_NEUTRAL}</option>
          </select>
          <select id="type-filter">
            <option value="">Todos los tipos</option>
          </select>
        </div>
      </div>
      {action_summary}
      {build_decision_priority_board(decision_view, action_col=action_col, motive_col=motive_col)}
      {build_collapsible("Ver tabla completa de decision", build_decision_table(decision_view, action_col=action_col, motive_col=motive_col))}
    </section>
    """


def build_portfolio_section(df_total: pd.DataFrame, *, pending_rows: pd.DataFrame | None = None) -> str:
    pending_block = ""
    pending_count = 0
    total_positions = int(len(df_total)) if isinstance(df_total, pd.DataFrame) else 0
    unique_types = int(df_total["Tipo"].nunique()) if isinstance(df_total, pd.DataFrame) and "Tipo" in df_total.columns else 0
    principal_label = "-"
    if isinstance(df_total, pd.DataFrame) and not df_total.empty and "Valorizado_ARS" in df_total.columns:
        principal_row = df_total.sort_values("Valorizado_ARS", ascending=False).iloc[0]
        principal_label = f"{principal_row.get('Ticker_IOL', '-')} \u00b7 {fmt_pct(principal_row.get('Peso_%'))}"

    if isinstance(pending_rows, pd.DataFrame) and not pending_rows.empty:
        pending_count = len(pending_rows)
        pending_view = pending_rows.copy()
        pending_columns = [
            "Ticker_IOL",
            "Tipo",
            "Bloque",
            "Cantidad",
            "Cantidad_Real",
            "Precio_ARS",
            "Valorizado_ARS",
            "Valor_USD",
            "Peso_%",
            "Fuente",
        ]
        pending_view = pending_view[[col for col in pending_columns if col in pending_view.columns]]
        if "Valorizado_ARS" in pending_view.columns:
            pending_view = pending_view.sort_values("Valorizado_ARS", ascending=False, na_position="last")
        pending_block = build_collapsible(
            "Ver tenencias pendientes de consolidaci\u00f3n",
            build_table(
                pending_view.rename(columns={"Ticker_IOL": "Ticker", "Cantidad_Real": "Cantidad real", "Precio_ARS": "Precio ARS", "Valorizado_ARS": "Valorizado ARS", "Valor_USD": "Valor USD", "Peso_%": "Peso %"}),
                formatters={
                    "Cantidad": fmt_quantity,
                    "Cantidad real": fmt_quantity,
                    "Precio ARS": fmt_ars,
                    "Valorizado ARS": fmt_ars,
                    "Valor USD": fmt_usd,
                    "Peso %": fmt_pct,
                    "Fuente": fmt_label,
                },
            ),
            compact=True,
        )

    return f"""
    <section class="panel" id="cartera">
      <h2>Cartera maestra</h2>
      <div class="meta">
        <span>Posiciones: <strong>{total_positions}</strong></span>
        <span>Tipos presentes: <strong>{unique_types}</strong></span>
        <span>Mayor posici\u00f3n: <strong>{esc_text(principal_label)}</strong></span>
        <span>Pendientes: <strong>{pending_count}</strong></span>
      </div>
      {build_collapsible(
          "Ver cartera completa",
          build_table(
              df_total[["Ticker_IOL", "Tipo", "Bloque", "Valorizado_ARS", "Valor_USD", "Ganancia_ARS", "Peso_%"]]
              .sort_values("Valorizado_ARS", ascending=False)
              .rename(columns={"Ticker_IOL": "Ticker", "Valorizado_ARS": "Valorizado ARS", "Valor_USD": "Valor USD", "Ganancia_ARS": "Ganancia ARS", "Peso_%": "Peso %"}),
              formatters={
                  "Valorizado ARS": fmt_ars,
                  "Valor USD": fmt_usd,
                  "Ganancia ARS": fmt_ars,
                  "Peso %": fmt_pct,
              },
          ),
          compact=True,
      )}
      {pending_block}
    </section>
    """


def build_integrity_section(integrity_report: pd.DataFrame) -> str:
    n_checks = len(integrity_report) if isinstance(integrity_report, pd.DataFrame) else 0
    n_warn = 0
    status = "OK"
    if isinstance(integrity_report, pd.DataFrame) and not integrity_report.empty and "estado" in integrity_report.columns:
        estados = integrity_report["estado"].astype(str).str.upper()
        n_warn = int(estados.isin({"WARN", "ERROR"}).sum())
        if (estados == "ERROR").any():
            status = "ERROR"
        elif n_warn > 0:
            status = "WARN"

    return f"""
    <section class="panel" id="integridad">
      <h2>Integridad</h2>
      <div class="meta">
        <span>Estado general: <strong>{status}</strong></span>
        <span>Chequeos: <strong>{n_checks}</strong></span>
        <span>Alertas: <strong>{n_warn}</strong></span>
      </div>
      {build_collapsible("Ver chequeos de integridad", build_table(integrity_report.rename(columns={"check": "Chequeo", "estado": "Estado", "detalle": "Detalle"})), compact=True)}
    </section>
    """


def build_report_body(
    *,
    title: str,
    generated_at_label: object,
    headline: str,
    lede: str,
    integrity_strip: str = "",
    quick_nav: str,
    primary_cards: str,
    secondary_cards: str,
    action_summary: str = "",
    panorama_section: str,
    changes_section: str,
    operations_section: str,
    prediction_section: str,
    regime_summary: str,
    summary_section: str,
    sizing_section: str,
    tech_enabled: str,
    tech_covered: int,
    tech_total: int,
    technical_view: pd.DataFrame,
    price_history: dict | None = None,
    bonistas_section: str,
    decision_section: str,
    portfolio_section: str,
    integrity_section: str,
) -> str:
    return build_report_page(
        title=title,
        generated_at_label=generated_at_label,
        headline=headline,
        lede=lede,
        integrity_strip=integrity_strip,
        quick_nav=quick_nav,
        primary_cards=primary_cards,
        secondary_cards=secondary_cards,
        panorama_section=panorama_section,
        changes_section=changes_section,
        operations_section=operations_section,
        prediction_section=prediction_section,
        regime_summary=regime_summary,
        summary_section=summary_section,
        sizing_section=sizing_section,
        tech_enabled=tech_enabled,
        tech_covered=tech_covered,
        tech_total=tech_total,
        technical_view=technical_view,
        price_history=price_history,
        bonistas_section=bonistas_section,
        decision_section=decision_section,
        portfolio_section=portfolio_section,
        integrity_section=integrity_section,
    )




