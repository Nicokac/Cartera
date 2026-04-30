from __future__ import annotations

import html
import pandas as pd

from report_primitives import (
    build_collapsible,
    build_focus_list,
    build_table,
    ensure_table_columns,
    esc_text,
    fmt_ars,
    fmt_pct,
    fmt_score,
    fmt_usd,
    safe_int,
)

from report_sections_risk import _build_risk_focus_block, build_score_distribution


_BOND_LABELS = {
    "bond_sov_ar": "Soberano AR",
    "bond_other": "Otros",
    "bond_bopreal": "Bopreal",
    "bond_cer": "CER",
    "bond_hard_dollar": "Hard Dollar",
}


def _bond_label(value: object) -> str:
    key = str(value or "").strip()
    return _BOND_LABELS.get(key, key or "-")


# ── Allocation bar ─────────────────────────────────────────────────────────────

_TIPO_COLOR: dict[str, str] = {
    "cedear": "#0f6c5c",
    "liquidez": "#b07e0f",
    "bono": "#5b6ead",
    "accion-local": "#22895c",
}
_TIPO_COLOR_FALLBACKS = ["#8a9ba8", "#6c7a89", "#4e5f70", "#3d5166"]


def _tipo_slug(tipo: str) -> str:
    s = tipo.lower().strip()
    for src, dst in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n"),(" ","-")]:
        s = s.replace(src, dst)
    return "".join(c for c in s if c.isalnum() or c == "-")


def build_allocation_bar(resumen_tipos: pd.DataFrame) -> str:
    if not isinstance(resumen_tipos, pd.DataFrame) or resumen_tipos.empty:
        return ""
    if "Peso_%" not in resumen_tipos.columns or "Tipo" not in resumen_tipos.columns:
        return ""

    work = resumen_tipos[["Tipo", "Peso_%"]].dropna(subset=["Peso_%"]).copy()
    total = float(work["Peso_%"].sum())
    if total <= 0:
        return ""

    work = work.sort_values("Peso_%", ascending=False)
    used: dict[str, str] = {}
    fallback_idx = 0
    segments: list[str] = []
    legend: list[str] = []

    for _, row in work.iterrows():
        tipo = str(row["Tipo"])
        slug = _tipo_slug(tipo)
        peso = float(row["Peso_%"])
        if slug not in used:
            color = _TIPO_COLOR.get(slug, _TIPO_COLOR_FALLBACKS[fallback_idx % len(_TIPO_COLOR_FALLBACKS)])
            if slug not in _TIPO_COLOR:
                fallback_idx += 1
            used[slug] = color
        color = used[slug]
        pct = peso / total * 100
        segments.append(
            f'<div class="alloc-seg" style="width:{pct:.2f}%;background:{color}" '
            f'title="{html.escape(tipo)} {html.escape(fmt_pct(peso))}"></div>'
        )
        legend.append(
            f'<span class="alloc-legend-item">'
            f'<span class="alloc-dot" style="background:{color}"></span>'
            f'{html.escape(tipo)} <strong>{html.escape(fmt_pct(peso))}</strong>'
            f'</span>'
        )

    return (
        '<div class="alloc-bar-wrap">'
        f'<div class="alloc-bar">{"".join(segments)}</div>'
        f'<div class="alloc-legend">{"".join(legend)}</div>'
        '</div>'
    )


# ── Technical summary ──────────────────────────────────────────────────────────

