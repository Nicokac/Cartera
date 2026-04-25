from __future__ import annotations

import html
import pandas as pd

from report_primitives import (
    badge_class,
    build_collapsible,
    build_focus_list,
    build_table,
    build_technical_table,
    ensure_table_columns,
    esc_text,
    fmt_ars,
    fmt_label,
    fmt_pct,
    fmt_score,
    fmt_usd,
    safe_int,
    truncate_text,
)

from decision.action_constants import ACTION_REDUCIR, ACTION_REFUERZO


# ── Signal matrix helpers ──────────────────────────────────────────────────────

_VOTE_KEYS = [
    ("rsi", "RSI"),
    ("momentum_20d", "m20"),
    ("momentum_60d", "m60"),
    ("sma_trend", "SMA"),
    ("score_unificado", "Sc"),
    ("market_regime", "Rg"),
    ("adx", "ADX"),
    ("relative_volume", "rVol"),
]


def _parse_votes(value: object) -> dict[str, float]:
    if isinstance(value, dict):
        out: dict[str, float] = {}
        for k, v in value.items():
            try:
                out[str(k)] = float(v)
            except Exception:
                out[str(k)] = 0.0
        return out
    if isinstance(value, str) and value and value != "-":
        out = {}
        for part in value.split("|"):
            part = part.strip()
            if ":" in part:
                k, v = part.rsplit(":", 1)
                try:
                    out[k.strip()] = float(v.strip().replace("+", ""))
                except ValueError:
                    pass
        return out
    return {}


def _sig_cell(vote: float) -> str:
    if vote > 0:
        return '<span class="sig sig-pos">+</span>'
    if vote < 0:
        return '<span class="sig sig-neg">\u2212</span>'
    return '<span class="sig sig-neu">\u25cb</span>'


def build_prediction_signal_table(predictions_view: pd.DataFrame) -> str:
    if not isinstance(predictions_view, pd.DataFrame) or predictions_view.empty:
        return '<div class="empty">Sin datos para mostrar.</div>'

    vote_headers = "".join(
        f'<th class="sig-th" title="{html.escape(key)}">{html.escape(label)}</th>'
        for key, label in _VOTE_KEYS
    )
    header = (
        "<tr><th>ticker</th><th>dir</th><th>conf</th>"
        + vote_headers
        + "<th>accion</th><th>outcome</th></tr>"
    )

    rows_html: list[str] = []
    for _, row in predictions_view.iterrows():
        votes = _parse_votes(row.get("signal_votes"))
        sig_cells = "".join(
            f"<td>{_sig_cell(votes.get(key, 0))}</td>" for key, _ in _VOTE_KEYS
        )
        ticker = html.escape(str(row.get("ticker", "-")))
        direction = html.escape(str(row.get("direction", "-")).strip().lower())
        conf_raw = row.get("confidence")
        _CONV_COLORS = {"alta": "#1a7f4b", "media": "#b07e0f", "baja": "#8a9ba8"}
        if pd.notna(conf_raw):
            conf_val = float(conf_raw)
            raw_label = str(row.get("conviction_label") or "").strip()
            conv_label = raw_label if raw_label in _CONV_COLORS else (
                "alta" if conf_val >= 0.35 else "media" if conf_val >= 0.20 else "baja"
            )
            conv_color = _CONV_COLORS[conv_label]
            conf_html = (
                f'<span style="color:{conv_color};font-size:10px;font-weight:600;margin-right:3px">{conv_label}</span>'
                f"{html.escape(fmt_pct(conf_val * 100.0))}"
            )
        else:
            conf_html = "-"
        accion = html.escape(str(row.get("accion_sugerida_v2", "-")))
        outcome = html.escape(str(row.get("outcome_date", "-")))
        rows_html.append(
            f"<tr>"
            f"<td><strong>{ticker}</strong></td>"
            f"<td>{direction}</td>"
            f"<td>{conf_html}</td>"
            f"{sig_cells}"
            f"<td>{accion}</td>"
            f"<td>{outcome}</td>"
            f"</tr>"
        )

    return (
        '<div class="table-wrap">'
        '<table class="signal-table">'
        f"<thead>{header}</thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        "</table></div>"
    )


# ── Allocation bar helpers ─────────────────────────────────────────────────────

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


