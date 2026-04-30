from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class HttpResponseProtocol(Protocol):
    status_code: int
    text: str
    content: bytes

    def json(self) -> Any:
        ...

    def raise_for_status(self) -> None:
        ...


class HttpGetProtocol(Protocol):
    def __call__(self, url: str, *, timeout: int) -> HttpResponseProtocol:
        ...


class HttpRequestProtocol(Protocol):
    def __call__(
        self,
        method: str,
        url: str,
        *,
        timeout: int,
        data: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> HttpResponseProtocol:
        ...

