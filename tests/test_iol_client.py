import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from clients.iol import iol_get_operaciones, iol_get_quote_with_reauth, iol_login


class IolClientTests(unittest.TestCase):
    def test_iol_login_returns_access_token(self) -> None:
        response = Mock()
        response.json.return_value = {"access_token": "token-demo"}
        response.raise_for_status.return_value = None

        with patch("clients.iol.requests.request", return_value=response) as request_mock:
            token = iol_login("user", "pass", base_url="https://iol.example")

        self.assertEqual(token, "token-demo")
        request_mock.assert_called_once()

    def test_get_quote_with_reauth_refreshes_token_after_401(self) -> None:
        unauthorized = Mock(status_code=401)
        unauthorized.raise_for_status.side_effect = requests.HTTPError("401")
        refreshed = Mock(status_code=200)
        refreshed.raise_for_status.return_value = None
        refreshed.json.return_value = {"simbolo": "GGAL"}

        with patch("clients.iol.requests.request", side_effect=[unauthorized, refreshed]) as get_mock, patch(
            "clients.iol.iol_login", return_value="new-token"
        ) as login_mock:
            payload, token = iol_get_quote_with_reauth(
                "GGAL",
                "old-token",
                username="user",
                password="pass",
                base_url="https://iol.example",
                market="argentina",
            )

        self.assertEqual(payload["simbolo"], "GGAL")
        self.assertEqual(token, "new-token")
        self.assertEqual(get_mock.call_count, 2)
        login_mock.assert_called_once()

    def test_get_quote_with_reauth_keeps_token_without_401(self) -> None:
        ok_response = Mock(status_code=200)
        ok_response.raise_for_status.return_value = None
        ok_response.json.return_value = {"simbolo": "AL30"}

        with patch("clients.iol.requests.request", return_value=ok_response) as get_mock, patch(
            "clients.iol.iol_login"
        ) as login_mock:
            payload, token = iol_get_quote_with_reauth(
                "AL30",
                "same-token",
                username="user",
                password="pass",
                base_url="https://iol.example",
                market="argentina",
            )

        self.assertEqual(payload["simbolo"], "AL30")
        self.assertEqual(token, "same-token")
        get_mock.assert_called_once()
        login_mock.assert_not_called()

    def test_get_operaciones_passes_filters_and_returns_payload(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = [{"numero": 123, "tipo": "Compra"}]

        with patch("clients.iol.requests.request", return_value=response) as get_mock:
            payload = iol_get_operaciones(
                "token-demo",
                base_url="https://iol.example",
                estado="todas",
                pais="argentina",
                fecha_desde="2026-04-01T00:00:00",
                fecha_hasta="2026-04-16T23:59:59",
            )

        self.assertEqual(payload[0]["numero"], 123)
        get_mock.assert_called_once()
        self.assertEqual(get_mock.call_args.kwargs["params"]["filtro.estado"], "todas")
        self.assertEqual(get_mock.call_args.kwargs["params"]["filtro.pais"], "argentina")
        self.assertEqual(get_mock.call_args.kwargs["params"]["filtro.fechaDesde"], "2026-04-01T00:00:00")
        self.assertEqual(get_mock.call_args.kwargs["params"]["filtro.fechaHasta"], "2026-04-16T23:59:59")

    def test_iol_login_retries_on_timeout(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"access_token": "token-ok"}

        with patch("clients.iol.requests.request", side_effect=[requests.Timeout("timeout"), response]) as request_mock, patch(
            "clients.iol.time.sleep"
        ) as sleep_mock:
            token = iol_login("user", "pass", base_url="https://iol.example")

        self.assertEqual(token, "token-ok")
        self.assertEqual(request_mock.call_count, 2)
        sleep_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
