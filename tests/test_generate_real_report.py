import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from generate_real_report import (
    build_real_bonistas_bundle,
    enrich_real_cedears,
    extract_quote_tickers,
    legacy_snapshots_enabled,
    load_previous_portfolio_snapshot,
    load_local_env,
    parse_finviz_number,
    parse_finviz_pct,
    parse_args,
    prompt_money_ars,
    prompt_yes_no,
    resolve_iol_credentials,
)


class GenerateRealReportTests(unittest.TestCase):
    def test_parse_finviz_number_handles_suffixes_and_missing_values(self) -> None:
        self.assertEqual(parse_finviz_number("1.5B"), 1_500_000_000.0)
        self.assertEqual(parse_finviz_number("2,400M"), 2_400_000_000.0)
        self.assertTrue(pd.isna(parse_finviz_number("-")))
        self.assertTrue(pd.isna(parse_finviz_number("no-num")))

    def test_parse_finviz_pct_handles_percent_strings_and_missing_values(self) -> None:
        self.assertEqual(parse_finviz_pct("12.5%"), 12.5)
        self.assertEqual(parse_finviz_pct("1,234.5%"), 1234.5)
        self.assertTrue(pd.isna(parse_finviz_pct("-")))
        self.assertTrue(pd.isna(parse_finviz_pct(None)))

    def test_extract_quote_tickers_filters_supported_iol_asset_types(self) -> None:
        activos = [
            {"titulo": {"simbolo": "AAPL", "tipo": "CEDEARS"}},
            {"titulo": {"simbolo": "AL30", "tipo": "Titulos Publicos"}},
            {"titulo": {"simbolo": "PAMP", "tipo": "ACCIONES"}},
            {"titulo": {"simbolo": "IOLPORA", "tipo": "FCI"}},
            {"titulo": {"simbolo": "", "tipo": "CEDEARS"}},
            {"titulo": {}},
        ]

        self.assertEqual(extract_quote_tickers(activos), ["AAPL", "AL30", "PAMP"])

    def test_load_local_env_parses_simple_env_file_without_overriding_existing_env(self) -> None:
        env_path = ROOT / "tmp_test.env"
        env_path.write_text(
            "# comment\n"
            "IOL_USERNAME=usuario@example.com\n"
            "IOL_PASSWORD='secret-pass'\n",
            encoding="utf-8",
        )
        self.addCleanup(lambda: env_path.unlink(missing_ok=True))

        with patch.dict("os.environ", {"IOL_USERNAME": "prioridad@env.com"}, clear=False):
            loaded = load_local_env(env_path)
            self.assertEqual(loaded["IOL_USERNAME"], "usuario@example.com")
            self.assertEqual(loaded["IOL_PASSWORD"], "secret-pass")
            self.assertEqual(resolve_iol_credentials()[0], "prioridad@env.com")

    def test_resolve_iol_credentials_uses_prompt_as_fallback(self) -> None:
        with patch("generate_real_report.load_local_env", return_value={}), patch.dict("os.environ", {}, clear=True), patch(
            "builtins.input", return_value="prompt-user@example.com"
        ), patch("generate_real_report.getpass", return_value="prompt-pass"):
            username, password = resolve_iol_credentials()

        self.assertEqual(username, "prompt-user@example.com")
        self.assertEqual(password, "prompt-pass")

    def test_resolve_iol_credentials_fails_in_non_interactive_mode_without_values(self) -> None:
        with patch("generate_real_report.load_local_env", return_value={}), patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "Usuario IOL faltante"):
                resolve_iol_credentials(non_interactive=True)

    def test_parse_args_accepts_non_interactive_funding_inputs(self) -> None:
        args = parse_args(
            [
                "--username",
                "bot@example.com",
                "--password",
                "secret",
                "--non-interactive",
                "--no-use-iol-liquidity",
                "--aporte-externo-ars",
                "600000",
            ]
        )

        self.assertEqual(args.username, "bot@example.com")
        self.assertEqual(args.password, "secret")
        self.assertTrue(args.non_interactive)
        self.assertFalse(args.use_iol_liquidity)
        self.assertEqual(args.aporte_externo_ars, 600000.0)

    def test_prompt_yes_no_retries_until_valid_answer(self) -> None:
        with patch("builtins.input", side_effect=["quizas", "s"]), patch("builtins.print") as print_mock:
            result = prompt_yes_no("Confirmar?", default=False)

        self.assertTrue(result)
        print_mock.assert_called_with("Respuesta invalida. Ingresa 's' o 'n'.")

    def test_prompt_money_ars_retries_on_invalid_and_negative_values(self) -> None:
        with patch("builtins.input", side_effect=["abc", "-5", "$600.000"]), patch("builtins.print") as print_mock:
            result = prompt_money_ars("Monto")

        self.assertEqual(result, 600000.0)
        self.assertEqual(print_mock.call_count, 2)

    def test_build_real_bonistas_bundle_delegates_to_split_module(self) -> None:
        df_bonos = pd.DataFrame(
            [
                {"Ticker_IOL": "GD30", "Tipo": "Bono", "Bloque": "Soberano AR", "asset_subfamily": "bond_sov_ar", "Peso_%": 3.62}
            ]
        )
        expected = {"bond_monitor": pd.DataFrame([{"Ticker_IOL": "GD30"}])}
        with patch("generate_real_report.build_real_bonistas_bundle_impl", return_value=expected) as impl_mock:
            bundle = build_real_bonistas_bundle(df_bonos, mep_real=1434.0)

        self.assertIs(bundle, expected)
        impl_mock.assert_called_once()
        self.assertTrue(impl_mock.call_args.args[0].equals(df_bonos))
        self.assertEqual(impl_mock.call_args.kwargs["mep_real"], 1434.0)

    def test_enrich_real_cedears_delegates_to_split_module(self) -> None:
        df_cedears = pd.DataFrame(
            [
                {"Ticker_IOL": "AAPL", "Ticker_Finviz": "AAPL", "Precio_ARS": 1200.0},
                {"Ticker_IOL": "KO", "Ticker_Finviz": "KO", "Precio_ARS": 540.0},
            ]
        )
        expected = (pd.DataFrame(), pd.DataFrame(), {"cedears_total": 2})
        with patch("generate_real_report.enrich_real_cedears_impl", return_value=expected) as impl_mock:
            result = enrich_real_cedears(df_cedears, mep_real=1200.0)

        self.assertIs(result, expected)
        impl_mock.assert_called_once()
        self.assertTrue(impl_mock.call_args.args[0].equals(df_cedears))
        self.assertEqual(impl_mock.call_args.kwargs["mep_real"], 1200.0)

    def test_enrich_real_cedears_passes_runtime_dependencies(self) -> None:
        df_cedears = pd.DataFrame([{"Ticker_IOL": "AAPL", "Ticker_Finviz": "AAPL"}])
        with patch("generate_real_report.enrich_real_cedears_impl", return_value=(pd.DataFrame(), pd.DataFrame(), {})) as impl_mock:
            _ = enrich_real_cedears(df_cedears, mep_real=1200.0)

        self.assertEqual(impl_mock.call_args.kwargs["fetch_finviz_bundle_fn"].__name__, "fetch_finviz_bundle")
        self.assertEqual(impl_mock.call_args.kwargs["thread_pool_executor_cls"].__name__, "ThreadPoolExecutor")

    def test_real_report_bond_context_columns_include_bcra_macro_fields(self) -> None:
        bond_analytics = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "GD30",
                    "bonistas_local_subfamily": "bond_hard_dollar",
                    "bonistas_tir_pct": 7.8,
                    "bonistas_paridad_pct": 87.2,
                    "bonistas_md": 2.05,
                    "bonistas_days_to_maturity": 1556,
                    "bonistas_tir_vs_avg_365d_pct": -2.7,
                    "bonistas_parity_gap_pct": -12.8,
                    "bonistas_put_flag": False,
                    "bonistas_riesgo_pais_bps": 609.0,
                    "bonistas_reservas_bcra_musd": 43381.0,
                    "bonistas_a3500_mayorista": 1387.72,
                    "bonistas_rem_inflacion_mensual_pct": 2.7,
                    "bonistas_rem_inflacion_12m_pct": 22.2,
                    "bonistas_ust_5y_pct": 3.94,
                    "bonistas_ust_10y_pct": 4.31,
                    "bonistas_spread_vs_ust_pct": 3.9,
                }
            ]
        )
        final_decision = pd.DataFrame([{"Ticker_IOL": "GD30"}])
        bond_context_cols = [
            "Ticker_IOL",
            "bonistas_local_subfamily",
            "bonistas_tir_pct",
            "bonistas_paridad_pct",
            "bonistas_md",
            "bonistas_days_to_maturity",
            "bonistas_tir_vs_avg_365d_pct",
            "bonistas_parity_gap_pct",
            "bonistas_put_flag",
            "bonistas_riesgo_pais_bps",
            "bonistas_reservas_bcra_musd",
            "bonistas_a3500_mayorista",
            "bonistas_rem_inflacion_mensual_pct",
            "bonistas_rem_inflacion_12m_pct",
            "bonistas_ust_5y_pct",
            "bonistas_ust_10y_pct",
            "bonistas_spread_vs_ust_pct",
        ]

        merged = final_decision.merge(
            bond_analytics[[col for col in bond_context_cols if col in bond_analytics.columns]].copy(),
            on="Ticker_IOL",
            how="left",
        )

        self.assertEqual(merged.loc[0, "bonistas_reservas_bcra_musd"], 43381.0)
        self.assertAlmostEqual(merged.loc[0, "bonistas_a3500_mayorista"], 1387.72, places=2)

    def test_load_previous_portfolio_snapshot_picks_latest_prior_day(self) -> None:
        snapshots_dir = ROOT / "tmp_snapshots_picks_latest"
        snapshots_dir.mkdir(exist_ok=True)
        csv_path = snapshots_dir / "2026-04-15_real_portfolio_master.csv"
        csv_path.write_text("Ticker_IOL,Tipo\nGD30,BONO\n", encoding="utf-8")
        self.addCleanup(lambda: snapshots_dir.rmdir())
        self.addCleanup(lambda: csv_path.unlink(missing_ok=True))

        previous_df, previous_date = load_previous_portfolio_snapshot(
            pd.Timestamp("2026-04-16"),
            snapshots_dir=snapshots_dir,
        )

        self.assertEqual(previous_date, "2026-04-15")
        self.assertFalse(previous_df.empty)

    def test_legacy_snapshots_enabled_can_be_disabled_from_env(self) -> None:
        with patch.dict("os.environ", {"ENABLE_LEGACY_SNAPSHOTS": "0"}, clear=False):
            self.assertFalse(legacy_snapshots_enabled())

        with patch.dict("os.environ", {"ENABLE_LEGACY_SNAPSHOTS": "1"}, clear=False):
            self.assertTrue(legacy_snapshots_enabled())

    def test_load_previous_portfolio_snapshot_warns_when_using_legacy_dir(self) -> None:
        legacy_dir = ROOT / "tmp_snapshots_legacy"
        primary_dir = ROOT / "tmp_snapshots_primary_empty"
        legacy_dir.mkdir(exist_ok=True)
        primary_dir.mkdir(exist_ok=True)
        csv_path = legacy_dir / "2026-04-15_real_portfolio_master.csv"
        csv_path.write_text("Ticker_IOL,Tipo\nGD30,BONO\n", encoding="utf-8")
        self.addCleanup(lambda: legacy_dir.rmdir())
        self.addCleanup(lambda: primary_dir.rmdir())
        self.addCleanup(lambda: csv_path.unlink(missing_ok=True))

        with patch.dict("os.environ", {"ENABLE_LEGACY_SNAPSHOTS": "1"}, clear=False), patch(
            "generate_real_report.LEGACY_SNAPSHOTS_DIR", legacy_dir
        ), patch(
            "generate_real_report.SNAPSHOTS_DIR", primary_dir
        ), patch(
            "generate_real_report.logger.warning"
        ) as warning_mock:
            previous_df, previous_date = load_previous_portfolio_snapshot(pd.Timestamp("2026-04-16"))

        self.assertEqual(previous_date, "2026-04-15")
        self.assertFalse(previous_df.empty)
        warning_mock.assert_called()

    def test_load_previous_portfolio_snapshot_can_skip_legacy_dir(self) -> None:
        with patch.dict("os.environ", {"ENABLE_LEGACY_SNAPSHOTS": "0"}, clear=False):
            previous_df, previous_date = load_previous_portfolio_snapshot(pd.Timestamp("2026-04-16"))

        self.assertTrue(previous_df.empty)
        self.assertIsNone(previous_date)

    def test_load_previous_portfolio_snapshot_skips_invalid_schema(self) -> None:
        snapshots_dir = ROOT / "tmp_snapshots_schema"
        snapshots_dir.mkdir(exist_ok=True)
        invalid_path = snapshots_dir / "2026-04-15_real_portfolio_master.csv"
        valid_path = snapshots_dir / "2026-04-14_real_portfolio_master.csv"
        invalid_path.write_text("Ticker,Tipo\nGOOGL,CEDEAR\n", encoding="utf-8")
        valid_path.write_text("Ticker_IOL,Tipo\nGOOGL,CEDEAR\n", encoding="utf-8")
        self.addCleanup(lambda: snapshots_dir.rmdir())
        self.addCleanup(lambda: [path.unlink(missing_ok=True) for path in snapshots_dir.glob("*")])
        self.addCleanup(lambda: valid_path.unlink(missing_ok=True))
        self.addCleanup(lambda: invalid_path.unlink(missing_ok=True))

        previous_df, previous_date = load_previous_portfolio_snapshot(
            pd.Timestamp("2026-04-16"),
            snapshots_dir=snapshots_dir,
        )

        self.assertEqual(previous_date, "2026-04-14")
        self.assertFalse(previous_df.empty)
        self.assertIn("Ticker_IOL", previous_df.columns)

    def test_load_previous_portfolio_snapshot_skips_corrupt_csv(self) -> None:
        snapshots_dir = ROOT / "tmp_snapshots_corrupt"
        snapshots_dir.mkdir(exist_ok=True)
        corrupt_path = snapshots_dir / "2026-04-15_real_portfolio_master.csv"
        valid_path = snapshots_dir / "2026-04-14_real_portfolio_master.csv"
        corrupt_path.write_bytes(b"\x00\x01\x02\x03")
        valid_path.write_text("Ticker_IOL,Tipo\nGOOGL,CEDEAR\n", encoding="utf-8")
        self.addCleanup(lambda: snapshots_dir.rmdir())
        self.addCleanup(lambda: [path.unlink(missing_ok=True) for path in snapshots_dir.glob("*")])
        self.addCleanup(lambda: valid_path.unlink(missing_ok=True))
        self.addCleanup(lambda: corrupt_path.unlink(missing_ok=True))

        previous_df, previous_date = load_previous_portfolio_snapshot(
            pd.Timestamp("2026-04-16"),
            snapshots_dir=snapshots_dir,
        )

        self.assertEqual(previous_date, "2026-04-14")
        self.assertFalse(previous_df.empty)

    def test_load_previous_portfolio_snapshot_skips_snapshot_without_usable_tickers(self) -> None:
        snapshots_dir = ROOT / "tmp_snapshots_empty_tickers"
        snapshots_dir.mkdir(exist_ok=True)
        invalid_path = snapshots_dir / "2026-04-15_real_portfolio_master.csv"
        valid_path = snapshots_dir / "2026-04-14_real_portfolio_master.csv"
        invalid_path.write_text("Ticker_IOL,Tipo\n,CEDEAR\n   ,Bono\n", encoding="utf-8")
        valid_path.write_text("Ticker_IOL,Tipo\nGOOGL,CEDEAR\n", encoding="utf-8")
        self.addCleanup(lambda: snapshots_dir.rmdir())
        self.addCleanup(lambda: [path.unlink(missing_ok=True) for path in snapshots_dir.glob("*")])
        self.addCleanup(lambda: valid_path.unlink(missing_ok=True))
        self.addCleanup(lambda: invalid_path.unlink(missing_ok=True))

        previous_df, previous_date = load_previous_portfolio_snapshot(
            pd.Timestamp("2026-04-16"),
            snapshots_dir=snapshots_dir,
        )

        self.assertEqual(previous_date, "2026-04-14")
        self.assertFalse(previous_df.empty)
        self.assertEqual(previous_df["Ticker_IOL"].tolist(), ["GOOGL"])

    def test_load_previous_portfolio_snapshot_coerces_optional_numeric_columns(self) -> None:
        snapshots_dir = ROOT / "tmp_snapshots_numeric"
        snapshots_dir.mkdir(exist_ok=True)
        snapshot_path = snapshots_dir / "2026-04-15_real_portfolio_master.csv"
        snapshot_path.write_text(
            "Ticker_IOL,Tipo,Peso_%,Valorizado_ARS,Cantidad,Cantidad_Real\n"
            "GOOGL,CEDEAR,1.25,285940,14,14\n"
            "AL30,Bono,no-num,621209,133,133\n",
            encoding="utf-8",
        )
        self.addCleanup(lambda: snapshots_dir.rmdir())
        self.addCleanup(lambda: [path.unlink(missing_ok=True) for path in snapshots_dir.glob("*")])
        self.addCleanup(lambda: snapshot_path.unlink(missing_ok=True))

        previous_df, previous_date = load_previous_portfolio_snapshot(
            pd.Timestamp("2026-04-16"),
            snapshots_dir=snapshots_dir,
        )

        self.assertEqual(previous_date, "2026-04-15")
        self.assertFalse(previous_df.empty)
        self.assertAlmostEqual(float(previous_df.loc[0, "Peso_%"]), 1.25, places=2)
        self.assertTrue(pd.isna(previous_df.loc[1, "Peso_%"]))
        self.assertEqual(float(previous_df.loc[0, "Cantidad_Real"]), 14.0)


if __name__ == "__main__":
    unittest.main()
