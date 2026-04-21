import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from prediction.predictor import predict, vote_signal


class PredictionPredictorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        project_config = importlib.import_module("config")
        project_config.clear_config_cache()
        cls.weights = project_config.PREDICTION_WEIGHTS

    def test_vote_signal_maps_rsi_momentum_trend_score_and_regime(self) -> None:
        row = {
            "RSI_14": 30.0,
            "Momentum_20d_%": 3.2,
            "Momentum_60d_%": -6.0,
            "Tech_Trend": "Alcista",
            "score_unificado": 0.18,
            "market_regime_any_active": True,
            "market_regime_active_flags": "stress_soberano_local",
        }
        signals = self.weights["signals"]

        self.assertEqual(vote_signal("rsi", row, signals["rsi"]), 1)
        self.assertEqual(vote_signal("momentum_20d", row, signals["momentum_20d"]), 1)
        self.assertEqual(vote_signal("momentum_60d", row, signals["momentum_60d"]), -1)
        self.assertEqual(vote_signal("sma_trend", row, signals["sma_trend"]), 1)
        self.assertEqual(vote_signal("score_unificado", row, signals["score_unificado"]), 1)
        self.assertEqual(vote_signal("market_regime", row, signals["market_regime"]), -1)

    def test_predict_returns_up_with_weighted_consensus(self) -> None:
        row = {
            "RSI_14": 30.0,
            "Momentum_20d_%": 4.0,
            "Momentum_60d_%": 8.0,
            "Tech_Trend": "Alcista fuerte",
            "score_unificado": 0.22,
            "market_regime_any_active": False,
            "market_regime_active_flags": "",
        }

        result = predict(row, self.weights)

        self.assertEqual(result["direction"], "up")
        self.assertGreater(result["confidence"], 0.15)
        self.assertGreater(result["consensus_raw"], 0.15)
        self.assertGreater(result["agreement_ratio"], 0.0)
        self.assertGreater(result["net_strength"], 0.15)
        self.assertEqual(result["votes"]["rsi"], 1)
        self.assertEqual(result["votes"]["market_regime"], 1)

    def test_predict_returns_down_with_bearish_consensus(self) -> None:
        row = {
            "RSI_14": 80.0,
            "Momentum_20d_%": -5.0,
            "Momentum_60d_%": -7.0,
            "Tech_Trend": "Bajista",
            "score_unificado": -0.18,
            "market_regime_any_active": True,
            "market_regime_active_flags": "tasas_ust_altas",
        }

        result = predict(row, self.weights)

        self.assertEqual(result["direction"], "down")
        self.assertLess(result["consensus_raw"], -0.15)
        self.assertEqual(result["votes"]["market_regime"], -1)

    def test_predict_returns_neutral_when_consensus_stays_inside_threshold(self) -> None:
        custom_weights = {
            "direction_threshold": 0.30,
            "signals": {
                "rsi": {
                    "weight": 1.0,
                    "vote_rules": {"oversold_threshold": 35, "overbought_threshold": 65},
                },
                "momentum_20d": {
                    "weight": 1.0,
                    "vote_rules": {"positive_threshold": 2.0, "negative_threshold": -2.0},
                },
            },
        }
        row = {
            "RSI_14": 30.0,
            "Momentum_20d_%": -3.0,
        }

        result = predict(row, custom_weights)

        self.assertEqual(result["direction"], "neutral")
        self.assertEqual(result["votes"], {"rsi": 1, "momentum_20d": -1})
        self.assertAlmostEqual(result["consensus_raw"], 0.0, places=6)
        self.assertAlmostEqual(result["confidence"], 0.0, places=6)
        self.assertAlmostEqual(result["agreement_ratio"], 0.0, places=6)
        self.assertAlmostEqual(result["net_strength"], 0.0, places=6)

    def test_predict_ignores_signals_with_zero_weight(self) -> None:
        custom_weights = {
            "direction_threshold": 0.15,
            "signals": {
                "rsi": {
                    "weight": 0.0,
                    "vote_rules": {"oversold_threshold": 35, "overbought_threshold": 65},
                },
                "momentum_20d": {
                    "weight": 1.0,
                    "vote_rules": {"positive_threshold": 2.0, "negative_threshold": -2.0},
                },
            },
        }
        row = {
            "RSI_14": 20.0,
            "Momentum_20d_%": 4.0,
        }

        result = predict(row, custom_weights)

        self.assertEqual(result["direction"], "up")
        self.assertEqual(result["votes"], {"momentum_20d": 1})
        self.assertAlmostEqual(result["consensus_raw"], 1.0, places=6)

    def test_predict_confidence_is_discounted_by_signal_disagreement(self) -> None:
        custom_weights = {
            "direction_threshold": 0.15,
            "signals": {
                "rsi": {
                    "weight": 1.0,
                    "vote_rules": {"oversold_threshold": 35, "overbought_threshold": 65},
                },
                "momentum_20d": {
                    "weight": 1.0,
                    "vote_rules": {"positive_threshold": 2.0, "negative_threshold": -2.0},
                },
                "momentum_60d": {
                    "weight": 1.0,
                    "vote_rules": {"positive_threshold": 5.0, "negative_threshold": -5.0},
                },
            },
        }
        row = {
            "RSI_14": 30.0,
            "Momentum_20d_%": 4.0,
            "Momentum_60d_%": -7.0,
        }

        result = predict(row, custom_weights)

        self.assertAlmostEqual(result["consensus_raw"], 0.333333, places=6)
        self.assertAlmostEqual(result["net_strength"], 0.333333, places=6)
        self.assertAlmostEqual(result["agreement_ratio"], 0.333333, places=6)
        self.assertAlmostEqual(result["confidence"], 0.111111, places=6)

    def test_predict_handles_missing_values_as_neutral_votes(self) -> None:
        row = {
            "RSI_14": None,
            "Momentum_20d_%": None,
            "Momentum_60d_%": None,
            "Tech_Trend": None,
            "score_unificado": None,
            "market_regime_any_active": True,
            "market_regime_active_flags": "inflacion_local_alta",
        }

        result = predict(row, self.weights)

        self.assertEqual(result["direction"], "neutral")
        self.assertEqual(result["votes"]["rsi"], 0)
        self.assertEqual(result["votes"]["momentum_20d"], 0)
        self.assertEqual(result["votes"]["momentum_60d"], 0)
        self.assertEqual(result["votes"]["sma_trend"], 0)
        self.assertEqual(result["votes"]["score_unificado"], 0)
        self.assertEqual(result["votes"]["market_regime"], 0)

    def test_vote_signal_uses_centered_thresholds_for_score_unificado_scale(self) -> None:
        signal_cfg = self.weights["signals"]["score_unificado"]

        self.assertEqual(vote_signal("score_unificado", {"score_unificado": 0.14}, signal_cfg), 1)
        self.assertEqual(vote_signal("score_unificado", {"score_unificado": -0.14}, signal_cfg), -1)
        self.assertEqual(vote_signal("score_unificado", {"score_unificado": 0.03}, signal_cfg), 0)

    def test_market_regime_inflacion_local_alta_keeps_bond_cer_non_bearish(self) -> None:
        signal_cfg = self.weights["signals"]["market_regime"]
        row = {
            "asset_family": "bond",
            "asset_subfamily": "bond_cer",
            "market_regime_any_active": True,
            "market_regime_active_flags": "inflacion_local_alta",
        }

        self.assertEqual(vote_signal("market_regime", row, signal_cfg), 0)

    def test_market_regime_inflacion_local_alta_penalizes_stock_argentina(self) -> None:
        signal_cfg = self.weights["signals"]["market_regime"]
        row = {
            "asset_family": "stock",
            "asset_subfamily": "stock_argentina",
            "market_regime_any_active": True,
            "market_regime_active_flags": "inflacion_local_alta",
        }

        self.assertEqual(vote_signal("market_regime", row, signal_cfg), -1)

    def test_market_regime_inflacion_local_alta_keeps_stock_growth_neutral(self) -> None:
        signal_cfg = self.weights["signals"]["market_regime"]
        row = {
            "asset_family": "stock",
            "asset_subfamily": "stock_growth",
            "market_regime_any_active": True,
            "market_regime_active_flags": "inflacion_local_alta",
        }

        self.assertEqual(vote_signal("market_regime", row, signal_cfg), 0)


if __name__ == "__main__":
    unittest.main()
