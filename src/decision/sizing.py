from __future__ import annotations

import numpy as np
import pandas as pd


def _comentario_operativo(row: pd.Series) -> str:
    accion = row["accion_operativa"]
    tech = row.get("Tech_Trend")
    beta = row.get("Beta")

    if accion == "Desplegar liquidez":
        return "Liquidez disponible para fondear refuerzos sin vender posiciones de riesgo."
    if accion == "Mantener liquidez":
        return "Liquidez conservada como reserva táctica."
    if accion == "Rebalancear / tomar ganancia":
        return "Bono con señal parcial de salida; priorizar rebalanceo o toma parcial de ganancia."
    if accion == "Refuerzo":
        if tech == "Alcista fuerte":
            return "Refuerzo favorecido por score alto y soporte técnico alcista."
        if pd.notna(beta) and beta < 0.8:
            return "Refuerzo defensivo con beta controlada."
        return "Refuerzo razonable por score compuesto favorable."
    if accion == "Reducir":
        if tech == "Bajista":
            return "Reducción favorecida por score débil y técnico bajista."
        if pd.notna(beta) and beta > 1.5:
            return "Reducir por beta alta y deterioro relativo."
        return "Reducción o rebalanceo sugerido por score compuesto débil."
    return "Mantener y monitorear evolución."


def _bucket_prudencia(
    row: pd.Series,
    *,
    defensive_tickers: set[str],
    aggressive_tickers: set[str],
) -> str:
    ticker = row["Ticker_IOL"]
    beta = row.get("Beta")
    if ticker in defensive_tickers:
        return "Defensivo"
    if ticker in aggressive_tickers:
        return "Agresivo"
    if pd.notna(beta) and beta <= 0.8:
        return "Defensivo"
    if pd.notna(beta) and beta >= 1.3:
        return "Agresivo"
    return "Intermedio"


