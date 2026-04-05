from __future__ import annotations

import re
from typing import Any

import requests


DEFAULT_TIMEOUT = 10


def _fetch_text(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def get_rem_latest(
    *,
    base_url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any] | None:
    text = _fetch_text(base_url, timeout=timeout)

    monthly_match = re.search(r"inflaci[oó]n mensual de\s+(\d+(?:,\d+)?)%", text, flags=re.IGNORECASE)
    if not monthly_match:
        return None

    month_match = re.search(
        r"(?:#+\s*)?RESUMEN EJECUTIVO\s*\|\s*([A-ZÁÉÍÓÚÑ]+\s+DE\s+\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    published_match = re.search(r"publicado el d[ií]a\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})", text, flags=re.IGNORECASE)

    return {
        "inflacion_mensual_pct": float(monthly_match.group(1).replace(",", ".")),
        "periodo": month_match.group(1).title() if month_match else None,
        "fecha_publicacion": published_match.group(1) if published_match else None,
        "source_url": base_url,
    }
