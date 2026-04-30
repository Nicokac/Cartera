from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from decision.action_constants import (
    ACTION_DESPLEGAR_LIQUIDEZ,
    ACTION_MANTENER_LIQUIDEZ,
    ACTION_MANTENER_LIQUIDEZ_BLOQUEADA,
    ACTION_MANTENER_MONITOREAR,
    ACTION_REBALANCEAR,
    ACTION_REDUCIR,
    ACTION_REFUERZO,
)
from decision.operational_comments import (
    _join_with_y as _join_with_y_impl,
    build_operational_comment,
)

logger = logging.getLogger(__name__)


def _format_funding_sources(tickers: list[str]) -> str | None:
    clean = [str(ticker).strip() for ticker in tickers if str(ticker).strip()]
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    return "Fuentes multiples: " + ", ".join(clean)


def _join_with_y(parts: list[str]) -> str:
    return _join_with_y_impl(parts)


def _comentario_operativo(row: pd.Series) -> str:
    return build_operational_comment(row)


def _bucket_prudencia(
    row: pd.Series,
    *,
    sizing_rules: dict[str, object] | None = None,
) -> str:
    sizing_rules = sizing_rules or {}
    bucket_beta_thresholds = sizing_rules.get("bucket_beta_thresholds", {}) or {}
    bucket_type_defaults = sizing_rules.get("bucket_type_defaults", {}) or {}
    bucket_weight_thresholds = sizing_rules.get("bucket_weight_thresholds", {}) or {}
    defensivo_max = float(bucket_beta_thresholds.get("defensivo_max", 0.8))
    agresivo_min = float(bucket_beta_thresholds.get("agresivo_min", 1.3))
    agresivo_peso_min = float(bucket_weight_thresholds.get("agresivo_min_pct", 5.0))

    tipo = str(row.get("Tipo") or "").strip()
    es_liquidez = bool(row.get("Es_Liquidez", False))
    beta = row.get("Beta")
    peso_pct = pd.to_numeric(row.get("Peso_%"), errors="coerce")
    tipo_default = bucket_type_defaults.get(tipo)
    if tipo_default in {"Defensivo", "Intermedio", "Agresivo"}:
        if es_liquidez or tipo == "Bono":
            return str(tipo_default)
    if pd.notna(beta) and beta <= defensivo_max:
        return "Defensivo"
    if pd.notna(beta) and beta >= agresivo_min:
        return "Agresivo"
    if tipo in {"CEDEAR", "Accion Local", "Acción Local"} and pd.notna(peso_pct) and peso_pct >= agresivo_peso_min:
        return "Agresivo"
    if tipo_default in {"Defensivo", "Intermedio", "Agresivo"}:
        return str(tipo_default)
    return "Intermedio"


def _prepare_allocation_frame(
    df: pd.DataFrame,
    *,
    bucket_weights: dict[str, float],
    sizing_rules: dict[str, object] | None = None,
) -> pd.DataFrame:
    sizing_rules = sizing_rules or {}
    allocation_mix = sizing_rules.get("allocation_mix", {}) or {}
    peso_base_weight = float(allocation_mix.get("peso_base", 0.80))
    score_ajustado_weight = float(allocation_mix.get("score_ajustado", 0.20))
    bucket_fallback_weight = float(sizing_rules.get("bucket_fallback_weight", 0.60))

    out = df.copy()
    if out.empty:
        return out

    out["Bucket_Prudencia"] = out.apply(
        lambda row: _bucket_prudencia(row, sizing_rules=sizing_rules),
        axis=1,
    )
    out["Peso_Base"] = out["Bucket_Prudencia"].map(bucket_weights).fillna(bucket_fallback_weight)
    out["Score_Ajustado"] = pd.to_numeric(out["score_unificado"], errors="coerce").fillna(0).clip(lower=0)
    out["Peso_Asignacion"] = (
        peso_base_weight * out["Peso_Base"]
        + score_ajustado_weight * out["Score_Ajustado"]
    )
    return out


