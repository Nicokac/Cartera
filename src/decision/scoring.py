from __future__ import annotations

import numpy as np
import pandas as pd

from common.numeric import positive_float_or_none, to_float_or_none


def rank_score(series: pd.Series, higher_is_better: bool = True, neutral: float = 0.5) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    out = pd.Series(neutral, index=s.index, dtype=float)
    valid = s.notna()
    if valid.any():
        ranks = s[valid].rank(pct=True, method="average")
        relative_scores = ranks if higher_is_better else (1 - ranks)
        valid_count = int(valid.sum())
        if valid_count <= 1:
            out.loc[valid] = neutral
        elif valid_count <= 4:
            # Small cohorts are too thin for a fully relative percentile.
            # Damp the relative spread toward neutral while still preserving order.
            damping = (valid_count - 1) / valid_count
            out.loc[valid] = ((relative_scores - neutral) * damping) + neutral
        else:
            out.loc[valid] = relative_scores
    return out


def threshold_score(
    series: pd.Series,
    *,
    good: float,
    bad: float,
    higher_is_better: bool,
    neutral: float = 0.5,
) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    out = pd.Series(neutral, index=s.index, dtype=float)
    valid = s.notna()
    if not valid.any():
        return out

    spread = max(abs(float(bad) - float(good)), 1e-9)
    if higher_is_better:
        raw = (s[valid] - float(bad)) / spread
    else:
        raw = (float(bad) - s[valid]) / spread
    out.loc[valid] = np.clip(raw, 0, 1)
    return out


def blend_scores(relative: pd.Series, absolute: pd.Series, *, relative_weight: float, absolute_weight: float) -> pd.Series:
    total = max(float(relative_weight) + float(absolute_weight), 1e-9)
    return ((float(relative_weight) * relative) + (float(absolute_weight) * absolute)) / total


def _market_value(market_context: dict[str, object] | None, key: str) -> float | None:
    if not market_context:
        return None
    return to_float_or_none(market_context.get(key))


def detect_market_regime_flags(
    market_context: dict[str, object] | None,
    *,
    scoring_rules: dict[str, object] | None = None,
) -> dict[str, bool]:
    scoring_rules = scoring_rules or {}
    regime_rules = scoring_rules.get("market_regime", {}) or {}
    if regime_rules.get("enabled", True) is False:
        return {}

    flag_rules = regime_rules.get("flags", {}) or {}
    stress_soberano_rules = flag_rules.get("stress_soberano_local", {}) or {}
    inflacion_rules = flag_rules.get("inflacion_local_alta", {}) or {}
    ust_rules = flag_rules.get("tasas_ust_altas", {}) or {}

    riesgo_pais_bps = _market_value(market_context, "riesgo_pais_bps")
    rem_12m = _market_value(market_context, "rem_inflacion_12m_pct")
    rem_mensual = _market_value(market_context, "rem_inflacion_mensual_pct")
    ust_5y = _market_value(market_context, "ust_5y_pct")
    ust_10y = _market_value(market_context, "ust_10y_pct")

    flags = {
        "stress_soberano_local": bool(
            riesgo_pais_bps is not None
            and riesgo_pais_bps >= float(stress_soberano_rules.get("riesgo_pais_bps_min", 800.0))
        ),
        "inflacion_local_alta": bool(
            (rem_12m is not None and rem_12m >= float(inflacion_rules.get("rem_inflacion_12m_pct_min", 30.0)))
            or (
                rem_mensual is not None
                and rem_mensual >= float(inflacion_rules.get("rem_inflacion_mensual_pct_min", 3.0))
            )
        ),
        "tasas_ust_altas": bool(
            (ust_10y is not None and ust_10y >= float(ust_rules.get("ust_10y_pct_min", 4.5)))
            or (ust_5y is not None and ust_5y >= float(ust_rules.get("ust_5y_pct_min", 4.25)))
        ),
    }
    return flags


