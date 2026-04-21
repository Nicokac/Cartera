from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from ..config import MAPPINGS_DIR
except ImportError:
    from config import MAPPINGS_DIR


OUTCOME_TO_NUMERIC = {
    "down": -1.0,
    "neutral": 0.0,
    "up": 1.0,
}

PREDICTION_WEIGHTS_PATH = MAPPINGS_DIR / "prediction_weights.json"


def outcome_to_numeric(value: object) -> float | None:
    normalized = str(value or "").strip().lower()
    if normalized not in OUTCOME_TO_NUMERIC:
        return None
    return OUTCOME_TO_NUMERIC[normalized]


def extract_signal_vote_frame(history: pd.DataFrame) -> pd.DataFrame:
    if history is None or history.empty:
        return pd.DataFrame(columns=["ticker", "outcome"])

    rows: list[dict[str, Any]] = []
    for row in history.to_dict(orient="records"):
        outcome_numeric = outcome_to_numeric(row.get("outcome"))
        if outcome_numeric is None:
            continue

        raw_votes = row.get("signal_votes")
        if raw_votes is None or (isinstance(raw_votes, float) and pd.isna(raw_votes)):
            votes: dict[str, Any] = {}
        elif isinstance(raw_votes, str):
            text = raw_votes.strip()
            votes = json.loads(text) if text else {}
        elif isinstance(raw_votes, dict):
            votes = raw_votes
        else:
            votes = dict(raw_votes)

        parsed_votes = {}
        for key, value in votes.items():
            numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            if pd.notna(numeric):
                parsed_votes[str(key)] = float(numeric)

        rows.append(
            {
                "ticker": str(row.get("ticker") or "").strip().upper(),
                "run_date": str(row.get("run_date") or "").strip(),
                "outcome": str(row.get("outcome") or "").strip().lower(),
                "outcome_numeric": float(outcome_numeric),
                "signal_votes": parsed_votes,
            }
        )

    return pd.DataFrame(rows)


def compute_signal_ic(vote_frame: pd.DataFrame, signal_name: str) -> dict[str, Any]:
    if vote_frame is None or vote_frame.empty:
        return {"signal": signal_name, "samples": 0, "ic": None}

    rows: list[dict[str, float]] = []
    for row in vote_frame.to_dict(orient="records"):
        votes = row.get("signal_votes", {}) or {}
        if signal_name not in votes:
            continue
        rows.append(
            {
                "vote": float(votes[signal_name]),
                "outcome_numeric": float(row["outcome_numeric"]),
            }
        )

    if not rows:
        return {"signal": signal_name, "samples": 0, "ic": None}

    df = pd.DataFrame(rows)
    if df["vote"].nunique(dropna=True) <= 1 or df["outcome_numeric"].nunique(dropna=True) <= 1:
        return {"signal": signal_name, "samples": int(len(df)), "ic": 0.0}

    ic = df["vote"].corr(df["outcome_numeric"])
    if pd.isna(ic):
        ic = 0.0
    return {"signal": signal_name, "samples": int(len(df)), "ic": float(ic)}


def calibrate_prediction_weights(
    history: pd.DataFrame,
    weights: dict[str, Any],
) -> tuple[dict[str, Any], pd.DataFrame]:
    updated = copy.deepcopy(weights)
    calibration_cfg = updated.get("calibration", {}) or {}
    min_samples = int(calibration_cfg.get("min_samples", 30))
    min_weight = float(calibration_cfg.get("min_weight", 0.1))
    max_weight = float(calibration_cfg.get("max_weight", 1.0))

    lookback_samples = int(calibration_cfg.get("lookback_samples", 0) or 0)
    min_recent_samples = int(calibration_cfg.get("min_recent_samples", min_samples) or min_samples)

    vote_frame = extract_signal_vote_frame(history)
    if lookback_samples > 0 and not vote_frame.empty:
        sorted_frame = vote_frame.sort_values("run_date", ascending=False)
        recent_frame = sorted_frame.head(lookback_samples)
        effective_frame = recent_frame if len(recent_frame) >= min_recent_samples else vote_frame
    else:
        effective_frame = vote_frame

    summaries: list[dict[str, Any]] = []

    for signal_name, signal_cfg in (updated.get("signals", {}) or {}).items():
        previous_weight = float(signal_cfg.get("weight", 0.0) or 0.0)
        stats = compute_signal_ic(effective_frame, signal_name)
        samples = int(stats["samples"])
        ic = stats["ic"]

        if samples < min_samples or ic is None:
            new_weight = previous_weight
            status = "insufficient_samples"
        else:
            if float(ic) <= 0:
                new_weight = 0.0
            else:
                bounded_ic = max(min_weight, float(ic))
                new_weight = max(min_weight, min(max_weight, bounded_ic))
            status = "recalibrated"

        signal_cfg["weight"] = round(float(new_weight), 6)
        summaries.append(
            {
                "signal": signal_name,
                "samples": samples,
                "ic": None if ic is None else round(float(ic), 6),
                "previous_weight": previous_weight,
                "new_weight": float(signal_cfg["weight"]),
                "status": status,
            }
        )

    summary_df = pd.DataFrame(summaries).sort_values("signal").reset_index(drop=True)
    return updated, summary_df


def save_prediction_weights(weights: dict[str, Any], path: Path | None = None) -> Path:
    path = path or PREDICTION_WEIGHTS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(weights, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
