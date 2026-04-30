import sys
import shutil
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from generate_real_report import (
    _build_analysis_context,
    _collect_market_runtime_inputs,
    _log_phase_duration,
    _build_report_payload,
    _build_prediction_accuracy_metrics,
    configure_logging,
    _merge_bond_context_into_decision,
    _enrich_decision_with_temporal_memory,
    _render_and_persist_report,
    _resolve_funding_policy,
    build_real_bonistas_bundle,
    enrich_real_cedears,
    extract_quote_tickers,
    legacy_snapshots_enabled,
    should_use_legacy_snapshots,
    load_previous_portfolio_snapshot,
    load_local_env,
    parse_finviz_number,
    parse_finviz_pct,
    parse_args,
    prompt_money_ars,
    prompt_yes_no,
    resolve_iol_credentials,
    backup_runtime_csvs,
    run_scheduled_real_report,
)


class GenerateRealReportTests(unittest.TestCase):
    def test_build_prediction_accuracy_metrics_computes_global_and_by_family(self) -> None:
        history = pd.DataFrame(
            [
                {"ticker": "AAPL", "asset_family": "stock", "score_unificado": 0.25, "outcome": "up", "correct": True},
                {"ticker": "MSFT", "asset_family": "stock", "score_unificado": -0.22, "outcome": "down", "correct": False},
                {"ticker": "GD30", "asset_family": "bond", "score_unificado": 0.02, "outcome": "neutral", "correct": True},
                {"ticker": "AL30", "asset_family": "bond", "score_unificado": 0.20, "direction": "up", "outcome": "up", "correct": True},
                {"ticker": "AL35", "asset_family": "bond", "score_unificado": -0.20, "direction": "down", "outcome": "down", "correct": True},
                {"ticker": "KO", "asset_family": "stock", "score_unificado": 0.10, "outcome": "", "correct": pd.NA},
            ]
        )

        metrics = _build_prediction_accuracy_metrics(history)

        self.assertEqual(metrics["global"]["completed"], 5)
        self.assertAlmostEqual(float(metrics["global"]["accuracy_pct"]), 80.0, places=3)
        by_family = {row["asset_family"]: row for row in metrics["by_family"]}
        self.assertEqual(by_family["stock"]["completed"], 2)
        self.assertAlmostEqual(float(by_family["stock"]["accuracy_pct"]), 50.0, places=3)
        self.assertEqual(by_family["bond"]["completed"], 3)
        self.assertAlmostEqual(float(by_family["bond"]["accuracy_pct"]), 100.0, places=3)
        by_band = {row["score_band"]: row for row in metrics["by_score_band"]}
        self.assertEqual(by_band["Alto (>= 0.15)"]["completed"], 2)
        self.assertAlmostEqual(float(by_band["Alto (>= 0.15)"]["accuracy_pct"]), 100.0, places=3)
        self.assertEqual(by_band["Bajo (<= -0.15)"]["completed"], 2)
        self.assertAlmostEqual(float(by_band["Bajo (<= -0.15)"]["accuracy_pct"]), 50.0, places=3)
        readiness = {row["asset_family"]: row for row in metrics["calibration_readiness"]}
        self.assertIn("bond", readiness)
        self.assertIn("stock", readiness)
        self.assertFalse(bool(readiness["bond"]["ready"]))

    def test_configure_logging_default_text_format(self) -> None:
        root_logger = Mock()
        root_logger.handlers = []
        with patch("generate_real_report.logging.getLogger", return_value=root_logger), patch(
            "generate_real_report.logging.basicConfig"
        ) as basic_config_mock, patch.dict("generate_real_report.os.environ", {}, clear=False):
            configure_logging()

        basic_config_mock.assert_called_once()
        kwargs = basic_config_mock.call_args.kwargs
        self.assertEqual(kwargs["level"], 20)
        self.assertIn("%(asctime)s", kwargs["format"])

    def test_configure_logging_json_format(self) -> None:
        root_logger = Mock()
        root_logger.handlers = []
        with patch("generate_real_report.logging.getLogger", return_value=root_logger), patch(
            "generate_real_report.logging.basicConfig"
        ) as basic_config_mock, patch.dict("generate_real_report.os.environ", {"LOG_FORMAT": "json"}, clear=False):
            configure_logging()

        basic_config_mock.assert_called_once()
        kwargs = basic_config_mock.call_args.kwargs
        self.assertEqual(kwargs["level"], 20)
        self.assertIn("handlers", kwargs)
        self.assertEqual(len(kwargs["handlers"]), 1)
        self.assertIsNotNone(kwargs["handlers"][0].formatter)

    def test_configure_logging_is_noop_when_root_has_handlers(self) -> None:
        root_logger = Mock()
        root_logger.handlers = [object()]
        with patch("generate_real_report.logging.getLogger", return_value=root_logger), patch(
            "generate_real_report.logging.basicConfig"
        ) as basic_config_mock:
            configure_logging()
        basic_config_mock.assert_not_called()

    def test_log_phase_duration_emits_elapsed_log(self) -> None:
        with patch("generate_real_report.time.perf_counter", side_effect=[10.0, 12.25]), patch(
            "generate_real_report.logger.info"
        ) as info_mock:
            with _log_phase_duration("Demo"):
                pass

        info_mock.assert_called_once_with("Fase %s: %.1fs", "Demo", 2.25)

    def test_backup_runtime_csvs_delegates_to_runtime_impl_with_resolved_date(self) -> None:
        expected = [Path("x.csv")]
        with patch("generate_real_report.backup_runtime_csvs_impl", return_value=expected) as backup_impl_mock:
            out = backup_runtime_csvs(run_date_value="2026-04-28")

        self.assertIs(out, expected)
        backup_impl_mock.assert_called_once()
        self.assertEqual(str(backup_impl_mock.call_args.kwargs["run_date"]), "2026-04-28")

    def test_main_delegates_to_run_real_report(self) -> None:
        args_obj = object()
        with patch("generate_real_report.parse_args", return_value=args_obj) as parse_mock, patch(
            "generate_real_report.run_real_report"
        ) as run_mock:
            from generate_real_report import main

            main(["--non-interactive"])

        parse_mock.assert_called_once_with(["--non-interactive"])
        run_mock.assert_called_once_with(args_obj)

    def test_resolve_funding_policy_uses_args_values_in_non_interactive(self) -> None:
        class Args:
            use_iol_liquidity = True
            aporte_externo_ars = 120000.0
            non_interactive = True

        usar_liquidez_iol, aporte_externo_ars = _resolve_funding_policy(Args())
        self.assertTrue(usar_liquidez_iol)
        self.assertEqual(aporte_externo_ars, 120000.0)

    def test_merge_bond_context_into_decision_adds_available_columns(self) -> None:
        decision_bundle = {"final_decision": pd.DataFrame([{"Ticker_IOL": "GD30", "accion": "Reducir"}])}
        bonistas_bundle = {
            "bond_analytics": pd.DataFrame(
                [
                    {
                        "Ticker_IOL": "GD30",
                        "bonistas_tir_pct": 7.8,
                        "bonistas_paridad_pct": 87.2,
                        "extra": "ignored",
                    }
                ]
            )
        }

        out = _merge_bond_context_into_decision(decision_bundle, bonistas_bundle)
        self.assertIn("bonistas_tir_pct", out["final_decision"].columns)
        self.assertIn("bonistas_paridad_pct", out["final_decision"].columns)
        self.assertNotIn("extra", out["final_decision"].columns)

    def test_enrich_decision_with_temporal_memory_applies_history_retention(self) -> None:
        decision_bundle = {
            "final_decision": pd.DataFrame([{"Ticker_IOL": "AAPL", "accion_sugerida_v2": "Refuerzo"}]),
            "market_regime": {"any_active": False, "active_flags": []},
        }
        history = pd.DataFrame([{"run_date": "2026-01-01", "Ticker_IOL": "AAPL"}])
        observation = pd.DataFrame([{"run_date": "2026-04-29", "Ticker_IOL": "AAPL"}])
        retained_history = pd.DataFrame([{"run_date": "2026-04-29", "Ticker_IOL": "AAPL"}])
        enriched_final = pd.DataFrame([{"Ticker_IOL": "AAPL", "accion_previa": "Refuerzo"}])

        with patch("generate_real_report.load_decision_history", return_value=history), patch(
            "generate_real_report.build_decision_history_observation", return_value=observation
        ), patch(
            "generate_real_report.upsert_daily_decision_history", return_value=observation
        ), patch(
            "generate_real_report.apply_decision_history_retention", return_value=retained_history
        ) as retention_mock, patch(
            "generate_real_report.enrich_with_temporal_memory", return_value=enriched_final
        ), patch(
            "generate_real_report.build_temporal_memory_summary", return_value={"sin_historial": 0}
        ), patch(
            "generate_real_report.save_decision_history"
        ):
            out = _enrich_decision_with_temporal_memory(decision_bundle, run_date="2026-04-29")

        retention_mock.assert_called_once()
        self.assertTrue(out["final_decision"].equals(enriched_final))

    def test_build_report_payload_contains_expected_keys(self) -> None:
        payload = _build_report_payload(
            mep_real=1400.0,
            run_ts=pd.Timestamp("2026-04-26 10:30:00"),
            precios_iol={"AAPL": 100.0},
            portfolio_bundle={"df_total": pd.DataFrame()},
            dashboard_bundle={"kpis": {"total_ars": 1.0}},
            decision_bundle={"final_decision": pd.DataFrame()},
            sizing_bundle={"asignacion_final": pd.DataFrame()},
            technical_overlay=pd.DataFrame(),
            price_history={},
            finviz_stats={"cedears_total": 0},
            bonistas_bundle={},
            operations_bundle={},
            prediction_bundle={},
            risk_bundle={},
        )
        self.assertEqual(payload["mep_real"], 1400.0)
        self.assertEqual(payload["generated_at_label"], "2026-04-26 10:30:00")
        self.assertIn("portfolio_bundle", payload)
        self.assertIn("risk_bundle", payload)

    def test_render_and_persist_report_delegates_render_and_snapshots(self) -> None:
        report = {"k": "v"}
        portfolio_bundle = {"df_total": pd.DataFrame([{"Ticker_IOL": "AAPL"}])}
        dashboard_bundle = {"kpis": {"total_ars": 1000.0}}
        decision_bundle = {"final_decision": pd.DataFrame([{"Ticker_IOL": "AAPL", "score_unificado": 0.1}])}
        technical_overlay = pd.DataFrame([{"Ticker_IOL": "AAPL", "RSI_14": 50.0}])

        html_path_mock = Mock()
        with patch("generate_real_report.render_report", return_value="<html>ok</html>") as render_mock, patch(
            "generate_real_report.write_real_snapshots",
            return_value=[Path("a.csv"), Path("b.json")],
        ) as snapshots_mock, patch("generate_real_report.HTML_PATH", html_path_mock), patch(
            "generate_real_report.logger.info"
        ) as logger_mock, patch("builtins.print") as print_mock:
            _render_and_persist_report(
                report,
                portfolio_bundle=portfolio_bundle,
                dashboard_bundle=dashboard_bundle,
                decision_bundle=decision_bundle,
                technical_overlay=technical_overlay,
            )

        render_mock.assert_called_once()
        self.assertIs(render_mock.call_args.args[0], report)
        html_path_mock.write_text.assert_called_once_with("<html>ok</html>", encoding="utf-8")
        snapshots_mock.assert_called_once()
        self.assertIs(snapshots_mock.call_args.kwargs["portfolio_bundle"], portfolio_bundle)
        self.assertIs(snapshots_mock.call_args.kwargs["dashboard_bundle"], dashboard_bundle)
        self.assertIs(snapshots_mock.call_args.kwargs["decision_bundle"], decision_bundle)
        self.assertTrue(snapshots_mock.call_args.kwargs["technical_overlay"].equals(technical_overlay))
        logger_mock.assert_called()
        self.assertGreaterEqual(print_mock.call_count, 3)

    def test_collect_market_runtime_inputs_fetches_payload_and_prices(self) -> None:
        portfolio_payload = {"activos": [{"titulo": {"simbolo": "AAPL", "tipo": "CEDEARS"}}]}
        estado_payload = {"ok": True}
        operaciones_payload = [{"tipo": "Compra", "estado": "terminada", "simbolo": "AAPL"}]

        with patch("generate_real_report.iol_login", return_value="token0"), patch(
            "generate_real_report.fetch_iol_payloads",
            return_value=(portfolio_payload, estado_payload, operaciones_payload, "token1"),
        ) as payloads_mock, patch(
            "generate_real_report.get_mep_real",
            return_value={"promedio": 1400.5},
        ), patch(
            "generate_real_report.get_dollar_series",
            return_value=[{"fecha": "2026-04-24", "compra": 1000.0, "venta": 1010.0}, {"fecha": "2026-04-25", "compra": 1010.0, "venta": 1020.0}],
        ), patch(
            "generate_real_report.extract_quote_tickers",
            return_value=["AAPL"],
        ), patch(
            "generate_real_report.extract_operation_quote_tickers",
            return_value=["AAPL"],
        ), patch(
            "generate_real_report.fetch_prices",
            return_value=({"AAPL": 101.0}, "token2"),
        ) as prices_mock, patch("builtins.print") as print_mock:
            out = _collect_market_runtime_inputs(username="u", password="p")

        self.assertEqual(out["activos"], portfolio_payload["activos"])
        self.assertEqual(out["estado_payload"], estado_payload)
        self.assertEqual(out["operaciones_payload"], operaciones_payload)
        self.assertEqual(out["mep_real"], 1400.5)
        self.assertFalse(out["mep_daily_returns"].empty)
        self.assertEqual(out["precios_iol"], {"AAPL": 101.0})
        payloads_mock.assert_called_once_with(token="token0", username="u", password="p")
        prices_mock.assert_called_once()
        self.assertGreaterEqual(print_mock.call_count, 3)

    def test_build_analysis_context_orchestrates_bundle_building(self) -> None:
        df_total = pd.DataFrame([{"Ticker_IOL": "AAPL"}])
        df_bonos = pd.DataFrame([{"Ticker_IOL": "GD30"}])
        df_cedears_src = pd.DataFrame([{"Ticker_IOL": "AAPL", "Ticker_Finviz": "AAPL"}])
        df_cedears_enriched = pd.DataFrame([{"Ticker_IOL": "AAPL", "RSI_14": 52.0}])
        df_ratings = pd.DataFrame([{"Ticker_Finviz": "AAPL", "consenso": "Buy"}])
        technical_overlay = pd.DataFrame([{"Ticker_IOL": "AAPL", "Momentum_20d_%": 1.5}])
        final_decision = pd.DataFrame([{"Ticker_IOL": "AAPL", "score_unificado": 0.12}])

        portfolio_bundle = {
            "df_total": df_total,
            "df_bonos": df_bonos,
            "df_cedears": df_cedears_src,
            "liquidity_contract": {"cash_ars": 10.0},
        }
        bonistas_bundle = {"macro_variables": {"ust_status": "ok"}}
        decision_bundle_initial = {"final_decision": final_decision.copy(), "market_regime": {"regime": "neutral"}}
        decision_bundle_merged = {"final_decision": final_decision.copy(), "market_regime": {"regime": "neutral"}}
        decision_bundle_temporal = {"final_decision": final_decision.copy(), "market_regime": {"regime": "neutral"}, "decision_memory": {}}
        prediction_bundle = {"predictions": pd.DataFrame(), "summary": {}}
        sizing_bundle = {"asignacion_final": pd.DataFrame()}
        dashboard_bundle = {"kpis": {"total_ars": 100.0}}
        risk_bundle = {"summary": {}}
        operations_bundle = {"rows": pd.DataFrame()}

        with patch("generate_real_report.build_portfolio_bundle", return_value=portfolio_bundle) as build_portfolio_mock, patch(
            "generate_real_report.build_real_bonistas_bundle", return_value=bonistas_bundle
        ) as bonistas_mock, patch(
            "generate_real_report.enrich_real_cedears",
            return_value=(df_cedears_enriched, df_ratings, {"cedears_total": 1}),
        ) as enrich_mock, patch(
            "generate_real_report.build_technical_overlay", return_value=technical_overlay
        ) as technical_mock, patch(
            "generate_real_report._print_coverage_stats"
        ) as coverage_mock, patch(
            "generate_real_report.build_decision_bundle", return_value=decision_bundle_initial
        ) as decision_mock, patch(
            "generate_real_report._merge_bond_context_into_decision", return_value=decision_bundle_merged
        ) as merge_mock, patch(
            "generate_real_report._enrich_decision_with_temporal_memory", return_value=decision_bundle_temporal
        ) as temporal_mock, patch(
            "generate_real_report._build_prediction_bundle_with_history", return_value=prediction_bundle
        ) as prediction_mock, patch(
            "generate_real_report.build_sizing_bundle", return_value=sizing_bundle
        ) as sizing_mock, patch(
            "generate_real_report.build_dashboard_bundle", return_value=dashboard_bundle
        ) as dashboard_mock, patch(
            "generate_real_report._build_risk_bundle", return_value=risk_bundle
        ) as risk_mock, patch(
            "generate_real_report._build_operations_context", return_value=operations_bundle
        ) as operations_mock:
            out = _build_analysis_context(
                activos=[{"titulo": {"simbolo": "AAPL"}}],
                estado_payload={"estado": "ok"},
                operaciones_payload=[{"tipo": "Compra"}],
                mep_real=1400.0,
                precios_iol={"AAPL": 101.0},
                benchmark_daily_returns=pd.Series([1.0], index=[pd.Timestamp("2026-04-25")]),
                run_date=pd.Timestamp("2026-04-26"),
                usar_liquidez_iol=True,
                aporte_externo_ars=100000.0,
            )

        build_portfolio_mock.assert_called_once()
        bonistas_mock.assert_called_once_with(df_bonos, mep_real=1400.0)
        enrich_mock.assert_called_once_with(df_cedears_src, mep_real=1400.0)
        technical_mock.assert_called_once()
        coverage_mock.assert_called_once()
        decision_mock.assert_called_once()
        merge_mock.assert_called_once_with(decision_bundle_initial, bonistas_bundle)
        temporal_mock.assert_called_once()
        prediction_mock.assert_called_once_with(decision_bundle_temporal, run_date=pd.Timestamp("2026-04-26"))
        sizing_mock.assert_called_once()
        dashboard_mock.assert_called_once_with(df_total, mep_real=1400.0, liquidity_contract={"cash_ars": 10.0})
        risk_mock.assert_called_once()
        self.assertIs(risk_mock.call_args.args[0], df_total)
        self.assertEqual(risk_mock.call_args.kwargs["run_date"], pd.Timestamp("2026-04-26"))
        self.assertIs(risk_mock.call_args.kwargs["dashboard_bundle"], dashboard_bundle)
        benchmark_arg = risk_mock.call_args.kwargs["benchmark_daily_returns"]
        self.assertIsInstance(benchmark_arg, pd.Series)
        self.assertEqual(float(benchmark_arg.iloc[0]), 1.0)
        operations_mock.assert_called_once_with(
            [{"tipo": "Compra"}],
            portfolio_bundle=portfolio_bundle,
            run_date=pd.Timestamp("2026-04-26"),
        )
        self.assertIs(out["decision_phase"]["portfolio_bundle"], portfolio_bundle)
        self.assertIs(out["decision_phase"]["bonistas_bundle"], bonistas_bundle)
        self.assertIs(out["decision_phase"]["decision_bundle"], decision_bundle_temporal)
        self.assertIs(out["decision_phase"]["prediction_bundle"], prediction_bundle)
        self.assertIs(out["decision_phase"]["sizing_bundle"], sizing_bundle)
        self.assertIs(out["output_phase"]["dashboard_bundle"], dashboard_bundle)
        self.assertIs(out["output_phase"]["risk_bundle"], risk_bundle)
        self.assertIs(out["output_phase"]["operations_bundle"], operations_bundle)
        self.assertTrue(out["output_phase"]["technical_overlay"].equals(technical_overlay))

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

    def test_parse_args_accepts_scheduler_interval(self) -> None:
        args = parse_args(["--non-interactive", "--schedule-every-minutes", "15"])
        self.assertTrue(args.non_interactive)
        self.assertEqual(args.schedule_every_minutes, 15)

    def test_run_scheduled_real_report_requires_non_interactive(self) -> None:
        args = type("Args", (), {"schedule_every_minutes": 5, "non_interactive": False})()
        with self.assertRaisesRegex(ValueError, "--schedule-every-minutes requiere --non-interactive"):
            run_scheduled_real_report(args)

    def test_run_scheduled_real_report_runs_once_when_interval_is_zero(self) -> None:
        args = type("Args", (), {"schedule_every_minutes": 0, "non_interactive": True})()
        with patch("generate_real_report.run_real_report") as run_mock:
            run_scheduled_real_report(args)
        run_mock.assert_called_once_with(args)

    def test_run_scheduled_real_report_loops_and_sleeps(self) -> None:
        args = type("Args", (), {"schedule_every_minutes": 1, "non_interactive": True})()
        state = {"calls": 0}

        def fake_run(_args):
            state["calls"] += 1
            if state["calls"] >= 2:
                raise KeyboardInterrupt()

        sleep_mock = Mock()
        with patch("generate_real_report.run_real_report", side_effect=fake_run):
            with self.assertRaises(KeyboardInterrupt):
                run_scheduled_real_report(args, sleep_fn=sleep_mock)
        self.assertEqual(state["calls"], 2)
        sleep_mock.assert_called_once_with(60)

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

    def test_should_use_legacy_snapshots_disables_fallback_after_min_window(self) -> None:
        snapshots_dir = ROOT / "tmp_primary_snapshot_window"
        snapshots_dir.mkdir(exist_ok=True)
        for day in range(1, 21):
            (snapshots_dir / f"2026-04-{day:02d}_real_portfolio_master.csv").write_text(
                "Ticker_IOL,Tipo\nAAPL,CEDEAR\n",
                encoding="utf-8",
            )
        self.addCleanup(lambda: shutil.rmtree(snapshots_dir, ignore_errors=True))

        with patch.dict("os.environ", {"ENABLE_LEGACY_SNAPSHOTS": "1"}, clear=False), patch(
            "generate_real_report.SNAPSHOTS_DIR", snapshots_dir
        ):
            self.assertFalse(should_use_legacy_snapshots())

    def test_should_use_legacy_snapshots_keeps_fallback_before_min_window(self) -> None:
        snapshots_dir = ROOT / "tmp_primary_snapshot_short"
        snapshots_dir.mkdir(exist_ok=True)
        for day in range(1, 6):
            (snapshots_dir / f"2026-04-{day:02d}_real_portfolio_master.csv").write_text(
                "Ticker_IOL,Tipo\nAAPL,CEDEAR\n",
                encoding="utf-8",
            )
        self.addCleanup(lambda: shutil.rmtree(snapshots_dir, ignore_errors=True))

        with patch.dict("os.environ", {"ENABLE_LEGACY_SNAPSHOTS": "1"}, clear=False), patch(
            "generate_real_report.SNAPSHOTS_DIR", snapshots_dir
        ):
            self.assertTrue(should_use_legacy_snapshots())

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
