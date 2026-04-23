import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from decision.market_regime_scoring import (
    apply_market_regime_adjustments,
    build_market_regime_summary,
    detect_market_regime_flags,
)


class MarketRegimeScoringTests(unittest.TestCase):
    def test_detect_market_regime_flags_returns_empty_when_disabled(self) -> None:
        flags = detect_market_regime_flags(
            {
                "riesgo_pais_bps": 900,
                "rem_inflacion_12m_pct": 35,
                "ust_10y_pct": 4.8,
            },
            scoring_rules={"market_regime": {"enabled": False}},
        )

        self.assertEqual(flags, {})

    def test_detect_market_regime_flags_handles_missing_context(self) -> None:
        flags = detect_market_regime_flags(None)

        self.assertEqual(
            flags,
            {
                "stress_soberano_local": False,
                "inflacion_local_alta": False,
                "tasas_ust_altas": False,
            },
        )

    def test_detect_market_regime_flags_detects_partial_activation(self) -> None:
        flags = detect_market_regime_flags(
            {
                "riesgo_pais_bps": 850,
                "rem_inflacion_12m_pct": 22,
                "rem_inflacion_mensual_pct": 2.4,
                "ust_10y_pct": 4.1,
                "ust_5y_pct": 3.8,
            }
        )

        self.assertTrue(flags["stress_soberano_local"])
        self.assertFalse(flags["inflacion_local_alta"])
        self.assertFalse(flags["tasas_ust_altas"])

    def test_apply_market_regime_adjustments_applies_family_and_subfamily_deltas(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "GD30",
                    "asset_family": "bond",
                    "asset_subfamily": "bond_sov_ar",
                    "score_refuerzo": 0.40,
                    "score_reduccion": 0.20,
                },
                {
                    "Ticker_IOL": "KO",
                    "asset_family": "stock",
                    "asset_subfamily": "stock_defensive_dividend",
                    "score_refuerzo": 0.55,
                    "score_reduccion": 0.15,
                },
            ]
        )

        out = apply_market_regime_adjustments(
            df,
            market_context={"riesgo_pais_bps": 900},
            scoring_rules={
                "market_regime": {
                    "flags": {
                        "stress_soberano_local": {"riesgo_pais_bps_min": 800},
                    },
                    "adjustments": {
                        "stress_soberano_local": {
                            "bond_sov_ar": {"refuerzo_delta": -0.10, "reduccion_delta": 0.25},
                            "family:stock": {"refuerzo_delta": 0.05, "reduccion_delta": -0.05},
                        }
                    },
                }
            },
        )

        self.assertAlmostEqual(out.loc[0, "score_refuerzo"], 0.30)
        self.assertAlmostEqual(out.loc[0, "score_reduccion"], 0.45)
        self.assertAlmostEqual(out.loc[1, "score_refuerzo"], 0.60)
        self.assertAlmostEqual(out.loc[1, "score_reduccion"], 0.10)
        self.assertTrue(out.loc[0, "market_regime_stress_soberano_local"])
        self.assertEqual(out.loc[0, "market_regime_flags"], "stress_soberano_local")

    def test_apply_market_regime_adjustments_returns_copy_unchanged_when_disabled(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "GD30",
                    "score_refuerzo": 0.4,
                    "score_reduccion": 0.2,
                }
            ]
        )

        out = apply_market_regime_adjustments(
            df,
            market_context={"riesgo_pais_bps": 900},
            scoring_rules={"market_regime": {"enabled": False}},
        )

        self.assertEqual(out.to_dict("records"), df.to_dict("records"))
        self.assertIsNot(out, df)

    def test_build_market_regime_summary_reflects_active_flags(self) -> None:
        summary = build_market_regime_summary(
            {
                "riesgo_pais_bps": 810,
                "rem_inflacion_mensual_pct": 3.2,
                "ust_10y_pct": 4.6,
            }
        )

        self.assertTrue(summary["any_active"])
        self.assertEqual(
            summary["active_flags"],
            ["stress_soberano_local", "inflacion_local_alta", "tasas_ust_altas"],
        )
        self.assertTrue(summary["flags"]["stress_soberano_local"])
        self.assertTrue(summary["flags"]["inflacion_local_alta"])
        self.assertTrue(summary["flags"]["tasas_ust_altas"])


if __name__ == "__main__":
    unittest.main()
