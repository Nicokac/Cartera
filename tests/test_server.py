import os
import sys
import threading
import unittest
from datetime import datetime
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
    server._cancel_requested = False
    server._session_token = "test-session-token"
    server._run_request_timestamps = []


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

    def test_api_health_all_ok(self):
        ok_response = MagicMock()
        status_by_url = {
            "https://api.invertironline.com/token": 401,
            "https://api.argentinadatos.com/v1/cotizaciones/dolares/bolsa": 200,
            "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias": 200,
            "https://bonistas.com": 200,
            "https://api.stlouisfed.org/fred/series?series_id=DGS10": 400,
            "https://finviz.com/quote.ashx?t=AAPL": 403,
        }

        def fake_get(url, timeout):
            resp = MagicMock()
            resp.status_code = status_by_url[url]
            return resp

        with patch("server.requests.get", side_effect=fake_get):
            r = _client.get("/api-health")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["apis"]), 6)
        self.assertTrue(all(item["ok"] for item in data["apis"]))
        self.assertTrue(all(isinstance(item["latency_ms"], int) for item in data["apis"]))

    def test_api_health_with_partial_failure(self):
        def fake_get(url, timeout):
            if "bonistas.com" in url:
                raise RuntimeError("timeout")
            resp = MagicMock()
            if "invertironline.com/token" in url:
                resp.status_code = 401
            elif "argentinadatos.com" in url:
                resp.status_code = 200
            elif "api.bcra.gob.ar/estadisticas/v4.0/monetarias" in url:
                resp.status_code = 200
            elif "stlouisfed.org" in url:
                resp.status_code = 400
            elif "finviz.com/quote.ashx" in url:
                resp.status_code = 403
            else:
                resp.status_code = 200
            return resp

        with patch("server.requests.get", side_effect=fake_get):
            r = _client.get("/api-health")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertFalse(data["ok"])
        bonistas = next(item for item in data["apis"] if item["name"] == "bonistas")
        self.assertFalse(bonistas["ok"])
        self.assertIn("error", bonistas)


class TestSession(unittest.TestCase):
    def test_get_session_returns_token(self):
        with patch("server._ensure_session_token", return_value="abc-token"):
            r = _client.get("/session")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["token"], "abc-token")


class TestGetReportsList(unittest.TestCase):
    def test_returns_reports_sorted_by_mtime_desc(self):
        with TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            older = reports_dir / "older.html"
            newer = reports_dir / "newer.html"
            older.write_text("<html>old</html>", encoding="utf-8")
            newer.write_text("<html>new</html>", encoding="utf-8")
            old_ts = datetime(2026, 4, 26, 10, 0, 0).timestamp()
            new_ts = datetime(2026, 4, 27, 10, 0, 0).timestamp()
            os.utime(older, (old_ts, old_ts))
            os.utime(newer, (new_ts, new_ts))

            with patch.object(server, "REPORTS_DIR", reports_dir):
                r = _client.get("/reports/list")

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual([x["name"] for x in data["reports"]], ["newer.html", "older.html"])
        self.assertEqual(data["reports"][0]["url"], "/reports/newer.html")


