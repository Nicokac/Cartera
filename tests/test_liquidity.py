import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from portfolio.liquidity import extract_estado_cuenta_components, rebuild_liquidity


class LiquidityTests(unittest.TestCase):
    def test_extract_estado_cuenta_components_distinguishes_immediate_and_pending(self) -> None:
        estado_payload = {
            "totalEnPesos": 250000,
            "cuentas": [
                {
                    "moneda": "Pesos",
                    "disponible": 150000,
                    "saldo": 180000,
                    "comprometido": 30000,
                    "saldos": [
                        {"liquidacion": "inmediato", "disponible": 100000},
                        {"liquidacion": "48hs", "disponible": 50000},
                    ],
                },
                {
                    "moneda": "Dolares",
                    "disponible": 200,
                    "saldo": 225,
                    "comprometido": 25,
                    "saldos": [
                        {"liquidacion": "inmediato", "disponible": 120},
                        {"liquidacion": "24hs", "disponible": 80},
                    ],
                },
            ],
        }

        result = extract_estado_cuenta_components(estado_payload)

        self.assertEqual(result["cash_immediate_ars"], 100000)
        self.assertEqual(result["cash_pending_ars"], 50000)
        self.assertEqual(result["cash_immediate_usd"], 120)
        self.assertEqual(result["cash_pending_usd"], 80)
        self.assertEqual(result["cash_saldo_ars"], 180000)
        self.assertEqual(result["cash_saldo_usd"], 225)
        self.assertEqual(result["cash_comprometido_ars"], 30000)
        self.assertEqual(result["cash_comprometido_usd"], 25)
        self.assertEqual(result["total_broker_en_pesos"], 250000)

    def test_rebuild_liquidity_builds_contract_and_converts_usd(self) -> None:
        activos = [
            {
                "valorizado": 50000,
                "gananciaDinero": 1200,
                "titulo": {
                    "simbolo": "CAU123",
                    "descripcion": "Caucion colocada",
                    "tipo": "CAUCION",
                    "moneda": "Pesos",
                },
            },
            {
                "valorizado": 100,
                "gananciaDinero": 0,
                "titulo": {
                    "simbolo": "FCI_USD",
                    "descripcion": "Fondo Dolar",
                    "tipo": "FCI",
                    "moneda": "USD",
                },
            },
        ]
        estado_payload = {
            "totalEnPesos": 300000,
            "cuentas": [
                {
                    "moneda": "Pesos",
                    "disponible": 100000,
                    "saldos": [{"liquidacion": "inmediato", "disponible": 100000}],
                },
                {
                    "moneda": "USD",
                    "disponible": 50,
                    "saldos": [{"liquidacion": "inmediato", "disponible": 50}],
                },
            ],
        }

        df_liquidez, contract, raw_rows = rebuild_liquidity(
            activos,
            estado_payload,
            mep_real=1000,
            fci_cash_management={"FCI_USD"},
        )

        self.assertEqual(len(raw_rows), 4)
        self.assertIn("CASH_ARS", df_liquidez["Ticker_IOL"].tolist())
        self.assertIn("CASH_USD", df_liquidez["Ticker_IOL"].tolist())
        self.assertNotIn("PEND_ARS", df_liquidez["Ticker_IOL"].tolist())
        self.assertNotIn("PEND_USD", df_liquidez["Ticker_IOL"].tolist())
        self.assertTrue(math.isclose(contract["cash_operativo_ars"], 150000, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(contract["cash_comprometido_ars"], 0, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(contract["caucion_tactica_ars"], 50000, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(contract["fci_estrategico_ars"], 100000, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isclose(contract["liquidez_desplegable_total_ars"], 300000, rel_tol=0, abs_tol=0.01))
        self.assertFalse(contract["duplicate_caucion_in_cash"])

    def test_rebuild_liquidity_treats_zero_mep_as_missing_without_dividing_by_zero(self) -> None:
        activos = [
            {
                "valorizado": 100,
                "gananciaDinero": 0,
                "titulo": {
                    "simbolo": "FCI_USD",
                    "descripcion": "Fondo Dolar",
                    "tipo": "FCI",
                    "moneda": "USD",
                },
            },
        ]
        estado_payload = {
            "totalEnPesos": 100000,
            "cuentas": [
                {
                    "moneda": "Pesos",
                    "disponible": 100000,
                    "saldos": [{"liquidacion": "inmediato", "disponible": 100000}],
                },
                {
                    "moneda": "USD",
                    "disponible": 50,
                    "saldos": [{"liquidacion": "inmediato", "disponible": 50}],
                },
            ],
        }

        df_liquidez, contract, _ = rebuild_liquidity(
            activos,
            estado_payload,
            mep_real=0.0,
            fci_cash_management={"FCI_USD"},
        )

        self.assertTrue(math.isclose(contract["cash_operativo_ars"], 100000, rel_tol=0, abs_tol=0.01))
        self.assertTrue(math.isnan(contract["cash_operativo_usd"]))
        self.assertTrue(math.isnan(contract["liquidez_desplegable_total_usd"]))
        fci_row = df_liquidez[df_liquidez["Ticker_IOL"] == "FCI_USD"].iloc[0]
        self.assertTrue(math.isnan(float(fci_row["Valorizado_ARS"])))
        self.assertEqual(float(fci_row["Valor_USD"]), 100.0)


if __name__ == "__main__":
    unittest.main()
