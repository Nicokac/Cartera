from __future__ import annotations

import logging

import pandas as pd


logger = logging.getLogger(__name__)

ACTIVE_OPERATION_TYPES = {"Compra", "Venta"}
PASSIVE_OPERATION_TYPES = {"Pago de Dividendos", "Pago de Amortización"}

_MOJIBAKE_FIXES = {
    "AmortizaciÃ³n": "Amortización",
    "AmortizaciÃƒÂ³n": "Amortización",
    "AcciÃ³n": "Acción",
    "sÃ­": "sí",
}


def normalize_text(value: object) -> str:
    text = str(value or "").strip()
    for broken, fixed in _MOJIBAKE_FIXES.items():
        text = text.replace(broken, fixed)
    return text


def classify_operation_bucket(tipo: object) -> str:
    tipo_text = normalize_text(tipo)
    if tipo_text in ACTIVE_OPERATION_TYPES:
        return "trading"
    if tipo_text in PASSIVE_OPERATION_TYPES:
        return "evento"
    return "otro"


def infer_operation_currency(simbolo: object) -> str:
    simbolo_text = normalize_text(simbolo).upper()
    if simbolo_text.endswith("US$"):
        return "USD"
    return "ARS"


def normalize_symbol(value: object) -> str:
    return normalize_text(value).upper()


def resolve_position_quantity(row: pd.Series | None) -> float | None:
    if row is None:
        return None
    for column in ("Cantidad_Real", "Cantidad"):
        value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
        if pd.notna(value):
            return float(value)
    return None


def infer_trade_vn_factor(
    *,
    quantity: object,
    price: object,
    amount: object,
    default: float = 1.0,
) -> float:
    qty = pd.to_numeric(pd.Series([quantity]), errors="coerce").iloc[0]
    px = pd.to_numeric(pd.Series([price]), errors="coerce").iloc[0]
    amt = pd.to_numeric(pd.Series([amount]), errors="coerce").iloc[0]
    if pd.isna(qty) or pd.isna(px) or pd.isna(amt) or qty <= 0 or px <= 0 or amt <= 0:
        return float(default)

    implied = float(qty * px / amt)
    candidates = [1.0, 10.0, 100.0, 1000.0]
    nearest = min(candidates, key=lambda candidate: abs(candidate - implied))
    if nearest == 1.0:
        return 1.0

    # Bonds and letras commonly settle with VN scaling; allow moderate noise from
    # fees, partial fills, or the broker using a slightly different monetary base.
    rel_error = abs(implied - nearest) / nearest
    return nearest if rel_error <= 0.3 else float(default)


