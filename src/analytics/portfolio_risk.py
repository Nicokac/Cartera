from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {"Ticker_IOL"}
OPTIONAL_NUMERIC_COLUMNS = ("Peso_%", "Valorizado_ARS", "Precio_ARS")
EXCLUDED_RISK_TICKERS = {"CAUCION", "CASH_USD"}
EXCLUDED_RISK_TYPES = {"FCI"}


def _load_snapshot_csv(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

    if df.empty or not REQUIRED_COLUMNS.issubset(df.columns):
        return pd.DataFrame()

    out = df.copy()
    out["Ticker_IOL"] = out["Ticker_IOL"].fillna("").astype(str).str.strip()
    out = out.loc[out["Ticker_IOL"] != ""].copy()
    if out.empty:
        return pd.DataFrame()

    for column in OPTIONAL_NUMERIC_COLUMNS:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    return out


def load_portfolio_snapshot_history(
    run_date: object,
    *,
    snapshots_dirs: list[Path] | None = None,
) -> pd.DataFrame:
    run_ts = pd.to_datetime(run_date, errors="coerce")
    if pd.isna(run_ts):
        return pd.DataFrame()
    run_ts = run_ts.normalize()

    paths: list[tuple[pd.Timestamp, Path]] = []
    seen: set[Path] = set()
    for base_dir in snapshots_dirs or []:
        if not isinstance(base_dir, Path) or not base_dir.exists():
            continue
        for path in sorted(base_dir.glob("*_real_portfolio_master.csv")):
            if path in seen:
                continue
            seen.add(path)
            stamp = path.name.split("_real_portfolio_master.csv", 1)[0]
            snapshot_ts = pd.to_datetime(stamp, errors="coerce")
            if pd.isna(snapshot_ts):
                continue
            snapshot_ts = snapshot_ts.normalize()
            if snapshot_ts < run_ts:
                paths.append((snapshot_ts, path))

    if not paths:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    for snapshot_ts, path in sorted(paths, key=lambda item: item[0]):
        df = _load_snapshot_csv(path)
        if df.empty:
            continue
        df = df.copy()
        df["snapshot_date"] = snapshot_ts
        frames.append(df)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _series_metrics(values: pd.Series) -> dict[str, float | int]:
    clean = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    if clean.empty:
        return {
            "observaciones": 0,
            "retorno_acum_pct": np.nan,
            "volatilidad_diaria_pct": np.nan,
            "drawdown_max_pct": np.nan,
        }

    returns = clean.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    running_max = clean.cummax()
    drawdowns = clean / running_max - 1.0
    drawdown_max_pct = float(drawdowns.min() * 100.0) if not drawdowns.empty else 0.0
    retorno_acum_pct = float((clean.iloc[-1] / clean.iloc[0] - 1.0) * 100.0) if len(clean) >= 2 else 0.0
    volatilidad_diaria_pct = float(returns.std(ddof=0) * 100.0) if not returns.empty else 0.0
    return {
        "observaciones": int(len(clean)),
        "retorno_acum_pct": retorno_acum_pct,
        "volatilidad_diaria_pct": volatilidad_diaria_pct,
        "drawdown_max_pct": drawdown_max_pct,
    }


def _metrics_from_return_steps(returns_pct: pd.Series) -> dict[str, float | int]:
    clean = pd.to_numeric(returns_pct, errors="coerce").dropna().astype(float)
    if clean.empty:
        return {
            "observaciones": 0,
            "retorno_acum_pct": np.nan,
            "volatilidad_diaria_pct": np.nan,
            "drawdown_max_pct": np.nan,
        }

    levels = [100.0]
    for daily_ret_pct in clean.tolist():
        levels.append(levels[-1] * (1.0 + daily_ret_pct / 100.0))
    series = pd.Series(levels, dtype=float)
    metrics = _series_metrics(series)
    metrics["observaciones"] = int(len(clean))
    return metrics


def _history_quality_label(observaciones: int, total_snapshots: int) -> str:
    if total_snapshots <= 0 or observaciones <= 0:
        return "Sin historia"
    coverage = observaciones / total_snapshots
    if coverage >= 0.85:
        return "Robusta"
    if coverage >= 0.5:
        return "Parcial"
    return "Corta"


def _filter_risk_universe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    tickers = out["Ticker_IOL"].fillna("").astype(str).str.strip().str.upper()
    types = out["Tipo"].fillna("").astype(str).str.strip().str.upper() if "Tipo" in out.columns else pd.Series("", index=out.index)
    return out.loc[~tickers.isin(EXCLUDED_RISK_TICKERS) & ~types.isin(EXCLUDED_RISK_TYPES)].copy()


def _build_comparable_portfolio_timeseries(history_all: pd.DataFrame) -> pd.DataFrame:
    if history_all.empty or "snapshot_date" not in history_all.columns:
        return pd.DataFrame()

    work = history_all.copy()
    work["snapshot_date"] = pd.to_datetime(work["snapshot_date"], errors="coerce")
    work = work.dropna(subset=["snapshot_date"]).copy()
    if work.empty:
        return pd.DataFrame()

    work["Precio_ARS"] = pd.to_numeric(work.get("Precio_ARS"), errors="coerce")
    work["Valorizado_ARS"] = pd.to_numeric(work.get("Valorizado_ARS"), errors="coerce")
    work["metric_value"] = work["Precio_ARS"].where(work["Precio_ARS"].notna(), work["Valorizado_ARS"])

    totals = (
        work.groupby("snapshot_date", as_index=False)["Valorizado_ARS"]
        .sum(min_count=1)
        .rename(columns={"Valorizado_ARS": "total_ars"})
        .sort_values("snapshot_date")
        .reset_index(drop=True)
    )
    if totals.empty:
        return pd.DataFrame()

    dates = totals["snapshot_date"].tolist()
    rows: list[dict[str, object]] = [
        {
            "snapshot_date": dates[0],
            "total_ars": float(totals.loc[0, "total_ars"]),
            "comparable_index": 100.0,
            "daily_return_pct": np.nan,
            "overlap_prev_pct": np.nan,
            "coverage_prev_pct": np.nan,
            "coverage_curr_pct": np.nan,
            "stable_step": True,
        }
    ]

    index_level = 100.0
    for prev_date, curr_date in zip(dates, dates[1:]):
        prev_df = work.loc[work["snapshot_date"].eq(prev_date)].copy()
        curr_df = work.loc[work["snapshot_date"].eq(curr_date)].copy()
        merged = prev_df.merge(
            curr_df,
            on="Ticker_IOL",
            how="inner",
            suffixes=("_prev", "_curr"),
        )

        prev_total = float(prev_df["Valorizado_ARS"].sum(min_count=1) or 0.0)
        curr_total = float(curr_df["Valorizado_ARS"].sum(min_count=1) or 0.0)

        if merged.empty:
            rows.append(
                {
                    "snapshot_date": curr_date,
                    "total_ars": curr_total,
                    "comparable_index": np.nan,
                    "daily_return_pct": np.nan,
                    "overlap_prev_pct": 0.0,
                    "coverage_prev_pct": 0.0,
                    "coverage_curr_pct": 0.0,
                    "stable_step": False,
                }
            )
            continue

        merged["metric_value_prev"] = pd.to_numeric(merged["metric_value_prev"], errors="coerce")
        merged["metric_value_curr"] = pd.to_numeric(merged["metric_value_curr"], errors="coerce")
        merged["Valorizado_ARS_prev"] = pd.to_numeric(merged["Valorizado_ARS_prev"], errors="coerce")
        merged["Valorizado_ARS_curr"] = pd.to_numeric(merged["Valorizado_ARS_curr"], errors="coerce")
        merged = merged.loc[
            merged["metric_value_prev"].notna()
            & merged["metric_value_curr"].notna()
            & (merged["metric_value_prev"] != 0)
            & merged["Valorizado_ARS_prev"].notna()
            & merged["Valorizado_ARS_curr"].notna()
        ].copy()

        overlap_prev = float(merged["Valorizado_ARS_prev"].sum(min_count=1) or 0.0)
        overlap_curr = float(merged["Valorizado_ARS_curr"].sum(min_count=1) or 0.0)
        overlap_ratio = len(merged) / max(len(prev_df), 1)
        coverage_prev = overlap_prev / prev_total if prev_total > 0 else np.nan
        coverage_curr = overlap_curr / curr_total if curr_total > 0 else np.nan

        if merged.empty or overlap_prev <= 0:
            rows.append(
                {
                    "snapshot_date": curr_date,
                    "total_ars": curr_total,
                    "comparable_index": np.nan,
                    "daily_return_pct": np.nan,
                    "overlap_prev_pct": overlap_ratio * 100.0,
                    "coverage_prev_pct": coverage_prev * 100.0 if pd.notna(coverage_prev) else np.nan,
                    "coverage_curr_pct": coverage_curr * 100.0 if pd.notna(coverage_curr) else np.nan,
                    "stable_step": False,
                }
            )
            continue

        merged["weight_prev"] = merged["Valorizado_ARS_prev"] / overlap_prev
        merged["asset_return"] = merged["metric_value_curr"] / merged["metric_value_prev"] - 1.0
        portfolio_return = float((merged["weight_prev"] * merged["asset_return"]).sum())
        index_level = index_level * (1.0 + portfolio_return)

        stable_step = bool((coverage_prev >= 0.8 if pd.notna(coverage_prev) else False) and (coverage_curr >= 0.8 if pd.notna(coverage_curr) else False))
        rows.append(
            {
                "snapshot_date": curr_date,
                "total_ars": curr_total,
                "comparable_index": index_level,
                "daily_return_pct": portfolio_return * 100.0,
                "overlap_prev_pct": overlap_ratio * 100.0,
                "coverage_prev_pct": coverage_prev * 100.0 if pd.notna(coverage_prev) else np.nan,
                "coverage_curr_pct": coverage_curr * 100.0 if pd.notna(coverage_curr) else np.nan,
                "stable_step": stable_step,
            }
        )

    return pd.DataFrame(rows)


def build_portfolio_risk_bundle(
    current_portfolio: pd.DataFrame | None,
    *,
    run_date: object,
    snapshots_dirs: list[Path] | None = None,
    total_ars: float | None = None,
) -> dict[str, object]:
    current_df = current_portfolio.copy() if isinstance(current_portfolio, pd.DataFrame) else pd.DataFrame()
    if current_df.empty or "Ticker_IOL" not in current_df.columns:
        return {
            "portfolio_summary": {},
            "portfolio_timeseries": pd.DataFrame(),
            "position_risk": pd.DataFrame(),
        }

    history_df = load_portfolio_snapshot_history(run_date, snapshots_dirs=snapshots_dirs)
    run_ts = pd.to_datetime(run_date, errors="coerce")
    run_ts = run_ts.normalize() if pd.notna(run_ts) else pd.NaT

    current_view = current_df.copy()
    current_view["Ticker_IOL"] = current_view["Ticker_IOL"].fillna("").astype(str).str.strip()
    current_view = current_view.loc[current_view["Ticker_IOL"] != ""].copy()
    if current_view.empty:
        return {
            "portfolio_summary": {},
            "portfolio_timeseries": pd.DataFrame(),
            "position_risk": pd.DataFrame(),
        }
    current_view["snapshot_date"] = run_ts
    for column in OPTIONAL_NUMERIC_COLUMNS:
        if column in current_view.columns:
            current_view[column] = pd.to_numeric(current_view[column], errors="coerce")

    risk_current_view = _filter_risk_universe(current_view)
    if risk_current_view.empty:
        return {
            "portfolio_summary": {},
            "portfolio_timeseries": pd.DataFrame(),
            "position_risk": pd.DataFrame(),
        }

    risk_history_df = history_df.copy()
    if not risk_history_df.empty:
        risk_history_df["Ticker_IOL"] = risk_history_df["Ticker_IOL"].fillna("").astype(str).str.strip()
        risk_history_df = _filter_risk_universe(risk_history_df)

    history_all = (
        pd.concat([risk_history_df, risk_current_view], ignore_index=True, sort=False)
        if not risk_history_df.empty
        else risk_current_view
    )

    total_current = pd.to_numeric(pd.Series([total_ars]), errors="coerce").iloc[0]
    if pd.isna(total_current) or len(risk_current_view) != len(current_view):
        total_current = pd.to_numeric(risk_current_view.get("Valorizado_ARS"), errors="coerce").sum()

    portfolio_timeseries = _build_comparable_portfolio_timeseries(history_all)
    steps = portfolio_timeseries.iloc[1:].copy() if len(portfolio_timeseries) > 1 else pd.DataFrame()
    stable_returns = pd.to_numeric(
        steps.loc[steps["stable_step"].fillna(False), "daily_return_pct"] if not steps.empty else pd.Series(dtype=float),
        errors="coerce",
    )
    portfolio_summary = _metrics_from_return_steps(stable_returns)
    portfolio_summary["snapshots"] = int(len(portfolio_timeseries))
    if not portfolio_timeseries.empty:
        portfolio_summary["desde"] = portfolio_timeseries["snapshot_date"].min().strftime("%Y-%m-%d")
        portfolio_summary["hasta"] = portfolio_timeseries["snapshot_date"].max().strftime("%Y-%m-%d")
        portfolio_summary["total_actual_ars"] = float(portfolio_timeseries["total_ars"].iloc[-1])
    else:
        portfolio_summary["desde"] = None
        portfolio_summary["hasta"] = None
        portfolio_summary["total_actual_ars"] = float(total_current) if pd.notna(total_current) else np.nan

    coverage_prev_avg = float(pd.to_numeric(steps.get("coverage_prev_pct"), errors="coerce").dropna().mean()) if not steps.empty else 100.0
    coverage_curr_avg = float(pd.to_numeric(steps.get("coverage_curr_pct"), errors="coerce").dropna().mean()) if not steps.empty else 100.0
    stable_steps = int(pd.to_numeric(steps.get("stable_step"), errors="coerce").fillna(0).astype(int).sum()) if not steps.empty else 0
    total_steps = int(len(steps))
    estabilidad_pct = float(stable_steps / total_steps * 100.0) if total_steps > 0 else 100.0
    min_stable_steps = min(8, total_steps) if total_steps > 0 else 0
    serie_confiable = bool(
        total_steps == 0
        or (
            stable_steps >= min_stable_steps
            and estabilidad_pct >= 60.0
            and coverage_prev_avg >= 85.0
            and coverage_curr_avg >= 85.0
        )
    )
    portfolio_summary["metodologia"] = "serie_comparable"
    portfolio_summary["coverage_prev_promedio_pct"] = coverage_prev_avg
    portfolio_summary["coverage_curr_promedio_pct"] = coverage_curr_avg
    portfolio_summary["pasos_estables"] = stable_steps
    portfolio_summary["pasos_totales"] = total_steps
    portfolio_summary["min_pasos_estables_requeridos"] = min_stable_steps
    portfolio_summary["estabilidad_pct"] = estabilidad_pct
    portfolio_summary["observaciones_agregadas"] = int(portfolio_summary.get("observaciones", 0))
    portfolio_summary["serie_agregada_confiable"] = serie_confiable
    portfolio_summary["nota_estabilidad"] = None
    if not serie_confiable:
        portfolio_summary["retorno_acum_pct"] = np.nan
        portfolio_summary["volatilidad_diaria_pct"] = np.nan
        portfolio_summary["drawdown_max_pct"] = np.nan
        portfolio_summary["nota_estabilidad"] = (
            "Serie agregada basada en universo comparable. "
            "Las metricas de cartera se ocultan cuando la cobertura entre snapshots es insuficiente."
        )
    elif stable_steps < total_steps:
        portfolio_summary["nota_estabilidad"] = (
            "Metricas agregadas calculadas solo sobre pasos estables comparables."
        )

    current_symbols = risk_current_view["Ticker_IOL"].dropna().astype(str).tolist()
    total_snapshots = int(len(portfolio_timeseries))
    risk_rows: list[dict[str, object]] = []
    for symbol in current_symbols:
        ticker_history = history_all.loc[history_all["Ticker_IOL"].eq(symbol)].copy()
        if ticker_history.empty:
            continue
        ticker_history = ticker_history.sort_values("snapshot_date")
        price_series = pd.to_numeric(
            ticker_history["Precio_ARS"] if "Precio_ARS" in ticker_history.columns else pd.Series(index=ticker_history.index, dtype=float),
            errors="coerce",
        )
        value_series = pd.to_numeric(
            ticker_history["Valorizado_ARS"] if "Valorizado_ARS" in ticker_history.columns else pd.Series(index=ticker_history.index, dtype=float),
            errors="coerce",
        )
        use_price = int(price_series.notna().sum()) >= 2
        metric_series = price_series if use_price else value_series
        metrics = _series_metrics(metric_series)
        latest_row = ticker_history.iloc[-1]
        risk_rows.append(
            {
                "Ticker_IOL": symbol,
                "Tipo": latest_row.get("Tipo"),
                "Bloque": latest_row.get("Bloque"),
                "Peso_%": pd.to_numeric(pd.Series([latest_row.get("Peso_%")]), errors="coerce").iloc[0],
                "Base_Riesgo": "Precio_ARS" if use_price else "Valorizado_ARS",
                "Retorno_Acum_%": metrics["retorno_acum_pct"],
                "Volatilidad_Diaria_%": metrics["volatilidad_diaria_pct"],
                "Drawdown_Max_%": metrics["drawdown_max_pct"],
                "Observaciones": metrics["observaciones"],
                "Calidad_Historia": _history_quality_label(int(metrics["observaciones"]), total_snapshots),
            }
        )

    position_risk = pd.DataFrame(risk_rows)
    if not position_risk.empty and "Drawdown_Max_%" in position_risk.columns:
        position_risk = position_risk.sort_values(
            ["Drawdown_Max_%", "Volatilidad_Diaria_%"],
            ascending=[True, False],
            na_position="last",
        ).reset_index(drop=True)

    return {
        "portfolio_summary": portfolio_summary,
        "portfolio_timeseries": portfolio_timeseries,
        "position_risk": position_risk,
    }