def build_technical_summary(technical_view: pd.DataFrame) -> str:
    if technical_view.empty:
        return '<div class="empty compact-empty">Sin resumen técnico disponible.</div>'

    work = technical_view.copy()

    def _items(source: pd.DataFrame, *, title_fn, extra_class: str = "") -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for _, row in source.head(3).iterrows():
            items.append(
                {
                    "kicker": str(row.get("Ticker_IOL", "-")),
                    "title": title_fn(row),
                    "detail": f"Tendencia {row.get('Tech_Trend', '-')}",
                    "extra_class": extra_class,
                }
            )
        return items

    momentum_col = "Momentum_20d_%"
    high52_col = "Dist_52w_High_%"
    sma200_col = "Dist_SMA200_%"

    fuertes = work.sort_values(momentum_col, ascending=False) if momentum_col in work.columns else work
    debiles = work.sort_values(momentum_col, ascending=True) if momentum_col in work.columns else work
    cerca_max = work.sort_values(high52_col, ascending=False) if high52_col in work.columns else pd.DataFrame()
    bajo_sma = work[work[sma200_col].notna()].sort_values(sma200_col, ascending=True) if sma200_col in work.columns else pd.DataFrame()

    if not cerca_max.empty and high52_col in cerca_max.columns:
        cerca_max = cerca_max[cerca_max[high52_col] >= -10]
    if not bajo_sma.empty and sma200_col in bajo_sma.columns:
        bajo_sma = bajo_sma[bajo_sma[sma200_col] < 0]

    technical_detail = f"""
    <div class="focus-columns focus-columns-wide">
      <div>
        <h3>Cerca de máximos 52w</h3>
        {build_focus_list(_items(cerca_max, title_fn=lambda row: 'En máximos 52w' if abs(float(row.get(high52_col) or 0)) < 0.5 else f"{fmt_pct(row.get(high52_col))} vs máximo anual"), empty_message='Sin nombres cerca de máximos anuales.', tone='neutral')}
      </div>
      <div>
        <h3>Por debajo de SMA200</h3>
        {build_focus_list(_items(bajo_sma, title_fn=lambda row: f"{fmt_pct(row.get(sma200_col))} vs SMA200"), empty_message='Sin nombres relevantes por debajo de SMA200.', tone='neutral')}
      </div>
    </div>
    """

    return f"""
    <div class="focus-columns focus-columns-wide">
      <div>
        <h3>Más fuertes</h3>
        {build_focus_list(_items(fuertes, title_fn=lambda row: f"{fmt_pct(row.get(momentum_col))} en 20d", extra_class='tech-up'), empty_message='Sin datos de fortaleza.', tone='buy')}
      </div>
      <div>
        <h3>Más débiles</h3>
        {build_focus_list(_items(debiles, title_fn=lambda row: f"{fmt_pct(row.get(momentum_col))} en 20d", extra_class='tech-down'), empty_message='Sin datos de debilidad.', tone='sell')}
      </div>
    </div>
    {build_collapsible('Ver detalle técnico adicional', technical_detail, compact=True)}
    """


# ── Bond summary ───────────────────────────────────────────────────────────────

def build_bond_summary(
    bond_subfamily_summary: pd.DataFrame,
    bond_local_subfamily_summary: pd.DataFrame,
    bonistas_macro: dict[str, object],
) -> str:
    macro_cards = f"""
    <section class="cards cards-secondary bond-macro-cards">
      <article class="card compact"><span class="label">CER diario</span><strong>{esc_text(bonistas_macro.get('cer_diario'))}</strong></article>
      <article class="card compact"><span class="label">Inflación REM</span><strong>{esc_text(bonistas_macro.get('rem_inflacion_mensual_pct'))} | 12m {esc_text(bonistas_macro.get('rem_inflacion_12m_pct'))}</strong></article>
      <article class="card compact"><span class="label">Tasas locales</span><strong>TAMAR {esc_text(bonistas_macro.get('tamar'))} | BADLAR {esc_text(bonistas_macro.get('badlar'))}</strong></article>
      <article class="card compact"><span class="label">Tipo de cambio / RP</span><strong>A3500 {esc_text(bonistas_macro.get('a3500_mayorista'))} | RP {esc_text(bonistas_macro.get('riesgo_pais_bps'))}</strong></article>
      <article class="card compact"><span class="label">Reservas BCRA</span><strong>{esc_text(bonistas_macro.get('reservas_bcra_musd'))}</strong></article>
      <article class="card compact"><span class="label">Curva UST</span><strong>5y {esc_text(bonistas_macro.get('ust_5y_pct'))} | 10y {esc_text(bonistas_macro.get('ust_10y_pct'))}</strong></article>
    </section>
    """

    macro_items = [
        {
            "kicker": "Macro local",
            "title": f"Riesgo país {esc_text(bonistas_macro.get('riesgo_pais_bps'))} | A3500 {esc_text(bonistas_macro.get('a3500_mayorista'))}",
            "detail": f"CER {esc_text(bonistas_macro.get('cer_diario'))} | REM mensual {esc_text(bonistas_macro.get('rem_inflacion_mensual_pct'))}",
        },
        {
            "kicker": "Curva UST",
            "title": f"UST 5y {esc_text(bonistas_macro.get('ust_5y_pct'))} | UST 10y {esc_text(bonistas_macro.get('ust_10y_pct'))}",
            "detail": f"Reservas BCRA {esc_text(bonistas_macro.get('reservas_bcra_musd'))}",
        },
    ]

    subfamily_items: list[dict[str, str]] = []
    if isinstance(bond_subfamily_summary, pd.DataFrame) and not bond_subfamily_summary.empty:
        for _, row in bond_subfamily_summary.head(3).iterrows():
            subfamily_items.append(
                {
                    "kicker": _bond_label(row.get("asset_subfamily", "-")),
                    "title": f"{int(row.get('Instrumentos', 0) or 0)} instrumentos | TIR {row.get('TIR_Promedio', '-')}",
                    "detail": f"Paridad {row.get('Paridad_Promedio', '-')} | MD {row.get('MD_Promedio', '-')}",
                }
            )

    local_items: list[dict[str, str]] = []
    if isinstance(bond_local_subfamily_summary, pd.DataFrame) and not bond_local_subfamily_summary.empty:
        for _, row in bond_local_subfamily_summary.head(3).iterrows():
            local_items.append(
                {
                    "kicker": _bond_label(row.get("bonistas_local_subfamily", "-")),
                    "title": f"{int(row.get('Instrumentos', 0) or 0)} instrumentos | TIR {row.get('TIR_Promedio', '-')}",
                    "detail": f"Paridad {row.get('Paridad_Promedio', '-')} | MD {row.get('MD_Promedio', '-')}",
                }
            )

    return f"""
    {macro_cards}
    <div class="focus-columns focus-columns-wide">
      <div>
        <h3>Contexto macro</h3>
        {build_focus_list(macro_items, empty_message='Sin contexto macro disponible.', tone='neutral')}
      </div>
      <div>
        <h3>Subfamilias</h3>
        {build_focus_list(subfamily_items, empty_message='Sin resumen por subfamilia.', tone='neutral')}
      </div>
      <div>
        <h3>Taxonomía local</h3>
        {build_focus_list(local_items, empty_message='Sin resumen por taxonomía local.', tone='neutral')}
      </div>
    </div>
    """


