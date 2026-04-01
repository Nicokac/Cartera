from __future__ import annotations

import pandas as pd


def summarize_ratings(df_ratings: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df_ratings.empty:
        return pd.DataFrame(), pd.DataFrame()

    action_col = next((c for c in df_ratings.columns if c.lower() in ["action", "rating", "status"]), None)
    if action_col is None:
        return pd.DataFrame(), df_ratings.copy()

    base = df_ratings[df_ratings[action_col].notna()].copy()
    if base.empty:
        return pd.DataFrame(), base

    resumen = (
        base.groupby("Ticker")[action_col]
        .agg(total="count", consenso=lambda s: s.value_counts().index[0])
        .reset_index()
    )
    return resumen, base
