from __future__ import annotations

import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait
from contextlib import contextmanager
from datetime import datetime, timezone
from getpass import getpass
import json
from pathlib import Path
from typing import TypedDict
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

import config as project_config
from analytics.bond_analytics import (
    build_bond_local_subfamily_summary,
    build_bond_monitor_table,
    build_bond_subfamily_summary,
    enrich_bond_analytics,
)
from analytics.portfolio_risk import build_portfolio_risk_bundle
from analytics.technical import build_technical_overlay
from clients.argentinadatos import get_dollar_series, get_mep_real, get_riesgo_pais_latest
from clients.bcra import get_bcra_monetary_context, get_rem_latest
from clients.bonistas_client import get_bonds_for_portfolio, get_macro_variables
from clients.finviz_client import fetch_finviz_bundle
from clients.fred_client import get_ust_latest
from clients.iol import (
    iol_get_estado_cuenta,
    iol_get_operaciones,
    iol_get_portafolio,
    iol_get_quote_with_reauth,
    iol_login,
)
from clients.pyobd_client import get_bond_volume_context
from decision.history import (
    DEFAULT_DECISION_HISTORY_RETENTION_DAYS,
    apply_decision_history_retention,
    build_decision_history_observation,
    build_temporal_memory_summary,
    enrich_with_temporal_memory,
    load_decision_history,
    resolve_market_run_date,
    save_decision_history,
    upsert_daily_decision_history,
)
from generate_real_report_bonistas import build_real_bonistas_bundle_impl
from generate_real_report_cli import (
    load_local_env_impl,
    parse_args_impl,
    prompt_money_ars_impl,
    prompt_yes_no_impl,
    resolve_iol_credentials_impl,
)
from generate_real_report_runtime import (
    backup_runtime_csvs_impl,
    enrich_real_cedears_impl,
    extract_operation_quote_tickers_impl,
    extract_quote_tickers_impl,
    fetch_iol_payloads_impl,
    fetch_prices_impl,
    parse_finviz_number_impl,
    parse_finviz_pct_impl,
)
from generate_real_report_snapshots import (
    load_previous_portfolio_snapshot_impl,
    write_real_snapshots_impl,
)
from pipeline import (
    build_dashboard_bundle,
    build_decision_bundle,
    build_portfolio_bundle,
    build_prediction_bundle,
    build_sizing_bundle,
)
from portfolio.operations import build_operations_bundle, enrich_operations_bundle
from prediction.store import (
    DEFAULT_PREDICTION_HISTORY_RETENTION_DAYS,
    apply_prediction_history_retention,
    load_prediction_history,
    save_prediction_history,
    upsert_prediction_history,
)
from prediction.maturity import MIN_OUTCOMES_PER_FAMILY_FOR_CALIBRATION, MIN_RUNS_FOR_RELIABLE_SERIES
from report_renderer import REPORTS_DIR, render_report


HTML_PATH = REPORTS_DIR / "real-report.html"
SNAPSHOTS_DIR = ROOT / "data" / "snapshots"
LEGACY_SNAPSHOTS_DIR = ROOT / "tests" / "snapshots"
RUNTIME_DIR = ROOT / "data" / "runtime"
BACKUPS_DIR = ROOT / "data" / "backups"
IOL_PRICE_CACHE_PATH = RUNTIME_DIR / "iol_price_cache.json"
ENV_PATH = ROOT / ".env"
logger = logging.getLogger(__name__)

REQUIRED_SNAPSHOT_COLUMNS = {"Ticker_IOL"}
SNAPSHOT_OPTIONAL_NUMERIC_COLUMNS = ("Peso_%", "Valorizado_ARS", "Cantidad", "Cantidad_Real")
BOND_CONTEXT_COLS = (
    "Ticker_IOL",
    "bonistas_local_subfamily",
    "bonistas_tir_pct",
    "bonistas_paridad_pct",
    "bonistas_md",
    "bonistas_volume_last",
    "bonistas_volume_avg_20d",
    "bonistas_volume_ratio",
    "bonistas_liquidity_bucket",
    "bonistas_days_to_maturity",
    "bonistas_tir_vs_avg_365d_pct",
    "bonistas_parity_gap_pct",
    "bonistas_put_flag",
    "bonistas_riesgo_pais_bps",
    "bonistas_reservas_bcra_musd",
    "bonistas_a3500_mayorista",
    "bonistas_rem_inflacion_mensual_pct",
    "bonistas_rem_inflacion_12m_pct",
    "bonistas_ust_5y_pct",
    "bonistas_ust_10y_pct",
    "bonistas_spread_vs_ust_pct",
)


