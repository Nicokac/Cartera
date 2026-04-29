import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from common.text import normalize_text_basic, normalize_text_folded


class TextUtilsTests(unittest.TestCase):
    def test_normalize_text_basic(self) -> None:
        self.assertEqual(normalize_text_basic("  Hola  "), "Hola")
        self.assertEqual(normalize_text_basic(None), "")

    def test_normalize_text_folded(self) -> None:
        self.assertEqual(normalize_text_folded("  Tasa de InterÃ©s   "), "tasa de interes")
        self.assertEqual(normalize_text_folded(None), "")


if __name__ == "__main__":
    unittest.main()
