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
    prediction_bundle: dict[str, object] | None,
    technical_overlay: pd.DataFrame | None,
    finviz_stats: dict[str, object] | None,
    snapshots_dir: Path,
) -> list[Path]:
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    stamp = pd.Timestamp.now().strftime("%Y-%m-%d")

    df_total = portfolio_bundle["df_total"].copy()
    final_decision = decision_bundle["final_decision"].copy()
    liquidity_contract = dict(portfolio_bundle["liquidity_contract"])
    kpis = dict(dashboard_bundle["kpis"])
    finviz = finviz_stats or {}
    finviz_total = int(finviz.get("cedears_total", 0) or 0)
    finviz_fundamentals = int(finviz.get("fundamentals_covered", 0) or 0)
    finviz_ratings = int(finviz.get("ratings_covered", 0) or 0)
    finviz_degraded = bool(finviz_total > 0 and (finviz_fundamentals == 0 or finviz_ratings == 0))
    kpis["finviz_degraded"] = finviz_degraded
    kpis["finviz_fundamentals_covered"] = finviz_fundamentals
    kpis["finviz_ratings_covered"] = finviz_ratings
    kpis["finviz_total"] = finviz_total
    accuracy = (prediction_bundle or {}).get("accuracy", {}) if isinstance(prediction_bundle, dict) else {}
    health = accuracy.get("health", {}) if isinstance(accuracy, dict) else {}
    kpis["prediction_verifiable_due_status"] = str(health.get("verifiable_due_status", "ok") or "ok")
    kpis["prediction_verifiable_pending_due"] = int(health.get("verifiable_pending_due", 0) or 0)
    kpis["prediction_verifiable_pending"] = int(health.get("verifiable_pending", 0) or 0)
    kpis["prediction_verifiable_total"] = int(health.get("verifiable_total", 0) or 0)
    kpis["prediction_pending_due_verifiable_top"] = health.get("pending_due_verifiable_top", [])
    verifiable_due = int(kpis["prediction_verifiable_pending_due"] or 0)
    if finviz_degraded:
        kpis["run_quality_status"] = "degradada"
        kpis["run_quality_detail"] = f"finviz {finviz_fundamentals}/{finviz_total} | ratings {finviz_ratings}/{finviz_total}"
        kpis["run_quality_recommendation"] = "restaurar cobertura finviz antes de usar la corrida como referencia táctica"
    elif verifiable_due > 20:
        kpis["run_quality_status"] = "critica"
        kpis["run_quality_detail"] = f"{verifiable_due} vencidos verificables"
        kpis["run_quality_recommendation"] = "priorizar cierre de vencidos verificables hasta bajar de 20"
    elif verifiable_due > 0:
        kpis["run_quality_status"] = "atencion"
        kpis["run_quality_detail"] = f"{verifiable_due} vencidos verificables"
        kpis["run_quality_recommendation"] = "llevar vencidos verificables a 0 para estabilizar métricas históricas"
    else:
        kpis["run_quality_status"] = "ok"
        kpis["run_quality_detail"] = "sin vencidos verificables"
        kpis["run_quality_recommendation"] = "mantener monitoreo diario"

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
