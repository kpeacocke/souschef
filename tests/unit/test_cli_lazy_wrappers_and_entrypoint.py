"""Coverage tests for CLI lazy wrappers and module entrypoint."""

from __future__ import annotations

import runpy
from types import SimpleNamespace
from unittest.mock import patch

from souschef import cli


def test_cli_lazy_wrappers_delegate_to_server_api() -> None:
    """Selected lazy wrappers should delegate to matching server symbols."""
    fake_server = SimpleNamespace(
        convert_bash_to_ansible=lambda path: f"bash:{path}",
        convert_inspec_to_test=lambda profile, fmt: f"inspec:{profile}:{fmt}",
        generate_ansible_role_from_bash=lambda content, role_name=None: (
            f"role:{content}:{role_name}"
        ),
        generate_inspec_from_recipe=lambda path: f"recipe:{path}",
        parse_bash_script=lambda path: f"parse:{path}",
    )

    with patch("souschef.cli._server_api", return_value=fake_server):
        assert cli.convert_bash_to_ansible("a.sh") == "bash:a.sh"
        assert cli.convert_inspec_to_test("profile", "goss") == "inspec:profile:goss"
        assert (
            cli.generate_ansible_role_from_bash("echo hi", role_name="r1")
            == "role:echo hi:r1"
        )
        assert cli.generate_inspec_from_recipe("default.rb") == "recipe:default.rb"
        assert cli.parse_bash_script("script.sh") == "parse:script.sh"


def test_cli_module_entrypoint_calls_main() -> None:
    """Running ``python -m souschef.cli`` should call ``main()`` exactly once."""
    with patch("souschef.cli.main") as mock_main:
        runpy.run_module("souschef.cli.__main__", run_name="__main__")

    mock_main.assert_called_once_with()
