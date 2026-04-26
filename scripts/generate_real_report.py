from __future__ import annotations

import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait
from getpass import getpass
from pathlib import Path
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
from clients.argentinadatos import get_mep_real, get_riesgo_pais_latest
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
from prediction.store import load_prediction_history, save_prediction_history, upsert_prediction_history
from report_renderer import REPORTS_DIR, render_report


HTML_PATH = REPORTS_DIR / "real-report.html"
SNAPSHOTS_DIR = ROOT / "data" / "snapshots"
LEGACY_SNAPSHOTS_DIR = ROOT / "tests" / "snapshots"
ENV_PATH = ROOT / ".env"
logger = logging.getLogger(__name__)

REQUIRED_SNAPSHOT_COLUMNS = {"Ticker_IOL"}
SNAPSHOT_OPTIONAL_NUMERIC_COLUMNS = ("Peso_%", "Valorizado_ARS", "Cantidad", "Cantidad_Real")


def legacy_snapshots_enabled() -> bool:
    raw = str(os.environ.get("ENABLE_LEGACY_SNAPSHOTS", "1")).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def configure_logging() -> None:
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


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
        use_legacy_snapshots=legacy_snapshots_enabled(),
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


def main(argv: list[str] | None = None) -> None:
    configure_logging()
    args = parse_args(argv)
    REPORTS_DIR.mkdir(exist_ok=True)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    run_ts = pd.Timestamp.now(tz=ZoneInfo("America/Argentina/Buenos_Aires"))
    run_date = resolve_market_run_date(run_ts)

    username, password = resolve_iol_credentials(
        username_override=args.username,
        password_override=args.password,
        non_interactive=args.non_interactive,
    )

    print("Login IOL...")
    token = iol_login(username, password, base_url=project_config.IOL_BASE_URL)

    print("Descargando portafolio, estado de cuenta y operaciones...")
    portfolio_payload, estado_payload, operaciones_payload, token = fetch_iol_payloads(
        token=token,
        username=username,
        password=password,
    )
    activos = portfolio_payload.get("activos", []) or []

    print("Definiendo politica de fondeo...")
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

    mep_data = get_mep_real(casa=project_config.MEP_CASA, base_url=project_config.ARGENTINADATOS_URL)
    mep_real = float(mep_data["promedio"]) if mep_data else None

    tickers = sorted(set(extract_quote_tickers(activos)) | set(extract_operation_quote_tickers(operaciones_payload)))
    print(f"Descargando precios IOL para {len(tickers)} tickers...")
    precios_iol, token = fetch_prices(tickers, token=token, username=username, password=password)

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
    print(f"Cobertura técnica: {tech_covered}/{tech_total}")
    print(
        "Cobertura Finviz: "
        f"{finviz_stats.get('fundamentals_covered', 0)}/{finviz_stats.get('cedears_total', 0)}"
        f" | Ratings: {finviz_stats.get('ratings_covered', 0)}/{finviz_stats.get('cedears_total', 0)}"
    )
    if finviz_stats.get("errors"):
        print("Errores Finviz (muestra):")
        for item in finviz_stats["errors"]:
            print(f"  - {item}")

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
    bond_analytics = bonistas_bundle.get("bond_analytics", pd.DataFrame())
    if isinstance(bond_analytics, pd.DataFrame) and not bond_analytics.empty:
        bond_context_cols = [
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
        ]
        bond_context = bond_analytics[[col for col in bond_context_cols if col in bond_analytics.columns]].copy()
        decision_bundle["final_decision"] = decision_bundle["final_decision"].merge(
            bond_context,
            on="Ticker_IOL",
            how="left",
        )
    history = load_decision_history()
    current_observation = build_decision_history_observation(
        decision_bundle["final_decision"],
        run_date=run_date,
        market_regime=decision_bundle.get("market_regime"),
    )
    history = upsert_daily_decision_history(history, current_observation)
    decision_bundle["final_decision"] = enrich_with_temporal_memory(
        decision_bundle["final_decision"],
        history,
        run_date=run_date,
    )
    decision_bundle["decision_memory"] = build_temporal_memory_summary(decision_bundle["final_decision"])
    save_decision_history(history)
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
    save_prediction_history(prediction_history)
    prediction_bundle["history_size"] = int(len(prediction_history))
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
    risk_snapshot_dirs = [SNAPSHOTS_DIR]
    if legacy_snapshots_enabled():
        risk_snapshot_dirs.append(LEGACY_SNAPSHOTS_DIR)
    risk_bundle = build_portfolio_risk_bundle(
        df_total,
        run_date=run_date,
        snapshots_dirs=risk_snapshot_dirs,
        total_ars=float(dashboard_bundle.get("kpis", {}).get("total_ars", 0) or 0),
    )
    previous_portfolio, previous_snapshot_date = load_previous_portfolio_snapshot(run_date)
    operations_bundle = enrich_operations_bundle(
        build_operations_bundle(operaciones_payload),
        current_portfolio=portfolio_bundle["df_total"],
        previous_portfolio=previous_portfolio,
        previous_snapshot_date=previous_snapshot_date,
    )

    report = {
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


if __name__ == "__main__":
    main()
