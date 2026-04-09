from __future__ import annotations

import pandas as pd


def to_float_or_none(value: object) -> float | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return None
    return float(numeric)


def positive_float_or_none(value: object) -> float | None:
    numeric = to_float_or_none(value)
    if numeric is None or numeric <= 0:
        return None
    return numeric
