from __future__ import annotations

import pandas as pd


def build_fundamentals_table(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    cols = [c for c in columns if c in df.columns]
    if not cols:
        return pd.DataFrame()
    return df[cols].copy().sort_values("Valor_USD", ascending=False) if "Valor_USD" in cols else df[cols].copy()


def build_pe_table(df: pd.DataFrame) -> pd.DataFrame:
    if "P/E" not in df.columns:
        return pd.DataFrame()
    out = df[["Ticker_IOL", "Bloque", "Valor_USD", "P/E"]].dropna(subset=["P/E"]).copy()
    if out.empty:
        return out
    promedio_pe = out["P/E"].mean()
    out["vs_promedio"] = (out["P/E"] - promedio_pe).round(2)
    out["Señal"] = out["P/E"].apply(lambda x: "P/E alto" if x > 40 else ("P/E bajo" if x < 15 else "P/E medio"))
    return out.sort_values("P/E")


def build_beta_table(df: pd.DataFrame) -> pd.DataFrame:
    if "Beta" not in df.columns:
        return pd.DataFrame()
    out = df[["Ticker_IOL", "Bloque", "Valor_USD", "Peso_%", "Beta"]].dropna(subset=["Beta"]).copy()
    if out.empty:
        return out
    out["Señal"] = out["Beta"].apply(
        lambda x: "Volátil" if x > 1.5 else ("Mercado" if x > 1 else "Defensivo")
    )
    return out.sort_values("Beta")
