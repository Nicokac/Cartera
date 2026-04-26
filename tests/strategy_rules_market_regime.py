import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from decision.actions import assign_action_v2, assign_base_action, enrich_decision_explanations
from decision.scoring import (
    apply_base_scores,
    apply_technical_overlay_scores,
    build_market_regime_summary,
    build_decision_base,
    build_technical_overlay_scores,
    consensus_to_score,
    rank_score,
)
class StrategyRulesMarketRegimeTests(unittest.TestCase):
    def test_market_regime_can_penalize_local_equity_and_help_hard_currency_bonds(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "LOMA",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_family": "stock",
                    "asset_subfamily": "stock_argentina",
                    "Peso_%": 1.0,
                    "Perf Week": 1.0,
                    "Perf Month": 2.0,
                    "Perf YTD": 3.0,
                    "Beta": 0.9,
                    "P/E": 10.0,
                    "ROE": 18.0,
                    "Profit Margin": 15.0,
                    "MEP_Premium_%": -95.0,
                    "Consensus_Final": 0.6,
                    "Ganancia_%": 10.0,
                    "Ganancia_ARS": 100.0,
                },
                {
                    "Ticker_IOL": "GD30",
                    "Es_Liquidez": False,
                    "Es_Bono": True,
                    "asset_family": "bond",
                    "asset_subfamily": "bond_sov_ar",
                    "Peso_%": 1.0,
                    "Perf Week": None,
                    "Perf Month": None,
                    "Perf YTD": None,
                    "Beta": None,
                    "P/E": None,
                    "ROE": None,
                    "Profit Margin": None,
                    "MEP_Premium_%": None,
                    "Consensus_Final": 0.5,
                    "Ganancia_%": 10.0,
                    "Ganancia_ARS": 100.0,
                },
            ]
        )

        base = apply_base_scores(df)
        stressed = apply_base_scores(
            df,
            market_context={"riesgo_pais_bps": 950.0},
            scoring_rules={
                "market_regime": {
                    "enabled": True,
                    "flags": {"stress_soberano_local": {"riesgo_pais_bps_min": 800.0}},
                    "adjustments": {
                        "stress_soberano_local": {
                            "stock_argentina": {"refuerzo_delta": -0.03, "reduccion_delta": 0.03},
                            "bond_sov_ar": {"refuerzo_delta": 0.02, "reduccion_delta": -0.02},
                        }
                    },
                }
            },
        )

        self.assertLess(stressed.loc[0, "score_refuerzo"], base.loc[0, "score_refuerzo"])
        self.assertGreater(stressed.loc[0, "score_reduccion"], base.loc[0, "score_reduccion"])
        self.assertGreater(stressed.loc[1, "score_refuerzo"], base.loc[1, "score_refuerzo"])
        self.assertLess(stressed.loc[1, "score_reduccion"], base.loc[1, "score_reduccion"])


    def test_market_regime_can_penalize_growth_when_ust_rates_are_high(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "AMD",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_family": "stock",
                    "asset_subfamily": "stock_growth",
                    "Peso_%": 1.0,
                    "Perf Week": 3.0,
                    "Perf Month": 5.0,
                    "Perf YTD": 8.0,
                    "Beta": 1.2,
                    "P/E": 28.0,
                    "ROE": 20.0,
                    "Profit Margin": 18.0,
                    "MEP_Premium_%": -95.0,
                    "Consensus_Final": 0.7,
                    "Ganancia_%": 10.0,
                    "Ganancia_ARS": 100.0,
                },
                {
                    "Ticker_IOL": "KO",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "asset_family": "stock",
                    "asset_subfamily": "stock_defensive_dividend",
                    "Peso_%": 1.0,
                    "Perf Week": 3.0,
                    "Perf Month": 5.0,
                    "Perf YTD": 8.0,
                    "Beta": 0.7,
                    "P/E": 18.0,
                    "ROE": 20.0,
                    "Profit Margin": 18.0,
                    "MEP_Premium_%": -95.0,
                    "Consensus_Final": 0.7,
                    "Ganancia_%": 10.0,
                    "Ganancia_ARS": 100.0,
                },
            ]
        )

        base = apply_base_scores(df)
        regime = apply_base_scores(
            df,
            market_context={"ust_10y_pct": 4.6},
            scoring_rules={
                "market_regime": {
                    "enabled": True,
                    "flags": {"tasas_ust_altas": {"ust_10y_pct_min": 4.5, "ust_5y_pct_min": 4.25}},
                    "adjustments": {
                        "tasas_ust_altas": {
                            "stock_growth": {"refuerzo_delta": -0.02, "reduccion_delta": 0.02},
                            "stock_defensive_dividend": {"refuerzo_delta": 0.02, "reduccion_delta": -0.01},
                        }
                    },
                }
            },
        )

        self.assertLess(regime.loc[0, "score_refuerzo"], base.loc[0, "score_refuerzo"])
        self.assertGreater(regime.loc[0, "score_reduccion"], base.loc[0, "score_reduccion"])
        self.assertGreater(regime.loc[1, "score_refuerzo"], base.loc[1, "score_refuerzo"])


    def test_market_regime_summary_stays_inactive_with_current_real_macro_baseline(self) -> None:
        summary = build_market_regime_summary(
            {
                "riesgo_pais_bps": 609.0,
                "rem_inflacion_mensual_pct": 2.7,
                "rem_inflacion_12m_pct": 22.2,
                "ust_5y_pct": 3.99,
                "ust_10y_pct": 4.35,
            },
            scoring_rules={
                "market_regime": {
                    "enabled": True,
                    "flags": {
                        "stress_soberano_local": {"riesgo_pais_bps_min": 800.0},
                        "inflacion_local_alta": {
                            "rem_inflacion_12m_pct_min": 30.0,
                            "rem_inflacion_mensual_pct_min": 3.0,
                        },
                        "tasas_ust_altas": {"ust_10y_pct_min": 4.5, "ust_5y_pct_min": 4.25},
                    },
                }
            },
        )

        self.assertFalse(summary["any_active"])
        self.assertEqual(summary["active_flags"], [])


    def test_market_regime_summary_can_be_forced_for_calibration_by_lowering_thresholds(self) -> None:
        summary = build_market_regime_summary(
            {
                "riesgo_pais_bps": 609.0,
                "rem_inflacion_mensual_pct": 2.7,
                "rem_inflacion_12m_pct": 22.2,
                "ust_5y_pct": 3.99,
                "ust_10y_pct": 4.35,
            },
            scoring_rules={
                "market_regime": {
                    "enabled": True,
                    "flags": {
                        "stress_soberano_local": {"riesgo_pais_bps_min": 600.0},
                        "inflacion_local_alta": {
                            "rem_inflacion_12m_pct_min": 22.0,
                            "rem_inflacion_mensual_pct_min": 2.5,
                        },
                        "tasas_ust_altas": {"ust_10y_pct_min": 4.3, "ust_5y_pct_min": 3.95},
                    },
                }
            },
        )

        self.assertTrue(summary["any_active"])
        self.assertIn("stress_soberano_local", summary["active_flags"])
        self.assertIn("inflacion_local_alta", summary["active_flags"])
        self.assertIn("tasas_ust_altas", summary["active_flags"])


if __name__ == "__main__":
    unittest.main()

