from __future__ import annotations

import html
import pandas as pd

from report_primitives import (
    badge_class,
    build_collapsible,
    build_focus_list,
    ensure_table_columns,
    fmt_pct,
)

from decision.action_constants import ACTION_REDUCIR, ACTION_REFUERZO


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
        return '<span class="sig sig-neg">âˆ’</span>'
    return '<span class="sig sig-neu">â—‹</span>'


def build_prediction_signal_table(predictions_view: pd.DataFrame) -> str:
    if not isinstance(predictions_view, pd.DataFrame) or predictions_view.empty:
        return '<div class="empty">Sin datos para mostrar.</div>'

    vote_headers = "".join(
        f'<th scope="col" class="sig-th" title="{html.escape(key)}">{html.escape(label)}</th>'
        for key, label in _VOTE_KEYS
    )
    header = (
        '<tr><th scope="col">Ticker</th><th scope="col">Direccion</th><th scope="col">Confianza</th>'
        + vote_headers
        + '<th scope="col">Accion</th><th scope="col">Fecha objetivo</th></tr>'
    )

    rows_html: list[str] = []
    for _, row in predictions_view.iterrows():
        votes = _parse_votes(row.get("signal_votes"))
        sig_cells = "".join(
            f"<td>{_sig_cell(votes.get(key, 0))}</td>" for key, _ in _VOTE_KEYS
        )
        ticker = html.escape(str(row.get("ticker", "-")))
        direction_raw = str(row.get("direction", "-")).strip().lower()
        direction = html.escape(
            {
                "up": "Suba",
                "down": "Baja",
                "neutral": "Neutral",
            }.get(direction_raw, direction_raw or "-")
        )
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


