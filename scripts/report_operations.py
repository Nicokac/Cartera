from __future__ import annotations

import html

import pandas as pd

from decision.action_constants import ACTION_REDUCIR, ACTION_REFUERZO
from report_primitives import (
    build_collapsible,
    build_focus_list,
    build_table,
    ensure_table_columns,
    fmt_ars,
    fmt_count_label,
    fmt_datetime_short,
    fmt_label,
    fmt_money_by_currency,
    fmt_pct,
    fmt_quantity,
)


def build_executive_summary(
    *,
    action_counts: dict[object, object],
    decision_memory: dict[str, object],
    changed_actions: list[dict[str, str]],
    operations_bundle: dict[str, object],
    asignacion_final: pd.DataFrame,
    current_tickers: set[str],
) -> str:
    summary_parts: list[str] = []

    if changed_actions:
        tickers = [str(item.get("kicker", "")).strip() for item in changed_actions[:3] if str(item.get("kicker", "")).strip()]
        if tickers:
            summary_parts.append(f"Cambios de señal en {', '.join(tickers)}")

    transition_summary = operations_bundle.get("position_transitions", {}) or {}
    transition_df = transition_summary.get("summary", pd.DataFrame())
    if isinstance(transition_df, pd.DataFrame) and not transition_df.empty:
        visibles = transition_df["simbolo"].dropna().astype(str).head(3).tolist()
        if visibles:
            summary_parts.append(f"Movimientos ya visibles en cartera: {', '.join(visibles)}")

    recent_trades = operations_bundle.get("recent_trades", pd.DataFrame())
    unresolved: list[str] = []
    if isinstance(recent_trades, pd.DataFrame) and not recent_trades.empty:
        for simbolo in recent_trades.get("simbolo", pd.Series(dtype=object)).dropna().astype(str).tolist():
            symbol_upper = simbolo.strip().upper()
            if symbol_upper and symbol_upper not in current_tickers and symbol_upper not in unresolved:
                unresolved.append(symbol_upper)
    if unresolved:
        summary_parts.append(f"Pendiente de consolidación en cartera: {', '.join(unresolved[:3])}")

    if isinstance(asignacion_final, pd.DataFrame) and not asignacion_final.empty:
        sizing_names = asignacion_final["Ticker_IOL"].dropna().astype(str).head(3).tolist()
        if sizing_names:
            summary_parts.append(f"Sizing activo en {', '.join(sizing_names)}")

    if summary_parts:
        return ". ".join(summary_parts) + "."

    return (
        f"{fmt_count_label(action_counts.get(ACTION_REFUERZO, 0), 'refuerzo')}, "
        f"{fmt_count_label(action_counts.get(ACTION_REDUCIR, 0), 'reducción', 'reducciones')}, "
        f"{fmt_count_label(decision_memory.get('senales_nuevas', 0), 'cambio material', 'cambios materiales')} y "
        f"sizing activo en {', '.join(asignacion_final['Ticker_IOL'].head(3).astype(str).tolist()) if isinstance(asignacion_final, pd.DataFrame) and not asignacion_final.empty else 'sin asignación'}."
    )


