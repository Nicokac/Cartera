import math
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from decision.sizing import (
    _comentario_operativo,
    _format_funding_sources,
    _join_with_y,
    build_dynamic_allocation,
    build_operational_proposal,
    build_prudent_allocation,
)
from decision.action_constants import ACTION_MANTENER_MONITOREAR, ACTION_REBALANCEAR, ACTION_REFUERZO


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
        self.assertTrue(result["descartados_reforzar"].empty)
        self.assertTrue(result["descartados_reducir"].empty)
        self.assertTrue(result["descartados_rebalancear"].empty)
        self.assertTrue(result["descartados_fondeo"].empty)

    def test_build_operational_proposal_exposes_discarded_candidates_beyond_top_limit(self) -> None:
        extra_rows = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "KO",
                    "Descripcion": "Coca Cola",
                    "Tipo": "CEDEAR",
                    "accion_sugerida_v2": "Refuerzo",
                    "score_unificado": 0.30,
                    "score_despliegue_liquidez": 0.0,
                    "Valorizado_ARS": 0.0,
                    "Valor_USD": 0.0,
                    "Tech_Trend": "Alcista",
                    "Beta": 0.8,
                },
                {
                    "Ticker_IOL": "MELI",
                    "Descripcion": "Mercado Libre",
                    "Tipo": "CEDEAR",
                    "accion_sugerida_v2": "Reducir",
                    "score_unificado": -0.40,
                    "score_despliegue_liquidez": 0.0,
                    "Valorizado_ARS": 0.0,
                    "Valor_USD": 0.0,
                    "Tech_Trend": "Bajista",
                    "Beta": 1.9,
                },
                {
                    "Ticker_IOL": "AL30",
                    "Descripcion": "Bono AL30",
                    "Tipo": "Bono",
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "score_unificado": -0.27,
                    "score_despliegue_liquidez": 0.0,
                    "Valorizado_ARS": 0.0,
                    "Valor_USD": 0.0,
                    "Tech_Trend": None,
                    "Beta": None,
                },
                {
                    "Ticker_IOL": "IOLPORA",
                    "Descripcion": "FCI IOL Portfolio Potenciado",
                    "Tipo": "FCI",
                    "Es_Liquidez": False,
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "score_unificado": 0.0,
                    "score_despliegue_liquidez": 0.8,
                    "Valorizado_ARS": 500000.0,
                    "Valor_USD": 500.0,
                    "Tech_Trend": None,
                    "Beta": None,
                },
            ]
        )
        extra_rows = extra_rows.astype(self.final_decision.dtypes.to_dict())
        final_decision = pd.concat([self.final_decision, extra_rows], ignore_index=True)

        result = build_operational_proposal(final_decision, mep_real=1000, sizing_rules={"top_candidates": 1})

        self.assertEqual(result["top_reforzar_final"]["Ticker_IOL"].tolist(), ["T"])
        self.assertEqual(result["descartados_reforzar"]["Ticker_IOL"].tolist(), ["VIST", "KO"])
        self.assertEqual(result["top_reducir_final"]["Ticker_IOL"].tolist(), ["MELI"])
        self.assertEqual(result["descartados_reducir"]["Ticker_IOL"].tolist(), ["NVDA"])
        self.assertEqual(result["top_bonos_rebalancear"]["Ticker_IOL"].tolist(), ["AL30"])
        self.assertEqual(result["descartados_rebalancear"]["Ticker_IOL"].tolist(), ["GD30"])
        self.assertEqual(result["top_fondeo"]["Ticker_IOL"].tolist(), ["CAUCION"])
        self.assertTrue(result["descartados_fondeo"].empty)

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

    def test_build_operational_proposal_excludes_adbaica_when_it_is_a_real_fci(self) -> None:
        extra_row = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "ADBAICA",
                    "Descripcion": "FCI cobertura",
                    "Tipo": "FCI",
                    "Es_Liquidez": False,
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

        self.assertEqual(result["fuente_fondeo"], "CAUCION")
        self.assertTrue(math.isclose(result["monto_fondeo_liquidez_ars"], 200000, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(result["monto_fondeo_liquidez_usd"], 200.0, rel_tol=0, abs_tol=0.01))
        self.assertNotIn("ADBAICA", result["top_fondeo"]["Ticker_IOL"].tolist())

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

    def test_bond_subfamily_can_emit_refuerzo_when_threshold_is_met(self) -> None:
        final_decision = self.final_decision.copy()
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "asset_subfamily"] = "bond_other"
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_local_subfamily"] = "bond_cer"
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_tir_pct"] = -0.5
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_paridad_pct"] = 99.5
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_rem_inflacion_mensual_pct"] = 2.7
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "bonistas_rem_inflacion_12m_pct"] = 22.2
        final_decision.loc[final_decision["Ticker_IOL"] == "GD30", "score_unificado"] = 0.16

        result = build_operational_proposal(
            final_decision,
            mep_real=1000,
            action_rules={
                "bono_rebalance_threshold": -0.20,
                "bono_monitor_max": 0.08,
                "bond_subfamily_thresholds": {
                    "bond_other": {"refuerzo_threshold": 0.15}
                },
            },
        )

        accion = result["propuesta"].loc[result["propuesta"]["Ticker_IOL"] == "GD30", "accion_operativa"].iloc[0]
        comentario = result["propuesta"].loc[result["propuesta"]["Ticker_IOL"] == "GD30", "comentario_operativo"].iloc[0]

        self.assertEqual(accion, "Refuerzo")
        self.assertIn("Refuerzo CER", comentario)
        self.assertIn("REM 12m 22.2%", comentario)

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
        final_decision = pd.DataFrame.from_records(
            [*final_decision.to_dict("records"), bpoc7_row.iloc[0].to_dict()],
            columns=final_decision.columns,
        )

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
        final_decision = pd.DataFrame.from_records(
            [*final_decision.to_dict("records"), cer_row],
            columns=final_decision.columns,
        )

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


