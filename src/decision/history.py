from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT / "data" / "runtime"
DECISION_HISTORY_PATH = RUNTIME_DIR / "decision_history.csv"

HISTORY_COLUMNS = [
    "run_date",
    "Ticker_IOL",
    "asset_subfamily",
    "score_unificado",
    "accion_sugerida_v2",
    "Peso_%",
    "Tech_Trend",
    "Momentum_20d_%",
    "Momentum_60d_%",
    "market_regime_any_active",
    "market_regime_active_flags",
]
DEFAULT_DECISION_HISTORY_RETENTION_DAYS = 365

TEMPORAL_COLUMNS = [
    "accion_previa",
    "score_delta_vs_dia_anterior",
    "dias_consecutivos_refuerzo",
    "dias_consecutivos_reduccion",
    "dias_consecutivos_mantener",
    "sin_historial_temporal",
    "es_nueva_senal",
    "senal_persistente_refuerzo",
    "senal_persistente_reduccion",
]

LIQUIDITY_TEMPORAL_GROUPS = {
    "operativa_ars": {"CASH_ARS", "CAUCION"},
}


def _empty_history_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=HISTORY_COLUMNS)


def _normalize_run_date(run_date: object) -> str:
    return pd.Timestamp(run_date).strftime("%Y-%m-%d")


def resolve_market_run_date(run_date: object, *, market_open_hour: int = 10) -> str:
    raw = run_date
    ts = pd.Timestamp(run_date)

    has_explicit_time = False
    if isinstance(raw, pd.Timestamp):
        has_explicit_time = raw.hour != 0 or raw.minute != 0 or raw.second != 0 or raw.microsecond != 0 or raw.nanosecond != 0
    elif isinstance(raw, str):
        has_explicit_time = ":" in raw or "T" in raw

    market_ts = ts
    if ts.dayofweek >= 5:
        market_ts = (ts.normalize() - BDay(1))
    elif has_explicit_time and ts.hour < int(market_open_hour):
        market_ts = (ts.normalize() - BDay(1))

    return market_ts.strftime("%Y-%m-%d")


def _normalize_action_bucket(action: object) -> str:
    text = str(action or "").strip().lower()
    if text == "refuerzo":
        return "refuerzo"
    if text == "reducir":
        return "reduccion"
    if text.startswith("mantener"):
        return "mantener"
    if text == "desplegar liquidez":
        return "despliegue"
    return "otro"


def _history_match_tickers(ticker: object) -> set[str]:
    normalized = str(ticker or "").strip().upper()
    if not normalized:
        return set()
    for members in LIQUIDITY_TEMPORAL_GROUPS.values():
        if normalized in members:
            return set(members)
    return {normalized}


