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


DEFAULT_CONSENSUS_TAXONOMY = {
    "positive_terms": ["buy", "outperform", "overweight", "upgrade", "positive", "strong buy", "initiated"],
    "negative_terms": ["sell", "underperform", "underweight", "downgrade", "negative", "reduce"],
    "neutral_terms": ["hold", "neutral", "equal-weight", "equal weight", "market perform", "sector perform", "reiterated"],
}


def consensus_to_score(text: object, *, scoring_rules: dict[str, object] | None = None) -> float:
    if pd.isna(text):
        return 0.5
    t = str(text).strip().lower()

    scoring_rules = scoring_rules or {}
    taxonomy = scoring_rules.get("consensus_taxonomy", {}) or {}
    positivos = [str(x).strip().lower() for x in taxonomy.get("positive_terms", DEFAULT_CONSENSUS_TAXONOMY["positive_terms"])]
    negativos = [str(x).strip().lower() for x in taxonomy.get("negative_terms", DEFAULT_CONSENSUS_TAXONOMY["negative_terms"])]
    neutros = [str(x).strip().lower() for x in taxonomy.get("neutral_terms", DEFAULT_CONSENSUS_TAXONOMY["neutral_terms"])]

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
    scoring_rules: dict[str, object] | None = None,
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
        "ROE",
        "Profit Margin",
        "MEP_Implicito",
    ]
    ced_data = df_cedears.copy()
    for col in ced_cols:
        if col not in ced_data.columns:
            ced_data[col] = np.nan
    ced_data = ced_data[ced_cols].copy()

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
    decision["MEP_Premium_%"] = np.where(
        decision["MEP_Implicito"].notna() & bool(mep_real),
        (decision["MEP_Implicito"] / mep_real - 1) * 100,
        np.nan,
    )

    decision["Consensus_Score"] = decision["consenso"].apply(
        lambda value: consensus_to_score(value, scoring_rules=scoring_rules)
    )
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


