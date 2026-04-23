from __future__ import annotations

import numpy as np
import pandas as pd

from common.numeric import to_float_or_none


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

    return {
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
