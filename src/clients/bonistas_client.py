from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import html
from io import StringIO
import json
import logging
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
MAX_CACHE_ENTRIES = 128
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
MAPPING_PATH = ROOT / "data" / "mappings" / "bonistas_ticker_map.json"


@dataclass
class _CacheEntry:
    data: Any
    fetched_at: datetime


_CACHE: OrderedDict[str, _CacheEntry] = OrderedDict()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _read_ticker_map() -> dict[str, str]:
    if not MAPPING_PATH.exists():
        return {}
    try:
        return json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("No se pudo leer bonistas_ticker_map.json: %s", exc)
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
        _CACHE.pop(key, None)
        return None
    _CACHE.move_to_end(key)
    return entry.data


def _set_cached(key: str, data: Any) -> Any:
    if key in _CACHE:
        _CACHE.pop(key, None)
    _CACHE[key] = _CacheEntry(data=data, fetched_at=_utcnow())
    while len(_CACHE) > MAX_CACHE_ENTRIES:
        _CACHE.popitem(last=False)
    return data


def clear_cache() -> None:
    _CACHE.clear()


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


def _safe_macro_rate(value: Any, *, min_value: float = 5.0, max_value: float = 200.0) -> float | None:
    number = _safe_float(value)
    if number is None:
        return None
    if number < min_value or number > max_value:
        return None
    return number


def _infer_bonistas_subfamily(ticker: str) -> str | None:
    normalized = normalize_bonistas_ticker(ticker)
    if normalized.startswith("BPO"):
        return "bond_bopreal"
    if normalized.startswith(("TZX", "TX", "TC")):
        return "bond_cer"
    if normalized.startswith(("AL", "GD", "AE")):
        return "bond_hard_dollar"
    if normalized.startswith(("TTM", "TDF")):
        return "bond_dual"
    if normalized.startswith(("TV", "D")):
        return "bond_dollar_linked"
    if normalized.startswith(("TM", "S")):
        return "bond_fixed_rate"
    return None