def apply_base_scores(decision: pd.DataFrame, *, scoring_rules: dict[str, object] | None = None) -> pd.DataFrame:
    scoring_rules = scoring_rules or {}
    rank_neutral = float(scoring_rules.get("rank_neutral", 0.5))
    gain_clip = scoring_rules.get("gain_clip", {}) or {}
    momentum_weights = scoring_rules.get("momentum_weights", {}) or {}
    score_refuerzo_weights = scoring_rules.get("score_refuerzo_weights", {}) or {}
    score_reduccion_weights = scoring_rules.get("score_reduccion_weights", {}) or {}
    score_despliegue_liquidez_weights = scoring_rules.get("score_despliegue_liquidez_weights", {}) or {}
    concentration_rules = scoring_rules.get("concentration", {}) or {}
    penalties = scoring_rules.get("penalties", {}) or {}
    refuerzo_penalties = penalties.get("refuerzo", {}) or {}
    reduccion_penalties = penalties.get("reduccion", {}) or {}

    gain_clip_min = float(gain_clip.get("min", -100))
    gain_clip_max = float(gain_clip.get("max", 150))
    mom_week = float(momentum_weights.get("week", 0.2))
    mom_month = float(momentum_weights.get("month", 0.4))
    mom_ytd = float(momentum_weights.get("ytd", 0.4))
    ref_soft_pct = float(concentration_rules.get("refuerzo_soft_pct", 3.0))
    ref_hard_pct = float(concentration_rules.get("refuerzo_hard_pct", 5.0))
    red_soft_pct = float(concentration_rules.get("reduccion_soft_pct", 3.5))
    red_hard_pct = float(concentration_rules.get("reduccion_hard_pct", 6.0))

    out = decision.copy()
    numeric_defaults = {
        "Peso_%": np.nan,
        "Perf Week": np.nan,
        "Perf Month": np.nan,
        "Perf YTD": np.nan,
        "Beta": np.nan,
        "P/E": np.nan,
        "ROE": np.nan,
        "Profit Margin": np.nan,
        "MEP_Premium_%": np.nan,
        "Consensus_Final": rank_neutral,
        "Ganancia_%": np.nan,
        "Ganancia_ARS": np.nan,
    }
    bool_defaults = {
        "Es_Liquidez": False,
        "Es_Bono": False,
    }
    for col, default in numeric_defaults.items():
        if col not in out.columns:
            out[col] = default
    for col, default in bool_defaults.items():
        if col not in out.columns:
            out[col] = default
    out["s_low_weight"] = rank_score(out["Peso_%"], higher_is_better=False, neutral=rank_neutral)
    out["s_high_weight"] = rank_score(out["Peso_%"], higher_is_better=True, neutral=rank_neutral)
    out["s_mom_week"] = rank_score(out["Perf Week"], higher_is_better=True, neutral=rank_neutral)
    out["s_mom_month"] = rank_score(out["Perf Month"], higher_is_better=True, neutral=rank_neutral)
    out["s_mom_ytd"] = rank_score(out["Perf YTD"], higher_is_better=True, neutral=rank_neutral)
    out["s_weak_mom_week"] = rank_score(out["Perf Week"], higher_is_better=False, neutral=rank_neutral)
    out["s_weak_mom_month"] = rank_score(out["Perf Month"], higher_is_better=False, neutral=rank_neutral)
    out["s_weak_mom_ytd"] = rank_score(out["Perf YTD"], higher_is_better=False, neutral=rank_neutral)
    out["s_beta_ok"] = rank_score(out["Beta"], higher_is_better=False, neutral=rank_neutral)
    out["s_beta_risk"] = rank_score(out["Beta"], higher_is_better=True, neutral=rank_neutral)
    out["s_pe_ok"] = rank_score(out["P/E"], higher_is_better=False, neutral=rank_neutral)
    out["s_pe_expensive"] = rank_score(out["P/E"], higher_is_better=True, neutral=rank_neutral)
    out["s_quality_roe"] = rank_score(out["ROE"], higher_is_better=True, neutral=rank_neutral)
    out["s_quality_margin"] = rank_score(out["Profit Margin"], higher_is_better=True, neutral=rank_neutral)
    out["s_mep_ok"] = rank_score(out["MEP_Premium_%"], higher_is_better=False, neutral=rank_neutral)
    out["s_mep_premium"] = rank_score(out["MEP_Premium_%"], higher_is_better=True, neutral=rank_neutral)
    out["s_consensus_good"] = out["Consensus_Final"].fillna(0.5)
    out["s_consensus_bad"] = 1 - out["s_consensus_good"]
    out["Ganancia_%_Cap"] = out["Ganancia_%"].clip(lower=gain_clip_min, upper=gain_clip_max)
    out["s_big_gain"] = rank_score(out["Ganancia_%_Cap"], higher_is_better=True, neutral=rank_neutral)
    out["s_big_loss"] = rank_score(out["Ganancia_%_Cap"], higher_is_better=False, neutral=rank_neutral)
    quality_parts = pd.concat([out["s_quality_roe"], out["s_quality_margin"]], axis=1)
    out["s_quality"] = quality_parts.mean(axis=1).fillna(rank_neutral)
    out["s_low_quality"] = 1 - out["s_quality"]
    out["s_concentration_room"] = np.where(
        out["Peso_%"].isna(),
        rank_neutral,
        np.where(
            out["Peso_%"] <= ref_soft_pct,
            1.0,
            np.where(
                out["Peso_%"] >= ref_hard_pct,
                0.0,
                1 - ((out["Peso_%"] - ref_soft_pct) / max(ref_hard_pct - ref_soft_pct, 1e-9)),
            ),
        ),
    )
    out["s_concentration_pressure"] = np.where(
        out["Peso_%"].isna(),
        rank_neutral,
        np.where(
            out["Peso_%"] <= red_soft_pct,
            0.0,
            np.where(
                out["Peso_%"] >= red_hard_pct,
                1.0,
                (out["Peso_%"] - red_soft_pct) / max(red_hard_pct - red_soft_pct, 1e-9),
            ),
        ),
    )

    out["Momentum_Refuerzo"] = mom_week * out["s_mom_week"] + mom_month * out["s_mom_month"] + mom_ytd * out["s_mom_ytd"]
    out["Momentum_Reduccion"] = (
        mom_week * out["s_weak_mom_week"] + mom_month * out["s_weak_mom_month"] + mom_ytd * out["s_weak_mom_ytd"]
    )

    out["score_refuerzo"] = (
        float(score_refuerzo_weights.get("low_weight", 0.20)) * out["s_low_weight"]
        + float(score_refuerzo_weights.get("momentum", 0.25)) * out["Momentum_Refuerzo"]
        + float(score_refuerzo_weights.get("consensus_good", 0.15)) * out["s_consensus_good"]
        + float(score_refuerzo_weights.get("beta_ok", 0.10)) * out["s_beta_ok"]
        + float(score_refuerzo_weights.get("mep_ok", 0.10)) * out["s_mep_ok"]
        + float(score_refuerzo_weights.get("pe_ok", 0.10)) * out["s_pe_ok"]
        + float(score_refuerzo_weights.get("big_gain_inverse", 0.10)) * (1 - out["s_big_gain"])
        + float(score_refuerzo_weights.get("concentration_room", 0.0)) * out["s_concentration_room"]
        + float(score_refuerzo_weights.get("quality", 0.0)) * out["s_quality"]
    )
    out["score_refuerzo"] -= np.where(out["Es_Liquidez"], float(refuerzo_penalties.get("liquidez", 0.35)), 0.00)
    out["score_refuerzo"] -= np.where(out["Es_Bono"], float(refuerzo_penalties.get("bono", 0.08)), 0.00)
    out["score_refuerzo"] -= np.where(
        out["Beta"].fillna(0) > float(refuerzo_penalties.get("beta_high_threshold", 1.8)),
        float(refuerzo_penalties.get("beta_high", 0.08)),
        0.00,
    )
    out["score_refuerzo"] = out["score_refuerzo"].clip(0, 1)

    out["score_reduccion"] = (
        float(score_reduccion_weights.get("high_weight", 0.25)) * out["s_high_weight"]
        + float(score_reduccion_weights.get("momentum", 0.20)) * out["Momentum_Reduccion"]
        + float(score_reduccion_weights.get("beta_risk", 0.15)) * out["s_beta_risk"]
        + float(score_reduccion_weights.get("mep_premium", 0.10)) * out["s_mep_premium"]
        + float(score_reduccion_weights.get("consensus_bad", 0.10)) * out["s_consensus_bad"]
        + float(score_reduccion_weights.get("pe_expensive", 0.10)) * out["s_pe_expensive"]
        + float(score_reduccion_weights.get("big_gain", 0.10)) * out["s_big_gain"]
        + float(score_reduccion_weights.get("concentration_pressure", 0.0)) * out["s_concentration_pressure"]
        + float(score_reduccion_weights.get("low_quality", 0.0)) * out["s_low_quality"]
    )
    out["score_reduccion"] -= np.where(out["Es_Liquidez"], float(reduccion_penalties.get("liquidez", 0.25)), 0.00)
    out["score_reduccion"] -= np.where(out["Es_Bono"], float(reduccion_penalties.get("bono", 0.05)), 0.00)
    out["score_reduccion"] = out["score_reduccion"].clip(0, 1)

    out["score_despliegue_liquidez"] = 0.0
    mask_liq = out["Es_Liquidez"]
    out.loc[mask_liq, "score_despliegue_liquidez"] = (
        float(score_despliegue_liquidez_weights.get("peso", 0.60))
        * rank_score(out.loc[mask_liq, "Peso_%"], higher_is_better=True, neutral=rank_neutral)
        + float(score_despliegue_liquidez_weights.get("ganancia_inversa", 0.40))
        * rank_score(out.loc[mask_liq, "Ganancia_ARS"], higher_is_better=False, neutral=rank_neutral)
    ).clip(0, 1)

    return out


