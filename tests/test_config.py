import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))


class ConfigTests(unittest.TestCase):
    def test_config_uses_lazy_cache_for_json_payloads(self) -> None:
        project_config = importlib.import_module("config")
        project_config.clear_config_cache()

        self.assertEqual(project_config._CONFIG_CACHE, {})

        finviz_map = project_config.FINVIZ_MAP

        self.assertIn("FINVIZ_MAP", project_config._CONFIG_CACHE)
        self.assertIs(finviz_map, project_config.FINVIZ_MAP)

    def test_load_runtime_config_still_exposes_strategy_dicts(self) -> None:
        project_config = importlib.import_module("config")
        project_config.clear_config_cache()

        runtime_config = project_config.load_runtime_config()

        self.assertIn("SCORING_RULES", runtime_config)
        self.assertIn("ACTION_RULES", runtime_config)
        self.assertIn("SIZING_RULES", runtime_config)
        self.assertIn("BUCKET_WEIGHTS", runtime_config)
        self.assertIn("FINVIZ_MAX_WORKERS", runtime_config)
        self.assertIn("FINVIZ_WORKER_TIMEOUT_SECONDS", runtime_config)
        self.assertIsInstance(runtime_config["SCORING_RULES"], dict)
        self.assertIsInstance(runtime_config["BUCKET_WEIGHTS"], dict)
