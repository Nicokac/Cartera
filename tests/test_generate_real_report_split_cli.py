import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from generate_real_report_cli import (
    load_local_env_impl,
    prompt_money_ars_impl,
    prompt_yes_no_impl,
    resolve_iol_credentials_impl,
)


class GenerateRealReportSplitCliTests(unittest.TestCase):
    def test_load_local_env_impl_returns_empty_when_file_missing(self) -> None:
        loaded = load_local_env_impl(ROOT / "tmp_missing_env_file.env", environ={})
        self.assertEqual(loaded, {})

    def test_load_local_env_impl_keeps_existing_env_values(self) -> None:
        env_path = ROOT / "tmp_split_test.env"
        env_path.write_text(
            "export IOL_USERNAME=user@test.com\n"
            "IOL_PASSWORD='top-secret'\n"
            "INVALID_LINE\n",
            encoding="utf-8",
        )
        self.addCleanup(lambda: env_path.unlink(missing_ok=True))

        environ = {"IOL_USERNAME": "already@set.com"}
        loaded = load_local_env_impl(env_path, environ=environ)

        self.assertEqual(loaded["IOL_USERNAME"], "user@test.com")
        self.assertEqual(loaded["IOL_PASSWORD"], "top-secret")
        self.assertEqual(environ["IOL_USERNAME"], "already@set.com")
        self.assertEqual(environ["IOL_PASSWORD"], "top-secret")

    def test_resolve_iol_credentials_impl_raises_in_non_interactive_when_missing(self) -> None:
        with self.assertRaisesRegex(ValueError, "Usuario IOL faltante"):
            resolve_iol_credentials_impl(
                username_override="",
                password_override="",
                non_interactive=True,
                load_local_env_fn=lambda: {},
                environ={},
                input_fn=lambda _x: "",
                getpass_fn=lambda _x: "",
                print_fn=lambda _x: None,
            )

    def test_resolve_iol_credentials_impl_raises_for_missing_password_in_non_interactive(self) -> None:
        with self.assertRaisesRegex(ValueError, "Password IOL faltante"):
            resolve_iol_credentials_impl(
                username_override="user@example.com",
                password_override="",
                non_interactive=True,
                load_local_env_fn=lambda: {},
                environ={},
                input_fn=lambda _x: "",
                getpass_fn=lambda _x: "",
                print_fn=lambda _x: None,
            )

    def test_resolve_iol_credentials_impl_prompts_for_missing_values(self) -> None:
        input_mock = Mock(return_value="prompt-user@example.com")
        getpass_mock = Mock(return_value="prompt-pass")
        print_mock = Mock()

        username, password = resolve_iol_credentials_impl(
            username_override="",
            password_override="",
            non_interactive=False,
            load_local_env_fn=lambda: {},
            environ={},
            input_fn=input_mock,
            getpass_fn=getpass_mock,
            print_fn=print_mock,
        )

        self.assertEqual(username, "prompt-user@example.com")
        self.assertEqual(password, "prompt-pass")
        print_mock.assert_not_called()

    def test_prompt_helpers_cover_default_and_negative_paths(self) -> None:
        result_default = prompt_yes_no_impl(
            "Confirmar?",
            default=True,
            input_fn=lambda _msg: "",
            print_fn=lambda _msg: None,
        )
        self.assertTrue(result_default)

        result_no = prompt_yes_no_impl(
            "Confirmar?",
            default=False,
            input_fn=lambda _msg: "no",
            print_fn=lambda _msg: None,
        )
        self.assertFalse(result_no)

        result_money = prompt_money_ars_impl(
            "Monto",
            input_fn=Mock(side_effect=["-10", ""]),
            print_fn=lambda _msg: None,
        )
        self.assertEqual(result_money, 0.0)

    def test_resolve_iol_credentials_impl_raises_when_prompt_returns_empty(self) -> None:
        with self.assertRaisesRegex(ValueError, "obligatorios"):
            resolve_iol_credentials_impl(
                username_override="",
                password_override="",
                non_interactive=False,
                load_local_env_fn=lambda: {},
                environ={},
                input_fn=lambda _x: " ",
                getpass_fn=lambda _x: " ",
                print_fn=lambda _x: None,
            )

    def test_load_local_env_impl_skips_empty_key_assignment(self) -> None:
        env_path = ROOT / "tmp_split_test_empty_key.env"
        env_path.write_text(" =value\n", encoding="utf-8")
        self.addCleanup(lambda: env_path.unlink(missing_ok=True))
        loaded = load_local_env_impl(env_path, environ={})
        self.assertEqual(loaded, {})


if __name__ == "__main__":
    unittest.main()
