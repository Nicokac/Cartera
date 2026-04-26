import logging
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from generate_real_report_snapshots import (
    _load_snapshot_csv_impl,
    load_previous_portfolio_snapshot_impl,
    write_real_snapshots_impl,
)


class GenerateRealReportSplitSnapshotsTests(unittest.TestCase):
    def test_write_real_snapshots_impl_creates_expected_files(self) -> None:
        snapshots_dir = ROOT / "tmp_split_snapshots_write"
        snapshots_dir.mkdir(exist_ok=True)
        self.addCleanup(lambda: snapshots_dir.rmdir())
        self.addCleanup(lambda: [path.unlink(missing_ok=True) for path in snapshots_dir.glob("*")])

        paths = write_real_snapshots_impl(
            portfolio_bundle={
                "df_total": pd.DataFrame([{"Ticker_IOL": "AAPL", "Valorizado_ARS": 1000.0}]),
                "liquidity_contract": {"cash_ars": 150000.0},
            },
            dashboard_bundle={"kpis": {"total_ars": 1000.0}},
            decision_bundle={"final_decision": pd.DataFrame([{"Ticker_IOL": "AAPL", "score_unificado": 0.15}])},
            technical_overlay=pd.DataFrame([{"Ticker_IOL": "AAPL", "RSI_14": 52.0}]),
            snapshots_dir=snapshots_dir,
        )

        self.assertEqual(len(paths), 5)
        for path in paths:
            self.assertTrue(path.exists())

    def test_load_previous_portfolio_snapshot_impl_skips_invalid_stamps_and_schema(self) -> None:
        snapshots_dir = ROOT / "tmp_split_snapshots_invalid"
        snapshots_dir.mkdir(exist_ok=True)
        bad_stamp = snapshots_dir / "foo_real_portfolio_master.csv"
        bad_schema = snapshots_dir / "2026-04-15_real_portfolio_master.csv"
        bad_stamp.write_text("Ticker_IOL,Tipo\nAAPL,CEDEAR\n", encoding="utf-8")
        bad_schema.write_text("Ticker,Tipo\nAAPL,CEDEAR\n", encoding="utf-8")
        self.addCleanup(lambda: snapshots_dir.rmdir())
        self.addCleanup(lambda: [path.unlink(missing_ok=True) for path in snapshots_dir.glob("*")])

        previous_df, previous_date = load_previous_portfolio_snapshot_impl(
            pd.Timestamp("2026-04-16"),
            snapshots_dir=snapshots_dir,
            primary_snapshots_dir=ROOT / "unused_primary",
            legacy_snapshots_dir=ROOT / "unused_legacy",
            use_legacy_snapshots=False,
            required_snapshot_columns={"Ticker_IOL"},
            optional_numeric_columns=("Peso_%",),
            logger=logging.getLogger("test.snapshots.invalid"),
        )
        self.assertTrue(previous_df.empty)
        self.assertIsNone(previous_date)

    def test_load_previous_portfolio_snapshot_impl_returns_empty_when_dirs_missing(self) -> None:
        previous_df, previous_date = load_previous_portfolio_snapshot_impl(
            pd.Timestamp("2026-04-16"),
            snapshots_dir=None,
            primary_snapshots_dir=ROOT / "tmp_missing_primary_snapshots",
            legacy_snapshots_dir=ROOT / "tmp_missing_legacy_snapshots",
            use_legacy_snapshots=True,
            required_snapshot_columns={"Ticker_IOL"},
            optional_numeric_columns=("Peso_%",),
            logger=logging.getLogger("test.snapshots.missing"),
        )
        self.assertTrue(previous_df.empty)
        self.assertIsNone(previous_date)

    def test_load_previous_portfolio_snapshot_impl_handles_corrupt_csv_and_duplicate_dir_scan(self) -> None:
        snapshots_dir = ROOT / "tmp_split_snapshots_corrupt_dup"
        snapshots_dir.mkdir(exist_ok=True)
        corrupt = snapshots_dir / "2026-04-15_real_portfolio_master.csv"
        corrupt.write_bytes(b"\x00\x01\x02")
        self.addCleanup(lambda: snapshots_dir.rmdir())
        self.addCleanup(lambda: [path.unlink(missing_ok=True) for path in snapshots_dir.glob("*")])

        previous_df, previous_date = load_previous_portfolio_snapshot_impl(
            pd.Timestamp("2026-04-16"),
            snapshots_dir=None,
            primary_snapshots_dir=snapshots_dir,
            legacy_snapshots_dir=snapshots_dir,
            use_legacy_snapshots=True,
            required_snapshot_columns={"Ticker_IOL"},
            optional_numeric_columns=("Peso_%",),
            logger=logging.getLogger("test.snapshots.corrupt"),
        )
        self.assertTrue(previous_df.empty)
        self.assertIsNone(previous_date)

    def test_load_previous_portfolio_snapshot_impl_handles_invalid_run_date(self) -> None:
        previous_df, previous_date = load_previous_portfolio_snapshot_impl(
            "not-a-date",
            snapshots_dir=None,
            primary_snapshots_dir=ROOT / "tmp_non_existing_snapshots",
            legacy_snapshots_dir=ROOT / "tmp_non_existing_legacy",
            use_legacy_snapshots=True,
            required_snapshot_columns={"Ticker_IOL"},
            optional_numeric_columns=("Peso_%",),
            logger=logging.getLogger("test.snapshots"),
        )

        self.assertTrue(previous_df.empty)
        self.assertIsNone(previous_date)

    def test_load_snapshot_csv_impl_returns_empty_on_read_error(self) -> None:
        snapshots_dir = ROOT / "tmp_split_snapshots_read_error"
        snapshots_dir.mkdir(exist_ok=True)
        self.addCleanup(lambda: snapshots_dir.rmdir())

        previous_df = _load_snapshot_csv_impl(
            snapshots_dir,
            required_snapshot_columns={"Ticker_IOL"},
            optional_numeric_columns=("Peso_%",),
            logger=logging.getLogger("test.snapshots.read_error"),
        )
        self.assertTrue(previous_df.empty)


if __name__ == "__main__":
    unittest.main()
