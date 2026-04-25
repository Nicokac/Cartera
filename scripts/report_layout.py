from __future__ import annotations

import html
import pandas as pd

from report_decision import build_decision_priority_board, build_decision_table
from report_primitives import (
    build_collapsible,
    build_focus_list,
    build_table,
    build_technical_table,
    esc_text,
    fmt_ars,
    fmt_pct,
    fmt_quantity,
    fmt_label,
    fmt_usd,
)
from report_sections import build_technical_summary

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
      <article class="card compact"><span class="label">Cobertura tecnica</span><strong>{tech_covered}/{tech_total}</strong></article>
      <article class="card compact"><span class="label">Cobertura Finviz</span><strong>{finviz_fund_covered}/{finviz_total}</strong></article>
      <article class="card compact"><span class="label">Ratings Finviz</span><strong>{finviz_ratings_covered}/{finviz_total}</strong></article>
    </section>
    """

    action_summary = f"""
    <section class="action-strip">
      <article class="action-card buy"><span>Refuerzos</span><strong>{int(action_counts.get(ACTION_REFUERZO, 0))}</strong></article>
      <article class="action-card sell"><span>Reducciones</span><strong>{int(action_counts.get(ACTION_REDUCIR, 0))}</strong></article>
      <article class="action-card fund"><span>Despliegue</span><strong>{int(action_counts.get(ACTION_DESPLEGAR_LIQUIDEZ, 0))}</strong></article>
      <article class="action-card neutral"><span>Neutrales</span><strong>{neutrales}</strong></article>
    </section>
    """
    return primary_cards, secondary_cards, action_summary


def build_panorama_section(
    *,
    executive_summary: str,
    market_regime: dict[str, object],
    active_flags_label: str,
    tech_enabled: str,
    buy_focus: list[dict[str, str]],
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
          <span>Régimen: <strong>{'Activo' if market_regime.get('any_active') else 'Sin activación'}</strong></span>
          <span>Flags activos: <strong>{esc_text(active_flags_label)}</strong></span>
          <span>Overlay técnico: <strong>{tech_enabled}</strong></span>
        </div>
        <div class="focus-columns">
          <div>
            <h3>Prioridades de refuerzo</h3>
            {build_focus_list(buy_focus, empty_message='Sin refuerzos activos.', tone='buy')}
          </div>
          <div>
            <h3>Prioridades de reducción</h3>
            {build_focus_list(sell_focus, empty_message='Sin reducciones activas.', tone='sell')}
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
    changed_actions: list[dict[str, str]],
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
      <article class="action-card neutral"><span>Cambios materiales</span><strong>{int(decision_memory.get('senales_nuevas', 0))}</strong></article>
      <article class="action-card buy"><span>Refuerzos persistentes</span><strong>{int(decision_memory.get('persistentes_refuerzo', 0))}</strong></article>
      <article class="action-card sell"><span>Reducciones persistentes</span><strong>{int(decision_memory.get('persistentes_reduccion', 0))}</strong></article>
      <article class="action-card fund"><span>Sin historial</span><strong>{int(decision_memory.get('sin_historial', 0))}</strong></article>
    </section>
    """

    return f"""
    <section class="panel" id="cambios">
      <div class="panel-head">
        <h2>Cambios</h2>
      </div>
      {memory_summary}
      {changes_direction_summary}
      <div class="focus-columns">
        <div>
          <h3>Cambios de accion</h3>
          {build_focus_list(changed_actions, empty_message='Sin cambios de accion respecto de la corrida previa.', tone='neutral')}
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
              <div class="focus-top"><strong>Técnico</strong></div>
              <div class="focus-title">{tech_covered}/{tech_total} con overlay</div>
              <div class="focus-detail">Cobertura tecnica efectiva para la lectura de tendencia y momentum.</div>
            </article>
          </div>
        </div>
      </div>
    </section>
    """


