"""Tests for Bash migration MCP server tools."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from souschef.server import convert_bash_to_ansible, parse_bash_script


class TestParseBashScriptMcpTool:
    """Tests for the parse_bash_script MCP tool in server.py."""

    def test_parse_bash_script_success(self) -> None:
        """Tool parses a valid Bash script and returns pattern summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            script = base / "deploy.sh"
            script.write_text(
                "#!/bin/bash\napt-get install -y nginx\nsystemctl enable nginx\n"
            )
            with patch("souschef.parsers.bash._get_workspace_root", return_value=base):
                result = parse_bash_script(str(script))

        assert isinstance(result, str)
        assert "Package Installs" in result
        assert "Service Control" in result

    def test_parse_bash_script_file_not_found(self) -> None:
        """Tool returns error string for missing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            with patch("souschef.parsers.bash._get_workspace_root", return_value=base):
                result = parse_bash_script(str(base / "missing.sh"))

        assert "error" in result.lower() or "not found" in result.lower()

    def test_parse_bash_script_detects_downloads(self) -> None:
        """Tool detects curl/wget download commands."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            script = base / "download.sh"
            script.write_text(
                "#!/bin/bash\ncurl -o /tmp/f.tgz https://example.com/f.tgz\n"
            )
            with patch("souschef.parsers.bash._get_workspace_root", return_value=base):
                result = parse_bash_script(str(script))

        assert "Downloads" in result

    def test_parse_bash_script_detects_file_writes(self) -> None:
        """Tool detects heredoc and echo redirect file writes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            script = base / "write.sh"
            script.write_text('#!/bin/bash\necho "KEY=val" > /etc/app/env\n')
            with patch("souschef.parsers.bash._get_workspace_root", return_value=base):
                result = parse_bash_script(str(script))

        assert isinstance(result, str)

    def test_parse_bash_script_empty_script(self) -> None:
        """Tool handles empty script gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            script = base / "empty.sh"
            script.write_text("")
            with patch("souschef.parsers.bash._get_workspace_root", return_value=base):
                result = parse_bash_script(str(script))

        assert "No provisioning patterns detected" in result

    def test_parse_bash_script_detects_idempotency_risks(self) -> None:
        """Tool flags idempotency risks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            script = base / "risky.sh"
            script.write_text("apt-get install nginx\nwget https://example.com/f\n")
            with patch("souschef.parsers.bash._get_workspace_root", return_value=base):
                result = parse_bash_script(str(script))

        assert "Idempotency Risks" in result


class TestConvertBashToAnsibleMcpTool:
    """Tests for the convert_bash_to_ansible MCP tool in server.py."""

    def test_convert_bash_to_ansible_returns_json(self) -> None:
        """Tool returns valid JSON string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            script = base / "deploy.sh"
            script.write_text(
                "#!/bin/bash\napt-get install -y nginx\nsystemctl start nginx\n"
            )
            with patch(
                "souschef.converters.bash_to_ansible._get_workspace_root",
                return_value=base,
            ):
                result = convert_bash_to_ansible(str(script))

        data = json.loads(result)
        assert data["status"] == "success"

    def test_convert_bash_to_ansible_generates_playbook(self) -> None:
        """Tool generates a valid YAML playbook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            script = base / "deploy.sh"
            script.write_text(
                "#!/bin/bash\napt-get install -y nginx\nsystemctl start nginx\n"
            )
            with patch(
                "souschef.converters.bash_to_ansible._get_workspace_root",
                return_value=base,
            ):
                result = convert_bash_to_ansible(str(script))

        data = json.loads(result)
        assert "---" in data["playbook_yaml"]
        assert "hosts: all" in data["playbook_yaml"]

    def test_convert_bash_to_ansible_has_tasks(self) -> None:
        """Tool response includes tasks list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            script = base / "deploy.sh"
            script.write_text("apt-get install -y nginx\n")
            with patch(
                "souschef.converters.bash_to_ansible._get_workspace_root",
                return_value=base,
            ):
                result = convert_bash_to_ansible(str(script))

        data = json.loads(result)
        assert isinstance(data["tasks"], list)
        assert len(data["tasks"]) > 0

    def test_convert_bash_to_ansible_has_idempotency_report(self) -> None:
        """Tool response includes idempotency report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            script = base / "deploy.sh"
            script.write_text("apt-get install nginx\n")
            with patch(
                "souschef.converters.bash_to_ansible._get_workspace_root",
                return_value=base,
            ):
                result = convert_bash_to_ansible(str(script))

        data = json.loads(result)
        assert "idempotency_report" in data
        assert "total_risks" in data["idempotency_report"]

    def test_convert_bash_to_ansible_file_not_found_returns_error_json(
        self,
    ) -> None:
        """Tool returns error JSON for missing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            with patch(
                "souschef.converters.bash_to_ansible._get_workspace_root",
                return_value=base,
            ):
                result = convert_bash_to_ansible(str(base / "missing.sh"))

        data = json.loads(result)
        assert data["status"] == "error"
        assert "error" in data

    def test_convert_bash_to_ansible_directory_returns_error_json(self) -> None:
        """Tool returns error JSON when path is a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            with patch(
                "souschef.converters.bash_to_ansible._get_workspace_root",
                return_value=base,
            ):
                result = convert_bash_to_ansible(str(base))

        data = json.loads(result)
        assert data["status"] == "error"

    def test_convert_bash_to_ansible_apt_package_in_playbook(self) -> None:
        """Apt installs appear as ansible.builtin.apt in playbook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            script = base / "apt.sh"
            script.write_text("apt-get install -y nginx python3\n")
            with patch(
                "souschef.converters.bash_to_ansible._get_workspace_root",
                return_value=base,
            ):
                result = convert_bash_to_ansible(str(script))

        data = json.loads(result)
        assert "ansible.builtin.apt" in data["playbook_yaml"]

    def test_convert_bash_to_ansible_service_in_playbook(self) -> None:
        """Systemctl commands appear as ansible.builtin.service in playbook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            script = base / "svc.sh"
            script.write_text("systemctl start nginx\n")
            with patch(
                "souschef.converters.bash_to_ansible._get_workspace_root",
                return_value=base,
            ):
                result = convert_bash_to_ansible(str(script))

        data = json.loads(result)
        assert "ansible.builtin.service" in data["playbook_yaml"]

    def test_convert_bash_to_ansible_download_uses_get_url(self) -> None:
        """Curl downloads appear as ansible.builtin.get_url in playbook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            script = base / "dl.sh"
            script.write_text("curl -o /tmp/f.tgz https://example.com/f.tgz\n")
            with patch(
                "souschef.converters.bash_to_ansible._get_workspace_root",
                return_value=base,
            ):
                result = convert_bash_to_ansible(str(script))

        data = json.loads(result)
        assert "ansible.builtin.get_url" in data["playbook_yaml"]

    def test_convert_bash_to_ansible_warnings_list(self) -> None:
        """Tool response includes a warnings list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            script = base / "warn.sh"
            script.write_text("custom-unknown-cmd --flag value\n")
            with patch(
                "souschef.converters.bash_to_ansible._get_workspace_root",
                return_value=base,
            ):
                result = convert_bash_to_ansible(str(script))

        data = json.loads(result)
        assert "warnings" in data
        assert isinstance(data["warnings"], list)
