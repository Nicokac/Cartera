import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from generate_real_report_bonistas import build_real_bonistas_bundle_impl
from generate_real_report_cli import (
    load_local_env_impl,
    prompt_money_ars_impl,
    prompt_yes_no_impl,
    resolve_iol_credentials_impl,
)
from generate_real_report_runtime import (
    _enrich_cedear_row_payload_impl,
    enrich_real_cedears_impl,
    extract_operation_quote_tickers_impl,
    fetch_iol_payloads_impl,
    fetch_prices_impl,
    parse_finviz_number_impl,
    parse_finviz_pct_impl,
)
from generate_real_report_snapshots import (
    _load_snapshot_csv_impl,
    load_previous_portfolio_snapshot_impl,
    write_real_snapshots_impl,
)


def _http_error(status_code: int) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status_code
    return requests.HTTPError(response=response)


class GenerateRealReportSplitModulesTests(unittest.TestCase):
    def test_load_local_env_impl_returns_empty_when_file_missing(self) -> None:
        loaded = load_local_env_impl(ROOT / "tmp_missing_env_file.env", environ={})
        self.assertEqual(loaded, {})

    def test_load_local_env_impl_keeps_existing_env_values(self) -> None:
        env_path = ROOT / "tmp_split_test.env"
        env_path.write_text(
            "export IOL_USERNAME=user@test.com\n"
            "IOL_PASSWORD='top-secret'\n"
            "INVALID_LINE\n",
            encoding="utf-8",
        )
        self.addCleanup(lambda: env_path.unlink(missing_ok=True))

        environ = {"IOL_USERNAME": "already@set.com"}
        loaded = load_local_env_impl(env_path, environ=environ)

        self.assertEqual(loaded["IOL_USERNAME"], "user@test.com")
        self.assertEqual(loaded["IOL_PASSWORD"], "top-secret")
        self.assertEqual(environ["IOL_USERNAME"], "already@set.com")
        self.assertEqual(environ["IOL_PASSWORD"], "top-secret")

    def test_resolve_iol_credentials_impl_raises_in_non_interactive_when_missing(self) -> None:
        with self.assertRaisesRegex(ValueError, "Usuario IOL faltante"):
            resolve_iol_credentials_impl(
                username_override="",
                password_override="",
                non_interactive=True,
                load_local_env_fn=lambda: {},
                environ={},
                input_fn=lambda _x: "",
                getpass_fn=lambda _x: "",
                print_fn=lambda _x: None,
            )

    def test_resolve_iol_credentials_impl_raises_for_missing_password_in_non_interactive(self) -> None:
        with self.assertRaisesRegex(ValueError, "Password IOL faltante"):
            resolve_iol_credentials_impl(
                username_override="user@example.com",
                password_override="",
                non_interactive=True,
                load_local_env_fn=lambda: {},
                environ={},
                input_fn=lambda _x: "",
                getpass_fn=lambda _x: "",
                print_fn=lambda _x: None,
            )

    def test_resolve_iol_credentials_impl_prompts_for_missing_values(self) -> None:
        input_mock = Mock(return_value="prompt-user@example.com")
        getpass_mock = Mock(return_value="prompt-pass")
        print_mock = Mock()

        username, password = resolve_iol_credentials_impl(
            username_override="",
            password_override="",
            non_interactive=False,
            load_local_env_fn=lambda: {},
            environ={},
            input_fn=input_mock,
            getpass_fn=getpass_mock,
            print_fn=print_mock,
        )

        self.assertEqual(username, "prompt-user@example.com")
        self.assertEqual(password, "prompt-pass")
        print_mock.assert_not_called()

    def test_prompt_helpers_cover_default_and_negative_paths(self) -> None:
        result_default = prompt_yes_no_impl(
            "Confirmar?",
            default=True,
            input_fn=lambda _msg: "",
            print_fn=lambda _msg: None,
        )
        self.assertTrue(result_default)

        result_no = prompt_yes_no_impl(
            "Confirmar?",
            default=False,
            input_fn=lambda _msg: "no",
            print_fn=lambda _msg: None,
        )
        self.assertFalse(result_no)

        result_money = prompt_money_ars_impl(
            "Monto",
            input_fn=Mock(side_effect=["-10", ""]),
            print_fn=lambda _msg: None,
        )
        self.assertEqual(result_money, 0.0)

    def test_resolve_iol_credentials_impl_raises_when_prompt_returns_empty(self) -> None:
        with self.assertRaisesRegex(ValueError, "obligatorios"):
            resolve_iol_credentials_impl(
                username_override="",
                password_override="",
                non_interactive=False,
                load_local_env_fn=lambda: {},
                environ={},
                input_fn=lambda _x: " ",
                getpass_fn=lambda _x: " ",
                print_fn=lambda _x: None,
            )

    def test_load_local_env_impl_skips_empty_key_assignment(self) -> None:
        env_path = ROOT / "tmp_split_test_empty_key.env"
        env_path.write_text(" =value\n", encoding="utf-8")
        self.addCleanup(lambda: env_path.unlink(missing_ok=True))
        loaded = load_local_env_impl(env_path, environ={})
        self.assertEqual(loaded, {})

    def test_extract_operation_quote_tickers_impl_applies_filters_and_limit(self) -> None:
        operations = [
            {"tipo": "Compra", "estado": "terminada", "simbolo": "AAPL"},
            {"tipo": "Venta", "estado": "terminada", "simbolo": "KO"},
            {"tipo": "Compra", "estado": "pendiente", "simbolo": "MSFT"},
            {"tipo": "Transferencia", "estado": "terminada", "simbolo": "TSLA"},
            {"tipo": "Compra", "estado": "terminada", "simbolo": "AAPL"},
        ]
        tickers = extract_operation_quote_tickers_impl(operations, limit=2)
        self.assertEqual(tickers, ["AAPL", "KO"])

    def test_extract_operation_quote_tickers_impl_returns_empty_for_none(self) -> None:
        self.assertEqual(extract_operation_quote_tickers_impl(None), [])

    def test_extract_operation_quote_tickers_impl_skips_non_matching_rows(self) -> None:
        operations = [{"tipo": "Transferencia", "estado": "pendiente", "simbolo": "AAPL"}]
        self.assertEqual(extract_operation_quote_tickers_impl(operations), [])

    def test_parse_finviz_helpers_return_nan_for_invalid_tokens(self) -> None:
        logger = logging.getLogger("test.parse")
        self.assertTrue(pd.isna(parse_finviz_number_impl("abc", logger=logger)))
        self.assertTrue(pd.isna(parse_finviz_pct_impl("bad%", logger=logger)))

    def test_fetch_prices_impl_handles_404_and_missing_price(self) -> None:
        calls = {"n": 0}

        def _quote_fn(ticker: str, token: str, **_kwargs):
            calls["n"] += 1
            if ticker == "MISS404":
                raise _http_error(404)
            if ticker == "NOPRICE":
                return {}, token + "_x"
            return {"ultimoPrecio": 123.45}, token + "_ok"

        printed: list[str] = []
        prices, new_token = fetch_prices_impl(
            ["MISS404", "NOPRICE", "AAPL"],
            token="tok",
            username="u",
            password="p",
            iol_get_quote_with_reauth_fn=_quote_fn,
            base_url="https://example.test",
            market="bCBA",
            logger=logging.getLogger("test.fetch_prices"),
            print_fn=printed.append,
        )

        self.assertEqual(calls["n"], 3)
        self.assertIn("AAPL", prices)
        self.assertNotIn("MISS404", prices)
        self.assertNotIn("NOPRICE", prices)
        self.assertEqual(new_token, "tok_x_ok")
        self.assertTrue(any("404" in msg for msg in printed))
        self.assertTrue(any("ultimoPrecio ausente" in msg for msg in printed))

    def test_fetch_prices_impl_raises_on_non_404_http_error(self) -> None:
        def _quote_fn(_ticker: str, _token: str, **_kwargs):
            raise _http_error(500)

        with self.assertRaises(requests.HTTPError):
            fetch_prices_impl(
                ["AAPL"],
                token="tok",
                username="u",
                password="p",
                iol_get_quote_with_reauth_fn=_quote_fn,
                base_url="https://example.test",
                market="bCBA",
                logger=logging.getLogger("test.fetch_prices.non404"),
                print_fn=lambda _msg: None,
            )

    def test_fetch_iol_payloads_impl_reauthenticates_on_401(self) -> None:
        state = {"first": True}

        def _portafolio(token: str, **_kwargs):
            if state["first"]:
                state["first"] = False
                raise _http_error(401)
            return {"activos": [{"titulo": {"simbolo": "AAPL"}}], "token": token}

        def _estado(_token: str, **_kwargs):
            return {"ok": True}

        def _ops(_token: str, **_kwargs):
            return [{"tipo": "Compra"}]

        login_mock = Mock(return_value="new-token")
        portfolio, estado, ops, token = fetch_iol_payloads_impl(
            token="expired-token",
            username="user",
            password="pass",
            iol_get_portafolio_fn=_portafolio,
            iol_get_estado_cuenta_fn=_estado,
            iol_get_operaciones_fn=_ops,
            iol_login_fn=login_mock,
            base_url="https://example.test",
            logger=logging.getLogger("test.fetch_iol_payloads"),
        )

        self.assertEqual(token, "new-token")
        self.assertIn("activos", portfolio)
        self.assertTrue(estado["ok"])
        self.assertEqual(len(ops), 1)
        login_mock.assert_called_once()

    def test_fetch_iol_payloads_impl_returns_without_reauth_when_token_is_valid(self) -> None:
        login_mock = Mock(return_value="should-not-be-used")
        portfolio, estado, ops, token = fetch_iol_payloads_impl(
            token="valid-token",
            username="user",
            password="pass",
            iol_get_portafolio_fn=lambda _t, **_kwargs: {"activos": []},
            iol_get_estado_cuenta_fn=lambda _t, **_kwargs: {"ok": True},
            iol_get_operaciones_fn=lambda _t, **_kwargs: [],
            iol_login_fn=login_mock,
            base_url="https://example.test",
            logger=logging.getLogger("test.fetch_iol_payloads.valid"),
        )
        self.assertEqual(token, "valid-token")
        self.assertIn("activos", portfolio)
        self.assertTrue(estado["ok"])
        self.assertEqual(ops, [])
        login_mock.assert_not_called()

    def test_fetch_iol_payloads_impl_raises_non_401_http_error(self) -> None:
        def _portafolio(_t: str, **_kwargs):
            raise _http_error(500)

        with self.assertRaises(requests.HTTPError):
            fetch_iol_payloads_impl(
                token="tok",
                username="user",
                password="pass",
                iol_get_portafolio_fn=_portafolio,
                iol_get_estado_cuenta_fn=lambda _t, **_kwargs: {"ok": True},
                iol_get_operaciones_fn=lambda _t, **_kwargs: [],
                iol_login_fn=lambda *_args, **_kwargs: "new-token",
                base_url="https://example.test",
                logger=logging.getLogger("test.fetch_iol_payloads.non401"),
            )

    def test_enrich_real_cedears_impl_returns_empty_stats_for_empty_df(self) -> None:
        enriched, ratings, stats = enrich_real_cedears_impl(
            pd.DataFrame(),
            mep_real=1200.0,
            fetch_finviz_bundle_fn=lambda _ticker: {},
            finviz_max_workers=2,
            finviz_worker_timeout_seconds=5.0,
            finviz_submit_delay_seconds=0.0,
            thread_pool_executor_cls=Mock(),
            logger=logging.getLogger("test.enrich"),
        )
        self.assertTrue(enriched.empty)
        self.assertTrue(ratings.empty)
        self.assertEqual(stats["cedears_total"], 0)
        self.assertEqual(stats["fundamentals_covered"], 0)
        self.assertEqual(stats["ratings_covered"], 0)
        self.assertEqual(stats["errors"], [])

    def test_enrich_real_cedears_impl_parallel_fetch_preserves_outputs(self) -> None:
        df_cedears = pd.DataFrame(
            [
                {"Ticker_IOL": "AAPL", "Ticker_Finviz": "AAPL", "Precio_ARS": 1200.0},
                {"Ticker_IOL": "KO", "Ticker_Finviz": "KO", "Precio_ARS": 540.0},
            ]
        )

        def fake_bundle(ticker: str) -> dict[str, object]:
            if ticker == "AAPL":
                return {
                    "fundamentals": {"Perf Week": "1.5%", "Beta": "1.2", "P/E": "28", "ROE": "20%", "Profit Margin": "25%"},
                    "ratings": pd.DataFrame([{"Rating": "Buy"}, {"Rating": "Buy"}, {"Rating": "Hold"}]),
                }
            return {
                "fundamentals": {"Perf Month": "2.0%", "Beta": "0.7", "P/E": "22", "ROE": "18%", "Profit Margin": "21%"},
                "ratings": pd.DataFrame([{"Action": "Hold"}, {"Action": "Hold"}]),
            }

        enriched, ratings, stats = enrich_real_cedears_impl(
            df_cedears,
            mep_real=1200.0,
            fetch_finviz_bundle_fn=fake_bundle,
            finviz_max_workers=2,
            finviz_worker_timeout_seconds=10.0,
            finviz_submit_delay_seconds=0.0,
            thread_pool_executor_cls=__import__("concurrent.futures").futures.ThreadPoolExecutor,
            logger=logging.getLogger("test.enrich.parallel"),
        )

        self.assertEqual(stats["cedears_total"], 2)
        self.assertEqual(stats["fundamentals_covered"], 2)
        self.assertEqual(stats["ratings_covered"], 2)
        self.assertEqual(stats["errors"], [])
        self.assertAlmostEqual(enriched.loc[0, "MEP_Implicito"], 1.0, places=4)
        self.assertAlmostEqual(enriched.loc[1, "MEP_Implicito"], 0.45, places=4)
        self.assertEqual(ratings.loc["AAPL", "consenso"], "Buy")
        self.assertEqual(ratings.loc["KO", "consenso"], "Hold")

    def test_enrich_real_cedears_impl_keeps_per_ticker_errors(self) -> None:
        df_cedears = pd.DataFrame(
            [
                {"Ticker_IOL": "AAPL", "Ticker_Finviz": "AAPL", "Precio_ARS": 1200.0},
                {"Ticker_IOL": "KO", "Ticker_Finviz": "KO", "Precio_ARS": 540.0},
            ]
        )

        def fake_bundle(ticker: str) -> dict[str, object]:
            if ticker == "AAPL":
                raise RuntimeError("timeout")
            return {
                "fundamentals": {"Perf Week": "1.0%", "Beta": "0.7"},
                "ratings": pd.DataFrame([{"Status": "Hold"}]),
            }

        enriched, ratings, stats = enrich_real_cedears_impl(
            df_cedears,
            mep_real=1200.0,
            fetch_finviz_bundle_fn=fake_bundle,
            finviz_max_workers=2,
            finviz_worker_timeout_seconds=10.0,
            finviz_submit_delay_seconds=0.0,
            thread_pool_executor_cls=__import__("concurrent.futures").futures.ThreadPoolExecutor,
            logger=logging.getLogger("test.enrich.errors"),
        )

        self.assertEqual(stats["fundamentals_covered"], 1)
        self.assertEqual(stats["ratings_covered"], 1)
        self.assertEqual(len(stats["errors"]), 1)
        self.assertIn("AAPL: timeout", stats["errors"][0])
        self.assertTrue(pd.isna(enriched.loc[0, "Beta"]))
        self.assertEqual(ratings.loc["KO", "consenso"], "Hold")

    def test_enrich_real_cedears_impl_marks_timeout_when_future_not_done(self) -> None:
        from concurrent.futures import Future

        df_cedears = pd.DataFrame(
            [
                {"Ticker_IOL": "AAPL", "Ticker_Finviz": "AAPL", "Precio_ARS": 1200.0},
                {"Ticker_IOL": "KO", "Ticker_Finviz": "KO", "Precio_ARS": 540.0},
            ]
        )
        finished = Future()
        finished.set_result(
            (
                0,
                {"Perf Week": 1.5, "Beta": 1.2, "MEP_Implicito": 1.0},
                {"Ticker_Finviz": "AAPL", "consenso": "Buy", "consenso_n": 1, "total_ratings": 1},
                None,
            )
        )
        pending = Future()

        class FakeExecutor:
            def __init__(self, *_args, **_kwargs) -> None:
                self._futures = [finished, pending]

            def submit(self, *_args, **_kwargs):
                return self._futures.pop(0)

            def shutdown(self, *args, **kwargs) -> None:
                return None

        enriched, ratings, stats = enrich_real_cedears_impl(
            df_cedears,
            mep_real=1200.0,
            fetch_finviz_bundle_fn=lambda _ticker: {},
            finviz_max_workers=2,
            finviz_worker_timeout_seconds=7.0,
            finviz_submit_delay_seconds=0.0,
            thread_pool_executor_cls=FakeExecutor,
            wait_fn=lambda _futures, timeout: ({finished}, {pending}),
            logger=logging.getLogger("test.enrich.timeout"),
        )

        self.assertEqual(stats["fundamentals_covered"], 1)
        self.assertEqual(stats["ratings_covered"], 1)
        self.assertIn("KO: timeout after 7s", stats["errors"])
        self.assertEqual(ratings.loc["AAPL", "consenso"], "Buy")
        self.assertTrue(pd.isna(enriched.loc[1, "Beta"]))

    def test_enrich_real_cedears_impl_uses_submit_delay(self) -> None:
        from concurrent.futures import Future

        df_cedears = pd.DataFrame(
            [
                {"Ticker_IOL": "AAPL", "Ticker_Finviz": "AAPL", "Precio_ARS": 1200.0},
                {"Ticker_IOL": "KO", "Ticker_Finviz": "KO", "Precio_ARS": 540.0},
            ]
        )
        finished_a = Future()
        finished_a.set_result((0, {}, None, None))
        finished_b = Future()
        finished_b.set_result((1, {}, None, None))

        class FakeExecutor:
            def __init__(self, *_args, **_kwargs) -> None:
                self._futures = [finished_a, finished_b]

            def submit(self, *_args, **_kwargs):
                return self._futures.pop(0)

            def shutdown(self, *args, **kwargs) -> None:
                return None

        sleep_mock = Mock()
        _enriched, _ratings, _stats = enrich_real_cedears_impl(
            df_cedears,
            mep_real=1200.0,
            fetch_finviz_bundle_fn=lambda _ticker: {},
            finviz_max_workers=2,
            finviz_worker_timeout_seconds=7.0,
            finviz_submit_delay_seconds=0.25,
            thread_pool_executor_cls=FakeExecutor,
            wait_fn=lambda _futures, timeout: ({finished_a, finished_b}, set()),
            sleep_fn=sleep_mock,
            logger=logging.getLogger("test.enrich.delay"),
        )

        sleep_mock.assert_called_once_with(0.25)

    def test_enrich_cedear_row_payload_impl_handles_missing_ticker_and_bad_mep(self) -> None:
        idx, updates, rating_row, error = _enrich_cedear_row_payload_impl(
            1,
            row_data={},
            mep_real=1200.0,
            fetch_finviz_bundle_fn=lambda _ticker: {},
            parse_finviz_pct_fn=lambda _value: float("nan"),
            parse_finviz_number_fn=lambda _value: float("nan"),
            logger=logging.getLogger("test.enrich.row.missing"),
        )
        self.assertEqual(idx, 1)
        self.assertEqual(updates, {})
        self.assertIsNone(rating_row)
        self.assertIsNone(error)

        idx2, updates2, _rating2, error2 = _enrich_cedear_row_payload_impl(
            2,
            row_data={"Ticker_Finviz": "AAPL", "Precio_ARS": "invalid"},
            mep_real=1200.0,
            fetch_finviz_bundle_fn=lambda _ticker: {"fundamentals": {}, "ratings": pd.DataFrame()},
            parse_finviz_pct_fn=lambda _value: float("nan"),
            parse_finviz_number_fn=lambda _value: float("nan"),
            logger=logging.getLogger("test.enrich.row.badmep"),
        )
        self.assertEqual(idx2, 2)
        self.assertIn("Perf Week", updates2)
        self.assertIsNone(error2)

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

    def test_build_real_bonistas_bundle_impl_returns_empty_for_empty_inputs(self) -> None:
        base_kwargs = {
            "mep_real": 1400.0,
            "get_bonds_for_portfolio_fn": lambda _tickers: pd.DataFrame(),
            "get_bond_volume_context_fn": lambda _tickers: pd.DataFrame(),
            "get_macro_variables_fn": lambda: {},
            "get_riesgo_pais_latest_fn": lambda **_kwargs: None,
            "riesgo_pais_url": "https://example.test/riesgo",
            "get_rem_latest_fn": lambda **_kwargs: None,
            "rem_url": "https://example.test/rem",
            "rem_xls_url": "https://example.test/rem.xlsx",
            "get_bcra_monetary_context_fn": lambda **_kwargs: {},
            "bcra_monetarias_api_url": "https://example.test/bcra",
            "bcra_reservas_id": 1,
            "bcra_a3500_id": 2,
            "bcra_badlar_tna_id": 3,
            "bcra_badlar_tea_id": 4,
            "get_ust_latest_fn": lambda: None,
            "enrich_bond_analytics_fn": lambda *_args, **_kwargs: pd.DataFrame(),
            "build_bond_monitor_table_fn": lambda _df: pd.DataFrame(),
            "build_bond_subfamily_summary_fn": lambda _df: pd.DataFrame(),
            "build_bond_local_subfamily_summary_fn": lambda _df: pd.DataFrame(),
            "logger": logging.getLogger("test.bonistas.empty"),
            "print_fn": lambda _msg: None,
        }

        self.assertEqual(build_real_bonistas_bundle_impl(pd.DataFrame(), **base_kwargs), {})
        self.assertEqual(build_real_bonistas_bundle_impl(pd.DataFrame([{"Ticker_IOL": "   "}]), **base_kwargs), {})

    def test_build_real_bonistas_bundle_impl_returns_empty_when_no_data(self) -> None:
        df_bonos = pd.DataFrame([{"Ticker_IOL": "GD30"}])
        bundle = build_real_bonistas_bundle_impl(
            df_bonos,
            mep_real=1400.0,
            get_bonds_for_portfolio_fn=lambda _tickers: pd.DataFrame(),
            get_bond_volume_context_fn=lambda _tickers: pd.DataFrame(),
            get_macro_variables_fn=lambda: {},
            get_riesgo_pais_latest_fn=lambda **_kwargs: None,
            riesgo_pais_url="https://example.test/riesgo",
            get_rem_latest_fn=lambda **_kwargs: None,
            rem_url="https://example.test/rem",
            rem_xls_url="https://example.test/rem.xlsx",
            get_bcra_monetary_context_fn=lambda **_kwargs: {},
            bcra_monetarias_api_url="https://example.test/bcra",
            bcra_reservas_id=1,
            bcra_a3500_id=2,
            bcra_badlar_tna_id=3,
            bcra_badlar_tea_id=4,
            get_ust_latest_fn=lambda: None,
            enrich_bond_analytics_fn=lambda *_args, **_kwargs: pd.DataFrame(),
            build_bond_monitor_table_fn=lambda _df: pd.DataFrame(),
            build_bond_subfamily_summary_fn=lambda _df: pd.DataFrame(),
            build_bond_local_subfamily_summary_fn=lambda _df: pd.DataFrame(),
            logger=logging.getLogger("test.bonistas"),
            print_fn=lambda _msg: None,
        )
        self.assertEqual(bundle, {})

    def test_build_real_bonistas_bundle_impl_happy_path_populates_macro_fields(self) -> None:
        df_bonos = pd.DataFrame(
            [
                {"Ticker_IOL": "GD30", "Tipo": "Bono", "Bloque": "Soberano AR", "asset_subfamily": "bond_sov_ar", "Peso_%": 3.62}
            ]
        )
        bundle = build_real_bonistas_bundle_impl(
            df_bonos,
            mep_real=1434.0,
            get_bonds_for_portfolio_fn=lambda _tickers: pd.DataFrame([{"bonistas_ticker": "GD30"}]),
            get_bond_volume_context_fn=lambda _tickers: pd.DataFrame(
                [
                    {
                        "Ticker_IOL": "GD30",
                        "bonistas_volume_last": 1500000.0,
                        "bonistas_volume_avg_20d": 1200000.0,
                        "bonistas_volume_ratio": 1.25,
                        "bonistas_liquidity_bucket": "alta",
                    }
                ]
            ),
            get_macro_variables_fn=lambda: {"cer_diario": 738.025},
            get_riesgo_pais_latest_fn=lambda **_kwargs: {"valor": 765.0, "fecha": "2026-04-05"},
            riesgo_pais_url="https://example.test/riesgo",
            get_rem_latest_fn=lambda **_kwargs: {
                "inflacion_mensual_pct": 2.7,
                "inflacion_12m_pct": 24.6,
                "periodo": "Febrero De 2026",
                "fecha_publicacion": "5 de marzo de 2026",
            },
            rem_url="https://example.test/rem",
            rem_xls_url="https://example.test/rem.xlsx",
            get_bcra_monetary_context_fn=lambda **_kwargs: {
                "reservas_bcra_musd": 28384.0,
                "a3500_mayorista": 1387.72,
                "badlar": 28.31,
                "tamar": 26.31,
            },
            bcra_monetarias_api_url="https://example.test/bcra",
            bcra_reservas_id=1,
            bcra_a3500_id=2,
            bcra_badlar_tna_id=3,
            bcra_badlar_tea_id=4,
            get_ust_latest_fn=lambda: {
                "ust_date": "2026-04-08",
                "ust_5y_pct": 3.95,
                "ust_10y_pct": 4.33,
                "ust_spread_10y_5y_pct": 0.38,
            },
            enrich_bond_analytics_fn=lambda _df_bonos, _df_bonistas, **_kwargs: _df_bonos.copy(),
            build_bond_monitor_table_fn=lambda _df: pd.DataFrame([{"Ticker_IOL": "GD30"}]),
            build_bond_subfamily_summary_fn=lambda _df: pd.DataFrame([{"asset_subfamily": "bond_sov_ar", "Instrumentos": 1}]),
            build_bond_local_subfamily_summary_fn=lambda _df: pd.DataFrame([{"bonistas_local_subfamily": "bond_hard_dollar", "Instrumentos": 1}]),
            logger=logging.getLogger("test.bonistas.happy"),
            print_fn=lambda _msg: None,
        )
        self.assertIn("bond_monitor", bundle)
        self.assertEqual(bundle["macro_variables"]["cer_diario"], 738.025)
        self.assertEqual(bundle["macro_variables"]["riesgo_pais_bps"], 765.0)
        self.assertEqual(bundle["macro_variables"]["rem_inflacion_mensual_pct"], 2.7)
        self.assertEqual(bundle["macro_variables"]["reservas_bcra_musd"], 28384.0)
        self.assertEqual(bundle["macro_variables"]["ust_status"], "ok")

    def test_build_real_bonistas_bundle_impl_handles_provider_exceptions_and_marks_ust_error(self) -> None:
        printed: list[str] = []
        logger = logging.getLogger("test.bonistas.errors")
        df_bonos = pd.DataFrame([{"Ticker_IOL": "GD30", "Tipo": "Bono"}])

        bundle = build_real_bonistas_bundle_impl(
            df_bonos,
            mep_real=1400.0,
            get_bonds_for_portfolio_fn=lambda _tickers: (_ for _ in ()).throw(RuntimeError("bonistas down")),
            get_bond_volume_context_fn=lambda _tickers: (_ for _ in ()).throw(RuntimeError("pyobd down")),
            get_macro_variables_fn=lambda: (_ for _ in ()).throw(RuntimeError("macro down")),
            get_riesgo_pais_latest_fn=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("riesgo down")),
            riesgo_pais_url="https://example.test/riesgo",
            get_rem_latest_fn=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("rem down")),
            rem_url="https://example.test/rem",
            rem_xls_url="https://example.test/rem.xlsx",
            get_bcra_monetary_context_fn=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("bcra down")),
            bcra_monetarias_api_url="https://example.test/bcra",
            bcra_reservas_id=1,
            bcra_a3500_id=2,
            bcra_badlar_tna_id=3,
            bcra_badlar_tea_id=4,
            get_ust_latest_fn=lambda: (_ for _ in ()).throw(RuntimeError("fred down")),
            enrich_bond_analytics_fn=lambda _df_bonos, _df_bonistas, **_kwargs: _df_bonos.copy(),
            build_bond_monitor_table_fn=lambda _df: pd.DataFrame(),
            build_bond_subfamily_summary_fn=lambda _df: pd.DataFrame(),
            build_bond_local_subfamily_summary_fn=lambda _df: pd.DataFrame(),
            logger=logger,
            print_fn=printed.append,
        )

        self.assertEqual(bundle["macro_variables"]["ust_status"], "error")
        self.assertIn("fred down", bundle["macro_variables"]["ust_error"])
        self.assertTrue(any("no disponible" in msg for msg in printed))

    def test_build_real_bonistas_bundle_impl_uses_volume_frame_when_bonistas_is_empty(self) -> None:
        df_bonos = pd.DataFrame([{"Ticker_IOL": "GD30", "Tipo": "Bono"}])
        bundle = build_real_bonistas_bundle_impl(
            df_bonos,
            mep_real=1400.0,
            get_bonds_for_portfolio_fn=lambda _tickers: pd.DataFrame(),
            get_bond_volume_context_fn=lambda _tickers: pd.DataFrame([{"Ticker_IOL": "GD30", "bonistas_volume_last": 1.0}]),
            get_macro_variables_fn=lambda: {},
            get_riesgo_pais_latest_fn=lambda **_kwargs: None,
            riesgo_pais_url="https://example.test/riesgo",
            get_rem_latest_fn=lambda **_kwargs: None,
            rem_url="https://example.test/rem",
            rem_xls_url="https://example.test/rem.xlsx",
            get_bcra_monetary_context_fn=lambda **_kwargs: {},
            bcra_monetarias_api_url="https://example.test/bcra",
            bcra_reservas_id=1,
            bcra_a3500_id=2,
            bcra_badlar_tna_id=3,
            bcra_badlar_tea_id=4,
            get_ust_latest_fn=lambda: None,
            enrich_bond_analytics_fn=lambda _df_bonos, df_bonistas, **_kwargs: df_bonistas.copy(),
            build_bond_monitor_table_fn=lambda _df: pd.DataFrame(),
            build_bond_subfamily_summary_fn=lambda _df: pd.DataFrame(),
            build_bond_local_subfamily_summary_fn=lambda _df: pd.DataFrame(),
            logger=logging.getLogger("test.bonistas.volume"),
            print_fn=lambda _msg: None,
        )
        self.assertIn("bond_analytics", bundle)
        self.assertFalse(bundle["bond_analytics"].empty)


if __name__ == "__main__":
    unittest.main()
