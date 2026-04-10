from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "data" / "reference"
FINVIZ_CANDIDATES_DIR = REFERENCE_DIR / "finviz_candidates"
MAPPINGS_DIR = ROOT / "data" / "mappings"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> None:
    coverage = load_json(REFERENCE_DIR / "byma_mapping_coverage.json")
    manual = load_json(FINVIZ_CANDIDATES_DIR / "manual_review_status.json")
    excluded = load_json(FINVIZ_CANDIDATES_DIR / "excluded.json")
    final_status = load_json(FINVIZ_CANDIDATES_DIR / "final_status.json")
    unsupported = load_json(MAPPINGS_DIR / "unsupported_byma_tickers.json")

    missing_both = set(coverage["missing_both"])
    excluded_set = {row["ticker_byma"] for row in excluded}
    rescued = {row["ticker_byma"] for row in manual["rescued_after_manual_review"]}
    manual_backlog = {
        ticker
        for tickers in manual["manual_backlog_by_reason"].values()
        for ticker in tickers
    }
    unsupported_set = {
        ticker
        for tickers in unsupported["excluded_by_reason"].values()
        for ticker in tickers
    }

    assert missing_both == manual_backlog, "missing_both no coincide con el backlog manual"
    assert excluded_set == manual_backlog | rescued, "excluded.json no coincide con backlog + rescatados"
    assert len(manual_backlog) == manual["remaining_manual_review_count"], "conteo manual_review_status inconsistente"
    assert len(manual_backlog) == final_status["remaining_manual_review_count"], "conteo final_status inconsistente"
    assert manual_backlog == unsupported_set, "unsupported_byma_tickers no coincide con backlog manual"
    assert len(unsupported_set) == unsupported["excluded_count"], "conteo unsupported_byma_tickers inconsistente"
    assert len(rescued) == len(manual["rescued_after_manual_review"]), "rescatados duplicados"

    print(f"Backlog manual validado: {len(manual_backlog)} tickers")
    print(f"Rescatados manualmente: {len(rescued)}")
    print("Estado BYMA/Finviz consistente")


if __name__ == "__main__":
    main()
