from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
MAPPINGS_DIR = ROOT_DIR / "data" / "mappings"
STRATEGY_DIR = ROOT_DIR / "data" / "strategy"

IOL_BASE_URL = "https://api.invertironline.com"
MARKET = "BCBA"

ARGENTINADATOS_URL = "https://api.argentinadatos.com/v1/cotizaciones/dolares/{casa}"
ARGENTINADATOS_RIESGO_PAIS_URL = "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais"
ARGENTINADATOS_RIESGO_PAIS_ULTIMO_URL = "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo"
BCRA_REM_URL = "https://www.bcra.gob.ar/relevamiento-expectativas-mercado-rem/"
BCRA_REM_XLS_URL = "https://www.bcra.gob.ar/archivos/Pdfs/Estadisticas/Base%20de%20Resultados%20del%20REM%20web.xlsx"
BCRA_MONETARIAS_API_URL = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias"
BCRA_RESERVAS_ID = 1
BCRA_A3500_ID = 5
BCRA_BADLAR_PRIV_TNA_ID = 7
BCRA_BADLAR_PRIV_TEA_ID = 35
MEP_CASA = "bolsa"

FCI_CASH_MANAGEMENT = {"ADBAICA", "PRPEDOB"}
FINVIZ_MAX_WORKERS = 2
FINVIZ_WORKER_TIMEOUT_SECONDS = 30
FINVIZ_SUBMIT_DELAY_SECONDS = 0.75

_MAPPING_FILES = {
    "FINVIZ_MAP": "finviz_map.json",
    "BLOCK_MAP": "block_map.json",
    "ARGENTINA_EQUITY_MAP": "argentina_equity_map.json",
    "INSTRUMENT_PROFILE_MAP": "instrument_profile_map.json",
    "BOND_LOCAL_SUBFAMILY_RULES": "bond_local_subfamily_rules.json",
    "RATIOS": "ratios.json",
    "VN_FACTOR_MAP": "vn_factor_map.json",
    "PREDICTION_WEIGHTS": "prediction_weights.json",
}

_STRATEGY_FILES = {
    "SCORING_RULES": "scoring_rules.json",
    "ACTION_RULES": "action_rules.json",
    "SIZING_RULES": "sizing_rules.json",
}

_CONFIG_CACHE: dict[str, Any] = {}


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{label} {path} debe ser un objeto JSON.")
    return data


def _load_json_mapping(filename: str) -> dict[str, Any]:
    return _load_json_object(MAPPINGS_DIR / filename, label="El mapping")


def _load_strategy_rules(filename: str) -> dict[str, Any]:
    return _load_json_object(STRATEGY_DIR / filename, label="La estrategia")


def _load_cached_config(name: str) -> Any:
    if name in _CONFIG_CACHE:
        return _CONFIG_CACHE[name]

    if name in _MAPPING_FILES:
        value = _load_json_mapping(_MAPPING_FILES[name])
    elif name in _STRATEGY_FILES:
        value = _load_strategy_rules(_STRATEGY_FILES[name])
    elif name == "BUCKET_WEIGHTS":
        value = dict(getattr(__import__(__name__), "SIZING_RULES").get("bucket_weights", {}))
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    _CONFIG_CACHE[name] = value
    return value


def __getattr__(name: str) -> Any:
    return _load_cached_config(name)


def __dir__() -> list[str]:
    return sorted(
        list(globals().keys()) + list(_MAPPING_FILES.keys()) + list(_STRATEGY_FILES.keys()) + ["BUCKET_WEIGHTS"]
    )


def clear_config_cache() -> None:
    _CONFIG_CACHE.clear()


def load_runtime_config() -> dict[str, Any]:
    return {
        "IOL_BASE_URL": IOL_BASE_URL,
        "MARKET": MARKET,
        "ARGENTINADATOS_URL": ARGENTINADATOS_URL,
        "ARGENTINADATOS_RIESGO_PAIS_URL": ARGENTINADATOS_RIESGO_PAIS_URL,
        "ARGENTINADATOS_RIESGO_PAIS_ULTIMO_URL": ARGENTINADATOS_RIESGO_PAIS_ULTIMO_URL,
        "BCRA_REM_URL": BCRA_REM_URL,
        "BCRA_REM_XLS_URL": BCRA_REM_XLS_URL,
        "BCRA_MONETARIAS_API_URL": BCRA_MONETARIAS_API_URL,
        "BCRA_RESERVAS_ID": BCRA_RESERVAS_ID,
        "BCRA_A3500_ID": BCRA_A3500_ID,
        "BCRA_BADLAR_PRIV_TNA_ID": BCRA_BADLAR_PRIV_TNA_ID,
        "BCRA_BADLAR_PRIV_TEA_ID": BCRA_BADLAR_PRIV_TEA_ID,
        "MEP_CASA": MEP_CASA,
        "FCI_CASH_MANAGEMENT": set(FCI_CASH_MANAGEMENT),
        "FINVIZ_MAX_WORKERS": FINVIZ_MAX_WORKERS,
        "FINVIZ_WORKER_TIMEOUT_SECONDS": FINVIZ_WORKER_TIMEOUT_SECONDS,
        "FINVIZ_SUBMIT_DELAY_SECONDS": FINVIZ_SUBMIT_DELAY_SECONDS,
        "BUCKET_WEIGHTS": dict(_load_cached_config("BUCKET_WEIGHTS")),
        "SCORING_RULES": dict(_load_cached_config("SCORING_RULES")),
        "ACTION_RULES": dict(_load_cached_config("ACTION_RULES")),
        "SIZING_RULES": dict(_load_cached_config("SIZING_RULES")),
    }


def load_portfolio_mappings() -> dict[str, dict[str, Any]]:
    return {
        "FINVIZ_MAP": dict(_load_cached_config("FINVIZ_MAP")),
        "BLOCK_MAP": dict(_load_cached_config("BLOCK_MAP")),
        "ARGENTINA_EQUITY_MAP": dict(_load_cached_config("ARGENTINA_EQUITY_MAP")),
        "INSTRUMENT_PROFILE_MAP": dict(_load_cached_config("INSTRUMENT_PROFILE_MAP")),
        "BOND_LOCAL_SUBFAMILY_RULES": dict(_load_cached_config("BOND_LOCAL_SUBFAMILY_RULES")),
        "RATIOS": dict(_load_cached_config("RATIOS")),
        "VN_FACTOR_MAP": dict(_load_cached_config("VN_FACTOR_MAP")),
        "PREDICTION_WEIGHTS": dict(_load_cached_config("PREDICTION_WEIGHTS")),
    }
