from __future__ import annotations

import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait
from getpass import getpass
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

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
from pipeline import build_dashboard_bundle, build_decision_bundle, build_portfolio_bundle, build_sizing_bundle
from portfolio.operations import build_operations_bundle, enrich_operations_bundle
from report_renderer import REPORTS_DIR, render_report


HTML_PATH = REPORTS_DIR / "real-report.html"
SNAPSHOTS_DIR = ROOT / "data" / "snapshots"
LEGACY_SNAPSHOTS_DIR = ROOT / "tests" / "snapshots"
ENV_PATH = ROOT / ".env"
logger = logging.getLogger(__name__)

REQUIRED_SNAPSHOT_COLUMNS = {"Ticker_IOL"}


def configure_logging() -> None:
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def load_local_env(path: Path = ENV_PATH) -> dict[str, str]:
    if not path.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if not key:
            continue
        loaded[key] = value
        os.environ.setdefault(key, value)

    return loaded


def resolve_iol_credentials() -> tuple[str, str]:
    load_local_env()

    username = os.environ.get("IOL_USERNAME", "").strip()
    password = os.environ.get("IOL_PASSWORD", "").strip()

    if not username:
        username = input("Usuario IOL: ").strip()
    else:
        print("Usuario IOL: cargado desde entorno")

    if not password:
        password = getpass("Password IOL: ").strip()
    else:
        print("Password IOL: cargado desde entorno")

    if not username or not password:
        raise ValueError("Usuario y password son obligatorios.")

    return username, password


def prompt_yes_no(label: str, *, default: bool = False) -> bool:
    suffix = " [s/N]: " if not default else " [S/n]: "
    while True:
        raw = input(label + suffix).strip().lower()
        if not raw:
            return default
        if raw in {"s", "si", "sí", "y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Respuesta invalida. Ingresa 's' o 'n'.")


def prompt_money_ars(label: str) -> float:
    while True:
        raw = input(label + " ").strip()
        if not raw:
            return 0.0
        normalized = raw.replace("$", "").replace(".", "").replace(",", ".").strip()
        try:
            amount = float(normalized)
        except ValueError:
            print("Monto invalido. Ingresa un numero en ARS, por ejemplo 600000.")
            continue
        if amount < 0:
            print("El monto no puede ser negativo. Ingresa 0 o un valor positivo.")
            continue
        return amount


def parse_finviz_number(value: object) -> float:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    text = str(value).strip().replace(",", "")
    if not text or text == "-":
        return np.nan
    suffixes = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
    suffix = text[-1].upper()
    if suffix in suffixes:
        try:
            return float(text[:-1]) * suffixes[suffix]
        except Exception as exc:
            logger.debug("No se pudo parsear numero Finviz con sufijo %r: %s", value, exc)
            return np.nan
    try:
        return float(text)
    except Exception as exc:
        logger.debug("No se pudo parsear numero Finviz %r: %s", value, exc)
        return np.nan


def parse_finviz_pct(value: object) -> float:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    text = str(value).strip().replace(",", "")
    if not text or text == "-":
        return np.nan
    text = text.replace("%", "")
    try:
        return float(text)
    except Exception as exc:
        logger.debug("No se pudo parsear porcentaje Finviz %r: %s", value, exc)
        return np.nan


def extract_quote_tickers(activos: list[dict]) -> list[str]:
    tickers: set[str] = set()
    allowed_types = {"CEDEARS", "ACCIONES", "ACCION", "TITULOSPUBLICOS", "TITULOPUBLICO"}

    for activo in activos:
        titulo = activo.get("titulo", {}) or {}
        simbolo = str(titulo.get("simbolo") or "").strip()
        tipo = str(titulo.get("tipo") or "").strip()
        tipo_norm = tipo.upper().replace(" ", "")

        if not simbolo or tipo_norm not in allowed_types:
            continue
        tickers.add(simbolo)

    return sorted(tickers)


def fetch_prices(
    tickers: list[str],
    *,
    token: str,
    username: str,
    password: str,
) -> tuple[dict[str, float], str]:
    prices: dict[str, float] = {}
    current_token = token

    for ticker in tickers:
        try:
            data, current_token = iol_get_quote_with_reauth(
                ticker,
                current_token,
                username=username,
                password=password,
                base_url=project_config.IOL_BASE_URL,
                market=project_config.MARKET,
            )
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 404:
                print(f"  [skip] Sin cotizacion IOL para {ticker} (404)")
                logger.info("Sin cotizacion IOL para %s (404)", ticker)
                continue
            raise

        price = data.get("ultimoPrecio")
        if price is not None:
            prices[ticker] = float(price)
        else:
            print(f"  [skip] ultimoPrecio ausente para {ticker}")
            logger.info("ultimoPrecio ausente para %s", ticker)

    return prices, current_token


