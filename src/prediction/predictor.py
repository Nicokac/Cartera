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
}


def _as_float(value: object) -> float | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    return float(numeric)


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


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


def _vote_trend(value: object, rules: dict[str, Any]) -> int:
    trend = _normalize_text(value)
    bullish_values = {str(item).strip() for item in rules.get("bullish_values", [])}
    bearish_values = {str(item).strip() for item in rules.get("bearish_values", [])}
    if trend in bullish_values:
        return 1
    if trend in bearish_values:
        return -1
    return 0


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


def _vote_market_regime(row: dict[str, Any], rules: dict[str, Any]) -> int:
    active_flags = _extract_flags(row)
    bearish_flags = {str(item).strip() for item in rules.get("bearish_flags", [])}
    if active_flags & bearish_flags:
        return -1
    bullish_when_no_flags = bool(rules.get("bullish_when_no_flags", False))
    any_active = bool(row.get("market_regime_any_active", False))
    if bullish_when_no_flags and not any_active and not active_flags:
        return 1
    return 0


def vote_signal(signal_name: str, row: dict[str, Any], signal_config: dict[str, Any]) -> int:
    rules = signal_config.get("vote_rules", {}) or {}
    source_column = SIGNAL_COLUMN_MAP.get(signal_name, signal_name)

    if signal_name == "rsi":
        return _vote_rsi(row.get(source_column), rules)
    if signal_name == "momentum_20d":
        return _vote_threshold(row.get(source_column), rules, positive_key="positive_threshold", negative_key="negative_threshold")
    if signal_name == "momentum_60d":
        return _vote_threshold(row.get(source_column), rules, positive_key="positive_threshold", negative_key="negative_threshold")
    if signal_name == "sma_trend":
        return _vote_trend(row.get(source_column), rules)
    if signal_name == "score_unificado":
        return _vote_score(row.get(source_column), rules)
    if signal_name == "market_regime":
        return _vote_market_regime(row, rules)
    return 0


def predict(row: dict[str, Any], weights: dict[str, Any]) -> dict[str, Any]:
    signals = weights.get("signals", {}) or {}
    direction_threshold = float(weights.get("direction_threshold", 0.15))

    weighted_sum = 0.0
    total_weight = 0.0
    votes: dict[str, int] = {}

    for signal_name, signal_config in signals.items():
        weight = float(signal_config.get("weight", 0.0) or 0.0)
        if weight <= 0:
            continue
        vote = int(vote_signal(signal_name, row, signal_config))
        votes[signal_name] = vote
        weighted_sum += weight * vote
        total_weight += weight

    consensus_raw = 0.0 if total_weight <= 0 else weighted_sum / total_weight
    confidence = abs(consensus_raw)

    if consensus_raw > direction_threshold:
        direction = "up"
    elif consensus_raw < (-1 * direction_threshold):
        direction = "down"
    else:
        direction = "neutral"

    return {
        "direction": direction,
        "confidence": round(confidence, 6),
        "consensus_raw": round(consensus_raw, 6),
        "votes": votes,
    }