def build_operational_proposal(
    final_decision: pd.DataFrame,
    *,
    mep_real: float | None,
    usar_liquidez_iol: bool = True,
    aporte_externo_ars: float = 0.0,
) -> dict[str, object]:
    propuesta = final_decision.copy()
    propuesta["accion_operativa"] = propuesta["accion_sugerida_v2"]

    mask_liq = propuesta["Tipo"] == "Liquidez"
    propuesta.loc[mask_liq, "accion_operativa"] = np.where(
        propuesta.loc[mask_liq, "score_despliegue_liquidez"].fillna(0) >= 0.55,
        "Desplegar liquidez",
        "Mantener liquidez",
    )

    mask_bonos = propuesta["Tipo"] == "Bono"
    propuesta.loc[mask_bonos & (propuesta["score_unificado"] <= -0.20), "accion_operativa"] = (
        "Rebalancear / tomar ganancia"
    )
    propuesta.loc[
        mask_bonos & (propuesta["score_unificado"] > -0.20) & (propuesta["score_unificado"] < 0.08),
        "accion_operativa",
    ] = "Mantener / monitorear"

    propuesta["comentario_operativo"] = propuesta.apply(_comentario_operativo, axis=1)

    top_reforzar_final = (
        propuesta[propuesta["accion_operativa"] == "Refuerzo"]
        .sort_values("score_unificado", ascending=False)
        .head(3)
        .copy()
    )
    top_reducir_final = (
        propuesta[propuesta["accion_operativa"] == "Reducir"]
        .sort_values("score_unificado", ascending=True)
        .head(3)
        .copy()
    )
    top_bonos_rebalancear = (
        propuesta[propuesta["accion_operativa"] == "Rebalancear / tomar ganancia"]
        .sort_values("score_unificado", ascending=True)
        .head(3)
        .copy()
    )
    top_fondeo = (
        propuesta[propuesta["accion_operativa"] == "Desplegar liquidez"]
        .sort_values("score_despliegue_liquidez", ascending=False)
        .head(3)
        .copy()
    )

    row_caucion = propuesta[(propuesta["Ticker_IOL"].astype(str).str.upper() == "CAUCION")].copy()
    if row_caucion.empty and "Descripcion" in propuesta.columns:
        row_caucion = propuesta[
            propuesta["Descripcion"].astype(str).str.upper().str.contains("CAUCION", na=False)
        ].copy()
    if row_caucion.empty:
        row_caucion = top_fondeo.head(1).copy()

    monto_fondeo_liquidez_ars = 0.0
    monto_fondeo_liquidez_usd = 0.0
    fuente_liquidez = None

    if usar_liquidez_iol and not row_caucion.empty:
        fuente_fondeo = str(row_caucion["Ticker_IOL"].iloc[0])
        liquidez_ars = float(row_caucion["Valorizado_ARS"].iloc[0])
        liquidez_usd = float(row_caucion["Valor_USD"].iloc[0])
        n_refuerzo_fuerte = int((propuesta["score_unificado"] >= 0.20).sum())
        if n_refuerzo_fuerte >= 3:
            pct_fondeo = 0.30
        elif n_refuerzo_fuerte >= 1:
            pct_fondeo = 0.20
        else:
            pct_fondeo = 0.10
        monto_fondeo_liquidez_ars = liquidez_ars * pct_fondeo
        monto_fondeo_liquidez_usd = liquidez_usd * pct_fondeo
        fuente_liquidez = fuente_fondeo
    else:
        pct_fondeo = 0.0

    aporte_externo_ars = max(float(aporte_externo_ars or 0.0), 0.0)
    aporte_externo_usd = aporte_externo_ars / mep_real if mep_real and aporte_externo_ars > 0 else 0.0

    monto_fondeo_ars = monto_fondeo_liquidez_ars + aporte_externo_ars
    monto_fondeo_usd = monto_fondeo_liquidez_usd + aporte_externo_usd

    if usar_liquidez_iol and aporte_externo_ars > 0 and fuente_liquidez:
        fuente_fondeo = f"Mixto: {fuente_liquidez} + aporte externo"
    elif usar_liquidez_iol and fuente_liquidez:
        fuente_fondeo = fuente_liquidez
    elif aporte_externo_ars > 0:
        fuente_fondeo = "Aporte externo"
    else:
        fuente_fondeo = "Sin fondeo disponible"

    if not top_reforzar_final.empty and monto_fondeo_ars > 0:
        peso_scores = top_reforzar_final["score_unificado"].clip(lower=0)
        if peso_scores.sum() > 0:
            pesos_relativos = peso_scores / peso_scores.sum()
        else:
            pesos_relativos = pd.Series(
                [1 / len(top_reforzar_final)] * len(top_reforzar_final),
                index=top_reforzar_final.index,
            )
        top_reforzar_final["Fondeo_Sugerido_ARS"] = (pesos_relativos * monto_fondeo_ars).round(0)
        top_reforzar_final["Fondeo_Sugerido_USD"] = (
            top_reforzar_final["Fondeo_Sugerido_ARS"] / mep_real
        ).round(2) if mep_real else np.nan
    else:
        top_reforzar_final["Fondeo_Sugerido_ARS"] = np.nan
        top_reforzar_final["Fondeo_Sugerido_USD"] = np.nan

    return {
        "propuesta": propuesta,
        "top_reforzar_final": top_reforzar_final,
        "top_reducir_final": top_reducir_final,
        "top_bonos_rebalancear": top_bonos_rebalancear,
        "top_fondeo": top_fondeo,
        "fuente_fondeo": fuente_fondeo,
        "usar_liquidez_iol": usar_liquidez_iol,
        "pct_fondeo": pct_fondeo,
        "aporte_externo_ars": aporte_externo_ars,
        "aporte_externo_usd": aporte_externo_usd,
        "monto_fondeo_liquidez_ars": monto_fondeo_liquidez_ars,
        "monto_fondeo_liquidez_usd": monto_fondeo_liquidez_usd,
        "monto_fondeo_ars": monto_fondeo_ars,
        "monto_fondeo_usd": monto_fondeo_usd,
    }


def build_prudent_allocation(
    propuesta: pd.DataFrame,
    *,
    monto_fondeo_ars: float,
    monto_fondeo_usd: float,
    mep_real: float | None,
    defensive_tickers: set[str],
    aggressive_tickers: set[str],
    bucket_weights: dict[str, float],
) -> pd.DataFrame:
    candidatos_refuerzo = propuesta[propuesta["accion_operativa"] == "Refuerzo"].copy()
    if len(candidatos_refuerzo) == 0 or monto_fondeo_ars <= 0:
        return candidatos_refuerzo

    candidatos_refuerzo["Bucket_Prudencia"] = candidatos_refuerzo.apply(
        lambda row: _bucket_prudencia(
            row,
            defensive_tickers=defensive_tickers,
            aggressive_tickers=aggressive_tickers,
        ),
        axis=1,
    )
    candidatos_refuerzo["Peso_Base"] = candidatos_refuerzo["Bucket_Prudencia"].map(bucket_weights).fillna(0.60)
    candidatos_refuerzo["Score_Ajustado"] = candidatos_refuerzo["score_unificado"].clip(lower=0)
    candidatos_refuerzo["Peso_Asignacion"] = (
        0.80 * candidatos_refuerzo["Peso_Base"] + 0.20 * candidatos_refuerzo["Score_Ajustado"]
    )

    pesos = candidatos_refuerzo["Peso_Asignacion"] / candidatos_refuerzo["Peso_Asignacion"].sum()
    candidatos_refuerzo["Asignacion_Bruta_ARS"] = (pesos * monto_fondeo_ars).round(0)

    tope_ars = monto_fondeo_ars * 0.65
    candidatos_refuerzo["Asignacion_Topeada_ARS"] = candidatos_refuerzo["Asignacion_Bruta_ARS"].clip(upper=tope_ars)
    remanente = monto_fondeo_ars - candidatos_refuerzo["Asignacion_Topeada_ARS"].sum()
    if remanente > 0:
        elegibles = candidatos_refuerzo[candidatos_refuerzo["Asignacion_Topeada_ARS"] < tope_ars].copy()
        if not elegibles.empty:
            pesos_rem = elegibles["Peso_Asignacion"] / elegibles["Peso_Asignacion"].sum()
            extra = (pesos_rem * remanente).round(0)
            for idx in extra.index:
                candidatos_refuerzo.loc[idx, "Asignacion_Topeada_ARS"] += extra.loc[idx]

    candidatos_refuerzo["Asignacion_Final_ARS"] = candidatos_refuerzo["Asignacion_Topeada_ARS"]
    candidatos_refuerzo["Asignacion_Final_USD"] = (
        candidatos_refuerzo["Asignacion_Final_ARS"] / mep_real
    ).round(2) if mep_real else np.nan

    def comentario_sizing(row: pd.Series) -> str:
        if row["Bucket_Prudencia"] == "Defensivo":
            return "Mayor peso por perfil defensivo/dividendos."
        if row["Bucket_Prudencia"] == "Agresivo":
            return "Peso limitado por perfil más agresivo."
        return "Peso intermedio por perfil balanceado."

    candidatos_refuerzo["Comentario_Asignacion"] = candidatos_refuerzo.apply(comentario_sizing, axis=1)
    return candidatos_refuerzo.sort_values("Asignacion_Final_ARS", ascending=False)


