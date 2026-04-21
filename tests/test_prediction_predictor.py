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

        self.assertGreater(vote_signal("rsi", row, signals["rsi"]), 0)
        self.assertGreater(vote_signal("momentum_20d", row, signals["momentum_20d"]), 0)
        self.assertLess(vote_signal("momentum_60d", row, signals["momentum_60d"]), 0)
        self.assertGreater(vote_signal("sma_trend", row, signals["sma_trend"]), 0)
        self.assertGreater(vote_signal("score_unificado", row, signals["score_unificado"]), 0)
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
        self.assertGreater(result["votes"]["rsi"], 0)
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

    def test_predict_returns_conviction_label_alta_when_high_confidence(self) -> None:
        row = {
            "RSI_14": 25.0,
            "Momentum_20d_%": 6.0,
            "Momentum_60d_%": 12.0,
            "Tech_Trend": "Alcista fuerte",
            "score_unificado": 0.35,
            "market_regime_any_active": False,
            "market_regime_active_flags": "",
        }
        result = predict(row, self.weights)
        self.assertEqual(result["conviction_label"], "alta")
        self.assertGreaterEqual(result["confidence"], 0.35)

    def test_predict_returns_conviction_label_baja_when_low_confidence(self) -> None:
        row = {
            "RSI_14": 52.0,
            "Momentum_20d_%": 0.5,
            "Momentum_60d_%": 1.0,
            "Tech_Trend": "Neutral",
            "score_unificado": 0.02,
            "market_regime_any_active": False,
            "market_regime_active_flags": "",
        }
        weights = dict(self.weights)
        result = predict(row, weights)
        self.assertEqual(result["conviction_label"], "baja")
        self.assertLess(result["confidence"], 0.20)

    def test_predict_conviction_uses_custom_thresholds(self) -> None:
        # RSI=19 → voto=0.62, confidence=0.62²≈0.384
        # con thresholds default (high=0.35) → "alta"
        # con thresholds custom (high=0.50, medium=0.30) → "media"
        custom_weights = {
            "direction_threshold": 0.05,
            "conviction_thresholds": {"high": 0.50, "medium": 0.30},
            "signals": {
                "rsi": {
                    "weight": 1.0,
                    "vote_mode": "continuous",
                    "vote_rules": {"center": 50.0, "lower_bound": 0.0, "upper_bound": 100.0},
                }
            },
        }
        row = {"RSI_14": 19.0}
        result = predict(row, custom_weights)
        self.assertGreaterEqual(result["confidence"], 0.30)
        self.assertLess(result["confidence"], 0.50)
        self.assertEqual(result["conviction_label"], "media")

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

    def test_active_vote_threshold_excludes_near_zero_continuous_votes_from_active_weight(self) -> None:
        # RSI=51 en modo continuo emite voto=-0.02, por debajo del umbral 0.1.
        # Sin umbral, ese voto casi-neutro inflaría active_weight y bajaría agreement_ratio.
        # Con active_vote_threshold=0.1, solo momentum (voto=+1) cuenta como activo.
        custom_weights = {
            "direction_threshold": 0.15,
            "active_vote_threshold": 0.1,
            "signals": {
                "rsi": {
                    "weight": 1.0,
                    "vote_mode": "continuous",
                    "vote_rules": {"center": 50.0, "lower_bound": 0.0, "upper_bound": 100.0},
                },
                "momentum_20d": {
                    "weight": 1.0,
                    "vote_rules": {"positive_threshold": 2.0, "negative_threshold": -2.0},
                },
            },
        }
        row = {"RSI_14": 51.0, "Momentum_20d_%": 4.0}

        result = predict(row, custom_weights)

        # RSI voto=-0.02 queda zereado antes de entrar al weighted_sum
        # weighted_sum = 1*0 + 1*1 = 1.0 → consensus_raw = 1.0/2.0 = 0.5
        self.assertAlmostEqual(result["consensus_raw"], 0.5, places=6)
        # solo momentum es activo → agreement_ratio = |1.0|/1.0 = 1.0
        self.assertAlmostEqual(result["agreement_ratio"], 1.0, places=6)
        # confidence = 0.5 * 1.0 = 0.5
        self.assertAlmostEqual(result["confidence"], 0.5, places=6)

    def test_active_vote_threshold_zero_counts_all_nonzero_votes_as_active(self) -> None:
        # Sin umbral (default 0.0), un voto continuo de -0.02 sí cuenta como activo
        # y penaliza agreement_ratio aunque el voto sea casi neutro.
        custom_weights = {
            "direction_threshold": 0.15,
            "signals": {
                "rsi": {
                    "weight": 1.0,
                    "vote_mode": "continuous",
                    "vote_rules": {"center": 50.0, "lower_bound": 0.0, "upper_bound": 100.0},
                },
                "momentum_20d": {
                    "weight": 1.0,
                    "vote_rules": {"positive_threshold": 2.0, "negative_threshold": -2.0},
                },
            },
        }
        row = {"RSI_14": 51.0, "Momentum_20d_%": 4.0}

        result = predict(row, custom_weights)

        # ambas señales activas → active_weight=2.0; agreement_ratio = |0.98|/2.0 = 0.49
        self.assertAlmostEqual(result["agreement_ratio"], 0.49, places=6)
        self.assertAlmostEqual(result["confidence"], 0.49 * 0.49, places=6)

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
        self.assertEqual(result["votes"]["adx"], 0)
        self.assertEqual(result["votes"]["relative_volume"], 0)

    def test_vote_signal_uses_centered_thresholds_for_score_unificado_scale(self) -> None:
        signal_cfg = self.weights["signals"]["score_unificado"]

        self.assertGreater(vote_signal("score_unificado", {"score_unificado": 0.14}, signal_cfg), 0)
        self.assertLess(vote_signal("score_unificado", {"score_unificado": -0.14}, signal_cfg), 0)
        self.assertEqual(vote_signal("score_unificado", {"score_unificado": 0.03}, signal_cfg), 0)

    def test_vote_signal_supports_continuous_rsi_mode(self) -> None:
        signal_cfg = {
            "vote_mode": "continuous",
            "vote_rules": {
                "center": 50.0,
                "lower_bound": 0.0,
                "upper_bound": 100.0,
            },
        }

        self.assertAlmostEqual(vote_signal("rsi", {"RSI_14": 15.0}, signal_cfg), 0.7, places=6)
        self.assertAlmostEqual(vote_signal("rsi", {"RSI_14": 36.0}, signal_cfg), 0.28, places=6)
        self.assertAlmostEqual(vote_signal("rsi", {"RSI_14": 80.0}, signal_cfg), -0.6, places=6)

    def test_vote_signal_supports_continuous_threshold_mode(self) -> None:
        signal_cfg = {
            "vote_mode": "continuous",
            "vote_rules": {
                "positive_threshold": 2.0,
                "negative_threshold": -2.0,
                "positive_saturation": 6.0,
                "negative_saturation": 6.0,
            },
        }

        self.assertAlmostEqual(vote_signal("momentum_20d", {"Momentum_20d_%": 1.0}, signal_cfg), 0.0, places=6)
        self.assertAlmostEqual(vote_signal("momentum_20d", {"Momentum_20d_%": 4.0}, signal_cfg), 0.5, places=6)
        self.assertAlmostEqual(vote_signal("momentum_20d", {"Momentum_20d_%": -5.0}, signal_cfg), -0.75, places=6)

    def test_predict_preserves_discrete_mode_by_default(self) -> None:
        signal_cfg = {
            "vote_rules": {"positive_threshold": 2.0, "negative_threshold": -2.0},
        }

        self.assertEqual(vote_signal("momentum_20d", {"Momentum_20d_%": 4.0}, signal_cfg), 1)
        self.assertEqual(vote_signal("momentum_20d", {"Momentum_20d_%": 0.5}, signal_cfg), 0)

    def test_vote_signal_adx_continuous_scales_strength_by_adx_magnitude(self) -> None:
        signal_cfg = {
            "vote_mode": "continuous",
            "vote_rules": {"adx_threshold": 20.0, "adx_saturation": 45.0},
        }
        # ADX=20 → en el umbral → strength=0
        self.assertAlmostEqual(vote_signal("adx", {"ADX_14": 20.0, "DI_plus_14": 30.0, "DI_minus_14": 15.0}, signal_cfg), 0.0, places=6)
        # ADX=32.5 → mitad del rango → strength=0.5
        self.assertAlmostEqual(vote_signal("adx", {"ADX_14": 32.5, "DI_plus_14": 30.0, "DI_minus_14": 15.0}, signal_cfg), 0.5, places=6)
        # ADX=45 → saturado → strength=1.0
        self.assertAlmostEqual(vote_signal("adx", {"ADX_14": 45.0, "DI_plus_14": 30.0, "DI_minus_14": 15.0}, signal_cfg), 1.0, places=6)
        # ADX=45, DI- dominante → strength=-1.0
        self.assertAlmostEqual(vote_signal("adx", {"ADX_14": 45.0, "DI_plus_14": 15.0, "DI_minus_14": 30.0}, signal_cfg), -1.0, places=6)

    def test_vote_signal_adx_continuous_neutral_below_threshold(self) -> None:
        signal_cfg = {
            "vote_mode": "continuous",
            "vote_rules": {"adx_threshold": 20.0, "adx_saturation": 45.0},
        }
        self.assertAlmostEqual(vote_signal("adx", {"ADX_14": 15.0, "DI_plus_14": 30.0, "DI_minus_14": 10.0}, signal_cfg), 0.0, places=6)

    def test_vote_signal_adx_bullish_when_above_threshold_and_di_plus_dominates(self) -> None:
        signal_cfg = {"vote_rules": {"adx_threshold": 20.0}}
        row = {"ADX_14": 28.0, "DI_plus_14": 30.0, "DI_minus_14": 18.0}
        self.assertEqual(vote_signal("adx", row, signal_cfg), 1)

    def test_vote_signal_adx_bearish_when_above_threshold_and_di_minus_dominates(self) -> None:
        signal_cfg = {"vote_rules": {"adx_threshold": 20.0}}
        row = {"ADX_14": 25.0, "DI_plus_14": 14.0, "DI_minus_14": 32.0}
        self.assertEqual(vote_signal("adx", row, signal_cfg), -1)

    def test_vote_signal_adx_neutral_when_below_threshold(self) -> None:
        signal_cfg = {"vote_rules": {"adx_threshold": 20.0}}
        row = {"ADX_14": 15.0, "DI_plus_14": 30.0, "DI_minus_14": 10.0}
        self.assertEqual(vote_signal("adx", row, signal_cfg), 0)

    def test_vote_signal_adx_neutral_when_values_missing(self) -> None:
        signal_cfg = {"vote_rules": {"adx_threshold": 20.0}}
        row = {"ADX_14": None, "DI_plus_14": None, "DI_minus_14": None}
        self.assertEqual(vote_signal("adx", row, signal_cfg), 0)

    def test_vote_signal_relative_volume_bullish_when_high_volume_and_positive_return(self) -> None:
        signal_cfg = {"vote_rules": {"high_threshold": 1.5}}
        row = {"Relative_Volume": 2.0, "Return_intraday_%": 1.5}
        self.assertEqual(vote_signal("relative_volume", row, signal_cfg), 1)

    def test_vote_signal_relative_volume_bearish_when_high_volume_and_negative_return(self) -> None:
        signal_cfg = {"vote_rules": {"high_threshold": 1.5}}
        row = {"Relative_Volume": 2.5, "Return_intraday_%": -0.8}
        self.assertEqual(vote_signal("relative_volume", row, signal_cfg), -1)

    def test_vote_signal_relative_volume_neutral_when_below_threshold(self) -> None:
        signal_cfg = {"vote_rules": {"high_threshold": 1.5}}
        row = {"Relative_Volume": 0.9, "Return_intraday_%": 3.0}
        self.assertEqual(vote_signal("relative_volume", row, signal_cfg), 0)

    def test_vote_signal_relative_volume_neutral_when_values_missing(self) -> None:
        signal_cfg = {"vote_rules": {"high_threshold": 1.5}}
        row = {"Relative_Volume": None, "Return_intraday_%": None}
        self.assertEqual(vote_signal("relative_volume", row, signal_cfg), 0)

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


    # ── sma_trend continuous ──────────────────────────────────────────────────

    def test_vote_trend_continuous_alcista_fuerte_returns_1(self) -> None:
        signal_cfg = {
            "vote_mode": "continuous",
            "vote_rules": {
                "graduated_votes": {
                    "Alcista fuerte": 1.0, "Alcista": 0.5,
                    "Bajista": -0.5, "Bajista fuerte": -1.0,
                }
            },
        }
        self.assertAlmostEqual(vote_signal("sma_trend", {"Tech_Trend": "Alcista fuerte"}, signal_cfg), 1.0, places=6)

    def test_vote_trend_continuous_alcista_returns_half(self) -> None:
        signal_cfg = {
            "vote_mode": "continuous",
            "vote_rules": {"graduated_votes": {"Alcista fuerte": 1.0, "Alcista": 0.5, "Bajista": -0.5, "Bajista fuerte": -1.0}},
        }
        self.assertAlmostEqual(vote_signal("sma_trend", {"Tech_Trend": "Alcista"}, signal_cfg), 0.5, places=6)

    def test_vote_trend_continuous_bajista_fuerte_returns_minus_1(self) -> None:
        signal_cfg = {
            "vote_mode": "continuous",
            "vote_rules": {"graduated_votes": {"Alcista fuerte": 1.0, "Alcista": 0.5, "Bajista": -0.5, "Bajista fuerte": -1.0}},
        }
        self.assertAlmostEqual(vote_signal("sma_trend", {"Tech_Trend": "Bajista fuerte"}, signal_cfg), -1.0, places=6)

    def test_vote_trend_continuous_neutral_label_returns_zero(self) -> None:
        signal_cfg = {
            "vote_mode": "continuous",
            "vote_rules": {"graduated_votes": {"Alcista fuerte": 1.0, "Alcista": 0.5, "Bajista": -0.5, "Bajista fuerte": -1.0}},
        }
        self.assertAlmostEqual(vote_signal("sma_trend", {"Tech_Trend": "Neutral"}, signal_cfg), 0.0, places=6)

    # ── relative_volume continuous ────────────────────────────────────────────

    def test_vote_relative_volume_continuous_bullish_scales_with_volume(self) -> None:
        # rel_vol=2.25 → midpoint of [1.5, 3.0] → strength=0.5, positive return → 0.5
        signal_cfg = {
            "vote_mode": "continuous",
            "vote_rules": {"high_threshold": 1.5, "high_saturation": 3.0},
        }
        self.assertAlmostEqual(
            vote_signal("relative_volume", {"Relative_Volume": 2.25, "Return_intraday_%": 1.2}, signal_cfg),
            0.5, places=5,
        )

    def test_vote_relative_volume_continuous_bearish_scales_with_volume(self) -> None:
        # rel_vol=3.0 → saturado → strength=1.0, negative return → -1.0
        signal_cfg = {
            "vote_mode": "continuous",
            "vote_rules": {"high_threshold": 1.5, "high_saturation": 3.0},
        }
        self.assertAlmostEqual(
            vote_signal("relative_volume", {"Relative_Volume": 3.0, "Return_intraday_%": -0.5}, signal_cfg),
            -1.0, places=5,
        )

    def test_vote_relative_volume_continuous_neutral_below_threshold(self) -> None:
        signal_cfg = {
            "vote_mode": "continuous",
            "vote_rules": {"high_threshold": 1.5, "high_saturation": 3.0},
        }
        self.assertAlmostEqual(
            vote_signal("relative_volume", {"Relative_Volume": 1.2, "Return_intraday_%": 2.0}, signal_cfg),
            0.0, places=6,
        )

    def test_vote_relative_volume_continuous_neutral_when_missing(self) -> None:
        signal_cfg = {
            "vote_mode": "continuous",
            "vote_rules": {"high_threshold": 1.5, "high_saturation": 3.0},
        }
        self.assertAlmostEqual(
            vote_signal("relative_volume", {"Relative_Volume": None, "Return_intraday_%": None}, signal_cfg),
            0.0, places=6,
        )


if __name__ == "__main__":
    unittest.main()
