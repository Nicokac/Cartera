from __future__ import annotations

import logging
import json
from datetime import date
from pathlib import Path
import shutil
from collections.abc import Callable
from concurrent.futures import wait
from typing import Any

import numpy as np
import pandas as pd
import requests

IOL_PRICE_CACHE_TTL_MINUTES = 15


def backup_runtime_csvs_impl(
    *,
    runtime_dir: Path,
    backups_root: Path,
    run_date: date | None = None,
) -> list[Path]:
    effective_date = run_date or date.today()
    target_dir = backups_root / effective_date.strftime("%Y-%m-%d")
    target_dir.mkdir(parents=True, exist_ok=True)

    backed_up: list[Path] = []
    if not runtime_dir.exists():
        return backed_up

    for csv_path in sorted(runtime_dir.glob("*.csv")):
        target_path = target_dir / csv_path.name
        shutil.copy2(csv_path, target_path)
        backed_up.append(target_path)
    return backed_up


def parse_finviz_number_impl(value: object, *, logger: logging.Logger) -> float:
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


def parse_finviz_pct_impl(value: object, *, logger: logging.Logger) -> float:
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


def extract_quote_tickers_impl(activos: list[dict]) -> list[str]:
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


def extract_operation_quote_tickers_impl(
    operations: list[dict[str, object]] | None,
    *,
    limit: int = 20,
) -> list[str]:
    if not operations:
        return []

    tickers: list[str] = []
    for operation in operations:
        tipo = str(operation.get("tipo") or "").strip()
        estado = str(operation.get("estado") or "").strip().lower()
        simbolo = str(operation.get("simbolo") or "").strip().upper()
        if tipo not in {"Compra", "Venta"} or estado != "terminada" or not simbolo:
            continue
        if simbolo not in tickers:
            tickers.append(simbolo)
        if len(tickers) >= limit:
            break
    return tickers


def fetch_prices_impl(
    tickers: list[str],
    *,
    token: str,
    username: str,
    password: str,
    iol_get_quote_with_reauth_fn: Callable[..., tuple[dict[str, object], str]],
    base_url: str,
    market: str,
    logger: logging.Logger,
    print_fn: Callable[[str], None],
    cache_path: Path | None = None,
    cache_ttl_minutes: int = IOL_PRICE_CACHE_TTL_MINUTES,
    now_ts: pd.Timestamp | None = None,
) -> tuple[dict[str, float], str]:
    prices: dict[str, float] = {}
    current_token = token
    now_value = now_ts or pd.Timestamp.now(tz="UTC")
    ttl_minutes = int(cache_ttl_minutes)
    cache_payload: dict[str, Any] = {"updated_at": now_value.isoformat(), "prices": {}}
    if cache_path is not None and cache_path.exists():
        try:
            cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache_payload = {"updated_at": now_value.isoformat(), "prices": {}}
    cached_prices = cache_payload.get("prices", {}) if isinstance(cache_payload, dict) else {}
    if not isinstance(cached_prices, dict):
        cached_prices = {}

    updated_at_raw = cache_payload.get("updated_at") if isinstance(cache_payload, dict) else None
    cache_fresh = False
    if isinstance(updated_at_raw, str):
        updated_at = pd.to_datetime(updated_at_raw, errors="coerce", utc=True)
        if pd.notna(updated_at):
            age_minutes = (now_value - updated_at).total_seconds() / 60.0
            cache_fresh = age_minutes <= ttl_minutes

    for ticker in tickers:
        if cache_fresh and ticker in cached_prices:
            try:
                prices[ticker] = float(cached_prices[ticker])
                continue
            except Exception:
                pass
        try:
            data, current_token = iol_get_quote_with_reauth_fn(
                ticker,
                current_token,
                username=username,
                password=password,
                base_url=base_url,
                market=market,
            )
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 404:
                print_fn(f"  [skip] Sin cotizacion IOL para {ticker} (404)")
                logger.info("Sin cotizacion IOL para %s (404)", ticker)
                continue
            raise

        price = data.get("ultimoPrecio")
        if price is not None:
            prices[ticker] = float(price)
        else:
            print_fn(f"  [skip] ultimoPrecio ausente para {ticker}")
            logger.info("ultimoPrecio ausente para %s", ticker)

    if cache_path is not None:
        merged_prices = dict(cached_prices)
        merged_prices.update(prices)
        cache_out = {"updated_at": now_value.isoformat(), "prices": merged_prices}
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache_out, ensure_ascii=True, sort_keys=True), encoding="utf-8")

    return prices, current_token