class SizingBranchTests(unittest.TestCase):
    def test_join_and_format_funding_helpers(self) -> None:
        self.assertEqual(_join_with_y([]), "")
        self.assertEqual(_join_with_y(["A"]), "A")
        self.assertEqual(_join_with_y(["A", "B", "C"]), "A, B y C")
        self.assertIsNone(_format_funding_sources([]))
        self.assertEqual(_format_funding_sources(["CAUCION"]), "CAUCION")
        self.assertIn("Fuentes multiples", _format_funding_sources(["CAUCION", "CASH_USD"]))

    def test_comentario_operativo_key_paths(self) -> None:
        row_hard = pd.Series(
            {
                "accion_operativa": ACTION_MANTENER_MONITOREAR,
                "bonistas_local_subfamily": "bond_hard_dollar",
                "bonistas_paridad_pct": 88.1,
                "bonistas_tir_pct": 7.1,
                "bonistas_riesgo_pais_bps": 710.0,
                "bonistas_spread_vs_ust_pct": 3.2,
                "bonistas_reservas_bcra_musd": 43000.0,
                "bonistas_a3500_mayorista": 1200.0,
            }
        )
        self.assertIn("Hard-dollar", _comentario_operativo(row_hard))

        row_cer = pd.Series(
            {
                "accion_operativa": "Refuerzo",
                "bonistas_local_subfamily": "bond_cer",
                "bonistas_tir_pct": -3.1,
                "bonistas_paridad_pct": 101.2,
                "bonistas_rem_inflacion_mensual_pct": 2.2,
                "bonistas_rem_inflacion_12m_pct": 21.5,
            }
        )
        self.assertIn("Refuerzo CER", _comentario_operativo(row_cer))

        row_bopreal = pd.Series(
            {
                "accion_operativa": ACTION_REBALANCEAR,
                "bonistas_local_subfamily": "bond_bopreal",
                "bonistas_paridad_pct": 102.0,
                "bonistas_put_flag": True,
                "bonistas_spread_vs_ust_pct": -0.8,
            }
        )
        self.assertIn("Bopreal", _comentario_operativo(row_bopreal))

        row_reducir = pd.Series({"accion_operativa": "Reducir", "Tech_Trend": "Bajista", "Beta": 1.7})
        self.assertIn("Reduccion", _comentario_operativo(row_reducir))

        row_liq = pd.Series({"accion_operativa": "Desplegar liquidez"})
        self.assertIn("Liquidez disponible", _comentario_operativo(row_liq))

        row_default = pd.Series({"accion_operativa": "Unknown"})
        self.assertIn("Mantener y monitorear", _comentario_operativo(row_default))

    def test_comentario_operativo_more_branches(self) -> None:
        row_rebalance_hard = pd.Series(
            {
                "accion_operativa": ACTION_REBALANCEAR,
                "bonistas_local_subfamily": "bond_hard_dollar",
                "bonistas_paridad_pct": 90.0,
                "bonistas_tir_pct": 9.0,
                "bonistas_riesgo_pais_bps": 800.0,
                "bonistas_spread_vs_ust_pct": 4.0,
            }
        )
        self.assertIn("Hard-dollar", _comentario_operativo(row_rebalance_hard))

        row_ref_bopreal = pd.Series(
            {
                "accion_operativa": ACTION_REFUERZO,
                "bonistas_local_subfamily": "bond_bopreal",
                "bonistas_paridad_pct": 101.0,
                "bonistas_tir_pct": 3.0,
                "bonistas_put_flag": True,
                "bonistas_spread_vs_ust_pct": -0.6,
            }
        )
        self.assertIn("Bopreal", _comentario_operativo(row_ref_bopreal))

        row_ref_other = pd.Series(
            {"accion_operativa": ACTION_REFUERZO, "asset_subfamily": "bond_other", "bonistas_tir_pct": 8.0, "bonistas_md": 2.0}
        )
        self.assertIn("bono local", _comentario_operativo(row_ref_other))

        row_mon_cer = pd.Series(
            {
                "accion_operativa": ACTION_MANTENER_MONITOREAR,
                "bonistas_local_subfamily": "bond_cer",
                "bonistas_tir_pct": -4.0,
                "bonistas_paridad_pct": 99.0,
                "bonistas_rem_inflacion_mensual_pct": 2.0,
                "bonistas_rem_inflacion_12m_pct": 20.0,
            }
        )
        self.assertIn("Bono CER en monitoreo", _comentario_operativo(row_mon_cer))

        row_mon_bopreal = pd.Series(
            {
                "accion_operativa": ACTION_MANTENER_MONITOREAR,
                "bonistas_local_subfamily": "bond_bopreal",
                "bonistas_paridad_pct": 103.0,
                "bonistas_put_flag": True,
                "bonistas_spread_vs_ust_pct": -0.5,
                "bonistas_riesgo_pais_bps": 700.0,
            }
        )
        self.assertIn("Bopreal en monitoreo", _comentario_operativo(row_mon_bopreal))

    def test_build_prudent_allocation_early_return(self) -> None:
        df = pd.DataFrame([{"accion_operativa": "Reducir", "score_unificado": -0.1}])
        out = build_prudent_allocation(
            df,
            monto_fondeo_ars=0,
            monto_fondeo_usd=0,
            mep_real=1000,
            bucket_weights={"Defensivo": 1.0, "Intermedio": 0.75, "Agresivo": 0.5},
        )
        self.assertTrue(out.empty or "accion_operativa" in out.columns)

    def test_operational_proposal_mixed_source_default_pct_and_equal_weights(self) -> None:
        final_decision = pd.DataFrame(
            [
                {
                    "Ticker_IOL": "A",
                    "Tipo": "CEDEAR",
                    "accion_sugerida_v2": "Refuerzo",
                    "score_unificado": -0.2,
                    "score_despliegue_liquidez": 0.0,
                    "Valorizado_ARS": 0.0,
                    "Valor_USD": 0.0,
                },
                {
                    "Ticker_IOL": "B",
                    "Tipo": "CEDEAR",
                    "accion_sugerida_v2": "Refuerzo",
                    "score_unificado": -0.1,
                    "score_despliegue_liquidez": 0.0,
                    "Valorizado_ARS": 0.0,
                    "Valor_USD": 0.0,
                },
                {
                    "Ticker_IOL": "CAUCION",
                    "Tipo": "Liquidez",
                    "accion_sugerida_v2": "Mantener / Neutral",
                    "score_unificado": 0.0,
                    "score_despliegue_liquidez": 0.9,
                    "Valorizado_ARS": 100000.0,
                    "Valor_USD": 100.0,
                },
            ]
        )
        out = build_operational_proposal(final_decision, mep_real=1000, aporte_externo_ars=50000)
        self.assertIn("Mixto", out["fuente_fondeo"])
        self.assertAlmostEqual(out["pct_fondeo"], 0.10, places=3)
        self.assertTrue((out["top_reforzar_final"]["Fondeo_Sugerido_ARS"].fillna(0) >= 0).all())

    def test_comentario_liquidez_variants(self) -> None:
        self.assertIn("reserva tactica", _comentario_operativo(pd.Series({"accion_operativa": "Mantener liquidez"})))
        self.assertIn(
            "excluida del fondeo",
            _comentario_operativo(pd.Series({"accion_operativa": "Mantener liquidez bloqueada"})),
        )

    def test_comentario_monitor_asset_subfamilies_and_reducir_variants(self) -> None:
        for sub, expected in [
            ("bond_cer", "Bono CER en zona neutral"),
            ("bond_bopreal", "Bopreal en zona prudente"),
            ("bond_other", "Bono sin clasificar"),
            ("bond_sov_ar", "Soberano AR sin senal extrema"),
        ]:
            txt = _comentario_operativo(pd.Series({"accion_operativa": ACTION_MANTENER_MONITOREAR, "asset_subfamily": sub}))
            self.assertIn(expected, txt)

        self.assertIn(
            "beta alta",
            _comentario_operativo(pd.Series({"accion_operativa": "Reducir", "Tech_Trend": "Lateral", "Beta": 1.6})),
        )
        self.assertIn(
            "score compuesto debil",
            _comentario_operativo(pd.Series({"accion_operativa": "Reducir", "Tech_Trend": "Lateral", "Beta": 1.0})),
        )

    def test_operational_proposal_without_funding_sets_nan_suggestions(self) -> None:
        final_decision = pd.DataFrame(
            [
                {"Ticker_IOL": "A", "Tipo": "CEDEAR", "accion_sugerida_v2": "Refuerzo", "score_unificado": 0.4, "score_despliegue_liquidez": 0.0, "Valorizado_ARS": 0.0, "Valor_USD": 0.0},
                {"Ticker_IOL": "B", "Tipo": "CEDEAR", "accion_sugerida_v2": "Refuerzo", "score_unificado": 0.3, "score_despliegue_liquidez": 0.0, "Valorizado_ARS": 0.0, "Valor_USD": 0.0},
            ]
        )
        out = build_operational_proposal(final_decision, mep_real=1000, usar_liquidez_iol=False, aporte_externo_ars=0)
        self.assertEqual(out["fuente_fondeo"], "Sin fondeo disponible")
        self.assertTrue(out["top_reforzar_final"]["Fondeo_Sugerido_ARS"].isna().all())

    def test_dynamic_allocation_bucket_defaults_and_empty(self) -> None:
        empty = build_dynamic_allocation(
            pd.DataFrame(),
            monto_fondeo_ars=1000,
            monto_fondeo_usd=1,
            mep_real=1000,
            bucket_weights={"Defensivo": 1.0, "Intermedio": 0.75, "Agresivo": 0.5},
        )
        self.assertTrue(empty.empty)

        df = pd.DataFrame(
            [
                {"Ticker_IOL": "BONO1", "Tipo": "Bono", "Es_Liquidez": False, "Peso_%": 2.0, "Beta": 0.2, "score_unificado": 0.3},
                {"Ticker_IOL": "EQ1", "Tipo": "CEDEAR", "Es_Liquidez": False, "Peso_%": 10.0, "Beta": 1.0, "score_unificado": 0.2},
            ]
        )
        out = build_dynamic_allocation(
            df,
            monto_fondeo_ars=100000,
            monto_fondeo_usd=100,
            mep_real=1000,
            bucket_weights={"Defensivo": 1.0, "Intermedio": 0.75, "Agresivo": 0.5},
            sizing_rules={"bucket_type_defaults": {"Bono": "Defensivo"}},
        )
        self.assertIn("Bucket_Prudencia", out.columns)

if __name__ == "__main__":
    unittest.main()
