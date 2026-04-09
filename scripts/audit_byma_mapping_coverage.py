from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BYMA_RATIOS_PATH = (
    PROJECT_ROOT
    / "data"
    / "reference"
    / "69822eccb14ee34b5414710b_BYMA-CEDEARs-2026-02-03.ratios.unique.json"
)
DEFAULT_FINVIZ_MAP_PATH = PROJECT_ROOT / "data" / "mappings" / "finviz_map.json"
DEFAULT_PROFILE_MAP_PATH = (
    PROJECT_ROOT / "data" / "mappings" / "instrument_profile_map.json"
)
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "reference" / "byma_mapping_coverage.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_coverage_report(
    *,
    byma_ratios: dict[str, int | float],
    finviz_map: dict[str, str],
    instrument_profile_map: dict[str, dict],
) -> dict[str, object]:
    byma_tickers = set(byma_ratios)
    finviz_tickers = set(finviz_map)
    profile_tickers = set(instrument_profile_map)

    fully_covered = sorted(byma_tickers & finviz_tickers & profile_tickers)
    missing_finviz = sorted(byma_tickers - finviz_tickers)
    missing_profile = sorted(byma_tickers - profile_tickers)
    missing_both = sorted(byma_tickers - (finviz_tickers | profile_tickers))
    ratios_only = sorted(
        byma_tickers & profile_tickers - finviz_tickers
    )
    finviz_only = sorted(
        byma_tickers & finviz_tickers - profile_tickers
    )

    return {
        "summary": {
            "byma_ticker_count": len(byma_tickers),
            "finviz_map_count": len(finviz_tickers),
            "instrument_profile_count": len(profile_tickers),
            "fully_covered_count": len(fully_covered),
            "missing_finviz_count": len(missing_finviz),
            "missing_profile_count": len(missing_profile),
            "missing_both_count": len(missing_both),
            "ratios_plus_profile_without_finviz_count": len(ratios_only),
            "ratios_plus_finviz_without_profile_count": len(finviz_only),
        },
        "fully_covered": fully_covered,
        "missing_finviz": missing_finviz,
        "missing_profile": missing_profile,
        "missing_both": missing_both,
        "ratios_plus_profile_without_finviz": ratios_only,
        "ratios_plus_finviz_without_profile": finviz_only,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audita cobertura de mappings del catálogo BYMA de CEDEARs."
    )
    parser.add_argument(
        "--byma-ratios",
        type=Path,
        default=DEFAULT_BYMA_RATIOS_PATH,
        help="Ruta a ratios únicos extraídos desde el PDF de BYMA.",
    )
    parser.add_argument(
        "--finviz-map",
        type=Path,
        default=DEFAULT_FINVIZ_MAP_PATH,
        help="Ruta a data/mappings/finviz_map.json.",
    )
    parser.add_argument(
        "--instrument-profile-map",
        type=Path,
        default=DEFAULT_PROFILE_MAP_PATH,
        help="Ruta a data/mappings/instrument_profile_map.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Ruta del JSON de salida.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_coverage_report(
        byma_ratios=_load_json(args.byma_ratios),
        finviz_map=_load_json(args.finviz_map),
        instrument_profile_map=_load_json(args.instrument_profile_map),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    summary = report["summary"]
    print(f"Tickers BYMA: {summary['byma_ticker_count']}")
    print(f"Cobertura completa: {summary['fully_covered_count']}")
    print(f"Faltan en finviz_map: {summary['missing_finviz_count']}")
    print(f"Faltan en instrument_profile_map: {summary['missing_profile_count']}")
    print(f"Faltan en ambos: {summary['missing_both_count']}")


if __name__ == "__main__":
    main()