def build_operations_explanations(
    recent_operations: pd.DataFrame,
    *,
    current_portfolio: pd.DataFrame,
    skip_symbols: set[str] | None = None,
    fallback_window_days: int = 3,
    limit: int = 6,
) -> list[dict[str, str]]:
    if not isinstance(recent_operations, pd.DataFrame) or recent_operations.empty:
        return []

    portfolio_view = current_portfolio.copy() if isinstance(current_portfolio, pd.DataFrame) else pd.DataFrame()
    if not portfolio_view.empty:
        portfolio_view["Ticker_IOL"] = portfolio_view["Ticker_IOL"].astype(str).str.strip().str.upper()
        portfolio_view = portfolio_view.drop_duplicates(subset=["Ticker_IOL"], keep="first").set_index("Ticker_IOL")

    items: list[dict[str, str]] = []
    seen_keys: set[tuple[str, str]] = set()
    skip_symbols = {str(symbol).strip().upper() for symbol in (skip_symbols or set()) if str(symbol).strip()}
    latest_event_ts = pd.to_datetime(recent_operations.get("fecha_evento"), errors="coerce").max()
    fallback_cutoff_ts = (
        latest_event_ts - pd.Timedelta(days=fallback_window_days)
        if pd.notna(latest_event_ts)
        else pd.NaT
    )

    passive_types = {"Pago de Dividendos", "Pago de Amortización"}

    for _, row in recent_operations.iterrows():
        symbol = str(row.get("simbolo", "-")).strip().upper()
        if not symbol or symbol == "-":
            continue
        if symbol in skip_symbols:
            continue

        bucket = str(row.get("operation_bucket", "")).strip().lower()
        if not bucket:
            tipo_text = str(row.get("tipo", "")).strip()
            if tipo_text in {"Compra", "Venta"}:
                bucket = "trading"
            elif tipo_text in passive_types:
                bucket = "evento"
            else:
                bucket = "otro"
        unique_key = (bucket, symbol)
        if unique_key in seen_keys:
            continue
        seen_keys.add(unique_key)

        tipo_operacion = str(row.get("tipo", "-"))
        event_ts = pd.to_datetime(row.get("fecha_evento"), errors="coerce")
        fecha = fmt_datetime_short(event_ts)
        monto = fmt_money_by_currency(row.get("monto_final"), row.get("operation_currency"))

        if bucket == "trading":
            if symbol in portfolio_view.index:
                if pd.notna(fallback_cutoff_ts) and pd.notna(event_ts) and event_ts < fallback_cutoff_ts:
                    continue
                current_row = portfolio_view.loc[symbol]
                tipo_actual = fmt_label(current_row.get("Tipo"))
                bloque_actual = fmt_label(current_row.get("Bloque"))
                peso_actual = fmt_pct(current_row.get("Peso_%"))
                if tipo_operacion == "Compra":
                    title = f"Compra reciente ya reflejada en cartera | {fecha}"
                else:
                    title = f"Venta reciente sobre una posicion que sigue abierta | {fecha}"
                detail = f"{symbol} hoy sigue en cartera como {tipo_actual} / {bloque_actual}. Peso actual {peso_actual}."
                badge = tipo_operacion
            else:
                title = f"Movimiento reciente aun no reflejado en cartera | {fecha}"
                detail = f"{symbol} tuvo una {tipo_operacion.lower()} reciente, pero todavia no figura en /portafolio actual."
                badge = tipo_operacion
                items.append(
                    {
                        "kicker": symbol,
                        "title": title,
                        "detail": detail,
                        "badge": badge,
                        "extra_class": "item-pending",
                    }
                )
                continue
            items.append(
                {
                    "kicker": symbol,
                    "title": title,
                    "detail": detail,
                    "badge": badge,
                }
            )
        elif bucket == "evento":
            if pd.notna(fallback_cutoff_ts) and pd.notna(event_ts) and event_ts < fallback_cutoff_ts:
                continue
            detail = f"Se acredito {tipo_operacion.lower()} de {symbol}. Monto informado {monto}."
            items.append(
                {
                    "kicker": symbol,
                    "title": f"Cobro o acreditacion reciente | {fecha}",
                    "detail": detail,
                }
            )

        if len(items) >= limit:
            break

    return items


