import logging
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from generate_real_report_bonistas import build_real_bonistas_bundle_impl


class GenerateRealReportSplitBonistasTests(unittest.TestCase):
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
