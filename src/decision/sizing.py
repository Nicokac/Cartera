from __future__ import annotations

import numpy as np
import pandas as pd


def _fmt_pct_short(value: object) -> str | None:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(number):
        return None
    return f"{float(number):.1f}%"


def _comentario_operativo(row: pd.Series) -> str:
    accion = row["accion_operativa"]
    tech = row.get("Tech_Trend")
    beta = row.get("Beta")
    asset_subfamily = row.get("asset_subfamily")
    local_subfamily = row.get("bonistas_local_subfamily")
    parity = _fmt_pct_short(row.get("bonistas_paridad_pct"))
    tir = _fmt_pct_short(row.get("bonistas_tir_pct"))
    tir_gap = _fmt_pct_short(row.get("bonistas_tir_vs_avg_365d_pct"))
    md = pd.to_numeric(pd.Series([row.get("bonistas_md")]), errors="coerce").iloc[0]
    riesgo_pais = pd.to_numeric(pd.Series([row.get("bonistas_riesgo_pais_bps")]), errors="coerce").iloc[0]
    rem_inflacion = _fmt_pct_short(row.get("bonistas_rem_inflacion_mensual_pct"))
    put_flag = bool(row.get("bonistas_put_flag")) if pd.notna(row.get("bonistas_put_flag")) else False

    if accion == "Desplegar liquidez":
        return "Liquidez disponible para fondear refuerzos sin vender posiciones de riesgo."
    if accion == "Mantener liquidez":
        return "Liquidez conservada como reserva tactica."
    if accion == "Mantener liquidez bloqueada":
        return "Liquidez excluida del fondeo por politica explicita del analisis."
    if accion == "Rebalancear / tomar ganancia":
        if local_subfamily == "bond_hard_dollar":
            if parity and tir:
                riesgo_txt = f" con riesgo pais {int(riesgo_pais)} bps" if pd.notna(riesgo_pais) else ""
                return (
                    f"Hard-dollar soberano con paridad {parity} y TIR {tir}{riesgo_txt}; "
                    "priorizar rebalanceo o toma parcial de ganancia."
                )
            return "Hard-dollar soberano con ganancia extendida; priorizar rebalanceo o toma parcial de ganancia."
        if local_subfamily == "bond_bopreal":
            if parity and put_flag:
                riesgo_txt = f" con riesgo pais {int(riesgo_pais)} bps" if pd.notna(riesgo_pais) else ""
                return (
                    f"Bopreal con paridad {parity} y opcionalidad PUT{riesgo_txt}; "
                    "priorizar rebalanceo o toma parcial de ganancia."
                )
            return "Bopreal con senal parcial de salida; priorizar rebalanceo o toma parcial de ganancia."
        if asset_subfamily == "bond_sov_ar":
            return "Soberano AR con ganancia extendida; priorizar rebalanceo o toma parcial de ganancia."
        return "Bono con senal parcial de salida; priorizar rebalanceo o toma parcial de ganancia."
    if accion == "Refuerzo":
        if tech == "Alcista fuerte":
            return "Refuerzo favorecido por score alto y soporte tecnico alcista."
        if pd.notna(beta) and beta < 0.8:
            return "Refuerzo defensivo con beta controlada."
        return "Refuerzo razonable por score compuesto favorable."
    if accion == "Reducir":
        if tech == "Bajista":
            return "Reduccion favorecida por score debil y tecnico bajista."
        if pd.notna(beta) and beta > 1.5:
            return "Reducir por beta alta y deterioro relativo."
        return "Reduccion o rebalanceo sugerido por score compuesto debil."
    if accion == "Mantener / monitorear":
        if local_subfamily == "bond_hard_dollar":
            details: list[str] = []
            if parity:
                details.append(f"paridad {parity}")
            if tir:
                details.append(f"TIR {tir}")
            if pd.notna(riesgo_pais):
                details.append(f"riesgo pais {int(riesgo_pais)} bps")
            if pd.notna(md):
                details.append(f"duration {float(md):.2f}")
            if details:
                return (
                    "Hard-dollar soberano en monitoreo por "
                    + ", ".join(details[:2])
                    + (" y " + details[2] if len(details) > 2 else "")
                    + "; seguir riesgo soberano y compresion de spread."
                )
            return "Hard-dollar soberano en monitoreo; seguir riesgo soberano y compresion de spread."
        if local_subfamily == "bond_cer":
            if tir and parity and rem_inflacion:
                return (
                    f"Bono CER en monitoreo con TIR real {tir}, paridad {parity} y REM {rem_inflacion}; "
                    "seguir inflacion esperada y carry."
                )
            if tir and parity:
                return (
                    f"Bono CER en monitoreo con TIR real {tir} y paridad {parity}; "
                    "seguir inflacion esperada y carry."
                )
            return "Bono CER en zona neutral; mantener y monitorear carry e inflacion."
        if local_subfamily == "bond_bopreal":
            if parity and put_flag:
                riesgo_txt = f" con riesgo pais {int(riesgo_pais)} bps" if pd.notna(riesgo_pais) else ""
                return (
                    f"Bopreal en monitoreo con paridad {parity} y PUT disponible{riesgo_txt}; "
                    "seguir compresion y liquidez."
                )
            if tir_gap:
                riesgo_txt = f" y riesgo pais {int(riesgo_pais)} bps" if pd.notna(riesgo_pais) else ""
                return (
                    f"Bopreal en monitoreo con TIR relativa {tir_gap}{riesgo_txt}; "
                    "seguir compresion y liquidez."
                )
            return "Bopreal en zona prudente; mantener y monitorear compresion y liquidez."
        if asset_subfamily == "bond_cer":
            return "Bono CER en zona neutral; mantener y monitorear carry e inflacion."
        if asset_subfamily == "bond_bopreal":
            return "Bopreal en zona prudente; mantener y monitorear compresion y liquidez."
        if asset_subfamily == "bond_other":
            return "Bono sin clasificar en zona prudente; mantener y revisar clasificacion si suma relevancia."
        if asset_subfamily == "bond_sov_ar":
            return "Soberano AR sin senal extrema; mantener y monitorear riesgo y ganancias acumuladas."
    return "Mantener y monitorear evolucion."


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
    beta = row.get("Beta")
    peso_pct = pd.to_numeric(row.get("Peso_%"), errors="coerce")
    tipo_default = bucket_type_defaults.get(tipo)
    if tipo_default in {"Defensivo", "Intermedio", "Agresivo"}:
        if tipo in {"Liquidez", "Bono"}:
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
    bono_rebalance_threshold = float(action_rules.get("bono_rebalance_threshold", -0.20))
    bono_monitor_max = float(action_rules.get("bono_monitor_max", 0.08))
    bond_subfamily_thresholds = action_rules.get("bond_subfamily_thresholds", {}) or {}

    propuesta = final_decision.copy()
    propuesta["accion_operativa"] = propuesta["accion_sugerida_v2"]

    mask_liq = propuesta["Tipo"] == "Liquidez"
    if usar_liquidez_iol:
        propuesta.loc[mask_liq, "accion_operativa"] = np.where(
            propuesta.loc[mask_liq, "score_despliegue_liquidez"].fillna(0) >= 0.55,
            "Desplegar liquidez",
            "Mantener liquidez",
        )
    else:
        propuesta.loc[mask_liq, "accion_operativa"] = "Mantener liquidez bloqueada"

    mask_bonos = propuesta["Tipo"] == "Bono"
    bond_rebalance_threshold = propuesta.get("asset_subfamily", pd.Series(index=propuesta.index, dtype=object)).map(
        lambda subfamily: float(
            (bond_subfamily_thresholds.get(subfamily, {}) or {}).get("rebalance_threshold", bono_rebalance_threshold)
        )
    )
    propuesta.loc[mask_bonos & (propuesta["score_unificado"] <= bond_rebalance_threshold), "accion_operativa"] = (
        "Rebalancear / tomar ganancia"
    )
    propuesta.loc[
        mask_bonos
        & (propuesta["score_unificado"] > bond_rebalance_threshold)
        & (propuesta["score_unificado"] < bono_monitor_max),
        "accion_operativa",
    ] = "Mantener / monitorear"

    propuesta["comentario_operativo"] = propuesta.apply(_comentario_operativo, axis=1)
    mask_market_assets = ~propuesta["Tipo"].isin(["Bono", "Liquidez"])
    if "motivo_accion" in propuesta.columns:
        propuesta.loc[
            mask_market_assets & propuesta["motivo_accion"].notna(),
            "comentario_operativo",
        ] = propuesta.loc[
            mask_market_assets & propuesta["motivo_accion"].notna(),
            "motivo_accion",
        ]

    top_reforzar_final = (
        propuesta[propuesta["accion_operativa"] == "Refuerzo"]
        .sort_values("score_unificado", ascending=False)
        .head(top_candidates)
        .copy()
    )
    top_reducir_final = (
        propuesta[propuesta["accion_operativa"] == "Reducir"]
        .sort_values("score_unificado", ascending=True)
        .head(top_candidates)
        .copy()
    )
    top_bonos_rebalancear = (
        propuesta[propuesta["accion_operativa"] == "Rebalancear / tomar ganancia"]
        .sort_values("score_unificado", ascending=True)
        .head(top_candidates)
        .copy()
    )
    top_fondeo = (
        propuesta[propuesta["accion_operativa"] == "Desplegar liquidez"]
        .sort_values(["score_despliegue_liquidez", "Valorizado_ARS"], ascending=[False, False])
        .head(top_candidates)
        .copy()
    )
    source_row = top_fondeo.head(1).copy()

    monto_fondeo_liquidez_ars = 0.0
    monto_fondeo_liquidez_usd = 0.0
    fuente_liquidez = None

    if usar_liquidez_iol and not source_row.empty:
        fuente_fondeo = str(source_row["Ticker_IOL"].iloc[0])
        liquidez_ars = float(source_row["Valorizado_ARS"].iloc[0])
        liquidez_usd = float(source_row["Valor_USD"].iloc[0])
        n_refuerzo_fuerte = int((propuesta["score_unificado"] >= strong_refuerzo_threshold).sum())
        if n_refuerzo_fuerte >= 3:
            pct_fondeo = pct_fondeo_3_plus
        elif n_refuerzo_fuerte >= 1:
            pct_fondeo = pct_fondeo_1_plus
        else:
            pct_fondeo = pct_fondeo_default
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
    bucket_weights: dict[str, float],
    sizing_rules: dict[str, object] | None = None,
) -> pd.DataFrame:
    sizing_rules = sizing_rules or {}
    allocation_mix = sizing_rules.get("allocation_mix", {}) or {}
    peso_base_weight = float(allocation_mix.get("peso_base", 0.80))
    score_ajustado_weight = float(allocation_mix.get("score_ajustado", 0.20))
    bucket_fallback_weight = float(sizing_rules.get("bucket_fallback_weight", 0.60))
    tope_posicion_pct = float(sizing_rules.get("tope_posicion_pct", 65.0))

    candidatos_refuerzo = propuesta[propuesta["accion_operativa"] == "Refuerzo"].copy()
    if len(candidatos_refuerzo) == 0 or monto_fondeo_ars <= 0:
        return candidatos_refuerzo

    candidatos_refuerzo["Bucket_Prudencia"] = candidatos_refuerzo.apply(
        lambda row: _bucket_prudencia(row, sizing_rules=sizing_rules),
        axis=1,
    )
    candidatos_refuerzo["Peso_Base"] = candidatos_refuerzo["Bucket_Prudencia"].map(bucket_weights).fillna(
        bucket_fallback_weight
    )
    candidatos_refuerzo["Score_Ajustado"] = candidatos_refuerzo["score_unificado"].clip(lower=0)
    candidatos_refuerzo["Peso_Asignacion"] = (
        peso_base_weight * candidatos_refuerzo["Peso_Base"]
        + score_ajustado_weight * candidatos_refuerzo["Score_Ajustado"]
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
    allocation_mix = sizing_rules.get("allocation_mix", {}) or {}
    peso_base_weight = float(allocation_mix.get("peso_base", 0.80))
    score_ajustado_weight = float(allocation_mix.get("score_ajustado", 0.20))
    bucket_fallback_weight = float(sizing_rules.get("bucket_fallback_weight", 0.60))
    tope_pct = float(sizing_rules.get("tope_posicion_pct", tope_pct))

    asignacion_final = top_reforzar_final.copy()
    if asignacion_final.empty or monto_fondeo_ars <= 0:
        return asignacion_final

    asignacion_final["Bucket_Prudencia"] = asignacion_final.apply(
        lambda row: _bucket_prudencia(row, sizing_rules=sizing_rules),
        axis=1,
    )
    asignacion_final["Peso_Base"] = asignacion_final["Bucket_Prudencia"].map(bucket_weights).fillna(
        bucket_fallback_weight
    )
    asignacion_final["Score_Ajustado"] = asignacion_final["score_unificado"].clip(lower=0)
    asignacion_final["Peso_Asignacion"] = (
        peso_base_weight * asignacion_final["Peso_Base"]
        + score_ajustado_weight * asignacion_final["Score_Ajustado"]
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
