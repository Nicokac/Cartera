from __future__ import annotations

import numpy as np
import pandas as pd


def rank_score(series: pd.Series, higher_is_better: bool = True, neutral: float = 0.5) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    out = pd.Series(neutral, index=s.index, dtype=float)
    valid = s.notna()
    if valid.any():
        ranks = s[valid].rank(pct=True, method="average")
        out.loc[valid] = ranks if higher_is_better else (1 - ranks)
    return out


def consensus_to_score(text: object) -> float:
    if pd.isna(text):
        return 0.5
    t = str(text).strip().lower()

    positivos = ["buy", "outperform", "overweight", "upgrade", "positive", "strong buy", "initiated"]
    negativos = ["sell", "underperform", "underweight", "downgrade", "negative", "reduce"]
    neutros = ["hold", "neutral", "equal-weight", "equal weight", "market perform", "sector perform", "reiterated"]

    if any(x in t for x in positivos):
        return 1.0
    if any(x in t for x in negativos):
        return 0.0
    if any(x in t for x in neutros):
        return 0.5
    return 0.5


def build_decision_base(
    df_total: pd.DataFrame,
    df_cedears: pd.DataFrame,
    df_ratings_res: pd.DataFrame,
    *,
    mep_real: float | None,
) -> pd.DataFrame:
    decision_cols = [
        "Ticker_IOL",
        "Tipo",
        "Bloque",
        "Peso_%",
        "Valorizado_ARS",
        "Valor_USD",
        "Ganancia_ARS",
        "Cantidad_Real",
        "PPC_ARS",
    ]
    base = df_total[decision_cols].copy()
    base["Costo_ARS"] = base["Cantidad_Real"].fillna(0) * base["PPC_ARS"].fillna(0)
    base["Ganancia_%"] = np.where(
        base["Costo_ARS"] > 0,
        base["Ganancia_ARS"] / base["Costo_ARS"] * 100,
        np.nan,
    )

    ced_cols = [
        "Ticker_IOL",
        "Ticker_Finviz",
        "Perf Week",
        "Perf Month",
        "Perf YTD",
        "Beta",
        "P/E",
        "MEP_Implicito",
    ]
    ced_data = df_cedears[ced_cols].copy()

    if not df_ratings_res.empty:
        ratings_map = df_ratings_res.reset_index()[
            ["Ticker_Finviz", "consenso", "consenso_n", "total_ratings"]
        ].copy()
        ced_data = ced_data.merge(ratings_map, on="Ticker_Finviz", how="left")
    else:
        ced_data["consenso"] = None
        ced_data["consenso_n"] = np.nan
        ced_data["total_ratings"] = np.nan

    decision = base.merge(ced_data, on="Ticker_IOL", how="left")
    decision["Cobertura_Modelo"] = np.where(decision["Ticker_Finviz"].notna(), "Completa", "Parcial")
    decision["Es_Liquidez"] = decision["Tipo"].eq("Liquidez")
    decision["Es_Cedear"] = decision["Tipo"].eq("CEDEAR")
    decision["Es_Bono"] = decision["Tipo"].eq("Bono")
    decision["Es_Accion_Local"] = decision["Tipo"].eq("Acción Local")
    decision["Es_Core"] = decision["Bloque"].eq("Core")
    decision["MEP_Premium_%"] = np.where(
        decision["MEP_Implicito"].notna() & bool(mep_real),
        (decision["MEP_Implicito"] / mep_real - 1) * 100,
        np.nan,
    )

    decision["Consensus_Score"] = decision["consenso"].apply(consensus_to_score)
    decision["Consensus_Strength"] = np.where(
        decision["total_ratings"].fillna(0) > 0,
        decision["consenso_n"].fillna(0) / decision["total_ratings"].fillna(1),
        np.nan,
    )
    decision["Consensus_Final"] = (
        0.7 * decision["Consensus_Score"].fillna(0.5)
        + 0.3 * decision["Consensus_Strength"].fillna(0.5)
    )
    decision["Ganancia_%_Cap"] = decision["Ganancia_%"].clip(lower=-100, upper=150)
    return decision