def apply_market_regime_adjustments(
    df: pd.DataFrame,
    *,
    market_context: dict[str, object] | None = None,
    scoring_rules: dict[str, object] | None = None,
) -> pd.DataFrame:
    out = df.copy()
    scoring_rules = scoring_rules or {}
    regime_rules = scoring_rules.get("market_regime", {}) or {}
    if regime_rules.get("enabled", True) is False:
        return out

    flags = detect_market_regime_flags(market_context, scoring_rules=scoring_rules)
    adjustments = regime_rules.get("adjustments", {}) or {}

    for flag_name, is_active in flags.items():
        out[f"market_regime_{flag_name}"] = bool(is_active)
    active_flags = [flag_name for flag_name, is_active in flags.items() if is_active]
    out["market_regime_flags"] = ", ".join(active_flags) if active_flags else None

    if "asset_family" not in out.columns:
        out["asset_family"] = None
    if "asset_subfamily" not in out.columns:
        out["asset_subfamily"] = None

    for flag_name in active_flags:
        per_flag = adjustments.get(flag_name, {}) or {}
        for target, delta_rules in per_flag.items():
            delta_rules = delta_rules or {}
            refuerzo_delta = float(delta_rules.get("refuerzo_delta", 0.0))
            reduccion_delta = float(delta_rules.get("reduccion_delta", 0.0))
            if not refuerzo_delta and not reduccion_delta:
                continue

            if target.startswith("family:"):
                family = target.split(":", 1)[1]
                mask = out["asset_family"].eq(family)
            else:
                mask = out["asset_subfamily"].eq(target)

            if refuerzo_delta:
                out["score_refuerzo"] += np.where(mask, refuerzo_delta, 0.0)
            if reduccion_delta:
                out["score_reduccion"] += np.where(mask, reduccion_delta, 0.0)

    out["score_refuerzo"] = out["score_refuerzo"].clip(0, 1)
    out["score_reduccion"] = out["score_reduccion"].clip(0, 1)
    return out


