import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from portfolio.operations import (
    build_pending_trade_portfolio_rows,
    build_operations_bundle,
    enrich_operations_bundle,
    build_position_transition_bundle,
    infer_trade_vn_factor,
    normalize_iol_operations,
)


class OperationsBundleTests(unittest.TestCase):
    def test_infer_trade_vn_factor_detects_bond_scale_from_trade_amount(self) -> None:
        factor = infer_trade_vn_factor(quantity=102127, price=117, amount=119008.59)

        self.assertEqual(factor, 100.0)

    def test_normalize_iol_operations_builds_final_fields_and_sorting(self) -> None:
        df = normalize_iol_operations(
            [
                {
                    "numero": 2,
                    "fechaOrden": "2026-04-16T12:54:14",
                    "fechaOperada": "2026-04-16T12:54:19",
                    "tipo": "Compra",
                    "estado": "terminada",
                    "simbolo": "GOOGL",
                    "cantidad": 126600,
                    "cantidadOperada": 14,
                    "precioOperado": 8440,
                    "montoOperado": 118160,
                },
                {
                    "numero": 1,
                    "fechaOrden": "2026-04-13T15:39:56",
                    "fechaOperada": "2026-04-13T15:39:56",
                    "tipo": "Pago de Dividendos",
                    "estado": "terminada",
                    "simbolo": "DIA US$",
                    "montoOperado": 0.06,
                },
            ]
        )

        self.assertEqual(df.loc[0, "simbolo"], "GOOGL")
        self.assertEqual(df.loc[0, "operation_bucket"], "trading")
        self.assertEqual(df.loc[1, "operation_bucket"], "evento")
        self.assertEqual(df.loc[0, "cantidad_final"], 14)
        self.assertEqual(df.loc[0, "monto_final"], 118160)

    def test_normalize_iol_operations_handles_missing_numero(self) -> None:
        df = normalize_iol_operations(
            [
                {
                    "fechaOperada": "2026-04-16T12:54:19",
                    "tipo": "Compra",
                    "estado": "terminada",
                    "simbolo": "GOOGL",
                    "cantidadOperada": 14,
                    "montoOperado": 118160,
                }
            ]
        )

        self.assertEqual(len(df), 1)
        self.assertTrue(pd.isna(df.loc[0, "numero"]))
        self.assertEqual(df.loc[0, "operation_bucket"], "trading")

    def test_normalize_iol_operations_normalizes_amortizacion_label(self) -> None:
        df = normalize_iol_operations(
            [
                {
                    "numero": 3,
                    "fechaOperada": "2026-04-13T15:39:56",
                    "tipo": "Pago de AmortizaciÃ³n",
                    "estado": "terminada",
                    "simbolo": "AL30",
                    "montoOperado": 1200,
                }
            ]
        )

        self.assertEqual(df.loc[0, "tipo"], "Pago de Amortización")
        self.assertEqual(df.loc[0, "operation_bucket"], "evento")

    def test_build_operations_bundle_separates_trades_events_and_summary(self) -> None:
        bundle = build_operations_bundle(
            [
                {
                    "numero": 170860042,
                    "fechaOrden": "2026-04-16T12:54:14.037",
                    "fechaOperada": "2026-04-16T12:54:19",
                    "tipo": "Compra",
                    "estado": "terminada",
                    "mercado": "BCBA",
                    "simbolo": "GOOGL",
                    "cantidadOperada": 14,
                    "precioOperado": 8440,
                    "montoOperado": 118160,
                    "plazo": "a24horas",
                },
                {
                    "numero": 170443236,
                    "fechaOrden": "2026-04-13T15:39:56.647",
                    "fechaOperada": "2026-04-13T15:39:56.647",
                    "tipo": "Pago de Dividendos",
                    "estado": "terminada",
                    "mercado": "BCBA",
                    "simbolo": "DIA US$",
                    "montoOperado": 0.06,
                    "plazo": "inmediata",
                },
            ]
        )

        self.assertEqual(bundle["stats"]["total"], 2)
        self.assertEqual(bundle["stats"]["trading"], 1)
        self.assertEqual(bundle["stats"]["events"], 1)
        self.assertFalse(bundle["recent_trades"].empty)
        self.assertFalse(bundle["recent_events"].empty)
        self.assertFalse(bundle["symbol_summary"].empty)
        self.assertEqual(bundle["symbol_summary"].iloc[0]["simbolo"], "GOOGL")
        self.assertNotIn("position_transitions", bundle)

    def test_build_operations_bundle_no_longer_includes_position_transitions_stub(self) -> None:
        bundle = build_operations_bundle([])

        self.assertNotIn("position_transitions", bundle)

    def test_enrich_operations_bundle_populates_transitions_and_snapshot_date(self) -> None:
        operations_bundle = build_operations_bundle(
            [
                {
                    "numero": 170860042,
                    "fechaOperada": "2026-04-16T12:54:19",
                    "tipo": "Compra",
                    "estado": "terminada",
                    "simbolo": "GOOGL",
                    "cantidadOperada": 14,
                    "montoOperado": 118160,
                }
            ]
        )
        current_portfolio = pd.DataFrame(
            [
                {"Ticker_IOL": "GOOGL", "Tipo": "CEDEAR", "Bloque": "Growth", "Cantidad": 34, "Peso_%": 1.17, "Valorizado_ARS": 285940},
            ]
        )
        previous_portfolio = pd.DataFrame(
            [
                {"Ticker_IOL": "GOOGL", "Tipo": "CEDEAR", "Bloque": "Growth", "Cantidad": 20, "Peso_%": 0.69, "Valorizado_ARS": 169200},
            ]
        )

        enriched = enrich_operations_bundle(
            operations_bundle,
            current_portfolio=current_portfolio,
            previous_portfolio=previous_portfolio,
            previous_snapshot_date="2026-04-15",
        )

        self.assertEqual(enriched["previous_snapshot_date"], "2026-04-15")
        self.assertFalse(enriched["position_transitions"]["summary"].empty)
        self.assertEqual(enriched["position_transitions"]["summary"].iloc[0]["simbolo"], "GOOGL")

    def test_build_position_transition_bundle_detects_new_increase_and_exit(self) -> None:
        current_portfolio = pd.DataFrame(
            [
                {"Ticker_IOL": "GOOGL", "Tipo": "CEDEAR", "Bloque": "Growth", "Cantidad": 34, "Peso_%": 1.17, "Valorizado_ARS": 285940},
                {"Ticker_IOL": "PAMP", "Tipo": "Acción Local", "Bloque": "Sin clasificar", "Cantidad": 42, "Peso_%": 0.83, "Valorizado_ARS": 201495},
            ]
        )
        previous_portfolio = pd.DataFrame(
            [
                {"Ticker_IOL": "GOOGL", "Tipo": "CEDEAR", "Bloque": "Growth", "Cantidad": 20, "Peso_%": 0.69, "Valorizado_ARS": 169200},
                {"Ticker_IOL": "AL30D", "Tipo": "Bono", "Bloque": "Soberano AR", "Cantidad": 1040, "Peso_%": 0.40, "Valorizado_ARS": 600},
            ]
        )
        recent_operations = normalize_iol_operations(
            [
                {
                    "numero": 170860042,
                    "fechaOperada": "2026-04-16T12:54:19",
                    "tipo": "Compra",
                    "estado": "terminada",
                    "simbolo": "GOOGL",
                    "cantidadOperada": 14,
                    "montoOperado": 118160,
                },
                {
                    "numero": 170859929,
                    "fechaOperada": "2026-04-16T12:53:40",
                    "tipo": "Compra",
                    "estado": "terminada",
                    "simbolo": "PAMP",
                    "cantidadOperada": 42,
                    "montoOperado": 201600,
                },
                {
                    "numero": 168909106,
                    "fechaOperada": "2026-03-31T10:58:49",
                    "tipo": "Venta",
                    "estado": "terminada",
                    "simbolo": "AL30D",
                    "cantidadOperada": 1040,
                    "montoOperado": 632.53,
                },
            ]
        )

        bundle = build_position_transition_bundle(
            current_portfolio,
            previous_portfolio,
            recent_operations=recent_operations,
            limit=6,
        )

        titles = [item["title"] for item in bundle["items"]]
        self.assertIn("Posicion ampliada", titles)
        self.assertIn("Nueva posicion incorporada", titles)
        self.assertIn("Posicion salida de cartera", titles)

    def test_build_position_transition_bundle_reclassification_vs_truly_new(self) -> None:
        # IOLPORA was "Liquidez" in the previous snapshot → reclassification (not a new buy)
        # PAMP was absent entirely from the previous snapshot → truly new
        current_portfolio = pd.DataFrame(
            [
                {"Ticker_IOL": "IOLPORA", "Tipo": "FCI", "Bloque": "Renta Fija ARS", "Cantidad": 100, "Peso_%": 2.0, "Valorizado_ARS": 500000},
                {"Ticker_IOL": "PAMP", "Tipo": "Acción Local", "Bloque": "Sin clasificar", "Cantidad": 42, "Peso_%": 0.83, "Valorizado_ARS": 201495},
            ]
        )
        previous_portfolio = pd.DataFrame(
            [
                {"Ticker_IOL": "IOLPORA", "Tipo": "Liquidez", "Bloque": "Efectivo", "Cantidad": 100, "Peso_%": 2.0, "Valorizado_ARS": 500000},
            ]
        )

        bundle = build_position_transition_bundle(current_portfolio, previous_portfolio, limit=6)

        by_kicker = {item["kicker"]: item for item in bundle["items"]}
        self.assertIn("IOLPORA", by_kicker)
        self.assertEqual(by_kicker["IOLPORA"]["title"], "Posicion reclasificada")
        self.assertIn("PAMP", by_kicker)
        self.assertEqual(by_kicker["PAMP"]["title"], "Nueva posicion incorporada")

        cambios = bundle["summary"].set_index("simbolo")["cambio"].to_dict()
        self.assertEqual(cambios["IOLPORA"], "reclasificacion")
        self.assertEqual(cambios["PAMP"], "alta_nueva")

    def test_build_pending_trade_portfolio_rows_builds_pending_bond_row(self) -> None:
        recent_trades = normalize_iol_operations(
            [
                {
                    "numero": 170860257,
                    "fechaOperada": "2026-04-16T12:55:00",
                    "tipo": "Compra",
                    "estado": "terminada",
                    "simbolo": "S31G6",
                    "cantidadOperada": 102127,
                    "precioOperado": 117,
                    "montoOperado": 119008.59,
                }
            ]
        )

        out = build_pending_trade_portfolio_rows(
            recent_trades,
            current_portfolio=pd.DataFrame([{"Ticker_IOL": "AL30", "Tipo": "Bono"}]),
            prices_iol={"S31G6": 117.0},
            mep_real=1419.0,
            total_portfolio_ars=24834540.0,
        )

        self.assertEqual(len(out), 1)
        self.assertEqual(out.iloc[0]["Ticker_IOL"], "S31G6")
        self.assertEqual(out.iloc[0]["Tipo"], "Pendiente")
        self.assertAlmostEqual(float(out.iloc[0]["Cantidad_Real"]), 1021.27, places=2)
        self.assertAlmostEqual(float(out.iloc[0]["Valorizado_ARS"]), 119488.59, places=2)


if __name__ == "__main__":
    unittest.main()
