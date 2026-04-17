from __future__ import annotations

import pandas as pd


ACTIVE_OPERATION_TYPES = {"Compra", "Venta"}
PASSIVE_OPERATION_TYPES = {"Pago de Dividendos", "Pago de Amortización", "Pago de AmortizaciÃ³n"}


def classify_operation_bucket(tipo: object) -> str:
    tipo_text = str(tipo or "").strip()
    if tipo_text in ACTIVE_OPERATION_TYPES:
        return "trading"
    if tipo_text in PASSIVE_OPERATION_TYPES:
        return "evento"
    return "otro"


def infer_operation_currency(simbolo: object) -> str:
    simbolo_text = str(simbolo or "").strip().upper()
    if simbolo_text.endswith("US$"):
        return "USD"
    return "ARS"


def normalize_symbol(value: object) -> str:
    return str(value or "").strip().upper()


def resolve_position_quantity(row: pd.Series | None) -> float | None:
    if row is None:
        return None
    for column in ("Cantidad_Real", "Cantidad"):
        value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
        if pd.notna(value):
            return float(value)
    return None


def prepare_portfolio_for_compare(df: pd.DataFrame | None) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame) or df.empty or "Ticker_IOL" not in df.columns:
        return pd.DataFrame()

    view = df.copy()
    view["Ticker_IOL"] = view["Ticker_IOL"].map(normalize_symbol)
    if "Tipo" in view.columns:
        view = view[view["Tipo"].fillna("").astype(str).str.lower() != "liquidez"].copy()
    view = view[view["Ticker_IOL"] != ""].copy()
    if view.empty:
        return view

    for column in ("Peso_%", "Valorizado_ARS", "Cantidad", "Cantidad_Real"):
        if column not in view.columns:
            view[column] = pd.NA

    view = view.sort_values("Valorizado_ARS", ascending=False, na_position="last")
    return view.drop_duplicates(subset=["Ticker_IOL"], keep="first").set_index("Ticker_IOL")


def build_position_transition_bundle(
    current_portfolio: pd.DataFrame | None,
    previous_portfolio: pd.DataFrame | None,
    *,
    recent_operations: pd.DataFrame | None = None,
    limit: int = 6,
) -> dict[str, object]:
    current_view = prepare_portfolio_for_compare(current_portfolio)
    previous_view = prepare_portfolio_for_compare(previous_portfolio)

    if current_view.empty and previous_view.empty:
        return {"items": [], "summary": pd.DataFrame()}

    latest_trade_by_symbol: dict[str, pd.Series] = {}
    if isinstance(recent_operations, pd.DataFrame) and not recent_operations.empty:
        trades = recent_operations[recent_operations["operation_bucket"] == "trading"].copy()
        if not trades.empty:
            trades["simbolo"] = trades["simbolo"].map(normalize_symbol)
            trades = trades.sort_values("fecha_evento", ascending=False, na_position="last")
            for _, row in trades.iterrows():
                symbol = row["simbolo"]
                if symbol and symbol not in latest_trade_by_symbol:
                    latest_trade_by_symbol[symbol] = row

    def operation_tail(symbol: str) -> str:
        trade = latest_trade_by_symbol.get(symbol)
        if trade is None:
            return ""
        tipo = str(trade.get("tipo", "")).strip().lower()
        fecha = pd.to_datetime(trade.get("fecha_evento"), errors="coerce")
        fecha_label = fecha.strftime("%Y-%m-%d %H:%M") if pd.notna(fecha) else "-"
        monto = pd.to_numeric(pd.Series([trade.get("monto_final")]), errors="coerce").iloc[0]
        currency = str(trade.get("operation_currency") or "ARS").strip().upper()
        if pd.isna(monto):
            return f" Se alinea con una {tipo} reciente del {fecha_label}."
        monto_label = f"USD {float(monto):,.2f}" if currency == "USD" else f"${float(monto):,.0f}"
        return f" Se alinea con una {tipo} reciente del {fecha_label} por {monto_label}."

    def fmt_qty(value: float | None) -> str:
        if value is None:
            return "-"
        if abs(value - round(value)) < 1e-9:
            return f"{int(round(value)):,}"
        return f"{value:,.2f}".rstrip("0").rstrip(".")

    items: list[dict[str, str]] = []
    summary_rows: list[dict[str, object]] = []
    all_symbols = sorted(set(current_view.index.tolist()) | set(previous_view.index.tolist()))

    for symbol in all_symbols:
        current_row = current_view.loc[symbol] if symbol in current_view.index else None
        previous_row = previous_view.loc[symbol] if symbol in previous_view.index else None
        current_qty = resolve_position_quantity(current_row)
        previous_qty = resolve_position_quantity(previous_row)

        if previous_row is None and current_row is not None:
            title = "Nueva posicion incorporada"
            badge = "Compra"
            detail = (
                f"{symbol} ahora forma parte de la cartera como {current_row.get('Tipo', '-')} / "
                f"{current_row.get('Bloque', '-')}. Peso actual {float(current_row.get('Peso_%', 0) or 0):.2f}%."
                f"{operation_tail(symbol)}"
            )
            change_kind = "alta_nueva"
        elif current_row is None and previous_row is not None:
            title = "Posicion salida de cartera"
            badge = "Venta"
            detail = (
                f"{symbol} estaba presente en la foto previa como {previous_row.get('Tipo', '-')} / "
                f"{previous_row.get('Bloque', '-')}, pero ya no aparece en la cartera actual."
                f"{operation_tail(symbol)}"
            )
            change_kind = "salida_total"
        else:
            if current_qty is None or previous_qty is None or abs(current_qty - previous_qty) < 1e-9:
                continue
            if current_qty > previous_qty:
                title = "Posicion ampliada"
                badge = "Compra"
                change_kind = "aumento_posicion"
            else:
                title = "Posicion recortada"
                badge = "Venta"
                change_kind = "reduccion_parcial"
            detail = (
                f"{symbol} paso de {fmt_qty(previous_qty)} a {fmt_qty(current_qty)} unidades. "
                f"Peso actual {float(current_row.get('Peso_%', 0) or 0):.2f}%."
                f"{operation_tail(symbol)}"
            )

        items.append(
            {
                "kicker": symbol,
                "title": title,
                "detail": detail,
                "badge": badge,
            }
        )
        summary_rows.append({"simbolo": symbol, "cambio": change_kind, "detalle": detail})
        if len(items) >= limit:
            break

    return {"items": items, "summary": pd.DataFrame(summary_rows)}


