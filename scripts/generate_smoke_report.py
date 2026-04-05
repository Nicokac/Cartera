from __future__ import annotations

import html
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from smoke_run import run_smoke_pipeline


REPORTS_DIR = ROOT / "reports"
HTML_PATH = REPORTS_DIR / "smoke-report.html"


def fmt_ars(value: object) -> str:
    if pd.isna(value):
        return "-"
    return f"${float(value):,.0f}"


def fmt_usd(value: object) -> str:
    if pd.isna(value):
        return "-"
    return f"USD {float(value):,.2f}"


def fmt_pct(value: object) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value):.2f}%"


def fmt_score(value: object) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value):+.3f}"


def fmt_label(value: object) -> str:
    if pd.isna(value) or value in {None, ""}:
        return "-"
    return str(value)


def metric_class(column: str, value: object) -> str:
    if pd.isna(value):
        return "metric metric-neutral"

    try:
        num = float(value)
    except Exception:
        text = str(value).strip().lower()
        if column == "asset_family":
            if text == "stock":
                return "metric metric-positive"
            if text == "etf":
                return "metric metric-warn"
            if text in {"bond", "liquidity"}:
                return "metric metric-neutral"
        if column == "asset_subfamily":
            if text == "etf_sector":
                return "metric metric-positive"
            if text == "etf_country_region":
                return "metric metric-warn"
            if text in {"etf_core", "etf_other"}:
                return "metric metric-neutral"
        if column == "Tech_Trend":
            if "alcista fuerte" in text:
                return "metric metric-strong"
            if "alcista" in text:
                return "metric metric-positive"
            if "mixta" in text or "parcial" in text:
                return "metric metric-warn"
            if "bajista" in text or "error" in text:
                return "metric metric-negative"
        return "metric metric-neutral"

    if column == "score_unificado":
        if num >= 0.18:
            return "metric metric-strong"
        if num > 0.03:
            return "metric metric-positive"
        if num <= -0.12:
            return "metric metric-negative"
        return "metric metric-neutral"

    if column == "Peso_%":
        if num >= 5:
            return "metric metric-negative"
        if num >= 3:
            return "metric metric-warn"
        if num > 0:
            return "metric metric-positive"
        return "metric metric-neutral"

    if column == "RSI_14":
        if 45 <= num <= 65:
            return "metric metric-positive"
        if 30 <= num < 45 or 65 < num <= 75:
            return "metric metric-warn"
        return "metric metric-negative"

    if column in {"Momentum_20d_%", "Momentum_60d_%", "Dist_SMA20_%", "Dist_SMA50_%", "Dist_EMA20_%", "Dist_EMA50_%"}:
        if num > 1:
            return "metric metric-positive"
        if num < -1:
            return "metric metric-negative"
        return "metric metric-neutral"

    if column == "Vol_20d_Anual_%":
        if num <= 25:
            return "metric metric-positive"
        if num <= 40:
            return "metric metric-warn"
        return "metric metric-negative"

    if column == "Drawdown_desde_Max3m_%":
        if num >= -8:
            return "metric metric-positive"
        if num >= -18:
            return "metric metric-warn"
        return "metric metric-negative"

    return "metric metric-neutral"


def render_metric(column: str, value: object, formatter: callable | None = None) -> str:
    formatter = formatter or (lambda x: "-" if pd.isna(x) else str(x))
    rendered = formatter(value)
    css_class = metric_class(column, value)
    return f"<span class=\"{css_class}\">{html.escape(str(rendered))}</span>"