def build_operational_proposal(
    final_decision: pd.DataFrame,
    *,
    mep_real: float | None,
    usar_liquidez_iol: bool = True,
    aporte_externo_ars: float = 0.0,
    action_rules: dict[str, object] | None = None,
    sizing_rules: dict[str, object] | None = None,
) -> dict[str, object]:
    action_rules = action_rules or {}
    sizing_rules = sizing_rules or {}
    top_candidates = int(sizing_rules.get("top_candidates", 3))
    funding_policy = sizing_rules.get("funding_policy", {}) or {}
    strong_refuerzo_threshold = float(funding_policy.get("strong_refuerzo_threshold", 0.20))
    pct_fondeo_rules = funding_policy.get("pct_fondeo", {}) or {}
    pct_fondeo_3_plus = float(pct_fondeo_rules.get("strong_refuerzo_3_plus", 0.30))
    pct_fondeo_1_plus = float(pct_fondeo_rules.get("strong_refuerzo_1_plus", 0.20))
    pct_fondeo_default = float(pct_fondeo_rules.get("default", 0.10))
    default_bond_rebalance_threshold = float(action_rules.get("bono_rebalance_threshold", -0.20))
    bono_monitor_max = float(action_rules.get("bono_monitor_max", 0.08))
    bond_subfamily_thresholds = action_rules.get("bond_subfamily_thresholds", {}) or {}

    propuesta = final_decision.copy()
    propuesta["accion_operativa"] = propuesta["accion_sugerida_v2"]

    if "Es_Liquidez" in propuesta.columns:
        mask_liq = propuesta["Es_Liquidez"].fillna(propuesta["Tipo"].eq("Liquidez"))
    else:
        mask_liq = propuesta["Tipo"].eq("Liquidez")
    if usar_liquidez_iol:
        propuesta.loc[mask_liq, "accion_operativa"] = np.where(
            propuesta.loc[mask_liq, "score_despliegue_liquidez"].fillna(0) >= 0.55,
            ACTION_DESPLEGAR_LIQUIDEZ,
            ACTION_MANTENER_LIQUIDEZ,
        )
    else:
        propuesta.loc[mask_liq, "accion_operativa"] = ACTION_MANTENER_LIQUIDEZ_BLOQUEADA

    mask_bonos = propuesta["Tipo"] == "Bono"
    bond_rebalance_threshold = propuesta.get("asset_subfamily", pd.Series(index=propuesta.index, dtype=object)).map(
        lambda subfamily: float(
            (bond_subfamily_thresholds.get(subfamily, {}) or {}).get(
                "rebalance_threshold", default_bond_rebalance_threshold
            )
        )
    )
    bond_refuerzo_threshold = propuesta.get("asset_subfamily", pd.Series(index=propuesta.index, dtype=object)).map(
        lambda subfamily: (bond_subfamily_thresholds.get(subfamily, {}) or {}).get("refuerzo_threshold")
    )
    bond_refuerzo_threshold = pd.to_numeric(bond_refuerzo_threshold, errors="coerce")

    propuesta.loc[
        mask_bonos
        & bond_refuerzo_threshold.notna()
        & (propuesta["score_unificado"] >= bond_refuerzo_threshold),
        "accion_operativa",
    ] = ACTION_REFUERZO
    propuesta.loc[mask_bonos & (propuesta["score_unificado"] <= bond_rebalance_threshold), "accion_operativa"] = (
        ACTION_REBALANCEAR
    )
    propuesta.loc[
        mask_bonos
        & ~(
            bond_refuerzo_threshold.notna()
            & (propuesta["score_unificado"] >= bond_refuerzo_threshold)
        )
        & (propuesta["score_unificado"] > bond_rebalance_threshold)
        & (propuesta["score_unificado"] < bono_monitor_max),
        "accion_operativa",
    ] = ACTION_MANTENER_MONITOREAR

    propuesta["comentario_operativo"] = propuesta.apply(_comentario_operativo, axis=1)
    mask_market_assets = ~(mask_bonos | mask_liq)
    if "motivo_accion" in propuesta.columns:
        propuesta.loc[
            mask_market_assets & propuesta["motivo_accion"].notna(),
            "comentario_operativo",
        ] = propuesta.loc[
            mask_market_assets & propuesta["motivo_accion"].notna(),
            "motivo_accion",
        ]

    top_reforzar_final = (
        propuesta[propuesta["accion_operativa"] == ACTION_REFUERZO]
        .sort_values("score_unificado", ascending=False)
        .head(top_candidates)
        .copy()
    )
    top_reducir_final = (
        propuesta[propuesta["accion_operativa"] == ACTION_REDUCIR]
        .sort_values("score_unificado", ascending=True)
        .head(top_candidates)
        .copy()
    )
    top_bonos_rebalancear = (
        propuesta[propuesta["accion_operativa"] == ACTION_REBALANCEAR]
        .sort_values("score_unificado", ascending=True)
        .head(top_candidates)
        .copy()
    )
    top_fondeo = (
        propuesta[propuesta["accion_operativa"] == ACTION_DESPLEGAR_LIQUIDEZ]
        .sort_values(["score_despliegue_liquidez", "Valorizado_ARS"], ascending=[False, False])
        .head(top_candidates)
        .copy()
    )

    descartados_reforzar = (
        propuesta[propuesta["accion_operativa"] == ACTION_REFUERZO]
        .sort_values("score_unificado", ascending=False)
        .iloc[top_candidates:]
        .copy()
    )
    descartados_reducir = (
        propuesta[propuesta["accion_operativa"] == ACTION_REDUCIR]
        .sort_values("score_unificado", ascending=True)
        .iloc[top_candidates:]
        .copy()
    )
    descartados_rebalancear = (
        propuesta[propuesta["accion_operativa"] == ACTION_REBALANCEAR]
        .sort_values("score_unificado", ascending=True)
        .iloc[top_candidates:]
        .copy()
    )
    descartados_fondeo = (
        propuesta[propuesta["accion_operativa"] == ACTION_DESPLEGAR_LIQUIDEZ]
        .sort_values(["score_despliegue_liquidez", "Valorizado_ARS"], ascending=[False, False])
        .iloc[top_candidates:]
        .copy()
    )

    logger.info(
        "Sizing proposal: top_candidates=%s refuerzos=%s/%s reducir=%s/%s rebalancear=%s/%s fondeo=%s/%s",
        top_candidates,
        len(top_reforzar_final),
        int((propuesta["accion_operativa"] == ACTION_REFUERZO).sum()),
        len(top_reducir_final),
        int((propuesta["accion_operativa"] == ACTION_REDUCIR).sum()),
        len(top_bonos_rebalancear),
        int((propuesta["accion_operativa"] == ACTION_REBALANCEAR).sum()),
        len(top_fondeo),
        int((propuesta["accion_operativa"] == ACTION_DESPLEGAR_LIQUIDEZ).sum()),
    )
    logger.info(
        "Sizing discarded candidates: refuerzos=%s reducir=%s rebalancear=%s fondeo=%s",
        ",".join(descartados_reforzar["Ticker_IOL"].astype(str).tolist()) or "-",
        ",".join(descartados_reducir["Ticker_IOL"].astype(str).tolist()) or "-",
        ",".join(descartados_rebalancear["Ticker_IOL"].astype(str).tolist()) or "-",
        ",".join(descartados_fondeo["Ticker_IOL"].astype(str).tolist()) or "-",
    )

    monto_fondeo_liquidez_ars = 0.0
    monto_fondeo_liquidez_usd = 0.0
    fuente_liquidez = None

    if usar_liquidez_iol and not top_fondeo.empty:
        funding_sources = top_fondeo["Ticker_IOL"].astype(str).tolist()
        liquidez_ars = float(pd.to_numeric(top_fondeo["Valorizado_ARS"], errors="coerce").fillna(0).sum())
        liquidez_usd = float(pd.to_numeric(top_fondeo["Valor_USD"], errors="coerce").fillna(0).sum())
        n_refuerzo_fuerte = int((propuesta["score_unificado"] >= strong_refuerzo_threshold).sum())
        if n_refuerzo_fuerte >= 3:
            pct_fondeo = pct_fondeo_3_plus
        elif n_refuerzo_fuerte >= 1:
            pct_fondeo = pct_fondeo_1_plus
        else:
            pct_fondeo = pct_fondeo_default
        monto_fondeo_liquidez_ars = liquidez_ars * pct_fondeo
        monto_fondeo_liquidez_usd = liquidez_usd * pct_fondeo
        fuente_liquidez = _format_funding_sources(funding_sources)
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
        "descartados_reforzar": descartados_reforzar,
        "descartados_reducir": descartados_reducir,
        "descartados_rebalancear": descartados_rebalancear,
        "descartados_fondeo": descartados_fondeo,
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
    bucket_weights: dict[str, float],
    sizing_rules: dict[str, object] | None = None,
) -> pd.DataFrame:
    sizing_rules = sizing_rules or {}
    tope_posicion_pct = float(sizing_rules.get("tope_posicion_pct", 65.0))

    candidatos_refuerzo = propuesta[propuesta["accion_operativa"] == ACTION_REFUERZO].copy()
    if len(candidatos_refuerzo) == 0 or monto_fondeo_ars <= 0:
        return candidatos_refuerzo

    candidatos_refuerzo = _prepare_allocation_frame(
        candidatos_refuerzo,
        bucket_weights=bucket_weights,
        sizing_rules=sizing_rules,
    )

    pesos = candidatos_refuerzo["Peso_Asignacion"] / candidatos_refuerzo["Peso_Asignacion"].sum()
    candidatos_refuerzo["Asignacion_Bruta_ARS"] = (pesos * monto_fondeo_ars).round(0)

    tope_ars = monto_fondeo_ars * (tope_posicion_pct / 100)
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
            return "Peso limitado por perfil mas agresivo."
        return "Peso intermedio por perfil balanceado."

    candidatos_refuerzo["Comentario_Asignacion"] = candidatos_refuerzo.apply(comentario_sizing, axis=1)
    return candidatos_refuerzo.sort_values("Asignacion_Final_ARS", ascending=False)