# ── Summary section ────────────────────────────────────────────────────────────

def build_summary_section(
    *,
    kpis: dict[str, object],
    resumen_tipos: pd.DataFrame,
    family_summary: pd.DataFrame,
    finviz_fund_covered: int,
    finviz_total: int,
    finviz_ratings_covered: int,
    decision_view: pd.DataFrame | None = None,
    action_col: str = "",
    risk_bundle: dict[str, object] | None = None,
) -> str:
    score_dist_html = (
        build_score_distribution(decision_view, action_col)
        if isinstance(decision_view, pd.DataFrame) and action_col
        else ""
    )
    risk_bundle = risk_bundle or {}
    portfolio_summary = risk_bundle.get("portfolio_summary", {}) or {}
    position_risk = risk_bundle.get("position_risk", pd.DataFrame())

    summary_kpis = f"""
      <section class="cards cards-secondary summary-kpis">
        <article class="card compact"><span class="label">Total consolidado</span><strong>{fmt_ars(kpis['total_ars'])}</strong></article>
        <article class="card compact"><span class="label">Total estilo IOL</span><strong>{fmt_ars(kpis['total_ars_iol'])}</strong></article>
        <article class="card compact"><span class="label">Liquidez broker</span><strong>{fmt_ars(kpis.get('liquidez_broker_ars', kpis['liquidez_ars']))}</strong></article>
        <article class="card compact"><span class="label">Liquidez ampliada</span><strong>{fmt_ars(kpis['liquidez_ars'])}</strong></article>
        <article class="card compact"><span class="label">Liquidez USD convertida</span><strong>{fmt_ars(kpis['liquidez_usd_ars'])}</strong></article>
        <article class="card compact"><span class="label">Finviz fundamentals</span><strong>{finviz_fund_covered}/{finviz_total}</strong></article>
        <article class="card compact"><span class="label">Finviz ratings</span><strong>{finviz_ratings_covered}/{finviz_total}</strong></article>
      </section>
    """

    family_summary_view = family_summary.copy() if isinstance(family_summary, pd.DataFrame) else pd.DataFrame()
    if not family_summary_view.empty:
        family_labels = {
            "bond": "Bono",
            "etf": "ETF",
            "fund": "FCI",
            "liquidity": "Liquidez",
            "stock": "Acción",
        }
        subfamily_labels = {
            "bond_bopreal": "Bopreal",
            "bond_cer": "CER",
            "bond_other": "Otros",
            "bond_sov_ar": "Soberano AR",
            "etf_core": "Core",
            "etf_country_region": "País / Región",
            "etf_sector": "Sectorial",
            "fund_other": "Otros",
            "liquidity_other": "Liquidez",
            "stock_argentina": "Argentina",
            "stock_commodity": "Commodities",
            "stock_defensive_dividend": "Defensivo / Dividendos",
            "stock_growth": "Growth",
        }
        if 'asset_family' in family_summary_view.columns:
            family_summary_view['asset_family'] = family_summary_view['asset_family'].map(lambda x: family_labels.get(str(x), str(x)))
        if 'asset_subfamily' in family_summary_view.columns:
            family_summary_view['asset_subfamily'] = family_summary_view['asset_subfamily'].map(lambda x: subfamily_labels.get(str(x), str(x)))
        family_summary_view = family_summary_view.rename(columns={
            'asset_family': 'Familia',
            'asset_subfamily': 'Subfamilia',
            'Instrumentos': 'Instrumentos',
            'Score_Promedio': 'Score promedio',
        })

    risk_html = ""
    if portfolio_summary and isinstance(position_risk, pd.DataFrame) and not position_risk.empty:
        history_rank = {"Robusta": 0, "Parcial": 1, "Corta": 2, "Sin historia": 3}
        position_risk = position_risk.copy()
        position_risk["_history_rank"] = (
            position_risk["Calidad_Historia"].map(history_rank).fillna(9)
            if "Calidad_Historia" in position_risk.columns
            else 9
        )
        position_risk = position_risk.sort_values(
            ["_history_rank", "Drawdown_Max_%", "Volatilidad_Diaria_%"],
            ascending=[True, True, False],
            na_position="last",
        ).drop(columns=["_history_rank"]).reset_index(drop=True)
        market_risk = position_risk.loc[position_risk["Tipo"].astype(str) != "Bono"].copy()
        bond_risk = position_risk.loc[position_risk["Tipo"].astype(str) == "Bono"].copy()
        stability_note = portfolio_summary.get("nota_estabilidad")
        benchmark_validation = portfolio_summary.get("benchmark_validation", {}) or {}
        benchmark_note = benchmark_validation.get("nota")

        risk_details = f"""
      {_build_risk_focus_block(market_risk, title='Riesgo de mercado', empty_message='Sin posiciones de mercado para analizar.')}
      {_build_risk_focus_block(bond_risk, title='Riesgo de renta fija', empty_message='Sin bonos para analizar.')}
      <div class="panel-head">
        <h3>Tabla de riesgo</h3>
        <div class="filters">
          <select id="risk-history-filter">
            <option value="">Toda la historia</option>
            <option value="Robusta">Solo robusta</option>
            <option value="Parcial">Solo parcial</option>
            <option value="Corta">Solo corta</option>
          </select>
          <select id="risk-history-type-filter">
            <option value="">Todos los tipos</option>
            <option value="CEDEAR">Solo CEDEAR</option>
            <option value="Bono">Solo Bono</option>
            <option value="Acción Local">Solo Acción Local</option>
          </select>
        </div>
      </div>
      {build_table(
          position_risk[["Ticker_IOL", "Tipo", "Bloque", "Peso_%", "Base_Riesgo", "Calidad_Historia", "Retorno_Acum_%", "Volatilidad_Diaria_%", "Drawdown_Max_%", "Observaciones"]].rename(columns={"Ticker_IOL": "Ticker", "Peso_%": "Peso %", "Base_Riesgo": "Base de riesgo", "Calidad_Historia": "Calidad de historia", "Retorno_Acum_%": "Retorno acum.", "Volatilidad_Diaria_%": "Volatilidad diaria", "Drawdown_Max_%": "Drawdown máx."}),
          formatters={
              "Peso %": fmt_pct,
              "Retorno acum.": fmt_pct,
              "Volatilidad diaria": fmt_pct,
              "Drawdown máx.": fmt_pct,
          },
          table_class="risk-history-table",
          table_id="risk-history-table",
      )}
        """

        risk_html = f"""
      <h3>Riesgo histórico</h3>
      <div class="meta">
        <span>Ventana: <strong>{esc_text(portfolio_summary.get('desde'))} → {esc_text(portfolio_summary.get('hasta'))}</strong></span>
        <span>Snapshots: <strong>{safe_int(portfolio_summary.get('snapshots'))}</strong></span>
        <span>Retorno cartera: <strong>{fmt_pct(portfolio_summary.get('retorno_acum_pct'))}</strong></span>
        <span>Vol diaria cartera: <strong>{fmt_pct(portfolio_summary.get('volatilidad_diaria_pct'))}</strong></span>
        <span>Max drawdown cartera: <strong>{fmt_pct(portfolio_summary.get('drawdown_max_pct'))}</strong></span>
      </div>
      <div class="meta">
        <span>Metodó: <strong>Universo comparable</strong></span>
        <span>Pasos estables: <strong>{safe_int(portfolio_summary.get('pasos_estables'))}/{safe_int(portfolio_summary.get('pasos_totales'))}</strong></span>
        <span>Cobertura previa prom.: <strong>{fmt_pct(portfolio_summary.get('coverage_prev_promedio_pct'))}</strong></span>
        <span>Cobertura actual prom.: <strong>{fmt_pct(portfolio_summary.get('coverage_curr_promedio_pct'))}</strong></span>
      </div>
      {f'''
      <div class="meta">
        <span>Benchmark: <strong>{esc_text(benchmark_validation.get("benchmark"))}</strong></span>
        <span>Estado validacion: <strong>{esc_text(benchmark_validation.get("status"))}</strong></span>
        <span>Obs benchmark: <strong>{safe_int(benchmark_validation.get("observaciones"))}</strong></span>
        <span>Correlacion: <strong>{fmt_score(benchmark_validation.get("correlacion"))}</strong></span>
        <span>Tracking error diario: <strong>{fmt_pct(benchmark_validation.get("tracking_error_pct"))}</strong></span>
      </div>
      ''' if benchmark_validation else ''}
      {f'<div class="meta"><span>{esc_text(stability_note)}</span></div>' if stability_note else ''}
      {f'<div class="meta"><span>{esc_text(benchmark_note)}</span></div>' if benchmark_note else ''}
      {build_collapsible(
          "Ver diagnóstico completo de riesgo",
          risk_details,
          compact=True,
      )}
        """
    return f"""
    <section class="panel" id="resumen">
      <h2>Resumen por tipo</h2>
      {summary_kpis}
      {score_dist_html}
      {build_allocation_bar(resumen_tipos)}
      {build_table(
          resumen_tipos[["Tipo", "Instrumentos", "Valorizado_ARS", "Valor_USD", "Ganancia_ARS", "Peso_%"]].rename(columns={"Valorizado_ARS": "Valorizado ARS", "Valor_USD": "Valor USD", "Ganancia_ARS": "Ganancia ARS", "Peso_%": "Peso %"}),
          formatters={
              "Valorizado ARS": fmt_ars,
              "Valor USD": fmt_usd,
              "Ganancia ARS": fmt_ars,
              "Peso %": fmt_pct,
          },
      )}
      {build_collapsible(
          "Ver taxonomía operativa",
          build_table(
              family_summary_view[["Familia", "Subfamilia", "Instrumentos", "Score promedio"]]
              if not family_summary_view.empty else family_summary_view,
              formatters={"Score promedio": fmt_score},
          ),
          compact=True,
      )}
      {risk_html}
    </section>
    """


