from __future__ import annotations

import html
from pathlib import Path

import pandas as pd

from decision.action_constants import (
    ACTION_DESPLEGAR_LIQUIDEZ,
    ACTION_MANTENER_NEUTRAL,
    ACTION_REDUCIR,
    ACTION_REFUERZO,
    NEUTRAL_ACTIONS,
)


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"


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


def fmt_delta_score(value: object) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value):+.3f}"


def fmt_label(value: object) -> str:
    if pd.isna(value) or value in {None, ""}:
        return "-"
    return str(value)


def fmt_count_label(value: object, singular: str, plural: str | None = None) -> str:
    try:
        count = int(value or 0)
    except Exception:
        count = 0
    plural = plural or f"{singular}s"
    return f"{count} {singular if count == 1 else plural}"


def esc_text(value: object) -> str:
    return html.escape(fmt_label(value))


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

    if column == "score_delta_vs_dia_anterior":
        if num >= 0.03:
            return "metric metric-positive"
        if num <= -0.03:
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

    if column in {
        "Momentum_20d_%",
        "Momentum_60d_%",
        "Dist_SMA20_%",
        "Dist_SMA50_%",
        "Dist_SMA200_%",
        "Dist_EMA20_%",
        "Dist_EMA50_%",
        "Dist_52w_High_%",
        "Dist_52w_Low_%",
    }:
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


def ensure_table_columns(df: pd.DataFrame | None, columns: list[str]) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=columns)
    return df.reindex(columns=columns)


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
        "Dist_SMA200_%": fmt_pct,
        "Dist_EMA20_%": fmt_pct,
        "Dist_EMA50_%": fmt_pct,
        "Dist_52w_High_%": fmt_pct,
        "Dist_52w_Low_%": fmt_pct,
        "Vol_20d_Anual_%": fmt_pct,
        "Avg_Volume_20d": lambda x: "-" if pd.isna(x) else f"{float(x):,.0f}",
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
                "Dist_SMA200_%",
                "Dist_EMA20_%",
                "Dist_EMA50_%",
                "Dist_52w_High_%",
                "Dist_52w_Low_%",
                "Vol_20d_Anual_%",
                "Avg_Volume_20d",
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
    if action_text == ACTION_REFUERZO.lower():
        return "badge badge-buy"
    if action_text == ACTION_REDUCIR.lower():
        return "badge badge-sell"
    if action_text == ACTION_DESPLEGAR_LIQUIDEZ.lower():
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
        ticker = esc_text(row["Ticker_IOL"])
        tipo = esc_text(row["Tipo"])
        accion = str(row.get(action_col, ""))
        motivo = esc_text(row.get(motive_col, ""))
        motivo_score = esc_text(row.get("motivo_score", ""))
        accion_previa = row.get("accion_previa")
        delta_score = row.get("score_delta_vs_dia_anterior")
        racha_refuerzo = int(row.get("dias_consecutivos_refuerzo", 0) or 0)
        racha_reduccion = int(row.get("dias_consecutivos_reduccion", 0) or 0)
        racha_mantener = int(row.get("dias_consecutivos_mantener", 0) or 0)
        racha = max(racha_refuerzo, racha_reduccion, racha_mantener)
        if racha <= 0 and accion.strip():
            racha = 1
        driver_html = build_driver_chips(row)
        score_detail = ""
        if motivo_score not in {"", "-"}:
            score_detail = (
                '<details class="inline-detail">'
                "<summary>Ver criterio de score</summary>"
                f"<div class=\"muted-inline\">{motivo_score}</div>"
                "</details>"
            )
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
            f"<td>{esc_text(accion_previa)}</td>"
            f"<td>{render_metric('score_delta_vs_dia_anterior', delta_score, fmt_delta_score)}</td>"
            f"<td>{html.escape('-' if racha <= 0 else str(racha))}</td>"
            f"<td><div class=\"driver-stack\">{driver_html}</div></td>"
            f"<td><div>{motivo}</div>{score_detail}</td>"
            "</tr>"
        )

    return (
        '<div class="table-wrap"><table id="decision-table">'
        "<thead><tr><th>Ticker</th><th>Tipo</th><th>Familia</th><th>Subfamilia</th><th>Peso_%</th><th>Score</th><th>Accion</th><th>Accion previa</th><th>Δ Score</th><th>Racha</th><th>Drivers</th><th>Motivo</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def build_focus_list(
    items: list[dict[str, str]],
    *,
    empty_message: str,
    tone: str = "neutral",
) -> str:
    if not items:
        return f'<div class="empty compact-empty">{html.escape(empty_message)}</div>'

    rows = []
    for item in items:
        kicker = html.escape(item.get("kicker", "-"))
        title = html.escape(item.get("title", ""))
        detail = html.escape(item.get("detail", ""))
        badge = item.get("badge")
        badge_html = f'<span class="{badge_class(badge)}">{html.escape(str(badge))}</span>' if badge else ""
        rows.append(
            '<article class="focus-item">'
            f'<div class="focus-top"><strong>{kicker}</strong>{badge_html}</div>'
            f'<div class="focus-title">{title}</div>'
            f'<div class="focus-detail">{detail}</div>'
            "</article>"
        )
    return f'<div class="focus-list tone-{tone}">{"".join(rows)}</div>'


