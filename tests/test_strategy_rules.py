import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from decision.actions import assign_action_v2


class StrategyRulesTests(unittest.TestCase):
    def test_action_thresholds_can_be_overridden_from_external_rules(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "CRM",
                    "Es_Liquidez": False,
                    "Es_Bono": False,
                    "score_refuerzo_v2": 0.55,
                    "score_reduccion_v2": 0.20,
                    "score_despliegue_liquidez": 0.0,
                }
            ]
        )

        default_result = assign_action_v2(df)
        custom_result = assign_action_v2(
            df,
            action_rules={
                "refuerzo_threshold": 0.50,
                "reduccion_threshold": 0.60,
                "score_gap_min": 0.10,
                "despliegue_liquidez_threshold": 0.55,
            },
        )

        self.assertEqual(default_result.loc[0, "accion_sugerida_v2"], "Mantener / Neutral")
        self.assertEqual(custom_result.loc[0, "accion_sugerida_v2"], "Refuerzo")


if __name__ == "__main__":
    unittest.main()
