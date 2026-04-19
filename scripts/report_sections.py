from __future__ import annotations

import pandas as pd

from report_primitives import (
    build_collapsible,
    build_focus_list,
    build_table,
    ensure_table_columns,
    fmt_pct,
    fmt_score,
    safe_int,
    truncate_text,
)


def build_prediction_section(prediction_bundle: dict[str, object]) -> str:
    predictions = prediction_bundle.get("predictions", pd.DataFrame())
    if not isinstance(predictions, pd.DataFrame) or predictions.empty:
        return ""

    work = predictions.copy()
    summary = prediction_bundle.get("summary", {}) or {}
    config = prediction_bundle.get("config", {}) or {}

    def _votes_label(value: object) -> str:
        votes = value if isinstance(value, dict) else {}
        parts = []
        for signal_name, vote in votes.items():
            try:
                numeric_vote = int(vote)
            except Exception:
                numeric_vote = 0
            sign = f"+{numeric_vote}" if numeric_vote > 0 else str(numeric_vote)
            parts.append(f"{signal_name}:{sign}")
        return " | ".join(parts) if parts else "-"

    def _focus_items(source: pd.DataFrame, *, tone: str) -> str:
        items: list[dict[str, str]] = []
        for _, row in source.head(3).iterrows():
            items.append(
                {
                    "kicker": str(row.get("ticker", "-")),
                    "title": f"Confianza {fmt_pct(float(row.get('confidence', 0.0)) * 100.0)}",
                    "detail": truncate_text(_votes_label(row.get("signal_votes")), 180),
                    "badge": str(row.get("direction", "")).upper(),
                }
            )
        return build_focus_list(items, empty_message="Sin nombres para mostrar.", tone=tone)

    bullish = work.loc[work["direction"].astype(str) == "up"].sort_values("confidence", ascending=False)
    bearish = work.loc[work["direction"].astype(str) == "down"].sort_values("confidence", ascending=False)
    neutral = work.loc[work["direction"].astype(str) == "neutral"].sort_values("confidence", ascending=False)
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
      <h2>Prediccion</h2>
      <div class="meta">
        <span>Total: <strong>{int(summary.get('total', len(work)))}</strong></span>
        <span>Suba: <strong>{int(summary.get('up', 0))}</strong></span>
        <span>Baja: <strong>{int(summary.get('down', 0))}</strong></span>
        <span>Neutral: <strong>{int(summary.get('neutral', 0))}</strong></span>
        <span>Confianza media: <strong>{fmt_pct(float(summary.get('mean_confidence', 0.0)) * 100.0)}</strong></span>
        <span>Horizonte: <strong>{safe_int(config.get('horizon_days'))} ruedas</strong></span>
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
          build_table(
              predictions_view,
              formatters={
                  "confidence": lambda value: fmt_pct(float(value) * 100.0) if pd.notna(value) else "-",
                  "consensus_raw": lambda value: "-" if pd.isna(value) else f"{float(value):+.3f}",
                  "score_unificado": fmt_score,
                  "signal_votes": _votes_label,
              },
          ),
          compact=True,
      )}
    </section>
    """
