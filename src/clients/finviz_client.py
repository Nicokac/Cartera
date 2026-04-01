from __future__ import annotations

from typing import Any

import pandas as pd


def fetch_finviz_bundle(ticker: str) -> dict[str, Any]:
    from finvizfinance.quote import finvizfinance

    stock = finvizfinance(ticker)

    bundle: dict[str, Any] = {
        "ticker": ticker,
        "stock": stock,
        "fundamentals": {},
        "ratings": pd.DataFrame(),
        "news": pd.DataFrame(),
        "insiders": pd.DataFrame(),
    }

    try:
        bundle["fundamentals"] = stock.ticker_fundament()
    except Exception:
        bundle["fundamentals"] = {}

    try:
        bundle["ratings"] = stock.ticker_outer_ratings()
    except Exception:
        bundle["ratings"] = pd.DataFrame()

    try:
        bundle["news"] = stock.ticker_news()
    except Exception:
        bundle["news"] = pd.DataFrame()

    try:
        bundle["insiders"] = stock.ticker_inside_trader()
    except Exception:
        bundle["insiders"] = pd.DataFrame()

    return bundle
