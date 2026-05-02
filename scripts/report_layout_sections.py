from __future__ import annotations

import html
import pandas as pd

from report_primitives import (
    build_collapsible,
    build_focus_list,
    build_table,
    esc_text,
    fmt_ars,
    fmt_label,
    fmt_pct,
    fmt_quantity,
    fmt_usd,
)
from report_decision import build_decision_priority_board, build_decision_table
from decision.action_constants import (
    ACTION_DESPLEGAR_LIQUIDEZ,
    ACTION_MANTENER_NEUTRAL,
    ACTION_REDUCIR,
    ACTION_REFUERZO,
)


def build_integrity_strip(
    integrity_report: pd.DataFrame,
    generated_at_label: object,
) -> str:
    status = "ok"
    n_checks = 0
    n_warn = 0
    if isinstance(integrity_report, pd.DataFrame) and not integrity_report.empty and "estado" in integrity_report.columns:
        n_checks = len(integrity_report)
        estados = integrity_report["estado"].str.upper()
        n_warn = int(estados.isin({"WARN", "ERROR"}).sum())
        if (estados == "ERROR").any():
            status = "error"
        elif n_warn > 0:
            status = "warn"

    status_label = {"ok": "OK", "warn": "WARN", "error": "ERROR"}[status]
    time_part = str(generated_at_label or "")
    if " " in time_part:
        time_part = time_part.split(" ", 1)[1]
    warn_part = (
        f' &middot; <span class="integrity-warn-count">{n_warn} alerta{"s" if n_warn != 1 else ""}</span>'
        if n_warn > 0
        else ""
    )
    return (
        f'<div class="integrity-strip integrity-{html.escape(status)}">'
        f'<span class="integrity-dot"></span>'
        f'<span>Integridad: <strong>{html.escape(status_label)}</strong>'
        f" &middot; {n_checks} checks{warn_part}</span>"
        f'<span class="integrity-time">{html.escape(time_part)}</span>'
        f"</div>"
    )


def build_header_cards(
    *,
    generated_at_label: object,
    kpis: dict[str, object],
    mep_real: float,
    action_counts: dict[object, object],
    neutrales: int,
    tech_covered: int,
    tech_total: int,
    finviz_fund_covered: int,
    finviz_total: int,
    finviz_ratings_covered: int,
) -> tuple[str, str, str]:
    primary_cards = f"""
    <section class="cards cards-primary">
      <article class="card"><span class="label">Corrida</span><strong>{esc_text(generated_at_label)}</strong></article>
      <article class="card"><span class="label">Total ARS consolidado</span><strong>{fmt_ars(kpis['total_ars'])}</strong></article>
      <article class="card"><span class="label">Liquidez broker</span><strong>{fmt_ars(kpis.get('liquidez_broker_ars', kpis['liquidez_ars']))}</strong></article>
      <article class="card"><span class="label">MEP</span><strong>{fmt_ars(mep_real)}</strong></article>
      <article class="card"><span class="label">Refuerzos</span><strong>{int(action_counts.get(ACTION_REFUERZO, 0))}</strong></article>
      <article class="card"><span class="label">Reducciones</span><strong>{int(action_counts.get(ACTION_REDUCIR, 0))}</strong></article>
    </section>
    """
    secondary_cards = f"""
    <section class="cards cards-secondary">
      <article class="card compact"><span class="label">Total ARS estilo IOL</span><strong>{fmt_ars(kpis['total_ars_iol'])}</strong></article>
      <article class="card compact"><span class="label">Liquidez ampliada</span><strong>{fmt_ars(kpis['liquidez_ars'])}</strong></article>
      <article class="card compact"><span class="label">Total USD</span><strong>{fmt_usd(kpis['total_usd'])}</strong></article>
      <article class="card compact"><span class="label">Ganancia</span><strong>{fmt_ars(kpis['ganancia_total'])}</strong></article>
      <article class="card compact"><span class="label">Instrumentos</span><strong>{int(kpis['n_instrumentos'])}</strong></article>
      <article class="card compact"><span class="label">Cobertura t\u00e9cnica</span><strong>{tech_covered}/{tech_total}</strong></article>
      <article class="card compact"><span class="label">Cobertura Finviz</span><strong>{finviz_fund_covered}/{finviz_total}</strong></article>
      <article class="card compact"><span class="label">Ratings Finviz</span><strong>{finviz_ratings_covered}/{finviz_total}</strong></article>
    </section>
    """
    action_summary = f"""
    <section class="action-summary-block" aria-label="Distribuci\u00f3n de acciones">
      <p class="action-summary-title">Distribuci\u00f3n de acciones</p>
      <section class="action-strip">
        <article class="action-card buy"><span>En refuerzo</span><strong>{int(action_counts.get(ACTION_REFUERZO, 0))}</strong></article>
        <article class="action-card sell"><span>En reducci\u00f3n</span><strong>{int(action_counts.get(ACTION_REDUCIR, 0))}</strong></article>
        <article class="action-card fund"><span>En despliegue</span><strong>{int(action_counts.get(ACTION_DESPLEGAR_LIQUIDEZ, 0))}</strong></article>
        <article class="action-card neutral"><span>En neutral</span><strong>{neutrales}</strong></article>
      </section>
    </section>
    """
    return primary_cards, secondary_cards, action_summary


