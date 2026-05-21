from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any, TypedDict

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


class SizingBundle(TypedDict):
    propuesta: pd.DataFrame
    top_reforzar_final: pd.DataFrame
    top_reducir_final: pd.DataFrame
    top_bonos_rebalancear: pd.DataFrame
    top_fondeo: pd.DataFrame
    descartados_reforzar: pd.DataFrame
    descartados_reducir: pd.DataFrame
    descartados_rebalancear: pd.DataFrame
    descartados_fondeo: pd.DataFrame
    fuente_fondeo: str
    usar_liquidez_iol: bool
    pct_fondeo: float
    aporte_externo_ars: float
    aporte_externo_usd: float
    monto_fondeo_liquidez_ars: float
    monto_fondeo_liquidez_usd: float
    monto_fondeo_ars: float
    monto_fondeo_usd: float


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
    sizing_rules: Mapping[str, Any] | None = None,
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
    sizing_rules: Mapping[str, Any] | None = None,
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


def _apply_operational_actions(
    propuesta: pd.DataFrame,
    *,
    usar_liquidez_iol: bool,
    action_rules: Mapping[str, Any],
) -> pd.DataFrame:
    out = propuesta.copy()
    funding_policy = action_rules
    default_bond_rebalance_threshold = float(funding_policy.get("bono_rebalance_threshold", -0.20))
    bono_monitor_max = float(funding_policy.get("bono_monitor_max", 0.08))
    bond_subfamily_thresholds = funding_policy.get("bond_subfamily_thresholds", {}) or {}

    if "Es_Liquidez" in out.columns:
        mask_liq = out["Es_Liquidez"].fillna(out["Tipo"].eq("Liquidez"))
    else:
        mask_liq = out["Tipo"].eq("Liquidez")
    if usar_liquidez_iol:
        out.loc[mask_liq, "accion_operativa"] = np.where(
            out.loc[mask_liq, "score_despliegue_liquidez"].fillna(0) >= 0.55,
            ACTION_DESPLEGAR_LIQUIDEZ,
            ACTION_MANTENER_LIQUIDEZ,
        )
    else:
        out.loc[mask_liq, "accion_operativa"] = ACTION_MANTENER_LIQUIDEZ_BLOQUEADA

    mask_bonos = out["Tipo"] == "Bono"
    asset_subfamily = out.get("asset_subfamily", pd.Series(index=out.index, dtype=object))
    bond_rebalance_threshold = asset_subfamily.map(
        lambda subfamily: float(
            (bond_subfamily_thresholds.get(subfamily, {}) or {}).get(
                "rebalance_threshold", default_bond_rebalance_threshold
            )
        )
    )
    bond_refuerzo_threshold = asset_subfamily.map(
        lambda subfamily: (bond_subfamily_thresholds.get(subfamily, {}) or {}).get("refuerzo_threshold")
    )
    bond_refuerzo_threshold = pd.to_numeric(bond_refuerzo_threshold, errors="coerce")

    out.loc[
        mask_bonos
        & bond_refuerzo_threshold.notna()
        & (out["score_unificado"] >= bond_refuerzo_threshold),
        "accion_operativa",
    ] = ACTION_REFUERZO
    out.loc[mask_bonos & (out["score_unificado"] <= bond_rebalance_threshold), "accion_operativa"] = (
        ACTION_REBALANCEAR
    )
    out.loc[
        mask_bonos
        & ~(
            bond_refuerzo_threshold.notna()
            & (out["score_unificado"] >= bond_refuerzo_threshold)
        )
        & (out["score_unificado"] > bond_rebalance_threshold)
        & (out["score_unificado"] < bono_monitor_max),
        "accion_operativa",
    ] = ACTION_MANTENER_MONITOREAR
    return out


def _apply_operational_comments(propuesta: pd.DataFrame) -> pd.DataFrame:
    out = propuesta.copy()
    out["comentario_operativo"] = out.apply(_comentario_operativo, axis=1)

    mask_bonos = out["Tipo"] == "Bono"
    if "Es_Liquidez" in out.columns:
        mask_liq = out["Es_Liquidez"].fillna(out["Tipo"].eq("Liquidez"))
    else:
        mask_liq = out["Tipo"].eq("Liquidez")
    mask_market_assets = ~(mask_bonos | mask_liq)
    if "motivo_accion" in out.columns:
        out.loc[
            mask_market_assets & out["motivo_accion"].notna(),
            "comentario_operativo",
        ] = out.loc[
            mask_market_assets & out["motivo_accion"].notna(),
            "motivo_accion",
        ]
    return out


