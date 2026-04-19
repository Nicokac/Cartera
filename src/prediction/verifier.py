from __future__ import annotations

import logging
from typing import Any, Callable

import pandas as pd

try:
    from ..clients.market_data import fetch_price_history
    from ..config import PREDICTION_WEIGHTS
except ImportError:
    from clients.market_data import fetch_price_history
    from config import PREDICTION_WEIGHTS


logger = logging.getLogger(__name__)


def classify_outcome(return_pct: float, *, neutral_return_band: float) -> str:
    if abs(float(return_pct)) < float(neutral_return_band):
        return "neutral"
    if float(return_pct) > 0:
        return "up"
    return "down"


def build_verification_period(
    run_date: object,
    outcome_date: object,
    *,
    buffer_days: int = 10,
) -> str:
    start = pd.Timestamp(run_date).normalize()
    end = pd.Timestamp(outcome_date).normalize()
    span_days = max(1, (end - start).days)
    total_days = max(30, span_days + int(buffer_days))
    return f"{total_days}d"


def resolve_close_on_or_after(history: pd.DataFrame, target_date: object) -> float | None:
    if not isinstance(history, pd.DataFrame) or history.empty or "Close" not in history.columns:
        return None

    index = pd.to_datetime(history.index, errors="coerce")
    valid = history.copy()
    valid.index = index
    valid = valid.loc[valid.index.notna()].sort_index()
    if valid.empty:
        return None

    target_ts = pd.Timestamp(target_date).normalize()
    matched = valid.loc[valid.index.normalize() >= target_ts]
    if matched.empty:
        return None

    close = pd.to_numeric(matched.iloc[0].get("Close"), errors="coerce")
    if pd.isna(close):
        return None
    return float(close)


def verify_prediction_history(
    history: pd.DataFrame,
    *,
    today: object | None = None,
    neutral_return_band: float | None = None,
    price_fetcher: Callable[..., pd.DataFrame] | None = None,
) -> pd.DataFrame:
    if history is None or history.empty:
        return pd.DataFrame(columns=getattr(history, "columns", []))

    out = history.copy()
    if "outcome" not in out.columns:
        out["outcome"] = ""
    if "correct" not in out.columns:
        out["correct"] = pd.NA

    out["outcome"] = out["outcome"].fillna("").astype(str).str.strip()
    out["ticker"] = out["ticker"].astype(str).str.strip().str.upper()
    out["run_date"] = pd.to_datetime(out["run_date"], errors="coerce")
    out["outcome_date"] = pd.to_datetime(out["outcome_date"], errors="coerce")

    today_ts = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    neutral_band = float(
        neutral_return_band
        if neutral_return_band is not None
        else (PREDICTION_WEIGHTS.get("neutral_return_band", 0.01))
    )
    price_fetcher = price_fetcher or fetch_price_history

    pending_mask = (
        out["outcome"].eq("")
        & out["outcome_date"].notna()
        & (out["outcome_date"].dt.normalize() <= today_ts)
        & out["run_date"].notna()
    )
    pending = out.loc[pending_mask].copy()
    if pending.empty:
        return out

    logger.info("Prediction verifier started: pending=%s today=%s", len(pending), today_ts.strftime("%Y-%m-%d"))

    for ticker, ticker_rows in pending.groupby("ticker", sort=False):
        min_run_date = ticker_rows["run_date"].min()
        max_outcome_date = ticker_rows["outcome_date"].max()
        period = build_verification_period(min_run_date, max_outcome_date)
        history_frame = price_fetcher(ticker, period=period, interval="1d", auto_adjust=True)

        if history_frame is None or history_frame.empty:
            logger.warning("Prediction verifier skipped %s: no price history", ticker)
            continue

        for idx, row in ticker_rows.iterrows():
            price_run = resolve_close_on_or_after(history_frame, row["run_date"])
            price_outcome = resolve_close_on_or_after(history_frame, row["outcome_date"])
            if price_run is None or price_outcome is None or price_run == 0:
                logger.warning(
                    "Prediction verifier left pending %s: price_run=%s price_outcome=%s",
                    ticker,
                    price_run,
                    price_outcome,
                )
                continue

            return_pct = (float(price_outcome) / float(price_run)) - 1
            outcome = classify_outcome(return_pct, neutral_return_band=neutral_band)
            predicted_direction = str(row.get("direction") or "").strip().lower()
            out.at[idx, "outcome"] = outcome
            out.at[idx, "correct"] = bool(predicted_direction == outcome)

    logger.info(
        "Prediction verifier completed: verified=%s remaining_pending=%s",
        int(out["outcome"].ne("").sum()),
        int(out["outcome"].eq("").sum()),
    )
    out["run_date"] = out["run_date"].dt.strftime("%Y-%m-%d")
    out["outcome_date"] = out["outcome_date"].dt.strftime("%Y-%m-%d")
    return out
