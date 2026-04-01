from __future__ import annotations

from typing import Any

import requests


DEFAULT_TIMEOUT = 10


def get_dollar_series(
    *,
    casa: str,
    base_url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    resp = requests.get(base_url.format(casa=casa), timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
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
