from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT / "data" / "runtime"
PREDICTION_HISTORY_PATH = RUNTIME_DIR / "prediction_history.csv"

PREDICTION_HISTORY_COLUMNS = [
    "run_date",
    "ticker",
    "asset_family",
    "asset_subfamily",
    "direction",
    "confidence",
    "conviction_label",
    "consensus_raw",
    "score_unificado",
    "signal_votes",
    "horizon_days",
    "outcome_date",
    "outcome",
    "correct",
]
DEFAULT_PREDICTION_HISTORY_RETENTION_DAYS = 90


def _empty_prediction_history() -> pd.DataFrame:
    return pd.DataFrame(columns=PREDICTION_HISTORY_COLUMNS)


def _normalize_date(value: object) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _normalize_signal_votes(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "{}"
    if isinstance(value, str):
        text = value.strip()
        return text or "{}"
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=True, sort_keys=True)
    return json.dumps(dict(value), ensure_ascii=True, sort_keys=True)


def resolve_prediction_run_date(run_date: object) -> str:
    return _normalize_date(run_date)


def resolve_prediction_outcome_date(run_date: object, *, horizon_days: int) -> str:
    if int(horizon_days) < 0:
        raise ValueError("horizon_days no puede ser negativo")
    base = pd.Timestamp(run_date).normalize()
    outcome_ts = base + BDay(int(horizon_days))
    return outcome_ts.strftime("%Y-%m-%d")


def load_prediction_history(path: Path | None = None) -> pd.DataFrame:
    path = path or PREDICTION_HISTORY_PATH
    if not path.exists():
        return _empty_prediction_history()

    history = pd.read_csv(path)
    for column in PREDICTION_HISTORY_COLUMNS:
        if column not in history.columns:
            history[column] = np.nan
    return history[PREDICTION_HISTORY_COLUMNS].copy()


def build_prediction_observation(
    predictions: pd.DataFrame,
    *,
    run_date: object,
    horizon_days: int,
) -> pd.DataFrame:
    if predictions.empty:
        return _empty_prediction_history()

    if int(horizon_days) < 0:
        raise ValueError("horizon_days no puede ser negativo")

    observation = predictions.copy()
    for column in PREDICTION_HISTORY_COLUMNS:
        if column not in observation.columns:
            observation[column] = np.nan

    observation["run_date"] = resolve_prediction_run_date(run_date)
    observation["horizon_days"] = int(horizon_days)
    observation["outcome_date"] = resolve_prediction_outcome_date(run_date, horizon_days=int(horizon_days))
    observation["signal_votes"] = observation["signal_votes"].map(_normalize_signal_votes)
    if "asset_family" in observation.columns:
        observation["asset_family"] = observation["asset_family"].fillna("").astype(str).str.strip().str.lower()
    if "asset_subfamily" in observation.columns:
        observation["asset_subfamily"] = observation["asset_subfamily"].fillna("").astype(str).str.strip().str.lower()
    observation["direction"] = observation["direction"].fillna("neutral").astype(str).str.strip().replace("", "neutral")
    observation["outcome"] = observation["outcome"].fillna("").astype(str).str.strip()
    observation["ticker"] = observation["ticker"].astype(str).str.strip().str.upper()
    observation["correct"] = observation["correct"].where(observation["correct"].notna(), np.nan)

    observation = observation[PREDICTION_HISTORY_COLUMNS].copy()
    observation = observation.loc[observation["ticker"] != ""].copy()
    observation = observation.drop_duplicates(subset=["run_date", "ticker", "horizon_days"], keep="last")
    observation = observation.sort_values(["ticker", "run_date", "horizon_days"]).reset_index(drop=True)
    return observation


def upsert_prediction_history(
    history: pd.DataFrame,
    observation: pd.DataFrame,
) -> pd.DataFrame:
    if history.empty and observation.empty:
        return _empty_prediction_history()
    if history.empty:
        merged = observation.copy()
    elif observation.empty:
        merged = history.copy()
    else:
        merged = pd.concat([history.copy(), observation.copy()], ignore_index=True)

    for column in PREDICTION_HISTORY_COLUMNS:
        if column not in merged.columns:
            merged[column] = np.nan

    merged["run_date"] = merged["run_date"].map(_normalize_date)
    merged["outcome_date"] = merged["outcome_date"].where(merged["outcome_date"].isna(), merged["outcome_date"].map(_normalize_date))
    merged["signal_votes"] = merged["signal_votes"].map(_normalize_signal_votes)
    if "asset_family" in merged.columns:
        merged["asset_family"] = merged["asset_family"].fillna("").astype(str).str.strip().str.lower()
    if "asset_subfamily" in merged.columns:
        merged["asset_subfamily"] = merged["asset_subfamily"].fillna("").astype(str).str.strip().str.lower()
    merged["ticker"] = merged["ticker"].astype(str).str.strip().str.upper()
    merged["direction"] = merged["direction"].fillna("neutral").astype(str).str.strip().replace("", "neutral")
    merged["outcome"] = merged["outcome"].fillna("").astype(str).str.strip()
    merged["horizon_days"] = pd.to_numeric(merged["horizon_days"], errors="coerce").fillna(0).astype(int)
    merged = merged.loc[merged["ticker"] != ""].copy()
    merged = merged.drop_duplicates(subset=["run_date", "ticker", "horizon_days"], keep="last")
    merged = merged.sort_values(["ticker", "run_date", "horizon_days"]).reset_index(drop=True)
    return merged[PREDICTION_HISTORY_COLUMNS].copy()


def save_prediction_history(history: pd.DataFrame, path: Path | None = None) -> Path:
    path = path or PREDICTION_HISTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(path, index=False, encoding="utf-8")
    return path


def apply_prediction_history_retention(
    history: pd.DataFrame,
    *,
    retention_days: int = DEFAULT_PREDICTION_HISTORY_RETENTION_DAYS,
    today: object | None = None,
) -> pd.DataFrame:
    days = int(retention_days)
    if days < 1:
        raise ValueError("retention_days debe ser >= 1")
    if history.empty:
        return _empty_prediction_history()

    retained = history.copy()
    for column in PREDICTION_HISTORY_COLUMNS:
        if column not in retained.columns:
            retained[column] = np.nan
    retained = retained[PREDICTION_HISTORY_COLUMNS].copy()

    retained["run_date"] = pd.to_datetime(retained["run_date"], errors="coerce")
    base_today = pd.Timestamp(today).normalize() if today is not None else pd.Timestamp.now().normalize()
    min_date = base_today - pd.Timedelta(days=days)
    retained = retained.loc[retained["run_date"].notna() & (retained["run_date"] >= min_date)].copy()
    retained["run_date"] = retained["run_date"].dt.strftime("%Y-%m-%d")
    retained = retained.reset_index(drop=True)
    return retained[PREDICTION_HISTORY_COLUMNS].copy()