def _extract_single(pattern: str, raw_html: str) -> str | None:
    match = re.search(pattern, raw_html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _normalize_label_text(value: str) -> str:
    text = str(value or "")
    replacements = {
        "Ã³": "ó",
        "Ã©": "é",
        "Ã­": "í",
        "Ã¡": "á",
        "Ãº": "ú",
        "VariaciÃ³n": "Variación",
        "EmisiÃ³n": "Emisión",
        "TÃ©cnico": "Técnico",
        "InflaciÃ³n": "Inflación",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = html.unescape(text)
    text = text.strip().lower()
    text = text.replace("ó", "o").replace("é", "e").replace("í", "i").replace("á", "a").replace("ú", "u")
    text = re.sub(r"\s+", " ", text)
    return text


def _html_text_lines(raw_html: str) -> list[str]:
    text = re.sub(r"<[^>]+>", "\n", raw_html)
    text = html.unescape(text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return [line for line in lines if line]


def _extract_value_after_label(raw_html: str, label: str, *, max_lookahead: int = 6) -> str | None:
    lines = _html_text_lines(raw_html)
    target = _normalize_label_text(label)
    for idx, line in enumerate(lines):
        if _normalize_label_text(line) != target:
            continue
        for candidate in lines[idx + 1 : idx + 1 + max_lookahead]:
            if _safe_float(candidate) is not None or re.search(r"\d+/\d+/\d+|\d{4}-\d{2}-\d{2}", candidate):
                return candidate.strip()
    return None


def _parse_instrument_html(ticker: str, raw_html: str) -> dict[str, Any]:
    normalized = normalize_bonistas_ticker(ticker)
    put_flag = "opcionalidad de rescate" in raw_html.lower() or "put" in raw_html.lower()
    data: dict[str, Any] = {
        "bonistas_ticker": normalized,
        "bonistas_source_url": f"{BASE_URL}/bono-cotizacion-rendimiento-precio-hoy/{normalized}",
        "bonistas_source_section": "instrument",
        "bonistas_parse_status": "partial",
        "bonistas_fetched_at": _utcnow().isoformat(),
        "bonistas_precio": _safe_float(_extract_value_after_label(raw_html, "Precio")),
        "bonistas_variacion_diaria_pct": _safe_float(_extract_value_after_label(raw_html, "Variación diaria")),
        "bonistas_tir_pct": _safe_float(_extract_value_after_label(raw_html, "TIR")),
        "bonistas_paridad_pct": _safe_float(_extract_value_after_label(raw_html, "Paridad")),
        "bonistas_md": _safe_float(_extract_value_after_label(raw_html, "MD")),
        "bonistas_fecha_emision": _safe_date(_extract_value_after_label(raw_html, "Fecha Emisión")),
        "bonistas_fecha_vencimiento": _safe_date(_extract_value_after_label(raw_html, "Fecha Vencimiento")),
        "bonistas_valor_tecnico": _safe_float(_extract_value_after_label(raw_html, "Valor Técnico")),
        "bonistas_precio_clean": None,
        "bonistas_precio_dirty": None,
        "bonistas_cupon_corrido": None,
        "bonistas_tir_avg_365d_pct": _safe_float(_extract_value_after_label(raw_html, "TIR Promedio (en 365 días)")),
        "bonistas_tir_min_365d_pct": _safe_float(_extract_value_after_label(raw_html, "TIR Min (en 365 días)")),
        "bonistas_tir_max_365d_pct": _safe_float(_extract_value_after_label(raw_html, "TIR Max (en 365 días)")),
        "bonistas_tir_sens_p1": _safe_float(_extract_value_after_label(raw_html, "TIR+1")),
        "bonistas_tir_sens_m1": _safe_float(_extract_value_after_label(raw_html, "TIR-1")),
        "bonistas_put_flag": put_flag,
        "bonistas_subfamily": _infer_bonistas_subfamily(normalized),
    }
    informative_keys = {
        "bonistas_parse_status",
        "bonistas_source_url",
        "bonistas_source_section",
        "bonistas_fetched_at",
        "bonistas_ticker",
    }
    if any(value is not None for key, value in data.items() if key.startswith("bonistas_") and key not in informative_keys):
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
        raw_html = _fetch_html(f"/bono-cotizacion-rendimiento-precio-hoy/{normalized}", timeout=timeout)
        payload = _parse_instrument_html(normalized, raw_html)
    except Exception as exc:
        logger.warning("Bonistas instrument fetch failed for %s: %s", normalized, exc)
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

    raw_html = _fetch_html(_listing_path(family), timeout=timeout)
    tables = pd.read_html(StringIO(raw_html))
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
        raw_html = _fetch_html("/variables", timeout=timeout)
    except Exception as exc:
        logger.warning("Bonistas macro fetch failed: %s", exc)
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
        "cer_diario": _safe_float(_extract_value_after_label(raw_html, "CER")),
        "tamar": _safe_macro_rate(_extract_value_after_label(raw_html, "TAMAR")),
        "badlar": _safe_macro_rate(_extract_value_after_label(raw_html, "BADLAR")),
        "inflacion_mensual": _safe_macro_rate(_extract_value_after_label(raw_html, "Inflacion Mensual"), min_value=-50.0, max_value=100.0),
        "inflacion_interanual": _safe_macro_rate(_extract_value_after_label(raw_html, "Inflacion Interanual"), min_value=-50.0, max_value=500.0),
        "rem_esperada": _safe_macro_rate(_extract_value_after_label(raw_html, "Inflacion Esperada (REM)"), min_value=-50.0, max_value=500.0),
    }
    informative_keys = {"bonistas_parse_status", "bonistas_source_url", "bonistas_fetched_at"}
    if any(value is not None for key_name, value in payload.items() if key_name not in informative_keys):
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
