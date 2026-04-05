from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
import re
from typing import Any

import pandas as pd
import requests


DEFAULT_TIMEOUT = 30
BASE_URL = "https://bonistas.com"
INSTRUMENT_TTL_MINUTES = 15
LISTING_TTL_MINUTES = 30
MACRO_TTL_MINUTES = 60

ROOT = Path(__file__).resolve().parents[2]
MAPPING_PATH = ROOT / "data" / "mappings" / "bonistas_ticker_map.json"


@dataclass
class _CacheEntry:
    data: Any
    fetched_at: datetime


_CACHE: dict[str, _CacheEntry] = {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _read_ticker_map() -> dict[str, str]:
    if not MAPPING_PATH.exists():
        return {}
    try:
        return json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def normalize_bonistas_ticker(ticker: str) -> str:
    raw = str(ticker or "").strip().upper()
    if not raw:
        return raw
    mapping = {str(k).upper(): str(v).upper() for k, v in _read_ticker_map().items()}
    return mapping.get(raw, raw)


def _cache_key(kind: str, identifier: str) -> str:
    return f"{kind}:{identifier}"


def _get_cached(key: str, ttl_minutes: int) -> Any | None:
    entry = _CACHE.get(key)
    if entry is None:
        return None
    if _utcnow() - entry.fetched_at > timedelta(minutes=ttl_minutes):
        return None
    return entry.data


def _set_cached(key: str, data: Any) -> Any:
    _CACHE[key] = _CacheEntry(data=data, fetched_at=_utcnow())
    return data


def _fetch_html(path: str, *, timeout: int = DEFAULT_TIMEOUT) -> str:
    response = requests.get(f"{BASE_URL}{path}", timeout=timeout)
    response.raise_for_status()
    return response.text


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"-", "N/A", "nan"}:
        return None
    text = text.replace("%", "").replace("$", "").replace(",", ".")
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _safe_date(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _extract_single(pattern: str, html: str) -> str | None:
    match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _parse_instrument_html(ticker: str, html: str) -> dict[str, Any]:
    normalized = normalize_bonistas_ticker(ticker)
    data: dict[str, Any] = {
        "bonistas_ticker": normalized,
        "bonistas_source_url": f"{BASE_URL}/bono-cotizacion-rendimiento-precio-hoy/{normalized}",
        "bonistas_source_section": "instrument",
        "bonistas_parse_status": "partial",
        "bonistas_fetched_at": _utcnow().isoformat(),
        "bonistas_precio": _safe_float(_extract_single(r"Precio\s*</[^>]+>\s*<[^>]+>([^<]+)", html)),
        "bonistas_variacion_diaria_pct": _safe_float(_extract_single(r"Variaci[oó]n diaria\s*</[^>]+>\s*<[^>]+>([^<]+)", html)),
        "bonistas_tir_pct": _safe_float(_extract_single(r"TIR\s*</[^>]+>\s*<[^>]+>([^<]+)", html)),
        "bonistas_paridad_pct": _safe_float(_extract_single(r"Paridad\s*</[^>]+>\s*<[^>]+>([^<]+)", html)),
        "bonistas_md": _safe_float(_extract_single(r"MD\s*</[^>]+>\s*<[^>]+>([^<]+)", html)),
        "bonistas_fecha_emision": _safe_date(_extract_single(r"Fecha Emisi[oó]n\s*</[^>]+>\s*<[^>]+>([^<]+)", html)),
        "bonistas_fecha_vencimiento": _safe_date(_extract_single(r"Fecha Vencimiento\s*</[^>]+>\s*<[^>]+>([^<]+)", html)),
        "bonistas_valor_tecnico": _safe_float(_extract_single(r"Valor T[eé]cnico\s*</[^>]+>\s*<[^>]+>([^<]+)", html)),
        "bonistas_precio_clean": None,
        "bonistas_precio_dirty": None,
        "bonistas_cupon_corrido": None,
        "bonistas_tir_avg_365d_pct": _safe_float(_extract_single(r"TIR Promedio.*?>([^<]+)", html)),
        "bonistas_tir_min_365d_pct": _safe_float(_extract_single(r"TIR Min.*?>([^<]+)", html)),
        "bonistas_tir_max_365d_pct": _safe_float(_extract_single(r"TIR Max.*?>([^<]+)", html)),
        "bonistas_tir_sens_p1": _safe_float(_extract_single(r"TIR\+1\s*</[^>]+>\s*<[^>]+>([^<]+)", html)),
        "bonistas_tir_sens_m1": _safe_float(_extract_single(r"TIR-1\s*</[^>]+>\s*<[^>]+>([^<]+)", html)),
        "bonistas_put_flag": "opcionalidad de rescate anticipado" in html.lower() or "put" in html.lower(),
        "bonistas_subfamily": None,
    }
    if any(value is not None for key, value in data.items() if key.startswith("bonistas_") and key not in {"bonistas_parse_status", "bonistas_source_url", "bonistas_source_section", "bonistas_fetched_at", "bonistas_ticker"}):
        data["bonistas_parse_status"] = "ok"
    return data


def get_instrument_data(ticker: str, *, timeout: int = DEFAULT_TIMEOUT, use_cache: bool = True) -> dict[str, Any]:
    normalized = normalize_bonistas_ticker(ticker)
    key = _cache_key("instrument", normalized)
    if use_cache:
        cached = _get_cached(key, INSTRUMENT_TTL_MINUTES)
        if cached is not None:
            return cached

    try:
        html = _fetch_html(f"/bono-cotizacion-rendimiento-precio-hoy/{normalized}", timeout=timeout)
        payload = _parse_instrument_html(normalized, html)
    except Exception:
        payload = {
            "bonistas_ticker": normalized,
            "bonistas_source_url": f"{BASE_URL}/bono-cotizacion-rendimiento-precio-hoy/{normalized}",
            "bonistas_source_section": "instrument",
            "bonistas_parse_status": "error",
            "bonistas_fetched_at": _utcnow().isoformat(),
        }
    return _set_cached(key, payload)


def _listing_path(family: str) -> str:
    mapping = {
        "cer": "/bonos-cer-hoy",
        "bopreal": "/bonos-bopreal-hoy",
        "hard_dollar": "/",
        "variables": "/variables",
    }
    if family not in mapping:
        raise ValueError(f"Unsupported Bonistas listing family: {family}")
    return mapping[family]


def get_listing(family: str, *, timeout: int = DEFAULT_TIMEOUT, use_cache: bool = True) -> pd.DataFrame:
    key = _cache_key("listing", family)
    if use_cache:
        cached = _get_cached(key, LISTING_TTL_MINUTES)
        if cached is not None:
            return cached.copy()

    html = _fetch_html(_listing_path(family), timeout=timeout)
    tables = pd.read_html(StringIO(html))
    listing = tables[0].copy() if tables else pd.DataFrame()
    if not listing.empty:
        listing.columns = [str(col).strip() for col in listing.columns]
        listing["bonistas_source_section"] = family
    _set_cached(key, listing.copy())
    return listing


def get_macro_variables(*, timeout: int = DEFAULT_TIMEOUT, use_cache: bool = True) -> dict[str, Any]:
    key = _cache_key("macro", "variables")
    if use_cache:
        cached = _get_cached(key, MACRO_TTL_MINUTES)
        if cached is not None:
            return dict(cached)

    try:
        html = _fetch_html("/variables", timeout=timeout)
    except Exception:
        payload = {
            "bonistas_parse_status": "error",
            "bonistas_source_url": f"{BASE_URL}/variables",
            "bonistas_fetched_at": _utcnow().isoformat(),
        }
        return _set_cached(key, payload)

    payload = {
        "bonistas_parse_status": "partial",
        "bonistas_source_url": f"{BASE_URL}/variables",
        "bonistas_fetched_at": _utcnow().isoformat(),
        "cer_diario": _safe_float(_extract_single(r"CER.*?>([^<]+)", html)),
        "tamar": _safe_float(_extract_single(r"TAMAR.*?>([^<]+)", html)),
        "badlar": _safe_float(_extract_single(r"BADLAR.*?>([^<]+)", html)),
        "inflacion_mensual": _safe_float(_extract_single(r"Inflaci[oó]n mensual.*?>([^<]+)", html)),
        "inflacion_interanual": _safe_float(_extract_single(r"Inflaci[oó]n interanual.*?>([^<]+)", html)),
        "rem_esperada": _safe_float(_extract_single(r"REM.*?>([^<]+)", html)),
    }
    if any(value is not None for key_name, value in payload.items() if key_name not in {"bonistas_parse_status", "bonistas_source_url", "bonistas_fetched_at"}):
        payload["bonistas_parse_status"] = "ok"
    return _set_cached(key, payload)


def get_bonds_for_portfolio(
    tickers: list[str],
    *,
    timeout: int = DEFAULT_TIMEOUT,
    use_cache: bool = True,
) -> pd.DataFrame:
    rows = [get_instrument_data(ticker, timeout=timeout, use_cache=use_cache) for ticker in tickers]
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    ordered_cols = [
        "bonistas_ticker",
        "bonistas_source_url",
        "bonistas_source_section",
        "bonistas_parse_status",
        "bonistas_precio",
        "bonistas_variacion_diaria_pct",
        "bonistas_tir_pct",
        "bonistas_paridad_pct",
        "bonistas_md",
        "bonistas_fecha_emision",
        "bonistas_fecha_vencimiento",
        "bonistas_valor_tecnico",
        "bonistas_precio_clean",
        "bonistas_precio_dirty",
        "bonistas_cupon_corrido",
        "bonistas_tir_avg_365d_pct",
        "bonistas_tir_min_365d_pct",
        "bonistas_tir_max_365d_pct",
        "bonistas_tir_sens_p1",
        "bonistas_tir_sens_m1",
        "bonistas_put_flag",
        "bonistas_subfamily",
        "bonistas_fetched_at",
    ]
    for col in ordered_cols:
        if col not in df.columns:
            df[col] = None
    remaining_cols = [col for col in df.columns if col not in ordered_cols]
    return df[ordered_cols + remaining_cols]