def build_pending_trade_portfolio_rows(
    recent_trades: pd.DataFrame | None,
    *,
    current_portfolio: pd.DataFrame | None = None,
    prices_iol: dict[str, float] | None = None,
    vn_factor_map: dict[str, float | int] | None = None,
    mep_real: float | None = None,
    total_portfolio_ars: float | None = None,
) -> pd.DataFrame:
    if not isinstance(recent_trades, pd.DataFrame) or recent_trades.empty:
        return pd.DataFrame()

    current_view = prepare_portfolio_for_compare(current_portfolio)
    current_symbols = set(current_view.index.tolist())
    prices_iol = {str(k).strip().upper(): float(v) for k, v in (prices_iol or {}).items()}
    vn_factor_map = {str(k).strip().upper(): float(v) for k, v in (vn_factor_map or {}).items()}

    rows: list[dict[str, object]] = []
    seen_symbols: set[str] = set()

    trades = recent_trades.copy()
    if "simbolo" not in trades.columns:
        return pd.DataFrame()
    trades["simbolo"] = trades["simbolo"].map(normalize_symbol)

    for _, row in trades.iterrows():
        symbol = str(row.get("simbolo", "")).strip().upper()
        if not symbol or symbol in current_symbols or symbol in seen_symbols:
            continue

        quantity = pd.to_numeric(pd.Series([row.get("cantidad_final")]), errors="coerce").iloc[0]
        trade_price = pd.to_numeric(pd.Series([row.get("precio_final")]), errors="coerce").iloc[0]
        trade_amount = pd.to_numeric(pd.Series([row.get("monto_final")]), errors="coerce").iloc[0]
        current_price = prices_iol.get(symbol)
        vn_factor = vn_factor_map.get(symbol)
        if vn_factor is None:
            vn_factor = infer_trade_vn_factor(quantity=quantity, price=trade_price, amount=trade_amount)
        quantity_real = quantity / vn_factor if pd.notna(quantity) and vn_factor not in (0, None) else pd.NA

        valuation_price = current_price if current_price is not None else trade_price
        if pd.notna(quantity_real) and valuation_price is not None and pd.notna(valuation_price):
            valorizado = float(quantity_real) * float(valuation_price)
        else:
            valorizado = float(trade_amount) if pd.notna(trade_amount) else pd.NA

        if pd.notna(valorizado) and mep_real:
            valor_usd = float(valorizado) / float(mep_real)
        else:
            valor_usd = pd.NA

        if (
            pd.notna(quantity_real)
            and pd.notna(trade_price)
            and valuation_price is not None
            and pd.notna(valuation_price)
        ):
            ganancia = float(quantity_real) * (float(valuation_price) - float(trade_price))
        else:
            ganancia = pd.NA

        peso = pd.NA
        if pd.notna(valorizado) and total_portfolio_ars and total_portfolio_ars > 0:
            peso = (float(valorizado) / float(total_portfolio_ars)) * 100.0

        rows.append(
            {
                "Ticker_IOL": symbol,
                "Tipo": "Pendiente",
                "Bloque": "Pendiente de consolidacion",
                "Cantidad": quantity,
                "Cantidad_Real": quantity_real,
                "VN_Factor": vn_factor,
                "Precio_ARS": valuation_price if valuation_price is not None else pd.NA,
                "Valorizado_ARS": valorizado,
                "Valor_USD": valor_usd,
                "Ganancia_ARS": ganancia,
                "Peso_%": peso,
                "Fuente": "Operaciones recientes",
            }
        )
        seen_symbols.add(symbol)

    return pd.DataFrame(rows)


