from __future__ import annotations

from decimal import Decimal, InvalidOperation
import logging
from typing import Any

import numpy as np
import pandas as pd

from common.numeric import positive_float_or_none


logger = logging.getLogger(__name__)

MASTER_PORTFOLIO_COLUMNS = [
    "Ticker_IOL",
    "Ticker_Finviz",
    "Ticker_API",
    "Descripcion",
    "Bloque",
    "Tipo",
    "Moneda",
    "Cantidad",
    "Cantidad_Real",
    "VN_Factor",
    "Precio_ARS",
    "PPC_ARS",
    "Ratio",
    "Valorizado_ARS",
    "Valor_USD",
    "Ganancia_ARS",
    "Peso_%",
    "Es_Liquidez",
]

_DECIMAL_ZERO = Decimal("0")


def _to_decimal(value: object) -> Decimal | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    try:
        return Decimal(str(numeric))
    except (InvalidOperation, ValueError):
        return None


def _decimal_to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _money_mul(left: object, right: object) -> float | None:
    left_dec = _to_decimal(left)
    right_dec = _to_decimal(right)
    if left_dec is None or right_dec is None:
        return None
    return _decimal_to_float(left_dec * right_dec)


def _money_sub(left: object, right: object) -> Decimal | None:
    left_dec = _to_decimal(left)
    right_dec = _to_decimal(right)
    if left_dec is None or right_dec is None:
        return None
    return left_dec - right_dec


def _money_div(left: object, right: object) -> float | None:
    left_dec = _to_decimal(left)
    right_dec = _to_decimal(right)
    if left_dec is None or right_dec is None or right_dec == _DECIMAL_ZERO:
        return None
    return _decimal_to_float(left_dec / right_dec)