def _prepare_history_lookup(prior_history: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if prior_history.empty:
        return {}
    sorted_history = prior_history.sort_values(["Ticker_IOL", "run_date"]).copy()
    return {str(ticker): frame.copy() for ticker, frame in sorted_history.groupby("Ticker_IOL", sort=False)}


def _merge_ticker_histories(
    history_lookup: dict[str, pd.DataFrame],
    tickers: set[str],
) -> pd.DataFrame:
    if not tickers:
        return _empty_history_frame()
    frames = [history_lookup[ticker] for ticker in sorted(tickers) if ticker in history_lookup]
    if not frames:
        return _empty_history_frame()
    return pd.concat(frames, ignore_index=True)


def load_decision_history(path: Path | None = None) -> pd.DataFrame:
    path = path or DECISION_HISTORY_PATH
    if not path.exists():
        return _empty_history_frame()

    history = pd.read_csv(path)
    for column in HISTORY_COLUMNS:
        if column not in history.columns:
            history[column] = np.nan
    return history[HISTORY_COLUMNS].copy()


def build_decision_history_observation(
    final_decision: pd.DataFrame,
    *,
    run_date: object,
    market_regime: dict[str, Any] | None = None,
) -> pd.DataFrame:
    if final_decision.empty:
        return _empty_history_frame()

    observation = final_decision.copy()
    for column in HISTORY_COLUMNS:
        if column not in observation.columns:
            observation[column] = np.nan

    regime = market_regime or {}
    active_flags = regime.get("active_flags", []) or []
    observation["run_date"] = resolve_market_run_date(run_date)
    observation["market_regime_any_active"] = bool(regime.get("any_active", False))
    observation["market_regime_active_flags"] = ",".join(str(flag) for flag in active_flags)

    observation = observation[HISTORY_COLUMNS].copy()
    observation = observation.drop_duplicates(subset=["Ticker_IOL"], keep="last")
    return observation.sort_values("Ticker_IOL").reset_index(drop=True)


def upsert_daily_decision_history(
    history: pd.DataFrame,
    observation: pd.DataFrame,
) -> pd.DataFrame:
    if history.empty and observation.empty:
        return _empty_history_frame()
    if history.empty:
        merged = observation.copy()
    elif observation.empty:
        merged = history.copy()
    else:
        observation_dates = {_normalize_run_date(value) for value in observation["run_date"].tolist()}
        history = history.copy()
        history["run_date"] = history["run_date"].map(_normalize_run_date)
        history = history.loc[~history["run_date"].isin(observation_dates)].copy()
        merged = pd.concat([history, observation], ignore_index=True)

    for column in HISTORY_COLUMNS:
        if column not in merged.columns:
            merged[column] = np.nan

    merged["run_date"] = merged["run_date"].map(_normalize_run_date)
    merged = merged.drop_duplicates(subset=["run_date", "Ticker_IOL"], keep="last")
    merged = merged.sort_values(["Ticker_IOL", "run_date"]).reset_index(drop=True)
    return merged[HISTORY_COLUMNS].copy()


def save_decision_history(history: pd.DataFrame, path: Path | None = None) -> Path:
    path = path or DECISION_HISTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(path, index=False, encoding="utf-8")
    return path


def apply_decision_history_retention(
    history: pd.DataFrame,
    *,
    retention_days: int = DEFAULT_DECISION_HISTORY_RETENTION_DAYS,
    today: object | None = None,
) -> pd.DataFrame:
    days = int(retention_days)
    if days < 1:
        raise ValueError("retention_days debe ser >= 1")
    if history.empty:
        return _empty_history_frame()

    retained = history.copy()
    for column in HISTORY_COLUMNS:
        if column not in retained.columns:
            retained[column] = np.nan
    retained = retained[HISTORY_COLUMNS].copy()

    retained["run_date"] = pd.to_datetime(retained["run_date"], errors="coerce")
    base_today = pd.Timestamp(today).normalize() if today is not None else pd.Timestamp.now().normalize()
    min_date = base_today - pd.Timedelta(days=days)
    retained = retained.loc[retained["run_date"].notna() & (retained["run_date"] >= min_date)].copy()
    retained["run_date"] = retained["run_date"].dt.strftime("%Y-%m-%d")
    retained = retained.sort_values(["Ticker_IOL", "run_date"]).reset_index(drop=True)
    return retained[HISTORY_COLUMNS].copy()


def _build_temporal_row(
    row: dict[str, Any],
    *,
    ticker_history: pd.DataFrame,
) -> dict[str, Any]:
    current_action = row.get("accion_sugerida_v2")
    current_bucket = _normalize_action_bucket(current_action)
    previous = ticker_history.iloc[-1] if not ticker_history.empty else None
    comparable_previous = previous

    current_subfamily = str(row.get("asset_subfamily") or "").strip().lower()
    if comparable_previous is not None:
        previous_subfamily = str(comparable_previous.get("asset_subfamily") or "").strip().lower()
        if current_subfamily and previous_subfamily and current_subfamily != previous_subfamily:
            comparable_previous = None

    score_delta = np.nan
    previous_action = None
    if comparable_previous is not None:
        previous_action = comparable_previous.get("accion_sugerida_v2")
        prev_score = comparable_previous.get("score_unificado")
        current_score = row.get("score_unificado")
        if pd.notna(prev_score) and pd.notna(current_score):
            score_delta = float(current_score) - float(prev_score)

    streak = 1 if current_bucket in {"refuerzo", "reduccion", "mantener"} else 0
    if streak:
        comparable_history = ticker_history
        if current_subfamily:
            comparable_history = comparable_history.loc[
                comparable_history["asset_subfamily"].fillna("").astype(str).str.strip().str.lower() == current_subfamily
            ].copy()
        history_buckets = comparable_history["accion_sugerida_v2"].map(_normalize_action_bucket).tolist()
        for bucket in reversed(history_buckets):
            if bucket != current_bucket:
                break
            streak += 1

    return {
        "accion_previa": previous_action,
        "score_delta_vs_dia_anterior": score_delta,
        "dias_consecutivos_refuerzo": streak if current_bucket == "refuerzo" else 0,
        "dias_consecutivos_reduccion": streak if current_bucket == "reduccion" else 0,
        "dias_consecutivos_mantener": streak if current_bucket == "mantener" else 0,
        "sin_historial_temporal": comparable_previous is None,
        "es_nueva_senal": previous_action is not None and str(previous_action) != str(current_action),
        "senal_persistente_refuerzo": current_bucket == "refuerzo" and streak >= 2,
        "senal_persistente_reduccion": current_bucket == "reduccion" and streak >= 2,
    }


def enrich_with_temporal_memory(
    final_decision: pd.DataFrame,
    history: pd.DataFrame,
    *,
    run_date: object,
) -> pd.DataFrame:
    out = final_decision.copy()
    if out.empty:
        for column in TEMPORAL_COLUMNS:
            out[column] = pd.Series(dtype="object")
        return out

    run_date_norm = resolve_market_run_date(run_date)
    prior_history = history.copy()
    if not prior_history.empty:
        prior_history["run_date"] = prior_history["run_date"].map(_normalize_run_date)
        prior_history = prior_history.loc[prior_history["run_date"] < run_date_norm].copy()
    history_lookup = _prepare_history_lookup(prior_history)

    temporal_rows: list[dict[str, Any]] = []
    for row in out.to_dict(orient="records"):
        ticker = row.get("Ticker_IOL")
        match_tickers = _history_match_tickers(ticker)
        ticker_history = _merge_ticker_histories(history_lookup, match_tickers)
        temporal_rows.append(_build_temporal_row(row, ticker_history=ticker_history))

    temporal_df = pd.DataFrame(temporal_rows, index=out.index)
    for column in TEMPORAL_COLUMNS:
        if column not in temporal_df.columns:
            temporal_df[column] = np.nan
    for column in TEMPORAL_COLUMNS:
        out[column] = temporal_df[column]
    return out


def build_temporal_memory_summary(final_decision: pd.DataFrame) -> dict[str, int]:
    if final_decision.empty:
        return {
            "senales_nuevas": 0,
            "persistentes_refuerzo": 0,
            "persistentes_reduccion": 0,
            "sin_historial": 0,
        }

    eligible = final_decision.copy()
    if "Tipo" in eligible.columns:
        eligible = eligible.loc[eligible["Tipo"].ne("Liquidez")].copy()

    return {
        "senales_nuevas": int(eligible.get("es_nueva_senal", pd.Series(dtype=bool)).fillna(False).sum()),
        "persistentes_refuerzo": int(
            eligible.get("senal_persistente_refuerzo", pd.Series(dtype=bool)).fillna(False).sum()
        ),
        "persistentes_reduccion": int(
            eligible.get("senal_persistente_reduccion", pd.Series(dtype=bool)).fillna(False).sum()
        ),
        "sin_historial": int(eligible.get("sin_historial_temporal", pd.Series(dtype=bool)).fillna(False).sum()),
    }
