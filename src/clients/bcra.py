from __future__ import annotations

from io import BytesIO
import re
from typing import Any
import zipfile
import xml.etree.ElementTree as ET

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


def _fetch_bytes(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> bytes:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def _fetch_json(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _normalize_text(value: object) -> str:
    text = str(value or "").strip().lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
        "Ã¡": "a",
        "Ã©": "e",
        "Ã­": "i",
        "Ã³": "o",
        "Ãº": "u",
        "Ã±": "n",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return " ".join(text.split())


def _build_url_with_params(base_url: str, params: dict[str, object] | None = None) -> str:
    if not params:
        return base_url
    query_parts = [f"{key}={value}" for key, value in params.items() if value not in {None, ""}]
    if not query_parts:
        return base_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{'&'.join(query_parts)}"


def _extract_latest_result(payload: object) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        return None
    flattened: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        if item.get("valor") is not None:
            flattened.append(item)
            continue
        detalle = item.get("detalle")
        if isinstance(detalle, list):
            flattened.extend(entry for entry in detalle if isinstance(entry, dict) and entry.get("valor") is not None)
    if not flattened:
        return None
    flattened.sort(key=lambda item: str(item.get("fecha") or ""))
    return flattened[-1]


def get_monetary_variable_latest(
    *,
    base_url: str,
    variable_id: int,
    timeout: int = DEFAULT_TIMEOUT,
    desde: str | None = None,
    hasta: str | None = None,
) -> dict[str, Any] | None:
    payload = _fetch_json(
        _build_url_with_params(f"{base_url.rstrip('/')}/{int(variable_id)}", {"desde": desde, "hasta": hasta}),
        timeout=timeout,
    )
    latest = _extract_latest_result(payload)
    if not latest:
        return None
    try:
        value = float(str(latest["valor"]).replace(",", "."))
    except Exception:
        return None
    return {"id_variable": int(variable_id), "fecha": latest.get("fecha"), "valor": value}


def get_monetary_variables_catalog(
    *,
    base_url: str,
    timeout: int = DEFAULT_TIMEOUT,
    limit: int = 3000,
) -> list[dict[str, Any]]:
    payload = _fetch_json(_build_url_with_params(base_url, {"limit": limit}), timeout=timeout)
    if not isinstance(payload, dict):
        return []
    results = payload.get("results")
    return [item for item in results if isinstance(item, dict)] if isinstance(results, list) else []


def _get_catalog_entry(
    catalog: list[dict[str, Any]],
    variable_id: int,
) -> dict[str, Any] | None:
    for item in catalog:
        try:
            if int(item.get("idVariable")) == int(variable_id):
                return item
        except Exception:
            continue
    return None


def _find_catalog_variable_id(
    catalog: list[dict[str, Any]],
    *,
    include_terms: tuple[str, ...],
    exclude_terms: tuple[str, ...] = (),
) -> int | None:
    for item in catalog:
        description = _normalize_text(item.get("descripcion") or item.get("detalle") or item.get("nombre"))
        if not description:
            continue
        if not all(term in description for term in include_terms):
            continue
        if any(term in description for term in exclude_terms):
            continue
        try:
            return int(item.get("idVariable"))
        except Exception:
            continue
    return None


def discover_tamar_variable_ids(
    *,
    base_url: str,
    timeout: int = DEFAULT_TIMEOUT,
    limit: int = 3000,
) -> dict[str, int | None]:
    catalog = get_monetary_variables_catalog(base_url=base_url, timeout=timeout, limit=limit)
    return {
        "tamar_tna_id": _find_catalog_variable_id(
            catalog,
            include_terms=("tamar", "bancos privados", "% n.a"),
            exclude_terms=("badlar",),
        ),
        "tamar_tea_id": _find_catalog_variable_id(
            catalog,
            include_terms=("tamar", "bancos privados", "% e.a"),
            exclude_terms=("badlar",),
        ),
    }


def get_bcra_monetary_context(
    *,
    base_url: str,
    reservas_id: int,
    a3500_id: int,
    badlar_tna_id: int,
    badlar_tea_id: int | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    desde: str | None = None,
    hasta: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    catalog = get_monetary_variables_catalog(base_url=base_url, timeout=timeout)

    reservas_entry = _get_catalog_entry(catalog, reservas_id)
    if reservas_entry:
        payload["reservas_bcra_musd"] = float(reservas_entry.get("ultValorInformado"))
        payload["reservas_bcra_fecha"] = reservas_entry.get("ultFechaInformada")
    else:
        reservas = get_monetary_variable_latest(
            base_url=base_url,
            variable_id=reservas_id,
            timeout=timeout,
            desde=desde,
            hasta=hasta,
        )
        if reservas:
            payload["reservas_bcra_musd"] = reservas["valor"]
            payload["reservas_bcra_fecha"] = reservas.get("fecha")

    a3500_entry = _get_catalog_entry(catalog, a3500_id)
    if a3500_entry:
        payload["a3500_mayorista"] = float(a3500_entry.get("ultValorInformado"))
        payload["a3500_fecha"] = a3500_entry.get("ultFechaInformada")
    else:
        a3500 = get_monetary_variable_latest(
            base_url=base_url,
            variable_id=a3500_id,
            timeout=timeout,
            desde=desde,
            hasta=hasta,
        )
        if a3500:
            payload["a3500_mayorista"] = a3500["valor"]
            payload["a3500_fecha"] = a3500.get("fecha")

    badlar_tna_entry = _get_catalog_entry(catalog, badlar_tna_id)
    if badlar_tna_entry:
        payload["badlar"] = float(badlar_tna_entry.get("ultValorInformado"))
        payload["badlar_fecha"] = badlar_tna_entry.get("ultFechaInformada")
    else:
        badlar_tna = get_monetary_variable_latest(
            base_url=base_url,
            variable_id=badlar_tna_id,
            timeout=timeout,
            desde=desde,
            hasta=hasta,
        )
        if badlar_tna:
            payload["badlar"] = badlar_tna["valor"]
            payload["badlar_fecha"] = badlar_tna.get("fecha")

    if badlar_tea_id is not None:
        badlar_tea_entry = _get_catalog_entry(catalog, badlar_tea_id)
        if badlar_tea_entry and badlar_tea_entry.get("ultValorInformado") is not None:
            payload["badlar_tea"] = float(badlar_tea_entry.get("ultValorInformado"))
        else:
            try:
                badlar_tea = get_monetary_variable_latest(
                    base_url=base_url,
                    variable_id=badlar_tea_id,
                    timeout=timeout,
                    desde=desde,
                    hasta=hasta,
                )
            except Exception:
                badlar_tea = None
            if badlar_tea:
                payload["badlar_tea"] = badlar_tea["valor"]

    tamar_ids = discover_tamar_variable_ids(base_url=base_url, timeout=timeout)
    tamar_tna_id = tamar_ids.get("tamar_tna_id")
    tamar_tea_id = tamar_ids.get("tamar_tea_id")

    if tamar_tna_id is not None:
        tamar_tna_entry = _get_catalog_entry(catalog, int(tamar_tna_id))
        if tamar_tna_entry and tamar_tna_entry.get("ultValorInformado") is not None:
            payload["tamar"] = float(tamar_tna_entry.get("ultValorInformado"))
            payload["tamar_fecha"] = tamar_tna_entry.get("ultFechaInformada")
            payload["tamar_tna_id"] = int(tamar_tna_id)
        else:
            tamar_tna = get_monetary_variable_latest(
                base_url=base_url,
                variable_id=int(tamar_tna_id),
                timeout=timeout,
                desde=desde,
                hasta=hasta,
            )
            if tamar_tna:
                payload["tamar"] = tamar_tna["valor"]
                payload["tamar_fecha"] = tamar_tna.get("fecha")
                payload["tamar_tna_id"] = int(tamar_tna_id)

    if tamar_tea_id is not None:
        tamar_tea_entry = _get_catalog_entry(catalog, int(tamar_tea_id))
        if tamar_tea_entry and tamar_tea_entry.get("ultValorInformado") is not None:
            payload["tamar_tea"] = float(tamar_tea_entry.get("ultValorInformado"))
            payload["tamar_tea_id"] = int(tamar_tea_id)
        else:
            tamar_tea = get_monetary_variable_latest(
                base_url=base_url,
                variable_id=int(tamar_tea_id),
                timeout=timeout,
                desde=desde,
                hasta=hasta,
            )
            if tamar_tea:
                payload["tamar_tea"] = tamar_tea["valor"]
                payload["tamar_tea_id"] = int(tamar_tea_id)

    return payload


def _resolve_sheet_target(zip_file: zipfile.ZipFile, sheet_name: str) -> str | None:
    ns = {
        "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    workbook = ET.fromstring(zip_file.read("xl/workbook.xml"))
    rels = ET.fromstring(zip_file.read("xl/_rels/workbook.xml.rels"))
    rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("rel:Relationship", ns)}
    sheets = workbook.find("a:sheets", ns)
    if sheets is None:
        return None
    for sheet in sheets:
        if sheet.attrib.get("name") != sheet_name:
            continue
        rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rel_map.get(rel_id)
        if not target:
            return None
        return "xl/" + target.lstrip("/")
    return None


def _extract_rem_12m_from_excel_content(content: bytes) -> float | None:
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    def col_to_idx(ref: str) -> int:
        letters = "".join(ch for ch in ref if ch.isalpha())
        total = 0
        for ch in letters:
            total = total * 26 + (ord(ch.upper()) - ord("A") + 1)
        return total - 1

    with zipfile.ZipFile(BytesIO(content)) as zf:
        target = _resolve_sheet_target(zf, "Indicadores Principales")
        if not target:
            return None

        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            shared = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in shared.findall("a:si", ns):
                texts = [t.text or "" for t in si.iterfind(".//a:t", ns)]
                shared_strings.append("".join(texts))

        sheet = ET.fromstring(zf.read(target))
        current_section = ""

        for row in sheet.findall(".//a:sheetData/a:row", ns):
            section_label = None
            row_values: dict[int, str] = {}

            for cell in row.findall("a:c", ns):
                ref = cell.attrib.get("r", "")
                idx = col_to_idx(ref)
                value_node = cell.find("a:v", ns)
                if value_node is None:
                    continue
                raw = value_node.text or ""
                if cell.attrib.get("t") == "s":
                    try:
                        value = shared_strings[int(raw)]
                    except Exception:
                        value = raw
                else:
                    value = raw
                row_values[idx] = value
                if idx == 0:
                    section_label = value

            if section_label:
                normalized = _normalize_text(section_label)
                if "ipc-gba" in normalized and "prox. 12 meses" in normalized:
                    current_section = "ipc_12m"
                    continue
                if current_section == "ipc_12m" and normalized not in {
                    "mediana",
                    "promedio",
                    "desvio",
                    "maximo",
                    "minimo",
                    "percentil 90",
                    "percentil 75",
                    "percentil 25",
                    "percentil 10",
                    "cantidad de participantes",
                }:
                    break

            if current_section != "ipc_12m" or not row_values:
                continue

            label = _normalize_text(row_values.get(0, ""))
            if label == "mediana":
                value = row_values.get(2) or row_values.get(1)
                try:
                    return float(str(value).replace(",", "."))
                except Exception:
                    return None

    return None


def get_rem_latest(
    *,
    base_url: str,
    xlsx_url: str | None = None,
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

    rem_12m_pct = None
    if xlsx_url:
        try:
            rem_12m_pct = _extract_rem_12m_from_excel_content(_fetch_bytes(xlsx_url, timeout=timeout))
        except Exception:
            rem_12m_pct = None

    return {
        "inflacion_mensual_pct": float(monthly_match.group(1).replace(",", ".")),
        "inflacion_12m_pct": rem_12m_pct,
        "periodo": month_match.group(1).title() if month_match else None,
        "fecha_publicacion": published_match.group(1) if published_match else None,
        "source_url": base_url,
        "source_xlsx_url": xlsx_url,
    }