def fetch_iol_payloads(
    *,
    token: str,
    username: str,
    password: str,
) -> tuple[dict[str, object], dict[str, object], list[dict[str, object]], str]:
    current_token = token
    try:
        portfolio_payload = iol_get_portafolio(current_token, base_url=project_config.IOL_BASE_URL, pais="argentina")
        estado_payload = iol_get_estado_cuenta(current_token, base_url=project_config.IOL_BASE_URL)
        operaciones_payload = iol_get_operaciones(
            current_token,
            base_url=project_config.IOL_BASE_URL,
            pais="argentina",
            estado="todas",
        )
        return portfolio_payload, estado_payload, operaciones_payload, current_token
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status != 401:
            raise
        logger.info("IOL token expirado durante descarga inicial. Reautenticando y reintentando.")
        current_token = iol_login(username, password, base_url=project_config.IOL_BASE_URL)
        portfolio_payload = iol_get_portafolio(current_token, base_url=project_config.IOL_BASE_URL, pais="argentina")
        estado_payload = iol_get_estado_cuenta(current_token, base_url=project_config.IOL_BASE_URL)
        operaciones_payload = iol_get_operaciones(
            current_token,
            base_url=project_config.IOL_BASE_URL,
            pais="argentina",
            estado="todas",
        )
        return portfolio_payload, estado_payload, operaciones_payload, current_token


def enrich_real_cedears(
    df_cedears: pd.DataFrame,
    *,
    mep_real: float | None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    if df_cedears.empty:
        return df_cedears, pd.DataFrame(), {
            "cedears_total": 0,
            "fundamentals_covered": 0,
            "ratings_covered": 0,
            "coverage_by_field": {},
            "errors": [],
        }

    out = df_cedears.copy()
    ratings_rows: list[dict[str, object]] = []
    errors: list[str] = []

    defaults = {
        "Perf Week": np.nan,
        "Perf Month": np.nan,
        "Perf YTD": np.nan,
        "Beta": np.nan,
        "P/E": np.nan,
        "ROE": np.nan,
        "Profit Margin": np.nan,
        "MEP_Implicito": np.nan,
    }
    for col, default in defaults.items():
        if col not in out.columns:
            out[col] = default

    tasks: list[tuple[object, dict[str, object]]] = []
    for idx, row in out.iterrows():
        row_data = row.to_dict()
        ticker_finviz = row_data.get("Ticker_Finviz")
        if ticker_finviz:
            tasks.append((idx, row_data))

    if tasks:
        max_workers = min(project_config.FINVIZ_MAX_WORKERS, len(tasks))
        timeout_seconds = float(project_config.FINVIZ_WORKER_TIMEOUT_SECONDS)
        submit_delay_seconds = max(float(getattr(project_config, "FINVIZ_SUBMIT_DELAY_SECONDS", 0.0)), 0.0)
        executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="finviz")
        future_map = {}
        for task_index, (idx, row_data) in enumerate(tasks):
            future = executor.submit(_enrich_cedear_row_payload, idx, row_data=row_data, mep_real=mep_real)
            future_map[future] = (idx, row_data)
            if submit_delay_seconds > 0 and task_index < len(tasks) - 1:
                time.sleep(submit_delay_seconds)
        done, not_done = wait(future_map.keys(), timeout=timeout_seconds)
        for future in done:
            idx, updates, rating_row, error = future.result()
            if error:
                errors.append(error)
                continue
            for col, value in updates.items():
                out.loc[idx, col] = value
            if rating_row is not None:
                ratings_rows.append(rating_row)
        for future in not_done:
            idx, row_data = future_map[future]
            ticker_finviz = str(row_data.get("Ticker_Finviz") or row_data.get("Ticker_IOL") or idx)
            future.cancel()
            errors.append(f"{ticker_finviz}: timeout after {timeout_seconds:.0f}s")
        executor.shutdown(wait=False, cancel_futures=True)

    df_ratings_res = pd.DataFrame(ratings_rows)
    if not df_ratings_res.empty:
        df_ratings_res = df_ratings_res.drop_duplicates(subset=["Ticker_Finviz"]).set_index("Ticker_Finviz")
    coverage_fields = ["Perf Week", "Perf Month", "Perf YTD", "Beta", "P/E", "ROE", "Profit Margin"]
    coverage_by_field = {col: int(out[col].notna().sum()) for col in coverage_fields if col in out.columns}
    fundamentals_covered = int(out[coverage_fields].notna().any(axis=1).sum()) if coverage_fields else 0
    stats = {
        "cedears_total": int(len(out)),
        "fundamentals_covered": fundamentals_covered,
        "ratings_covered": int(len(df_ratings_res)),
        "coverage_by_field": coverage_by_field,
        "errors": errors[:10],
    }
    return out, df_ratings_res, stats