class MarketRuntimeInputs(TypedDict):
    activos: list[dict[str, object]]
    estado_payload: dict[str, object]
    operaciones_payload: list[dict[str, object]]
    mep_real: float | None
    mep_daily_returns: pd.Series
    precios_iol: dict[str, float]


class DecisionPhaseContext(TypedDict):
    portfolio_bundle: dict[str, object]
    bonistas_bundle: dict[str, object]
    decision_bundle: dict[str, object]
    prediction_bundle: dict[str, object]
    sizing_bundle: dict[str, object]


class OutputPhaseContext(TypedDict):
    dashboard_bundle: dict[str, object]
    risk_bundle: dict[str, object]
    operations_bundle: dict[str, object]
    technical_overlay: pd.DataFrame
    price_history: dict[str, list[float]]
    finviz_stats: dict[str, object]


class AnalysisContext(TypedDict):
    decision_phase: DecisionPhaseContext
    output_phase: OutputPhaseContext


def legacy_snapshots_enabled() -> bool:
    raw = str(os.environ.get("ENABLE_LEGACY_SNAPSHOTS", "1")).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _count_snapshot_days(*, snapshots_dir: Path) -> int:
    if not snapshots_dir.exists():
        return 0
    days: set[str] = set()
    for path in snapshots_dir.glob("*_real_portfolio_master.csv"):
        stamp = path.name.split("_real_portfolio_master.csv", 1)[0].strip()
        if stamp:
            days.add(stamp)
    return len(days)


def should_use_legacy_snapshots() -> bool:
    if not legacy_snapshots_enabled():
        return False
    # Cuando la carpeta canonica ya tiene ventana suficiente, se apaga fallback legacy.
    return _count_snapshot_days(snapshots_dir=SNAPSHOTS_DIR) < MIN_RUNS_FOR_RELIABLE_SERIES


class _JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    if logging.getLogger().handlers:
        return
    log_format = str(os.environ.get("LOG_FORMAT", "")).strip().lower()
    if log_format == "json":
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonLogFormatter())
        logging.basicConfig(
            level=logging.INFO,
            handlers=[handler],
        )
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@contextmanager
def _log_phase_duration(label: str):
    started = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - started
        logger.info("Fase %s: %.1fs", label, elapsed)


def load_local_env(path: Path = ENV_PATH) -> dict[str, str]:
    return load_local_env_impl(path, environ=os.environ)


def resolve_iol_credentials(
    *,
    username_override: str = "",
    password_override: str = "",
    non_interactive: bool = False,
) -> tuple[str, str]:
    return resolve_iol_credentials_impl(
        username_override=username_override,
        password_override=password_override,
        non_interactive=non_interactive,
        load_local_env_fn=load_local_env,
        environ=os.environ,
        input_fn=input,
        getpass_fn=getpass,
        print_fn=print,
    )


def prompt_yes_no(label: str, *, default: bool = False) -> bool:
    return prompt_yes_no_impl(label, default=default, input_fn=input, print_fn=print)


def prompt_money_ars(label: str) -> float:
    return prompt_money_ars_impl(label, input_fn=input, print_fn=print)


def parse_args(argv: list[str] | None = None):
    return parse_args_impl(argv)


def parse_finviz_number(value: object) -> float:
    return parse_finviz_number_impl(value, logger=logger)


def parse_finviz_pct(value: object) -> float:
    return parse_finviz_pct_impl(value, logger=logger)


def backup_runtime_csvs(*, run_date_value: object) -> list[Path]:
    run_ts = pd.Timestamp(run_date_value)
    backed_up = backup_runtime_csvs_impl(
        runtime_dir=RUNTIME_DIR,
        backups_root=BACKUPS_DIR,
        run_date=run_ts.date(),
    )
    if backed_up:
        logger.info("Backup runtime CSVs: %s", ", ".join(path.name for path in backed_up))
    return backed_up


def extract_quote_tickers(activos: list[dict]) -> list[str]:
    return extract_quote_tickers_impl(activos)


def extract_operation_quote_tickers(operations: list[dict[str, object]] | None, *, limit: int = 20) -> list[str]:
    return extract_operation_quote_tickers_impl(operations, limit=limit)


def fetch_prices(
    tickers: list[str],
    *,
    token: str,
    username: str,
    password: str,
) -> tuple[dict[str, float], str]:
    return fetch_prices_impl(
        tickers,
        token=token,
        username=username,
        password=password,
        iol_get_quote_with_reauth_fn=iol_get_quote_with_reauth,
        base_url=project_config.IOL_BASE_URL,
        market=project_config.MARKET,
        logger=logger,
        print_fn=print,
        cache_path=IOL_PRICE_CACHE_PATH,
    )


