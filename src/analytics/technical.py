from __future__ import annotations

import pandas as pd


def normalize_technical_overlay(df_tech: pd.DataFrame) -> pd.DataFrame:
    if df_tech is None:
        return pd.DataFrame()
    return df_tech.copy()
