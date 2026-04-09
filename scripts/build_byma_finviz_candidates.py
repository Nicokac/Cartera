from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BYMA_CSV = (
    PROJECT_ROOT / "data" / "reference" / "69822eccb14ee34b5414710b_BYMA-CEDEARs-2026-02-03.csv"
)
DEFAULT_FINVIZ_MAP = PROJECT_ROOT / "data" / "mappings" / "finviz_map.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "reference" / "finviz_candidates"

SUPPORTED_FINVIZ_MARKETS = {
    "NYSE",
    "NASDAQ",
    "NASDAQ GS",
    "NASDAQ GM",
    "NASDAQ CM",
    "NYSE Arca",
    "NYSE American",
    "New York",
    "CBOE",
}
SIMPLE_TICKER_PATTERN = re.compile(r"^[A-Z]{1,5}$")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_candidates(rows: list[dict[str, str]], finviz_map: dict[str, str]) -> dict[str, object]:
    existing = set(finviz_map)
    candidates: list[dict[str, str]] = []
    excluded: list[dict[str, str]] = []

    for row in rows:
        ticker = row["ticker_byma"]
        market = row["market"]
        if ticker in existing:
            continue

        reason = None
        if market not in SUPPORTED_FINVIZ_MARKETS:
            reason = "mercado_no_prioritario_para_finviz"
        elif not SIMPLE_TICKER_PATTERN.fullmatch(ticker):
            reason = "ticker_no_simple"

        if reason:
            excluded.append(
                {
                    "ticker_byma": ticker,
                    "company_name": row["company_name"],
                    "market": market,
                    "reason": reason,
                }
            )
            continue

        candidates.append(
            {
                "ticker_byma": ticker,
                "ticker_finviz_candidate": ticker,
                "company_name": row["company_name"],
                "market": market,
                "ratio": row["ratio"],
            }
        )

    candidates.sort(key=lambda item: (item["market"], item["ticker_byma"]))
    excluded.sort(key=lambda item: (item["reason"], item["market"], item["ticker_byma"]))
    return {"candidates": candidates, "excluded": excluded}


def write_batches(candidates: list[dict[str, str]], output_dir: Path, batch_size: int) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_files: list[str] = []
    total_batches = max(math.ceil(len(candidates) / batch_size), 1)
    for index in range(total_batches):
        batch = candidates[index * batch_size : (index + 1) * batch_size]
        batch_name = f"byma_finviz_candidates_batch_{index + 1:02d}.json"
        (output_dir / batch_name).write_text(
            json.dumps(batch, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        batch_files.append(batch_name)
    return batch_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Construye tandas candidatas para ampliar finviz_map desde el catalogo BYMA."
    )
    parser.add_argument("--byma-csv", type=Path, default=DEFAULT_BYMA_CSV)
    parser.add_argument("--finviz-map", type=Path, default=DEFAULT_FINVIZ_MAP)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--batch-size", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = _read_rows(args.byma_csv)
    finviz_map = _load_json(args.finviz_map)
    result = build_candidates(rows, finviz_map)

    batch_files = write_batches(result["candidates"], args.output_dir, args.batch_size)
    summary = {
        "candidate_count": len(result["candidates"]),
        "excluded_count": len(result["excluded"]),
        "batch_size": args.batch_size,
        "batch_files": batch_files,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (args.output_dir / "excluded.json").write_text(
        json.dumps(result["excluded"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Candidatos directos BYMA->Finviz: {summary['candidate_count']}")
    print(f"Excluidos para revision manual: {summary['excluded_count']}")
    print(f"Tandas generadas: {len(batch_files)}")


if __name__ == "__main__":
    main()