def build_table(
    df: pd.DataFrame,
    *,
    formatters: dict[str, callable] | None = None,
    table_class: str = "",
) -> str:
    if df.empty:
        return '<div class="empty">Sin datos para mostrar.</div>'

    formatters = formatters or {}
    headers = "".join(f"<th>{html.escape(str(col))}</th>" for col in df.columns)
    rows = []
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            value = row[col]
            formatter = formatters.get(col, lambda x: "-" if pd.isna(x) else str(x))
            rendered = formatter(value)
            cells.append(f"<td>{html.escape(str(rendered))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<div class="table-wrap"><table class="{table_class}"><thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def build_technical_table(df: pd.DataFrame) -> str:
    if df.empty:
        return '<div class="empty">Sin datos para mostrar.</div>'

    formatters = {
        "Peso_%": fmt_pct,
        "RSI_14": lambda x: "-" if pd.isna(x) else f"{float(x):.1f}",
        "Momentum_20d_%": fmt_pct,
        "Momentum_60d_%": fmt_pct,
        "Dist_SMA20_%": fmt_pct,
        "Dist_SMA50_%": fmt_pct,
        "Dist_EMA20_%": fmt_pct,
        "Dist_EMA50_%": fmt_pct,
        "Vol_20d_Anual_%": fmt_pct,
        "Drawdown_desde_Max3m_%": fmt_pct,
    }
    headers = "".join(f"<th>{html.escape(str(col))}</th>" for col in df.columns)
    rows = []
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            if col in formatters or col in {
                "Tech_Trend",
                "RSI_14",
                "Momentum_20d_%",
                "Momentum_60d_%",
                "Dist_SMA20_%",
                "Dist_SMA50_%",
                "Dist_EMA20_%",
                "Dist_EMA50_%",
                "Vol_20d_Anual_%",
                "Drawdown_desde_Max3m_%",
                "Peso_%",
            }:
                cells.append(f"<td>{render_metric(col, row[col], formatters.get(col))}</td>")
            else:
                cells.append(f"<td>{html.escape('-' if pd.isna(row[col]) else str(row[col]))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<div class="table-wrap"><table class="technical-table"><thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def badge_class(action: object) -> str:
    action_text = str(action or "").lower()
    if "refuerzo" in action_text:
        return "badge badge-buy"
    if "reducir" in action_text:
        return "badge badge-sell"
    if "desplegar" in action_text:
        return "badge badge-fund"
    return "badge badge-neutral"


def build_driver_chips(row: pd.Series) -> str:
    drivers = [row.get("driver_1"), row.get("driver_2"), row.get("driver_3")]
    chips = []
    for driver in drivers:
        if pd.isna(driver) or driver in {None, ""}:
            continue
        chips.append(f'<span class="metric metric-neutral">{html.escape(str(driver))}</span>')
    return "".join(chips) if chips else '<span class="muted-inline">-</span>'


def build_decision_table(
    df: pd.DataFrame,
    *,
    action_col: str,
    motive_col: str,
) -> str:
    if df.empty:
        return '<div class="empty">Sin decisiones para mostrar.</div>'

    rows = []
    ordered = df.sort_values("score_unificado", ascending=False)
    for _, row in ordered.iterrows():
        ticker = html.escape(str(row["Ticker_IOL"]))
        tipo = html.escape(str(row["Tipo"]))
        accion = str(row.get(action_col, ""))
        motivo = html.escape(str(row.get(motive_col, "")))
        motivo_score = html.escape(str(row.get("motivo_score", "")))
        driver_html = build_driver_chips(row)
        rows.append(
            "<tr "
            f"data-ticker=\"{ticker}\" "
            f"data-action=\"{html.escape(accion)}\" "
            f"data-type=\"{tipo}\">"
            f"<td><strong>{ticker}</strong></td>"
            f"<td>{tipo}</td>"
            f"<td>{render_metric('asset_family', row.get('asset_family'), fmt_label)}</td>"
            f"<td>{render_metric('asset_subfamily', row.get('asset_subfamily'), fmt_label)}</td>"
            f"<td>{render_metric('Peso_%', row.get('Peso_%'), fmt_pct)}</td>"
            f"<td class=\"score\">{render_metric('score_unificado', row['score_unificado'], fmt_score)}</td>"
            f"<td><span class=\"{badge_class(accion)}\">{html.escape(accion)}</span></td>"
            f"<td><div class=\"driver-stack\">{driver_html}</div></td>"
            f"<td><div>{motivo}</div><div class=\"muted-inline\">{motivo_score}</div></td>"
            "</tr>"
        )

    return (
        '<div class="table-wrap"><table id="decision-table">'
        "<thead><tr><th>Ticker</th><th>Tipo</th><th>Familia</th><th>Subfamilia</th><th>Peso_%</th><th>Score</th><th>Accion</th><th>Drivers</th><th>Motivo</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def render_report(
    result: dict[str, object],
    *,
    title: str = "Smoke Run",
    headline: str = "Prueba visual del pipeline",
    lede: str = "Reporte generado desde <code>scripts/generate_smoke_report.py</code> sin depender del notebook.",
) -> str:
    mep_real = float(result["mep_real"])
    portfolio_bundle = result["portfolio_bundle"]
    dashboard_bundle = result["dashboard_bundle"]
    decision_bundle = result["decision_bundle"]
    sizing_bundle = result["sizing_bundle"]
    technical_overlay = result.get("technical_overlay", pd.DataFrame())
    finviz_stats = result.get("finviz_stats", {}) or {}
    bonistas_bundle = result.get("bonistas_bundle", {}) or {}

    df_total = portfolio_bundle["df_total"].copy()
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
    show_bonistas = (
        (isinstance(bond_monitor, pd.DataFrame) and not bond_monitor.empty)
        or (isinstance(bond_subfamily_summary, pd.DataFrame) and not bond_subfamily_summary.empty)
        or (isinstance(bond_local_subfamily_summary, pd.DataFrame) and not bond_local_subfamily_summary.empty)
        or bool(bonistas_macro)
    )
    tech_metric_cols = [
        "Dist_SMA20_%",
        "Dist_SMA50_%",
        "Dist_EMA20_%",
        "Dist_EMA50_%",
        "RSI_14",
        "Momentum_20d_%",
        "Momentum_60d_%",
        "Vol_20d_Anual_%",
        "Drawdown_desde_Max3m_%",
    ]
    tech_available_cols = [col for col in tech_metric_cols if col in technical_overlay.columns]
    tech_total = int(len(portfolio_bundle.get("df_cedears", pd.DataFrame())))
    tech_covered = int(technical_overlay[tech_available_cols].notna().any(axis=1).sum()) if tech_available_cols else 0
    tech_enabled = "Si" if tech_covered > 0 else "No"
    finviz_total = int(finviz_stats.get("cedears_total", tech_total))
    finviz_fund_covered = int(finviz_stats.get("fundamentals_covered", 0))
    finviz_ratings_covered = int(finviz_stats.get("ratings_covered", 0))

    if not propuesta.empty and "accion_operativa" in propuesta.columns:
        decision_view = propuesta
        action_col = "accion_operativa"
        motive_col = "comentario_operativo" if "comentario_operativo" in propuesta.columns else "motivo_accion"
    else:
        decision_view = final_decision
        action_col = "accion_sugerida_v2"
        motive_col = "motivo_accion"

    action_counts = decision_view[action_col].value_counts(dropna=False).to_dict()
    neutrales = (
        int(action_counts.get("Mantener / Neutral", 0))
        + int(action_counts.get("Mantener / monitorear", 0))
        + int(action_counts.get("Mantener liquidez", 0))
        + int(action_counts.get("Mantener liquidez bloqueada", 0))
    )

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
            "Dist_EMA20_%",
            "Dist_EMA50_%",
            "Vol_20d_Anual_%",
            "Drawdown_desde_Max3m_%",
        ]
        if col in technical_overlay.columns
    ]
    if isinstance(technical_overlay, pd.DataFrame) and not technical_overlay.empty:
        technical_view = technical_overlay[technical_cols].copy()
        if "Momentum_20d_%" in technical_view.columns:
            technical_view = technical_view.sort_values("Momentum_20d_%", ascending=False)
    else:
        technical_view = pd.DataFrame()

    family_summary = pd.DataFrame()
    if isinstance(decision_view, pd.DataFrame) and not decision_view.empty:
        family_base = decision_view.copy()
        if "asset_family" not in family_base.columns:
            family_base["asset_family"] = None
        if "asset_subfamily" not in family_base.columns:
            family_base["asset_subfamily"] = None
        family_summary = (
            family_base.groupby(["asset_family", "asset_subfamily"], dropna=False)
            .agg(
                Instrumentos=("Ticker_IOL", "count"),
                Score_Promedio=("score_unificado", "mean"),
            )
            .reset_index()
            .sort_values(["asset_family", "asset_subfamily"], na_position="last")
        )

    summary_cards = f"""
    <section class="cards">
      <article class="card"><span class="label">MEP</span><strong>{fmt_ars(mep_real)}</strong></article>
      <article class="card"><span class="label">Total ARS consolidado</span><strong>{fmt_ars(kpis['total_ars'])}</strong></article>
      <article class="card"><span class="label">Total ARS estilo IOL</span><strong>{fmt_ars(kpis['total_ars_iol'])}</strong></article>
      <article class="card"><span class="label">Total USD</span><strong>{fmt_usd(kpis['total_usd'])}</strong></article>
      <article class="card"><span class="label">Ganancia</span><strong>{fmt_ars(kpis['ganancia_total'])}</strong></article>
      <article class="card"><span class="label">Instrumentos</span><strong>{int(kpis['n_instrumentos'])}</strong></article>
      <article class="card"><span class="label">Liquidez</span><strong>{fmt_ars(kpis['liquidez_ars'])}</strong></article>
      <article class="card"><span class="label">Liquidez USD en ARS</span><strong>{fmt_ars(kpis['liquidez_usd_ars'])}</strong></article>
      <article class="card"><span class="label">Overlay tecnico</span><strong>{tech_enabled}</strong></article>
      <article class="card"><span class="label">Cobertura tecnica</span><strong>{tech_covered}/{tech_total}</strong></article>
      <article class="card"><span class="label">Cobertura Finviz</span><strong>{finviz_fund_covered}/{finviz_total}</strong></article>
      <article class="card"><span class="label">Ratings Finviz</span><strong>{finviz_ratings_covered}/{finviz_total}</strong></article>
    </section>
    """

    action_summary = f"""
    <section class="action-strip">
      <article class="action-card buy"><span>Refuerzos</span><strong>{int(action_counts.get('Refuerzo', 0))}</strong></article>
      <article class="action-card sell"><span>Reducciones</span><strong>{int(action_counts.get('Reducir', 0))}</strong></article>
      <article class="action-card fund"><span>Despliegue</span><strong>{int(action_counts.get('Desplegar liquidez', 0))}</strong></article>
      <article class="action-card neutral"><span>Neutrales</span><strong>{neutrales}</strong></article>
    </section>
    """

    bonistas_nav = '<a href="#bonistas">Bonos Locales</a>' if show_bonistas else ""
    bonistas_section = ""
    if show_bonistas:
        bonistas_section = f"""
    <section class="panel" id="bonistas">
      <h2>Bonos Locales</h2>
      <div class="meta">
        <span>CER: <strong>{fmt_label(bonistas_macro.get('cer_diario'))}</strong></span>
        <span>TAMAR: <strong>{fmt_label(bonistas_macro.get('tamar'))}</strong></span>
        <span>BADLAR: <strong>{fmt_label(bonistas_macro.get('badlar'))}</strong></span>
        <span>Riesgo pais: <strong>{fmt_label(bonistas_macro.get('riesgo_pais_bps'))}</strong></span>
        <span>REM inflacion: <strong>{fmt_label(bonistas_macro.get('rem_inflacion_mensual_pct'))}</strong></span>
        <span>REM 12m: <strong>{fmt_label(bonistas_macro.get('rem_inflacion_12m_pct'))}</strong></span>
        <span>UST 5y: <strong>{fmt_label(bonistas_macro.get('ust_5y_pct'))}</strong></span>
        <span>UST 10y: <strong>{fmt_label(bonistas_macro.get('ust_10y_pct'))}</strong></span>
      </div>
      <h3>Resumen por subfamilia</h3>
      {build_table(
          bond_subfamily_summary,
          formatters={},
      )}
      <h3>Resumen por taxonomia local</h3>
      {build_table(
          bond_local_subfamily_summary,
          formatters={},
      )}
      <h3>Monitoreo de bonos</h3>
      {build_table(
          bond_monitor,
          formatters={
              "Peso_%": fmt_pct,
              "bonistas_tir_pct": fmt_pct,
              "bonistas_paridad_pct": fmt_pct,
              "bonistas_md": lambda x: "-" if pd.isna(x) else f"{float(x):.2f}",
              "bonistas_tir_vs_avg_365d_pct": fmt_pct,
              "bonistas_parity_gap_pct": fmt_pct,
          },
      )}
    </section>
    """

    html_body = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Smoke Report</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main class="page">
    <header class="hero">
      <div>
        <p class="eyebrow">{html.escape(title)}</p>
        <h1>{html.escape(headline)}</h1>
        <p class="lede">{lede}</p>
      </div>
    </header>

    <nav class="quick-nav">
      <a href="#integridad">Integridad</a>
      <a href="#resumen">Resumen</a>
      <a href="#decision">Decision</a>
      <a href="#tecnico">Tecnico</a>
      {bonistas_nav}
      <a href="#sizing">Sizing</a>
      <a href="#cartera">Cartera</a>
    </nav>

    {summary_cards}
    {action_summary}

    <section class="panel" id="integridad">
      <h2>Integridad</h2>
      {build_table(integrity_report)}
    </section>

    <section class="grid">
      <section class="panel" id="resumen">
        <h2>Resumen por tipo</h2>
        <div class="meta">
          <span>Total consolidado: <strong>{fmt_ars(kpis['total_ars'])}</strong></span>
          <span>Total estilo IOL: <strong>{fmt_ars(kpis['total_ars_iol'])}</strong></span>
          <span>Liquidez USD convertida: <strong>{fmt_ars(kpis['liquidez_usd_ars'])}</strong></span>
          <span>Finviz fundamentals: <strong>{finviz_fund_covered}/{finviz_total}</strong></span>
          <span>Finviz ratings: <strong>{finviz_ratings_covered}/{finviz_total}</strong></span>
        </div>
        {build_table(
            resumen_tipos[["Tipo", "Instrumentos", "Valorizado_ARS", "Valor_USD", "Ganancia_ARS", "Peso_%"]],
            formatters={
                "Valorizado_ARS": fmt_ars,
                "Valor_USD": fmt_usd,
                "Ganancia_ARS": fmt_ars,
                "Peso_%": fmt_pct,
            },
        )}
        <h3>Taxonomia operativa</h3>
        {build_table(
            family_summary[["asset_family", "asset_subfamily", "Instrumentos", "Score_Promedio"]]
            if not family_summary.empty else family_summary,
            formatters={
                "Score_Promedio": fmt_score,
            },
        )}
      </section>

      <section class="panel" id="sizing">
        <h2>Sizing</h2>
        <div class="meta">
          <span>Fuente de fondeo: <strong>{html.escape(str(sizing_bundle['fuente_fondeo']))}</strong></span>
          <span>Usa liquidez IOL: <strong>{"Si" if sizing_bundle.get('usar_liquidez_iol') else "No"}</strong></span>
          <span>Aporte externo: <strong>{fmt_ars(sizing_bundle.get('aporte_externo_ars', 0.0))}</strong></span>
          <span>Porcentaje: <strong>{sizing_bundle['pct_fondeo']:.0%}</strong></span>
          <span>Monto: <strong>{fmt_ars(sizing_bundle['monto_fondeo_ars'])}</strong></span>
        </div>
        {build_table(
            asignacion_final[["Ticker_IOL", "Bucket_Prudencia", "Peso_Fondeo_%", "Monto_ARS", "Monto_USD"]]
            if not asignacion_final.empty else asignacion_final,
            formatters={
                "Peso_Fondeo_%": fmt_pct,
                "Monto_ARS": fmt_ars,
                "Monto_USD": fmt_usd,
            },
        )}
      </section>
    </section>

    <section class="panel" id="tecnico">
      <h2>Overlay tecnico</h2>
      <div class="meta">
        <span>Activo: <strong>{tech_enabled}</strong></span>
        <span>Cobertura: <strong>{tech_covered}/{tech_total}</strong></span>
      </div>
      {build_technical_table(technical_view)}
    </section>

    {bonistas_section}

    <section class="panel" id="decision">
      <div class="panel-head">
      <h2>Decision final</h2>
        <div class="filters">
          <input id="ticker-filter" type="search" placeholder="Filtrar ticker">
          <select id="action-filter">
            <option value="">Todas las acciones</option>
            <option value="Refuerzo">Refuerzo</option>
            <option value="Reducir">Reducir</option>
            <option value="Desplegar liquidez">Desplegar liquidez</option>
            <option value="Mantener / Neutral">Mantener / Neutral</option>
          </select>
        </div>
      </div>
      {build_decision_table(decision_view, action_col=action_col, motive_col=motive_col)}
    </section>

    <section class="panel" id="cartera">
      <h2>Cartera maestra</h2>
      {build_table(
          df_total[["Ticker_IOL", "Tipo", "Bloque", "Valorizado_ARS", "Valor_USD", "Ganancia_ARS", "Peso_%"]]
          .sort_values("Valorizado_ARS", ascending=False),
          formatters={
              "Valorizado_ARS": fmt_ars,
              "Valor_USD": fmt_usd,
              "Ganancia_ARS": fmt_ars,
              "Peso_%": fmt_pct,
          },
      )}
    </section>
  </main>
  <script>
    const tickerInput = document.getElementById('ticker-filter');
    const actionSelect = document.getElementById('action-filter');
    const rows = Array.from(document.querySelectorAll('#decision-table tbody tr'));

    function applyDecisionFilter() {{
      const tickerNeedle = (tickerInput?.value || '').toLowerCase().trim();
      const actionNeedle = actionSelect?.value || '';
      rows.forEach((row) => {{
        const ticker = (row.dataset.ticker || '').toLowerCase();
        const action = row.dataset.action || '';
        const matchesTicker = !tickerNeedle || ticker.includes(tickerNeedle);
        const matchesAction = !actionNeedle || action === actionNeedle;
        row.style.display = matchesTicker && matchesAction ? '' : 'none';
      }});
    }}

    tickerInput?.addEventListener('input', applyDecisionFilter);
    actionSelect?.addEventListener('change', applyDecisionFilter);
  </script>
</body>
</html>
"""

    return html_body


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    result = run_smoke_pipeline()
    html_body = render_report(result)
    HTML_PATH.write_text(html_body, encoding="utf-8")
    print(f"Reporte generado en: {HTML_PATH}")


if __name__ == "__main__":
    main()