class TestGetRunsRecent(unittest.TestCase):
    def test_returns_last_five_runs_desc(self):
        with TemporaryDirectory() as tmp:
            history_path = Path(tmp) / "run_history.jsonl"
            rows = [
                {"status": "done", "finished_at": f"2026-04-2{i} 10:00:00", "username": f"user{i}"}
                for i in range(1, 8)
            ]
            history_path.write_text("\n".join([__import__("json").dumps(r) for r in rows]), encoding="utf-8")
            with patch.object(server, "RUN_HISTORY_FILE", history_path):
                r = _client.get("/runs/recent")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(len(data["runs"]), 5)
        self.assertEqual(data["runs"][0]["username"], "user7")
        self.assertEqual(data["runs"][-1]["username"], "user3")


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
        self.assertIsNone(data["elapsed_seconds"])
        self.assertIn("log_tail", data)
        self.assertIn("log_lines", data)

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
        self.assertIsInstance(data["elapsed_seconds"], int)
        self.assertGreaterEqual(data["elapsed_seconds"], 0)

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
        self.assertEqual(data["log_lines"], 3)
        self.assertIsNotNone(data["last_log_mtime"])
        self.assertIsNone(data["elapsed_seconds"])

    def test_done_uses_finished_at_for_elapsed_seconds(self):
        server._state["status"] = "done"
        server._state["started_at"] = "2026-04-26 10:00:00"
        server._state["finished_at"] = "2026-04-26 10:05:30"
        data = _client.get("/status/detail").json()
        self.assertEqual(data["elapsed_seconds"], 330)

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

    def test_status_detail_redacts_credentials_from_log_tail_and_error(self):
        server._state["status"] = "error"
        server._state["error"] = "IOL_PASSWORD=supersecret password: 123456"
        with TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "server_run.log"
            log_path.write_text(
                "IOL_USERNAME=demo_user\npassword=abc123\nusername: user@example.com",
                encoding="utf-8",
            )
            with patch.object(server, "LOG_PATH", log_path):
                data = _client.get("/status/detail").json()
        self.assertIn("IOL_USERNAME=<redacted>", data["log_tail"])
        self.assertIn("password=<redacted>", data["log_tail"])
        self.assertIn("username=<redacted>", data["log_tail"])
        self.assertNotIn("demo_user", data["log_tail"])
        self.assertNotIn("abc123", data["log_tail"])
        self.assertNotIn("user@example.com", data["log_tail"])
        self.assertIn("IOL_PASSWORD=<redacted>", data["error"])
        self.assertNotIn("supersecret", data["error"])


