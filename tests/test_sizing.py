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

    def test_prudent_and_dynamic_allocation_apply_buckets_and_caps(self) -> None:
        proposal_bundle = build_operational_proposal(self.final_decision, mep_real=1000)
        propuesta = proposal_bundle["propuesta"]

        prudente = build_prudent_allocation(
            propuesta,
            monto_fondeo_ars=proposal_bundle["monto_fondeo_ars"],
            monto_fondeo_usd=proposal_bundle["monto_fondeo_usd"],
            mep_real=1000,
            defensive_tickers={"T"},
            aggressive_tickers={"VIST"},
            bucket_weights=self.bucket_weights,
        )
        dinamica = build_dynamic_allocation(
            proposal_bundle["top_reforzar_final"],
            monto_fondeo_ars=proposal_bundle["monto_fondeo_ars"],
            monto_fondeo_usd=proposal_bundle["monto_fondeo_usd"],
            mep_real=1000,
            defensive_tickers={"T"},
            aggressive_tickers={"VIST"},
            bucket_weights=self.bucket_weights,
        )

        self.assertEqual(prudente.iloc[0]["Ticker_IOL"], "T")
        self.assertLessEqual(prudente["Asignacion_Final_ARS"].max(), 130000)
        self.assertTrue(math.isclose(prudente["Asignacion_Final_ARS"].sum(), 200000, rel_tol=0, abs_tol=1))

        self.assertEqual(dinamica.iloc[0]["Ticker_IOL"], "T")
        self.assertLessEqual(dinamica["Peso_Fondeo_%"].max(), 65.0)
        self.assertTrue(math.isclose(dinamica["Monto_ARS"].sum(), 200000, rel_tol=0, abs_tol=1))


if __name__ == "__main__":
    unittest.main()
