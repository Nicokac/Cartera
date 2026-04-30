import logging
import json
import sys
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from generate_real_report_runtime import (
    _enrich_cedear_row_payload_impl,
    backup_runtime_csvs_impl,
    enrich_real_cedears_impl,
    extract_operation_quote_tickers_impl,
    fetch_iol_payloads_impl,
    fetch_prices_impl,
    parse_finviz_number_impl,
    parse_finviz_pct_impl,
)


def _http_error(status_code: int) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status_code
    return requests.HTTPError(response=response)


class GenerateRealReportSplitRuntimeTests(unittest.TestCase):
    def test_backup_runtime_csvs_impl_copies_all_csvs_for_date(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "runtime"
            backups = root / "backups"
            runtime.mkdir(parents=True, exist_ok=True)
            (runtime / "decision_history.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            (runtime / "prediction_history.csv").write_text("x,y\n3,4\n", encoding="utf-8")
            (runtime / "ignore.txt").write_text("nope", encoding="utf-8")

            out = backup_runtime_csvs_impl(runtime_dir=runtime, backups_root=backups, run_date=pd.Timestamp("2026-04-28").date())

            self.assertEqual(len(out), 2)
            self.assertTrue((backups / "2026-04-28" / "decision_history.csv").exists())
            self.assertTrue((backups / "2026-04-28" / "prediction_history.csv").exists())
            self.assertFalse((backups / "2026-04-28" / "ignore.txt").exists())

    def test_backup_runtime_csvs_impl_no_runtime_dir_returns_empty(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = backup_runtime_csvs_impl(
                runtime_dir=root / "missing_runtime",
                backups_root=root / "backups",
                run_date=pd.Timestamp("2026-04-28").date(),
            )
            self.assertEqual(out, [])

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

    def test_extract_operation_quote_tickers_impl_skips_non_dict_rows(self) -> None:
        operations = [
            "unexpected",
            {"tipo": "Compra", "estado": "terminada", "simbolo": "AAPL"},
        ]
        self.assertEqual(extract_operation_quote_tickers_impl(operations), ["AAPL"])

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

    def test_fetch_prices_impl_uses_fresh_cache_without_calling_iol(self) -> None:
        with TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "iol_price_cache.json"
            cache_path.write_text(
                json.dumps(
                    {
                        "updated_at": "2026-04-29T12:00:00+00:00",
                        "prices": {"AAPL": 111.11},
                    }
                ),
                encoding="utf-8",
            )

            quote_mock = Mock(side_effect=AssertionError("No deberia consultar IOL con cache fresca"))
            prices, new_token = fetch_prices_impl(
                ["AAPL"],
                token="tok",
                username="u",
                password="p",
                iol_get_quote_with_reauth_fn=quote_mock,
                base_url="https://example.test",
                market="bCBA",
                logger=logging.getLogger("test.fetch_prices.cache_hit"),
                print_fn=lambda _msg: None,
                cache_path=cache_path,
                now_ts=pd.Timestamp("2026-04-29T12:05:00+00:00"),
            )

            self.assertEqual(prices, {"AAPL": 111.11})
            self.assertEqual(new_token, "tok")
            quote_mock.assert_not_called()

    def test_fetch_prices_impl_refetches_when_cache_is_stale(self) -> None:
        with TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "iol_price_cache.json"
            cache_path.write_text(
                json.dumps(
                    {
                        "updated_at": "2026-04-29T11:00:00+00:00",
                        "prices": {"AAPL": 100.0},
                    }
                ),
                encoding="utf-8",
            )

            quote_mock = Mock(return_value=({"ultimoPrecio": 123.45}, "tok2"))
            prices, new_token = fetch_prices_impl(
                ["AAPL"],
                token="tok1",
                username="u",
                password="p",
                iol_get_quote_with_reauth_fn=quote_mock,
                base_url="https://example.test",
                market="bCBA",
                logger=logging.getLogger("test.fetch_prices.cache_stale"),
                print_fn=lambda _msg: None,
                cache_path=cache_path,
                now_ts=pd.Timestamp("2026-04-29T12:00:00+00:00"),
            )

            self.assertEqual(prices, {"AAPL": 123.45})
            self.assertEqual(new_token, "tok2")
            quote_mock.assert_called_once()
            updated = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertEqual(float(updated["prices"]["AAPL"]), 123.45)

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

    def test_fetch_iol_payloads_impl_normalizes_dict_wrapper_operations(self) -> None:
        login_mock = Mock(return_value="should-not-be-used")
        _portfolio, _estado, ops, _token = fetch_iol_payloads_impl(
            token="valid-token",
            username="user",
            password="pass",
            iol_get_portafolio_fn=lambda _t, **_kwargs: {"activos": []},
            iol_get_estado_cuenta_fn=lambda _t, **_kwargs: {"ok": True},
            iol_get_operaciones_fn=lambda _t, **_kwargs: {
                "operaciones": [{"tipo": "Compra"}, "noise", None]
            },
            iol_login_fn=login_mock,
            base_url="https://example.test",
            logger=logging.getLogger("test.fetch_iol_payloads.wrap"),
        )
        self.assertEqual(ops, [{"tipo": "Compra"}])
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


if __name__ == "__main__":
    unittest.main()