class TestPostRun(unittest.TestCase):
    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def _post_run(self, body=None):
        with patch("server.subprocess.Popen", return_value=MagicMock()), \
             patch("server.threading.Thread", return_value=MagicMock()):
            payload = body or {"username": "demo_user", "password": "secret"}
            return _client.post("/run", json=payload, headers={"X-Session-Token": "test-session-token"})

    def test_401_without_valid_session_token(self):
        with patch("server.subprocess.Popen", return_value=MagicMock()), \
             patch("server.threading.Thread", return_value=MagicMock()):
            r = _client.post("/run", json={}, headers={"X-Session-Token": "bad-token"})
        self.assertEqual(r.status_code, 401)

    def test_returns_started(self):
        r = self._post_run()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "started"})

    def test_state_transitions_to_running(self):
        self._post_run()
        self.assertEqual(server._state["status"], "running")
        self.assertIsNotNone(server._state["started_at"])

    def test_params_stored_in_state(self):
        self._post_run(
            {
                "username": "demo_user",
                "password": "secret",
                "usar_liquidez_iol": True,
                "aporte_externo_ars": 5000.0,
            }
        )
        self.assertEqual(server._state["params"]["username"], "demo_user")
        self.assertNotIn("password", server._state["params"])
        self.assertTrue(server._state["params"]["usar_liquidez_iol"])
        self.assertEqual(server._state["params"]["aporte_externo_ars"], 5000.0)

    def test_default_funding_uses_iol_liquidity(self):
        self._post_run({})
        self.assertTrue(server._state["params"]["usar_liquidez_iol"])

    def test_409_when_already_running(self):
        server._state["status"] = "running"
        r = _client.post("/run", json={}, headers={"X-Session-Token": "test-session-token"})
        self.assertEqual(r.status_code, 409)

    def test_concurrent_run_requests_second_returns_409(self):
        responses: list[int] = []
        barrier = threading.Barrier(2)
        real_thread_cls = threading.Thread

        def send_run():
            try:
                barrier.wait(timeout=1.0)
                response = server.post_run(
                    server.RunParams(username="demo_user", password="secret"),
                    x_session_token="test-session-token",
                )
                responses.append(response.status_code)
            except Exception as exc:
                status_code = getattr(exc, "status_code", None)
                responses.append(int(status_code) if status_code is not None else 500)

        with patch("server.subprocess.Popen", return_value=MagicMock(pid=9999)), \
             patch("server.threading.Thread", return_value=MagicMock()):
            t1 = real_thread_cls(target=send_run)
            t2 = real_thread_cls(target=send_run)
            t1.start()
            t2.start()
            t1.join(timeout=1.0)
            t2.join(timeout=1.0)

        self.assertEqual(sorted(responses), [200, 409])

    def test_422_when_aporte_externo_is_negative(self):
        r = _client.post(
            "/run",
            json={"username": "demo_user", "password": "secret", "aporte_externo_ars": -1},
            headers={"X-Session-Token": "test-session-token"},
        )
        self.assertEqual(r.status_code, 422)

    def test_422_when_username_is_empty(self):
        r = _client.post(
            "/run",
            json={"username": "   ", "password": "secret"},
            headers={"X-Session-Token": "test-session-token"},
        )
        self.assertEqual(r.status_code, 422)

    def test_422_when_password_is_empty(self):
        r = _client.post(
            "/run",
            json={"username": "demo_user", "password": "   "},
            headers={"X-Session-Token": "test-session-token"},
        )
        self.assertEqual(r.status_code, 422)

    def test_422_when_username_exceeds_max_length(self):
        r = _client.post(
            "/run",
            json={"username": "u" * 201, "password": "secret"},
            headers={"X-Session-Token": "test-session-token"},
        )
        self.assertEqual(r.status_code, 422)

    def test_422_when_password_exceeds_max_length(self):
        r = _client.post(
            "/run",
            json={"username": "demo_user", "password": "p" * 201},
            headers={"X-Session-Token": "test-session-token"},
        )
        self.assertEqual(r.status_code, 422)

    def test_run_closes_parent_log_handle(self):
        fake_log = MagicMock()
        with patch.object(server, "LOG_PATH", MagicMock(open=MagicMock(return_value=fake_log))), \
             patch("server.subprocess.Popen", return_value=MagicMock()), \
             patch("server.threading.Thread", return_value=MagicMock()):
            r = _client.post(
                "/run",
                json={"username": "demo_user", "password": "secret"},
                headers={"X-Session-Token": "test-session-token"},
            )
        self.assertEqual(r.status_code, 200)
        fake_log.close.assert_called_once()

    def test_run_passes_username_and_password_via_child_env(self):
        fake_log = MagicMock()
        with patch.object(server, "LOG_PATH", MagicMock(open=MagicMock(return_value=fake_log))), \
             patch("server.subprocess.Popen", return_value=MagicMock()) as popen_mock, \
             patch("server.threading.Thread", return_value=MagicMock()):
            r = _client.post(
                "/run",
                json={
                    "username": "demo_user",
                    "password": "secret",
                    "usar_liquidez_iol": False,
                    "aporte_externo_ars": 123.0,
                },
                headers={"X-Session-Token": "test-session-token"},
            )
        self.assertEqual(r.status_code, 200)
        cmd = popen_mock.call_args.args[0]
        self.assertNotIn("--username", cmd)
        self.assertNotIn("--password", cmd)
        child_env = popen_mock.call_args.kwargs["env"]
        self.assertEqual(child_env["IOL_USERNAME"], "demo_user")
        self.assertEqual(child_env["IOL_PASSWORD"], "secret")

    def test_run_returns_500_when_subprocess_fails_to_start(self):
        fake_log = MagicMock()
        with patch.object(server, "LOG_PATH", MagicMock(open=MagicMock(return_value=fake_log))), \
             patch("server.subprocess.Popen", side_effect=OSError("spawn failed")), \
             patch("server.threading.Thread", return_value=MagicMock()):
            r = _client.post(
                "/run",
                json={"username": "demo_user", "password": "secret"},
                headers={"X-Session-Token": "test-session-token"},
            )
        self.assertEqual(r.status_code, 500)
        self.assertIn("No se pudo iniciar la corrida", r.json()["detail"])

    def test_429_when_run_rate_limit_exceeded(self):
        fake_log = MagicMock()
        with patch.object(server, "LOG_PATH", MagicMock(open=MagicMock(return_value=fake_log))), \
             patch("server.subprocess.Popen", return_value=MagicMock()), \
             patch("server.threading.Thread", return_value=MagicMock()):
            for _ in range(3):
                r_ok = _client.post(
                    "/run",
                    json={"username": "demo_user", "password": "secret"},
                    headers={"X-Session-Token": "test-session-token"},
                )
                self.assertEqual(r_ok.status_code, 200)
                server._state.update(_IDLE)
                server._process = None
                server._cancel_requested = False
                server._session_token = "test-session-token"
            r_limit = _client.post(
                "/run",
                json={"username": "demo_user", "password": "secret"},
                headers={"X-Session-Token": "test-session-token"},
            )
        self.assertEqual(r_limit.status_code, 429)


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
        server._state["params"] = {"username": "demo_user", "usar_liquidez_iol": True, "aporte_externo_ars": 0.0}
        with patch("server._clear_run_pid") as clear_pid, patch("server._append_run_history") as append_history:
            server._watch_process()
        self.assertEqual(server._state["status"], "done")
        self.assertIsNotNone(server._state["finished_at"])
        self.assertIsNone(server._process)
        clear_pid.assert_called_once()
        append_history.assert_called_once()

    def test_error_on_nonzero_returncode(self):
        server._process = self._make_proc(1)
        server._state["status"] = "running"
        mock_log = MagicMock()
        mock_log.read_text.return_value = "pipeline failed"
        with patch.object(server, "LOG_PATH", mock_log), \
             patch("server._clear_run_pid") as clear_pid:
            server._watch_process()
        self.assertEqual(server._state["status"], "error")
        self.assertIn("pipeline failed", server._state["error"])
        self.assertIsNone(server._process)
        clear_pid.assert_called_once()

    def test_error_fallback_on_unreadable_log(self):
        server._process = self._make_proc(2)
        server._state["status"] = "running"
        mock_log = MagicMock()
        mock_log.read_text.side_effect = OSError("no log")
        with patch.object(server, "LOG_PATH", mock_log), \
             patch("server._clear_run_pid") as clear_pid:
            server._watch_process()
        self.assertEqual(server._state["status"], "error")
        self.assertIn("2", server._state["error"])
        self.assertIsNone(server._process)
        clear_pid.assert_called_once()

    def test_interrupted_when_cancel_requested(self):
        server._process = self._make_proc(-15)
        server._state["status"] = "running"
        server._cancel_requested = True
        with patch("server._clear_run_pid") as clear_pid:
            server._watch_process()
        self.assertEqual(server._state["status"], "interrupted")
        self.assertIsNone(server._state["error"])
        self.assertIsNotNone(server._state["finished_at"])
        self.assertIsNone(server._process)
        clear_pid.assert_called_once()

    def test_noop_when_process_is_none(self):
        server._process = None
        server._watch_process()
        self.assertEqual(server._state["status"], "idle")

    def test_watch_process_sends_completion_webhook_when_configured(self):
        server._process = self._make_proc(0)
        server._state["status"] = "running"
        server._state["params"] = {"username": "demo_user", "usar_liquidez_iol": True, "aporte_externo_ars": 0.0}
        with patch("server._clear_run_pid"), patch("server._append_run_history"), patch.dict(
            "server.os.environ",
            {"RUN_COMPLETION_WEBHOOK_URL": "http://127.0.0.1:9999/webhook"},
            clear=False,
        ), patch("server.requests.post") as post_mock:
            server._watch_process()
        post_mock.assert_called_once()
        self.assertEqual(post_mock.call_args.args[0], "http://127.0.0.1:9999/webhook")
        self.assertEqual(post_mock.call_args.kwargs["json"]["status"], "done")

    def test_watch_process_ignores_webhook_errors(self):
        server._process = self._make_proc(0)
        server._state["status"] = "running"
        server._state["params"] = {"username": "demo_user", "usar_liquidez_iol": True, "aporte_externo_ars": 0.0}
        with patch("server._clear_run_pid"), patch("server._append_run_history"), patch.dict(
            "server.os.environ",
            {"RUN_COMPLETION_WEBHOOK_URL": "http://127.0.0.1:9999/webhook"},
            clear=False,
        ), patch("server.requests.post", side_effect=RuntimeError("network down")):
            server._watch_process()
        self.assertEqual(server._state["status"], "done")


