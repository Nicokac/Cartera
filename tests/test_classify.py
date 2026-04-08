import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from portfolio.classify import classify_iol_portfolio


class ClassifyPortfolioTests(unittest.TestCase):
    def test_classify_iol_portfolio_splits_assets_by_type(self) -> None:
        activos = [
            {
                "cantidad": 10,
                "ppc": 1000,
                "valorizado": 12000,
                "gananciaDinero": 2000,
                "titulo": {
                    "simbolo": "AAPL",
                    "descripcion": "Apple CEDEAR",
                    "tipo": "CEDEARS",
                    "moneda": "Pesos",
                },
            },
            {
                "cantidad": 5,
                "ppc": 200,
                "valorizado": 1500,
                "gananciaDinero": 500,
                "titulo": {
                    "simbolo": "GGAL",
                    "descripcion": "Grupo Galicia",
                    "tipo": "ACCIONES",
                    "moneda": "Pesos",
                },
            },
            {
                "cantidad": 1000,
                "ppc": 80,
                "valorizado": 950,
                "gananciaDinero": 150,
                "titulo": {
                    "simbolo": "GD30",
                    "descripcion": "Bono GD30",
                    "tipo": "TITULOS PUBLICOS",
                    "moneda": "Pesos",
                },
            },
            {
                "cantidad": 1,
                "ppc": 1,
                "valorizado": 5000,
                "gananciaDinero": 0,
                "titulo": {
                    "simbolo": "FCI1",
                    "descripcion": "Fondo Money Market",
                    "tipo": "FONDO COMUN DE INVERSION",
                    "moneda": "Pesos",
                },
            },
            {
                "cantidad": 1,
                "ppc": 1,
                "valorizado": 3000,
                "gananciaDinero": 0,
                "titulo": {
                    "simbolo": "CAU123",
                    "descripcion": "Caucion colocada",
                    "tipo": "CAUCION",
                    "moneda": "Pesos",
                },
            },
        ]

        result = classify_iol_portfolio(
            activos,
            finviz_map={"AAPL": "AAPL"},
            block_map={"AAPL": "Tecnologia", "GGAL": "Finanzas", "GD30": "Bonos"},
            vn_factor_map={"GD30": 100},
        )

        self.assertEqual(result["PORTAFOLIO"], [("AAPL", "AAPL", "Tecnologia", 10.0, 1000.0)])
        self.assertEqual(result["ACCIONES_LOCALES"], [("GGAL", "GGAL", "Finanzas", 5.0, 200.0)])
        self.assertEqual(result["BONOS"], [("GD30", "Bonos", 1000.0, 80.0, 100.0)])
        self.assertEqual(len(result["LIQUIDEZ"]), 2)
        self.assertEqual(result["LIQUIDEZ"][0][0], "CAUCION")
        self.assertEqual(result["LIQUIDEZ"][1][0], "FCI1")

    def test_classify_iol_portfolio_keeps_cedear_without_finviz_mapping(self) -> None:
        activos = [
            {
                "cantidad": 10,
                "ppc": 1000,
                "valorizado": 12000,
                "gananciaDinero": 2000,
                "titulo": {
                    "simbolo": "NEWC",
                    "descripcion": "Nuevo Cedear",
                    "tipo": "CEDEARS",
                    "moneda": "Pesos",
                },
            }
        ]

        result = classify_iol_portfolio(
            activos,
            finviz_map={},
            block_map={},
            vn_factor_map={},
        )

        self.assertEqual(result["PORTAFOLIO"], [("NEWC", None, "Sin clasificar", 10.0, 1000.0)])


if __name__ == "__main__":
    unittest.main()