def _build_action_rankings(
    propuesta: pd.DataFrame,
    *,
    top_candidates: int,
) -> dict[str, pd.DataFrame]:
    ranking_specs = {
        "top_reforzar_final": (ACTION_REFUERZO, ["score_unificado"], [False], slice(0, top_candidates)),
        "top_reducir_final": (ACTION_REDUCIR, ["score_unificado"], [True], slice(0, top_candidates)),
        "top_bonos_rebalancear": (ACTION_REBALANCEAR, ["score_unificado"], [True], slice(0, top_candidates)),
        "top_fondeo": (
            ACTION_DESPLEGAR_LIQUIDEZ,
            ["score_despliegue_liquidez", "Valorizado_ARS"],
            [False, False],
            slice(0, top_candidates),
        ),
        "descartados_reforzar": (ACTION_REFUERZO, ["score_unificado"], [False], slice(top_candidates, None)),
        "descartados_reducir": (ACTION_REDUCIR, ["score_unificado"], [True], slice(top_candidates, None)),
        "descartados_rebalancear": (ACTION_REBALANCEAR, ["score_unificado"], [True], slice(top_candidates, None)),
        "descartados_fondeo": (
            ACTION_DESPLEGAR_LIQUIDEZ,
            ["score_despliegue_liquidez", "Valorizado_ARS"],
            [False, False],
            slice(top_candidates, None),
        ),
    }
    rankings: dict[str, pd.DataFrame] = {}
    for key, (action, sort_cols, ascending, row_slice) in ranking_specs.items():
        ordered = propuesta[propuesta["accion_operativa"] == action].sort_values(sort_cols, ascending=ascending)
        rankings[key] = ordered.iloc[row_slice].copy()
    return rankings


class FundingSummary(TypedDict):
    fuente_fondeo: str
    pct_fondeo: float
    aporte_externo_ars: float
    aporte_externo_usd: float
    monto_fondeo_liquidez_ars: float
    monto_fondeo_liquidez_usd: float
    monto_fondeo_ars: float
    monto_fondeo_usd: float


def _is_growth_candidate(row: pd.Series) -> bool:
    subfamily = str(row.get("asset_subfamily") or "").strip().lower()
    block = str(row.get("Bloque") or "").strip().lower()
    return ("growth" in subfamily) or ("growth" in block)