def _enrich_cedear_row_payload(
    idx: object,
    *,
    row_data: dict[str, object],
    mep_real: float | None,
) -> tuple[object, dict[str, object], dict[str, object] | None, str | None]:
    ticker_finviz = row_data.get("Ticker_Finviz")
    if not ticker_finviz:
        return idx, {}, None, None

    try:
        bundle = fetch_finviz_bundle(str(ticker_finviz))
    except Exception as exc:
        logger.warning("Finviz enrichment failed for %s: %s", ticker_finviz, exc)
        return idx, {}, None, f"{ticker_finviz}: {exc}"

    updates: dict[str, object] = {}
    fundamentals = bundle.get("fundamentals", {}) or {}
    updates["Perf Week"] = parse_finviz_pct(fundamentals.get("Perf Week", row_data.get("Perf Week")))
    updates["Perf Month"] = parse_finviz_pct(fundamentals.get("Perf Month", row_data.get("Perf Month")))
    updates["Perf YTD"] = parse_finviz_pct(fundamentals.get("Perf YTD", row_data.get("Perf YTD")))
    updates["Beta"] = parse_finviz_number(fundamentals.get("Beta", row_data.get("Beta")))
    updates["P/E"] = parse_finviz_number(fundamentals.get("P/E", row_data.get("P/E")))
    updates["ROE"] = parse_finviz_pct(fundamentals.get("ROE", row_data.get("ROE")))
    updates["Profit Margin"] = parse_finviz_pct(fundamentals.get("Profit Margin", row_data.get("Profit Margin")))

    if mep_real and pd.notna(row_data.get("Precio_ARS")):
        try:
            updates["MEP_Implicito"] = float(row_data["Precio_ARS"]) / max(float(mep_real), 1.0)
        except Exception as exc:
            logger.debug("No se pudo calcular MEP implicito para %s: %s", ticker_finviz, exc)

    rating_row = None
    ratings = bundle.get("ratings")
    if isinstance(ratings, pd.DataFrame) and not ratings.empty:
        ratings = ratings.copy()
        action_col = next((c for c in ratings.columns if c.lower() in {"rating", "action", "status"}), None)
        if action_col:
            consenso = str(ratings[action_col].mode().iloc[0]) if not ratings[action_col].mode().empty else None
            consenso_n = int((ratings[action_col] == consenso).sum()) if consenso else 0
            rating_row = {
                "Ticker_Finviz": str(ticker_finviz),
                "consenso": consenso,
                "consenso_n": consenso_n,
                "total_ratings": int(len(ratings)),
            }

    return idx, updates, rating_row, None


def write_real_snapshots(
    *,
    portfolio_bundle: dict[str, object],
    dashboard_bundle: dict[str, object],
    decision_bundle: dict[str, object],
    technical_overlay: pd.DataFrame | None,
) -> list[Path]:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = pd.Timestamp.now().strftime("%Y-%m-%d")

    df_total = portfolio_bundle["df_total"].copy()
    final_decision = decision_bundle["final_decision"].copy()
    liquidity_contract = dict(portfolio_bundle["liquidity_contract"])
    kpis = dict(dashboard_bundle["kpis"])

    paths = [
        SNAPSHOTS_DIR / f"{stamp}_real_portfolio_master.csv",
        SNAPSHOTS_DIR / f"{stamp}_real_decision_table.csv",
        SNAPSHOTS_DIR / f"{stamp}_real_liquidity_contract.json",
        SNAPSHOTS_DIR / f"{stamp}_real_kpis.json",
        SNAPSHOTS_DIR / f"{stamp}_real_technical_overlay.csv",
    ]

    df_total.sort_values("Valorizado_ARS", ascending=False).to_csv(paths[0], index=False, encoding="utf-8")
    final_decision.sort_values("score_unificado", ascending=False).to_csv(paths[1], index=False, encoding="utf-8")
    paths[2].write_text(json.dumps(liquidity_contract, ensure_ascii=False, indent=2), encoding="utf-8")
    paths[3].write_text(json.dumps(kpis, ensure_ascii=False, indent=2), encoding="utf-8")
    technical_df = technical_overlay.copy() if isinstance(technical_overlay, pd.DataFrame) else pd.DataFrame()
    technical_df.to_csv(paths[4], index=False, encoding="utf-8")
    return paths


