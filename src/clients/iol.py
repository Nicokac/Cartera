from __future__ import annotations

import logging
import time
from typing import Any

import requests
from clients.protocols import HttpRequestProtocol, HttpResponseProtocol


DEFAULT_TIMEOUT = 30
IOL_MAX_ATTEMPTS = 3
IOL_BACKOFF_SECONDS = 0.25
_RETRY_STATUS_CODES = {408, 429, 500, 502, 503, 504}
logger = logging.getLogger(__name__)


def _request_with_retry(
    method: str,
    url: str,
    *,
    timeout: int,
    requester: HttpRequestProtocol | None = None,
    raise_for_status: bool = True,
    **kwargs: Any,
) -> HttpResponseProtocol:
    request_impl = requester or requests.request
    last_exc: Exception | None = None
    for attempt in range(1, IOL_MAX_ATTEMPTS + 1):
        try:
            response = request_impl(method, url, timeout=timeout, **kwargs)
            if raise_for_status:
                response.raise_for_status()
            elif response.status_code in _RETRY_STATUS_CODES:
                raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
            return response
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_exc = exc
            logger.warning("IOL call failed on attempt %s/%s: %s", attempt, IOL_MAX_ATTEMPTS, exc)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status not in _RETRY_STATUS_CODES:
                raise
            last_exc = exc
            logger.warning("IOL call failed on attempt %s/%s with HTTP %s", attempt, IOL_MAX_ATTEMPTS, status)
        if attempt < IOL_MAX_ATTEMPTS:
            time.sleep(IOL_BACKOFF_SECONDS * attempt)
    raise last_exc or RuntimeError("IOL request failed")


def iol_login(
    username: str,
    password: str,
    *,
    base_url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    resp = _request_with_retry(
        "post",
        f"{base_url}/token",
        data={"username": username, "password": password, "grant_type": "password"},
        timeout=timeout,
    )
    return resp.json()["access_token"]


def iol_get_quote(
    symbol: str,
    token: str,
    *,
    base_url: str,
    market: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    resp = _request_with_retry(
        "get",
        f"{base_url}/api/v2/{market}/Titulos/{symbol}/CotizacionDetalle",
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
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
    resp = _request_with_retry(
        "get",
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
        raise_for_status=False,
    )

    if resp.status_code == 401 and username and password:
        new_token = iol_login(username, password, base_url=base_url, timeout=timeout)
        resp = _request_with_retry(
            "get",
            url,
            headers={"Authorization": f"Bearer {new_token}"},
            timeout=timeout,
        )
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
    resp = _request_with_retry(
        "get",
        f"{base_url}/api/v2/portafolio/{pais}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    return resp.json()


def iol_get_estado_cuenta(
    token: str,
    *,
    base_url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    resp = _request_with_retry(
        "get",
        f"{base_url}/api/v2/estadocuenta",
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
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

    resp = _request_with_retry(
        "get",
        f"{base_url}/api/v2/operaciones",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=timeout,
    )
    return resp.json()
