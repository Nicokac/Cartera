import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from smoke_run import main


class SmokeRunTests(unittest.TestCase):
    def test_main_dry_run_does_not_raise(self) -> None:
        main(dry_run=True)

    def test_main_prints_expected_sections(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            main()

        output = buffer.getvalue()
        self.assertIn("Smoke Run", output)
        self.assertIn("Dashboard", output)
        self.assertIn("Operaciones", output)


if __name__ == "__main__":
    unittest.main()
