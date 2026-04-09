from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

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


def _empty_history_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=HISTORY_COLUMNS)


def _normalize_run_date(run_date: object) -> str:
    return pd.Timestamp(run_date).strftime("%Y-%m-%d")


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
    observation["run_date"] = _normalize_run_date(run_date)
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


def _build_temporal_row(
    row: pd.Series,
    *,
    ticker_history: pd.DataFrame,
) -> dict[str, Any]:
    current_action = row.get("accion_sugerida_v2")
    current_bucket = _normalize_action_bucket(current_action)
    previous = ticker_history.iloc[-1] if not ticker_history.empty else None

    score_delta = np.nan
    previous_action = None
    if previous is not None:
        previous_action = previous.get("accion_sugerida_v2")
        prev_score = previous.get("score_unificado")
        current_score = row.get("score_unificado")
        if pd.notna(prev_score) and pd.notna(current_score):
            score_delta = float(current_score) - float(prev_score)

    streak = 1 if current_bucket in {"refuerzo", "reduccion", "mantener"} else 0
    if streak:
        for _, hist_row in ticker_history.sort_values("run_date", ascending=False).iterrows():
            if _normalize_action_bucket(hist_row.get("accion_sugerida_v2")) != current_bucket:
                break
            streak += 1

    return {
        "accion_previa": previous_action,
        "score_delta_vs_dia_anterior": score_delta,
        "dias_consecutivos_refuerzo": streak if current_bucket == "refuerzo" else 0,
        "dias_consecutivos_reduccion": streak if current_bucket == "reduccion" else 0,
        "dias_consecutivos_mantener": streak if current_bucket == "mantener" else 0,
        "sin_historial_temporal": previous is None,
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

    run_date_norm = _normalize_run_date(run_date)
    prior_history = history.copy()
    if not prior_history.empty:
        prior_history["run_date"] = prior_history["run_date"].map(_normalize_run_date)
        prior_history = prior_history.loc[prior_history["run_date"] < run_date_norm].copy()

    temporal_rows: list[dict[str, Any]] = []
    for _, row in out.iterrows():
        ticker = row.get("Ticker_IOL")
        ticker_history = (
            prior_history.loc[prior_history["Ticker_IOL"] == ticker].copy()
            if not prior_history.empty
            else _empty_history_frame()
        )
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