def build_operations_summary(
    operations_bundle: dict[str, object],
    *,
    current_tickers: set[str] | None = None,
    current_portfolio: pd.DataFrame | None = None,
) -> str:
    recent_trades = operations_bundle.get("recent_trades", pd.DataFrame())
    recent_events = operations_bundle.get("recent_events", pd.DataFrame())
    recent_operations = operations_bundle.get("recent_operations", pd.DataFrame())
    symbol_summary = operations_bundle.get("symbol_summary", pd.DataFrame())
    position_transitions = operations_bundle.get("position_transitions", {}) or {}
    transition_items = position_transitions.get("items", []) or []
    transition_summary = position_transitions.get("summary", pd.DataFrame())
    previous_snapshot_date = operations_bundle.get("previous_snapshot_date")
    stats = operations_bundle.get("stats", {}) or {}
    current_tickers = {str(ticker).strip().upper() for ticker in (current_tickers or set()) if str(ticker).strip()}

    trade_items = []
    if isinstance(recent_trades, pd.DataFrame) and not recent_trades.empty:
        for _, row in recent_trades.head(4).iterrows():
            trade_items.append(
                {
                    "kicker": str(row.get("simbolo", "-")),
                    "title": f"{fmt_label(row.get('tipo'))} | {fmt_datetime_short(row.get('fecha_evento'))}",
                    "detail": f"{fmt_money_by_currency(row.get('monto_final'), row.get('operation_currency'))} | Cantidad {fmt_quantity(row.get('cantidad_final'))}",
                    "badge": row.get("tipo"),
                }
            )

    event_items = []
    if isinstance(recent_events, pd.DataFrame) and not recent_events.empty:
        for _, row in recent_events.head(4).iterrows():
            event_items.append(
                {
                    "kicker": str(row.get("simbolo", "-")),
                    "title": f"{fmt_label(row.get('tipo'))} | {fmt_datetime_short(row.get('fecha_evento'))}",
                    "detail": f"Monto {fmt_money_by_currency(row.get('monto_final'), row.get('operation_currency'))} | Estado {fmt_label(row.get('estado'))}",
                }
            )

    summary_table = ""
    if isinstance(symbol_summary, pd.DataFrame) and not symbol_summary.empty:
        summary_table = build_collapsible(
            "Ver resumen por símbolo",
            build_table(
                ensure_table_columns(
                    symbol_summary,
                    ["simbolo", "tipo", "operaciones", "ultima_fecha", "monto_total", "cantidad_total"],
                ),
                formatters={
                    "ultima_fecha": fmt_datetime_short,
                    "monto_total": fmt_ars,
                    "cantidad_total": fmt_quantity,
                },
            ),
            compact=True,
        )

    unresolved_symbols: list[str] = []
    if isinstance(recent_trades, pd.DataFrame) and not recent_trades.empty:
        for simbolo in recent_trades["simbolo"].dropna().astype(str).tolist():
            symbol_upper = simbolo.strip().upper()
            if symbol_upper and symbol_upper not in current_tickers and symbol_upper not in unresolved_symbols:
                unresolved_symbols.append(symbol_upper)

    unresolved_note = ""
    if unresolved_symbols:
        joined = ", ".join(unresolved_symbols)
        unresolved_note = (
            '<div class="meta">'
            f'<span>Operaciones recientes fuera de cartera actual: <strong>{html.escape(joined)}</strong></span>'
            '<span>Esto suele indicar una operacion ejecutada que todavia no se refleja en <strong>/portafolio</strong> o una especie transitoria no consolidada en la foto de tenencias.</span>'
            "</div>"
        )

    explanations_html = build_focus_list(
        transition_items
        + build_operations_explanations(
            recent_operations,
            current_portfolio=current_portfolio if isinstance(current_portfolio, pd.DataFrame) else pd.DataFrame(),
            skip_symbols={item.get("kicker", "") for item in transition_items},
        ),
        empty_message="Sin lectura operacional adicional para esta ventana.",
        tone="neutral",
    )

    transition_table = ""
    if isinstance(transition_summary, pd.DataFrame) and not transition_summary.empty:
        transition_table = build_collapsible(
            "Ver cambios contra snapshot previo",
            build_table(
                ensure_table_columns(
                    transition_summary,
                    ["simbolo", "cambio", "detalle"],
                ),
            ),
            compact=True,
        )

    recent_operations_view = ensure_table_columns(
        recent_operations,
        [
            "numero",
            "fecha_evento",
            "tipo",
            "estado",
            "mercado",
            "simbolo",
            "operation_currency",
            "cantidad_final",
            "precio_final",
            "monto_final",
            "plazo",
        ],
    ).copy()
    if not recent_operations_view.empty:
        recent_operations_view["precio_final_label"] = recent_operations_view.apply(
            lambda row: fmt_money_by_currency(row.get("precio_final"), row.get("operation_currency")),
            axis=1,
        )
        recent_operations_view["monto_final_label"] = recent_operations_view.apply(
            lambda row: fmt_money_by_currency(row.get("monto_final"), row.get("operation_currency")),
            axis=1,
        )
        recent_operations_view = recent_operations_view.rename(
            columns={
                "operation_currency": "Moneda",
                "cantidad_final": "Cantidad final",
                "precio_final_label": "Precio final",
                "monto_final_label": "Monto final",
            }
        )

    return f"""
    <section class="panel" id="operaciones">
      <h2>Operaciones recientes</h2>
      <div class="meta">
        <span>Total: <strong>{int(stats.get('total', 0))}</strong></span>
        <span>Trading: <strong>{int(stats.get('trading', 0))}</strong></span>
        <span>Eventos: <strong>{int(stats.get('events', 0))}</strong></span>
        <span>Terminadas: <strong>{int(stats.get('completed', 0))}</strong></span>
        <span>Snapshot previo: <strong>{html.escape(str(previous_snapshot_date or '-'))}</strong></span>
      </div>
      {unresolved_note}
      <h3>Lectura operacional</h3>
      {explanations_html}
      <div class="focus-columns">
        <div>
          <h3>Compras y ventas recientes</h3>
          {build_focus_list(trade_items, empty_message='Sin operaciones activas recientes.', tone='buy')}
        </div>
        <div>
          <h3>Dividendos y amortizaciones</h3>
          {build_focus_list(event_items, empty_message='Sin eventos pasivos recientes.', tone='neutral')}
        </div>
      </div>
      {summary_table}
      {transition_table}
      {build_collapsible(
          "Ver tabla completa de operaciones",
          build_table(
              ensure_table_columns(
                  recent_operations_view,
                  [
                      "numero",
                      "fecha_evento",
                      "tipo",
                      "estado",
                      "mercado",
                      "simbolo",
                      "Moneda",
                      "Cantidad final",
                      "Precio final",
                      "Monto final",
                      "plazo",
                  ],
              ),
              formatters={
                  "fecha_evento": fmt_datetime_short,
                  "Moneda": fmt_label,
                  "Precio final": fmt_label,
                  "Monto final": fmt_label,
                  "Cantidad final": fmt_quantity,
              },
          ),
          compact=True,
      )}
    </section>
    """