def _load_snapshot_csv(path: Path) -> pd.DataFrame:
    try:
        previous_df = pd.read_csv(path)
    except Exception as exc:
        logger.warning("No se pudo leer snapshot previo %s: %s", path, exc)
        return pd.DataFrame()

    missing_columns = REQUIRED_SNAPSHOT_COLUMNS - set(previous_df.columns)
    if missing_columns:
        logger.warning(
            "Snapshot previo invalido %s. Faltan columnas requeridas: %s",
            path,
            ", ".join(sorted(missing_columns)),
        )
        return pd.DataFrame()
    return previous_df


def load_previous_portfolio_snapshot(
    run_date: object,
    *,
    snapshots_dir: Path | None = None,
) -> tuple[pd.DataFrame, str | None]:
    run_ts = pd.to_datetime(run_date, errors="coerce")
    if pd.isna(run_ts):
        return pd.DataFrame(), None
    run_ts = run_ts.normalize()

    candidate_dirs: list[Path] = []
    if snapshots_dir is not None:
        candidate_dirs.append(snapshots_dir)
    else:
        candidate_dirs.extend([SNAPSHOTS_DIR, LEGACY_SNAPSHOTS_DIR])

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
        previous_df = _load_snapshot_csv(previous_path)
        if not previous_df.empty:
            return previous_df, previous_date.strftime("%Y-%m-%d")
    return pd.DataFrame(), None


def build_real_bonistas_bundle(df_bonos: pd.DataFrame, *, mep_real: float | None = None) -> dict[str, object]:
    if df_bonos.empty:
        return {}

    tickers = sorted({str(ticker).strip().upper() for ticker in df_bonos["Ticker_IOL"].dropna().tolist() if str(ticker).strip()})
    if not tickers:
        return {}

    try:
        df_bonistas = get_bonds_for_portfolio(tickers)
    except Exception as exc:
        print(f"Bonistas instrumentos no disponible: {exc}")
        logger.warning("Bonistas instrumentos no disponible: %s", exc)
        df_bonistas = pd.DataFrame()
    if not df_bonistas.empty and "bonistas_ticker" in df_bonistas.columns and "Ticker_IOL" not in df_bonistas.columns:
        df_bonistas = df_bonistas.rename(columns={"bonistas_ticker": "Ticker_IOL"})

    try:
        df_bond_volume = get_bond_volume_context(tickers)
    except Exception as exc:
        print(f"PyOBD volumen no disponible: {exc}")
        logger.warning("PyOBD volumen no disponible: %s", exc)
        df_bond_volume = pd.DataFrame()
    if not df_bond_volume.empty:
        if df_bonistas.empty:
            df_bonistas = df_bond_volume.copy()
        else:
            df_bonistas = df_bonistas.merge(df_bond_volume, on="Ticker_IOL", how="left")

    try:
        macro_variables = get_macro_variables()
    except Exception as exc:
        print(f"Bonistas variables no disponible: {exc}")
        logger.warning("Bonistas variables no disponible: %s", exc)
        macro_variables = {}

    try:
        riesgo_pais = get_riesgo_pais_latest(base_url=project_config.ARGENTINADATOS_RIESGO_PAIS_ULTIMO_URL)
    except Exception as exc:
        print(f"ArgentinaDatos riesgo pais no disponible: {exc}")
        logger.warning("ArgentinaDatos riesgo pais no disponible: %s", exc)
        riesgo_pais = None
    if riesgo_pais:
        macro_variables = dict(macro_variables)
        macro_variables["riesgo_pais_bps"] = float(riesgo_pais["valor"])
        macro_variables["riesgo_pais_fecha"] = riesgo_pais.get("fecha")

    try:
        rem_latest = get_rem_latest(
            base_url=project_config.BCRA_REM_URL,
            xlsx_url=project_config.BCRA_REM_XLS_URL,
        )
    except Exception as exc:
        print(f"BCRA REM no disponible: {exc}")
        logger.warning("BCRA REM no disponible: %s", exc)
        rem_latest = None
    if rem_latest:
        macro_variables = dict(macro_variables)
        macro_variables["rem_inflacion_mensual_pct"] = float(rem_latest["inflacion_mensual_pct"])
        if rem_latest.get("inflacion_12m_pct") is not None:
            macro_variables["rem_inflacion_12m_pct"] = float(rem_latest["inflacion_12m_pct"])
        macro_variables["rem_periodo"] = rem_latest.get("periodo")
        macro_variables["rem_fecha_publicacion"] = rem_latest.get("fecha_publicacion")

    try:
        bcra_monetary = get_bcra_monetary_context(
            base_url=project_config.BCRA_MONETARIAS_API_URL,
            reservas_id=project_config.BCRA_RESERVAS_ID,
            a3500_id=project_config.BCRA_A3500_ID,
            badlar_tna_id=project_config.BCRA_BADLAR_PRIV_TNA_ID,
            badlar_tea_id=project_config.BCRA_BADLAR_PRIV_TEA_ID,
        )
    except Exception as exc:
        print(f"BCRA monetarias no disponible: {exc}")
        logger.warning("BCRA monetarias no disponible: %s", exc)
        bcra_monetary = {}
    if bcra_monetary:
        macro_variables = dict(macro_variables)
        macro_variables.update(bcra_monetary)

    try:
        ust_latest = get_ust_latest()
    except Exception as exc:
        print(f"FRED UST no disponible: {exc}")
        logger.warning("FRED UST no disponible: %s", exc)
        ust_latest = None
        macro_variables = dict(macro_variables)
        macro_variables["ust_status"] = "error"
        macro_variables["ust_error"] = str(exc)
    if ust_latest:
        macro_variables = dict(macro_variables)
        macro_variables["ust_status"] = "ok"
        macro_variables.update(ust_latest)

    if df_bonistas.empty and not macro_variables:
        return {}

    bond_analytics = enrich_bond_analytics(
        df_bonos,
        df_bonistas,
        macro_variables=macro_variables,
        mep_real=mep_real,
    )
    return {
        "bond_analytics": bond_analytics,
        "bond_monitor": build_bond_monitor_table(bond_analytics),
        "bond_subfamily_summary": build_bond_subfamily_summary(bond_analytics),
        "bond_local_subfamily_summary": build_bond_local_subfamily_summary(bond_analytics),
        "macro_variables": macro_variables,
    }


