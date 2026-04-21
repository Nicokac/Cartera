from __future__ import annotations

from typing import Any

import pandas as pd


SIGNAL_COLUMN_MAP = {
    "rsi": "RSI_14",
    "momentum_20d": "Momentum_20d_%",
    "momentum_60d": "Momentum_60d_%",
    "sma_trend": "Tech_Trend",
    "score_unificado": "score_unificado",
    "market_regime": "market_regime_any_active",
    "adx": "ADX_14",
    "relative_volume": "Relative_Volume",
}


def _as_float(value: object) -> float | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    return float(numeric)


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


def _normalize_key(value: object) -> str:
    return _normalize_text(value).lower()


def _extract_flags(row: dict[str, Any]) -> set[str]:
    raw = row.get("market_regime_active_flags")
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return set()
    if isinstance(raw, (list, tuple, set)):
        return {str(item).strip() for item in raw if str(item).strip()}
    text = str(raw).strip()
    if not text:
        return set()
    return {part.strip() for part in text.split(",") if part.strip()}


def _resolve_regime_target_keys(row: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    asset_subfamily = _normalize_key(row.get("asset_subfamily"))
    asset_family = _normalize_key(row.get("asset_family"))
    if asset_subfamily:
        keys.append(asset_subfamily)
    if asset_family and asset_family not in keys:
        keys.append(asset_family)
    keys.append("default")
    return keys


def _clip_vote(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def _coerce_vote(value: object) -> int:
    try:
        numeric = int(value)
    except Exception:
        return 0
    if numeric > 0:
        return 1
    if numeric < 0:
        return -1
    return 0


def _vote_rsi(value: object, rules: dict[str, Any]) -> int:
    rsi = _as_float(value)
    if rsi is None:
        return 0
    oversold = float(rules.get("oversold_threshold", 35))
    overbought = float(rules.get("overbought_threshold", 65))
    if rsi <= oversold:
        return 1
    if rsi >= overbought:
        return -1
    return 0


def _vote_rsi_continuous(value: object, rules: dict[str, Any]) -> float:
    rsi = _as_float(value)
    if rsi is None:
        return 0.0
    center = float(rules.get("center", 50.0))
    lower_bound = float(rules.get("lower_bound", 0.0))
    upper_bound = float(rules.get("upper_bound", 100.0))

    if rsi <= center:
        denom = max(1e-9, center - lower_bound)
        return round(_clip_vote((center - rsi) / denom), 6)

    denom = max(1e-9, upper_bound - center)
    return round(_clip_vote(-1.0 * ((rsi - center) / denom)), 6)


def _vote_threshold(value: object, rules: dict[str, Any], *, positive_key: str, negative_key: str) -> int:
    metric = _as_float(value)
    if metric is None:
        return 0
    positive_threshold = float(rules.get(positive_key, 0))
    negative_threshold = float(rules.get(negative_key, 0))
    if metric >= positive_threshold:
        return 1
    if metric <= negative_threshold:
        return -1
    return 0


def _vote_threshold_continuous(
    value: object,
    rules: dict[str, Any],
    *,
    positive_key: str,
    negative_key: str,
) -> float:
    metric = _as_float(value)
    if metric is None:
        return 0.0

    positive_threshold = float(rules.get(positive_key, 0.0))
    negative_threshold = float(rules.get(negative_key, 0.0))
    positive_saturation = float(rules.get("positive_saturation", positive_threshold * 3 if positive_threshold > 0 else 1.0))
    negative_saturation = float(rules.get("negative_saturation", abs(negative_threshold) * 3 if negative_threshold < 0 else 1.0))

    if metric >= positive_threshold:
        denom = max(1e-9, positive_saturation - positive_threshold)
        return round(_clip_vote((metric - positive_threshold) / denom), 6)
    if metric <= negative_threshold:
        denom = max(1e-9, negative_saturation - abs(negative_threshold))
        return round(_clip_vote(-1.0 * ((abs(metric) - abs(negative_threshold)) / denom)), 6)
    return 0.0


def _vote_trend(value: object, rules: dict[str, Any]) -> int:
    trend = _normalize_text(value)
    bullish_values = {str(item).strip() for item in rules.get("bullish_values", [])}
    bearish_values = {str(item).strip() for item in rules.get("bearish_values", [])}
    if trend in bullish_values:
        return 1
    if trend in bearish_values:
        return -1
    return 0


def _vote_trend_continuous(value: object, rules: dict[str, Any]) -> float:
    trend = _normalize_text(value)
    graduated = rules.get("graduated_votes", {}) or {}
    if trend in graduated:
        return _clip_vote(float(graduated[trend]))
    return 0.0


def _vote_score(value: object, rules: dict[str, Any]) -> int:
    score = _as_float(value)
    if score is None:
        return 0
    high_threshold = float(rules.get("high_threshold", 0.65))
    low_threshold = float(rules.get("low_threshold", 0.35))
    if score >= high_threshold:
        return 1
    if score <= low_threshold:
        return -1
    return 0


def _vote_score_continuous(value: object, rules: dict[str, Any]) -> float:
    score = _as_float(value)
    if score is None:
        return 0.0
    return _vote_threshold_continuous(
        score,
        rules,
        positive_key="high_threshold",
        negative_key="low_threshold",
    )


def _vote_adx(row: dict[str, Any], rules: dict[str, Any]) -> int:
    adx = _as_float(row.get("ADX_14"))
    di_plus = _as_float(row.get("DI_plus_14"))
    di_minus = _as_float(row.get("DI_minus_14"))
    if adx is None or di_plus is None or di_minus is None:
        return 0
    threshold = float(rules.get("adx_threshold", 20.0))
    if adx < threshold:
        return 0
    if di_plus > di_minus:
        return 1
    if di_minus > di_plus:
        return -1
    return 0


def _vote_adx_continuous(row: dict[str, Any], rules: dict[str, Any]) -> float:
    adx = _as_float(row.get("ADX_14"))
    di_plus = _as_float(row.get("DI_plus_14"))
    di_minus = _as_float(row.get("DI_minus_14"))
    if adx is None or di_plus is None or di_minus is None:
        return 0.0
    threshold = float(rules.get("adx_threshold", 20.0))
    saturation = float(rules.get("adx_saturation", 45.0))
    if adx < threshold:
        return 0.0
    strength = _clip_vote((adx - threshold) / max(1e-9, saturation - threshold))
    if di_plus > di_minus:
        return round(strength, 6)
    if di_minus > di_plus:
        return round(-strength, 6)
    return 0.0


def _vote_relative_volume(row: dict[str, Any], rules: dict[str, Any]) -> int:
    rel_vol = _as_float(row.get("Relative_Volume"))
    return_intraday = _as_float(row.get("Return_intraday_%"))
    if rel_vol is None or return_intraday is None:
        return 0
    high_threshold = float(rules.get("high_threshold", 1.5))
    if rel_vol < high_threshold:
        return 0
    if return_intraday > 0:
        return 1
    if return_intraday < 0:
        return -1
    return 0


def _vote_relative_volume_continuous(row: dict[str, Any], rules: dict[str, Any]) -> float:
    rel_vol = _as_float(row.get("Relative_Volume"))
    return_intraday = _as_float(row.get("Return_intraday_%"))
    if rel_vol is None or return_intraday is None:
        return 0.0
    high_threshold = float(rules.get("high_threshold", 1.5))
    high_saturation = float(rules.get("high_saturation", 3.0))
    if rel_vol < high_threshold:
        return 0.0
    strength = _clip_vote((rel_vol - high_threshold) / max(1e-9, high_saturation - high_threshold))
    if return_intraday > 0:
        return round(strength, 6)
    if return_intraday < 0:
        return round(-strength, 6)
    return 0.0


def _vote_market_regime(row: dict[str, Any], rules: dict[str, Any]) -> int:
    active_flags = _extract_flags(row)
    bearish_flags = {str(item).strip() for item in rules.get("bearish_flags", [])}
    if active_flags & bearish_flags:
        return -1

    flag_effects = rules.get("flag_effects", {}) or {}
    regime_target_keys = _resolve_regime_target_keys(row)
    contextual_votes: list[int] = []
    for flag in active_flags:
        effect_map = flag_effects.get(flag, {}) or {}
        for target_key in regime_target_keys:
            if target_key in effect_map:
                contextual_votes.append(_coerce_vote(effect_map.get(target_key)))
                break

    if any(vote < 0 for vote in contextual_votes):
        return -1
    if any(vote > 0 for vote in contextual_votes):
        return 1

    bullish_when_no_flags = bool(rules.get("bullish_when_no_flags", False))
    any_active = bool(row.get("market_regime_any_active", False))
    if bullish_when_no_flags and not any_active and not active_flags:
        return 1
    return 0


def vote_signal(signal_name: str, row: dict[str, Any], signal_config: dict[str, Any]) -> float:
    rules = signal_config.get("vote_rules", {}) or {}
    vote_mode = str(signal_config.get("vote_mode") or "discrete").strip().lower()
    source_column = SIGNAL_COLUMN_MAP.get(signal_name, signal_name)

    if signal_name == "rsi":
        if vote_mode == "continuous":
            return _vote_rsi_continuous(row.get(source_column), rules)
        return _vote_rsi(row.get(source_column), rules)
    if signal_name == "momentum_20d":
        if vote_mode == "continuous":
            return _vote_threshold_continuous(
                row.get(source_column),
                rules,
                positive_key="positive_threshold",
                negative_key="negative_threshold",
            )
        return _vote_threshold(row.get(source_column), rules, positive_key="positive_threshold", negative_key="negative_threshold")
    if signal_name == "momentum_60d":
        if vote_mode == "continuous":
            return _vote_threshold_continuous(
                row.get(source_column),
                rules,
                positive_key="positive_threshold",
                negative_key="negative_threshold",
            )
        return _vote_threshold(row.get(source_column), rules, positive_key="positive_threshold", negative_key="negative_threshold")
    if signal_name == "sma_trend":
        if vote_mode == "continuous":
            return _vote_trend_continuous(row.get(source_column), rules)
        return _vote_trend(row.get(source_column), rules)
    if signal_name == "score_unificado":
        if vote_mode == "continuous":
            return _vote_score_continuous(row.get(source_column), rules)
        return _vote_score(row.get(source_column), rules)
    if signal_name == "market_regime":
        return float(_vote_market_regime(row, rules))
    if signal_name == "adx":
        if vote_mode == "continuous":
            return _vote_adx_continuous(row, rules)
        return float(_vote_adx(row, rules))
    if signal_name == "relative_volume":
        if vote_mode == "continuous":
            return _vote_relative_volume_continuous(row, rules)
        return float(_vote_relative_volume(row, rules))
    return 0


def predict(row: dict[str, Any], weights: dict[str, Any]) -> dict[str, Any]:
    signals = weights.get("signals", {}) or {}
    direction_threshold = float(weights.get("direction_threshold", 0.15))
    active_vote_threshold = float(weights.get("active_vote_threshold", 0.0) or 0.0)

    weighted_sum = 0.0
    total_weight = 0.0
    active_weight = 0.0
    votes: dict[str, float] = {}

    for signal_name, signal_config in signals.items():
        weight = float(signal_config.get("weight", 0.0) or 0.0)
        if weight <= 0:
            continue
        vote = float(vote_signal(signal_name, row, signal_config))
        if active_vote_threshold > 0.0 and abs(vote) < active_vote_threshold:
            vote = 0.0
        votes[signal_name] = vote
        weighted_sum += weight * vote
        total_weight += weight
        if abs(vote) > 0:
            active_weight += weight

    consensus_raw = 0.0 if total_weight <= 0 else weighted_sum / total_weight
    net_strength = abs(consensus_raw)
    agreement_ratio = 0.0 if active_weight <= 0 else abs(weighted_sum) / active_weight
    confidence = net_strength * agreement_ratio

    conviction_cfg = weights.get("conviction_thresholds", {}) or {}
    high_threshold = float(conviction_cfg.get("high", 0.35))
    medium_threshold = float(conviction_cfg.get("medium", 0.20))
    if confidence >= high_threshold:
        conviction_label = "alta"
    elif confidence >= medium_threshold:
        conviction_label = "media"
    else:
        conviction_label = "baja"

    if consensus_raw > direction_threshold:
        direction = "up"
    elif consensus_raw < (-1 * direction_threshold):
        direction = "down"
    else:
        direction = "neutral"

    return {
        "direction": direction,
        "confidence": round(confidence, 6),
        "conviction_label": conviction_label,
        "consensus_raw": round(consensus_raw, 6),
        "agreement_ratio": round(agreement_ratio, 6),
        "net_strength": round(net_strength, 6),
        "votes": votes,
    }
