from __future__ import annotations

from datetime import datetime

from common.numeric import positive_float_or_none

import pandas as pd


def build_executive_dashboard_data(
    df_total: pd.DataFrame,
    *,
    mep_real: float | None,
    broker_total_ars: float | None = None,
    broker_cash_ars: float | None = None,
    broker_cash_committed_ars: float | None = None,
) -> dict:
    work = df_total.copy()
    if "Es_Liquidez" not in work.columns:
        work["Es_Liquidez"] = work["Tipo"].eq("Liquidez")
    if "Moneda" not in work.columns:
        work["Moneda"] = pd.NA

    total_ars_model = work["Valorizado_ARS"].sum()
    total_usd = work["Valor_USD"].sum()
    ganancia_total = work["Ganancia_ARS"].sum()

    df_invertido = work[~work["Es_Liquidez"]].copy()
    df_liquidez_total = work[work["Es_Liquidez"]].copy()
    df_liquidez_usd = df_liquidez_total[df_liquidez_total["Moneda"].eq("USD")].copy()

    invertido_ars = df_invertido["Valorizado_ARS"].sum()
    invertido_usd = df_invertido["Valor_USD"].sum()
    liquidez_ars = df_liquidez_total["Valorizado_ARS"].sum()
    liquidez_usd = df_liquidez_total["Valor_USD"].sum()
    liquidez_usd_ars = df_liquidez_usd["Valorizado_ARS"].sum()
    broker_total_ars_value = positive_float_or_none(broker_total_ars)
    broker_cash_ars_value = positive_float_or_none(broker_cash_ars)
    broker_cash_committed_ars_value = positive_float_or_none(broker_cash_committed_ars)
    total_ars = broker_total_ars_value if broker_total_ars_value is not None else total_ars_model
    total_ars_iol = total_ars - liquidez_usd_ars
    liquidez_ars_iol = liquidez_ars - liquidez_usd_ars

    costo_invertido = (
        df_invertido["PPC_ARS"].fillna(0) * df_invertido["Cantidad_Real"].fillna(0)
    ).sum()

    rentabilidad_invertida = (
        df_invertido["Ganancia_ARS"].sum() / costo_invertido * 100 if costo_invertido > 0 else 0
    )
    rentabilidad_total = ganancia_total / costo_invertido * 100 if costo_invertido > 0 else 0

    resumen_tipos = (
        work.groupby("Tipo", dropna=False)
        .agg(
            Instrumentos=("Ticker_IOL", "count"),
            Valorizado_ARS=("Valorizado_ARS", "sum"),
            Valor_USD=("Valor_USD", "sum"),
            Ganancia_ARS=("Ganancia_ARS", "sum"),
        )
        .reset_index()
    )
    resumen_tipos["Peso_%"] = (resumen_tipos["Valorizado_ARS"] / total_ars * 100).round(2)
    resumen_tipos = resumen_tipos.sort_values("Valorizado_ARS", ascending=False).reset_index(drop=True)

    top_posiciones = (
        work.sort_values("Valorizado_ARS", ascending=False)[
            ["Ticker_IOL", "Tipo", "Bloque", "Valorizado_ARS", "Valor_USD", "Peso_%"]
        ]
        .head(10)
        .copy()
    )
    top_ganadoras = (
        work.sort_values("Ganancia_ARS", ascending=False)[
            ["Ticker_IOL", "Tipo", "Ganancia_ARS", "Valorizado_ARS"]
        ]
        .head(10)
        .copy()
    )
    top_perdedoras = (
        work.sort_values("Ganancia_ARS", ascending=True)[
            ["Ticker_IOL", "Tipo", "Ganancia_ARS", "Valorizado_ARS"]
        ]
        .head(10)
        .copy()
    )

    kpis = {
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "total_ars": total_ars,
        "total_ars_model": total_ars_model,
        "total_ars_iol": total_ars_iol,
        "total_usd": total_usd,
        "ganancia_total": ganancia_total,
        "mep_real": mep_real,
        "invertido_ars": invertido_ars,
        "invertido_usd": invertido_usd,
        "liquidez_ars": liquidez_ars,
        "liquidez_broker_ars": broker_cash_ars_value if broker_cash_ars_value is not None else liquidez_ars,
        "liquidez_broker_comprometida_ars": (
            broker_cash_committed_ars_value if broker_cash_committed_ars_value is not None else 0.0
        ),
        "liquidez_ars_iol": liquidez_ars_iol,
        "liquidez_usd": liquidez_usd,
        "liquidez_usd_ars": liquidez_usd_ars,
        "costo_invertido": costo_invertido,
        "rentabilidad_invertida": rentabilidad_invertida,
        "rentabilidad_total": rentabilidad_total,
        "n_ganadoras": int((work["Ganancia_ARS"] > 0).sum()),
        "n_perdedoras": int((work["Ganancia_ARS"] < 0).sum()),
        "n_neutras": int((work["Ganancia_ARS"].fillna(0) == 0).sum()),
        "n_instrumentos": len(work),
    }

    return {
        "kpis": kpis,
        "resumen_tipos": resumen_tipos,
        "top_posiciones": top_posiciones,
        "top_ganadoras": top_ganadoras,
        "top_perdedoras": top_perdedoras,
    }
