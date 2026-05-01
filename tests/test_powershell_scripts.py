import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PowerShellScriptsSmokeTests(unittest.TestCase):
    EXPECTED_SCRIPTS = [
        "common_local_app.ps1",
        "setup_local_app.ps1",
        "start_local_app.ps1",
        "status_local_app.ps1",
        "stop_local_app.ps1",
        "smoke_local_app.ps1",
        "run_local_app.ps1",
    ]

    def test_expected_scripts_exist(self):
        scripts_dir = ROOT / "scripts"
        for name in self.EXPECTED_SCRIPTS:
            path = scripts_dir / name
            self.assertTrue(path.exists(), f"Missing script: {path}")

    def test_common_helper_covers_cross_platform_python_and_session(self):
        helper = (ROOT / "scripts" / "common_local_app.ps1").read_text(encoding="utf-8")
        self.assertIn('Join-Path $venvDir "Scripts"', helper)
        self.assertIn('Join-Path $venvDir "bin"', helper)
        self.assertIn("Get-LocalSessionToken", helper)
        self.assertIn("X-Session-Token", helper)
        self.assertIn("Open-LocalUrl", helper)

    def test_operational_scripts_import_common_helper(self):
        scripts_dir = ROOT / "scripts"
        for name in self.EXPECTED_SCRIPTS:
            if name == "common_local_app.ps1":
                continue
            text = (scripts_dir / name).read_text(encoding="utf-8")
            self.assertIn("common_local_app.ps1", text, f"Shared helper missing in {name}")

    def test_protected_endpoint_scripts_use_session_token(self):
        scripts_dir = ROOT / "scripts"
        for name in ["status_local_app.ps1", "smoke_local_app.ps1"]:
            text = (scripts_dir / name).read_text(encoding="utf-8")
            self.assertIn("Get-LocalSessionToken", text, f"Session token helper missing in {name}")
            self.assertIn("New-SessionHeaders", text, f"Session header helper missing in {name}")


if __name__ == "__main__":
    unittest.main()
