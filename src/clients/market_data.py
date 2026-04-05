from __future__ import annotations

import pandas as pd


def _normalize_history_frame(data: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if not isinstance(data, pd.DataFrame) or data.empty:
        return pd.DataFrame()

    out = data.copy()
    if isinstance(out.columns, pd.MultiIndex):
        if ticker in out.columns.get_level_values(-1):
            out = out.xs(ticker, axis=1, level=-1)
        elif ticker in out.columns.get_level_values(0):
            out = out.xs(ticker, axis=1, level=0)

    rename_map = {}
    for col in out.columns:
        text = str(col).strip()
        lower = text.lower()
        if lower == "close":
            rename_map[col] = "Close"
        elif lower == "open":
            rename_map[col] = "Open"
        elif lower == "high":
            rename_map[col] = "High"
        elif lower == "low":
            rename_map[col] = "Low"
        elif lower == "volume":
            rename_map[col] = "Volume"
    if rename_map:
        out = out.rename(columns=rename_map)

    return out if "Close" in out.columns else pd.DataFrame()


def fetch_price_history(
    ticker: str,
    *,
    period: str = "6mo",
    interval: str = "1d",
    auto_adjust: bool = True,
) -> pd.DataFrame:
    import yfinance as yf

    attempts = [
        lambda: yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=auto_adjust,
            progress=False,
            threads=False,
            group_by="column",
        ),
        lambda: yf.Ticker(ticker).history(
            period=period,
            interval=interval,
            auto_adjust=auto_adjust,
        ),
    ]

    for fetch in attempts:
        try:
            data = fetch()
        except Exception:
            continue
        normalized = _normalize_history_frame(data, ticker)
        if not normalized.empty:
            return normalized

    return pd.DataFrame()
