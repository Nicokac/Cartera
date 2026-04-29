from __future__ import annotations

import pandas as pd
import re


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


def safe_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"-", "N/A", "nan"}:
        return None
    text = text.replace("%", "").replace("$", "")
    if "." in text and "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None
