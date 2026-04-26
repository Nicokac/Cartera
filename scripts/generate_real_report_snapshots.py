from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd


def write_real_snapshots_impl(
    *,
    portfolio_bundle: dict[str, object],
    dashboard_bundle: dict[str, object],
    decision_bundle: dict[str, object],
    technical_overlay: pd.DataFrame | None,
    snapshots_dir: Path,
) -> list[Path]:
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    stamp = pd.Timestamp.now().strftime("%Y-%m-%d")

    df_total = portfolio_bundle["df_total"].copy()
    final_decision = decision_bundle["final_decision"].copy()
    liquidity_contract = dict(portfolio_bundle["liquidity_contract"])
    kpis = dict(dashboard_bundle["kpis"])

    paths = [
        snapshots_dir / f"{stamp}_real_portfolio_master.csv",
        snapshots_dir / f"{stamp}_real_decision_table.csv",
        snapshots_dir / f"{stamp}_real_liquidity_contract.json",
        snapshots_dir / f"{stamp}_real_kpis.json",
        snapshots_dir / f"{stamp}_real_technical_overlay.csv",
    ]

    df_total.sort_values("Valorizado_ARS", ascending=False).to_csv(paths[0], index=False, encoding="utf-8")
    final_decision.sort_values("score_unificado", ascending=False).to_csv(paths[1], index=False, encoding="utf-8")
    paths[2].write_text(json.dumps(liquidity_contract, ensure_ascii=False, indent=2), encoding="utf-8")
    paths[3].write_text(json.dumps(kpis, ensure_ascii=False, indent=2), encoding="utf-8")
    technical_df = technical_overlay.copy() if isinstance(technical_overlay, pd.DataFrame) else pd.DataFrame()
    technical_df.to_csv(paths[4], index=False, encoding="utf-8")
    return paths


def _load_snapshot_csv_impl(
    path: Path,
    *,
    required_snapshot_columns: set[str],
    optional_numeric_columns: tuple[str, ...],
    logger: logging.Logger,
) -> pd.DataFrame:
    try:
        previous_df = pd.read_csv(path)
    except Exception as exc:
        logger.warning("No se pudo leer snapshot previo %s: %s", path, exc)
        return pd.DataFrame()

    missing_columns = required_snapshot_columns - set(previous_df.columns)
    if missing_columns:
        logger.warning(
            "Snapshot previo invalido %s. Faltan columnas requeridas: %s",
            path,
            ", ".join(sorted(missing_columns)),
        )
        return pd.DataFrame()

    previous_df = previous_df.copy()
    previous_df["Ticker_IOL"] = previous_df["Ticker_IOL"].fillna("").astype(str).str.strip()
    previous_df = previous_df.loc[previous_df["Ticker_IOL"] != ""].copy()
    if previous_df.empty:
        logger.warning(
            "Snapshot previo invalido %s. No contiene filas utilizables con Ticker_IOL.",
            path,
        )
        return pd.DataFrame()

    for column in optional_numeric_columns:
        if column in previous_df.columns:
            previous_df[column] = pd.to_numeric(previous_df[column], errors="coerce")
    return previous_df


def load_previous_portfolio_snapshot_impl(
    run_date: object,
    *,
    snapshots_dir: Path | None,
    primary_snapshots_dir: Path,
    legacy_snapshots_dir: Path,
    use_legacy_snapshots: bool,
    required_snapshot_columns: set[str],
    optional_numeric_columns: tuple[str, ...],
    logger: logging.Logger,
) -> tuple[pd.DataFrame, str | None]:
    run_ts = pd.to_datetime(run_date, errors="coerce")
    if pd.isna(run_ts):
        return pd.DataFrame(), None
    run_ts = run_ts.normalize()

    candidate_dirs: list[Path] = []
    if snapshots_dir is not None:
        candidate_dirs.append(snapshots_dir)
    else:
        candidate_dirs.append(primary_snapshots_dir)
        if use_legacy_snapshots:
            candidate_dirs.append(legacy_snapshots_dir)

    candidates: list[tuple[pd.Timestamp, Path]] = []
    seen_paths: set[Path] = set()
    for base_dir in candidate_dirs:
        if not base_dir.exists():
            continue
        for path in sorted(base_dir.glob("*_real_portfolio_master.csv")):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            stamp = path.name.split("_real_portfolio_master.csv", 1)[0]
            ts = pd.to_datetime(stamp, errors="coerce")
            if pd.isna(ts):
                continue
            if ts.normalize() < run_ts:
                candidates.append((ts.normalize(), path))

    if not candidates:
        return pd.DataFrame(), None

    for previous_date, previous_path in sorted(candidates, key=lambda item: item[0], reverse=True):
        previous_df = _load_snapshot_csv_impl(
            previous_path,
            required_snapshot_columns=required_snapshot_columns,
            optional_numeric_columns=optional_numeric_columns,
            logger=logger,
        )
        if not previous_df.empty:
            if previous_path.parent == legacy_snapshots_dir:
                logger.warning(
                    "Usando snapshot legacy desde %s. Migra snapshots operativos a %s o desactiva el fallback con ENABLE_LEGACY_SNAPSHOTS=0.",
                    previous_path,
                    primary_snapshots_dir,
                )
            return previous_df, previous_date.strftime("%Y-%m-%d")
    return pd.DataFrame(), None