def main() -> None:
    configure_logging()
    REPORTS_DIR.mkdir(exist_ok=True)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    run_ts = pd.Timestamp.now(tz=ZoneInfo("America/Argentina/Buenos_Aires"))
    run_date = resolve_market_run_date(run_ts)

    username, password = resolve_iol_credentials()

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
    usar_liquidez_iol = prompt_yes_no("Usar liquidez actual de IOL para fondear la estrategia?", default=False)
    aporte_externo_ars = prompt_money_ars("Cuanto dinero nuevo vas a ingresar en ARS? (enter para 0)")

    mep_data = get_mep_real(casa=project_config.MEP_CASA, base_url=project_config.ARGENTINADATOS_URL)
    mep_real = float(mep_data["promedio"]) if mep_data else None

    tickers = extract_quote_tickers(activos)
    print(f"Descargando precios IOL para {len(tickers)} tickers...")
    precios_iol, token = fetch_prices(tickers, token=token, username=username, password=password)

    portfolio_bundle = build_portfolio_bundle(
        activos=activos,
        estado_payload=estado_payload,
        precios_iol=precios_iol,
        mep_real=mep_real,
        finviz_map=project_config.FINVIZ_MAP,
        block_map=project_config.BLOCK_MAP,
        instrument_profile_map=project_config.INSTRUMENT_PROFILE_MAP,
        vn_factor_map=project_config.VN_FACTOR_MAP,
        ratios=project_config.RATIOS,
        fci_cash_management=project_config.FCI_CASH_MANAGEMENT,
    )
    bonistas_bundle = build_real_bonistas_bundle(portfolio_bundle["df_bonos"], mep_real=mep_real)

    df_total = portfolio_bundle["df_total"]
    df_cedears, df_ratings_res, finviz_stats = enrich_real_cedears(portfolio_bundle["df_cedears"], mep_real=mep_real)
    technical_overlay = build_technical_overlay(df_cedears, scoring_rules=project_config.SCORING_RULES)
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
        "generated_at_timezone": "America/Buenos_Aires",
        "generated_at_source": "Hora local de corrida",
        "portfolio_bundle": portfolio_bundle,
        "dashboard_bundle": dashboard_bundle,
        "decision_bundle": decision_bundle,
        "sizing_bundle": sizing_bundle,
        "technical_overlay": technical_overlay,
        "finviz_stats": finviz_stats,
        "bonistas_bundle": bonistas_bundle,
        "operations_bundle": operations_bundle,
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