# ── Drift chart ────────────────────────────────────────────────────────────────

def build_drift_chart(
    asignacion_final: pd.DataFrame,
    df_total: pd.DataFrame,
    total_ars: float,
) -> str:
    if not isinstance(asignacion_final, pd.DataFrame) or asignacion_final.empty:
        return ""
    if total_ars <= 0:
        return ""

    current_weights: dict[str, float] = {}
    if isinstance(df_total, pd.DataFrame) and not df_total.empty:
        for _, row in df_total.iterrows():
            ticker = str(row.get("Ticker_IOL", ""))
            peso = float(row.get("Peso_%", 0) or 0)
            if ticker:
                current_weights[ticker] = peso

    drift_data: list[tuple[str, float, float]] = []
    max_projected = 0.0
    for _, row in asignacion_final.iterrows():
        ticker = str(row.get("Ticker_IOL", ""))
        if not ticker:
            continue
        monto_ars = float(row.get("Monto_ARS", 0) or 0)
        incremental = monto_ars / total_ars * 100.0
        current = current_weights.get(ticker, 0.0)
        projected = current + incremental
        max_projected = max(max_projected, projected)
        drift_data.append((ticker, current, incremental))

    if not drift_data or max_projected <= 0:
        return ""

    rows_html: list[str] = []
    for ticker, current, incremental in drift_data:
        projected = current + incremental
        w_cur = current / max_projected * 100
        w_inc = incremental / max_projected * 100
        rows_html.append(
            f'<div class="drift-row">'
            f'<span class="drift-ticker">{html.escape(ticker)}</span>'
            f'<div class="drift-bar-track">'
            f'<div class="drift-seg drift-current" style="width:{w_cur:.1f}%"></div>'
            f'<div class="drift-seg drift-incr" style="width:{w_inc:.1f}%"></div>'
            f'</div>'
            f'<span class="drift-label">{current:.2f}% → {projected:.2f}%</span>'
            f'</div>'
        )

    legend = (
        '<div class="drift-legend">'
        '<span><span class="drift-dot drift-current-dot"></span>Peso actual</span>'
        '<span><span class="drift-dot drift-incr-dot"></span>Incremento fondeo</span>'
        '</div>'
    )
    return f'<div class="drift-chart">{legend}{"".join(rows_html)}</div>'