def build_decision_priority_board(
    df: pd.DataFrame,
    *,
    action_col: str,
    motive_col: str,
) -> str:
    if df.empty:
        return '<div class="empty">Sin decisiones para priorizar.</div>'

    work = df.copy()
    work["_accion_actual"] = work[action_col].fillna("").astype(str)
    work["_accion_previa"] = work.get("accion_previa", pd.Series(index=work.index, dtype=object)).fillna("").astype(str)
    work["_cambio_accion"] = (
        (work["_accion_previa"].str.strip() != "")
        & (work["_accion_actual"].str.strip() != "")
        & (work["_accion_previa"] != work["_accion_actual"])
    )

    def _build_items(source: pd.DataFrame, *, ascending: bool = False, limit: int = 3, badge_from_action: bool = True) -> list[dict[str, str]]:
        if source.empty:
            return []
        ordered = source.sort_values("score_unificado", ascending=ascending).head(limit)
        items: list[dict[str, str]] = []
        for _, row in ordered.iterrows():
            racha = max(
                int(row.get("dias_consecutivos_refuerzo", 0) or 0),
                int(row.get("dias_consecutivos_reduccion", 0) or 0),
                int(row.get("dias_consecutivos_mantener", 0) or 0),
                1,
            )
            accion = str(row.get(action_col, ""))
            items.append(
                {
                    "kicker": str(row.get("Ticker_IOL", "-")),
                    "title": f"{fmt_score(row.get('score_unificado'))} | Racha {racha}",
                    "detail": str(row.get(motive_col, ""))[:160],
                    "badge": accion if badge_from_action else None,
                }
            )
        return items

    material_previous = {
        ACTION_REFUERZO,
        ACTION_REDUCIR,
        ACTION_MANTENER_NEUTRAL,
        "Mantener / monitorear",
    }
    material_current = {
        ACTION_REFUERZO,
        ACTION_REDUCIR,
        ACTION_MANTENER_NEUTRAL,
        "Mantener / monitorear",
    }

    nuevos = work[
        work["_cambio_accion"]
        & work["_accion_previa"].isin(material_previous)
        & work["_accion_actual"].isin(material_current)
        & ~(
            work["_accion_previa"].isin({ACTION_MANTENER_NEUTRAL, "Mantener / monitorear"})
            & work["_accion_actual"].isin({ACTION_MANTENER_NEUTRAL, "Mantener / monitorear"})
        )
    ]
    refuerzos = work[work["_accion_actual"] == ACTION_REFUERZO]
    reducciones = work[work["_accion_actual"] == ACTION_REDUCIR]
    nuevos_tickers = set(nuevos["Ticker_IOL"].astype(str).tolist())
    neutrales = work[
        work["_accion_actual"].isin(NEUTRAL_ACTIONS)
        & ~work["Ticker_IOL"].astype(str).isin(nuevos_tickers)
    ]

    return f"""
    <section class="decision-priority">
      <div class="focus-columns focus-columns-wide">
        <div>
          <h3>Cambios materiales</h3>
          {build_focus_list(_build_items(nuevos, ascending=False), empty_message='Sin cambios materiales respecto de la corrida previa.', tone='neutral')}
        </div>
        <div>
          <h3>Refuerzos activos</h3>
          {build_focus_list(_build_items(refuerzos, ascending=False), empty_message='Sin refuerzos activos.', tone='buy')}
        </div>
        <div>
          <h3>Reducciones activas</h3>
          {build_focus_list(_build_items(reducciones, ascending=True), empty_message='Sin reducciones activas.', tone='sell')}
        </div>
        <div>
          <h3>Neutrales relevantes</h3>
          {build_focus_list(_build_items(neutrales, ascending=False, badge_from_action=True), empty_message='Sin neutrales relevantes.', tone='neutral')}
        </div>
      </div>
    </section>
    """


