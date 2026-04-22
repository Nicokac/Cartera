import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from decision.history import (
    build_decision_history_observation,
    build_temporal_memory_summary,
    enrich_with_temporal_memory,
    resolve_market_run_date,
    upsert_daily_decision_history,
)


class DecisionHistoryTests(unittest.TestCase):
    def test_upsert_daily_decision_history_replaces_same_day_row(self) -> None:
        history = pd.DataFrame(
            [
                {
                    "run_date": "2026-04-07",
                    "Ticker_IOL": "AAPL",
                    "asset_subfamily": "stock_growth",
                    "score_unificado": -0.10,
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "Peso_%": 4.9,
                    "Tech_Trend": "Mixta",
                    "Momentum_20d_%": 0.5,
                    "Momentum_60d_%": -0.4,
                    "market_regime_any_active": False,
                    "market_regime_active_flags": "",
                },
                {
                    "run_date": "2026-04-07",
                    "Ticker_IOL": "KO",
                    "asset_subfamily": "stock_defensive_dividend",
                    "score_unificado": 0.25,
                    "accion_sugerida_v2": "Refuerzo",
                    "Peso_%": 2.2,
                    "Tech_Trend": "Alcista",
                    "Momentum_20d_%": 0.9,
                    "Momentum_60d_%": 15.0,
                    "market_regime_any_active": False,
                    "market_regime_active_flags": "",
                }
            ]
        )
        current = pd.DataFrame(
            [
                {
                    "run_date": "2026-04-07",
                    "Ticker_IOL": "AAPL",
                    "asset_subfamily": "stock_growth",
                    "score_unificado": -0.05,
                    "accion_sugerida_v2": "Refuerzo",
                    "Peso_%": 4.8,
                    "Tech_Trend": "Alcista",
                    "Momentum_20d_%": 2.5,
                    "Momentum_60d_%": 1.0,
                    "market_regime_any_active": True,
                    "market_regime_active_flags": "tasas_ust_altas",
                }
            ]
        )

        merged = upsert_daily_decision_history(history, current)

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged.loc[0, "accion_sugerida_v2"], "Refuerzo")
        self.assertAlmostEqual(merged.loc[0, "score_unificado"], -0.05, places=3)
        self.assertEqual(merged.loc[0, "market_regime_active_flags"], "tasas_ust_altas")
        self.assertEqual(merged.loc[0, "Ticker_IOL"], "AAPL")

    def test_enrich_with_temporal_memory_counts_streaks_by_previous_days(self) -> None:
        history = pd.DataFrame(
            [
                {
                    "run_date": "2026-04-05",
                    "Ticker_IOL": "AAPL",
                    "asset_subfamily": "stock_growth",
                    "score_unificado": 0.18,
                    "accion_sugerida_v2": "Refuerzo",
                    "Peso_%": 4.7,
                    "Tech_Trend": "Alcista",
                    "Momentum_20d_%": 1.5,
                    "Momentum_60d_%": 4.0,
                    "market_regime_any_active": False,
                    "market_regime_active_flags": "",
                },
                {
                    "run_date": "2026-04-06",
                    "Ticker_IOL": "AAPL",
                    "asset_subfamily": "stock_growth",
                    "score_unificado": 0.22,
                    "accion_sugerida_v2": "Refuerzo",
                    "Peso_%": 4.8,
                    "Tech_Trend": "Alcista",
                    "Momentum_20d_%": 1.8,
                    "Momentum_60d_%": 4.1,
                    "market_regime_any_active": False,
                    "market_regime_active_flags": "",
                },
                {
                    "run_date": "2026-04-06",
                    "Ticker_IOL": "MELI",
                    "asset_subfamily": "stock_growth",
                    "score_unificado": -0.25,
                    "accion_sugerida_v2": "Reducir",
                    "Peso_%": 3.8,
                    "Tech_Trend": "Mixta",
                    "Momentum_20d_%": -4.0,
                    "Momentum_60d_%": -21.0,
                    "market_regime_any_active": False,
                    "market_regime_active_flags": "",
                },
            ]
        )
        final_decision = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AAPL",
                    "score_unificado": 0.24,
                    "accion_sugerida_v2": "Refuerzo",
                },
                {
                    "Ticker_IOL": "MELI",
                    "score_unificado": -0.05,
                    "accion_sugerida_v2": "Mantener / Neutral",
                },
            ]
        )

        enriched = enrich_with_temporal_memory(final_decision, history, run_date="2026-04-07")
        summary = build_temporal_memory_summary(enriched)

        aapl = enriched.loc[enriched["Ticker_IOL"] == "AAPL"].iloc[0]
        self.assertEqual(aapl["accion_previa"], "Refuerzo")
        self.assertAlmostEqual(aapl["score_delta_vs_dia_anterior"], 0.02, places=3)
        self.assertEqual(aapl["dias_consecutivos_refuerzo"], 3)
        self.assertTrue(bool(aapl["senal_persistente_refuerzo"]))
        self.assertFalse(bool(aapl["es_nueva_senal"]))

        meli = enriched.loc[enriched["Ticker_IOL"] == "MELI"].iloc[0]
        self.assertEqual(meli["accion_previa"], "Reducir")
        self.assertEqual(meli["dias_consecutivos_mantener"], 1)
        self.assertTrue(bool(meli["es_nueva_senal"]))
        self.assertFalse(bool(meli["senal_persistente_reduccion"]))

        self.assertEqual(summary["senales_nuevas"], 1)
        self.assertEqual(summary["persistentes_refuerzo"], 1)
        self.assertEqual(summary["persistentes_reduccion"], 0)
        self.assertEqual(summary["sin_historial"], 0)

    def test_build_decision_history_observation_normalizes_daily_market_context(self) -> None:
        final_decision = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "KO",
                    "asset_subfamily": "stock_defensive_dividend",
                    "score_unificado": 0.31,
                    "accion_sugerida_v2": "Refuerzo",
                    "Peso_%": 2.2,
                    "Tech_Trend": "Alcista",
                    "Momentum_20d_%": 0.9,
                    "Momentum_60d_%": 15.1,
                }
            ]
        )

        observation = build_decision_history_observation(
            final_decision,
            run_date="2026-04-07 15:30:00",
            market_regime={"any_active": True, "active_flags": ["tasas_ust_altas", "inflacion_local_alta"]},
        )

        self.assertEqual(observation.loc[0, "run_date"], "2026-04-07")
        self.assertTrue(bool(observation.loc[0, "market_regime_any_active"]))
        self.assertEqual(
            observation.loc[0, "market_regime_active_flags"],
            "tasas_ust_altas,inflacion_local_alta",
        )

    def test_resolve_market_run_date_maps_weekend_to_previous_business_day(self) -> None:
        self.assertEqual(resolve_market_run_date("2026-04-11 09:30:00"), "2026-04-10")
        self.assertEqual(resolve_market_run_date("2026-04-12 18:00:00"), "2026-04-10")

    def test_resolve_market_run_date_maps_preopen_weekday_to_previous_business_day(self) -> None:
        self.assertEqual(resolve_market_run_date("2026-04-13 09:59:00"), "2026-04-10")
        self.assertEqual(resolve_market_run_date("2026-04-13 10:00:00"), "2026-04-13")

    def test_temporal_memory_summary_excludes_liquidity_rows_from_aggregate_counts(self) -> None:
        final_decision = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AAPL",
                    "Tipo": "CEDEAR",
                    "es_nueva_senal": True,
                    "senal_persistente_refuerzo": True,
                    "senal_persistente_reduccion": False,
                    "sin_historial_temporal": False,
                },
                {
                    "Ticker_IOL": "CASH_ARS",
                    "Tipo": "Liquidez",
                    "es_nueva_senal": True,
                    "senal_persistente_refuerzo": False,
                    "senal_persistente_reduccion": False,
                    "sin_historial_temporal": True,
                },
            ]
        )

        summary = build_temporal_memory_summary(final_decision)

        self.assertEqual(summary["senales_nuevas"], 1)
        self.assertEqual(summary["persistentes_refuerzo"], 1)
        self.assertEqual(summary["persistentes_reduccion"], 0)
        self.assertEqual(summary["sin_historial"], 0)

    def test_temporal_memory_treats_cash_ars_and_caucion_as_same_operational_liquidity(self) -> None:
        history = pd.DataFrame(
            [
                {
                    "run_date": "2026-04-08",
                    "Ticker_IOL": "CASH_ARS",
                    "asset_subfamily": "liquidity_other",
                    "score_unificado": -0.285,
                    "accion_sugerida_v2": "Mantener liquidez bloqueada",
                    "Peso_%": 30.0,
                    "Tech_Trend": np.nan,
                    "Momentum_20d_%": np.nan,
                    "Momentum_60d_%": np.nan,
                    "market_regime_any_active": True,
                    "market_regime_active_flags": "inflacion_local_alta",
                }
            ]
        )
        final_decision = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "CAUCION",
                    "Tipo": "Liquidez",
                    "score_unificado": -0.285,
                    "accion_sugerida_v2": "Mantener liquidez bloqueada",
                }
            ]
        )

        enriched = enrich_with_temporal_memory(final_decision, history, run_date="2026-04-09")
        row = enriched.iloc[0]

        self.assertEqual(row["accion_previa"], "Mantener liquidez bloqueada")
        self.assertFalse(bool(row["sin_historial_temporal"]))
        self.assertEqual(row["dias_consecutivos_mantener"], 2)

    def test_temporal_memory_resets_when_asset_subfamily_changes(self) -> None:
        history = pd.DataFrame(
            [
                {
                    "run_date": "2026-04-20",
                    "Ticker_IOL": "ADBAICA",
                    "asset_subfamily": "liquidity_other",
                    "score_unificado": -0.278,
                    "accion_sugerida_v2": "Mantener liquidez bloqueada",
                    "Peso_%": 7.2,
                    "Tech_Trend": np.nan,
                    "Momentum_20d_%": np.nan,
                    "Momentum_60d_%": np.nan,
                    "market_regime_any_active": True,
                    "market_regime_active_flags": "inflacion_local_alta",
                }
            ]
        )
        final_decision = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "ADBAICA",
                    "Tipo": "FCI",
                    "asset_subfamily": "fund_other",
                    "score_unificado": 0.0,
                    "accion_sugerida_v2": "Mantener / Neutral",
                }
            ]
        )

        enriched = enrich_with_temporal_memory(final_decision, history, run_date="2026-04-21")
        row = enriched.iloc[0]

        self.assertTrue(bool(row["sin_historial_temporal"]))
        self.assertTrue(pd.isna(row["score_delta_vs_dia_anterior"]))
        self.assertIsNone(row["accion_previa"])
        self.assertEqual(row["dias_consecutivos_mantener"], 1)
        self.assertFalse(bool(row["es_nueva_senal"]))


if __name__ == "__main__":
    unittest.main()
