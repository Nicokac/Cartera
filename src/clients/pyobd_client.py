from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd


DEFAULT_LOOKBACK_DAYS = 60


def _get_pyobd_client() -> Any:
    try:
        from PyOBD import openBYMAdata
        return openBYMAdata()
    except ImportError:
        try:
            from pyobd import BymaData
        except ImportError as exc:
            raise RuntimeError("PyOBD no esta instalado.") from exc
        return BymaData()


def _coerce_history_frame(payload: object) -> pd.DataFrame:
    if isinstance(payload, pd.DataFrame):
        return payload.copy()
    if isinstance(payload, list):
        return pd.DataFrame(payload)
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            return pd.DataFrame(payload["data"])
        return pd.DataFrame([payload])
    return pd.DataFrame()


def _find_volume_column(df: pd.DataFrame) -> str | None:
    normalized = {str(col).strip().lower(): col for col in df.columns}
    for candidate in ("volume", "volumen", "vol"):
        if candidate in normalized:
            return normalized[candidate]
    return None


def _liquidity_bucket(avg_volume_20d: float | None) -> str | None:
    if avg_volume_20d is None or pd.isna(avg_volume_20d):
        return None
    if avg_volume_20d >= 1_000_000:
        return "alta"
    if avg_volume_20d >= 100_000:
        return "media"
    return "baja"


def get_bond_volume_context(
    tickers: list[str],
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    today: date | None = None,
) -> pd.DataFrame:
    clean_tickers = sorted({str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()})
    if not clean_tickers:
        return pd.DataFrame()

    client = _get_pyobd_client()
    end_date = today or date.today()
    start_date = end_date - timedelta(days=lookback_days)
    rows: list[dict[str, object]] = []

    for ticker in clean_tickers:
        try:
            history_raw = client.get_daily_history(
                ticker,
                start_date.isoformat(),
                end_date.isoformat(),
            )
        except Exception:
            continue

        history = _coerce_history_frame(history_raw)
        if history.empty:
            continue

        volume_col = _find_volume_column(history)
        if not volume_col:
            continue

        volume_series = pd.to_numeric(history[volume_col], errors="coerce").dropna()
        if volume_series.empty:
            continue

        latest_volume = float(volume_series.iloc[-1])
        avg_volume_20d = float(volume_series.tail(20).mean())
        volume_ratio = latest_volume / avg_volume_20d if avg_volume_20d > 0 else None
        rows.append(
            {
                "Ticker_IOL": ticker,
                "bonistas_volume_last": latest_volume,
                "bonistas_volume_avg_20d": avg_volume_20d,
                "bonistas_volume_ratio": float(volume_ratio) if volume_ratio is not None else None,
                "bonistas_liquidity_bucket": _liquidity_bucket(avg_volume_20d),
            }
        )

    return pd.DataFrame(rows)
