from __future__ import annotations

import time
from typing import Any

import pandas as pd


FINVIZ_MAX_ATTEMPTS = 3
FINVIZ_BACKOFF_SECONDS = 0.25


def _call_with_retry(fetcher: callable) -> Any:
    last_exc: Exception | None = None
    for attempt in range(1, FINVIZ_MAX_ATTEMPTS + 1):
        try:
            return fetcher()
        except Exception as exc:
            last_exc = exc
            if attempt >= FINVIZ_MAX_ATTEMPTS:
                break
            time.sleep(FINVIZ_BACKOFF_SECONDS * attempt)
    raise last_exc or RuntimeError("Finviz fetch failed")


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
        bundle["fundamentals"] = _call_with_retry(stock.ticker_fundament)
    except Exception:
        bundle["fundamentals"] = {}

    try:
        bundle["ratings"] = _call_with_retry(stock.ticker_outer_ratings)
    except Exception:
        bundle["ratings"] = pd.DataFrame()

    try:
        bundle["news"] = _call_with_retry(stock.ticker_news)
    except Exception:
        bundle["news"] = pd.DataFrame()

    try:
        bundle["insiders"] = _call_with_retry(stock.ticker_inside_trader)
    except Exception:
        bundle["insiders"] = pd.DataFrame()

    return bundle
