from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = ROOT / "data" / "examples"


def iter_example_pairs() -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for source in EXAMPLES_DIR.rglob("*.json.example"):
        relative = source.relative_to(EXAMPLES_DIR)
        target = ROOT / "data" / relative.parent / source.name.replace(".json.example", ".json")
        pairs.append((source, target))
    return sorted(pairs, key=lambda item: str(item[1]))


def bootstrap(*, overwrite: bool = False, dry_run: bool = False) -> int:
    created = 0
    skipped = 0

    for source, target in iter_example_pairs():
        if target.exists() and not overwrite:
            print(f"SKIP {target.relative_to(ROOT)}")
            skipped += 1
            continue

        print(f"{'PLAN' if dry_run else 'COPY'} {source.relative_to(ROOT)} -> {target.relative_to(ROOT)}")
        if dry_run:
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        created += 1

    print(f"Done. created={created} skipped={skipped} dry_run={dry_run}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap local JSON config from data/examples. "
            "This script only copies files that have a .json.example pair; "
            "it is not intended to mirror every versioned mapping in data/mappings."
        )
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing target JSON files.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned copies without writing files.")
    args = parser.parse_args()
    return bootstrap(overwrite=args.overwrite, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