def build_dynamic_allocation(
    top_reforzar_final: pd.DataFrame,
    *,
    monto_fondeo_ars: float,
    monto_fondeo_usd: float,
    mep_real: float | None,
    bucket_weights: dict[str, float],
    tope_pct: float = 65.0,
    sizing_rules: dict[str, object] | None = None,
) -> pd.DataFrame:
    sizing_rules = sizing_rules or {}
    tope_pct = float(sizing_rules.get("tope_posicion_pct", tope_pct))

    asignacion_final = top_reforzar_final.copy()
    if asignacion_final.empty or monto_fondeo_ars <= 0:
        return asignacion_final

    asignacion_final = _prepare_allocation_frame(
        asignacion_final,
        bucket_weights=bucket_weights,
        sizing_rules=sizing_rules,
    )

    pesos = asignacion_final["Peso_Asignacion"] / asignacion_final["Peso_Asignacion"].sum()
    asignacion_final["Peso_Fondeo_%"] = (pesos * 100).round(2)
    asignacion_final["Monto_ARS"] = (pesos * monto_fondeo_ars).round(0)
    asignacion_final["Monto_USD"] = (asignacion_final["Monto_ARS"] / mep_real).round(2) if mep_real else np.nan

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
            return "Mayor asignacion por perfil defensivo y mejor encastre prudencial."
        if row["Bucket_Prudencia"] == "Agresivo":
            return "Asignacion limitada por perfil tactico / mas agresivo."
        return "Asignacion intermedia por perfil balanceado."

    asignacion_final["Comentario_Asignacion"] = asignacion_final.apply(comentario_final, axis=1)
    return asignacion_final.sort_values("Monto_ARS", ascending=False)