def apply_base_scores(decision: pd.DataFrame) -> pd.DataFrame:
    out = decision.copy()
    out["s_low_weight"] = rank_score(out["Peso_%"], higher_is_better=False)
    out["s_high_weight"] = rank_score(out["Peso_%"], higher_is_better=True)
    out["s_mom_week"] = rank_score(out["Perf Week"], higher_is_better=True)
    out["s_mom_month"] = rank_score(out["Perf Month"], higher_is_better=True)
    out["s_mom_ytd"] = rank_score(out["Perf YTD"], higher_is_better=True)
    out["s_weak_mom_week"] = rank_score(out["Perf Week"], higher_is_better=False)
    out["s_weak_mom_month"] = rank_score(out["Perf Month"], higher_is_better=False)
    out["s_weak_mom_ytd"] = rank_score(out["Perf YTD"], higher_is_better=False)
    out["s_beta_ok"] = rank_score(out["Beta"], higher_is_better=False)
    out["s_beta_risk"] = rank_score(out["Beta"], higher_is_better=True)
    out["s_pe_ok"] = rank_score(out["P/E"], higher_is_better=False)
    out["s_pe_expensive"] = rank_score(out["P/E"], higher_is_better=True)
    out["s_mep_ok"] = rank_score(out["MEP_Premium_%"], higher_is_better=False)
    out["s_mep_premium"] = rank_score(out["MEP_Premium_%"], higher_is_better=True)
    out["s_consensus_good"] = out["Consensus_Final"].fillna(0.5)
    out["s_consensus_bad"] = 1 - out["s_consensus_good"]
    out["s_big_gain"] = rank_score(out["Ganancia_%_Cap"], higher_is_better=True)
    out["s_big_loss"] = rank_score(out["Ganancia_%_Cap"], higher_is_better=False)

    out["Momentum_Refuerzo"] = 0.2 * out["s_mom_week"] + 0.4 * out["s_mom_month"] + 0.4 * out["s_mom_ytd"]
    out["Momentum_Reduccion"] = (
        0.2 * out["s_weak_mom_week"] + 0.4 * out["s_weak_mom_month"] + 0.4 * out["s_weak_mom_ytd"]
    )

    out["score_refuerzo"] = (
        0.20 * out["s_low_weight"]
        + 0.25 * out["Momentum_Refuerzo"]
        + 0.15 * out["s_consensus_good"]
        + 0.10 * out["s_beta_ok"]
        + 0.10 * out["s_mep_ok"]
        + 0.10 * out["s_pe_ok"]
        + 0.10 * (1 - out["s_big_gain"])
    )
    out["score_refuerzo"] -= np.where(out["Es_Liquidez"], 0.35, 0.00)
    out["score_refuerzo"] -= np.where(out["Es_Bono"], 0.08, 0.00)
    out["score_refuerzo"] -= np.where(out["Beta"].fillna(0) > 1.8, 0.08, 0.00)
    out["score_refuerzo"] -= np.where(out["Es_Core"], 0.05, 0.00)
    out["score_refuerzo"] = out["score_refuerzo"].clip(0, 1)

    out["score_reduccion"] = (
        0.25 * out["s_high_weight"]
        + 0.20 * out["Momentum_Reduccion"]
        + 0.15 * out["s_beta_risk"]
        + 0.10 * out["s_mep_premium"]
        + 0.10 * out["s_consensus_bad"]
        + 0.10 * out["s_pe_expensive"]
        + 0.10 * out["s_big_gain"]
    )
    out["score_reduccion"] -= np.where(out["Es_Liquidez"], 0.25, 0.00)
    out["score_reduccion"] -= np.where(out["Es_Core"], 0.12, 0.00)
    out["score_reduccion"] -= np.where(out["Es_Bono"], 0.05, 0.00)
    out["score_reduccion"] = out["score_reduccion"].clip(0, 1)

    out["score_despliegue_liquidez"] = 0.0
    mask_liq = out["Es_Liquidez"]
    out.loc[mask_liq, "score_despliegue_liquidez"] = (
        0.60 * rank_score(out.loc[mask_liq, "Peso_%"], higher_is_better=True)
        + 0.40 * rank_score(out.loc[mask_liq, "Ganancia_ARS"], higher_is_better=False)
    ).clip(0, 1)

    return out


def apply_technical_overlay_scores(decision_tech: pd.DataFrame) -> pd.DataFrame:
    out = decision_tech.copy()
    if "tech_refuerzo" not in out.columns:
        return out
    out["tech_reduccion"] = 1 - out["tech_refuerzo"]
    out["score_refuerzo_v2"] = (0.75 * out["score_refuerzo"] + 0.25 * out["tech_refuerzo"]).clip(0, 1)
    out["score_reduccion_v2"] = (0.75 * out["score_reduccion"] + 0.25 * out["tech_reduccion"]).clip(0, 1)
    out["score_unificado_v2"] = (out["score_refuerzo_v2"] - out["score_reduccion_v2"]).round(3)
    return out


def finalize_unified_score(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "score_unificado_v2" in out.columns:
        out["score_unificado"] = (out["score_refuerzo_v2"] - out["score_reduccion_v2"]).round(3)
    else:
        out["score_unificado"] = (out["score_refuerzo"] - out["score_reduccion"]).round(3)
    return out
