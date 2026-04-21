from __future__ import annotations

from typing import Iterable

import pandas as pd


def validate_required_columns(df: pd.DataFrame, required_columns: Iterable[str], *, df_name: str) -> None:
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"{df_name} no contiene las columnas requeridas: {missing}")


def build_integrity_report(
    df_total: pd.DataFrame,
    *,
    peso_tolerance_pct: float = 0.2,
) -> tuple[pd.DataFrame, dict]:
    required_columns = [
        "Ticker_IOL",
        "Tipo",
        "Valorizado_ARS",
        "Valor_USD",
        "Peso_%",
        "Precio_ARS",
    ]
    validate_required_columns(df_total, required_columns, df_name="df_total")

    es_liquidez = (
        df_total["Es_Liquidez"].fillna(False)
        if "Es_Liquidez" in df_total.columns
        else df_total["Tipo"].isin(["Liquidez", "FCI"])
    )
    faltan_precios = df_total[(~es_liquidez) & (df_total["Precio_ARS"].isna())]["Ticker_IOL"].dropna().astype(str).tolist()

    faltan_valores_usd = (
        df_total[df_total["Valor_USD"].isna()]["Ticker_IOL"].dropna().astype(str).tolist()
    )

    faltan_valorizado = (
        df_total[df_total["Valorizado_ARS"].isna()]["Ticker_IOL"].dropna().astype(str).tolist()
    )

    peso_total = float(df_total["Peso_%"].fillna(0).sum())
    peso_ok = abs(peso_total - 100) <= peso_tolerance_pct

    rows = [
        {
            "check": "precio_ars_invertidos",
            "estado": "OK" if not faltan_precios else "WARN",
            "detalle": "Todos los instrumentos invertidos tienen Precio_ARS"
            if not faltan_precios
            else f"Faltan precios en: {faltan_precios}",
        },
        {
            "check": "valor_usd",
            "estado": "OK" if not faltan_valores_usd else "WARN",
            "detalle": "Todos los instrumentos tienen Valor_USD"
            if not faltan_valores_usd
            else f"Faltan valores USD en: {faltan_valores_usd}",
        },
        {
            "check": "valorizado_ars",
            "estado": "OK" if not faltan_valorizado else "WARN",
            "detalle": "Todos los instrumentos tienen Valorizado_ARS"
            if not faltan_valorizado
            else f"Faltan valorizados en: {faltan_valorizado}",
        },
        {
            "check": "peso_total",
            "estado": "OK" if peso_ok else "WARN",
            "detalle": f"Suma de pesos: {peso_total:.2f}%",
        },
    ]

    report_df = pd.DataFrame(rows)
    summary = {
        "faltan_precios": faltan_precios,
        "faltan_valores_usd": faltan_valores_usd,
        "faltan_valorizado": faltan_valorizado,
        "peso_total": peso_total,
        "peso_ok": peso_ok,
        "warn_count": int((report_df["estado"] != "OK").sum()),
    }
    return report_df, summary
