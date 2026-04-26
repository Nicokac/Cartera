from __future__ import annotations

import html
import math

import pandas as pd

from decision.action_constants import (
    ACTION_DESPLEGAR_LIQUIDEZ,
    ACTION_REDUCIR,
    ACTION_REFUERZO,
)


FAMILY_LABELS = {
    "stock": "Acción",
    "etf": "ETF",
    "bond": "Bono",
    "fund": "FCI",
    "liquidity": "Liquidez",
}


SUBFAMILY_LABELS = {
    "bond_bopreal": "Bopreal",
    "bond_cer": "CER",
    "bond_other": "Otros",
    "bond_sov_ar": "Soberano AR",
    "etf_core": "Core",
    "etf_country_region": "País / Región",
    "etf_other": "Otros",
    "etf_sector": "Sectorial",
    "fund_other": "Otros",
    "liquidity_other": "Liquidez",
    "stock_argentina": "Argentina",
    "stock_commodity": "Commodities",
    "stock_defensive_dividend": "Defensivo / Dividendos",
    "stock_growth": "Growth",
}


def fmt_ars(value: object) -> str:
    if pd.isna(value):
        return "-"
    return f"${float(value):,.0f}"


def fmt_usd(value: object) -> str:
    if pd.isna(value):
        return "-"
    return f"USD {float(value):,.2f}"


def fmt_money_by_currency(value: object, currency: object) -> str:
    currency_text = str(currency or "ARS").strip().upper()
    if pd.isna(value):
        return "-"
    if currency_text == "USD":
        return fmt_usd(value)
    return fmt_ars(value)


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


def humanize_dimension_value(column: str, value: object) -> str:
    text = fmt_label(value)
    if text == "-":
        return text
    if column == "asset_family":
        return FAMILY_LABELS.get(text, text)
    if column == "asset_subfamily":
        return SUBFAMILY_LABELS.get(text, text)
    return text


def fmt_quantity(value: object) -> str:
    if pd.isna(value):
        return "-"
    numeric = float(value)
    if abs(numeric - round(numeric)) < 1e-9:
        return f"{int(round(numeric)):,}"
    return f"{numeric:,.2f}".rstrip("0").rstrip(".")