def build_panorama_section(
    *,
    executive_summary: str,
    market_regime: dict[str, object],
    active_flags_label: str,
    tech_enabled: str,
    changed_actions: list[dict[str, str]],
    sell_focus: list[dict[str, str]],
    sizing_bundle: dict[str, object],
    sizing_preview: str,
) -> str:
    return f"""
    <section class="grid spotlight-grid" id="panorama">
      <section class="panel spotlight">
        <h2>Panorama</h2>
        <p class="summary-lede">{esc_text(executive_summary)}</p>
        <div class="meta">
          <span>R\u00e9gimen: <strong>{'Activo' if market_regime.get('any_active') else 'Sin activaci\u00f3n'}</strong></span>
          <span>Flags activos: <strong>{esc_text(active_flags_label)}</strong></span>
          <span>Overlay t\u00e9cnico: <strong>{tech_enabled}</strong></span>
        </div>
        <div class="focus-columns">
          <div>
            <h3>Cambios de se\u00f1al</h3>
            {build_focus_list(changed_actions, empty_message='Sin cambios de se\u00f1al respecto de la corrida previa.', tone='neutral')}
          </div>
          <div>
            <h3>Alertas de cartera</h3>
            {build_focus_list(sell_focus, empty_message='Sin alertas de cartera destacadas.', tone='sell')}
          </div>
        </div>
      </section>
      <section class="panel spotlight spotlight-side" id="sizing-resumen">
        <h2>Sizing activo</h2>
        <div class="meta">
          <span>Fuente: <strong>{esc_text(sizing_bundle['fuente_fondeo'])}</strong></span>
          <span>Monto: <strong>{fmt_ars(sizing_bundle['monto_fondeo_ars'])}</strong></span>
          <span>Usa liquidez IOL: <strong>{"Si" if sizing_bundle.get('usar_liquidez_iol') else "No"}</strong></span>
        </div>
        {sizing_preview}
      </section>
    </section>
    """


def build_changes_section(
    *,
    decision_memory: dict[str, object],
    changes_direction_summary: str,
    finviz_fund_covered: int,
    finviz_total: int,
    finviz_ratings_covered: int,
    tech_covered: int,
    tech_total: int,
) -> str:
    memory_summary = ""
    if decision_memory:
        memory_summary = f"""
    <section class="action-strip compact-strip">
      <article class="action-card neutral"><span>Cambios materiales</span><strong>{int(decision_memory.get('se\u00f1ales_nuevas', 0))}</strong></article>
      <article class="action-card buy"><span>Refuerzos persistentes</span><strong>{int(decision_memory.get('persistentes_refuerzo', 0))}</strong></article>
      <article class="action-card sell"><span>Reducciones persistentes</span><strong>{int(decision_memory.get('persistentes_reduccion', 0))}</strong></article>
      <article class="action-card fund"><span>Sin historial</span><strong>{int(decision_memory.get('sin_historial', 0))}</strong></article>
    </section>
    """
    memory_focus: list[dict[str, str]] = []
    if decision_memory:
        pr = int(decision_memory.get('persistentes_refuerzo', 0))
        pdn = int(decision_memory.get('persistentes_reduccion', 0))
        memory_focus = [
            {"kicker": "Persistencia alcista", "title": f"{pr} refuerzo{'s' if pr != 1 else ''} {'persisten' if pr != 1 else 'persiste'}", "detail": "Convicciones que se sostienen respecto de la corrida previa."},
            {"kicker": "Persistencia bajista", "title": f"{pdn} reducci\u00f3n{'es' if pdn != 1 else ''} {'persisten' if pdn != 1 else 'persiste'}", "detail": "Se\u00f1ales de recorte que no fueron ruido de una sola corrida."},
            {"kicker": "Novedades", "title": f"{int(decision_memory.get('se\u00f1ales_nuevas', 0))} cambios materiales | {int(decision_memory.get('sin_historial', 0))} sin historial", "detail": "Sirve para separar cambios genuinos de ruido sin base hist\u00f3rica."},
        ]
    return f"""
    <section class="panel" id="cambios">
      <div class="panel-head">
        <h2>Cambios</h2>
      </div>
      {memory_summary}
      {changes_direction_summary}
      <div class="focus-columns">
        <div>
          <h3>Lectura de persistencia</h3>
          {build_focus_list(memory_focus, empty_message='Sin historial suficiente para evaluar persistencia.', tone='neutral')}
        </div>
        <div>
          <h3>Observaciones de cobertura</h3>
          <div class="focus-list tone-neutral">
            <article class="focus-item">
              <div class="focus-top"><strong>Finviz</strong></div>
              <div class="focus-title">{finviz_fund_covered}/{finviz_total} fundamentals | {finviz_ratings_covered}/{finviz_total} ratings</div>
              <div class="focus-detail">Cobertura visible para la capa fundamental y de consenso.</div>
            </article>
            <article class="focus-item">
              <div class="focus-top"><strong>T\u00e9cnico</strong></div>
              <div class="focus-title">{tech_covered}/{tech_total} con overlay</div>
              <div class="focus-detail">Cobertura t\u00e9cnica efectiva para la lectura de tendencia y momentum.</div>
            </article>
          </div>
        </div>
      </div>
    </section>
    """


