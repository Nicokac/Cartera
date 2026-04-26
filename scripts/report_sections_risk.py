from __future__ import annotations

import html
import pandas as pd

from report_primitives import (
    build_collapsible,
    build_focus_list,
    build_table,
    fmt_label,
    fmt_pct,
    safe_int,
)

from decision.action_constants import ACTION_REDUCIR, ACTION_REFUERZO


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
        f'<text x="{axis_x0}" y="{H - 2}" font-size="8" fill="#9f3a22" text-anchor="start">← Reducción</text>'
        f'<text x="{cx_zero:.1f}" y="{H - 2}" font-size="8" fill="#6a7478" text-anchor="middle">0</text>'
        f'<text x="{axis_x1}" y="{H - 2}" font-size="8" fill="#0f6c5c" text-anchor="end">Refuerzo →</text>'
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
            {build_focus_list(ret_items, empty_message='Sin rendimientos históricos.', tone='buy')}
          </div>
        </div>
      </div>
            """