def fmt_datetime_short(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return "-"
    return ts.strftime("%Y-%m-%d %H:%M")


def fmt_count_label(value: object, singular: str, plural: str | None = None) -> str:
    try:
        count = int(value or 0)
    except Exception:
        count = 0
    plural = plural or f"{singular}s"
    return f"{count} {singular if count == 1 else plural}"


def safe_int(value: object, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    try:
        return int(value)
    except Exception:
        return default


def esc_text(value: object) -> str:
    return html.escape(fmt_label(value))


def truncate_text(value: object, limit: int) -> str:
    text = fmt_label(value)
    if text == "-" or len(text) <= limit:
        return text
    trimmed = text[:limit].rstrip()
    if " " in trimmed:
        trimmed = trimmed.rsplit(" ", 1)[0]
    trimmed = trimmed.rstrip(".,;: ")
    return f"{trimmed}..."


def metric_class(column: str, value: object) -> str:
    if pd.isna(value):
        return "metric metric-neutral"

    try:
        num = float(value)
    except Exception:
        text = str(value).strip().lower()
        if column == "asset_family":
            if text in {"stock", "acción"}:
                return "metric metric-positive"
            if text == "etf":
                return "metric metric-warn"
            if text in {"bond", "bono", "liquidity", "liquidez", "fund", "fci"}:
                return "metric metric-neutral"
        if column == "asset_subfamily":
            if text in {"etf_sector", "sectorial"}:
                return "metric metric-positive"
            if text in {"etf_country_region", "país / región", "pais / región", "país / region", "país / región"}:
                return "metric metric-warn"
            if text in {"etf_core", "etf_other", "core", "otros"}:
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
    table_id: str = "",
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
            cell_class = ""
            if col == "Calidad_Historia":
                raw = str(value or "").strip().lower()
                if raw:
                    raw_slug = raw.replace(" ", "-")
                    cell_class = f' class="cell-quality cell-quality-{html.escape(raw_slug)}"'
            cells.append(f"<td{cell_class}>{html.escape(str(rendered))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    id_attr = f' id="{html.escape(table_id)}"' if table_id else ""
    return f'<div class="table-wrap"><table{id_attr} class="{table_class}"><thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def ensure_table_columns(df: pd.DataFrame | None, columns: list[str]) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=columns)
    return df.reindex(columns=columns)


def build_rsi_gauge(rsi_value: object, *, width: int = 80, height: int = 44) -> str:
    try:
        v = float(rsi_value)
    except (TypeError, ValueError):
        return "-"
    if v != v:
        return "-"
    v = max(0.0, min(100.0, v))

    cx = width / 2
    cy = float(height - 8)
    r_o = cx - 2
    r_i = r_o * 0.60

    def _pt(r: float, rsi: float) -> tuple[float, float]:
        a = math.pi * (1.0 - rsi / 100.0)
        return cx + r * math.cos(a), cy - r * math.sin(a)

    def _zone(lo: float, hi: float, color: str) -> str:
        ox1, oy1 = _pt(r_o, lo)
        ox2, oy2 = _pt(r_o, hi)
        ix1, iy1 = _pt(r_i, lo)
        ix2, iy2 = _pt(r_i, hi)
        d = (
            f"M{ox1:.2f},{oy1:.2f}"
            f" A{r_o:.2f},{r_o:.2f} 0 0,1 {ox2:.2f},{oy2:.2f}"
            f" L{ix2:.2f},{iy2:.2f}"
            f" A{r_i:.2f},{r_i:.2f} 0 0,0 {ix1:.2f},{iy1:.2f}Z"
        )
        return f'<path d="{d}" fill="{color}"/>'

    zones = (
        _zone(0, 30, "rgba(18,132,94,0.22)")
        + _zone(30, 70, "rgba(106,116,120,0.14)")
        + _zone(70, 100, "rgba(177,57,45,0.22)")
    )
    a_needle = math.pi * (1.0 - v / 100.0)
    nx = cx + (r_i - 1) * math.cos(a_needle)
    ny = cy - (r_i - 1) * math.sin(a_needle)
    needle = (
        f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{nx:.2f}" y2="{ny:.2f}" '
        f'stroke="#1d2a2f" stroke-width="1.5" stroke-linecap="round"/>'
        f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="2" fill="#1d2a2f"/>'
    )
    ink = "#0f6c5c" if v <= 30 else ("#9f3a22" if v >= 70 else "#1d2a2f")
    label = (
        f'<text x="{cx:.1f}" y="{cy + 7:.1f}" font-size="8" fill="{ink}" '
        f'text-anchor="middle" font-weight="700" '
        f'font-family="IBM Plex Mono,Consolas,monospace">{v:.0f}</text>'
    )
    return (
        f'<svg class="rsi-gauge" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f"{zones}{needle}{label}"
        f"</svg>"
    )


def build_sparkline_svg(closes: list[float], *, width: int = 60, height: int = 20) -> str:
    vals = [v for v in closes if isinstance(v, (int, float)) and v == v]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return ""
    x_step = width / (len(vals) - 1)
    points = " ".join(
        f"{i * x_step:.1f},{height - (v - lo) / (hi - lo) * height:.1f}"
        for i, v in enumerate(vals)
    )
    color = "#0f6c5c" if vals[-1] >= vals[0] else "#9f3a22"
    return (
        f'<svg class="sparkline" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.5" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f"</svg>"
    )


_SECONDARY_TECH_COLS = frozenset({
    "Vol_20d_Anual_%",
    "Avg_Volume_20d",
    "Dist_EMA20_%",
    "Dist_EMA50_%",
    "Dist_SMA20_%",
    "Dist_SMA50_%",
    "Dist_52w_High_%",
    "Dist_52w_Low_%",
    "Drawdown_desde_Max3m_%",
})


def build_technical_table(df: pd.DataFrame, *, price_history: dict | None = None) -> str:
    if df.empty:
        return '<div class="empty">Sin datos para mostrar.</div>'

    price_history = price_history or {}
    column_labels = {
        "Ticker_IOL": "Ticker",
        "Tech_Trend": "Tendencia",
        "RSI_14": "RSI 14",
        "Momentum_20d_%": "Momentum 20d",
        "Momentum_60d_%": "Momentum 60d",
        "Dist_SMA20_%": "Dist. SMA20",
        "Dist_SMA50_%": "Dist. SMA50",
        "Dist_SMA200_%": "Dist. SMA200",
        "Dist_EMA20_%": "Dist. EMA20",
        "Dist_EMA50_%": "Dist. EMA50",
        "Dist_52w_High_%": "Dist. máx. 52w",
        "Dist_52w_Low_%": "Dist. mín. 52w",
        "Vol_20d_Anual_%": "Vol. anual 20d",
        "Avg_Volume_20d": "Volumen prom. 20d",
        "Drawdown_desde_Max3m_%": "Drawdown desde máx. 3m",
    }
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
    metric_columns = {
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
    }
    has_sparks = bool(price_history)
    spark_th = "<th>Spark</th>" if has_sparks else ""

    def _sec(col: str) -> str:
        return ' class="col-secondary"' if col in _SECONDARY_TECH_COLS else ""

    col_ths = "".join(
        f'<th{_sec(col)}>{html.escape(column_labels.get(col, str(col)))}</th>'
        for col in df.columns
    )
    headers = spark_th + col_ths

    rows = []
    for _, row in df.iterrows():
        cells = []
        if has_sparks:
            ticker = str(row.get("Ticker_IOL", "")) if "Ticker_IOL" in df.columns else ""
            spark = build_sparkline_svg(price_history.get(ticker, []))
            cells.append(f'<td style="line-height:0;padding:4px 8px;">{spark}</td>')
        for col in df.columns:
            s = _sec(col)
            if col == "RSI_14":
                cells.append(f'<td{s} style="padding:2px 4px;line-height:0;">{build_rsi_gauge(row[col])}</td>')
            elif col in metric_columns:
                cells.append(f"<td{s}>{render_metric(col, row[col], formatters.get(col))}</td>")
            else:
                cells.append(f"<td{s}>{html.escape('-' if pd.isna(row[col]) else str(row[col]))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    toggle = (
        '<div class="tech-col-toggle">'
        '<button id="toggle-tech-cols" class="copy-btn">Mostrar m\u00e1s columnas</button>'
        '</div>'
    )
    table = (
        f'<div class="table-wrap">'
        f'<table class="technical-table">'
        f"<thead><tr>{headers}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        f"</table></div>"
    )
    return toggle + table


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
        detail_content = item.get("detail_html") or html.escape(item.get("detail", ""))
        badge = item.get("badge")
        explicit_badge_class = item.get("badge_class")
        badge_css_class = str(explicit_badge_class or badge_class(badge))
        badge_html = f'<span class="{badge_css_class}">{html.escape(str(badge))}</span>' if badge else ""
        if "badge-buy" in badge_css_class:
            item_tone = " item-buy"
        elif "badge-sell" in badge_css_class:
            item_tone = " item-sell"
        elif "badge-fund" in badge_css_class:
            item_tone = " item-fund"
        else:
            item_tone = ""
        extra = item.get("extra_class", "")
        extra_str = f" {extra}" if extra else ""
        rows.append(
            f'<article class="focus-item{item_tone}{extra_str}">'
            f'<div class="focus-top"><strong>{kicker}</strong>{badge_html}</div>'
            f'<div class="focus-title">{title}</div>'
            f'<div class="focus-detail">{detail_content}</div>'
            "</article>"
        )
    return f'<div class="focus-list tone-{tone}">{"".join(rows)}</div>'


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
