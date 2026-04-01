from __future__ import annotations

import pandas as pd


def fetch_price_history(
    ticker: str,
    *,
    period: str = "6mo",
    interval: str = "1d",
    auto_adjust: bool = True,
) -> pd.DataFrame:
    import yfinance as yf

    data = yf.Ticker(ticker).history(
        period=period,
        interval=interval,
        auto_adjust=auto_adjust,
    )
    if isinstance(data, pd.DataFrame):
        return data
    return pd.DataFrame()
