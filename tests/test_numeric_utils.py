import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from common.numeric import positive_float_or_none, to_float_or_none


class NumericUtilsTests(unittest.TestCase):
    def test_to_float_or_none_normalizes_numeric_scalars(self) -> None:
        self.assertEqual(to_float_or_none("12.5"), 12.5)
        self.assertEqual(to_float_or_none(7), 7.0)
        self.assertIsNone(to_float_or_none("nope"))

    def test_positive_float_or_none_rejects_zero_and_negative_values(self) -> None:
        self.assertEqual(positive_float_or_none("10"), 10.0)
        self.assertIsNone(positive_float_or_none(0))
        self.assertIsNone(positive_float_or_none(-3))
