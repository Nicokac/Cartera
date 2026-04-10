from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd


FINVIZ_MAX_ATTEMPTS = 3
FINVIZ_BACKOFF_SECONDS = 0.25
logger = logging.getLogger(__name__)


def _call_with_retry(fetcher: callable) -> Any:
    last_exc: Exception | None = None
    for attempt in range(1, FINVIZ_MAX_ATTEMPTS + 1):
        try:
            return fetcher()
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Finviz call failed on attempt %s/%s: %s",
                attempt,
                FINVIZ_MAX_ATTEMPTS,
                exc,
            )
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
    except Exception as exc:
        logger.warning("Finviz fundamentals unavailable for %s: %s", ticker, exc)
        bundle["fundamentals"] = {}

    try:
        bundle["ratings"] = _call_with_retry(stock.ticker_outer_ratings)
    except Exception as exc:
        logger.warning("Finviz ratings unavailable for %s: %s", ticker, exc)
        bundle["ratings"] = pd.DataFrame()

    try:
        bundle["news"] = _call_with_retry(stock.ticker_news)
    except Exception as exc:
        logger.warning("Finviz news unavailable for %s: %s", ticker, exc)
        bundle["news"] = pd.DataFrame()

    try:
        bundle["insiders"] = _call_with_retry(stock.ticker_inside_trader)
    except Exception as exc:
        logger.warning("Finviz insiders unavailable for %s: %s", ticker, exc)
        bundle["insiders"] = pd.DataFrame()

    return bundle