def normalize_iol_operations(operations: list[dict[str, object]] | None) -> pd.DataFrame:
    if not operations:
        return pd.DataFrame()

    df = pd.DataFrame(operations).copy()
    if df.empty:
        return df

    for col in ["fechaOrden", "fechaOperada"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        else:
            df[col] = pd.NaT

    numeric_cols = [
        "cantidad",
        "monto",
        "precio",
        "cantidadOperada",
        "precioOperado",
        "montoOperado",
    ]
    for col in numeric_cols:
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "tipo" not in df.columns:
        df["tipo"] = None
    if "simbolo" not in df.columns:
        df["simbolo"] = None
    if "estado" not in df.columns:
        df["estado"] = None

    df["operation_bucket"] = df["tipo"].map(classify_operation_bucket)
    df["fecha_evento"] = df["fechaOperada"].where(df["fechaOperada"].notna(), df["fechaOrden"])
    df["cantidad_final"] = df["cantidadOperada"].where(df["cantidadOperada"].notna(), df["cantidad"])
    df["precio_final"] = df["precioOperado"].where(df["precioOperado"].notna(), df["precio"])
    df["monto_final"] = df["montoOperado"].where(df["montoOperado"].notna(), df["monto"])
    df["simbolo"] = df["simbolo"].fillna("-").astype(str)
    df["estado"] = df["estado"].fillna("-").astype(str)
    df["tipo"] = df["tipo"].fillna("-").astype(str)
    df["mercado"] = df.get("mercado", pd.Series(index=df.index, dtype=object)).fillna("-").astype(str)
    df["plazo"] = df.get("plazo", pd.Series(index=df.index, dtype=object)).fillna("-").astype(str)
    df["operation_currency"] = df["simbolo"].map(infer_operation_currency)
    df = df.sort_values(["fecha_evento", "numero"], ascending=[False, False], na_position="last").reset_index(drop=True)
    return df


def build_operations_bundle(
    operations: list[dict[str, object]] | None,
    *,
    recent_limit: int = 12,
    highlight_limit: int = 4,
) -> dict[str, object]:
    df = normalize_iol_operations(operations)
    if df.empty:
        return {
            "recent_operations": pd.DataFrame(),
            "recent_trades": pd.DataFrame(),
            "recent_events": pd.DataFrame(),
            "symbol_summary": pd.DataFrame(),
            "position_transitions": {"items": [], "summary": pd.DataFrame()},
            "stats": {
                "total": 0,
                "trading": 0,
                "events": 0,
                "completed": 0,
            },
            "highlights": {
                "trades": [],
                "events": [],
            },
        }

    recent_operations = df.head(recent_limit).copy()
    recent_trades = recent_operations[recent_operations["operation_bucket"] == "trading"].copy()
    recent_events = recent_operations[recent_operations["operation_bucket"] == "evento"].copy()

    symbol_summary = (
        recent_operations[recent_operations["operation_bucket"] == "trading"]
        .groupby(["simbolo", "tipo"], dropna=False)
        .agg(
            operaciones=("numero", "count"),
            ultima_fecha=("fecha_evento", "max"),
            monto_total=("monto_final", "sum"),
            cantidad_total=("cantidad_final", "sum"),
        )
        .reset_index()
        .sort_values(["ultima_fecha", "monto_total"], ascending=[False, False], na_position="last")
    )

    def _highlight_items(source: pd.DataFrame) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        for _, row in source.head(highlight_limit).iterrows():
            items.append(
                {
                    "simbolo": row.get("simbolo", "-"),
                    "tipo": row.get("tipo", "-"),
                    "fecha": row.get("fecha_evento"),
                    "monto": row.get("monto_final"),
                    "currency": row.get("operation_currency", "ARS"),
                    "cantidad": row.get("cantidad_final"),
                    "estado": row.get("estado", "-"),
                    "plazo": row.get("plazo", "-"),
                }
            )
        return items

    return {
        "recent_operations": recent_operations,
        "recent_trades": recent_trades,
        "recent_events": recent_events,
        "symbol_summary": symbol_summary,
        "position_transitions": {"items": [], "summary": pd.DataFrame()},
        "stats": {
            "total": int(len(recent_operations)),
            "trading": int((recent_operations["operation_bucket"] == "trading").sum()),
            "events": int((recent_operations["operation_bucket"] == "evento").sum()),
            "completed": int((recent_operations["estado"].str.lower() == "terminada").sum()),
        },
        "highlights": {
            "trades": _highlight_items(recent_trades),
            "events": _highlight_items(recent_events),
        },
    }