def clamp01(value: pd.Series | float) -> pd.Series | float:
    return np.clip(value, 0, 1)


def build_technical_overlay_scores(
    decision: pd.DataFrame,
    technical_overlay: pd.DataFrame | None,
    *,
    scoring_rules: dict[str, object] | None = None,
) -> pd.DataFrame:
    out = decision.copy()
    if technical_overlay is None or technical_overlay.empty:
        return out

    scoring_rules = scoring_rules or {}
    tech_rules = scoring_rules.get("technical_overlay", {}) or {}
    if tech_rules.get("enabled", True) is False:
        return out

    metric_cols = [
        "Dist_SMA20_%",
        "Dist_SMA50_%",
        "Dist_EMA20_%",
        "Dist_EMA50_%",
        "RSI_14",
        "Momentum_20d_%",
        "Momentum_60d_%",
        "Vol_20d_Anual_%",
        "Drawdown_desde_Max3m_%",
    ]
    merge_cols = [
        "Ticker_IOL",
        *metric_cols,
        "Tech_Trend",
    ]
    available_cols = [col for col in merge_cols if col in technical_overlay.columns]
    available_metric_cols = [col for col in metric_cols if col in technical_overlay.columns]
    if not available_metric_cols:
        return out
    overlay = technical_overlay[available_cols].copy()
    out = out.merge(overlay, on="Ticker_IOL", how="left")

    if out[available_metric_cols].notna().sum().sum() == 0:
        return decision.copy()

    subscores = tech_rules.get("subscores", {}) or {}
    out["ts_above_sma20"] = clamp01((out["Dist_SMA20_%"].fillna(0) + 10) / 20)
    out["ts_above_sma50"] = clamp01((out["Dist_SMA50_%"].fillna(0) + 15) / 30)
    out["ts_above_ema20"] = clamp01((out["Dist_EMA20_%"].fillna(0) + 10) / 20)
    out["ts_above_ema50"] = clamp01((out["Dist_EMA50_%"].fillna(0) + 15) / 30)
    out["ts_rsi"] = np.where(
        out["RSI_14"].isna(),
        0.5,
        np.select(
            [
                out["RSI_14"] < 30,
                (out["RSI_14"] >= 30) & (out["RSI_14"] < 45),
                (out["RSI_14"] >= 45) & (out["RSI_14"] <= 65),
                (out["RSI_14"] > 65) & (out["RSI_14"] <= 75),
                out["RSI_14"] > 75,
            ],
            [0.35, 0.60, 1.00, 0.65, 0.30],
            default=0.5,
        ),
    )
    out["ts_mom20"] = clamp01((out["Momentum_20d_%"].fillna(0) + 15) / 30)
    out["ts_mom60"] = clamp01((out["Momentum_60d_%"].fillna(0) + 25) / 50)
    out["ts_drawdown"] = np.where(
        out["Drawdown_desde_Max3m_%"].isna(),
        0.5,
        clamp01((out["Drawdown_desde_Max3m_%"].fillna(-20) + 25) / 25),
    )
    out["ts_volatility"] = np.where(
        out["Vol_20d_Anual_%"].isna(),
        0.5,
        1 - clamp01((out["Vol_20d_Anual_%"] - 15) / 45),
    )
    out["tech_refuerzo"] = (
        float(subscores.get("above_sma20", 0.15)) * out["ts_above_sma20"]
        + float(subscores.get("above_sma50", 0.15)) * out["ts_above_sma50"]
        + float(subscores.get("above_ema20", 0.10)) * out["ts_above_ema20"]
        + float(subscores.get("above_ema50", 0.10)) * out["ts_above_ema50"]
        + float(subscores.get("rsi", 0.15)) * out["ts_rsi"]
        + float(subscores.get("mom20", 0.15)) * out["ts_mom20"]
        + float(subscores.get("mom60", 0.10)) * out["ts_mom60"]
        + float(subscores.get("drawdown", 0.05)) * out["ts_drawdown"]
        + float(subscores.get("volatility", 0.05)) * out["ts_volatility"]
    ).clip(0, 1)
    return out


