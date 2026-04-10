from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

try:
    from pypdf import PdfReader
except ModuleNotFoundError as exc:  # pragma: no cover - depende del entorno local
    raise SystemExit(
        "Falta la dependencia opcional 'pypdf'. Instalala con 'pip install pypdf' o 'pip install .[byma]'."
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "reference"

SKIP_PREFIXES = (
    "CEDEARs Negociables en BYMA",
    "Nombre de la Compañía",
    "Código",
    "Mercado donde",
    "Cotiza Ratio (*)",
    "Bolsas y Mercados Argentinos S.A.",
    "Mercado registrado bajo el N° 639 de la CNV (*) Relación CEDEAR Subyacente",
    "Actualizado ",
    "Página ",
)

MARKET_PATTERNS = [
    "LONDON STOCK EXCHANGE",
    "NYSE American",
    "NASDAQ GS",
    "NASDAQ GM",
    "NASDAQ CM",
    "NYSE Arca",
    "FRANKFURT",
    "New York",
    "BOVESPA",
    "NASDAQ",
    "NYSE",
    "XETRA",
    "OTC US",
    "CBOE",
    "B3",
    "OTC",
    "-",
]

ROW_PATTERN = re.compile(
    rf"^(?P<company_name>.+?)\s+"
    rf"(?P<ticker_byma>[A-Z0-9.]+)\s+"
    rf"(?P<market>{'|'.join(sorted((re.escape(m) for m in MARKET_PATTERNS), key=len, reverse=True))})\s+"
    rf"(?P<ratio>\d+:\d+)$"
)


def _normalize_line(raw_line: str) -> str:
    return " ".join(raw_line.replace("\xa0", " ").split())


def _extract_pdf_date(reader: PdfReader) -> str | None:
    for page in reader.pages:
        text = page.extract_text() or ""
        match = re.search(r"Actualizado\s+(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if match:
            day, month, year = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
    return None


def _iter_content_lines(reader: PdfReader) -> list[str]:
    content_lines: list[str] = []
    for page in reader.pages:
        for raw_line in (page.extract_text() or "").splitlines():
            line = _normalize_line(raw_line)
            if not line or line == "BYMA":
                continue
            if any(line.startswith(prefix) for prefix in SKIP_PREFIXES):
                continue
            content_lines.append(line)
    return content_lines


def extract_rows(pdf_path: Path) -> tuple[list[dict[str, object]], str | None]:
    reader = PdfReader(str(pdf_path))
    report_date = _extract_pdf_date(reader)
    content_lines = _iter_content_lines(reader)

    rows: list[dict[str, object]] = []
    buffer = ""
    for line in content_lines:
        candidate = f"{buffer} {line}".strip() if buffer else line
        match = ROW_PATTERN.match(candidate)
        if match:
            row = match.groupdict()
            numerator_text, denominator_text = row["ratio"].split(":", 1)
            row["ratio_numerator"] = int(numerator_text)
            row["ratio_denominator"] = int(denominator_text)
            row["ratio_factor"] = row["ratio_numerator"] / row["ratio_denominator"]
            rows.append(row)
            buffer = ""
        else:
            buffer = candidate

    if buffer:
        raise ValueError(f"No se pudo parsear la última fila del PDF: {buffer}")
    return rows, report_date


def build_conflicts(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["ticker_byma"])].append(row)
    return {ticker: values for ticker, values in grouped.items() if len(values) > 1}


def build_unique_ratio_map(
    rows: list[dict[str, object]], conflicts: dict[str, list[dict[str, object]]]
) -> dict[str, int | float]:
    ratio_map: dict[str, int | float] = {}
    for row in rows:
        ticker = str(row["ticker_byma"])
        if ticker in conflicts:
            continue
        value = row["ratio_factor"]
        ratio_map[ticker] = int(value) if float(value).is_integer() else float(value)
    return dict(sorted(ratio_map.items()))


def compare_with_current_ratios(candidate_map: dict[str, int | float]) -> dict[str, object]:
    current_path = PROJECT_ROOT / "data" / "mappings" / "ratios.json"
    current_ratios = json.loads(current_path.read_text(encoding="utf-8"))

    current_keys = set(current_ratios)
    candidate_keys = set(candidate_map)
    changed = {
        ticker: {"current": current_ratios[ticker], "byma_pdf": candidate_map[ticker]}
        for ticker in sorted(current_keys & candidate_keys)
        if float(current_ratios[ticker]) != float(candidate_map[ticker])
    }

    return {
        "current_ratio_count": len(current_ratios),
        "byma_unique_ratio_count": len(candidate_map),
        "missing_in_current": sorted(candidate_keys - current_keys),
        "missing_in_byma_pdf": sorted(current_keys - candidate_keys),
        "changed": changed,
    }


def write_outputs(
    *,
    output_dir: Path,
    stem: str,
    rows: list[dict[str, object]],
    conflicts: dict[str, list[dict[str, object]]],
    candidate_map: dict[str, int | float],
    comparison: dict[str, object],
    source_pdf: Path,
    report_date: str | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    catalog_path = output_dir / f"{stem}.csv"
    with catalog_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "company_name",
                "ticker_byma",
                "market",
                "ratio",
                "ratio_numerator",
                "ratio_denominator",
                "ratio_factor",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "source_pdf": str(source_pdf),
        "report_date": report_date,
        "row_count": len(rows),
        "unique_ticker_count": len({str(row["ticker_byma"]) for row in rows}),
        "duplicate_ticker_count": len(conflicts),
    }
    (output_dir / f"{stem}.metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / f"{stem}.conflicts.json").write_text(
        json.dumps(conflicts, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / f"{stem}.ratios.unique.json").write_text(
        json.dumps(candidate_map, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / f"{stem}.comparison.json").write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extrae el catálogo de CEDEARs negociables de un PDF de BYMA."
    )
    parser.add_argument("pdf_path", type=Path, help="Ruta al PDF de BYMA.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directorio donde se escribirán CSV/JSON de salida.",
    )
    parser.add_argument(
        "--stem",
        type=str,
        default=None,
        help="Prefijo para los archivos de salida. Por defecto se usa el nombre del PDF sin extensión.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pdf_path = args.pdf_path.expanduser().resolve()
    stem = args.stem or pdf_path.stem

    rows, report_date = extract_rows(pdf_path)
    conflicts = build_conflicts(rows)
    candidate_map = build_unique_ratio_map(rows, conflicts)
    comparison = compare_with_current_ratios(candidate_map)
    write_outputs(
        output_dir=args.output_dir,
        stem=stem,
        rows=rows,
        conflicts=conflicts,
        candidate_map=candidate_map,
        comparison=comparison,
        source_pdf=pdf_path,
        report_date=report_date,
    )

    print(f"Filas extraídas: {len(rows)}")
    print(f"Tickers únicos: {len({str(row['ticker_byma']) for row in rows})}")
    print(f"Conflictos por ticker duplicado: {len(conflicts)}")
    print(f"Ratios únicos exportables: {len(candidate_map)}")
    print(f"Nuevos ratios vs data/mappings/ratios.json: {len(comparison['missing_in_current'])}")
    print(f"Cambios detectados vs ratios actuales: {len(comparison['changed'])}")


if __name__ == "__main__":
    main()
