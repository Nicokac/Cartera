import sys
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server
from fastapi.testclient import TestClient

_client = TestClient(server.app)

_IDLE = {
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "error": None,
    "params": None,
}


def _reset():
    server._state.update(_IDLE)
    server._process = None


class TestGetIndex(unittest.TestCase):
    def test_200_with_html_content_type(self):
        r = _client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["content-type"])

    def test_503_when_static_dir_missing(self):
        with patch.object(server, "STATIC_DIR", ROOT / "__nonexistent__"):
            r = _client.get("/")
        self.assertEqual(r.status_code, 503)


class TestGetStatus(unittest.TestCase):
    def setUp(self):
        _reset()

    def test_idle_state(self):
        r = _client.get("/status")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "idle")
        self.assertIsNone(data["started_at"])
        self.assertIsNone(data["error"])

    def test_reflects_running_state(self):
        server._state["status"] = "running"
        server._state["started_at"] = "2026-04-26 10:00:00"
        data = _client.get("/status").json()
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["started_at"], "2026-04-26 10:00:00")

    def test_reflects_done_state(self):
        server._state["status"] = "done"
        server._state["finished_at"] = "2026-04-26 10:05:00"
        data = _client.get("/status").json()
        self.assertEqual(data["status"], "done")
        self.assertIsNotNone(data["finished_at"])


class TestGetHealth(unittest.TestCase):
    def test_health_endpoint(self):
        r = _client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")
        self.assertEqual(r.json()["service"], "cartera-local-app")


class TestGetStatusDetail(unittest.TestCase):
    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def test_idle_without_process(self):
        r = _client.get("/status/detail")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "idle")
        self.assertIsNone(data["pid"])
        self.assertIsNone(data["uptime_seconds"])
        self.assertIn("log_tail", data)

    def test_running_with_process_and_uptime(self):
        server._state["status"] = "running"
        server._state["started_at"] = "2026-04-26 10:00:00"
        proc = MagicMock()
        proc.pid = 12345
        server._process = proc

        data = _client.get("/status/detail").json()
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["pid"], 12345)
        self.assertIsInstance(data["uptime_seconds"], int)
        self.assertGreaterEqual(data["uptime_seconds"], 0)

    def test_error_with_log_present(self):
        server._state["status"] = "error"
        server._state["error"] = "pipeline failed"
        with TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "server_run.log"
            log_path.write_text("line1\nline2\npipeline failed", encoding="utf-8")
            with patch.object(server, "LOG_PATH", log_path):
                data = _client.get("/status/detail").json()
        self.assertEqual(data["status"], "error")
        self.assertIn("pipeline failed", data["log_tail"])
        self.assertIsNotNone(data["last_log_mtime"])

    def test_missing_log_does_not_fail(self):
        server._state["status"] = "done"
        with TemporaryDirectory() as tmp:
            missing_log = Path(tmp) / "missing.log"
            with patch.object(server, "LOG_PATH", missing_log):
                r = _client.get("/status/detail")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["log_tail"], "")
        self.assertIsNone(data["last_log_mtime"])


class TestPostRun(unittest.TestCase):
    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def _post_run(self, body=None):
        with patch("server.subprocess.Popen", return_value=MagicMock()), \
             patch("server.threading.Thread", return_value=MagicMock()):
            return _client.post("/run", json=body or {})

    def test_returns_started(self):
        r = self._post_run()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "started"})

    def test_state_transitions_to_running(self):
        self._post_run()
        self.assertEqual(server._state["status"], "running")
        self.assertIsNotNone(server._state["started_at"])

    def test_params_stored_in_state(self):
        self._post_run({"usar_liquidez_iol": True, "aporte_externo_ars": 5000.0})
        self.assertTrue(server._state["params"]["usar_liquidez_iol"])
        self.assertEqual(server._state["params"]["aporte_externo_ars"], 5000.0)

    def test_409_when_already_running(self):
        server._state["status"] = "running"
        r = _client.post("/run", json={})
        self.assertEqual(r.status_code, 409)

    def test_run_closes_parent_log_handle(self):
        fake_log = MagicMock()
        with patch.object(server, "LOG_PATH", MagicMock(open=MagicMock(return_value=fake_log))), \
             patch("server.subprocess.Popen", return_value=MagicMock()), \
             patch("server.threading.Thread", return_value=MagicMock()):
            r = _client.post("/run", json={})
        self.assertEqual(r.status_code, 200)
        fake_log.close.assert_called_once()


class TestWatchProcess(unittest.TestCase):
    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def _make_proc(self, returncode):
        proc = MagicMock()
        proc.returncode = returncode
        proc.wait.return_value = None
        return proc

    def test_done_on_returncode_zero(self):
        server._process = self._make_proc(0)
        server._state["status"] = "running"
        server._watch_process()
        self.assertEqual(server._state["status"], "done")
        self.assertIsNotNone(server._state["finished_at"])

    def test_error_on_nonzero_returncode(self):
        server._process = self._make_proc(1)
        server._state["status"] = "running"
        mock_log = MagicMock()
        mock_log.read_text.return_value = "pipeline failed"
        with patch.object(server, "LOG_PATH", mock_log):
            server._watch_process()
        self.assertEqual(server._state["status"], "error")
        self.assertIn("pipeline failed", server._state["error"])

    def test_error_fallback_on_unreadable_log(self):
        server._process = self._make_proc(2)
        server._state["status"] = "running"
        mock_log = MagicMock()
        mock_log.read_text.side_effect = OSError("no log")
        with patch.object(server, "LOG_PATH", mock_log):
            server._watch_process()
        self.assertEqual(server._state["status"], "error")
        self.assertIn("2", server._state["error"])

    def test_noop_when_process_is_none(self):
        server._process = None
        server._watch_process()
        self.assertEqual(server._state["status"], "idle")


if __name__ == "__main__":
    unittest.main()