def build_prediction_section(prediction_bundle: dict[str, object]) -> str:
    predictions = prediction_bundle.get("predictions", pd.DataFrame())
    if not isinstance(predictions, pd.DataFrame) or predictions.empty:
        return ""

    work = predictions.copy()
    summary = prediction_bundle.get("summary", {}) or {}
    config = prediction_bundle.get("config", {}) or {}
    accuracy = prediction_bundle.get("accuracy", {}) or {}
    accuracy_global = (accuracy.get("global", {}) or {}) if isinstance(accuracy, dict) else {}
    accuracy_by_family = accuracy.get("by_family", []) if isinstance(accuracy, dict) else []
    accuracy_by_score_band = accuracy.get("by_score_band", []) if isinstance(accuracy, dict) else []
    calibration_readiness = accuracy.get("calibration_readiness", []) if isinstance(accuracy, dict) else []

    def _votes_summary(value: object) -> str:
        votes = _parse_votes(value)
        if not votes:
            return "Sin matriz de seÃ±ales."
        favorable = sum(1 for key, _ in _VOTE_KEYS if float(votes.get(key, 0)) > 0)
        adverse = sum(1 for key, _ in _VOTE_KEYS if float(votes.get(key, 0)) < 0)
        neutral_count = sum(1 for key, _ in _VOTE_KEYS if float(votes.get(key, 0)) == 0)
        return f"Favorables {favorable} | Neutrales {neutral_count} | Adversas {adverse}"

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
            direction_text = str(row.get("direction", "")).strip().lower()
            direction_label = {
                "up": "Suba",
                "down": "Baja",
                "neutral": "Neutral",
            }.get(direction_text, direction_text.upper() or "-")
            items.append(
                {
                    "kicker": str(row.get("ticker", "-")),
                    "title": f"Confianza {fmt_pct(float(row.get('confidence', 0.0)) * 100.0)}",
                    "detail": _votes_summary(row.get("signal_votes")),
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
        return f"âš  {accion}" if contradice else accion

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
    signal_legend = """
      <div class="prediction-legend">
        <div class="signal-legend">
          <span class="signal-key"><span class="sig sig-pos">+</span> SeÃ±al favorable</span>
          <span class="signal-key"><span class="sig sig-neu">&#9675;</span> SeÃ±al neutral</span>
          <span class="signal-key"><span class="sig sig-neg">&#8722;</span> SeÃ±al adversa</span>
        </div>
        <div class="signal-map">
          <span><strong>Sc</strong> Score</span>
          <span><strong>Rg</strong> RÃ©gimen</span>
          <span><strong>m20</strong> Momentum 20d</span>
          <span><strong>m60</strong> Momentum 60d</span>
          <span><strong>rVol</strong> Volumen relativo</span>
        </div>
      </div>
    """
    prediction_detail = f"""
      {signal_legend}
      <div class="focus-columns focus-columns-wide">
        <div>
          <h3>Zona neutral</h3>
          {_focus_items(neutral, tone='neutral')}
        </div>
      </div>
      {build_prediction_signal_table(predictions_view)}
    """
    global_completed = int(accuracy_global.get("completed", 0) or 0)
    global_accuracy_pct = accuracy_global.get("accuracy_pct")
    global_accuracy_label = fmt_pct(global_accuracy_pct) if global_accuracy_pct is not None else "-"
    by_family_items = []
    for item in accuracy_by_family[:6]:
        fam = str(item.get("asset_family") or "sin_familia")
        completed = int(item.get("completed", 0) or 0)
        acc = item.get("accuracy_pct")
        by_family_items.append(
            {
                "kicker": fam,
                "title": f"{fmt_pct(acc) if acc is not None else '-'}",
                "detail": f"{completed} outcomes verificados",
            }
        )
    accuracy_block = f"""
      <div class="focus-columns focus-columns-wide">
        <div>
          <h3>Acierto histórico (global)</h3>
          <div class="focus-list tone-neutral">
            <article class="focus-item">
              <div class="focus-top"><strong>Global</strong></div>
              <div class="focus-title">{global_accuracy_label}</div>
              <div class="focus-detail">{global_completed} outcomes verificados</div>
            </article>
          </div>
        </div>
        <div>
          <h3>Acierto por familia</h3>
          {build_focus_list(by_family_items, empty_message='Sin outcomes verificados por familia.', tone='neutral')}
        </div>
        <div>
          <h3>Acierto por banda de score</h3>
          {build_focus_list(
              [
                  {
                      "kicker": str(item.get("score_band") or "-"),
                      "title": f"{fmt_pct(item.get('accuracy_pct')) if item.get('accuracy_pct') is not None else '-'}",
                      "detail": f"{int(item.get('completed', 0) or 0)} outcomes verificados",
                  }
                  for item in accuracy_by_score_band[:6]
              ],
              empty_message='Sin outcomes verificados por banda de score.',
              tone='neutral',
          )}
        </div>
      </div>
    """
    readiness_items = []
    for item in calibration_readiness[:6]:
        status = "Lista" if bool(item.get("ready")) else "Pendiente"
        readiness_items.append(
            {
                "kicker": str(item.get("asset_family") or "-"),
                "title": status,
                "detail": (
                    f"up={int(item.get('up', 0) or 0)} | down={int(item.get('down', 0) or 0)} | "
                    f"neutral={int(item.get('neutral', 0) or 0)} | min={int(item.get('min_count', 0) or 0)}/"
                    f"{int(item.get('required', 30) or 30)}"
                ),
            }
        )
    readiness_block = f"""
      <div class="focus-columns focus-columns-wide">
        <div>
          <h3>Preparación calibración por familia</h3>
          {build_focus_list(readiness_items, empty_message='Sin outcomes verificados para medir preparación.', tone='neutral')}
        </div>
      </div>
    """
    return f"""
    <section class="panel" id="prediccion">
      <h2>PredicciÃ³n</h2>
      <div class="meta">
        <span>Total: <strong>{int(summary.get('total', len(work)))}</strong></span>
        <span>Suba: <strong>{int(summary.get('up', 0))}</strong></span>
        <span>Baja: <strong>{int(summary.get('down', 0))}</strong></span>
        <span>Neutral: <strong>{int(summary.get('neutral', 0))}</strong></span>
        <span>Confianza media: <strong>{fmt_pct(float(summary.get('mean_confidence', 0.0)) * 100.0)}</strong></span>
        <span>Horizonte: <strong>{int(config.get('horizon_days') or 0)} ruedas</strong></span>
      </div>
      <div class="meta">
        <span>La predicciÃ³n direccional combina seÃ±ales tÃ©cnicas, <strong>score_unificado</strong> y rÃ©gimen; puede diferir de la decisiÃ³n final, que pondera ademÃ¡s criterios de cartera y sizing.</span>
      </div>
      <div class="focus-columns focus-columns-wide">
        <div>
          <h3>SeÃ±ales de suba</h3>
          {_focus_items(bullish, tone='buy')}
        </div>
        <div>
          <h3>SeÃ±ales de baja</h3>
          {_focus_items(bearish, tone='sell')}
        </div>
      </div>
      {accuracy_block}
      {readiness_block}
      {build_collapsible(
          "Ver detalle completo de predicciÃ³n",
          prediction_detail,
          compact=True,
      )}
    </section>
    """