def build_dynamic_allocation(
    top_reforzar_final: pd.DataFrame,
    *,
    monto_fondeo_ars: float,
    monto_fondeo_usd: float,
    mep_real: float | None,
    defensive_tickers: set[str],
    aggressive_tickers: set[str],
    bucket_weights: dict[str, float],
    tope_pct: float = 65.0,
) -> pd.DataFrame:
    asignacion_final = top_reforzar_final.copy()
    if asignacion_final.empty or monto_fondeo_ars <= 0:
        return asignacion_final

    asignacion_final["Bucket_Prudencia"] = asignacion_final.apply(
        lambda row: _bucket_prudencia(
            row,
            defensive_tickers=defensive_tickers,
            aggressive_tickers=aggressive_tickers,
        ),
        axis=1,
    )
    asignacion_final["Peso_Base"] = asignacion_final["Bucket_Prudencia"].map(bucket_weights).fillna(0.60)
    asignacion_final["Score_Ajustado"] = asignacion_final["score_unificado"].clip(lower=0)
    asignacion_final["Peso_Asignacion"] = (
        0.80 * asignacion_final["Peso_Base"] + 0.20 * asignacion_final["Score_Ajustado"]
    )

    pesos = asignacion_final["Peso_Asignacion"] / asignacion_final["Peso_Asignacion"].sum()
    asignacion_final["Peso_Fondeo_%"] = (pesos * 100).round(2)
    asignacion_final["Monto_ARS"] = (pesos * monto_fondeo_ars).round(0)
    asignacion_final["Monto_USD"] = (
        asignacion_final["Monto_ARS"] / mep_real
    ).round(2) if mep_real else np.nan

    mask_tope = asignacion_final["Peso_Fondeo_%"] > tope_pct
    if mask_tope.any():
        exceso = (asignacion_final.loc[mask_tope, "Peso_Fondeo_%"] - tope_pct).sum()
        asignacion_final.loc[mask_tope, "Peso_Fondeo_%"] = tope_pct
        mask_rest = ~mask_tope
        if mask_rest.any() and exceso > 0:
            pesos_rest = asignacion_final.loc[mask_rest, "Peso_Fondeo_%"]
            pesos_rest = pesos_rest / pesos_rest.sum()
            asignacion_final.loc[mask_rest, "Peso_Fondeo_%"] += pesos_rest * exceso
        asignacion_final["Monto_ARS"] = (asignacion_final["Peso_Fondeo_%"] / 100 * monto_fondeo_ars).round(0)
        asignacion_final["Monto_USD"] = (
            asignacion_final["Monto_ARS"] / mep_real
        ).round(2) if mep_real else np.nan

    def comentario_final(row: pd.Series) -> str:
        if row["Bucket_Prudencia"] == "Defensivo":
            return "Mayor asignación por perfil defensivo y mejor encastre prudencial."
        if row["Bucket_Prudencia"] == "Agresivo":
            return "Asignación limitada por perfil táctico / más agresivo."
        return "Asignación intermedia por perfil balanceado."

    asignacion_final["Comentario_Asignacion"] = asignacion_final.apply(comentario_final, axis=1)
    return asignacion_final.sort_values("Monto_ARS", ascending=False)