def prepare_portfolio_for_compare(df: pd.DataFrame | None) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame) or df.empty or "Ticker_IOL" not in df.columns:
        return pd.DataFrame()

    view = df.copy()
    view["Ticker_IOL"] = view["Ticker_IOL"].map(normalize_symbol)
    if "Tipo" in view.columns:
        view["Tipo"] = view["Tipo"].map(normalize_text)
        view = view[view["Tipo"].fillna("").astype(str).str.lower() != "liquidez"].copy()
    if "Bloque" in view.columns:
        view["Bloque"] = view["Bloque"].map(normalize_text)
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
            trade_rows = list(trades.itertuples(index=False))
            trade_columns = list(trades.columns)
            for row in trade_rows:
                row_series = pd.Series(row, index=trade_columns)
                symbol = row_series.get("simbolo", "")
                if symbol and symbol not in latest_trade_by_symbol:
                    latest_trade_by_symbol[symbol] = row_series

    def operation_tail(symbol: str) -> str:
        trade = latest_trade_by_symbol.get(symbol)
        if trade is None:
            return ""
        tipo = normalize_text(trade.get("tipo", "")).lower()
        fecha = pd.to_datetime(trade.get("fecha_evento"), errors="coerce")
        fecha_label = fecha.strftime("%Y-%m-%d %H:%M") if pd.notna(fecha) else "-"
        monto = pd.to_numeric(pd.Series([trade.get("monto_final")]), errors="coerce").iloc[0]
        currency = normalize_text(trade.get("operation_currency") or "ARS").upper()
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

    # Build unfiltered symbol set from previous portfolio to detect reclassifications.
    # prepare_portfolio_for_compare drops liquidez rows, so a ticker that moved from
    # liquidez→FCI would appear as previous_row=None even though it already existed.
    previous_all_symbols: set[str] = set()
    if isinstance(previous_portfolio, pd.DataFrame) and not previous_portfolio.empty and "Ticker_IOL" in previous_portfolio.columns:
        previous_all_symbols = set(
            previous_portfolio["Ticker_IOL"].map(normalize_symbol).dropna()
        )

    items: list[dict[str, str]] = []
    summary_rows: list[dict[str, object]] = []
    all_symbols = sorted(set(current_view.index.tolist()) | set(previous_view.index.tolist()))

    for symbol in all_symbols:
        current_row = current_view.loc[symbol] if symbol in current_view.index else None
        previous_row = previous_view.loc[symbol] if symbol in previous_view.index else None
        current_qty = resolve_position_quantity(current_row)
        previous_qty = resolve_position_quantity(previous_row)

        if previous_row is None and current_row is not None:
            if symbol in previous_all_symbols:
                title = "Posicion reclasificada"
                badge = "Reclasificacion"
                detail = (
                    f"{symbol} ya formaba parte de la cartera y ahora se clasifica como "
                    f"{current_row.get('Tipo', '-')} / {current_row.get('Bloque', '-')}. "
                    f"Peso actual {float(current_row.get('Peso_%', 0) or 0):.2f}%."
                    f"{operation_tail(symbol)}"
                )
                change_kind = "reclasificacion"
            else:
                title = "Nueva posicion incorporada"
                badge = "Compra"
                detail = (
                    f"{symbol} se incorpora por primera vez como "
                    f"{current_row.get('Tipo', '-')} / {current_row.get('Bloque', '-')}. "
                    f"Peso actual {float(current_row.get('Peso_%', 0) or 0):.2f}%."
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
        "numero",
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

    df["tipo"] = df["tipo"].map(normalize_text).replace("", "-")
    df["simbolo"] = df["simbolo"].map(normalize_text).replace("", "-")
    df["estado"] = df["estado"].map(normalize_text).replace("", "-")
    df["mercado"] = df.get("mercado", pd.Series(index=df.index, dtype=object)).map(normalize_text).replace("", "-")
    df["plazo"] = df.get("plazo", pd.Series(index=df.index, dtype=object)).map(normalize_text).replace("", "-")
    df["operation_bucket"] = df["tipo"].map(classify_operation_bucket)
    df["fecha_evento"] = df["fechaOperada"].where(df["fechaOperada"].notna(), df["fechaOrden"])
    df["cantidad_final"] = df["cantidadOperada"].where(df["cantidadOperada"].notna(), df["cantidad"])
    df["precio_final"] = df["precioOperado"].where(df["precioOperado"].notna(), df["precio"])
    df["monto_final"] = df["montoOperado"].where(df["montoOperado"].notna(), df["monto"])
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

    logger.info(
        "Operations bundle built: total=%s trading=%s events=%s",
        len(df),
        int((df["operation_bucket"] == "trading").sum()),
        int((df["operation_bucket"] == "evento").sum()),
    )

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
        for row in source.head(highlight_limit).itertuples(index=False):
            row_series = pd.Series(row, index=source.columns)
            items.append(
                {
                    "simbolo": row_series.get("simbolo", "-"),
                    "tipo": row_series.get("tipo", "-"),
                    "fecha": row_series.get("fecha_evento"),
                    "monto": row_series.get("monto_final"),
                    "currency": row_series.get("operation_currency", "ARS"),
                    "cantidad": row_series.get("cantidad_final"),
                    "estado": row_series.get("estado", "-"),
                    "plazo": row_series.get("plazo", "-"),
                }
            )
        return items

    return {
        "recent_operations": recent_operations,
        "recent_trades": recent_trades,
        "recent_events": recent_events,
        "symbol_summary": symbol_summary,
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


def enrich_operations_bundle(
    operations_bundle: dict[str, object],
    *,
    current_portfolio: pd.DataFrame | None = None,
    previous_portfolio: pd.DataFrame | None = None,
    previous_snapshot_date: str | None = None,
    transition_limit: int = 6,
) -> dict[str, object]:
    bundle = dict(operations_bundle or {})
    recent_operations = bundle.get("recent_operations", pd.DataFrame())
    bundle["position_transitions"] = build_position_transition_bundle(
        current_portfolio,
        previous_portfolio,
        recent_operations=recent_operations if isinstance(recent_operations, pd.DataFrame) else None,
        limit=transition_limit,
    )
    bundle["previous_snapshot_date"] = previous_snapshot_date
    return bundle