def apply_technical_overlay_scores(
    decision_tech: pd.DataFrame,
    *,
    scoring_rules: dict[str, object] | None = None,
) -> pd.DataFrame:
    out = decision_tech.copy()
    if "tech_refuerzo" not in out.columns:
        return out
    scoring_rules = scoring_rules or {}
    tech_rules = scoring_rules.get("technical_overlay", {}) or {}
    blend_base = float(tech_rules.get("blend_base", 0.75))
    blend_tech = float(tech_rules.get("blend_tech", 0.25))
    out["tech_reduccion"] = 1 - out["tech_refuerzo"]
    out["score_refuerzo_v2"] = (blend_base * out["score_refuerzo"] + blend_tech * out["tech_refuerzo"]).clip(0, 1)
    out["score_reduccion_v2"] = (blend_base * out["score_reduccion"] + blend_tech * out["tech_reduccion"]).clip(0, 1)
    out["score_unificado_v2"] = (out["score_refuerzo_v2"] - out["score_reduccion_v2"]).round(3)
    return out


def finalize_unified_score(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "score_unificado_v2" in out.columns:
        out["score_unificado"] = (out["score_refuerzo_v2"] - out["score_reduccion_v2"]).round(3)
    else:
        out["score_unificado"] = (out["score_refuerzo"] - out["score_reduccion"]).round(3)
    return out
