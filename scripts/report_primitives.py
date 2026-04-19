from __future__ import annotations

import html

import pandas as pd

from decision.action_constants import (
    ACTION_DESPLEGAR_LIQUIDEZ,
    ACTION_REDUCIR,
    ACTION_REFUERZO,
)


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
            cells.append(f"<td>{html.escape(str(rendered))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    id_attr = f' id="{html.escape(table_id)}"' if table_id else ""
    return f'<div class="table-wrap"><table{id_attr} class="{table_class}"><thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


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
    headers = "".join(f"<th>{html.escape(str(col))}</th>" for col in df.columns)
    rows = []
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            if col in metric_columns:
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
        explicit_badge_class = item.get("badge_class")
        badge_css_class = str(explicit_badge_class or badge_class(badge))
        badge_html = f'<span class="{badge_css_class}">{html.escape(str(badge))}</span>' if badge else ""
        rows.append(
            '<article class="focus-item">'
            f'<div class="focus-top"><strong>{kicker}</strong>{badge_html}</div>'
            f'<div class="focus-title">{title}</div>'
            f'<div class="focus-detail">{detail}</div>'
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
