from __future__ import annotations

import pandas as pd


def latest_news_by_ticker(df_news: pd.DataFrame, *, top_n: int = 5) -> pd.DataFrame:
    if df_news.empty:
        return pd.DataFrame()
    base = df_news.copy()
    date_col = next((c for c in base.columns if "date" in c.lower() or "time" in c.lower()), None)
    if date_col:
        try:
            base[date_col] = pd.to_datetime(base[date_col], errors="coerce")
            base = base.sort_values(["Ticker", date_col], ascending=[True, False])
        except Exception:
            pass
    return base.groupby("Ticker").head(top_n).reset_index(drop=True)