def fetch_iol_payloads(
    *,
    token: str,
    username: str,
    password: str,
) -> tuple[dict[str, object], dict[str, object], list[dict[str, object]], str]:
    return fetch_iol_payloads_impl(
        token=token,
        username=username,
        password=password,
        iol_get_portafolio_fn=iol_get_portafolio,
        iol_get_estado_cuenta_fn=iol_get_estado_cuenta,
        iol_get_operaciones_fn=iol_get_operaciones,
        iol_login_fn=iol_login,
        base_url=project_config.IOL_BASE_URL,
        logger=logger,
    )


def enrich_real_cedears(
    df_cedears: pd.DataFrame,
    *,
    mep_real: float | None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    return enrich_real_cedears_impl(
        df_cedears,
        mep_real=mep_real,
        fetch_finviz_bundle_fn=fetch_finviz_bundle,
        finviz_max_workers=project_config.FINVIZ_MAX_WORKERS,
        finviz_worker_timeout_seconds=float(project_config.FINVIZ_WORKER_TIMEOUT_SECONDS),
        finviz_submit_delay_seconds=float(getattr(project_config, "FINVIZ_SUBMIT_DELAY_SECONDS", 0.0)),
        thread_pool_executor_cls=ThreadPoolExecutor,
        wait_fn=wait,
        sleep_fn=time.sleep,
        logger=logger,
    )


def write_real_snapshots(
    *,
    portfolio_bundle: dict[str, object],
    dashboard_bundle: dict[str, object],
    decision_bundle: dict[str, object],
    technical_overlay: pd.DataFrame | None,
) -> list[Path]:
    return write_real_snapshots_impl(
        portfolio_bundle=portfolio_bundle,
        dashboard_bundle=dashboard_bundle,
        decision_bundle=decision_bundle,
        technical_overlay=technical_overlay,
        snapshots_dir=SNAPSHOTS_DIR,
    )


def load_previous_portfolio_snapshot(
    run_date: object,
    *,
    snapshots_dir: Path | None = None,
) -> tuple[pd.DataFrame, str | None]:
    return load_previous_portfolio_snapshot_impl(
        run_date,
        snapshots_dir=snapshots_dir,
        primary_snapshots_dir=SNAPSHOTS_DIR,
        legacy_snapshots_dir=LEGACY_SNAPSHOTS_DIR,
        use_legacy_snapshots=should_use_legacy_snapshots(),
        required_snapshot_columns=REQUIRED_SNAPSHOT_COLUMNS,
        optional_numeric_columns=SNAPSHOT_OPTIONAL_NUMERIC_COLUMNS,
        logger=logger,
    )


def build_real_bonistas_bundle(df_bonos: pd.DataFrame, *, mep_real: float | None = None) -> dict[str, object]:
    return build_real_bonistas_bundle_impl(
        df_bonos,
        mep_real=mep_real,
        get_bonds_for_portfolio_fn=get_bonds_for_portfolio,
        get_bond_volume_context_fn=get_bond_volume_context,
        get_macro_variables_fn=get_macro_variables,
        get_riesgo_pais_latest_fn=get_riesgo_pais_latest,
        riesgo_pais_url=project_config.ARGENTINADATOS_RIESGO_PAIS_ULTIMO_URL,
        get_rem_latest_fn=get_rem_latest,
        rem_url=project_config.BCRA_REM_URL,
        rem_xls_url=project_config.BCRA_REM_XLS_URL,
        get_bcra_monetary_context_fn=get_bcra_monetary_context,
        bcra_monetarias_api_url=project_config.BCRA_MONETARIAS_API_URL,
        bcra_reservas_id=project_config.BCRA_RESERVAS_ID,
        bcra_a3500_id=project_config.BCRA_A3500_ID,
        bcra_badlar_tna_id=project_config.BCRA_BADLAR_PRIV_TNA_ID,
        bcra_badlar_tea_id=project_config.BCRA_BADLAR_PRIV_TEA_ID,
        get_ust_latest_fn=get_ust_latest,
        enrich_bond_analytics_fn=enrich_bond_analytics,
        build_bond_monitor_table_fn=build_bond_monitor_table,
        build_bond_subfamily_summary_fn=build_bond_subfamily_summary,
        build_bond_local_subfamily_summary_fn=build_bond_local_subfamily_summary,
        logger=logger,
        print_fn=print,
    )


def _resolve_funding_policy(args: object) -> tuple[bool, float]:
    if args.use_iol_liquidity is None:
        if args.non_interactive:
            raise ValueError("Falta definir --use-iol-liquidity o --no-use-iol-liquidity en modo no interactivo.")
        usar_liquidez_iol = prompt_yes_no("Usar liquidez actual de IOL para fondear la estrategia?", default=False)
    else:
        usar_liquidez_iol = bool(args.use_iol_liquidity)

    if args.aporte_externo_ars is None:
        if args.non_interactive:
            raise ValueError("Falta definir --aporte-externo-ars en modo no interactivo.")
        aporte_externo_ars = prompt_money_ars("Cuanto dinero nuevo vas a ingresar en ARS? (enter para 0)")
    else:
        if args.aporte_externo_ars < 0:
            raise ValueError("--aporte-externo-ars no puede ser negativo.")
        aporte_externo_ars = float(args.aporte_externo_ars)
    return usar_liquidez_iol, aporte_externo_ars


def _merge_bond_context_into_decision(decision_bundle: dict[str, object], bonistas_bundle: dict[str, object]) -> dict[str, object]:
    bond_analytics = bonistas_bundle.get("bond_analytics", pd.DataFrame())
    if not isinstance(bond_analytics, pd.DataFrame) or bond_analytics.empty:
        return decision_bundle

    bond_context = bond_analytics[[col for col in BOND_CONTEXT_COLS if col in bond_analytics.columns]].copy()
    decision_bundle["final_decision"] = decision_bundle["final_decision"].merge(
        bond_context,
        on="Ticker_IOL",
        how="left",
    )
    return decision_bundle


def _enrich_decision_with_temporal_memory(decision_bundle: dict[str, object], *, run_date: object) -> dict[str, object]:
    history = load_decision_history()
    current_observation = build_decision_history_observation(
        decision_bundle["final_decision"],
        run_date=run_date,
        market_regime=decision_bundle.get("market_regime"),
    )
    history = upsert_daily_decision_history(history, current_observation)
    decision_retention_days = int(os.environ.get("DECISION_HISTORY_RETENTION_DAYS", DEFAULT_DECISION_HISTORY_RETENTION_DAYS))
    history = apply_decision_history_retention(
        history,
        retention_days=decision_retention_days,
        today=run_date,
    )
    decision_bundle["final_decision"] = enrich_with_temporal_memory(
        decision_bundle["final_decision"],
        history,
        run_date=run_date,
    )
    decision_bundle["decision_memory"] = build_temporal_memory_summary(decision_bundle["final_decision"])
    save_decision_history(history)
    return decision_bundle


def _build_prediction_bundle_with_history(decision_bundle: dict[str, object], *, run_date: object) -> dict[str, object]:
    prediction_bundle = build_prediction_bundle(
        final_decision=decision_bundle["final_decision"],
        weights=project_config.PREDICTION_WEIGHTS,
        run_date=run_date,
        market_regime=decision_bundle.get("market_regime"),
    )
    prediction_history = upsert_prediction_history(
        load_prediction_history(),
        prediction_bundle.get("history_observation", pd.DataFrame()),
    )
    retention_days = int(os.environ.get("PREDICTION_HISTORY_RETENTION_DAYS", DEFAULT_PREDICTION_HISTORY_RETENTION_DAYS))
    prediction_history = apply_prediction_history_retention(
        prediction_history,
        retention_days=retention_days,
        today=run_date,
    )
    save_prediction_history(prediction_history)
    prediction_bundle["history_size"] = int(len(prediction_history))
    prediction_bundle["accuracy"] = _build_prediction_accuracy_metrics(prediction_history)
    return prediction_bundle


def _build_prediction_accuracy_metrics(history: pd.DataFrame) -> dict[str, object]:
    if not isinstance(history, pd.DataFrame) or history.empty:
        return {
            "global": {"completed": 0, "accuracy_pct": None},
            "by_family": [],
            "by_score_band": [],
            "calibration_readiness": [],
        }

    work = history.copy()
    if "outcome" not in work.columns or "correct" not in work.columns:
        return {
            "global": {"completed": 0, "accuracy_pct": None},
            "by_family": [],
            "by_score_band": [],
            "calibration_readiness": [],
        }

    work["outcome"] = work["outcome"].fillna("").astype(str).str.strip()
    completed = work.loc[work["outcome"] != ""].copy()
    if completed.empty:
        return {
            "global": {"completed": 0, "accuracy_pct": None},
            "by_family": [],
            "by_score_band": [],
            "calibration_readiness": [],
        }

    correct_numeric = pd.to_numeric(completed["correct"], errors="coerce")
    global_accuracy = float(correct_numeric.mean() * 100.0) if correct_numeric.notna().any() else None

    by_family_rows: list[dict[str, object]] = []
    if "asset_family" in completed.columns:
        grouped = completed.copy()
        grouped["asset_family"] = grouped["asset_family"].fillna("").astype(str).str.strip().str.lower()
        grouped["asset_family"] = grouped["asset_family"].where(grouped["asset_family"] != "", "sin_familia")
        for family, frame in grouped.groupby("asset_family", dropna=False):
            fam_correct = pd.to_numeric(frame["correct"], errors="coerce")
            fam_accuracy = float(fam_correct.mean() * 100.0) if fam_correct.notna().any() else None
            by_family_rows.append(
                {
                    "asset_family": str(family),
                    "completed": int(len(frame)),
                    "accuracy_pct": fam_accuracy,
                }
            )
        by_family_rows.sort(key=lambda item: (-(item["completed"]), str(item["asset_family"])))

    by_score_band_rows: list[dict[str, object]] = []
    if "score_unificado" in completed.columns:
        scored = completed.copy()
        scored["score_unificado"] = pd.to_numeric(scored["score_unificado"], errors="coerce")
        scored = scored.dropna(subset=["score_unificado"]).copy()
        if not scored.empty:
            bins = [-float("inf"), -0.15, 0.15, float("inf")]
            labels = ["Bajo (<= -0.15)", "Neutro (-0.15 a 0.15)", "Alto (>= 0.15)"]
            scored["score_band"] = pd.cut(
                scored["score_unificado"],
                bins=bins,
                labels=labels,
                include_lowest=True,
                right=True,
            )
            for band in labels:
                frame = scored.loc[scored["score_band"].astype(str) == band].copy()
                if frame.empty:
                    continue
                band_correct = pd.to_numeric(frame["correct"], errors="coerce")
                band_accuracy = float(band_correct.mean() * 100.0) if band_correct.notna().any() else None
                by_score_band_rows.append(
                    {
                        "score_band": band,
                        "completed": int(len(frame)),
                        "accuracy_pct": band_accuracy,
                    }
                )
            by_score_band_rows.sort(key=lambda item: (-(item["completed"]), str(item["score_band"])))

    calibration_readiness_rows: list[dict[str, object]] = []
    if {"asset_family", "direction"}.issubset(set(completed.columns)):
        readiness = completed.copy()
        readiness["asset_family"] = readiness["asset_family"].fillna("").astype(str).str.strip().str.lower()
        readiness["asset_family"] = readiness["asset_family"].where(readiness["asset_family"] != "", "sin_familia")
        readiness["direction"] = readiness["direction"].fillna("neutral").astype(str).str.strip().str.lower()
        readiness["direction"] = readiness["direction"].where(readiness["direction"] != "", "neutral")
        pivot = (
            readiness.groupby(["asset_family", "direction"], dropna=False)
            .size()
            .unstack(fill_value=0)
        )
        for family, row in pivot.iterrows():
            up_n = int(row.get("up", 0))
            down_n = int(row.get("down", 0))
            neutral_n = int(row.get("neutral", 0))
            min_count = min(up_n, down_n, neutral_n)
            ready = min_count >= MIN_OUTCOMES_PER_FAMILY_FOR_CALIBRATION
            calibration_readiness_rows.append(
                {
                    "asset_family": str(family),
                    "up": up_n,
                    "down": down_n,
                    "neutral": neutral_n,
                    "min_count": min_count,
                    "required": MIN_OUTCOMES_PER_FAMILY_FOR_CALIBRATION,
                    "ready": ready,
                }
            )
        calibration_readiness_rows.sort(key=lambda item: (item["ready"] is False, -item["min_count"], item["asset_family"]))

    return {
        "global": {
            "completed": int(len(completed)),
            "accuracy_pct": global_accuracy,
        },
        "by_family": by_family_rows,
        "by_score_band": by_score_band_rows,
        "calibration_readiness": calibration_readiness_rows,
    }


def _build_risk_bundle(
    df_total: pd.DataFrame,
    *,
    run_date: object,
    dashboard_bundle: dict[str, object],
    benchmark_daily_returns: pd.Series | None = None,
) -> dict[str, object]:
    risk_snapshot_dirs = [SNAPSHOTS_DIR]
    if should_use_legacy_snapshots():
        risk_snapshot_dirs.append(LEGACY_SNAPSHOTS_DIR)
    return build_portfolio_risk_bundle(
        df_total,
        run_date=run_date,
        snapshots_dirs=risk_snapshot_dirs,
        total_ars=float(dashboard_bundle.get("kpis", {}).get("total_ars", 0) or 0),
        benchmark_daily_returns=benchmark_daily_returns,
        benchmark_name="MEP",
    )


def _build_operations_context(
    operaciones_payload: list[dict[str, object]],
    *,
    portfolio_bundle: dict[str, object],
    run_date: object,
) -> dict[str, object]:
    previous_portfolio, previous_snapshot_date = load_previous_portfolio_snapshot(run_date)
    return enrich_operations_bundle(
        build_operations_bundle(operaciones_payload),
        current_portfolio=portfolio_bundle["df_total"],
        previous_portfolio=previous_portfolio,
        previous_snapshot_date=previous_snapshot_date,
    )


def _print_coverage_stats(technical_overlay: pd.DataFrame, df_cedears: pd.DataFrame, finviz_stats: dict[str, object]) -> None:
    tech_metric_cols = [
        "Dist_SMA20_%",
        "Dist_SMA50_%",
        "Dist_EMA20_%",
        "Dist_EMA50_%",
        "RSI_14",
        "Momentum_20d_%",
        "Momentum_60d_%",
        "Vol_20d_Anual_%",
        "Drawdown_desde_Max3m_%",
    ]
    tech_available_cols = [col for col in tech_metric_cols if col in technical_overlay.columns]
    tech_covered = int(technical_overlay[tech_available_cols].notna().any(axis=1).sum()) if tech_available_cols else 0
    tech_total = int(len(df_cedears))
    print(f"Cobertura tÃ©cnica: {tech_covered}/{tech_total}")
    print(
        "Cobertura Finviz: "
        f"{finviz_stats.get('fundamentals_covered', 0)}/{finviz_stats.get('cedears_total', 0)}"
        f" | Ratings: {finviz_stats.get('ratings_covered', 0)}/{finviz_stats.get('cedears_total', 0)}"
    )
    if finviz_stats.get("errors"):
        print("Errores Finviz (muestra):")
        for item in finviz_stats["errors"]:
            print(f"  - {item}")


def _build_report_payload(
    *,
    mep_real: float | None,
    run_ts: pd.Timestamp,
    precios_iol: dict[str, float],
    portfolio_bundle: dict[str, object],
    dashboard_bundle: dict[str, object],
    decision_bundle: dict[str, object],
    sizing_bundle: dict[str, object],
    technical_overlay: pd.DataFrame,
    price_history: dict[str, list[float]],
    finviz_stats: dict[str, object],
    bonistas_bundle: dict[str, object],
    operations_bundle: dict[str, object],
    prediction_bundle: dict[str, object],
    risk_bundle: dict[str, object],
) -> dict[str, object]:
    return {
        "mep_real": mep_real or 0.0,
        "generated_at_label": run_ts.strftime("%Y-%m-%d %H:%M:%S"),
        "precios_iol": precios_iol,
        "vn_factor_map": project_config.VN_FACTOR_MAP,
        "portfolio_bundle": portfolio_bundle,
        "dashboard_bundle": dashboard_bundle,
        "decision_bundle": decision_bundle,
        "sizing_bundle": sizing_bundle,
        "technical_overlay": technical_overlay,
        "price_history": price_history,
        "finviz_stats": finviz_stats,
        "bonistas_bundle": bonistas_bundle,
        "operations_bundle": operations_bundle,
        "prediction_bundle": prediction_bundle,
        "risk_bundle": risk_bundle,
    }


def _render_and_persist_report(
    report: dict[str, object],
    *,
    portfolio_bundle: dict[str, object],
    dashboard_bundle: dict[str, object],
    decision_bundle: dict[str, object],
    technical_overlay: pd.DataFrame,
) -> None:
    render_started = time.perf_counter()
    html_body = render_report(
        report,
        title="Real Run",
        headline="Prueba visual con datos reales de IOL",
        lede="Reporte generado con login por terminal. Las credenciales no se guardan en disco.",
    )
    HTML_PATH.write_text(html_body, encoding="utf-8")
    logger.info("Report rendered in %.2fs", time.perf_counter() - render_started)
    snapshot_paths = write_real_snapshots(
        portfolio_bundle=portfolio_bundle,
        dashboard_bundle=dashboard_bundle,
        decision_bundle=decision_bundle,
        technical_overlay=technical_overlay,
    )
    print(f"Reporte generado en: {HTML_PATH}")
    print("Snapshots generados:")
    for path in snapshot_paths:
        print(f"  - {path}")


def _collect_market_runtime_inputs(*, username: str, password: str) -> MarketRuntimeInputs:
    print("Login IOL...")
    token = iol_login(username, password, base_url=project_config.IOL_BASE_URL)

    print("Descargando portafolio, estado de cuenta y operaciones...")
    portfolio_payload, estado_payload, operaciones_payload, token = fetch_iol_payloads(
        token=token,
        username=username,
        password=password,
    )
    activos = portfolio_payload.get("activos", []) or []

    mep_data = get_mep_real(casa=project_config.MEP_CASA, base_url=project_config.ARGENTINADATOS_URL)
    mep_real = float(mep_data["promedio"]) if mep_data else None
    mep_daily_returns = pd.Series(dtype=float)
    try:
        mep_series = get_dollar_series(casa=project_config.MEP_CASA, base_url=project_config.ARGENTINADATOS_URL)
        mep_df = pd.DataFrame(mep_series)
        if not mep_df.empty and "fecha" in mep_df.columns and {"compra", "venta"}.issubset(set(mep_df.columns)):
            mep_df["fecha"] = pd.to_datetime(mep_df["fecha"], errors="coerce").dt.normalize()
            mep_df["compra"] = pd.to_numeric(mep_df["compra"], errors="coerce")
            mep_df["venta"] = pd.to_numeric(mep_df["venta"], errors="coerce")
            mep_df["promedio"] = (mep_df["compra"] + mep_df["venta"]) / 2.0
            mep_df = mep_df.dropna(subset=["fecha", "promedio"]).sort_values("fecha")
            if not mep_df.empty:
                mep_daily = mep_df.groupby("fecha", as_index=True)["promedio"].last()
                mep_daily_returns = mep_daily.pct_change().dropna() * 100.0
    except Exception as exc:
        logger.warning("No se pudo construir benchmark diario MEP: %s", exc)

    tickers = sorted(set(extract_quote_tickers(activos)) | set(extract_operation_quote_tickers(operaciones_payload)))
    print(f"Descargando precios IOL para {len(tickers)} tickers...")
    precios_iol, token = fetch_prices(tickers, token=token, username=username, password=password)

    return {
        "activos": activos,
        "estado_payload": estado_payload,
        "operaciones_payload": operaciones_payload,
        "mep_real": mep_real,
        "mep_daily_returns": mep_daily_returns,
        "precios_iol": precios_iol,
    }


def _build_analysis_context(
    *,
    activos: list[dict[str, object]],
    estado_payload: dict[str, object],
    operaciones_payload: list[dict[str, object]],
    mep_real: float | None,
    precios_iol: dict[str, float],
    benchmark_daily_returns: pd.Series | None,
    run_date: object,
    usar_liquidez_iol: bool,
    aporte_externo_ars: float,
) -> AnalysisContext:
    portfolio_bundle = build_portfolio_bundle(
        activos=activos,
        estado_payload=estado_payload,
        precios_iol=precios_iol,
        mep_real=mep_real,
        finviz_map=project_config.FINVIZ_MAP,
        block_map=project_config.BLOCK_MAP,
        argentina_equity_map=project_config.ARGENTINA_EQUITY_MAP,
        instrument_profile_map=project_config.INSTRUMENT_PROFILE_MAP,
        vn_factor_map=project_config.VN_FACTOR_MAP,
        ratios=project_config.RATIOS,
        fci_cash_management=project_config.FCI_CASH_MANAGEMENT,
    )
    bonistas_bundle = build_real_bonistas_bundle(portfolio_bundle["df_bonos"], mep_real=mep_real)

    df_total = portfolio_bundle["df_total"]
    df_cedears, df_ratings_res, finviz_stats = enrich_real_cedears(portfolio_bundle["df_cedears"], mep_real=mep_real)
    price_history: dict[str, list[float]] = {}
    technical_overlay = build_technical_overlay(df_cedears, scoring_rules=project_config.SCORING_RULES, price_history_out=price_history)
    _print_coverage_stats(technical_overlay, df_cedears, finviz_stats)

    decision_bundle = build_decision_bundle(
        df_total=df_total,
        df_cedears=df_cedears,
        df_ratings_res=df_ratings_res,
        decision_tech=technical_overlay,
        mep_real=mep_real,
        market_context=bonistas_bundle.get("macro_variables", {}),
        scoring_rules=project_config.SCORING_RULES,
        action_rules=project_config.ACTION_RULES,
    )
    decision_bundle = _merge_bond_context_into_decision(decision_bundle, bonistas_bundle)
    decision_bundle = _enrich_decision_with_temporal_memory(decision_bundle, run_date=run_date)
    prediction_bundle = _build_prediction_bundle_with_history(decision_bundle, run_date=run_date)
    sizing_bundle = build_sizing_bundle(
        final_decision=decision_bundle["final_decision"],
        mep_real=mep_real,
        bucket_weights=project_config.BUCKET_WEIGHTS,
        usar_liquidez_iol=usar_liquidez_iol,
        aporte_externo_ars=aporte_externo_ars,
        action_rules=project_config.ACTION_RULES,
        sizing_rules=project_config.SIZING_RULES,
    )
    dashboard_bundle = build_dashboard_bundle(
        df_total,
        mep_real=mep_real,
        liquidity_contract=portfolio_bundle.get("liquidity_contract"),
    )
    risk_bundle = _build_risk_bundle(
        df_total,
        run_date=run_date,
        dashboard_bundle=dashboard_bundle,
        benchmark_daily_returns=benchmark_daily_returns,
    )
    operations_bundle = _build_operations_context(
        operaciones_payload,
        portfolio_bundle=portfolio_bundle,
        run_date=run_date,
    )

    decision_phase: DecisionPhaseContext = {
        "portfolio_bundle": portfolio_bundle,
        "bonistas_bundle": bonistas_bundle,
        "decision_bundle": decision_bundle,
        "prediction_bundle": prediction_bundle,
        "sizing_bundle": sizing_bundle,
    }
    output_phase: OutputPhaseContext = {
        "dashboard_bundle": dashboard_bundle,
        "risk_bundle": risk_bundle,
        "operations_bundle": operations_bundle,
        "technical_overlay": technical_overlay,
        "price_history": price_history,
        "finviz_stats": finviz_stats,
    }
    return {
        "decision_phase": decision_phase,
        "output_phase": output_phase,
    }


def run_real_report(args: object) -> None:
    configure_logging()
    REPORTS_DIR.mkdir(exist_ok=True)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    run_ts = pd.Timestamp.now(tz=ZoneInfo("America/Argentina/Buenos_Aires"))
    run_date = resolve_market_run_date(run_ts)
    with _log_phase_duration("Backup runtime"):
        backup_runtime_csvs(run_date_value=run_date)

    with _log_phase_duration("Credenciales"):
        username, password = resolve_iol_credentials(
            username_override=args.username,
            password_override=args.password,
            non_interactive=args.non_interactive,
        )
    with _log_phase_duration("Datos de mercado"):
        market_inputs: MarketRuntimeInputs = _collect_market_runtime_inputs(username=username, password=password)
    activos = market_inputs["activos"]
    estado_payload = market_inputs["estado_payload"]
    operaciones_payload = market_inputs["operaciones_payload"]
    mep_real = market_inputs["mep_real"]
    mep_daily_returns = market_inputs["mep_daily_returns"]
    precios_iol = market_inputs["precios_iol"]

    print("Definiendo politica de fondeo...")
    usar_liquidez_iol, aporte_externo_ars = _resolve_funding_policy(args)
    with _log_phase_duration("Analisis y decision"):
        analysis_context: AnalysisContext = _build_analysis_context(
            activos=activos,
            estado_payload=estado_payload,
            operaciones_payload=operaciones_payload,
            mep_real=mep_real,
            precios_iol=precios_iol,
            benchmark_daily_returns=mep_daily_returns,
            run_date=run_date,
            usar_liquidez_iol=usar_liquidez_iol,
            aporte_externo_ars=aporte_externo_ars,
        )
    decision_phase = analysis_context["decision_phase"]
    output_phase = analysis_context["output_phase"]

    with _log_phase_duration("Render y persistencia"):
        report = _build_report_payload(
            mep_real=mep_real,
            run_ts=run_ts,
            precios_iol=precios_iol,
            portfolio_bundle=decision_phase["portfolio_bundle"],
            dashboard_bundle=output_phase["dashboard_bundle"],
            decision_bundle=decision_phase["decision_bundle"],
            sizing_bundle=decision_phase["sizing_bundle"],
            technical_overlay=output_phase["technical_overlay"],
            price_history=output_phase["price_history"],
            finviz_stats=output_phase["finviz_stats"],
            bonistas_bundle=decision_phase["bonistas_bundle"],
            operations_bundle=output_phase["operations_bundle"],
            prediction_bundle=decision_phase["prediction_bundle"],
            risk_bundle=output_phase["risk_bundle"],
        )
        _render_and_persist_report(
            report,
            portfolio_bundle=decision_phase["portfolio_bundle"],
            dashboard_bundle=output_phase["dashboard_bundle"],
            decision_bundle=decision_phase["decision_bundle"],
            technical_overlay=output_phase["technical_overlay"],
        )


def run_scheduled_real_report(args: object, *, sleep_fn=time.sleep) -> None:
    interval_minutes = int(getattr(args, "schedule_every_minutes", 0) or 0)
    if interval_minutes <= 0:
        run_real_report(args)
        return
    if not bool(getattr(args, "non_interactive", False)):
        raise ValueError("--schedule-every-minutes requiere --non-interactive.")
    logger.info("Scheduler activo: corrida cada %s minutos.", interval_minutes)
    while True:
        try:
            run_real_report(args)
        except Exception:
            logger.exception("La corrida programada finalizo con error.")
        sleep_fn(interval_minutes * 60)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run_scheduled_real_report(args)


if __name__ == "__main__":
    main()
