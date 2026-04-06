from __future__ import annotations

from datetime import datetime

import pandas as pd


def _infer_bond_subfamily_from_block(value: object) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text == "soberano ar":
        return "bond_sov_ar"
    if text == "cer":
        return "bond_cer"
    if text == "bopreal":
        return "bond_bopreal"
    return "bond_other"


def _infer_bonistas_local_subfamily(row: pd.Series) -> str | None:
    explicit = str(row.get("bonistas_subfamily") or "").strip()
    if explicit:
        return explicit

    ticker = str(row.get("Ticker_IOL") or "").strip().upper()
    block = str(row.get("Bloque") or "").strip().lower()

    if ticker.startswith(("GD", "AL", "AE", "AO", "AN")):
        return "bond_hard_dollar"
    if ticker.startswith("BPO") or "bopreal" in block:
        return "bond_bopreal"
    if ticker.startswith(("TZX", "TX", "TC", "CUAP", "DICP", "DIP0", "PARP", "PAP0", "X")) or block == "cer":
        return "bond_cer"
    if ticker.startswith("TT"):
        return "bond_dual"
    if ticker.startswith(("TV", "D30", "TZV")):
        return "bond_dollar_linked"
    if ticker.startswith("TMF"):
        return "bond_tamar"
    if ticker.startswith(("M", "TM")):
        return "bond_tamar"
    if ticker.startswith(("S", "T")):
        return "bond_fixed_rate"
    return None


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
    mep_real: float | None = None,
) -> pd.DataFrame:
    work = df_bonds.copy()
    if work.empty:
        return work

    if df_bonistas is not None and not df_bonistas.empty:
        bonistas = df_bonistas.copy()
        if "bonistas_ticker" in bonistas.columns and "Ticker_IOL" not in bonistas.columns:
            bonistas = bonistas.rename(columns={"bonistas_ticker": "Ticker_IOL"})
        work = work.merge(bonistas, on="Ticker_IOL", how="left")

    if "asset_subfamily" not in work.columns:
        work["asset_subfamily"] = None
    work["asset_subfamily"] = work["asset_subfamily"].astype("object")
    work["asset_subfamily"] = work["asset_subfamily"].where(work["asset_subfamily"].notna(), None)

    if "Bloque" in work.columns:
        inferred_from_block = work["Bloque"].map(_infer_bond_subfamily_from_block)
        work["asset_subfamily"] = work["asset_subfamily"].where(work["asset_subfamily"].notna(), inferred_from_block)

    if "bonistas_subfamily" in work.columns:
        work["asset_subfamily"] = work["asset_subfamily"].where(work["asset_subfamily"].notna(), work["bonistas_subfamily"])

    work["bonistas_local_subfamily"] = work.apply(_infer_bonistas_local_subfamily, axis=1)

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
    raw_parity = pd.to_numeric(work.get("bonistas_paridad_pct"), errors="coerce")
    work["bonistas_paridad_bruta_pct"] = raw_parity

    if mep_real and mep_real > 0:
        precio = pd.to_numeric(work.get("bonistas_precio"), errors="coerce")
        valor_tecnico = pd.to_numeric(work.get("bonistas_valor_tecnico"), errors="coerce")
        hard_dollar_mask = work.get("asset_subfamily", pd.Series(index=work.index, dtype=object)).isin(
            {"bond_sov_ar", "bond_hard_dollar", "bond_bopreal"}
        )
        parity_operativa = ((precio / float(mep_real)) / valor_tecnico) * 100.0
        parity_operativa = parity_operativa.where(hard_dollar_mask & valor_tecnico.gt(0))
        if parity_operativa.notna().any():
            work["bonistas_paridad_pct"] = raw_parity.where(parity_operativa.isna(), parity_operativa)

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
    riesgo_pais_value = pd.to_numeric(pd.Series([macro_variables.get("riesgo_pais_bps")]), errors="coerce").iloc[0]
    if pd.notna(riesgo_pais_value):
        work["bonistas_riesgo_pais_bps"] = riesgo_pais_value
    rem_inflacion_value = pd.to_numeric(
        pd.Series([macro_variables.get("rem_inflacion_mensual_pct")]),
        errors="coerce",
    ).iloc[0]
    if pd.notna(rem_inflacion_value):
        work["bonistas_rem_inflacion_mensual_pct"] = rem_inflacion_value
    rem_inflacion_12m_value = pd.to_numeric(
        pd.Series([macro_variables.get("rem_inflacion_12m_pct")]),
        errors="coerce",
    ).iloc[0]
    if pd.notna(rem_inflacion_12m_value):
        work["bonistas_rem_inflacion_12m_pct"] = rem_inflacion_12m_value
    reservas_bcra_value = pd.to_numeric(pd.Series([macro_variables.get("reservas_bcra_musd")]), errors="coerce").iloc[0]
    if pd.notna(reservas_bcra_value):
        work["bonistas_reservas_bcra_musd"] = reservas_bcra_value
    a3500_value = pd.to_numeric(pd.Series([macro_variables.get("a3500_mayorista")]), errors="coerce").iloc[0]
    if pd.notna(a3500_value):
        work["bonistas_a3500_mayorista"] = a3500_value
    badlar_tea_value = pd.to_numeric(pd.Series([macro_variables.get("badlar_tea")]), errors="coerce").iloc[0]
    if pd.notna(badlar_tea_value):
        work["bonistas_badlar_tea_reference"] = badlar_tea_value
    tamar_tea_value = pd.to_numeric(pd.Series([macro_variables.get("tamar_tea")]), errors="coerce").iloc[0]
    if pd.notna(tamar_tea_value):
        work["bonistas_tamar_tea_reference"] = tamar_tea_value
    ust_5y_value = pd.to_numeric(pd.Series([macro_variables.get("ust_5y_pct")]), errors="coerce").iloc[0]
    if pd.notna(ust_5y_value):
        work["bonistas_ust_5y_pct"] = ust_5y_value
    ust_10y_value = pd.to_numeric(pd.Series([macro_variables.get("ust_10y_pct")]), errors="coerce").iloc[0]
    if pd.notna(ust_10y_value):
        work["bonistas_ust_10y_pct"] = ust_10y_value
    ust_curve_spread_value = pd.to_numeric(
        pd.Series([macro_variables.get("ust_spread_10y_5y_pct")]),
        errors="coerce",
    ).iloc[0]
    if pd.notna(ust_curve_spread_value):
        work["bonistas_ust_spread_10y_5y_pct"] = ust_curve_spread_value
    ust_date = macro_variables.get("ust_date")
    if ust_date:
        work["bonistas_ust_date"] = ust_date

    if pd.notna(ust_5y_value) or pd.notna(ust_10y_value):
        tir_value = pd.to_numeric(work.get("bonistas_tir_pct"), errors="coerce")
        md_value = pd.to_numeric(work.get("bonistas_md"), errors="coerce")
        local_subfamily = work.get("bonistas_local_subfamily", pd.Series(index=work.index, dtype=object))
        uses_ust_context = local_subfamily.isin({"bond_hard_dollar", "bond_bopreal"})
        ust_reference = pd.Series(index=work.index, dtype=float)
        ust_reference.loc[uses_ust_context & md_value.ge(3)] = ust_10y_value
        ust_reference.loc[uses_ust_context & ~md_value.ge(3)] = ust_5y_value
        if pd.notna(ust_10y_value):
            ust_reference.loc[uses_ust_context & ust_reference.isna()] = ust_10y_value
        elif pd.notna(ust_5y_value):
            ust_reference.loc[uses_ust_context & ust_reference.isna()] = ust_5y_value
        work["bonistas_spread_vs_ust_pct"] = tir_value - ust_reference

    return work


def build_bond_monitor_table(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "Ticker_IOL",
        "Tipo",
        "Bloque",
        "asset_subfamily",
        "bonistas_local_subfamily",
        "Peso_%",
        "bonistas_tir_pct",
        "bonistas_paridad_pct",
        "bonistas_md",
        "bonistas_volume_last",
        "bonistas_volume_avg_20d",
        "bonistas_volume_ratio",
        "bonistas_liquidity_bucket",
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


def build_bond_local_subfamily_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "bonistas_local_subfamily" not in df.columns:
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

    summary = (
        df.dropna(subset=["bonistas_local_subfamily"])
        .groupby("bonistas_local_subfamily", dropna=False)
        .agg(**metrics)
        .reset_index()
    )
    numeric_cols = [col for col in summary.columns if col not in {"bonistas_local_subfamily", "Instrumentos"}]
    for col in numeric_cols:
        summary[col] = pd.to_numeric(summary[col], errors="coerce").round(2)
    return summary.sort_values("Instrumentos", ascending=False).reset_index(drop=True)
