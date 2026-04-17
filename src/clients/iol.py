from __future__ import annotations

from typing import Any

import requests


DEFAULT_TIMEOUT = 30


def iol_login(
    username: str,
    password: str,
    *,
    base_url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    resp = requests.post(
        f"{base_url}/token",
        data={
            "username": username,
            "password": password,
            "grant_type": "password",
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def iol_get_quote(
    symbol: str,
    token: str,
    *,
    base_url: str,
    market: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    resp = requests.get(
        f"{base_url}/api/v2/{market}/Titulos/{symbol}/CotizacionDetalle",
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def iol_get_quote_with_reauth(
    symbol: str,
    token: str,
    *,
    username: str | None,
    password: str | None,
    base_url: str,
    market: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any], str]:
    url = f"{base_url}/api/v2/{market}/Titulos/{symbol}/CotizacionDetalle"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )

    if resp.status_code == 401 and username and password:
        new_token = iol_login(username, password, base_url=base_url, timeout=timeout)
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {new_token}"},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json(), new_token

    resp.raise_for_status()
    return resp.json(), token


def iol_get_portafolio(
    token: str,
    *,
    base_url: str,
    pais: str = "argentina",
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    resp = requests.get(
        f"{base_url}/api/v2/portafolio/{pais}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def iol_get_estado_cuenta(
    token: str,
    *,
    base_url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    resp = requests.get(
        f"{base_url}/api/v2/estadocuenta",
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def iol_get_operaciones(
    token: str,
    *,
    base_url: str,
    estado: str = "todas",
    pais: str = "argentina",
    numero: int | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "filtro.estado": estado,
        "filtro.pais": pais,
    }
    if numero is not None:
        params["filtro.numero"] = numero
    if fecha_desde:
        params["filtro.fechaDesde"] = fecha_desde
    if fecha_hasta:
        params["filtro.fechaHasta"] = fecha_hasta

    resp = requests.get(
        f"{base_url}/api/v2/operaciones",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()