def build_market_regime_summary(
    market_context: dict[str, object] | None,
    *,
    scoring_rules: dict[str, object] | None = None,
) -> dict[str, object]:
    flags = detect_market_regime_flags(market_context, scoring_rules=scoring_rules)
    return {
        "flags": flags,
        "active_flags": [name for name, active in flags.items() if active],
        "any_active": any(flags.values()) if flags else False,
    }


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
    mep_value = positive_float_or_none(mep_real)
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
    base = df_total.copy()
    for col in decision_cols:
        if col not in base.columns:
            base[col] = np.nan
    base = base.reindex(columns=decision_cols).copy()
    cantidad_real = pd.to_numeric(base["Cantidad_Real"], errors="coerce").fillna(0)
    ppc_ars = pd.to_numeric(base["PPC_ARS"], errors="coerce").fillna(0)
    base["Costo_ARS"] = cantidad_real * ppc_ars
    base["Ganancia_%"] = np.where(
        base["Costo_ARS"] > 0,
        base["Ganancia_ARS"] / base["Costo_ARS"] * 100,
        np.nan,
    )

    ced_cols = [
        "Ticker_IOL",
        "Ticker_Finviz",
        "instrument_class",
        "asset_family",
        "asset_subfamily",
        "is_etf",
        "is_core_etf",
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
    if "Es_Liquidez" in decision.columns:
        decision["Es_Liquidez"] = decision["Es_Liquidez"].fillna(decision["Tipo"].eq("Liquidez")).astype(bool)
    else:
        decision["Es_Liquidez"] = decision["Tipo"].eq("Liquidez")
    decision["Es_Cedear"] = decision["Tipo"].eq("CEDEAR")
    decision["Es_Bono"] = decision["Tipo"].eq("Bono")
    decision["Es_FCI"] = decision["Tipo"].eq("FCI")
    decision["Es_Accion_Local"] = decision["Tipo"].eq("Acción Local")
    decision["Es_ETF"] = decision["is_etf"].fillna(False).astype(bool) if "is_etf" in decision.columns else False
    decision["Es_Core_ETF"] = (
        decision["is_core_etf"].fillna(False).astype(bool) if "is_core_etf" in decision.columns else False
    )
    decision["asset_family"] = decision.get("asset_family")
    decision["asset_subfamily"] = decision.get("asset_subfamily")
    decision["asset_family"] = decision["asset_family"].astype("object")
    decision["asset_subfamily"] = decision["asset_subfamily"].astype("object")
    decision["asset_family"] = decision["asset_family"].where(decision["asset_family"].notna(), None)
    decision["asset_subfamily"] = decision["asset_subfamily"].where(decision["asset_subfamily"].notna(), None)
    decision.loc[decision["Es_Liquidez"], "asset_family"] = "liquidity"
    decision.loc[decision["Es_FCI"], "asset_family"] = "fund"
    decision.loc[decision["Es_Bono"], "asset_family"] = "bond"
    decision.loc[decision["Es_Accion_Local"], "asset_family"] = "stock"
    decision.loc[decision["Es_Cedear"] & ~decision["Es_ETF"], "asset_family"] = "stock"
    decision.loc[decision["Es_ETF"] & decision["Es_Core_ETF"], "asset_subfamily"] = "etf_core"
    decision.loc[decision["Es_ETF"] & decision["asset_subfamily"].isna(), "asset_subfamily"] = "etf_other"
    decision.loc[
        decision["asset_family"].eq("stock") & decision["Bloque"].isin(["Growth"]),
        "asset_subfamily",
    ] = "stock_growth"
    decision.loc[
        decision["asset_family"].eq("stock") & decision["Bloque"].isin(["Dividendos", "Defensivo"]),
        "asset_subfamily",
    ] = "stock_defensive_dividend"
    decision.loc[
        decision["asset_family"].eq("stock") & decision["Bloque"].isin(["Commodities"]),
        "asset_subfamily",
    ] = "stock_commodity"
    decision.loc[
        decision["asset_family"].eq("stock") & decision["Bloque"].isin(["Argentina"]),
        "asset_subfamily",
    ] = "stock_argentina"
    decision.loc[
        decision["asset_family"].eq("stock") & decision["asset_subfamily"].isna(),
        "asset_subfamily",
    ] = "stock_other"
    decision.loc[
        decision["Es_Bono"] & decision["Bloque"].eq("Soberano AR"),
        "asset_subfamily",
    ] = "bond_sov_ar"
    decision.loc[
        decision["Es_Bono"] & decision["Bloque"].eq("CER"),
        "asset_subfamily",
    ] = "bond_cer"
    decision.loc[
        decision["Es_Bono"] & decision["Bloque"].eq("Bopreal"),
        "asset_subfamily",
    ] = "bond_bopreal"
    decision.loc[
        decision["Es_Bono"] & decision["asset_subfamily"].isna(),
        "asset_subfamily",
    ] = "bond_other"
    decision.loc[
        decision["Es_Liquidez"] & decision["asset_subfamily"].isna(),
        "asset_subfamily",
    ] = "liquidity_other"
    decision.loc[
        decision["Es_FCI"] & decision["asset_subfamily"].isna(),
        "asset_subfamily",
    ] = "fund_other"
    decision["MEP_Premium_%"] = np.nan
    if mep_value is not None:
        premium_mask = decision["MEP_Implicito"].notna()
        decision.loc[premium_mask, "MEP_Premium_%"] = (
            decision.loc[premium_mask, "MEP_Implicito"] / mep_value - 1
        ) * 100

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


def apply_base_scores(
    decision: pd.DataFrame,
    *,
    scoring_rules: dict[str, object] | None = None,
    market_context: dict[str, object] | None = None,
) -> pd.DataFrame:
    scoring_rules = scoring_rules or {}
    rank_neutral = float(scoring_rules.get("rank_neutral", 0.5))
    gain_clip = scoring_rules.get("gain_clip", {}) or {}
    momentum_weights = scoring_rules.get("momentum_weights", {}) or {}
    score_refuerzo_weights = scoring_rules.get("score_refuerzo_weights", {}) or {}
    score_reduccion_weights = scoring_rules.get("score_reduccion_weights", {}) or {}
    score_despliegue_liquidez_weights = scoring_rules.get("score_despliegue_liquidez_weights", {}) or {}
    concentration_rules = scoring_rules.get("concentration", {}) or {}
    etf_adjustments = scoring_rules.get("etf_adjustments", {}) or {}
    asset_subfamily_adjustments = scoring_rules.get("asset_subfamily_adjustments", {}) or {}
    penalties = scoring_rules.get("penalties", {}) or {}
    refuerzo_penalties = penalties.get("refuerzo", {}) or {}
    reduccion_penalties = penalties.get("reduccion", {}) or {}
    absolute_rules = scoring_rules.get("absolute_scoring", {}) or {}

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
        "Es_ETF": False,
        "Es_Core_ETF": False,
        "Es_FCI": False,
    }
    for col, default in numeric_defaults.items():
        if col not in out.columns:
            out[col] = default
    for col, default in bool_defaults.items():
        if col not in out.columns:
            out[col] = default
    if "asset_family" not in out.columns:
        out["asset_family"] = None
    if "asset_subfamily" not in out.columns:
        out["asset_subfamily"] = None
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

    if bool(absolute_rules.get("enabled", False)):
        relative_weight = float(absolute_rules.get("relative_weight", 0.7))
        absolute_weight = float(absolute_rules.get("absolute_weight", 0.3))
        metrics = absolute_rules.get("metrics", {}) or {}

        beta_rules = metrics.get("beta", {}) or {}
        pe_rules = metrics.get("pe", {}) or {}
        roe_rules = metrics.get("roe", {}) or {}
        margin_rules = metrics.get("profit_margin", {}) or {}
        mep_rules = metrics.get("mep_premium_pct", {}) or {}
        gain_rules = metrics.get("ganancia_pct_cap", {}) or {}

        abs_beta_ok = threshold_score(
            out["Beta"],
            good=float(beta_rules.get("good_max", 0.8)),
            bad=float(beta_rules.get("bad_min", 1.5)),
            higher_is_better=False,
            neutral=rank_neutral,
        )
        abs_beta_risk = threshold_score(
            out["Beta"],
            good=float(beta_rules.get("bad_min", 1.5)),
            bad=float(beta_rules.get("good_max", 0.8)),
            higher_is_better=True,
            neutral=rank_neutral,
        )
        abs_pe_ok = threshold_score(
            out["P/E"],
            good=float(pe_rules.get("good_max", 18.0)),
            bad=float(pe_rules.get("bad_min", 30.0)),
            higher_is_better=False,
            neutral=rank_neutral,
        )
        abs_pe_expensive = threshold_score(
            out["P/E"],
            good=float(pe_rules.get("bad_min", 30.0)),
            bad=float(pe_rules.get("good_max", 18.0)),
            higher_is_better=True,
            neutral=rank_neutral,
        )
        abs_quality_roe = threshold_score(
            out["ROE"],
            good=float(roe_rules.get("good_min", 20.0)),
            bad=float(roe_rules.get("bad_max", 5.0)),
            higher_is_better=True,
            neutral=rank_neutral,
        )
        abs_quality_margin = threshold_score(
            out["Profit Margin"],
            good=float(margin_rules.get("good_min", 20.0)),
            bad=float(margin_rules.get("bad_max", 5.0)),
            higher_is_better=True,
            neutral=rank_neutral,
        )
        abs_mep_ok = threshold_score(
            out["MEP_Premium_%"],
            good=float(mep_rules.get("good_max", -90.0)),
            bad=float(mep_rules.get("bad_min", 10.0)),
            higher_is_better=False,
            neutral=rank_neutral,
        )
        abs_mep_premium = threshold_score(
            out["MEP_Premium_%"],
            good=float(mep_rules.get("bad_min", 10.0)),
            bad=float(mep_rules.get("good_max", -90.0)),
            higher_is_better=True,
            neutral=rank_neutral,
        )
        abs_big_gain = threshold_score(
            out["Ganancia_%_Cap"],
            good=float(gain_rules.get("bad_min", 80.0)),
            bad=float(gain_rules.get("good_max", 10.0)),
            higher_is_better=True,
            neutral=rank_neutral,
        )
        abs_big_loss = threshold_score(
            out["Ganancia_%_Cap"],
            good=float(gain_rules.get("bad_loss_max", -20.0)),
            bad=float(gain_rules.get("good_max", 10.0)),
            higher_is_better=False,
            neutral=rank_neutral,
        )

        out["s_beta_ok"] = blend_scores(out["s_beta_ok"], abs_beta_ok, relative_weight=relative_weight, absolute_weight=absolute_weight)
        out["s_beta_risk"] = blend_scores(
            out["s_beta_risk"], abs_beta_risk, relative_weight=relative_weight, absolute_weight=absolute_weight
        )
        out["s_pe_ok"] = blend_scores(out["s_pe_ok"], abs_pe_ok, relative_weight=relative_weight, absolute_weight=absolute_weight)
        out["s_pe_expensive"] = blend_scores(
            out["s_pe_expensive"], abs_pe_expensive, relative_weight=relative_weight, absolute_weight=absolute_weight
        )
        out["s_quality_roe"] = blend_scores(
            out["s_quality_roe"], abs_quality_roe, relative_weight=relative_weight, absolute_weight=absolute_weight
        )
        out["s_quality_margin"] = blend_scores(
            out["s_quality_margin"], abs_quality_margin, relative_weight=relative_weight, absolute_weight=absolute_weight
        )
        out["s_mep_ok"] = blend_scores(out["s_mep_ok"], abs_mep_ok, relative_weight=relative_weight, absolute_weight=absolute_weight)
        out["s_mep_premium"] = blend_scores(
            out["s_mep_premium"], abs_mep_premium, relative_weight=relative_weight, absolute_weight=absolute_weight
        )
        out["s_big_gain"] = blend_scores(
            out["s_big_gain"], abs_big_gain, relative_weight=relative_weight, absolute_weight=absolute_weight
        )
        out["s_big_loss"] = blend_scores(
            out["s_big_loss"], abs_big_loss, relative_weight=relative_weight, absolute_weight=absolute_weight
        )
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
    etf_quality_floor = float(etf_adjustments.get("quality_floor", rank_neutral))
    etf_pe_discount = float(etf_adjustments.get("pe_expensive_discount", 1.0))
    etf_low_quality_discount = float(etf_adjustments.get("low_quality_discount", 1.0))
    etf_concentration_discount = float(etf_adjustments.get("concentration_pressure_discount", 1.0))
    core_concentration_discount = float(etf_adjustments.get("core_concentration_pressure_discount", 1.0))
    core_momentum_discount = float(etf_adjustments.get("core_momentum_reduccion_discount", 1.0))
    out["s_quality_effective"] = np.where(
        out["Es_ETF"],
        np.maximum(out["s_quality"], etf_quality_floor),
        out["s_quality"],
    )
    out["has_quality_data"] = out[["ROE", "Profit Margin"]].notna().any(axis=1)
    out["has_valuation_data"] = out["P/E"].notna()
    out["has_ratings_data"] = out.get("total_ratings", pd.Series(index=out.index, dtype=float)).fillna(0) > 0
    out["has_fundamental_support"] = out["has_quality_data"] | out["has_valuation_data"] | out["has_ratings_data"]
    out["s_low_quality_effective"] = 1 - out["s_quality_effective"]
    out["s_pe_expensive_effective"] = np.where(
        out["Es_ETF"],
        rank_neutral + (out["s_pe_expensive"] - rank_neutral) * etf_pe_discount,
        out["s_pe_expensive"],
    )
    out["s_low_quality_effective"] = np.where(
        out["Es_ETF"],
        rank_neutral + (out["s_low_quality_effective"] - rank_neutral) * etf_low_quality_discount,
        out["s_low_quality_effective"],
    )
    out["s_concentration_pressure_effective"] = np.where(
        out["Es_ETF"],
        out["s_concentration_pressure"] * etf_concentration_discount,
        out["s_concentration_pressure"],
    )
    out["s_concentration_pressure_effective"] = np.where(
        out["Es_Core_ETF"],
        out["s_concentration_pressure_effective"] * core_concentration_discount,
        out["s_concentration_pressure_effective"],
    )
    out["Momentum_Reduccion_Effective"] = np.where(
        out["Es_Core_ETF"],
        out["Momentum_Reduccion"] * core_momentum_discount,
        out["Momentum_Reduccion"],
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
        + float(score_refuerzo_weights.get("quality", 0.0)) * out["s_quality_effective"]
    )
    out["score_refuerzo"] -= np.where(out["Es_Liquidez"], float(refuerzo_penalties.get("liquidez", 0.35)), 0.00)
    out["score_refuerzo"] -= np.where(out["Es_FCI"], 1.0, 0.00)
    out["score_refuerzo"] -= np.where(out["Es_Bono"], float(refuerzo_penalties.get("bono", 0.08)), 0.00)
    out["score_refuerzo"] -= np.where(
        out["Beta"].fillna(0) > float(refuerzo_penalties.get("beta_high_threshold", 1.8)),
        float(refuerzo_penalties.get("beta_high", 0.08)),
        0.00,
    )
    for subfamily, rules in asset_subfamily_adjustments.items():
        mask = out["asset_subfamily"].eq(subfamily)
        refuerzo_penalty = float((rules or {}).get("refuerzo_penalty", 0.0))
        refuerzo_boost = float((rules or {}).get("refuerzo_boost", 0.0))
        sparse_data_penalty = float((rules or {}).get("sparse_data_penalty", 0.0))
        if refuerzo_penalty:
            out["score_refuerzo"] -= np.where(mask, refuerzo_penalty, 0.0)
        if refuerzo_boost:
            out["score_refuerzo"] += np.where(mask, refuerzo_boost, 0.0)
        if sparse_data_penalty:
            out["score_refuerzo"] -= np.where(mask & ~out["has_fundamental_support"], sparse_data_penalty, 0.0)
    out["score_refuerzo"] = out["score_refuerzo"].clip(0, 1)

    out["score_reduccion"] = (
        float(score_reduccion_weights.get("high_weight", 0.25)) * out["s_high_weight"]
        + float(score_reduccion_weights.get("momentum", 0.20)) * out["Momentum_Reduccion_Effective"]
        + float(score_reduccion_weights.get("beta_risk", 0.15)) * out["s_beta_risk"]
        + float(score_reduccion_weights.get("mep_premium", 0.10)) * out["s_mep_premium"]
        + float(score_reduccion_weights.get("consensus_bad", 0.10)) * out["s_consensus_bad"]
        + float(score_reduccion_weights.get("pe_expensive", 0.10)) * out["s_pe_expensive_effective"]
        + float(score_reduccion_weights.get("big_gain", 0.10)) * out["s_big_gain"]
        + float(score_reduccion_weights.get("concentration_pressure", 0.0)) * out["s_concentration_pressure_effective"]
        + float(score_reduccion_weights.get("low_quality", 0.0)) * out["s_low_quality_effective"]
    )
    out["score_reduccion"] -= np.where(out["Es_Liquidez"], float(reduccion_penalties.get("liquidez", 0.25)), 0.00)
    out["score_reduccion"] -= np.where(out["Es_FCI"], 1.0, 0.00)
    out["score_reduccion"] -= np.where(out["Es_Bono"], float(reduccion_penalties.get("bono", 0.05)), 0.00)
    for subfamily, rules in asset_subfamily_adjustments.items():
        mask = out["asset_subfamily"].eq(subfamily)
        reduccion_boost = float((rules or {}).get("reduccion_boost", 0.0))
        high_gain_reduccion_boost = float((rules or {}).get("high_gain_reduccion_boost", 0.0))
        high_gain_threshold_pct = float((rules or {}).get("high_gain_threshold_pct", gain_clip_max))
        if reduccion_boost:
            out["score_reduccion"] += np.where(mask, reduccion_boost, 0.0)
        if high_gain_reduccion_boost:
            out["score_reduccion"] += np.where(
                mask & (out["Ganancia_%_Cap"].fillna(gain_clip_min) >= high_gain_threshold_pct),
                high_gain_reduccion_boost,
                0.0,
            )
    out = apply_market_regime_adjustments(out, market_context=market_context, scoring_rules=scoring_rules)
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


