import stat
import sys
import unittest
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class BashScriptsSmokeTests(unittest.TestCase):
    EXPECTED_SCRIPTS = [
        "setup_local_app.sh",
        "start_local_app.sh",
        "status_local_app.sh",
        "stop_local_app.sh",
        "smoke_local_app.sh",
        "run_local_app.sh",
    ]

    def test_expected_scripts_exist(self):
        scripts_dir = ROOT / "scripts"
        for name in self.EXPECTED_SCRIPTS:
            path = scripts_dir / name
            self.assertTrue(path.exists(), f"Missing script: {path}")

    def test_expected_scripts_have_bash_shebang(self):
        scripts_dir = ROOT / "scripts"
        for name in self.EXPECTED_SCRIPTS:
            path = scripts_dir / name
            first_line = path.read_text(encoding="utf-8").splitlines()[0]
            self.assertEqual(first_line.strip(), "#!/usr/bin/env bash", f"Invalid shebang in {path}")

    def test_expected_scripts_enable_strict_mode(self):
        scripts_dir = ROOT / "scripts"
        for name in self.EXPECTED_SCRIPTS:
            path = scripts_dir / name
            text = path.read_text(encoding="utf-8")
            self.assertIn("set -euo pipefail", text, f"Strict mode missing in {path}")

    def test_expected_scripts_are_not_world_writable(self):
        if os.name == "nt":
            self.skipTest("Permission bits for world-writable are not portable on Windows filesystems")
        scripts_dir = ROOT / "scripts"
        for name in self.EXPECTED_SCRIPTS:
            path = scripts_dir / name
            mode = path.stat().st_mode
            self.assertFalse(bool(mode & stat.S_IWOTH), f"World-writable script: {path}")


if __name__ == "__main__":
    unittest.main()