def build_technical_summary(technical_view: pd.DataFrame) -> str:
    if technical_view.empty:
        return '<div class="empty compact-empty">Sin resumen tecnico disponible.</div>'

    work = technical_view.copy()

    def _items(source: pd.DataFrame, *, title_fn) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for _, row in source.head(3).iterrows():
            items.append(
                {
                    "kicker": str(row.get("Ticker_IOL", "-")),
                    "title": title_fn(row),
                    "detail": f"Tendencia {row.get('Tech_Trend', '-')}",
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

    return f"""
    <div class="focus-columns focus-columns-wide">
      <div>
        <h3>Mas fuertes</h3>
        {build_focus_list(_items(fuertes, title_fn=lambda row: f"{fmt_pct(row.get(momentum_col))} en 20d"), empty_message='Sin datos de fortaleza.', tone='buy')}
      </div>
      <div>
        <h3>Mas debiles</h3>
        {build_focus_list(_items(debiles, title_fn=lambda row: f"{fmt_pct(row.get(momentum_col))} en 20d"), empty_message='Sin datos de debilidad.', tone='sell')}
      </div>
      <div>
        <h3>Cerca de maximos 52w</h3>
        {build_focus_list(_items(cerca_max, title_fn=lambda row: f"{fmt_pct(row.get(high52_col))} vs maximo anual"), empty_message='Sin nombres cerca de maximos anuales.', tone='neutral')}
      </div>
      <div>
        <h3>Por debajo de SMA200</h3>
        {build_focus_list(_items(bajo_sma, title_fn=lambda row: f"{fmt_pct(row.get(sma200_col))} vs SMA200"), empty_message='Sin nombres relevantes por debajo de SMA200.', tone='neutral')}
      </div>
    </div>
    """


def build_bond_summary(
    bond_subfamily_summary: pd.DataFrame,
    bond_local_subfamily_summary: pd.DataFrame,
    bonistas_macro: dict[str, object],
) -> str:
    macro_items = [
        {
            "kicker": "Macro local",
            "title": f"Riesgo pais {esc_text(bonistas_macro.get('riesgo_pais_bps'))} | A3500 {esc_text(bonistas_macro.get('a3500_mayorista'))}",
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
                    "kicker": str(row.get("asset_subfamily", "-")),
                    "title": f"{int(row.get('Instrumentos', 0) or 0)} instrumentos | TIR {row.get('TIR_Promedio', '-')}",
                    "detail": f"Paridad {row.get('Paridad_Promedio', '-')} | MD {row.get('MD_Promedio', '-')}",
                }
            )

    local_items: list[dict[str, str]] = []
    if isinstance(bond_local_subfamily_summary, pd.DataFrame) and not bond_local_subfamily_summary.empty:
        for _, row in bond_local_subfamily_summary.head(3).iterrows():
            local_items.append(
                {
                    "kicker": str(row.get("bonistas_local_subfamily", "-")),
                    "title": f"{int(row.get('Instrumentos', 0) or 0)} instrumentos | TIR {row.get('TIR_Promedio', '-')}",
                    "detail": f"Paridad {row.get('Paridad_Promedio', '-')} | MD {row.get('MD_Promedio', '-')}",
                }
            )

    return f"""
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
        <h3>Taxonomia local</h3>
        {build_focus_list(local_items, empty_message='Sin resumen por taxonomia local.', tone='neutral')}
      </div>
    </div>
    """


def build_collapsible(
    title: str,
    content: str,
    *,
    open_by_default: bool = False,
    compact: bool = False,
) -> str:
    open_attr = " open" if open_by_default else ""
    compact_class = " compact-collapsible" if compact else ""
    return (
        f'<details class="collapsible{compact_class}"{open_attr}>'
        f'<summary>{html.escape(title)}</summary>'
        f'<div class="collapsible-body">{content}</div>'
        "</details>"
    )


def render_report(
    result: dict[str, object],
    *,
    title: str = "Smoke Run",
    headline: str = "Prueba visual del pipeline",
    lede: str = "Reporte generado desde <code>scripts/generate_smoke_report.py</code> sin depender del notebook.",
) -> str:
    mep_real = float(result["mep_real"])
    generated_at_label = result.get("generated_at_label")
    portfolio_bundle = result["portfolio_bundle"]
    dashboard_bundle = result["dashboard_bundle"]
    decision_bundle = result["decision_bundle"]
    sizing_bundle = result["sizing_bundle"]
    technical_overlay = result.get("technical_overlay", pd.DataFrame())
    finviz_stats = result.get("finviz_stats", {}) or {}
    bonistas_bundle = result.get("bonistas_bundle", {}) or {}
    decision_memory = decision_bundle.get("decision_memory", {}) or {}
    market_regime = decision_bundle.get("market_regime", {}) or {}

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
    ust_status = str(bonistas_macro.get("ust_status") or "").strip().lower()
    ust_note = ""
    if ust_status == "error":
        ust_note = "<span>UST source: <strong>FRED no disponible</strong></span>"
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

    if not propuesta.empty and "accion_operativa" in propuesta.columns:
        decision_view = propuesta
        action_col = "accion_operativa"
        motive_col = "comentario_operativo" if "comentario_operativo" in propuesta.columns else "motivo_accion"
    else:
        decision_view = final_decision
        action_col = "accion_sugerida_v2"
        motive_col = "motivo_accion"

    action_counts = decision_view[action_col].value_counts(dropna=False).to_dict()
    neutrales = sum(int(action_counts.get(action_name, 0)) for action_name in NEUTRAL_ACTIONS)

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

    changed_actions: list[dict[str, str]] = []
    buy_focus: list[dict[str, str]] = []
    sell_focus: list[dict[str, str]] = []
    if isinstance(decision_view, pd.DataFrame) and not decision_view.empty:
        changed_view = decision_view.copy()
        changed_view["_accion_actual"] = changed_view[action_col].fillna("").astype(str)
        changed_view["_accion_previa"] = changed_view.get("accion_previa", pd.Series(index=changed_view.index, dtype=object)).fillna("").astype(str)
        changed_view = changed_view[
            (changed_view["_accion_previa"].str.strip() != "")
            & (changed_view["_accion_actual"].str.strip() != "")
            & (changed_view["_accion_previa"] != changed_view["_accion_actual"])
        ]
        changed_view = changed_view[
            changed_view["_accion_previa"].isin(
                {ACTION_REFUERZO, ACTION_REDUCIR, ACTION_MANTENER_NEUTRAL, "Mantener / monitorear"}
            )
            & changed_view["_accion_actual"].isin(
                {ACTION_REFUERZO, ACTION_REDUCIR, ACTION_MANTENER_NEUTRAL, "Mantener / monitorear"}
            )
            & ~(
                changed_view["_accion_previa"].isin({ACTION_MANTENER_NEUTRAL, "Mantener / monitorear"})
                & changed_view["_accion_actual"].isin({ACTION_MANTENER_NEUTRAL, "Mantener / monitorear"})
            )
        ]
        for _, row in changed_view.head(6).iterrows():
            changed_actions.append(
                {
                    "kicker": str(row.get("Ticker_IOL", "-")),
                    "title": f"{row['_accion_previa']} -> {row['_accion_actual']}",
                    "detail": str(row.get(motive_col, ""))[:140],
                    "badge": str(row["_accion_actual"]),
                }
            )

        refuerzo_view = decision_view[decision_view[action_col].astype(str) == ACTION_REFUERZO].sort_values(
            "score_unificado", ascending=False
        )
        reducir_view = decision_view[decision_view[action_col].astype(str) == ACTION_REDUCIR].sort_values(
            "score_unificado", ascending=True
        )
        for _, row in refuerzo_view.head(3).iterrows():
            buy_focus.append(
                {
                    "kicker": str(row.get("Ticker_IOL", "-")),
                    "title": f"Score {fmt_score(row.get('score_unificado'))}",
                    "detail": str(row.get(motive_col, ""))[:140],
                    "badge": ACTION_REFUERZO,
                }
            )
        for _, row in reducir_view.head(3).iterrows():
            sell_focus.append(
                {
                    "kicker": str(row.get("Ticker_IOL", "-")),
                    "title": f"Score {fmt_score(row.get('score_unificado'))}",
                    "detail": str(row.get(motive_col, ""))[:140],
                    "badge": ACTION_REDUCIR,
                }
            )

    sizing_preview = ""
    if isinstance(asignacion_final, pd.DataFrame) and not asignacion_final.empty:
        sizing_items = []
        for _, row in asignacion_final.head(3).iterrows():
            sizing_items.append(
                {
                    "kicker": str(row.get("Ticker_IOL", "-")),
                    "title": f"{fmt_pct(row.get('Peso_Fondeo_%'))} del fondeo",
                    "detail": f"{fmt_ars(row.get('Monto_ARS'))} | {fmt_usd(row.get('Monto_USD'))}",
                }
            )
        sizing_preview = build_focus_list(
            sizing_items,
            empty_message="Sin sizing sugerido.",
            tone="fund",
        )
    else:
        sizing_preview = '<div class="empty compact-empty">Sin sizing sugerido.</div>'

    active_flags_label = ", ".join(str(flag) for flag in (market_regime.get("active_flags", []) or [])) if market_regime else "Ninguno"
    executive_summary = (
        f"{fmt_count_label(action_counts.get(ACTION_REFUERZO, 0), 'refuerzo')}, "
        f"{fmt_count_label(action_counts.get(ACTION_REDUCIR, 0), 'reduccion')}, "
        f"{fmt_count_label(decision_memory.get('senales_nuevas', 0), 'cambio material', 'cambios materiales')} y "
        f"sizing activo en {', '.join(asignacion_final['Ticker_IOL'].head(3).astype(str).tolist()) if isinstance(asignacion_final, pd.DataFrame) and not asignacion_final.empty else 'sin asignacion'}."
    )

    primary_cards = f"""
    <section class="cards cards-primary">
      <article class="card"><span class="label">Corrida</span><strong>{esc_text(generated_at_label)}</strong></article>
      <article class="card"><span class="label">Total ARS consolidado</span><strong>{fmt_ars(kpis['total_ars'])}</strong></article>
      <article class="card"><span class="label">Liquidez</span><strong>{fmt_ars(kpis['liquidez_ars'])}</strong></article>
      <article class="card"><span class="label">MEP</span><strong>{fmt_ars(mep_real)}</strong></article>
      <article class="card"><span class="label">Refuerzos</span><strong>{int(action_counts.get(ACTION_REFUERZO, 0))}</strong></article>
      <article class="card"><span class="label">Reducciones</span><strong>{int(action_counts.get(ACTION_REDUCIR, 0))}</strong></article>
    </section>
    """

    secondary_cards = f"""
    <section class="cards cards-secondary">
      <article class="card compact"><span class="label">Total ARS estilo IOL</span><strong>{fmt_ars(kpis['total_ars_iol'])}</strong></article>
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
    panorama_section = f"""
    <section class="grid spotlight-grid" id="panorama">
      <section class="panel spotlight">
        <h2>Panorama</h2>
        <p class="summary-lede">{esc_text(executive_summary)}</p>
        <div class="meta">
          <span>Regimen: <strong>{'Activo' if market_regime.get('any_active') else 'Sin activacion'}</strong></span>
          <span>Flags activos: <strong>{esc_text(active_flags_label)}</strong></span>
          <span>Overlay tecnico: <strong>{tech_enabled}</strong></span>
        </div>
        <div class="focus-columns">
          <div>
            <h3>Prioridades de refuerzo</h3>
            {build_focus_list(buy_focus, empty_message='Sin refuerzos activos.', tone='buy')}
          </div>
          <div>
            <h3>Prioridades de reduccion</h3>
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

    changes_section = f"""
    <section class="panel" id="cambios">
      <div class="panel-head">
        <h2>Cambios</h2>
      </div>
      {memory_summary}
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
              <div class="focus-top"><strong>Tecnico</strong></div>
              <div class="focus-title">{tech_covered}/{tech_total} con overlay</div>
              <div class="focus-detail">Cobertura tecnica efectiva para la lectura de tendencia y momentum.</div>
            </article>
          </div>
        </div>
      </div>
    </section>
    """
    regime_flags = market_regime.get("flags", {}) or {}
    regime_active_flags = market_regime.get("active_flags", []) or []
    regime_summary = ""
    if market_regime:
        regime_items = []
        for flag_name, is_active in regime_flags.items():
            regime_items.append(
                f"<span>{esc_text(flag_name)}: <strong>{'Activo' if is_active else 'Inactivo'}</strong></span>"
            )
        active_flags_label = ", ".join(str(flag) for flag in regime_active_flags) if regime_active_flags else "Ninguno"
        regime_state = "Activo" if market_regime.get("any_active") else "Sin activacion"
        regime_summary = f"""
    <section class="panel" id="regimen">
      <h2>Regimen de mercado</h2>
      <div class="meta">
        <span>Estado: <strong>{esc_text(regime_state)}</strong></span>
        <span>Flags activos: <strong>{esc_text(active_flags_label)}</strong></span>
      </div>
      <div class="meta">
        {''.join(regime_items) if regime_items else '<span>Sin flags configurados</span>'}
      </div>
    </section>
    """

    bonistas_nav = '<a href="#bonistas">Bonos Locales</a>' if show_bonistas else ""
    bonistas_section = ""
    if show_bonistas:
        bond_summary_tables = (
            build_collapsible("Ver resumen por subfamilia", build_table(bond_subfamily_summary, formatters={}), open_by_default=True, compact=True)
            + build_collapsible("Ver resumen por taxonomia local", build_table(bond_local_subfamily_summary, formatters={}), compact=True)
            + build_collapsible(
                "Ver monitoreo completo de bonos",
                build_table(
                    bond_monitor,
                    formatters={
                        "Peso_%": fmt_pct,
                        "bonistas_tir_pct": fmt_pct,
                        "bonistas_paridad_pct": fmt_pct,
                        "bonistas_md": lambda x: "-" if pd.isna(x) else f"{float(x):.2f}",
                        "bonistas_volume_last": lambda x: "-" if pd.isna(x) else f"{float(x):,.0f}",
                        "bonistas_volume_avg_20d": lambda x: "-" if pd.isna(x) else f"{float(x):,.0f}",
                        "bonistas_volume_ratio": lambda x: "-" if pd.isna(x) else f"{float(x):.2f}x",
                        "bonistas_tir_vs_avg_365d_pct": fmt_pct,
                        "bonistas_parity_gap_pct": fmt_pct,
                    },
                ),
                compact=True,
            )
        )
        bonistas_section = f"""
    <section class="panel" id="bonistas">
      <h2>Bonos Locales</h2>
      <div class="meta">
        <span>CER: <strong>{esc_text(bonistas_macro.get('cer_diario'))}</strong></span>
        <span>TAMAR: <strong>{esc_text(bonistas_macro.get('tamar'))}</strong></span>
        <span>BADLAR: <strong>{esc_text(bonistas_macro.get('badlar'))}</strong></span>
        <span>Reservas BCRA: <strong>{esc_text(bonistas_macro.get('reservas_bcra_musd'))}</strong></span>
        <span>A3500: <strong>{esc_text(bonistas_macro.get('a3500_mayorista'))}</strong></span>
        <span>Riesgo pais: <strong>{esc_text(bonistas_macro.get('riesgo_pais_bps'))}</strong></span>
        <span>REM inflacion: <strong>{esc_text(bonistas_macro.get('rem_inflacion_mensual_pct'))}</strong></span>
        <span>REM 12m: <strong>{esc_text(bonistas_macro.get('rem_inflacion_12m_pct'))}</strong></span>
        <span>UST 5y: <strong>{esc_text(bonistas_macro.get('ust_5y_pct'))}</strong></span>
        <span>UST 10y: <strong>{esc_text(bonistas_macro.get('ust_10y_pct'))}</strong></span>
        {ust_note}
      </div>
      {build_bond_summary(bond_subfamily_summary, bond_local_subfamily_summary, bonistas_macro)}
      {bond_summary_tables}
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
        <p class="eyebrow">{esc_text(title)}</p>
        <h1>{esc_text(headline)}</h1>
        <p class="lede">{lede}</p>
      </div>
    </header>

    <nav class="quick-nav">
      <a href="#panorama">Panorama</a>
      <a href="#cambios">Cambios</a>
      <a href="#decision">Decision</a>
      <a href="#sizing">Sizing</a>
      <a href="#regimen">Regimen</a>
      <a href="#resumen">Resumen</a>
      <a href="#tecnico">Tecnico</a>
      {bonistas_nav}
      <a href="#cartera">Cartera</a>
      <a href="#integridad">Integridad</a>
    </nav>

    {primary_cards}
    {secondary_cards}
    {action_summary}
    {panorama_section}
    {changes_section}
    {regime_summary}

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
            formatters={"Score_Promedio": fmt_score},
        )}
      </section>

      <section class="panel" id="sizing">
        <h2>Sizing</h2>
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
            ),
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
      {build_technical_summary(technical_view)}
      {build_collapsible("Ver tabla tecnica completa", build_technical_table(technical_view), compact=True)}
    </section>

    {bonistas_section}

    <section class="panel" id="decision">
      <div class="panel-head">
      <h2>Decision final</h2>
        <div class="filters">
          <input id="ticker-filter" type="search" placeholder="Filtrar ticker">
          <select id="action-filter">
            <option value="">Todas las acciones</option>
            <option value="{ACTION_REFUERZO}">{ACTION_REFUERZO}</option>
            <option value="{ACTION_REDUCIR}">{ACTION_REDUCIR}</option>
            <option value="{ACTION_DESPLEGAR_LIQUIDEZ}">{ACTION_DESPLEGAR_LIQUIDEZ}</option>
            <option value="{ACTION_MANTENER_NEUTRAL}">{ACTION_MANTENER_NEUTRAL}</option>
          </select>
        </div>
      </div>
      {build_decision_priority_board(decision_view, action_col=action_col, motive_col=motive_col)}
      {build_collapsible("Ver tabla completa de decision", build_decision_table(decision_view, action_col=action_col, motive_col=motive_col), open_by_default=True)}
    </section>

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
    </section>

    <section class="panel" id="integridad">
      <h2>Integridad</h2>
      {build_collapsible("Ver chequeos de integridad", build_table(integrity_report), compact=True)}
    </section>
  </main>
  <script>
    const tickerInput = document.getElementById('ticker-filter');
    const actionSelect = document.getElementById('action-filter');
    const rows = Array.from(document.querySelectorAll('#decision-table tbody tr'));
    const navLinks = Array.from(document.querySelectorAll('.quick-nav a[href^="#"]'));
    const observedSections = navLinks
      .map((link) => document.querySelector(link.getAttribute('href')))
      .filter(Boolean);

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

    const observer = new IntersectionObserver((entries) => {{
      entries.forEach((entry) => {{
        if (!entry.isIntersecting) return;
        const id = `#${{entry.target.id}}`;
        navLinks.forEach((link) => {{
          link.classList.toggle('active', link.getAttribute('href') === id);
        }});
      }});
    }}, {{ rootMargin: '-35% 0px -55% 0px', threshold: 0.01 }});

    observedSections.forEach((section) => observer.observe(section));
  </script>
</body>
</html>
"""

    return html_body