# ── Sizing section ─────────────────────────────────────────────────────────────

def build_sizing_section(
    sizing_bundle: dict[str, object],
    asignacion_final: pd.DataFrame,
    *,
    df_total: pd.DataFrame | None = None,
    total_ars: float = 0.0,
) -> str:
    return f"""
    <section class="panel" id="sizing">
      <div class="panel-head">
        <h2>Sizing</h2>
        <button id="copy-sizing" class="copy-btn" title="Copiar tabla como TSV para pegar en Excel">Copiar tabla</button>
      </div>
      <div class="meta">
        <span>Fuente de fondeo: <strong>{esc_text(sizing_bundle['fuente_fondeo'])}</strong></span>
        <span>Usa liquidez IOL: <strong>{"Si" if sizing_bundle.get('usar_liquidez_iol') else "No"}</strong></span>
        <span>Aporte externo: <strong>{fmt_ars(sizing_bundle.get('aporte_externo_ars', 0.0))}</strong></span>
        <span>Porcentaje: <strong>{sizing_bundle['pct_fondeo']:.0%}</strong></span>
        <span>Monto: <strong>{fmt_ars(sizing_bundle['monto_fondeo_ars'])}</strong></span>
      </div>
      {build_table(
          ensure_table_columns(
              asignacion_final,
              ["Ticker_IOL", "Bucket_Prudencia", "Peso_Fondeo_%", "Monto_ARS", "Monto_USD"],
          ).rename(columns={"Ticker_IOL": "Ticker", "Bucket_Prudencia": "Bucket de prudencia", "Peso_Fondeo_%": "Peso del fondeo", "Monto_ARS": "Monto ARS", "Monto_USD": "Monto USD"}),
          formatters={
              "Peso del fondeo": fmt_pct,
              "Monto ARS": fmt_ars,
              "Monto USD": fmt_usd,
          },
          table_class="sizing-table",
          table_id="sizing-table",
      )}
      {build_collapsible(
          "Ver drift de cartera",
          build_drift_chart(asignacion_final, df_total if df_total is not None else pd.DataFrame(), total_ars),
          compact=True,
      )}
    </section>
    """