def _scaled_centered(series: pd.Series, *, floor: float, ceiling: float, fill: float = 0.5) -> pd.Series:
    spread = max(float(ceiling) - float(floor), 1e-9)
    return clamp01((pd.to_numeric(series, errors="coerce").fillna(0) - float(floor)) / spread).fillna(fill)


def _series_or_default(df: pd.DataFrame, column: str, default: float = 0.5) -> pd.Series:
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce").fillna(default)
    return pd.Series(default, index=df.index, dtype=float)


def _rsi_band_score(series: pd.Series, rsi_rules: dict[str, object], *, prefix: str = "") -> pd.Series:
    oversold_max = float(rsi_rules.get("oversold_max", 30.0))
    weak_max = float(rsi_rules.get("weak_max", 45.0))
    strong_max = float(rsi_rules.get("strong_max", 65.0))
    overbought_max = float(rsi_rules.get("overbought_max", 75.0))

    reduction_defaults = {
        "oversold_score": 0.10,
        "weak_score": 0.25,
        "strong_score": 0.45,
        "late_score": 0.75,
        "overbought_score": 1.00,
    }

    def _score(name: str, default: float) -> float:
        effective_default = reduction_defaults.get(name, default) if prefix == "reduction_" else default
        return float(rsi_rules.get(f"{prefix}{name}", effective_default))

    return np.where(
        series.isna(),
        0.5,
        np.select(
            [
                series < oversold_max,
                (series >= oversold_max) & (series < weak_max),
                (series >= weak_max) & (series <= strong_max),
                (series > strong_max) & (series <= overbought_max),
                series > overbought_max,
            ],
            [
                _score("oversold_score", 0.35),
                _score("weak_score", 0.60),
                _score("strong_score", 1.00),
                _score("late_score", 0.65),
                _score("overbought_score", 0.30),
            ],
            default=0.5,
        ),
    )


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
    absolute_rules = scoring_rules.get("absolute_scoring", {}) or {}
    if tech_rules.get("enabled", True) is False:
        return out

    metric_cols = [
        "Dist_SMA20_%",
        "Dist_SMA50_%",
        "Dist_SMA200_%",
        "Dist_EMA20_%",
        "Dist_EMA50_%",
        "Dist_52w_High_%",
        "RSI_14",
        "Momentum_20d_%",
        "Momentum_60d_%",
        "Vol_20d_Anual_%",
        "Drawdown_desde_Max3m_%",
    ]
    prediction_passthrough_cols = [
        "ADX_14",
        "DI_plus_14",
        "DI_minus_14",
        "Relative_Volume",
        "Return_1d_%",
        "Return_intraday_%",
    ]
    merge_cols = [
        "Ticker_IOL",
        *metric_cols,
        "Tech_Trend",
        *prediction_passthrough_cols,
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
    ranges = tech_rules.get("ranges", {}) or {}
    dist_sma20 = ranges.get("dist_sma20_pct", {}) or {}
    dist_sma50 = ranges.get("dist_sma50_pct", {}) or {}
    dist_sma200 = ranges.get("dist_sma200_pct", {}) or {}
    dist_ema20 = ranges.get("dist_ema20_pct", {}) or {}
    dist_ema50 = ranges.get("dist_ema50_pct", {}) or {}
    mom20 = ranges.get("momentum_20d_pct", {}) or {}
    mom60 = ranges.get("momentum_60d_pct", {}) or {}
    drawdown = ranges.get("drawdown_desde_max3m_pct", {}) or {}
    volatility = ranges.get("vol_20d_anual_pct", {}) or {}
    rsi_rules = ranges.get("rsi_14", {}) or {}

    out["ts_above_sma20"] = _scaled_centered(
        out["Dist_SMA20_%"],
        floor=float(dist_sma20.get("min", -10.0)),
        ceiling=float(dist_sma20.get("max", 10.0)),
    )
    out["ts_above_sma50"] = _scaled_centered(
        out["Dist_SMA50_%"],
        floor=float(dist_sma50.get("min", -15.0)),
        ceiling=float(dist_sma50.get("max", 15.0)),
    )
    out["ts_above_sma200"] = _scaled_centered(
        out["Dist_SMA200_%"],
        floor=float(dist_sma200.get("min", -25.0)),
        ceiling=float(dist_sma200.get("max", 25.0)),
    )
    out["ts_above_ema20"] = _scaled_centered(
        out["Dist_EMA20_%"],
        floor=float(dist_ema20.get("min", -10.0)),
        ceiling=float(dist_ema20.get("max", 10.0)),
    )
    out["ts_above_ema50"] = _scaled_centered(
        out["Dist_EMA50_%"],
        floor=float(dist_ema50.get("min", -15.0)),
        ceiling=float(dist_ema50.get("max", 15.0)),
    )
    out["ts_rsi"] = _rsi_band_score(pd.to_numeric(out["RSI_14"], errors="coerce"), rsi_rules)
    out["ts_rsi_reduccion"] = _rsi_band_score(
        pd.to_numeric(out["RSI_14"], errors="coerce"),
        rsi_rules,
        prefix="reduction_",
    )
    out["ts_mom20"] = _scaled_centered(
        out["Momentum_20d_%"],
        floor=float(mom20.get("min", -15.0)),
        ceiling=float(mom20.get("max", 15.0)),
    )
    out["ts_mom60"] = _scaled_centered(
        out["Momentum_60d_%"],
        floor=float(mom60.get("min", -25.0)),
        ceiling=float(mom60.get("max", 25.0)),
    )
    out["ts_drawdown"] = np.where(
        out["Drawdown_desde_Max3m_%"].isna(),
        0.5,
        _scaled_centered(
            out["Drawdown_desde_Max3m_%"],
            floor=float(drawdown.get("min", -25.0)),
            ceiling=float(drawdown.get("max", 0.0)),
        ),
    )
    out["ts_volatility"] = np.where(
        out["Vol_20d_Anual_%"].isna(),
        0.5,
        1
        - _scaled_centered(
            out["Vol_20d_Anual_%"],
            floor=float(volatility.get("min", 15.0)),
            ceiling=float(volatility.get("max", 60.0)),
        ),
    )
    out["tech_refuerzo"] = (
        float(subscores.get("above_sma20", 0.15)) * out["ts_above_sma20"]
        + float(subscores.get("above_sma50", 0.15)) * out["ts_above_sma50"]
        + float(subscores.get("above_sma200", 0.05)) * out["ts_above_sma200"]
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
    absolute_rules = scoring_rules.get("absolute_scoring", {}) or {}
    asset_subfamily_adjustments = scoring_rules.get("asset_subfamily_adjustments", {}) or {}
    blend_base = float(tech_rules.get("blend_base", 0.75))
    blend_tech = float(tech_rules.get("blend_tech", 0.25))
    reduction_subscores = tech_rules.get("reduction_subscores", {}) or {}
    out["tech_reduccion"] = (
        float(reduction_subscores.get("below_sma20", 0.15)) * (1 - _series_or_default(out, "ts_above_sma20"))
        + float(reduction_subscores.get("below_sma50", 0.15)) * (1 - _series_or_default(out, "ts_above_sma50"))
        + float(reduction_subscores.get("below_sma200", 0.05)) * (1 - _series_or_default(out, "ts_above_sma200"))
        + float(reduction_subscores.get("below_ema20", 0.10)) * (1 - _series_or_default(out, "ts_above_ema20"))
        + float(reduction_subscores.get("below_ema50", 0.10)) * (1 - _series_or_default(out, "ts_above_ema50"))
        + float(reduction_subscores.get("rsi", 0.10)) * _series_or_default(out, "ts_rsi_reduccion")
        + float(reduction_subscores.get("mom20", 0.15)) * (1 - _series_or_default(out, "ts_mom20"))
        + float(reduction_subscores.get("mom60", 0.15)) * (1 - _series_or_default(out, "ts_mom60"))
        + float(reduction_subscores.get("drawdown", 0.05)) * (1 - _series_or_default(out, "ts_drawdown"))
        + float(reduction_subscores.get("volatility", 0.05)) * (1 - _series_or_default(out, "ts_volatility"))
    ).clip(0, 1)
    out["score_refuerzo_v2"] = (blend_base * out["score_refuerzo"] + blend_tech * out["tech_refuerzo"]).clip(0, 1)
    out["score_reduccion_v2"] = (blend_base * out["score_reduccion"] + blend_tech * out["tech_reduccion"]).clip(0, 1)
    for subfamily, rules in asset_subfamily_adjustments.items():
        mask = out.get("asset_subfamily", pd.Series(index=out.index, dtype=object)).eq(subfamily)
        mixed_refuerzo_penalty = float((rules or {}).get("technical_mixed_refuerzo_penalty", 0.0))
        mixed_reduccion_boost = float((rules or {}).get("technical_mixed_reduccion_boost", 0.0))
        mixed_high_gain_refuerzo_penalty = float((rules or {}).get("technical_mixed_high_gain_refuerzo_penalty", 0.0))
        mixed_high_gain_reduccion_boost = float((rules or {}).get("technical_mixed_high_gain_reduccion_boost", 0.0))
        mixed_gain_threshold_pct = float((rules or {}).get("technical_mixed_gain_threshold_pct", 80.0))
        mixed_trends = set((rules or {}).get("technical_mixed_trends", ["Mixta"]))
        if (
            not mixed_refuerzo_penalty
            and not mixed_reduccion_boost
            and not mixed_high_gain_refuerzo_penalty
            and not mixed_high_gain_reduccion_boost
        ):
            continue
        trend_mask = (
            mask
            & out.get("Tech_Trend", pd.Series(index=out.index, dtype=object)).isin(mixed_trends)
        )
        high_gain_mixed_mask = trend_mask & (
            pd.to_numeric(out.get("Ganancia_%_Cap"), errors="coerce").fillna(-1e9) >= mixed_gain_threshold_pct
        )
        if mixed_refuerzo_penalty:
            out["score_refuerzo_v2"] -= np.where(trend_mask, mixed_refuerzo_penalty, 0.0)
        if mixed_reduccion_boost:
            out["score_reduccion_v2"] += np.where(trend_mask, mixed_reduccion_boost, 0.0)
        if mixed_high_gain_refuerzo_penalty:
            out["score_refuerzo_v2"] -= np.where(high_gain_mixed_mask, mixed_high_gain_refuerzo_penalty, 0.0)
        if mixed_high_gain_reduccion_boost:
            out["score_reduccion_v2"] += np.where(high_gain_mixed_mask, mixed_high_gain_reduccion_boost, 0.0)

    refuerzo_gate = absolute_rules.get("refuerzo_gate", {}) or {}
    if bool(refuerzo_gate.get("enabled", False)):
        negative_mom20_max = float(refuerzo_gate.get("momentum_20d_max", 0.0))
        max_refuerzo_score = float(refuerzo_gate.get("max_score", 0.58))
        allowed_trends = set(refuerzo_gate.get("allowed_trends", ["Alcista", "Alcista fuerte"]))
        excluded_families = set(refuerzo_gate.get("excluded_families", ["bond", "liquidity"]))
        asset_family = out.get("asset_family", pd.Series(index=out.index, dtype=object))
        tech_trend = out.get("Tech_Trend", pd.Series(index=out.index, dtype=object))
        mom20 = pd.to_numeric(out.get("Momentum_20d_%"), errors="coerce")
        gate_mask = (
            ~asset_family.isin(excluded_families)
            & mom20.notna()
            & (mom20 < negative_mom20_max)
            & ~tech_trend.isin(allowed_trends)
        )
        out["score_refuerzo_v2"] = np.where(
            gate_mask,
            np.minimum(out["score_refuerzo_v2"], max_refuerzo_score),
            out["score_refuerzo_v2"],
        )
    out["score_refuerzo_v2"] = out["score_refuerzo_v2"].clip(0, 1)
    out["score_reduccion_v2"] = out["score_reduccion_v2"].clip(0, 1)
    out["score_unificado_v2"] = (out["score_refuerzo_v2"] - out["score_reduccion_v2"]).round(3)
    return out


def finalize_unified_score(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "score_unificado_v2" in out.columns:
        out["score_unificado"] = (out["score_refuerzo_v2"] - out["score_reduccion_v2"]).round(3)
    else:
        out["score_unificado"] = (out["score_refuerzo"] - out["score_reduccion"]).round(3)
    return out
