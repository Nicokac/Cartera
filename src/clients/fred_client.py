from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_FRED_SERIES = {
    "ust_5y_pct": "DGS5",
    "ust_10y_pct": "DGS10",
}
DEFAULT_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def _load_local_env(path: Path = DEFAULT_ENV_PATH) -> dict[str, str]:
    if not path.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if not key:
            continue
        loaded[key] = value
        os.environ.setdefault(key, value)
    return loaded


def _get_fred_client(api_key: str | None = None) -> Any:
    try:
        from fredapi import Fred
    except ImportError as exc:
        raise RuntimeError(
            "fredapi no esta instalado. Instala la libreria o usa la API HTTP de FRED."
        ) from exc

    resolved_key = (api_key or os.environ.get("FRED_API_KEY") or "").strip()
    if not resolved_key:
        _load_local_env()
        resolved_key = (api_key or os.environ.get("FRED_API_KEY") or "").strip()
    if not resolved_key:
        raise ValueError("FRED_API_KEY es obligatorio para usar fredapi.")

    return Fred(api_key=resolved_key)


def get_ust_series(
    *,
    api_key: str | None = None,
    series_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    fred = _get_fred_client(api_key=api_key)
    series_map = series_map or dict(DEFAULT_FRED_SERIES)

    data: dict[str, pd.Series] = {}
    for label, series_id in series_map.items():
        series = fred.get_series(series_id)
        if not isinstance(series, pd.Series):
            series = pd.Series(series)
        series = pd.to_numeric(series, errors="coerce").dropna()
        series.index = pd.to_datetime(series.index, errors="coerce")
        data[label] = series

    if not data:
        return pd.DataFrame(columns=["date"])

    df = pd.concat(data, axis=1).reset_index().rename(columns={"index": "date"})
    if "ust_5y_pct" in df.columns and "ust_10y_pct" in df.columns:
        df["ust_spread_10y_5y_pct"] = df["ust_10y_pct"] - df["ust_5y_pct"]
    return df.sort_values("date").reset_index(drop=True)


def get_ust_latest(
    *,
    api_key: str | None = None,
    series_map: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    df = get_ust_series(api_key=api_key, series_map=series_map)
    if df.empty:
        return None

    latest = df.iloc[-1]
    payload = {
        "ust_date": latest["date"].date().isoformat() if pd.notna(latest["date"]) else None,
        "ust_5y_pct": float(latest["ust_5y_pct"]) if pd.notna(latest.get("ust_5y_pct")) else None,
        "ust_10y_pct": float(latest["ust_10y_pct"]) if pd.notna(latest.get("ust_10y_pct")) else None,
        "ust_spread_10y_5y_pct": float(latest["ust_spread_10y_5y_pct"])
        if pd.notna(latest.get("ust_spread_10y_5y_pct"))
        else None,
    }
    return payload
