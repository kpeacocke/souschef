"""
Unit tests for enterprise PowerShell CLI commands in souschef/cli.py.

Tests for the powershell-inventory, powershell-requirements, powershell-role,
powershell-job-template, and powershell-fidelity commands.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture()
def runner() -> CliRunner:
    """Create a Click CliRunner for testing."""
    return CliRunner()


@pytest.fixture()
def cli():
    """Import the CLI group."""
    from souschef.cli import cli as _cli

    return _cli


@pytest.fixture()
def sample_ps1(tmp_path: Path) -> Path:
    """Create a sample PowerShell script for testing."""
    script = tmp_path / "setup.ps1"
    script.write_text(
        "Install-WindowsFeature -Name Web-Server -IncludeManagementTools\n"
        "Start-Service -Name W3SVC\n"
        "Set-Service -Name W3SVC -StartupType Automatic\n"
        "New-LocalUser -Name svc_myapp\n"
        "New-NetFirewallRule -DisplayName 'MyApp HTTP'\n"
        "choco install nodejs\n",
        encoding="utf-8",
    )
    return script


class TestPowershellInventoryCli:
    """Tests for the powershell-inventory CLI command."""

    def test_outputs_inventory_by_default(self, runner: CliRunner, cli) -> None:
        """Command prints WinRM inventory to stdout by default."""
        result = runner.invoke(cli, ["powershell-inventory"])
        assert result.exit_code == 0
        assert "[windows]" in result.output
        assert "ansible_connection=winrm" in result.output

    def test_custom_hosts(self, runner: CliRunner, cli) -> None:
        """Command includes specified hosts."""
        result = runner.invoke(
            cli,
            ["powershell-inventory", "--hosts", "win01.example.com"],
        )
        assert result.exit_code == 0
        assert "win01.example.com" in result.output

    def test_custom_winrm_port(self, runner: CliRunner, cli) -> None:
        """Command uses specified WinRM port."""
        result = runner.invoke(
            cli,
            ["powershell-inventory", "--winrm-port", "5985"],
        )
        assert result.exit_code == 0
        assert "5985" in result.output

    def test_no_ssl_flag(self, runner: CliRunner, cli) -> None:
        """Command uses basic transport with --no-ssl."""
        result = runner.invoke(cli, ["powershell-inventory", "--no-ssl"])
        assert result.exit_code == 0
        assert "basic" in result.output

    def test_multiple_hosts_in_output(
        self, runner: CliRunner, cli, tmp_path: Path
    ) -> None:
        """Command includes multiple specified hosts in output."""
        result = runner.invoke(
            cli,
            ["powershell-inventory", "--hosts", "wina.example.com,winb.example.com"],
        )
        assert result.exit_code == 0
        assert "wina.example.com" in result.output
        assert "winb.example.com" in result.output


class TestPowershellRequirementsCli:
    """Tests for the powershell-requirements CLI command."""

    def test_outputs_requirements_yaml(self, runner: CliRunner, cli) -> None:
        """Command outputs requirements.yml YAML content."""
        result = runner.invoke(cli, ["powershell-requirements"])
        assert result.exit_code == 0
        assert "ansible.windows" in result.output
        assert "collections:" in result.output

    def test_with_script_tailors_output(
        self, runner: CliRunner, cli, sample_ps1: Path
    ) -> None:
        """Command tailors requirements to the provided script."""
        result = runner.invoke(cli, ["powershell-requirements", str(sample_ps1)])
        assert result.exit_code == 0
        assert "ansible.windows" in result.output

    def test_chocolatey_collection_for_choco_script(
        self, runner: CliRunner, cli, tmp_path: Path
    ) -> None:
        """Command includes chocolatey collection for choco install scripts."""
        script = tmp_path / "choco.ps1"
        script.write_text("choco install git\n", encoding="utf-8")

        result = runner.invoke(cli, ["powershell-requirements", str(script)])
        assert result.exit_code == 0
        assert "chocolatey" in result.output

    def test_output_is_valid_yaml(self, runner: CliRunner, cli, tmp_path: Path) -> None:
        """Command output is valid YAML."""
        import yaml

        result = runner.invoke(cli, ["powershell-requirements"])
        assert result.exit_code == 0
        parsed = yaml.safe_load(result.output)
        assert isinstance(parsed.get("collections"), list)


class TestPowershellRoleCli:
    """Tests for the powershell-role CLI command."""

    def test_outputs_json_by_default(
        self, runner: CliRunner, cli, sample_ps1: Path
    ) -> None:
        """Command prints JSON file map to stdout."""
        result = runner.invoke(cli, ["powershell-role", str(sample_ps1)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "files" in data
        assert data["file_count"] > 0

    def test_custom_role_name(self, runner: CliRunner, cli, sample_ps1: Path) -> None:
        """Custom role name appears in generated file paths."""
        result = runner.invoke(
            cli,
            ["powershell-role", str(sample_ps1), "--role-name", "acme_windows"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert any("acme_windows" in k for k in data["files"])

    def test_requirements_in_role_output(
        self, runner: CliRunner, cli, sample_ps1: Path, tmp_path: Path
    ) -> None:
        """Generated role JSON includes requirements.yml content."""
        result = runner.invoke(cli, ["powershell-role", str(sample_ps1)])
        assert result.exit_code == 0
        data = __import__("json").loads(result.output)
        files = data["files"]
        assert "requirements.yml" in files

    def test_error_for_missing_file(
        self, runner: CliRunner, cli, tmp_path: Path
    ) -> None:
        """Command exits with error for a non-existent script."""
        result = runner.invoke(cli, ["powershell-role", str(tmp_path / "missing.ps1")])
        assert result.exit_code != 0


class TestPowershellJobTemplateCli:
    """Tests for the powershell-job-template CLI command."""

    def test_outputs_job_template_text(
        self, runner: CliRunner, cli, sample_ps1: Path
    ) -> None:
        """Command prints job template text to stdout."""
        result = runner.invoke(cli, ["powershell-job-template", str(sample_ps1)])
        assert result.exit_code == 0
        assert "Job Template JSON" in result.output
        assert "CLI Import Command" in result.output

    def test_custom_template_name(
        self, runner: CliRunner, cli, sample_ps1: Path
    ) -> None:
        """Custom template name appears in output."""
        result = runner.invoke(
            cli,
            [
                "powershell-job-template",
                str(sample_ps1),
                "--name",
                "My Windows Setup",
            ],
        )
        assert result.exit_code == 0
        assert "My Windows Setup" in result.output

    def test_custom_environment(self, runner: CliRunner, cli, sample_ps1: Path) -> None:
        """Custom environment label appears in output."""
        result = runner.invoke(
            cli,
            [
                "powershell-job-template",
                str(sample_ps1),
                "--environment",
                "staging",
            ],
        )
        assert result.exit_code == 0
        assert "staging" in result.output

    def test_write_to_file(
        self, runner: CliRunner, cli, sample_ps1: Path, tmp_path: Path
    ) -> None:
        """Command writes job template to file when --output is specified."""
        from souschef.core.path_utils import _get_workspace_root

        workspace = Path(_get_workspace_root())
        out_file = workspace / "tmp_test_job_template.md"
        try:
            result = runner.invoke(
                cli,
                [
                    "powershell-job-template",
                    str(sample_ps1),
                    "--output",
                    str(out_file),
                ],
            )
            assert result.exit_code == 0
            assert out_file.exists()
            assert "Job Template JSON" in out_file.read_text(encoding="utf-8")
        finally:
            if out_file.exists():
                out_file.unlink()

    def test_error_for_missing_file(
        self, runner: CliRunner, cli, tmp_path: Path
    ) -> None:
        """Command exits with error for a non-existent script."""
        result = runner.invoke(
            cli, ["powershell-job-template", str(tmp_path / "missing.ps1")]
        )
        assert result.exit_code != 0


class TestPowershellFidelityCli:
    """Tests for the powershell-fidelity CLI command."""

    def test_outputs_fidelity_json(
        self, runner: CliRunner, cli, sample_ps1: Path
    ) -> None:
        """Command outputs fidelity JSON by default."""
        result = runner.invoke(cli, ["powershell-fidelity", str(sample_ps1)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "fidelity_score" in data
        assert 0 <= data["fidelity_score"] <= 100

    def test_high_fidelity_script(
        self, runner: CliRunner, cli, sample_ps1: Path
    ) -> None:
        """Script with known actions achieves non-zero fidelity."""
        result = runner.invoke(cli, ["powershell-fidelity", str(sample_ps1)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["fidelity_score"] > 0

    def test_recommendations_included(
        self, runner: CliRunner, cli, sample_ps1: Path
    ) -> None:
        """Fidelity output includes recommendations list."""
        result = runner.invoke(cli, ["powershell-fidelity", str(sample_ps1)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data.get("recommendations"), list)

    def test_error_for_missing_file(
        self, runner: CliRunner, cli, tmp_path: Path
    ) -> None:
        """Command exits with error for a non-existent script."""
        result = runner.invoke(
            cli, ["powershell-fidelity", str(tmp_path / "missing.ps1")]
        )
        assert result.exit_code != 0