def fetch_iol_payloads_impl(
    *,
    token: str,
    username: str,
    password: str,
    iol_get_portafolio_fn: Callable[..., dict[str, object]],
    iol_get_estado_cuenta_fn: Callable[..., dict[str, object]],
    iol_get_operaciones_fn: Callable[..., list[dict[str, object]]],
    iol_login_fn: Callable[..., str],
    base_url: str,
    logger: logging.Logger,
) -> tuple[dict[str, object], dict[str, object], list[dict[str, object]], str]:
    current_token = token
    try:
        portfolio_payload = iol_get_portafolio_fn(current_token, base_url=base_url, pais="argentina")
        estado_payload = iol_get_estado_cuenta_fn(current_token, base_url=base_url)
        operaciones_payload = iol_get_operaciones_fn(
            current_token,
            base_url=base_url,
            pais="argentina",
            estado="todas",
        )
        return portfolio_payload, estado_payload, operaciones_payload, current_token
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status != 401:
            raise
        logger.info("IOL token expirado durante descarga inicial. Reautenticando y reintentando.")
        current_token = iol_login_fn(username, password, base_url=base_url)
        portfolio_payload = iol_get_portafolio_fn(current_token, base_url=base_url, pais="argentina")
        estado_payload = iol_get_estado_cuenta_fn(current_token, base_url=base_url)
        operaciones_payload = iol_get_operaciones_fn(
            current_token,
            base_url=base_url,
            pais="argentina",
            estado="todas",
        )
        return portfolio_payload, estado_payload, operaciones_payload, current_token


def _enrich_cedear_row_payload_impl(
    idx: object,
    *,
    row_data: dict[str, object],
    mep_real: float | None,
    fetch_finviz_bundle_fn: Callable[[str], dict[str, object]],
    parse_finviz_pct_fn: Callable[[object], float],
    parse_finviz_number_fn: Callable[[object], float],
    logger: logging.Logger,
) -> tuple[object, dict[str, object], dict[str, object] | None, str | None]:
    ticker_finviz = row_data.get("Ticker_Finviz")
    if not ticker_finviz:
        return idx, {}, None, None

    try:
        bundle = fetch_finviz_bundle_fn(str(ticker_finviz))
    except Exception as exc:
        logger.warning("Finviz enrichment failed for %s: %s", ticker_finviz, exc)
        return idx, {}, None, f"{ticker_finviz}: {exc}"

    updates: dict[str, object] = {}
    fundamentals = bundle.get("fundamentals", {}) or {}
    updates["Perf Week"] = parse_finviz_pct_fn(fundamentals.get("Perf Week", row_data.get("Perf Week")))
    updates["Perf Month"] = parse_finviz_pct_fn(fundamentals.get("Perf Month", row_data.get("Perf Month")))
    updates["Perf YTD"] = parse_finviz_pct_fn(fundamentals.get("Perf YTD", row_data.get("Perf YTD")))
    updates["Beta"] = parse_finviz_number_fn(fundamentals.get("Beta", row_data.get("Beta")))
    updates["P/E"] = parse_finviz_number_fn(fundamentals.get("P/E", row_data.get("P/E")))
    updates["ROE"] = parse_finviz_pct_fn(fundamentals.get("ROE", row_data.get("ROE")))
    updates["Profit Margin"] = parse_finviz_pct_fn(fundamentals.get("Profit Margin", row_data.get("Profit Margin")))

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


def enrich_real_cedears_impl(
    df_cedears: pd.DataFrame,
    *,
    mep_real: float | None,
    fetch_finviz_bundle_fn: Callable[[str], dict[str, object]],
    finviz_max_workers: int,
    finviz_worker_timeout_seconds: float,
    finviz_submit_delay_seconds: float,
    thread_pool_executor_cls: type,
    wait_fn: Callable[[Any, float], tuple[set[Any], set[Any]]] = wait,
    sleep_fn: Callable[[float], None] | None = None,
    logger: logging.Logger,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    if sleep_fn is None:
        from time import sleep as sleep_fn_default

        sleep_fn = sleep_fn_default

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
        max_workers = min(finviz_max_workers, len(tasks))
        timeout_seconds = float(finviz_worker_timeout_seconds)
        submit_delay_seconds = max(float(finviz_submit_delay_seconds), 0.0)
        executor = thread_pool_executor_cls(max_workers=max_workers, thread_name_prefix="finviz")
        future_map = {}
        for task_index, (idx, row_data) in enumerate(tasks):
            future = executor.submit(
                _enrich_cedear_row_payload_impl,
                idx,
                row_data=row_data,
                mep_real=mep_real,
                fetch_finviz_bundle_fn=fetch_finviz_bundle_fn,
                parse_finviz_pct_fn=lambda value: parse_finviz_pct_impl(value, logger=logger),
                parse_finviz_number_fn=lambda value: parse_finviz_number_impl(value, logger=logger),
                logger=logger,
            )
            future_map[future] = (idx, row_data)
            if submit_delay_seconds > 0 and task_index < len(tasks) - 1:
                sleep_fn(submit_delay_seconds)
        done, not_done = wait_fn(future_map.keys(), timeout=timeout_seconds)
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
