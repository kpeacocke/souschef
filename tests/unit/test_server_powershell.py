"""
Unit tests for PowerShell MCP tools in souschef/server.py.

Tests for the parse_powershell and convert_powershell MCP tools,
as well as re-exported convenience functions.
"""

from __future__ import annotations

import json
from pathlib import Path


class TestParsePowershellMcpTool:
    """Tests for the parse_powershell() MCP tool in server.py."""

    def test_parse_valid_script(self, tmp_path: Path) -> None:
        """parse_powershell returns JSON for a valid .ps1 file."""
        from souschef.server import parse_powershell

        script = tmp_path / "setup.ps1"
        script.write_text(
            "Install-WindowsFeature -Name Web-Server\n", encoding="utf-8"
        )

        result = json.loads(parse_powershell(str(script)))
        assert "actions" in result
        assert any(a["action_type"] == "windows_feature_install" for a in result["actions"])

    def test_parse_missing_file(self, tmp_path: Path) -> None:
        """parse_powershell returns error for missing file."""
        from souschef.server import parse_powershell

        result = parse_powershell(str(tmp_path / "missing.ps1"))
        assert "Error" in result or "not found" in result.lower()

    def test_parse_directory_path(self, tmp_path: Path) -> None:
        """parse_powershell returns error when given a directory."""
        from souschef.server import parse_powershell

        result = parse_powershell(str(tmp_path))
        assert "Error" in result or "directory" in result.lower()


class TestConvertPowershellMcpTool:
    """Tests for the convert_powershell() MCP tool in server.py."""

    def test_convert_valid_script(self, tmp_path: Path) -> None:
        """convert_powershell returns JSON with playbook_yaml for valid input."""
        from souschef.server import convert_powershell

        script = tmp_path / "setup.ps1"
        script.write_text(
            "Install-WindowsFeature -Name Web-Server\n", encoding="utf-8"
        )

        result = json.loads(convert_powershell(str(script)))
        assert result["status"] == "success"
        assert "playbook_yaml" in result
        assert "win_feature" in result["playbook_yaml"]

    def test_convert_missing_file(self, tmp_path: Path) -> None:
        """convert_powershell returns error JSON for missing file."""
        from souschef.server import convert_powershell

        result = json.loads(convert_powershell(str(tmp_path / "missing.ps1")))
        assert result["status"] == "error"

    def test_convert_with_custom_playbook_name(self, tmp_path: Path) -> None:
        """convert_powershell respects the playbook_name argument."""
        from souschef.server import convert_powershell

        script = tmp_path / "setup.ps1"
        script.write_text("Start-Service -Name W3SVC\n", encoding="utf-8")

        result = json.loads(
            convert_powershell(str(script), playbook_name="my_custom_play")
        )
        assert "my_custom_play" in result["playbook_yaml"]

    def test_convert_with_custom_hosts(self, tmp_path: Path) -> None:
        """convert_powershell respects the hosts argument."""
        from souschef.server import convert_powershell

        script = tmp_path / "setup.ps1"
        script.write_text("Start-Service -Name W3SVC\n", encoding="utf-8")

        result = json.loads(
            convert_powershell(str(script), hosts="win_web_servers")
        )
        assert "win_web_servers" in result["playbook_yaml"]


class TestServerReExports:
    """Tests for backward-compat re-exports from server.py."""

    def test_parse_powershell_script_is_exported(self) -> None:
        """parse_powershell_script is accessible from souschef.server."""
        from souschef.server import parse_powershell_script

        assert callable(parse_powershell_script)

    def test_parse_powershell_content_is_exported(self) -> None:
        """parse_powershell_content is accessible from souschef.server."""
        from souschef.server import parse_powershell_content

        assert callable(parse_powershell_content)

    def test_convert_powershell_to_ansible_is_exported(self) -> None:
        """convert_powershell_to_ansible is accessible from souschef.server."""
        from souschef.server import convert_powershell_to_ansible

        assert callable(convert_powershell_to_ansible)

    def test_convert_powershell_content_to_ansible_is_exported(self) -> None:
        """convert_powershell_content_to_ansible is accessible from souschef.server."""
        from souschef.server import convert_powershell_content_to_ansible

        assert callable(convert_powershell_content_to_ansible)

    def test_parse_powershell_script_function_works(self, tmp_path: Path) -> None:
        """The re-exported parse_powershell_script function works end-to-end."""
        from souschef.server import parse_powershell_script

        script = tmp_path / "setup.ps1"
        script.write_text("Start-Service -Name W3SVC\n", encoding="utf-8")

        result = json.loads(parse_powershell_script(str(script)))
        assert "actions" in result

    def test_convert_powershell_to_ansible_function_works(
        self, tmp_path: Path
    ) -> None:
        """The re-exported convert_powershell_to_ansible function works end-to-end."""
        from souschef.server import convert_powershell_to_ansible

        script = tmp_path / "setup.ps1"
        script.write_text("Start-Service -Name W3SVC\n", encoding="utf-8")

        result = json.loads(convert_powershell_to_ansible(str(script)))
        assert result["status"] == "success"
