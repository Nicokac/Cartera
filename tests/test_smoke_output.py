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

from smoke_output import render_smoke_output
from smoke_run import run_smoke_pipeline


class SmokeOutputTests(unittest.TestCase):
    def test_render_smoke_output_includes_core_sections(self) -> None:
        result = run_smoke_pipeline()

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            render_smoke_output(result)

        output = buffer.getvalue()
        self.assertIn("Smoke Run", output)
        self.assertIn("Integridad", output)
        self.assertIn("Sizing", output)
        self.assertIn("Prediccion", output)
        self.assertIn("Operaciones", output)


if __name__ == "__main__":
    unittest.main()
