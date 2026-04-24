import sys
import unittest
from pathlib import Path
import shutil

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from analytics.portfolio_risk import build_portfolio_risk_bundle, load_portfolio_snapshot_history


class PortfolioRiskTests(unittest.TestCase):
    def test_load_portfolio_snapshot_history_reads_only_prior_snapshots(self) -> None:
        snapshots_dir = ROOT / "tmp_portfolio_risk_history"
        snapshots_dir.mkdir(exist_ok=True)
        first = snapshots_dir / "2026-04-20_real_portfolio_master.csv"
        second = snapshots_dir / "2026-04-21_real_portfolio_master.csv"
        future = snapshots_dir / "2026-04-23_real_portfolio_master.csv"
        invalid = snapshots_dir / "bad_real_portfolio_master.csv"
        first.write_text("Ticker_IOL,Valorizado_ARS\nAAPL,100\n", encoding="utf-8")
        second.write_text("Ticker_IOL,Valorizado_ARS\nAAPL,110\n", encoding="utf-8")
        future.write_text("Ticker_IOL,Valorizado_ARS\nAAPL,999\n", encoding="utf-8")
        invalid.write_text("foo,bar\n1,2\n", encoding="utf-8")
        self.addCleanup(lambda: first.unlink(missing_ok=True))
        self.addCleanup(lambda: second.unlink(missing_ok=True))
        self.addCleanup(lambda: future.unlink(missing_ok=True))
        self.addCleanup(lambda: invalid.unlink(missing_ok=True))
        self.addCleanup(lambda: shutil.rmtree(snapshots_dir, ignore_errors=True))

        history = load_portfolio_snapshot_history(
            "2026-04-23",
            snapshots_dirs=[snapshots_dir],
        )

        self.assertEqual(history["snapshot_date"].dt.strftime("%Y-%m-%d").unique().tolist(), ["2026-04-20", "2026-04-21"])
        self.assertEqual(len(history), 2)

    def test_build_portfolio_risk_bundle_computes_portfolio_and_position_metrics(self) -> None:
        snapshots_dir = ROOT / "tmp_portfolio_risk_bundle"
        snapshots_dir.mkdir(exist_ok=True)
        day1 = snapshots_dir / "2026-04-20_real_portfolio_master.csv"
        day2 = snapshots_dir / "2026-04-21_real_portfolio_master.csv"
        day3 = snapshots_dir / "2026-04-22_real_portfolio_master.csv"
        day1.write_text(
            "Ticker_IOL,Tipo,Bloque,Peso_%,Precio_ARS,Valorizado_ARS\nAAPL,CEDEAR,Growth,50,100,1000\nKO,CEDEAR,Dividendos,50,50,500\n",
            encoding="utf-8",
        )
        day2.write_text(
            "Ticker_IOL,Tipo,Bloque,Peso_%,Precio_ARS,Valorizado_ARS\nAAPL,CEDEAR,Growth,55,110,1100\nKO,CEDEAR,Dividendos,45,45,450\n",
            encoding="utf-8",
        )
        day3.write_text(
            "Ticker_IOL,Tipo,Bloque,Peso_%,Precio_ARS,Valorizado_ARS\nAAPL,CEDEAR,Growth,52,90,900\nKO,CEDEAR,Dividendos,48,47,470\n",
            encoding="utf-8",
        )
        self.addCleanup(lambda: day1.unlink(missing_ok=True))
        self.addCleanup(lambda: day2.unlink(missing_ok=True))
        self.addCleanup(lambda: day3.unlink(missing_ok=True))
        self.addCleanup(lambda: shutil.rmtree(snapshots_dir, ignore_errors=True))

        current = pd.DataFrame(
            [
                {"Ticker_IOL": "AAPL", "Tipo": "CEDEAR", "Bloque": "Growth", "Peso_%": 54.0, "Precio_ARS": 120.0, "Valorizado_ARS": 1200.0},
                {"Ticker_IOL": "KO", "Tipo": "CEDEAR", "Bloque": "Dividendos", "Peso_%": 46.0, "Precio_ARS": 46.0, "Valorizado_ARS": 460.0},
            ]
        )

        bundle = build_portfolio_risk_bundle(
            current,
            run_date="2026-04-23",
            snapshots_dirs=[snapshots_dir],
            total_ars=1660.0,
        )

        self.assertEqual(bundle["portfolio_summary"]["snapshots"], 4)
        self.assertEqual(bundle["portfolio_summary"]["desde"], "2026-04-20")
        self.assertEqual(bundle["portfolio_summary"]["hasta"], "2026-04-23")
        self.assertTrue(bundle["portfolio_summary"]["serie_agregada_confiable"])
        self.assertEqual(bundle["portfolio_summary"]["pasos_estables"], 3)
        self.assertEqual(bundle["portfolio_summary"]["pasos_totales"], 3)
        self.assertAlmostEqual(bundle["portfolio_summary"]["retorno_acum_pct"], 10.6667, places=3)
        self.assertAlmostEqual(bundle["portfolio_summary"]["drawdown_max_pct"], -11.6129, places=3)

        aapl = bundle["position_risk"].set_index("Ticker_IOL").loc["AAPL"]
        self.assertEqual(aapl["Base_Riesgo"], "Precio_ARS")
        self.assertEqual(aapl["Calidad_Historia"], "Robusta")
        self.assertAlmostEqual(float(aapl["Retorno_Acum_%"]), 20.0, places=3)
        self.assertAlmostEqual(float(aapl["Drawdown_Max_%"]), -18.1818, places=3)
        self.assertEqual(int(aapl["Observaciones"]), 4)

    def test_build_portfolio_risk_bundle_falls_back_to_valuation_when_price_is_missing(self) -> None:
        snapshots_dir = ROOT / "tmp_portfolio_risk_valuation"
        snapshots_dir.mkdir(exist_ok=True)
        day1 = snapshots_dir / "2026-04-20_real_portfolio_master.csv"
        day2 = snapshots_dir / "2026-04-21_real_portfolio_master.csv"
        day1.write_text("Ticker_IOL,Tipo,Bloque,Peso_%,Valorizado_ARS\nBOND1,Bono,Soberano AR,50,1000\n", encoding="utf-8")
        day2.write_text("Ticker_IOL,Tipo,Bloque,Peso_%,Valorizado_ARS\nBOND1,Bono,Soberano AR,55,1050\n", encoding="utf-8")
        self.addCleanup(lambda: day1.unlink(missing_ok=True))
        self.addCleanup(lambda: day2.unlink(missing_ok=True))
        self.addCleanup(lambda: shutil.rmtree(snapshots_dir, ignore_errors=True))

        current = pd.DataFrame(
            [
                {"Ticker_IOL": "BOND1", "Tipo": "Bono", "Bloque": "Soberano AR", "Peso_%": 60.0, "Valorizado_ARS": 1100.0},
            ]
        )

        bundle = build_portfolio_risk_bundle(
            current,
            run_date="2026-04-22",
            snapshots_dirs=[snapshots_dir],
            total_ars=1100.0,
        )

        row = bundle["position_risk"].iloc[0]
        self.assertEqual(row["Base_Riesgo"], "Valorizado_ARS")
        self.assertAlmostEqual(float(row["Retorno_Acum_%"]), 10.0, places=3)

    def test_build_portfolio_risk_bundle_excludes_fci_from_analysis(self) -> None:
        snapshots_dir = ROOT / "tmp_portfolio_risk_exclude_fci"
        snapshots_dir.mkdir(exist_ok=True)
        day1 = snapshots_dir / "2026-04-20_real_portfolio_master.csv"
        day2 = snapshots_dir / "2026-04-21_real_portfolio_master.csv"
        day1.write_text(
            "Ticker_IOL,Tipo,Bloque,Peso_%,Precio_ARS,Valorizado_ARS\n"
            "AAPL,CEDEAR,Growth,50,100,1000\n"
            "FCI1,FCI,FCI,50,,500\n",
            encoding="utf-8",
        )
        day2.write_text(
            "Ticker_IOL,Tipo,Bloque,Peso_%,Precio_ARS,Valorizado_ARS\n"
            "AAPL,CEDEAR,Growth,52,110,1100\n"
            "FCI1,FCI,FCI,48,,525\n",
            encoding="utf-8",
        )
        self.addCleanup(lambda: day1.unlink(missing_ok=True))
        self.addCleanup(lambda: day2.unlink(missing_ok=True))
        self.addCleanup(lambda: shutil.rmtree(snapshots_dir, ignore_errors=True))

        current = pd.DataFrame(
            [
                {"Ticker_IOL": "AAPL", "Tipo": "CEDEAR", "Bloque": "Growth", "Peso_%": 60.0, "Precio_ARS": 120.0, "Valorizado_ARS": 1200.0},
                {"Ticker_IOL": "FCI1", "Tipo": "FCI", "Bloque": "FCI", "Peso_%": 40.0, "Valorizado_ARS": 550.0},
            ]
        )

        bundle = build_portfolio_risk_bundle(
            current,
            run_date="2026-04-22",
            snapshots_dirs=[snapshots_dir],
            total_ars=1750.0,
        )

        self.assertEqual(bundle["position_risk"]["Ticker_IOL"].tolist(), ["AAPL"])
        self.assertEqual(bundle["portfolio_summary"]["snapshots"], 3)
        self.assertAlmostEqual(bundle["portfolio_summary"]["total_actual_ars"], 1200.0, places=3)
        self.assertTrue(bundle["portfolio_summary"]["serie_agregada_confiable"])
        self.assertAlmostEqual(bundle["portfolio_summary"]["retorno_acum_pct"], 20.0, places=3)

    def test_build_portfolio_risk_bundle_excludes_operational_liquidity_from_analysis(self) -> None:
        snapshots_dir = ROOT / "tmp_portfolio_risk_exclude_operational_liquidity"
        snapshots_dir.mkdir(exist_ok=True)
        day1 = snapshots_dir / "2026-04-20_real_portfolio_master.csv"
        day2 = snapshots_dir / "2026-04-21_real_portfolio_master.csv"
        day1.write_text(
            "Ticker_IOL,Tipo,Bloque,Peso_%,Precio_ARS,Valorizado_ARS\n"
            "AAPL,CEDEAR,Growth,50,100,1000\n"
            "CAUCION,Liquidez,Liquidez,50,,500\n",
            encoding="utf-8",
        )
        day2.write_text(
            "Ticker_IOL,Tipo,Bloque,Peso_%,Precio_ARS,Valorizado_ARS\n"
            "AAPL,CEDEAR,Growth,52,110,1100\n"
            "CAUCION,Liquidez,Liquidez,24,,100\n"
            "CASH_USD,Liquidez,Liquidez,24,,25\n",
            encoding="utf-8",
        )
        self.addCleanup(lambda: day1.unlink(missing_ok=True))
        self.addCleanup(lambda: day2.unlink(missing_ok=True))
        self.addCleanup(lambda: shutil.rmtree(snapshots_dir, ignore_errors=True))

        current = pd.DataFrame(
            [
                {"Ticker_IOL": "AAPL", "Tipo": "CEDEAR", "Bloque": "Growth", "Peso_%": 60.0, "Precio_ARS": 120.0, "Valorizado_ARS": 1200.0},
                {"Ticker_IOL": "CAUCION", "Tipo": "Liquidez", "Bloque": "Liquidez", "Peso_%": 40.0, "Valorizado_ARS": 300.0},
                {"Ticker_IOL": "CASH_USD", "Tipo": "Liquidez", "Bloque": "Liquidez", "Peso_%": 1.0, "Valorizado_ARS": 30.0},
            ]
        )

        bundle = build_portfolio_risk_bundle(
            current,
            run_date="2026-04-22",
            snapshots_dirs=[snapshots_dir],
            total_ars=1500.0,
        )

        self.assertEqual(bundle["position_risk"]["Ticker_IOL"].tolist(), ["AAPL"])
        self.assertEqual(bundle["portfolio_summary"]["snapshots"], 3)
        self.assertAlmostEqual(bundle["portfolio_summary"]["total_actual_ars"], 1200.0, places=3)
        self.assertTrue(bundle["portfolio_summary"]["serie_agregada_confiable"])
        self.assertAlmostEqual(bundle["portfolio_summary"]["retorno_acum_pct"], 20.0, places=3)

    def test_build_portfolio_risk_bundle_hides_aggregate_metrics_when_overlap_is_unstable(self) -> None:
        snapshots_dir = ROOT / "tmp_portfolio_risk_unstable_overlap"
        snapshots_dir.mkdir(exist_ok=True)
        day1 = snapshots_dir / "2026-04-20_real_portfolio_master.csv"
        day2 = snapshots_dir / "2026-04-21_real_portfolio_master.csv"
        day1.write_text(
            "Ticker_IOL,Tipo,Bloque,Peso_%,Precio_ARS,Valorizado_ARS\n"
            "AAPL,CEDEAR,Growth,50,100,1000\n"
            "KO,CEDEAR,Dividendos,50,50,1000\n",
            encoding="utf-8",
        )
        day2.write_text(
            "Ticker_IOL,Tipo,Bloque,Peso_%,Precio_ARS,Valorizado_ARS\n"
            "AAPL,CEDEAR,Growth,10,101,100\n"
            "MELI,CEDEAR,Growth,90,200,1800\n",
            encoding="utf-8",
        )
        self.addCleanup(lambda: day1.unlink(missing_ok=True))
        self.addCleanup(lambda: day2.unlink(missing_ok=True))
        self.addCleanup(lambda: shutil.rmtree(snapshots_dir, ignore_errors=True))

        current = pd.DataFrame(
            [
                {"Ticker_IOL": "AAPL", "Tipo": "CEDEAR", "Bloque": "Growth", "Peso_%": 10.0, "Precio_ARS": 102.0, "Valorizado_ARS": 100.0},
                {"Ticker_IOL": "MELI", "Tipo": "CEDEAR", "Bloque": "Growth", "Peso_%": 90.0, "Precio_ARS": 210.0, "Valorizado_ARS": 1800.0},
            ]
        )

        bundle = build_portfolio_risk_bundle(
            current,
            run_date="2026-04-22",
            snapshots_dirs=[snapshots_dir],
            total_ars=1900.0,
        )

        summary = bundle["portfolio_summary"]
        self.assertFalse(summary["serie_agregada_confiable"])
        self.assertEqual(summary["pasos_estables"], 1)
        self.assertEqual(summary["pasos_totales"], 2)
        self.assertLess(float(summary["coverage_prev_promedio_pct"]), 85.0)
        self.assertTrue(pd.isna(summary["retorno_acum_pct"]))
        self.assertTrue(pd.isna(summary["volatilidad_diaria_pct"]))
        self.assertTrue(pd.isna(summary["drawdown_max_pct"]))
        self.assertIn("universo comparable", str(summary["nota_estabilidad"]).lower())

    def test_build_portfolio_risk_bundle_labels_short_history_positions(self) -> None:
        snapshots_dir = ROOT / "tmp_portfolio_risk_short_history"
        snapshots_dir.mkdir(exist_ok=True)
        day1 = snapshots_dir / "2026-04-20_real_portfolio_master.csv"
        day2 = snapshots_dir / "2026-04-21_real_portfolio_master.csv"
        day3 = snapshots_dir / "2026-04-22_real_portfolio_master.csv"
        day1.write_text(
            "Ticker_IOL,Tipo,Bloque,Peso_%,Precio_ARS,Valorizado_ARS\nAAPL,CEDEAR,Growth,100,100,1000\n",
            encoding="utf-8",
        )
        day2.write_text(
            "Ticker_IOL,Tipo,Bloque,Peso_%,Precio_ARS,Valorizado_ARS\nAAPL,CEDEAR,Growth,100,105,1050\n",
            encoding="utf-8",
        )
        day3.write_text(
            "Ticker_IOL,Tipo,Bloque,Peso_%,Precio_ARS,Valorizado_ARS\nAAPL,CEDEAR,Growth,50,110,1100\nMELI,CEDEAR,Growth,50,200,1000\n",
            encoding="utf-8",
        )
        self.addCleanup(lambda: day1.unlink(missing_ok=True))
        self.addCleanup(lambda: day2.unlink(missing_ok=True))
        self.addCleanup(lambda: day3.unlink(missing_ok=True))
        self.addCleanup(lambda: shutil.rmtree(snapshots_dir, ignore_errors=True))

        current = pd.DataFrame(
            [
                {"Ticker_IOL": "AAPL", "Tipo": "CEDEAR", "Bloque": "Growth", "Peso_%": 45.0, "Precio_ARS": 112.0, "Valorizado_ARS": 1120.0},
                {"Ticker_IOL": "MELI", "Tipo": "CEDEAR", "Bloque": "Growth", "Peso_%": 55.0, "Precio_ARS": 210.0, "Valorizado_ARS": 1050.0},
            ]
        )

        bundle = build_portfolio_risk_bundle(
            current,
            run_date="2026-04-23",
            snapshots_dirs=[snapshots_dir],
            total_ars=2170.0,
        )

        risk = bundle["position_risk"].set_index("Ticker_IOL")
        self.assertEqual(risk.loc["AAPL", "Calidad_Historia"], "Robusta")
        self.assertEqual(risk.loc["MELI", "Calidad_Historia"], "Parcial")


if __name__ == "__main__":
    unittest.main()
