from __future__ import annotations

import pandas as pd


def summarize_insiders(df_insider: pd.DataFrame) -> pd.DataFrame:
    if df_insider.empty:
        return pd.DataFrame()
    trans_col = next((c for c in df_insider.columns if c.lower() in ["transaction", "type", "option type", "action"]), None)
    if trans_col is None:
        return pd.DataFrame()
    base = df_insider[df_insider[trans_col].notna()].copy()
    if base.empty:
        return pd.DataFrame()
    return base.groupby(["Ticker", trans_col]).size().unstack(fill_value=0)