def build_prediction_section(prediction_bundle: dict[str, object]) -> str:
    predictions = prediction_bundle.get("predictions", pd.DataFrame())
    if not isinstance(predictions, pd.DataFrame) or predictions.empty:
        return ""

    work = predictions.copy()
    summary = prediction_bundle.get("summary", {}) or {}
    config = prediction_bundle.get("config", {}) or {}

    def _votes_html(value: object) -> str:
        votes = _parse_votes(value)
        if not votes:
            return "-"
        # The matrix keeps a ternary visual representation even when votes are continuous.
        parts = [
            f'<span style="font-size:10px;color:var(--muted);margin-right:1px">{html.escape(label)}</span>{_sig_cell(float(votes[key]))}'
            for key, label in _VOTE_KEYS
            if key in votes
        ]
        return '<span style="display:inline-flex;flex-wrap:wrap;gap:4px;align-items:center">' + "".join(parts) + "</span>" if parts else "-"

    def _direction_badge(direction: object) -> str:
        direction_text = str(direction or "").strip().lower()
        if direction_text == "up":
            return "Refuerzo"
        if direction_text == "down":
            return "Reducir"
        return "Mantener / Neutral"

    def _focus_items(source: pd.DataFrame, *, tone: str) -> str:
        items: list[dict[str, str]] = []
        for _, row in source.head(3).iterrows():
            direction_label = str(row.get("direction", "")).upper()
            items.append(
                {
                    "kicker": str(row.get("ticker", "-")),
                    "title": f"Confianza {fmt_pct(float(row.get('confidence', 0.0)) * 100.0)}",
                    "detail_html": _votes_html(row.get("signal_votes")),
                    "badge": direction_label,
                    "badge_class": badge_class(_direction_badge(row.get("direction"))),
                }
            )
        return build_focus_list(items, empty_message="Sin nombres para mostrar.", tone=tone)

    bullish = work.loc[work["direction"].astype(str) == "up"].sort_values("confidence", ascending=False)
    bearish = work.loc[work["direction"].astype(str) == "down"].sort_values("confidence", ascending=False)
    neutral = work.loc[work["direction"].astype(str) == "neutral"].sort_values("confidence", ascending=False)
    def _accion_con_advertencia(row: object) -> str:
        direction = str(row.get("direction", "")).strip().lower()
        accion = str(row.get("accion_sugerida_v2", "")).strip()
        if not accion or accion == "-":
            return accion
        contradice = (
            (direction == "down" and accion == ACTION_REFUERZO)
            or (direction == "up" and accion == ACTION_REDUCIR)
            or (direction == "neutral" and accion in {ACTION_REFUERZO, ACTION_REDUCIR})
        )
        return f"\u26a0 {accion}" if contradice else accion

    work = work.copy()
    work["accion_sugerida_v2"] = work.apply(_accion_con_advertencia, axis=1)

    predictions_view = ensure_table_columns(
        work,
        [
            "ticker",
            "direction",
            "confidence",
            "consensus_raw",
            "score_unificado",
            "accion_sugerida_v2",
            "outcome_date",
            "signal_votes",
        ],
    )
    return f"""
    <section class="panel" id="prediccion">
      <h2>Predicción</h2>
      <div class="meta">
        <span>Total: <strong>{int(summary.get('total', len(work)))}</strong></span>
        <span>Suba: <strong>{int(summary.get('up', 0))}</strong></span>
        <span>Baja: <strong>{int(summary.get('down', 0))}</strong></span>
        <span>Neutral: <strong>{int(summary.get('neutral', 0))}</strong></span>
        <span>Confianza media: <strong>{fmt_pct(float(summary.get('mean_confidence', 0.0)) * 100.0)}</strong></span>
        <span>Horizonte: <strong>{safe_int(config.get('horizon_days'))} ruedas</strong></span>
      </div>
      <div class="meta">
        <span>La predicción direccional combina señales técnicas, <strong>score_unificado</strong> y régimen; puede diferir de la decisión final, que pondera además criterios de cartera y sizing.</span>
      </div>
      <div class="focus-columns focus-columns-wide">
        <div>
          <h3>Señales alcistas</h3>
          {_focus_items(bullish, tone='buy')}
        </div>
        <div>
          <h3>Señales bajistas</h3>
          {_focus_items(bearish, tone='sell')}
        </div>
        <div>
          <h3>Zona neutral</h3>
          {_focus_items(neutral, tone='neutral')}
        </div>
      </div>
      {build_collapsible(
          "Ver tabla completa de prediccion",
          build_prediction_signal_table(predictions_view),
          compact=True,
      )}
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
        {build_focus_list(_items(cerca_max, title_fn=lambda row: "En maximos 52w" if abs(float(row.get(high52_col) or 0)) < 0.5 else f"{fmt_pct(row.get(high52_col))} vs maximo anual"), empty_message='Sin nombres cerca de maximos anuales.', tone='neutral')}
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


# ── Score distribution SVG ────────────────────────────────────────────────────

def build_score_distribution(
    decision_view: pd.DataFrame,
    action_col: str,
) -> str:
    if not isinstance(decision_view, pd.DataFrame) or decision_view.empty:
        return ""
    if "score_unificado" not in decision_view.columns:
        return ""

    work = decision_view[["Ticker_IOL", "score_unificado", action_col]].dropna(subset=["score_unificado"]).copy()
    if work.empty:
        return ""

    W, H, PAD = 600, 52, 24
    axis_y = 30

    def _score_x(score: float) -> float:
        return PAD + (max(-1.0, min(1.0, float(score))) + 1) / 2 * (W - 2 * PAD)

    _ACTION_COLOR = {
        ACTION_REFUERZO: "#0f6c5c",
        ACTION_REDUCIR: "#9f3a22",
    }

    work = work.sort_values("score_unificado")
    dots: list[str] = []
    for i, (_, row) in enumerate(work.iterrows()):
        score = float(row["score_unificado"])
        ticker = str(row["Ticker_IOL"])
        accion = str(row.get(action_col, ""))
        color = _ACTION_COLOR.get(accion, "#6a7478")
        cx = _score_x(score)
        cy = axis_y - 5 if i % 2 == 0 else axis_y + 5
        r = 5 if accion == ACTION_REFUERZO else 4
        title = html.escape(f"{ticker}: {score:+.2f}")
        dots.append(
            f'<circle cx="{cx:.1f}" cy="{cy}" r="{r}" fill="{color}" '
            f'fill-opacity="0.82" stroke="none">'
            f"<title>{title}</title></circle>"
        )

    axis_x0, axis_x1 = PAD, W - PAD
    cx_zero = _score_x(0.0)
    axis_line = f'<line x1="{axis_x0}" y1="{axis_y}" x2="{axis_x1}" y2="{axis_y}" stroke="#d7d0c6" stroke-width="1.5"/>'
    center_line = f'<line x1="{cx_zero:.1f}" y1="{axis_y - 8}" x2="{cx_zero:.1f}" y2="{axis_y + 8}" stroke="#6a7478" stroke-width="1"/>'
    labels = (
        f'<text x="{axis_x0}" y="{H - 2}" font-size="8" fill="#9f3a22" text-anchor="start">\u2190 Reducci\u00f3n</text>'
        f'<text x="{cx_zero:.1f}" y="{H - 2}" font-size="8" fill="#6a7478" text-anchor="middle">0</text>'
        f'<text x="{axis_x1}" y="{H - 2}" font-size="8" fill="#0f6c5c" text-anchor="end">Refuerzo \u2192</text>'
    )
    svg = (
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
        f'class="score-dist" role="img" aria-label="Distribucion de scores">'
        f"{axis_line}{center_line}{''.join(dots)}{labels}"
        f"</svg>"
    )
    legend = (
        '<div class="score-dist-legend">'
        '<span><span class="score-dist-dot" style="background:#0f6c5c"></span>Refuerzo</span>'
        '<span><span class="score-dist-dot" style="background:#9f3a22"></span>Reducir</span>'
        '<span><span class="score-dist-dot" style="background:#6a7478"></span>Neutral / Monitoreo</span>'
        "</div>"
    )
    return f'<div class="score-dist-wrap">{svg}{legend}</div>'


def _build_risk_focus_block(source: pd.DataFrame, *, title: str, empty_message: str) -> str:
    if source.empty:
        return f'<div class="risk-subsection"><h3>{html.escape(title)}</h3><div class="empty compact-empty">{html.escape(empty_message)}</div></div>'

    dd_items: list[dict[str, str]] = []
    vol_items: list[dict[str, str]] = []
    ret_items: list[dict[str, str]] = []

    for _, row in source.nsmallest(3, "Drawdown_Max_%").iterrows():
        dd_items.append(
            {
                "kicker": str(row.get("Ticker_IOL", "-")),
                "title": f"Drawdown {fmt_pct(row.get('Drawdown_Max_%'))}",
                "detail": f"{fmt_label(row.get('Tipo'))} / {fmt_label(row.get('Bloque'))} | Base {fmt_label(row.get('Base_Riesgo'))}",
            }
        )
    for _, row in source.nlargest(3, "Volatilidad_Diaria_%").iterrows():
        vol_items.append(
            {
                "kicker": str(row.get("Ticker_IOL", "-")),
                "title": f"Vol diaria {fmt_pct(row.get('Volatilidad_Diaria_%'))}",
                "detail": f"Peso {fmt_pct(row.get('Peso_%'))} | Obs {safe_int(row.get('Observaciones'))} | Historia {fmt_label(row.get('Calidad_Historia'))}",
            }
        )
    for _, row in source.nlargest(3, "Retorno_Acum_%").iterrows():
        ret_items.append(
            {
                "kicker": str(row.get("Ticker_IOL", "-")),
                "title": f"Retorno {fmt_pct(row.get('Retorno_Acum_%'))}",
                "detail": f"Base {fmt_label(row.get('Base_Riesgo'))} | Obs {safe_int(row.get('Observaciones'))} | Historia {fmt_label(row.get('Calidad_Historia'))}",
            }
        )

    return f"""
      <div class="risk-subsection">
        <h3>{html.escape(title)}</h3>
        <div class="focus-columns focus-columns-wide">
          <div>
            <h3>Mayores drawdowns</h3>
            {build_focus_list(dd_items, empty_message='Sin drawdowns relevantes.', tone='sell')}
          </div>
          <div>
            <h3>Mayor volatilidad</h3>
            {build_focus_list(vol_items, empty_message='Sin volatilidad relevante.', tone='neutral')}
          </div>
          <div>
            <h3>Mejor rendimiento</h3>
            {build_focus_list(ret_items, empty_message='Sin rendimientos historicos.', tone='buy')}
          </div>
        </div>
      </div>
            """


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

        risk_html = f"""
      <h3>Riesgo historico</h3>
      <div class="meta">
        <span>Ventana: <strong>{esc_text(portfolio_summary.get('desde'))} → {esc_text(portfolio_summary.get('hasta'))}</strong></span>
        <span>Snapshots: <strong>{safe_int(portfolio_summary.get('snapshots'))}</strong></span>
        <span>Retorno cartera: <strong>{fmt_pct(portfolio_summary.get('retorno_acum_pct'))}</strong></span>
        <span>Vol diaria cartera: <strong>{fmt_pct(portfolio_summary.get('volatilidad_diaria_pct'))}</strong></span>
        <span>Max drawdown cartera: <strong>{fmt_pct(portfolio_summary.get('drawdown_max_pct'))}</strong></span>
      </div>
      <div class="meta">
        <span>Metodo: <strong>Universo comparable</strong></span>
        <span>Pasos estables: <strong>{safe_int(portfolio_summary.get('pasos_estables'))}/{safe_int(portfolio_summary.get('pasos_totales'))}</strong></span>
        <span>Cobertura previa prom.: <strong>{fmt_pct(portfolio_summary.get('coverage_prev_promedio_pct'))}</strong></span>
        <span>Cobertura actual prom.: <strong>{fmt_pct(portfolio_summary.get('coverage_curr_promedio_pct'))}</strong></span>
      </div>
      {f'<div class="meta"><span>{esc_text(stability_note)}</span></div>' if stability_note else ''}
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
      {build_collapsible(
          "Ver tabla completa de riesgo",
          build_table(
              position_risk[["Ticker_IOL", "Tipo", "Bloque", "Peso_%", "Base_Riesgo", "Calidad_Historia", "Retorno_Acum_%", "Volatilidad_Diaria_%", "Drawdown_Max_%", "Observaciones"]],
              formatters={
                  "Peso_%": fmt_pct,
                  "Retorno_Acum_%": fmt_pct,
                  "Volatilidad_Diaria_%": fmt_pct,
                  "Drawdown_Max_%": fmt_pct,
              },
              table_class="risk-history-table",
              table_id="risk-history-table",
          ),
          compact=True,
      )}
        """
    return f"""
    <section class="panel" id="resumen">
      <h2>Resumen por tipo</h2>
      <div class="meta">
        <span>Total consolidado: <strong>{fmt_ars(kpis['total_ars'])}</strong></span>
        <span>Total estilo IOL: <strong>{fmt_ars(kpis['total_ars_iol'])}</strong></span>
        <span>Liquidez broker: <strong>{fmt_ars(kpis.get('liquidez_broker_ars', kpis['liquidez_ars']))}</strong></span>
        <span>Liquidez ampliada: <strong>{fmt_ars(kpis['liquidez_ars'])}</strong></span>
        <span>Liquidez USD convertida: <strong>{fmt_ars(kpis['liquidez_usd_ars'])}</strong></span>
        <span>Finviz fundamentals: <strong>{finviz_fund_covered}/{finviz_total}</strong></span>
        <span>Finviz ratings: <strong>{finviz_ratings_covered}/{finviz_total}</strong></span>
      </div>
      {score_dist_html}
      {build_allocation_bar(resumen_tipos)}
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
      {risk_html}
    </section>
    """


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
          ),
          formatters={
              "Peso_Fondeo_%": fmt_pct,
              "Monto_ARS": fmt_ars,
              "Monto_USD": fmt_usd,
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

    bond_summary_tables = (
        build_collapsible("Ver resumen por subfamilia", build_table(bond_subfamily_summary, formatters={}), compact=True)
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
    return f"""
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