def build_quick_nav(*, show_bonistas: bool, show_operations: bool, show_prediction: bool) -> str:
    bonistas_nav = '<a href="#bonistas">Bonos Locales</a>' if show_bonistas else ""
    operations_nav = '<a href="#operaciones">Operaciones</a>' if show_operations else ""
    prediction_nav = '<a href="#prediccion">Predicción</a>' if show_prediction else ""
    return f"""
    <nav class="quick-nav">
      <a href="#panorama">Panorama</a>
      <a href="#cambios">Cambios</a>
      {operations_nav}
      {prediction_nav}
      <a href="#regimen">Régimen</a>
      <a href="#resumen">Resumen</a>
      <a href="#sizing">Sizing</a>
      <a href="#tecnico">Técnico</a>
      {bonistas_nav}
      <a href="#decision">Decisión</a>
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
            f'<span class="regime-chip {state_class}"><strong>{esc_text(flag_name)}</strong> {state_label}</span>'
        )
    active_flags_label = ", ".join(str(flag) for flag in regime_active_flags) if regime_active_flags else "Ninguno"
    regime_state = "Activo" if market_regime.get("any_active") else "Sin activación"
    regime_state_class = "regime-chip-active" if market_regime.get("any_active") else "regime-chip-inactive"
    return f"""
    <section class="panel" id="regimen">
      <h2>Régimen de mercado</h2>
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

    sizing_items = []
    for _, row in asignacion_final.head(3).iterrows():
        sizing_items.append(
            {
                "kicker": str(row.get("Ticker_IOL", "-")),
                "title": f"{fmt_pct(row.get('Peso_Fondeo_%'))} del fondeo",
                "detail": f"{fmt_ars(row.get('Monto_ARS'))} | {fmt_usd(row.get('Monto_USD'))}",
            }
        )
    return build_focus_list(
        sizing_items,
        empty_message="Sin sizing sugerido.",
        tone="fund",
    )


