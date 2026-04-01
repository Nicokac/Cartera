import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from pipeline import build_dashboard_bundle, build_decision_bundle, build_portfolio_bundle, build_sizing_bundle


class PipelineSmokeTests(unittest.TestCase):
    def test_pipeline_exports_are_importable(self) -> None:
        self.assertTrue(callable(build_portfolio_bundle))
        self.assertTrue(callable(build_dashboard_bundle))
        self.assertTrue(callable(build_decision_bundle))
        self.assertTrue(callable(build_sizing_bundle))


if __name__ == "__main__":
    unittest.main()
