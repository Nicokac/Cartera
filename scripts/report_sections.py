from __future__ import annotations

import pandas as pd

from report_primitives import (
    build_collapsible,
    build_focus_list,
    build_table,
    build_technical_table,
    ensure_table_columns,
    esc_text,
    fmt_ars,
    fmt_pct,
    fmt_score,
    fmt_usd,
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


def build_summary_section(
    *,
    kpis: dict[str, object],
    resumen_tipos: pd.DataFrame,
    family_summary: pd.DataFrame,
    finviz_fund_covered: int,
    finviz_total: int,
    finviz_ratings_covered: int,
) -> str:
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
    """


def build_sizing_section(sizing_bundle: dict[str, object], asignacion_final: pd.DataFrame) -> str:
    return f"""
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
