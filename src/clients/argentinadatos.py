from __future__ import annotations

from typing import Any

import requests


DEFAULT_TIMEOUT = 10


def _get_json_payload(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def get_dollar_series(
    *,
    casa: str,
    base_url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    payload = _get_json_payload(base_url.format(casa=casa), timeout=timeout)
    if not isinstance(payload, list):
        raise ValueError("ArgentinaDatos devolvió un payload no esperado.")
    return payload


def get_mep_real(
    *,
    casa: str,
    base_url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any] | None:
    payload = get_dollar_series(casa=casa, base_url=base_url, timeout=timeout)
    if not payload:
        return None

    ultimo = payload[-1]
    compra = float(ultimo["compra"])
    venta = float(ultimo["venta"])
    return {
        "compra": compra,
        "venta": venta,
        "promedio": (compra + venta) / 2,
        "fecha": ultimo.get("fecha"),
        "raw": ultimo,
    }


def get_riesgo_pais_latest(
    *,
    base_url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any] | None:
    payload = _get_json_payload(base_url, timeout=timeout)
    if not isinstance(payload, dict):
        raise ValueError("ArgentinaDatos devolvió un payload no esperado para riesgo pais.")

    valor = payload.get("valor")
    if valor is None:
        return None

    return {
        "valor": float(valor),
        "fecha": payload.get("fecha"),
        "raw": payload,
    }
