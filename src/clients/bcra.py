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