def _apply_growth_cap_if_high_ust_regime(
    asignacion: pd.DataFrame,
    *,
    market_regime: Mapping[str, Any] | None = None,
    sizing_rules: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    out = asignacion.copy()
    if out.empty or "Peso_Fondeo_%" not in out.columns:
        return out

    market_regime = market_regime or {}
    active_flags = {str(flag).strip() for flag in (market_regime.get("active_flags", []) or []) if str(flag).strip()}
    if "tasas_ust_altas" not in active_flags:
        return out

    sizing_rules = sizing_rules or {}
    cap_rules = (sizing_rules.get("market_regime_caps", {}) or {}).get("tasas_ust_altas", {}) or {}
    growth_max_pct = float(cap_rules.get("growth_max_pct", 35.0))
    if growth_max_pct <= 0:
        growth_max_pct = 0.0

    growth_mask = out.apply(_is_growth_candidate, axis=1)
    if not bool(growth_mask.any()):
        return out

    growth_total = float(pd.to_numeric(out.loc[growth_mask, "Peso_Fondeo_%"], errors="coerce").fillna(0.0).sum())
    if growth_total <= growth_max_pct + 1e-9:
        return out

    rest_mask = ~growth_mask
    if not bool(rest_mask.any()):
        return out

    growth_weights = pd.to_numeric(out.loc[growth_mask, "Peso_Fondeo_%"], errors="coerce").fillna(0.0)
    rest_weights = pd.to_numeric(out.loc[rest_mask, "Peso_Fondeo_%"], errors="coerce").fillna(0.0)
    rest_total = float(rest_weights.sum())
    if rest_total <= 0:
        return out

    scale = growth_max_pct / growth_total if growth_total > 0 else 0.0
    out.loc[growth_mask, "Peso_Fondeo_%"] = growth_weights * scale
    excess = growth_total - float(pd.to_numeric(out.loc[growth_mask, "Peso_Fondeo_%"], errors="coerce").fillna(0.0).sum())
    if excess > 0:
        out.loc[rest_mask, "Peso_Fondeo_%"] = rest_weights + (rest_weights / rest_total) * excess

    total = float(pd.to_numeric(out["Peso_Fondeo_%"], errors="coerce").fillna(0.0).sum())
    if total > 0:
        out["Peso_Fondeo_%"] = (pd.to_numeric(out["Peso_Fondeo_%"], errors="coerce").fillna(0.0) / total) * 100.0

    return out


def _calculate_funding_summary(
    propuesta: pd.DataFrame,
    *,
    top_fondeo: pd.DataFrame,
    usar_liquidez_iol: bool,
    aporte_externo_ars: float,
    mep_real: float | None,
    strong_refuerzo_threshold: float,
    pct_fondeo_3_plus: float,
    pct_fondeo_1_plus: float,
    pct_fondeo_default: float,
) -> FundingSummary:
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

    return {
        "fuente_fondeo": fuente_fondeo,
        "pct_fondeo": pct_fondeo,
        "aporte_externo_ars": aporte_externo_ars,
        "aporte_externo_usd": aporte_externo_usd,
        "monto_fondeo_liquidez_ars": monto_fondeo_liquidez_ars,
        "monto_fondeo_liquidez_usd": monto_fondeo_liquidez_usd,
        "monto_fondeo_ars": monto_fondeo_ars,
        "monto_fondeo_usd": monto_fondeo_usd,
    }


def _assign_refuerzo_funding(
    top_reforzar_final: pd.DataFrame,
    *,
    monto_fondeo_ars: float,
    mep_real: float | None,
) -> pd.DataFrame:
    out = top_reforzar_final.copy()
    if not out.empty and monto_fondeo_ars > 0:
        peso_scores = out["score_unificado"].clip(lower=0)
        if peso_scores.sum() > 0:
            pesos_relativos = peso_scores / peso_scores.sum()
        else:
            pesos_relativos = pd.Series(
                [1 / len(out)] * len(out),
                index=out.index,
            )
        out["Fondeo_Sugerido_ARS"] = (pesos_relativos * monto_fondeo_ars).round(0)
        out["Fondeo_Sugerido_USD"] = (
            out["Fondeo_Sugerido_ARS"] / mep_real
        ).round(2) if mep_real else np.nan
    else:
        out["Fondeo_Sugerido_ARS"] = np.nan
        out["Fondeo_Sugerido_USD"] = np.nan
    return out


def build_operational_proposal(
    final_decision: pd.DataFrame,
    *,
    mep_real: float | None,
    usar_liquidez_iol: bool = True,
    aporte_externo_ars: float = 0.0,
    action_rules: Mapping[str, Any] | None = None,
    sizing_rules: Mapping[str, Any] | None = None,
) -> SizingBundle:
    action_rules = action_rules or {}
    sizing_rules = sizing_rules or {}
    top_candidates = int(sizing_rules.get("top_candidates", 3))
    funding_policy = sizing_rules.get("funding_policy", {}) or {}
    strong_refuerzo_threshold = float(funding_policy.get("strong_refuerzo_threshold", 0.20))
    pct_fondeo_rules = funding_policy.get("pct_fondeo", {}) or {}
    pct_fondeo_3_plus = float(pct_fondeo_rules.get("strong_refuerzo_3_plus", 0.30))
    pct_fondeo_1_plus = float(pct_fondeo_rules.get("strong_refuerzo_1_plus", 0.20))
    pct_fondeo_default = float(pct_fondeo_rules.get("default", 0.10))

    propuesta = final_decision.copy()
    propuesta["accion_operativa"] = propuesta["accion_sugerida_v2"]
    propuesta = _apply_operational_actions(
        propuesta,
        usar_liquidez_iol=usar_liquidez_iol,
        action_rules=action_rules,
    )
    propuesta = _apply_operational_comments(propuesta)
    rankings = _build_action_rankings(propuesta, top_candidates=top_candidates)

    logger.info(
        "Sizing proposal: top_candidates=%s refuerzos=%s/%s reducir=%s/%s rebalancear=%s/%s fondeo=%s/%s",
        top_candidates,
        len(rankings["top_reforzar_final"]),
        int((propuesta["accion_operativa"] == ACTION_REFUERZO).sum()),
        len(rankings["top_reducir_final"]),
        int((propuesta["accion_operativa"] == ACTION_REDUCIR).sum()),
        len(rankings["top_bonos_rebalancear"]),
        int((propuesta["accion_operativa"] == ACTION_REBALANCEAR).sum()),
        len(rankings["top_fondeo"]),
        int((propuesta["accion_operativa"] == ACTION_DESPLEGAR_LIQUIDEZ).sum()),
    )
    logger.info(
        "Sizing discarded candidates: refuerzos=%s reducir=%s rebalancear=%s fondeo=%s",
        ",".join(rankings["descartados_reforzar"]["Ticker_IOL"].astype(str).tolist()) or "-",
        ",".join(rankings["descartados_reducir"]["Ticker_IOL"].astype(str).tolist()) or "-",
        ",".join(rankings["descartados_rebalancear"]["Ticker_IOL"].astype(str).tolist()) or "-",
        ",".join(rankings["descartados_fondeo"]["Ticker_IOL"].astype(str).tolist()) or "-",
    )

    funding = _calculate_funding_summary(
        propuesta,
        top_fondeo=rankings["top_fondeo"],
        usar_liquidez_iol=usar_liquidez_iol,
        aporte_externo_ars=aporte_externo_ars,
        mep_real=mep_real,
        strong_refuerzo_threshold=strong_refuerzo_threshold,
        pct_fondeo_3_plus=pct_fondeo_3_plus,
        pct_fondeo_1_plus=pct_fondeo_1_plus,
        pct_fondeo_default=pct_fondeo_default,
    )
    rankings["top_reforzar_final"] = _assign_refuerzo_funding(
        rankings["top_reforzar_final"],
        monto_fondeo_ars=funding["monto_fondeo_ars"],
        mep_real=mep_real,
    )

    return {
        "propuesta": propuesta,
        "top_reforzar_final": rankings["top_reforzar_final"],
        "top_reducir_final": rankings["top_reducir_final"],
        "top_bonos_rebalancear": rankings["top_bonos_rebalancear"],
        "top_fondeo": rankings["top_fondeo"],
        "descartados_reforzar": rankings["descartados_reforzar"],
        "descartados_reducir": rankings["descartados_reducir"],
        "descartados_rebalancear": rankings["descartados_rebalancear"],
        "descartados_fondeo": rankings["descartados_fondeo"],
        "fuente_fondeo": funding["fuente_fondeo"],
        "usar_liquidez_iol": usar_liquidez_iol,
        "pct_fondeo": funding["pct_fondeo"],
        "aporte_externo_ars": funding["aporte_externo_ars"],
        "aporte_externo_usd": funding["aporte_externo_usd"],
        "monto_fondeo_liquidez_ars": funding["monto_fondeo_liquidez_ars"],
        "monto_fondeo_liquidez_usd": funding["monto_fondeo_liquidez_usd"],
        "monto_fondeo_ars": funding["monto_fondeo_ars"],
        "monto_fondeo_usd": funding["monto_fondeo_usd"],
    }


def build_prudent_allocation(
    propuesta: pd.DataFrame,
    *,
    monto_fondeo_ars: float,
    monto_fondeo_usd: float,
    mep_real: float | None,
    bucket_weights: dict[str, float],
    sizing_rules: Mapping[str, Any] | None = None,
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
    sizing_rules: Mapping[str, Any] | None = None,
    market_regime: Mapping[str, Any] | None = None,
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

    asignacion_final = _apply_growth_cap_if_high_ust_regime(
        asignacion_final,
        market_regime=market_regime,
        sizing_rules=sizing_rules,
    )

    asignacion_final["Monto_ARS"] = (pesos * monto_fondeo_ars).round(0)
    asignacion_final["Monto_USD"] = (asignacion_final["Monto_ARS"] / mep_real).round(2) if mep_real else np.nan

    # Recalcula montos tras cap por régimen.
    asignacion_final["Monto_ARS"] = (
        pd.to_numeric(asignacion_final["Peso_Fondeo_%"], errors="coerce").fillna(0.0) / 100.0 * monto_fondeo_ars
    ).round(0)
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

