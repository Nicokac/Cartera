import math
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from decision.sizing import build_dynamic_allocation, build_operational_proposal, build_prudent_allocation


class SizingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.final_decision = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "T",
                    "Descripcion": "AT&T",
                    "Tipo": "CEDEAR",
                    "accion_sugerida_v2": "Refuerzo",
                    "score_unificado": 0.45,
                    "score_despliegue_liquidez": 0.0,
                    "Valorizado_ARS": 0.0,
                    "Valor_USD": 0.0,
                    "Tech_Trend": "Alcista fuerte",
                    "Beta": 0.7,
                },
                {
                    "Ticker_IOL": "VIST",
                    "Descripcion": "Vista",
                    "Tipo": "CEDEAR",
                    "accion_sugerida_v2": "Refuerzo",
                    "score_unificado": 0.35,
                    "score_despliegue_liquidez": 0.0,
                    "Valorizado_ARS": 0.0,
                    "Valor_USD": 0.0,
                    "Tech_Trend": "Alcista fuerte",
                    "Beta": 1.5,
                },
                {
                    "Ticker_IOL": "NVDA",
                    "Descripcion": "NVIDIA",
                    "Tipo": "CEDEAR",
                    "accion_sugerida_v2": "Reducir",
                    "score_unificado": -0.30,
                    "score_despliegue_liquidez": 0.0,
                    "Valorizado_ARS": 0.0,
                    "Valor_USD": 0.0,
                    "Tech_Trend": "Bajista",
                    "Beta": 1.8,
                },
                {
                    "Ticker_IOL": "GD30",
                    "Descripcion": "Bono GD30",
                    "Tipo": "Bono",
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "score_unificado": -0.25,
                    "score_despliegue_liquidez": 0.0,
                    "Valorizado_ARS": 0.0,
                    "Valor_USD": 0.0,
                    "Tech_Trend": None,
                    "Beta": None,
                },
                {
                    "Ticker_IOL": "CAUCION",
                    "Descripcion": "Caucion colocada",
                    "Tipo": "Liquidez",
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "score_unificado": 0.0,
                    "score_despliegue_liquidez": 0.9,
                    "Valorizado_ARS": 1000000.0,
                    "Valor_USD": 1000.0,
                    "Tech_Trend": None,
                    "Beta": None,
                },
            ]
        )
        self.bucket_weights = {"Defensivo": 1.0, "Intermedio": 0.75, "Agresivo": 0.5}

    def test_build_operational_proposal_selects_funding_source_and_amount(self) -> None:
        result = build_operational_proposal(self.final_decision, mep_real=1000)

        self.assertEqual(result["fuente_fondeo"], "CAUCION")
        self.assertTrue(math.isclose(result["pct_fondeo"], 0.20, rel_tol=0, abs_tol=0.001))
        self.assertTrue(math.isclose(result["monto_fondeo_ars"], 200000, rel_tol=0, abs_tol=0.01))
        self.assertEqual(result["top_reforzar_final"]["Ticker_IOL"].tolist(), ["T", "VIST"])
        self.assertEqual(result["top_bonos_rebalancear"]["Ticker_IOL"].tolist(), ["GD30"])

    def test_build_operational_proposal_supports_external_funding_without_using_iol_liquidity(self) -> None:
        result = build_operational_proposal(
            self.final_decision,
            mep_real=1000,
            usar_liquidez_iol=False,
            aporte_externo_ars=600000,
        )

        self.assertEqual(result["fuente_fondeo"], "Aporte externo")
        self.assertEqual(result["usar_liquidez_iol"], False)
        self.assertTrue(math.isclose(result["pct_fondeo"], 0.0, rel_tol=0, abs_tol=0.001))
        self.assertTrue(math.isclose(result["aporte_externo_ars"], 600000, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(result["monto_fondeo_liquidez_ars"], 0, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(result["monto_fondeo_ars"], 600000, rel_tol=0, abs_tol=0.01))
        self.assertEqual(result["top_fondeo"].shape[0], 0)
        self.assertEqual(
            result["propuesta"].loc[result["propuesta"]["Ticker_IOL"] == "CAUCION", "accion_operativa"].iloc[0],
            "Mantener liquidez bloqueada",
        )

    def test_build_operational_proposal_no_longer_prefers_caucion_by_name(self) -> None:
        extra_row = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "ADBAICA",
                    "Descripcion": "FCI cobertura",
                    "Tipo": "Liquidez",
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "score_unificado": 0.0,
                    "score_despliegue_liquidez": 0.95,
                    "Valorizado_ARS": 1200000.0,
                    "Valor_USD": 1200.0,
                    "Tech_Trend": None,
                    "Beta": math.nan,
                }
            ]
        )
        extra_row = extra_row.astype(self.final_decision.dtypes.to_dict())
        final_decision = pd.concat(
            [
                self.final_decision,
                extra_row,
            ],
            ignore_index=True,
        )

        result = build_operational_proposal(final_decision, mep_real=1000)

        self.assertEqual(result["fuente_fondeo"], "Fuentes multiples: ADBAICA, CAUCION")
        self.assertTrue(math.isclose(result["monto_fondeo_liquidez_ars"], 440000, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(result["monto_fondeo_liquidez_usd"], 440.0, rel_tol=0, abs_tol=0.01))

    def test_bond_subfamily_rebalance_threshold_is_not_overwritten_by_monitor_rule(self) -> None:
        final_decision = self.final_decision.copy()
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "score_unificado"] = -0.18
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "asset_subfamily"] = "bond_sov_ar"

        result = build_operational_proposal(
            final_decision,
            mep_real=1000,
            action_rules={
                "bono_rebalance_threshold": -0.20,
                "bono_monitor_min": -0.20,
                "bono_monitor_max": 0.08,
                "bond_subfamily_thresholds": {
                    "bond_sov_ar": {"rebalance_threshold": -0.12}
                },
            },
        )

        self.assertEqual(
            result["propuesta"].loc[result["propuesta"]["Ticker_IOL"] == "GD30", "accion_operativa"].iloc[0],
            "Rebalancear / tomar ganancia",
        )

    def test_bond_subfamily_comments_are_more_specific(self) -> None:
        final_decision = self.final_decision.copy()
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "asset_subfamily"] = "bond_sov_ar"
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_local_subfamily"] = "bond_hard_dollar"
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_paridad_pct"] = 87.2
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_tir_pct"] = 7.8
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "score_unificado"] = -0.18

        cer_row = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "TZX26",
                    "Descripcion": "Bono CER",
                    "Tipo": "Bono",
                    "asset_subfamily": "bond_cer",
                    "bonistas_local_subfamily": "bond_cer",
                    "bonistas_tir_pct": -8.1,
                    "bonistas_paridad_pct": 102.0,
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "score_unificado": -0.01,
                    "score_despliegue_liquidez": 0.0,
                    "Valorizado_ARS": 0.0,
                    "Valor_USD": 0.0,
                    "Tech_Trend": None,
                    "Beta": None,
                }
            ]
        )
        cer_row = cer_row.astype(final_decision.dtypes.to_dict())
        final_decision = pd.concat([final_decision, cer_row], ignore_index=True)

        result = build_operational_proposal(final_decision, mep_real=1000)
        propuesta = result["propuesta"]

        gd30_comment = propuesta.loc[propuesta["Ticker_IOL"] == "GD30", "comentario_operativo"].iloc[0]
        tzx26_comment = propuesta.loc[propuesta["Ticker_IOL"] == "TZX26", "comentario_operativo"].iloc[0]

        self.assertIn("Hard-dollar", gd30_comment)
        self.assertIn("CER", tzx26_comment)

    def test_bond_local_subfamily_comments_use_bonistas_context_when_available(self) -> None:
        final_decision = self.final_decision.copy()
        final_decision["bonistas_local_subfamily"] = None
        final_decision["bonistas_tir_pct"] = None
        final_decision["bonistas_paridad_pct"] = None
        final_decision["bonistas_md"] = None
        final_decision["bonistas_put_flag"] = None
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "asset_subfamily"] = "bond_sov_ar"
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_local_subfamily"] = "bond_hard_dollar"
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_paridad_pct"] = 87.2
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_tir_pct"] = 7.8
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_md"] = 2.05
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_riesgo_pais_bps"] = 720.0
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_spread_vs_ust_pct"] = 3.8
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_reservas_bcra_musd"] = 43381.0
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_a3500_mayorista"] = 1387.72
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_rem_inflacion_mensual_pct"] = 2.7
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "score_unificado"] = -0.18

        bpoc7_row = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "BPOC7",
                    "Descripcion": "Bopreal",
                    "Tipo": "Bono",
                    "asset_subfamily": "bond_bopreal",
                    "bonistas_local_subfamily": "bond_bopreal",
                    "bonistas_tir_pct": 3.4,
                    "bonistas_paridad_pct": 102.0,
                    "bonistas_put_flag": True,
                    "bonistas_rem_inflacion_mensual_pct": 2.7,
                    "bonistas_riesgo_pais_bps": 720.0,
                    "bonistas_spread_vs_ust_pct": -0.5,
                    "bonistas_reservas_bcra_musd": 43381.0,
                    "bonistas_a3500_mayorista": 1387.72,
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "score_unificado": -0.03,
                    "score_despliegue_liquidez": 0.0,
                    "Valorizado_ARS": 0.0,
                    "Valor_USD": 0.0,
                    "Tech_Trend": None,
                    "Beta": None,
                }
            ]
        )
        bpoc7_row = bpoc7_row.reindex(columns=final_decision.columns, fill_value=None)
        final_decision.loc[len(final_decision)] = bpoc7_row.iloc[0]

        result = build_operational_proposal(final_decision, mep_real=1000)
        propuesta = result["propuesta"]

        gd30_comment = propuesta.loc[propuesta["Ticker_IOL"] == "GD30", "comentario_operativo"].iloc[0]
        bpoc7_comment = propuesta.loc[propuesta["Ticker_IOL"] == "BPOC7", "comentario_operativo"].iloc[0]

        self.assertIn("Hard-dollar", gd30_comment)
        self.assertIn("paridad 87.2%", gd30_comment)
        self.assertIn("720 bps", gd30_comment)
        self.assertIn("spread 3.8% sobre UST", gd30_comment)
        self.assertIn("reservas 43381 MUSD", gd30_comment)
        self.assertIn("A3500 1387.72", gd30_comment)
        self.assertIn("PUT", bpoc7_comment)
        self.assertIn("reservas 43381 MUSD", bpoc7_comment)
        self.assertIn("A3500 1387.72", bpoc7_comment)

    def test_cer_comment_uses_rem_inflation_when_available(self) -> None:
        final_decision = self.final_decision.copy()
        final_decision["bonistas_local_subfamily"] = None
        final_decision["bonistas_tir_pct"] = None
        final_decision["bonistas_paridad_pct"] = None
        final_decision["bonistas_rem_inflacion_mensual_pct"] = None
        final_decision["bonistas_rem_inflacion_12m_pct"] = None

        cer_row = {
            "Ticker_IOL": "TZX26",
            "Descripcion": "Bono CER",
            "Tipo": "Bono",
            "asset_subfamily": "bond_cer",
            "bonistas_local_subfamily": "bond_cer",
            "bonistas_tir_pct": -8.1,
            "bonistas_paridad_pct": 102.0,
            "bonistas_rem_inflacion_mensual_pct": 2.7,
            "bonistas_rem_inflacion_12m_pct": 24.6,
            "accion_sugerida_v2": "Mantener / Neutral",
            "score_unificado": -0.01,
            "score_despliegue_liquidez": 0.0,
            "Valorizado_ARS": 0.0,
            "Valor_USD": 0.0,
            "Tech_Trend": None,
            "Beta": None,
        }
        for col in final_decision.columns:
            cer_row.setdefault(col, None)
        final_decision.loc[len(final_decision)] = cer_row

        result = build_operational_proposal(final_decision, mep_real=1000)
        propuesta = result["propuesta"]
        tzx26_comment = propuesta.loc[propuesta["Ticker_IOL"] == "TZX26", "comentario_operativo"].iloc[0]

        self.assertIn("REM 12m 24.6%", tzx26_comment)
        self.assertIn("REM mensual 2.7%", tzx26_comment)

    def test_cedear_keeps_enriched_action_reason_in_operational_comment(self) -> None:
        final_decision = self.final_decision.copy()
        final_decision.loc[final_decision["Ticker_IOL"] == "T", "motivo_accion"] = (
            "Refuerzo por beta controlada y momentum fuerte."
        )

        result = build_operational_proposal(final_decision, mep_real=1000)
        propuesta = result["propuesta"]
        t_comment = propuesta.loc[propuesta["Ticker_IOL"] == "T", "comentario_operativo"].iloc[0]

        self.assertEqual(t_comment, "Refuerzo por beta controlada y momentum fuerte.")

    def test_prudent_and_dynamic_allocation_apply_buckets_and_caps(self) -> None:
        proposal_bundle = build_operational_proposal(self.final_decision, mep_real=1000)
        propuesta = proposal_bundle["propuesta"]

        prudente = build_prudent_allocation(
            propuesta,
            monto_fondeo_ars=proposal_bundle["monto_fondeo_ars"],
            monto_fondeo_usd=proposal_bundle["monto_fondeo_usd"],
            mep_real=1000,
            bucket_weights=self.bucket_weights,
        )
        dinamica = build_dynamic_allocation(
            proposal_bundle["top_reforzar_final"],
            monto_fondeo_ars=proposal_bundle["monto_fondeo_ars"],
            monto_fondeo_usd=proposal_bundle["monto_fondeo_usd"],
            mep_real=1000,
            bucket_weights=self.bucket_weights,
        )

        self.assertEqual(prudente.iloc[0]["Ticker_IOL"], "T")
        self.assertEqual(prudente.iloc[0]["Bucket_Prudencia"], "Defensivo")
        self.assertEqual(prudente.iloc[1]["Bucket_Prudencia"], "Agresivo")
        self.assertLessEqual(prudente["Asignacion_Final_ARS"].max(), 130000)
        self.assertTrue(math.isclose(prudente["Asignacion_Final_ARS"].sum(), 200000, rel_tol=0, abs_tol=1))

        self.assertEqual(dinamica.iloc[0]["Ticker_IOL"], "T")
        self.assertLessEqual(dinamica["Peso_Fondeo_%"].max(), 65.0)
        self.assertTrue(math.isclose(dinamica["Monto_ARS"].sum(), 200000, rel_tol=0, abs_tol=1))


if __name__ == "__main__":
    unittest.main()
