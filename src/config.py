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
BCRA_A3500_ID = 55
BCRA_BADLAR_PRIV_TNA_ID = 77
BCRA_BADLAR_PRIV_TEA_ID = 3535
MEP_CASA = "bolsa"

ALERTA_MEP_DESVIO_PCT = 5
ALERTA_PERDIDA_MINIMA = -10000

FCI_CASH_MANAGEMENT = {"ADBAICA", "IOLPORA", "PRPEDOB"}


def _load_json_mapping(filename: str) -> dict[str, Any]:
    path = MAPPINGS_DIR / filename
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"El mapping {path} debe ser un objeto JSON.")
    return data


def _load_strategy_rules(filename: str) -> dict[str, Any]:
    path = STRATEGY_DIR / filename
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"La estrategia {path} debe ser un objeto JSON.")
    return data


FINVIZ_MAP = _load_json_mapping("finviz_map.json")
BLOCK_MAP = _load_json_mapping("block_map.json")
INSTRUMENT_PROFILE_MAP = _load_json_mapping("instrument_profile_map.json")
RATIOS = _load_json_mapping("ratios.json")
VN_FACTOR_MAP = _load_json_mapping("vn_factor_map.json")

SCORING_RULES = _load_strategy_rules("scoring_rules.json")
ACTION_RULES = _load_strategy_rules("action_rules.json")
SIZING_RULES = _load_strategy_rules("sizing_rules.json")
BUCKET_WEIGHTS = dict(SIZING_RULES.get("bucket_weights", {}))


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
        "ALERTA_MEP_DESVIO_PCT": ALERTA_MEP_DESVIO_PCT,
        "ALERTA_PERDIDA_MINIMA": ALERTA_PERDIDA_MINIMA,
        "FCI_CASH_MANAGEMENT": set(FCI_CASH_MANAGEMENT),
        "BUCKET_WEIGHTS": dict(BUCKET_WEIGHTS),
        "SCORING_RULES": dict(SCORING_RULES),
        "ACTION_RULES": dict(ACTION_RULES),
        "SIZING_RULES": dict(SIZING_RULES),
    }


def load_portfolio_mappings() -> dict[str, dict[str, Any]]:
    return {
        "FINVIZ_MAP": dict(FINVIZ_MAP),
        "BLOCK_MAP": dict(BLOCK_MAP),
        "INSTRUMENT_PROFILE_MAP": dict(INSTRUMENT_PROFILE_MAP),
        "RATIOS": dict(RATIOS),
        "VN_FACTOR_MAP": dict(VN_FACTOR_MAP),
    }