# ── Bonistas section ───────────────────────────────────────────────────────────

def build_bonistas_section(
    *,
    show_bonistas: bool,
    bond_monitor: pd.DataFrame,
    bond_subfamily_summary: pd.DataFrame,
    bond_local_subfamily_summary: pd.DataFrame,
    bonistas_macro: dict[str, object],
    ust_note: str,
) -> str:
    if not show_bonistas:
        return ""

    bond_subfamily_view = bond_subfamily_summary.copy() if isinstance(bond_subfamily_summary, pd.DataFrame) else pd.DataFrame()
    if not bond_subfamily_view.empty and "asset_subfamily" in bond_subfamily_view.columns:
        bond_subfamily_view["asset_subfamily"] = bond_subfamily_view["asset_subfamily"].map(_bond_label)
        bond_subfamily_view = bond_subfamily_view.rename(
            columns={
                "asset_subfamily": "Subfamilia",
                "TIR_Promedio": "TIR promedio",
                "Paridad_Promedio": "Paridad promedio",
                "MD_Promedio": "MD promedio",
                "Dias_al_Vto_Promedio": "Días al vto. promedio",
            }
        )

    bond_local_subfamily_view = bond_local_subfamily_summary.copy() if isinstance(bond_local_subfamily_summary, pd.DataFrame) else pd.DataFrame()
    if not bond_local_subfamily_view.empty and "bonistas_local_subfamily" in bond_local_subfamily_view.columns:
        bond_local_subfamily_view["bonistas_local_subfamily"] = bond_local_subfamily_view["bonistas_local_subfamily"].map(_bond_label)
        bond_local_subfamily_view = bond_local_subfamily_view.rename(
            columns={
                "bonistas_local_subfamily": "Taxonomía local",
                "TIR_Promedio": "TIR promedio",
                "Paridad_Promedio": "Paridad promedio",
                "MD_Promedio": "MD promedio",
            }
        )

    bond_monitor_view = bond_monitor.copy() if isinstance(bond_monitor, pd.DataFrame) else pd.DataFrame()
    if not bond_monitor_view.empty:
        for col in ["asset_subfamily", "bonistas_local_subfamily"]:
            if col in bond_monitor_view.columns:
                bond_monitor_view[col] = bond_monitor_view[col].map(_bond_label)
        if "bonistas_put_flag" in bond_monitor_view.columns:
            bond_monitor_view["bonistas_put_flag"] = bond_monitor_view["bonistas_put_flag"].map(
                lambda x: "Sí" if bool(x) else "No"
            )
        for col in ["bonistas_liquidity_bucket", "bonistas_duration_bucket"]:
            if col in bond_monitor_view.columns:
                bond_monitor_view[col] = bond_monitor_view[col].map(
                    lambda x: "-" if pd.isna(x) else str(x).strip().capitalize()
                )
        bond_monitor_view = bond_monitor_view.rename(
            columns={
                "Ticker_IOL": "Ticker",
                "asset_subfamily": "Subfamilia",
                "bonistas_local_subfamily": "Taxonomía local",
                "Peso_%": "Peso %",
                "bonistas_tir_pct": "TIR",
                "bonistas_paridad_pct": "Paridad",
                "bonistas_md": "MD",
                "bonistas_volume_last": "Volumen último",
                "bonistas_volume_avg_20d": "Volumen prom. 20d",
                "bonistas_volume_ratio": "Ratio volumen",
                "bonistas_liquidity_bucket": "Liquidez",
                "bonistas_duration_bucket": "Duración",
                "bonistas_days_to_maturity": "Días al vto.",
                "bonistas_tir_vs_avg_365d_pct": "TIR vs prom. 365d",
                "bonistas_parity_gap_pct": "Gap de paridad",
                "bonistas_put_flag": "PUT",
            }
        )

    bond_summary_tables = (
        build_collapsible("Ver resumen por subfamilia", build_table(bond_subfamily_view, formatters={}), compact=True)
        + build_collapsible("Ver resumen por taxonomía local", build_table(bond_local_subfamily_view, formatters={}), compact=True)
        + build_collapsible(
            "Ver monitoreo completo de bonos",
            build_table(
                bond_monitor_view,
                formatters={
                    "Peso %": fmt_pct,
                    "TIR": fmt_pct,
                    "Paridad": fmt_pct,
                    "MD": lambda x: "-" if pd.isna(x) else f"{float(x):.2f}",
                    "Volumen último": lambda x: "-" if pd.isna(x) else f"{float(x):,.0f}",
                    "Volumen prom. 20d": lambda x: "-" if pd.isna(x) else f"{float(x):,.0f}",
                    "Ratio volumen": lambda x: "-" if pd.isna(x) else f"{float(x):.2f}x",
                    "TIR vs prom. 365d": fmt_pct,
                    "Gap de paridad": fmt_pct,
                },
            ),
            compact=True,
        )
    )
    return f"""
    <section class="panel" id="bonistas">
      <h2>Bonos Locales</h2>
      {build_bond_summary(bond_subfamily_summary, bond_local_subfamily_summary, bonistas_macro)}
      {f'<div class="meta"><span>{ust_note}</span></div>' if ust_note else ''}
      {bond_summary_tables}
    </section>
    """