class TestPostCancel(unittest.TestCase):
    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def test_cancel_returns_cancelling_when_running(self):
        proc = MagicMock()
        proc.poll.return_value = None
        server._process = proc
        server._state["status"] = "running"

        r = _client.post("/cancel")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "cancelling"})
        proc.terminate.assert_called_once()
        self.assertTrue(server._cancel_requested)

    def test_cancel_409_when_not_running(self):
        r = _client.post("/cancel")
        self.assertEqual(r.status_code, 409)

    def test_cancel_409_when_process_already_finished(self):
        proc = MagicMock()
        proc.poll.return_value = 0
        server._process = proc
        server._state["status"] = "running"

        r = _client.post("/cancel")
        self.assertEqual(r.status_code, 409)
        proc.terminate.assert_not_called()


class TestRecoverOrphanRun(unittest.TestCase):
    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def test_noop_when_no_pid_file(self):
        with patch("server._read_run_pid", return_value=None):
            server._recover_orphan_run()
        self.assertEqual(server._state["status"], "idle")

    def test_marks_interrupted_and_clears_pid_when_stale(self):
        with patch("server._read_run_pid", return_value=12345), \
             patch("server._is_process_alive", return_value=False), \
             patch("server._terminate_pid") as terminate_pid, \
             patch("server._clear_run_pid") as clear_pid:
            server._recover_orphan_run()
        self.assertEqual(server._state["status"], "interrupted")
        self.assertIn("interrumpida", server._state["error"])
        terminate_pid.assert_not_called()
        clear_pid.assert_called_once()

    def test_terminates_alive_orphan_and_marks_interrupted(self):
        with patch("server._read_run_pid", return_value=23456), \
             patch("server._is_process_alive", return_value=True), \
             patch("server._terminate_pid") as terminate_pid, \
             patch("server._clear_run_pid") as clear_pid:
            server._recover_orphan_run()
        self.assertEqual(server._state["status"], "interrupted")
        terminate_pid.assert_called_once_with(23456)
        clear_pid.assert_called_once()