def _compute_weight_pct(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    total = float(values.sum(skipna=True))
    if not np.isfinite(total) or abs(total) < 1e-12:
        return pd.Series(0.0, index=series.index, dtype=float)
    return (values.fillna(0) / total * 100).round(2)


def build_cedears_df(
    portafolio: list[tuple],
    precios_iol: dict[str, float],
    *,
    ratios: dict[str, float | int],
) -> pd.DataFrame:
    registros = []
    for ticker_iol, ticker_finviz, bloque, cantidad, ppc_ars in portafolio:
        precio = precios_iol.get(ticker_iol)
        valorizado = _money_mul(cantidad, precio)
        delta_precio = _money_sub(precio, ppc_ars)
        ganancia = _decimal_to_float(delta_precio * _to_decimal(cantidad)) if delta_precio is not None else None
        registros.append(
            {
                "Ticker_IOL": ticker_iol,
                "Ticker_Finviz": ticker_finviz,
                "Bloque": bloque,
                "Tipo": "CEDEAR",
                "Cantidad": cantidad,
                "Precio_ARS": precio,
                "PPC_ARS": ppc_ars,
                "Valorizado_ARS": valorizado,
                "Ganancia_ARS": ganancia,
            }
        )

    df = pd.DataFrame(registros)
    if df.empty:
        logger.info("Valuation skipped CEDEAR build: empty portfolio slice")
        return df
    df["Ratio"] = df["Ticker_IOL"].map(ratios)
    df["Peso_%"] = _compute_weight_pct(df["Valorizado_ARS"])
    logger.info("Valuation built CEDEAR frame: rows=%s priced=%s", len(df), int(df["Precio_ARS"].notna().sum()))
    return df


def build_local_df(acciones_locales: list[tuple], precios_iol: dict[str, float]) -> pd.DataFrame:
    registros = []
    for ticker_iol, ticker_api, bloque, cantidad, ppc_ars in acciones_locales:
        precio = precios_iol.get(ticker_iol)
        valorizado = _money_mul(cantidad, precio)
        delta_precio = _money_sub(precio, ppc_ars)
        ganancia = _decimal_to_float(delta_precio * _to_decimal(cantidad)) if delta_precio is not None else None
        registros.append(
            {
                "Ticker_IOL": ticker_iol,
                "Ticker_API": ticker_api,
                "Bloque": bloque,
                "Tipo": "Acción Local",
                "Cantidad": cantidad,
                "Precio_ARS": precio,
                "PPC_ARS": ppc_ars,
                "Ratio": None,
                "Ticker_Finviz": None,
                "Valorizado_ARS": valorizado,
                "Ganancia_ARS": ganancia,
            }
        )

    df_local = pd.DataFrame(registros)
    if df_local.empty:
        logger.info("Valuation skipped local equity build: empty portfolio slice")
        return df_local
    df_local["Peso_%"] = _compute_weight_pct(df_local["Valorizado_ARS"])
    logger.info("Valuation built local equity frame: rows=%s priced=%s", len(df_local), int(df_local["Precio_ARS"].notna().sum()))
    return df_local


def build_bonos_df(bonos: list[tuple], precios_iol: dict[str, float]) -> pd.DataFrame:
    registros = []
    for ticker_iol, bloque, cantidad, ppc_ars, vn_factor in bonos:
        precio = precios_iol.get(ticker_iol)
        cantidad_real = cantidad / vn_factor
        valorizado = _money_mul(cantidad_real, precio)
        costo = _money_mul(cantidad_real, ppc_ars)
        ganancia = _decimal_to_float(_money_sub(valorizado, costo)) if valorizado is not None else None
        registros.append(
            {
                "Ticker_IOL": ticker_iol,
                "Bloque": bloque,
                "Tipo": "Bono",
                "Cantidad": cantidad,
                "Cantidad_Real": cantidad_real,
                "VN_Factor": vn_factor,
                "Precio_ARS": precio,
                "PPC_ARS": ppc_ars,
                "Valorizado_ARS": valorizado,
                "Ganancia_ARS": ganancia,
            }
        )

    df_bonos = pd.DataFrame(registros)
    if df_bonos.empty:
        logger.info("Valuation skipped bonds build: empty portfolio slice")
        return df_bonos
    df_bonos["Peso_%"] = _compute_weight_pct(df_bonos["Valorizado_ARS"])
    logger.info("Valuation built bonds frame: rows=%s priced=%s", len(df_bonos), int(df_bonos["Precio_ARS"].notna().sum()))
    return df_bonos


def attach_value_usd(
    df: pd.DataFrame,
    *,
    mep_real: float | None,
    default_columns: list[str] | None = None,
) -> pd.DataFrame:
    if df.empty:
        logger.debug("USD attachment skipped: empty frame")
        return df
    out = df.copy()
    mep_value = positive_float_or_none(mep_real)
    if "Valor_USD" not in out.columns:
        out["Valor_USD"] = (
            out["Valorizado_ARS"].apply(lambda value: _money_div(value, mep_value)) if mep_value is not None else np.nan
        )
    if default_columns:
        for col in default_columns:
            if col not in out.columns:
                out[col] = np.nan
    logger.debug("USD attachment completed: rows=%s mep_available=%s", len(out), mep_value is not None)
    return out


def build_portfolio_master(
    df_cedears: pd.DataFrame,
    df_local: pd.DataFrame,
    df_bonos: pd.DataFrame,
    df_liquidez: pd.DataFrame,
    *,
    mep_real: float | None,
) -> pd.DataFrame:
    mep_value = positive_float_or_none(mep_real)
    frames = []
    for frame in [df_cedears, df_local, df_bonos, df_liquidez]:
        if frame is None or frame.empty:
            continue
        normalized = frame.copy().dropna(axis=1, how="all")
        frames.append(normalized)

    if not frames:
        logger.info("Portfolio master skipped: no frames to merge")
        return pd.DataFrame()

    dynamic_cols = []
    for frame in frames:
        for col in frame.columns:
            if col not in dynamic_cols:
                dynamic_cols.append(col)
    ordered_cols = [col for col in MASTER_PORTFOLIO_COLUMNS if col in dynamic_cols] + [
        col for col in dynamic_cols if col not in MASTER_PORTFOLIO_COLUMNS
    ]

    df_total = pd.concat(frames, ignore_index=True, sort=False).reindex(columns=ordered_cols)

    if "Cantidad_Real" not in df_total.columns:
        df_total["Cantidad_Real"] = df_total.get("Cantidad")
    else:
        df_total["Cantidad_Real"] = df_total["Cantidad_Real"].fillna(df_total.get("Cantidad"))

    if "Valor_USD" not in df_total.columns:
        df_total["Valor_USD"] = (
            df_total["Valorizado_ARS"].apply(lambda value: _money_div(value, mep_value))
            if mep_value is not None
            else np.nan
        )
    else:
        faltantes = df_total["Valor_USD"].isna()
        if mep_value is not None:
            df_total.loc[faltantes, "Valor_USD"] = df_total.loc[faltantes, "Valorizado_ARS"].apply(
                lambda value: _money_div(value, mep_value)
            )

    df_total["Peso_%"] = _compute_weight_pct(df_total["Valorizado_ARS"])

    logger.info(
        "Portfolio master built: rows=%s cedears=%s local=%s bonos=%s liquidez=%s",
        len(df_total),
        0 if df_cedears is None else len(df_cedears),
        0 if df_local is None else len(df_local),
        0 if df_bonos is None else len(df_bonos),
        0 if df_liquidez is None else len(df_liquidez),
    )

    return df_total
