from __future__ import annotations

import pandas as pd


def assign_base_action(decision: pd.DataFrame) -> pd.DataFrame:
    out = decision.copy()
    out["accion_sugerida"] = "Mantener / Neutral"

    out.loc[
        (~out["Es_Liquidez"])
        & (~out["Es_Bono"])
        & (out["score_refuerzo"] >= 0.60)
        & ((out["score_refuerzo"] - out["score_reduccion"]) >= 0.10),
        "accion_sugerida",
    ] = "Refuerzo"

    out.loc[
        (~out["Es_Liquidez"])
        & (~out["Es_Bono"])
        & (out["score_reduccion"] >= 0.60)
        & ((out["score_reduccion"] - out["score_refuerzo"]) >= 0.10),
        "accion_sugerida",
    ] = "Reducir"

    out.loc[(out["Es_Bono"]) & (out["score_reduccion"] >= 0.60), "accion_sugerida"] = (
        "Rebalancear / tomar ganancia"
    )
    out.loc[(out["Es_Liquidez"]) & (out["score_despliegue_liquidez"] >= 0.55), "accion_sugerida"] = (
        "Desplegar liquidez"
    )
    return out


def assign_action_v2(decision_tech: pd.DataFrame) -> pd.DataFrame:
    out = decision_tech.copy()
    out["accion_sugerida_v2"] = "Mantener / Neutral"

    out.loc[
        (~out["Es_Liquidez"])
        & (~out["Es_Bono"])
        & (out["score_refuerzo_v2"] >= 0.60)
        & ((out["score_refuerzo_v2"] - out["score_reduccion_v2"]) >= 0.10),
        "accion_sugerida_v2",
    ] = "Refuerzo"

    out.loc[
        (~out["Es_Liquidez"])
        & (~out["Es_Bono"])
        & (out["score_reduccion_v2"] >= 0.60)
        & ((out["score_reduccion_v2"] - out["score_refuerzo_v2"]) >= 0.10),
        "accion_sugerida_v2",
    ] = "Reducir"

    out.loc[(out["Es_Bono"]) & (out["score_reduccion_v2"] >= 0.60), "accion_sugerida_v2"] = (
        "Rebalancear / tomar ganancia"
    )
    out.loc[(out["Es_Liquidez"]) & (out["score_despliegue_liquidez"] >= 0.55), "accion_sugerida_v2"] = (
        "Desplegar liquidez"
    )
    return out


def enrich_decision_explanations(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    def top_drivers(row: pd.Series) -> list[str]:
        candidates = [
            ("momentum", row.get("Momentum_Refuerzo", 0) - row.get("Momentum_Reduccion", 0)),
            ("consenso", row.get("s_consensus_good", 0) - row.get("s_consensus_bad", 0)),
            ("peso", row.get("s_low_weight", 0) - row.get("s_high_weight", 0)),
            ("beta", row.get("s_beta_ok", 0) - row.get("s_beta_risk", 0)),
            ("mep", row.get("s_mep_ok", 0) - row.get("s_mep_premium", 0)),
            ("valuacion", row.get("s_pe_ok", 0) - row.get("s_pe_expensive", 0)),
            ("liquidez", row.get("score_despliegue_liquidez", 0)),
        ]
        ordered = [name for name, _ in sorted(candidates, key=lambda x: abs(x[1]), reverse=True)]
        return ordered[:3]

    def motivo_score(row: pd.Series) -> str:
        if row.get("Es_Liquidez"):
            return "Score de liquidez calculado por peso y pérdida relativa."
        if row.get("Es_Bono"):
            return "Score de bono calculado con sesgo prudencial y control de rebalanceo."
        return "Score compuesto por momentum, peso, consenso, beta, MEP y valuación."

    def motivo_accion(row: pd.Series) -> str:
        accion = row.get("accion_sugerida_v2", row.get("accion_sugerida", "Mantener / Neutral"))
        if accion == "Refuerzo":
            return "Refuerzo por score favorable y diferencia positiva frente a reducción."
        if accion == "Reducir":
            return "Reducción por score débil y mayor presión de riesgo/valuación."
        if accion == "Rebalancear / tomar ganancia":
            return "Bono con señal de salida parcial o toma de ganancia."
        if accion == "Desplegar liquidez":
            return "Liquidez identificada como fuente potencial de fondeo."
        return "Sin señal dominante; mantener y monitorear."

    drivers = out.apply(top_drivers, axis=1)
    out["driver_1"] = drivers.apply(lambda x: x[0] if len(x) > 0 else None)
    out["driver_2"] = drivers.apply(lambda x: x[1] if len(x) > 1 else None)
    out["driver_3"] = drivers.apply(lambda x: x[2] if len(x) > 2 else None)
    out["motivo_score"] = out.apply(motivo_score, axis=1)
    out["motivo_accion"] = out.apply(motivo_accion, axis=1)
    return out
