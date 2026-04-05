from __future__ import annotations

from datetime import datetime

import pandas as pd


def _parse_date_ddmmyyyy(value: object) -> pd.Timestamp:
    text = str(value or "").strip()
    if not text:
        return pd.NaT
    return pd.to_datetime(text, dayfirst=True, errors="coerce")


def _duration_bucket(value: object) -> str | None:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return None
    if number < 1:
        return "corta"
    if number < 3:
        return "media"
    return "larga"


def enrich_bond_analytics(
    df_bonds: pd.DataFrame,
    df_bonistas: pd.DataFrame | None = None,
    *,
    reference_date: str | None = None,
    macro_variables: dict[str, object] | None = None,
) -> pd.DataFrame:
    work = df_bonds.copy()
    if work.empty:
        return work

    if df_bonistas is not None and not df_bonistas.empty:
        bonistas = df_bonistas.copy()
        if "bonistas_ticker" in bonistas.columns and "Ticker_IOL" not in bonistas.columns:
            bonistas = bonistas.rename(columns={"bonistas_ticker": "Ticker_IOL"})
        work = work.merge(bonistas, on="Ticker_IOL", how="left")

    ref_ts = pd.Timestamp(reference_date) if reference_date else pd.Timestamp(datetime.now().date())
    work["bonistas_fecha_vencimiento_dt"] = work.get(
        "bonistas_fecha_vencimiento",
        pd.Series(index=work.index, dtype=object),
    ).apply(_parse_date_ddmmyyyy)
    work["bonistas_fecha_emision_dt"] = work.get(
        "bonistas_fecha_emision",
        pd.Series(index=work.index, dtype=object),
    ).apply(_parse_date_ddmmyyyy)
    work["bonistas_days_to_maturity"] = (work["bonistas_fecha_vencimiento_dt"] - ref_ts).dt.days
    work["bonistas_duration_bucket"] = work.get(
        "bonistas_md",
        pd.Series(index=work.index, dtype=float),
    ).apply(_duration_bucket)
    work["bonistas_tir_vs_avg_365d_pct"] = (
        pd.to_numeric(work.get("bonistas_tir_pct"), errors="coerce")
        - pd.to_numeric(work.get("bonistas_tir_avg_365d_pct"), errors="coerce")
    )
    work["bonistas_parity_gap_pct"] = pd.to_numeric(work.get("bonistas_paridad_pct"), errors="coerce") - 100.0

    macro_variables = macro_variables or {}
    cer_value = pd.to_numeric(pd.Series([macro_variables.get("cer_diario")]), errors="coerce").iloc[0]
    if pd.notna(cer_value):
        work["bonistas_cer_reference"] = cer_value
    tamar_value = pd.to_numeric(pd.Series([macro_variables.get("tamar")]), errors="coerce").iloc[0]
    if pd.notna(tamar_value):
        work["bonistas_tamar_reference"] = tamar_value
    badlar_value = pd.to_numeric(pd.Series([macro_variables.get("badlar")]), errors="coerce").iloc[0]
    if pd.notna(badlar_value):
        work["bonistas_badlar_reference"] = badlar_value

    return work


def build_bond_monitor_table(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "Ticker_IOL",
        "Tipo",
        "Bloque",
        "asset_subfamily",
        "Peso_%",
        "bonistas_tir_pct",
        "bonistas_paridad_pct",
        "bonistas_md",
        "bonistas_duration_bucket",
        "bonistas_days_to_maturity",
        "bonistas_tir_vs_avg_365d_pct",
        "bonistas_parity_gap_pct",
        "bonistas_put_flag",
    ]
    available = [col for col in columns if col in df.columns]
    if not available:
        return pd.DataFrame()
    out = df[available].copy()
    sort_col = "Peso_%" if "Peso_%" in out.columns else available[0]
    return out.sort_values(sort_col, ascending=False).reset_index(drop=True)


def build_bond_subfamily_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "asset_subfamily" not in df.columns:
        return pd.DataFrame()

    metrics: dict[str, tuple[str, str]] = {
        "Instrumentos": ("Ticker_IOL", "count"),
    }
    if "bonistas_tir_pct" in df.columns:
        metrics["TIR_Promedio"] = ("bonistas_tir_pct", "mean")
    if "bonistas_paridad_pct" in df.columns:
        metrics["Paridad_Promedio"] = ("bonistas_paridad_pct", "mean")
    if "bonistas_md" in df.columns:
        metrics["MD_Promedio"] = ("bonistas_md", "mean")
    if "bonistas_days_to_maturity" in df.columns:
        metrics["Dias_al_Vto_Promedio"] = ("bonistas_days_to_maturity", "mean")

    summary = df.groupby("asset_subfamily", dropna=False).agg(**metrics).reset_index()
    numeric_cols = [col for col in summary.columns if col not in {"asset_subfamily", "Instrumentos"}]
    for col in numeric_cols:
        summary[col] = pd.to_numeric(summary[col], errors="coerce").round(2)
    return summary.sort_values("Instrumentos", ascending=False).reset_index(drop=True)