def build_quick_nav(*, show_bonistas: bool, show_operations: bool, show_prediction: bool) -> str:
    bonistas_nav = '<a href="#bonistas">Bonos</a>' if show_bonistas else ""
    operations_nav = '<a href="#operaciones">Operaciones</a>' if show_operations else ""
    prediction_nav = '<a href="#prediccion">Predicci\u00f3n</a>' if show_prediction else ""
    return f"""
    <nav class="quick-nav">
      <a href="#panorama">Panorama</a>
      <a href="#cambios">Cambios</a>
      {operations_nav}
      {prediction_nav}
      <a href="#regimen">R\u00e9gimen</a>
      <a href="#resumen">Resumen</a>
      <a href="#sizing">Sizing</a>
      <a href="#tecnico">T\u00e9cnico</a>
      {bonistas_nav}
      <a href="#decision">Decisi\u00f3n</a>
      <a href="#cartera">Cartera</a>
      <a href="#integridad">Integridad</a>
    </nav>
    """


def build_regime_section(market_regime: dict[str, object]) -> str:
    if not market_regime:
        return ""
    regime_flags = market_regime.get("flags", {}) or {}
    regime_active_flags = market_regime.get("active_flags", []) or []
    regime_items = []
    for flag_name, is_active in regime_flags.items():
        state_label = "Activo" if is_active else "Inactivo"
        state_class = "regime-chip-active" if is_active else "regime-chip-inactive"
        regime_items.append(
            f'<span class="regime-chip regime-flag"><strong class="regime-flag-name">{esc_text(flag_name)}</strong><span class="regime-flag-status {state_class}">{state_label}</span></span>'
        )
    active_flags_label = ", ".join(str(flag) for flag in regime_active_flags) if regime_active_flags else "Ninguno"
    regime_state = "Activo" if market_regime.get("any_active") else "Sin activaci\u00f3n"
    regime_state_class = "regime-chip-active" if market_regime.get("any_active") else "regime-chip-inactive"
    return f"""
    <section class="panel" id="regimen">
      <h2>R\u00e9gimen de mercado</h2>
      <div class="meta">
        <span class="regime-chip {regime_state_class}"><strong>Estado:</strong> {esc_text(regime_state)}</span>
        <span>Flags activos: <strong>{esc_text(active_flags_label)}</strong></span>
      </div>
      <div class="meta regime-flags">
        {''.join(regime_items) if regime_items else '<span>Sin flags configurados</span>'}
      </div>
    </section>
    """


def build_sizing_preview(asignacion_final: pd.DataFrame) -> str:
    if not isinstance(asignacion_final, pd.DataFrame) or asignacion_final.empty:
        return '<div class="empty compact-empty">Sin sizing sugerido.</div>'
    sizing_items: list[dict[str, str]] = []
    for _, row in asignacion_final.head(3).iterrows():
        sizing_items.append(
            {"kicker": str(row.get("Ticker_IOL", "-")), "title": f"{fmt_pct(row.get('Peso_Fondeo_%'))} del fondeo", "detail": f"{fmt_ars(row.get('Monto_ARS'))} | {fmt_usd(row.get('Monto_USD'))}"}
        )
    return build_focus_list(sizing_items, empty_message="Sin sizing sugerido.", tone="fund")


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
      <h2>Decisión final</h2>
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
        principal_label = f"{principal_row.get('Ticker_IOL', '-')} · {fmt_pct(principal_row.get('Peso_%'))}"

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
            "Ver tenencias pendientes de consolidación",
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
        <span>Mayor posición: <strong>{esc_text(principal_label)}</strong></span>
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