def build_decision_section(
    *,
    decision_view: pd.DataFrame,
    action_col: str,
    motive_col: str,
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
      {build_decision_priority_board(decision_view, action_col=action_col, motive_col=motive_col)}
      {build_collapsible("Ver tabla completa de decision", build_decision_table(decision_view, action_col=action_col, motive_col=motive_col))}
    </section>
    """


def build_portfolio_section(df_total: pd.DataFrame, *, pending_rows: pd.DataFrame | None = None) -> str:
    pending_block = ""
    if isinstance(pending_rows, pd.DataFrame) and not pending_rows.empty:
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
            "Ver tenencias pendientes de consolidacion",
            build_table(
                pending_view,
                formatters={
                    "Cantidad": fmt_quantity,
                    "Cantidad_Real": fmt_quantity,
                    "Precio_ARS": fmt_ars,
                    "Valorizado_ARS": fmt_ars,
                    "Valor_USD": fmt_usd,
                    "Peso_%": fmt_pct,
                    "Fuente": fmt_label,
                },
            ),
            compact=True,
        )

    return f"""
    <section class="panel" id="cartera">
      <h2>Cartera maestra</h2>
      {build_collapsible(
          "Ver cartera completa",
          build_table(
              df_total[["Ticker_IOL", "Tipo", "Bloque", "Valorizado_ARS", "Valor_USD", "Ganancia_ARS", "Peso_%"]]
              .sort_values("Valorizado_ARS", ascending=False),
              formatters={
                  "Valorizado_ARS": fmt_ars,
                  "Valor_USD": fmt_usd,
                  "Ganancia_ARS": fmt_ars,
                  "Peso_%": fmt_pct,
              },
          ),
          compact=True,
      )}
      {pending_block}
    </section>
    """


def build_integrity_section(integrity_report: pd.DataFrame) -> str:
    return f"""
    <section class="panel" id="integridad">
      <h2>Integridad</h2>
      {build_collapsible("Ver chequeos de integridad", build_table(integrity_report), compact=True)}
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
    action_summary: str,
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
    generated_at_text = str(generated_at_label or "").strip()
    generated_date = generated_at_text.split(" ", 1)[0] if generated_at_text else ""
    title_prefix = f"{title} · {generated_date}" if generated_date else title
    tab_title = f"{title_prefix} | Smoke Report"
    meta_description = (
        f"{title}. Reporte generado {generated_at_text or 'sin timestamp'} "
        "con panorama, cambios, decisiones, cartera e integridad."
    )
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc_text(tab_title)}</title>
  <meta name="description" content="{esc_text(meta_description)}">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main class="page">
    <header class="hero">
      <div>
        <p class="eyebrow">{esc_text(title)}</p>
        <h1>{esc_text(headline)}</h1>
        <p class="lede">{lede}</p>
      </div>
    </header>

    {integrity_strip}
    {quick_nav}

    {primary_cards}
    {secondary_cards}
    {action_summary}
    {panorama_section}
    {changes_section}
    {operations_section}
    {prediction_section}
    {regime_summary}

    <section class="grid">
      {summary_section}
      {sizing_section}
    </section>

    <section class="panel" id="tecnico">
      <h2>Overlay técnico</h2>
      <div class="meta">
        <span>Activo: <strong>{tech_enabled}</strong></span>
        <span>Cobertura: <strong>{tech_covered}/{tech_total}</strong></span>
      </div>
      {build_technical_summary(technical_view)}
      {build_collapsible("Ver tabla tecnica completa", build_technical_table(technical_view, price_history=price_history or {}), compact=True)}
    </section>

    {bonistas_section}
    {decision_section}
    {portfolio_section}
    {integrity_section}
  </main>
  <script>
    const tickerInput = document.getElementById('ticker-filter');
    const actionSelect = document.getElementById('action-filter');
    const typeSelect = document.getElementById('type-filter');
    const rows = Array.from(document.querySelectorAll('#decision-table tbody tr'));
    const riskHistoryFilter = document.getElementById('risk-history-filter');
    const riskHistoryTypeFilter = document.getElementById('risk-history-type-filter');
    const riskRows = Array.from(document.querySelectorAll('#risk-history-table tbody tr'));
    const navLinks = Array.from(document.querySelectorAll('.quick-nav a[href^="#"]'));
    const observedSections = Array.from(document.querySelectorAll('section[id]'));

    if (typeSelect) {{
      const types = [...new Set(rows.map((r) => r.dataset.type).filter(Boolean))].sort();
      types.forEach((t) => {{
        const opt = document.createElement('option');
        opt.value = t;
        opt.textContent = t;
        typeSelect.appendChild(opt);
      }});
    }}

    function applyDecisionFilter() {{
      const tickerNeedle = (tickerInput?.value || '').toLowerCase().trim();
      const actionNeedle = actionSelect?.value || '';
      const typeNeedle = typeSelect?.value || '';
      rows.forEach((row) => {{
        const ticker = (row.dataset.ticker || '').toLowerCase();
        const action = row.dataset.action || '';
        const type = row.dataset.type || '';
        const matchesTicker = !tickerNeedle || ticker.includes(tickerNeedle);
        const matchesAction = !actionNeedle || action === actionNeedle;
        const matchesType = !typeNeedle || type === typeNeedle;
        row.style.display = matchesTicker && matchesAction && matchesType ? '' : 'none';
      }});
    }}

    tickerInput?.addEventListener('input', applyDecisionFilter);
    actionSelect?.addEventListener('change', applyDecisionFilter);
    typeSelect?.addEventListener('change', applyDecisionFilter);

    function applyRiskHistoryFilter() {{
      const qualityNeedle = riskHistoryFilter?.value || '';
      const typeNeedle = riskHistoryTypeFilter?.value || '';
      riskRows.forEach((row) => {{
        const typeCell = row.children[1];
        const qualityCell = row.children[5];
        const type = (typeCell?.textContent || '').trim();
        const quality = (qualityCell?.textContent || '').trim();
        const matchesQuality = !qualityNeedle || quality === qualityNeedle;
        const matchesType = !typeNeedle || type === typeNeedle;
        row.style.display = matchesQuality && matchesType ? '' : 'none';
      }});
    }}

    riskHistoryFilter?.addEventListener('change', applyRiskHistoryFilter);
    riskHistoryTypeFilter?.addEventListener('change', applyRiskHistoryFilter);

    let sortState = {{ col: null, dir: 'asc' }};

    function sortRows(col) {{
      sortState.dir = sortState.col === col && sortState.dir === 'asc' ? 'desc' : 'asc';
      sortState.col = col;
      const tbody = document.querySelector('#decision-table tbody');
      const sorted = [...rows].sort((a, b) => {{
        const av = parseFloat(a.dataset[col] ?? 0);
        const bv = parseFloat(b.dataset[col] ?? 0);
        return sortState.dir === 'asc' ? av - bv : bv - av;
      }});
      sorted.forEach((r) => tbody.appendChild(r));
      document.querySelectorAll('#decision-table th.sortable').forEach((th) => {{
        th.dataset.dir = th.dataset.sort === col ? sortState.dir : '';
      }});
      applyDecisionFilter();
    }}

    document.querySelectorAll('#decision-table th.sortable').forEach((th) => {{
      th.addEventListener('click', () => sortRows(th.dataset.sort));
    }});

    const copySizingBtn = document.getElementById('copy-sizing');
    if (copySizingBtn) {{
      copySizingBtn.addEventListener('click', () => {{
        const table = document.getElementById('sizing-table');
        if (!table) return;
        const headers = Array.from(table.querySelectorAll('thead th')).map((th) => th.textContent.trim());
        const dataRows = Array.from(table.querySelectorAll('tbody tr')).map((r) =>
          Array.from(r.querySelectorAll('td')).map((td) => td.textContent.trim()).join('\t')
        );
        navigator.clipboard.writeText([headers.join('\t'), ...dataRows].join('\n')).then(() => {{
          copySizingBtn.textContent = '\u2713 Copiado';
          setTimeout(() => {{ copySizingBtn.textContent = 'Copiar'; }}, 2000);
        }});
      }});
    }}

    const toggleTechBtn = document.getElementById('toggle-tech-cols');
    if (toggleTechBtn) {{
      toggleTechBtn.addEventListener('click', () => {{
        const table = document.querySelector('.technical-table');
        if (!table) return;
        const expanded = table.classList.toggle('show-secondary');
        toggleTechBtn.textContent = expanded ? 'Ocultar columnas secundarias' : 'Mostrar m\u00e1s columnas';
      }});
    }}

    function setActiveNavByHash() {{
      const hash = window.location.hash;
      if (!hash) return;
      navLinks.forEach((link) => {{
        link.classList.toggle('active', link.getAttribute('href') === hash);
      }});
    }}

    const observer = new IntersectionObserver((entries) => {{
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      const id = `#${{visible.target.id}}`;
      navLinks.forEach((link) => {{
        link.classList.toggle('active', link.getAttribute('href') === id);
      }});
    }}, {{ threshold: [0.2, 0.45, 0.7] }});

    observedSections.forEach((section) => observer.observe(section));
    setActiveNavByHash();
    window.addEventListener('hashchange', setActiveNavByHash);

    function updateQuickNavOverflow() {{
      const quickNav = document.querySelector('.quick-nav');
      if (!quickNav) return;
      const overflow = quickNav.scrollWidth - quickNav.clientWidth > 4;
      quickNav.classList.toggle('is-scrollable', overflow);
      quickNav.classList.toggle('has-overflow-left', quickNav.scrollLeft > 4);
      quickNav.classList.toggle('has-overflow-right', quickNav.scrollLeft + quickNav.clientWidth < quickNav.scrollWidth - 4);
    }}

    const quickNav = document.querySelector('.quick-nav');
    if (quickNav) {{
      quickNav.addEventListener('scroll', updateQuickNavOverflow, {{ passive: true }});
      window.addEventListener('resize', updateQuickNavOverflow);
      updateQuickNavOverflow();
    }}

    document.querySelectorAll('details').forEach((det) => {{
      const summary = det.querySelector('summary');
      if (!summary) return;
      const slug = summary.textContent.trim().toLowerCase()
        .replace(/\\s+/g, '-').replace(/[^a-z0-9-]/g, '').slice(0, 60);
      const key = 'det-' + slug;
      const saved = localStorage.getItem(key);
      if (saved === 'open') det.open = true;
      else if (saved === 'closed') det.open = false;
      det.addEventListener('toggle', () => {{
        localStorage.setItem(key, det.open ? 'open' : 'closed');
      }});
    }});
  </script>
</body>
</html>
"""