class TestRuntimeCsvValidation(unittest.TestCase):
    def test_validate_runtime_csv_schema_accepts_valid_header(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "ok.csv"
            csv_path.write_text("run_date,Ticker_IOL,asset_subfamily,score_unificado,accion_sugerida_v2\n", encoding="utf-8")
            valid = server._validate_runtime_csv_schema(csv_path, server._DECISION_HISTORY_REQUIRED_COLUMNS)
            self.assertTrue(valid)
            self.assertTrue(csv_path.exists())

    def test_validate_runtime_csv_schema_quarantines_invalid_header(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "bad.csv"
            csv_path.write_text("foo,bar\n1,2\n", encoding="utf-8")
            corrupt_dir = root / "corrupt"
            with patch.object(server, "RUNTIME_CORRUPT_DIR", corrupt_dir):
                valid = server._validate_runtime_csv_schema(csv_path, server._DECISION_HISTORY_REQUIRED_COLUMNS)
            self.assertFalse(valid)
            self.assertFalse(csv_path.exists())
            quarantined = list(corrupt_dir.glob("bad.csv.*.corrupt"))
            self.assertEqual(len(quarantined), 1)

    def test_on_startup_calls_runtime_csv_validation(self):
        with patch("server._validate_runtime_csvs_on_startup") as validate_mock, patch(
            "server._recover_orphan_run"
        ), patch("server._ensure_session_token"):
            server.on_startup()
        validate_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
