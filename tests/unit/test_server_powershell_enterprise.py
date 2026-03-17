"""
Unit tests for enterprise PowerShell MCP tools in souschef/server.py.

Tests for the generate_windows_inventory_tool, generate_windows_requirements,
generate_powershell_role, generate_powershell_job_template, and
analyze_powershell_fidelity MCP tools.
"""

from __future__ import annotations

import json
from pathlib import Path


class TestGenerateWindowsInventoryTool:
    """Tests for the generate_windows_inventory_tool() MCP tool."""

    def test_returns_ini_with_windows_group(self) -> None:
        """Tool returns inventory containing [windows] group."""
        from souschef.server import generate_windows_inventory_tool

        result = generate_windows_inventory_tool()
        assert "[windows]" in result
        assert "ansible_connection=winrm" in result

    def test_custom_hosts_included(self) -> None:
        """Tool includes specified hosts in the inventory."""
        from souschef.server import generate_windows_inventory_tool

        result = generate_windows_inventory_tool(
            hosts="host1.example.com,host2.example.com"
        )
        assert "host1.example.com" in result
        assert "host2.example.com" in result

    def test_custom_winrm_port(self) -> None:
        """Tool uses specified WinRM port."""
        from souschef.server import generate_windows_inventory_tool

        result = generate_windows_inventory_tool(winrm_port=5985)
        assert "5985" in result

    def test_no_ssl_uses_http_scheme(self) -> None:
        """Tool switches to http scheme when use_ssl=False."""
        from souschef.server import generate_windows_inventory_tool

        result = generate_windows_inventory_tool(use_ssl=False)
        assert "ansible_winrm_scheme=http" in result


class TestGenerateWindowsRequirements:
    """Tests for the generate_windows_requirements() MCP tool."""

    def test_returns_requirements_yaml_no_path(self) -> None:
        """Tool returns requirements.yml YAML when no script path given."""
        from souschef.server import generate_windows_requirements

        result = generate_windows_requirements()
        assert "ansible.windows" in result
        assert "collections:" in result

    def test_returns_yaml_for_valid_script(self, tmp_path: Path) -> None:
        """Tool returns tailored requirements for a valid script."""
        from souschef.server import generate_windows_requirements

        script = tmp_path / "setup.ps1"
        script.write_text("choco install nodejs\n", encoding="utf-8")

        result = generate_windows_requirements(str(script))
        assert "ansible.windows" in result
        assert "chocolatey" in result

    def test_empty_path_includes_all_collections(self) -> None:
        """Tool with empty path includes all Windows collections."""
        from souschef.server import generate_windows_requirements

        result = generate_windows_requirements("")
        assert "community.windows" in result
        assert "ansible.windows" in result

    def test_returns_valid_yaml(self) -> None:
        """Tool returns parseable YAML."""
        import yaml

        from souschef.server import generate_windows_requirements

        result = generate_windows_requirements()
        parsed = yaml.safe_load(result)
        assert "collections" in parsed


class TestGeneratePowershellRole:
    """Tests for the generate_powershell_role() MCP tool."""

    def test_returns_success_for_valid_script(self, tmp_path: Path) -> None:
        """Tool returns success status and file dict for valid script."""
        from souschef.server import generate_powershell_role

        script = tmp_path / "setup.ps1"
        script.write_text("Install-WindowsFeature -Name Web-Server\n", encoding="utf-8")

        raw = generate_powershell_role(str(script))
        result = json.loads(raw)
        assert result["status"] == "success"
        assert "files" in result
        assert result["file_count"] > 0

    def test_returns_error_for_missing_file(self, tmp_path: Path) -> None:
        """Tool returns error status for a missing script."""
        from souschef.server import generate_powershell_role

        raw = generate_powershell_role(str(tmp_path / "missing.ps1"))
        result = json.loads(raw)
        assert result["status"] == "error"

    def test_role_files_contain_tasks_main(self, tmp_path: Path) -> None:
        """Generated role includes tasks/main.yml."""
        from souschef.server import generate_powershell_role

        script = tmp_path / "setup.ps1"
        script.write_text("Start-Service -Name W3SVC\n", encoding="utf-8")

        raw = generate_powershell_role(str(script))
        result = json.loads(raw)
        files = result["files"]
        tasks_files = [k for k in files if "tasks/main.yml" in k]
        assert tasks_files, "Expected tasks/main.yml in generated files"

    def test_role_files_contain_inventory(self, tmp_path: Path) -> None:
        """Generated role includes inventory/hosts."""
        from souschef.server import generate_powershell_role

        script = tmp_path / "setup.ps1"
        script.write_text("Start-Service -Name W3SVC\n", encoding="utf-8")

        raw = generate_powershell_role(str(script))
        result = json.loads(raw)
        files = result["files"]
        assert any("inventory" in k for k in files)

    def test_custom_role_name(self, tmp_path: Path) -> None:
        """Custom role_name is reflected in file paths."""
        from souschef.server import generate_powershell_role

        script = tmp_path / "setup.ps1"
        script.write_text("choco install git\n", encoding="utf-8")

        raw = generate_powershell_role(str(script), role_name="my_custom_role")
        result = json.loads(raw)
        files = result["files"]
        assert any("my_custom_role" in k for k in files)


class TestGeneratePowershellJobTemplate:
    """Tests for the generate_powershell_job_template() MCP tool."""

    def test_returns_job_template_for_valid_script(self, tmp_path: Path) -> None:
        """Tool returns job template text for a valid script."""
        from souschef.server import generate_powershell_job_template

        script = tmp_path / "setup.ps1"
        script.write_text("Install-WindowsFeature -Name Web-Server\n", encoding="utf-8")

        result = generate_powershell_job_template(str(script))
        assert "Job Template JSON" in result
        assert "CLI Import Command" in result

    def test_returns_error_for_missing_file(self, tmp_path: Path) -> None:
        """Tool returns error string for a missing script."""
        from souschef.server import generate_powershell_job_template

        result = generate_powershell_job_template(str(tmp_path / "missing.ps1"))
        assert "Error" in result or "not found" in result.lower()

    def test_custom_template_name_in_output(self, tmp_path: Path) -> None:
        """Custom job_template_name appears in the output."""
        from souschef.server import generate_powershell_job_template

        script = tmp_path / "setup.ps1"
        script.write_text("Start-Service W3SVC\n", encoding="utf-8")

        result = generate_powershell_job_template(
            str(script), job_template_name="My Windows Template"
        )
        assert "My Windows Template" in result

    def test_survey_included_by_default(self, tmp_path: Path) -> None:
        """Survey spec is referenced when include_survey=True (default)."""
        from souschef.server import generate_powershell_job_template

        script = tmp_path / "setup.ps1"
        script.write_text(
            "[System.Environment]::SetEnvironmentVariable('APP_HOME', 'C:\\App', 'Machine')\n",
            encoding="utf-8",
        )

        result = generate_powershell_job_template(str(script))
        assert "survey_enabled" in result or "survey" in result.lower()

    def test_environment_in_output(self, tmp_path: Path) -> None:
        """Environment label appears in the generated output."""
        from souschef.server import generate_powershell_job_template

        script = tmp_path / "setup.ps1"
        script.write_text("choco install git\n", encoding="utf-8")

        result = generate_powershell_job_template(str(script), environment="staging")
        assert "staging" in result


class TestAnalyzePowershellFidelity:
    """Tests for the analyze_powershell_fidelity() MCP tool."""

    def test_returns_fidelity_score(self, tmp_path: Path) -> None:
        """Tool returns a valid fidelity_score between 0 and 100."""
        from souschef.server import analyze_powershell_fidelity

        script = tmp_path / "setup.ps1"
        script.write_text(
            "Install-WindowsFeature -Name Web-Server\n"
            "Start-Service W3SVC\n"
            "choco install nodejs\n",
            encoding="utf-8",
        )

        result = json.loads(analyze_powershell_fidelity(str(script)))
        assert "fidelity_score" in result
        assert 0 <= result["fidelity_score"] <= 100

    def test_returns_error_for_missing_file(self, tmp_path: Path) -> None:
        """Tool returns error status for a missing file."""
        from souschef.server import analyze_powershell_fidelity

        result = json.loads(analyze_powershell_fidelity(str(tmp_path / "nope.ps1")))
        assert result.get("status") == "error"

    def test_high_fidelity_script(self, tmp_path: Path) -> None:
        """Script with only recognised actions has fidelity_score > 0."""
        from souschef.server import analyze_powershell_fidelity

        script = tmp_path / "setup.ps1"
        script.write_text(
            "Install-WindowsFeature -Name Web-Server\n"
            "Set-Service -Name W3SVC -StartupType Automatic\n",
            encoding="utf-8",
        )

        result = json.loads(analyze_powershell_fidelity(str(script)))
        assert result["fidelity_score"] > 0

    def test_all_fallbacks_gives_zero_fidelity(self, tmp_path: Path) -> None:
        """Script with only unrecognised commands has fidelity_score of 0."""
        from souschef.server import analyze_powershell_fidelity

        script = tmp_path / "setup.ps1"
        script.write_text(
            "Invoke-SomeWeirdCustomCmdlet -Param1 foo\nDoSomethingMagical -Foo bar\n",
            encoding="utf-8",
        )

        result = json.loads(analyze_powershell_fidelity(str(script)))
        assert result["fidelity_score"] == 0

    def test_recommendations_present(self, tmp_path: Path) -> None:
        """Fidelity result always includes recommendations."""
        from souschef.server import analyze_powershell_fidelity

        script = tmp_path / "setup.ps1"
        script.write_text("choco install git\n", encoding="utf-8")

        result = json.loads(analyze_powershell_fidelity(str(script)))
        assert isinstance(result.get("recommendations"), list)
        assert len(result["recommendations"]) > 0


class TestServerReExports:
    """Tests that enterprise generator functions are re-exported from server.py."""

    def test_generate_windows_inventory_exported(self) -> None:
        """generate_windows_inventory is accessible from souschef.server."""
        from souschef.server import generate_windows_inventory

        result = generate_windows_inventory()
        assert "[windows]" in result

    def test_generate_windows_group_vars_exported(self) -> None:
        """generate_windows_group_vars is accessible from souschef.server."""
        from souschef.server import generate_windows_group_vars

        result = generate_windows_group_vars()
        assert "ansible_connection" in result

    def test_generate_ansible_requirements_exported(self) -> None:
        """generate_ansible_requirements is accessible from souschef.server."""
        from souschef.server import generate_ansible_requirements

        result = generate_ansible_requirements()
        assert "ansible.windows" in result

    def test_generate_powershell_role_structure_exported(self) -> None:
        """generate_powershell_role_structure is accessible from souschef.server."""
        from souschef.server import generate_powershell_role_structure

        parsed_ir: dict = {
            "source": "<test>",
            "actions": [],
            "warnings": [],
            "metrics": {},
        }
        files = generate_powershell_role_structure(parsed_ir)
        assert isinstance(files, dict)
        assert len(files) > 0

    def test_generate_powershell_awx_job_template_exported(self) -> None:
        """generate_powershell_awx_job_template is accessible from souschef.server."""
        from souschef.server import generate_powershell_awx_job_template

        parsed_ir: dict = {
            "source": "<test>",
            "actions": [],
            "warnings": [],
            "metrics": {},
        }
        result = generate_powershell_awx_job_template(parsed_ir)
        assert "Job Template JSON" in result

    def test_analyze_powershell_migration_fidelity_exported(self) -> None:
        """analyze_powershell_migration_fidelity is accessible from souschef.server."""
        from souschef.server import analyze_powershell_migration_fidelity

        parsed_ir: dict = {
            "source": "<test>",
            "actions": [],
            "warnings": [],
            "metrics": {},
        }
        result = json.loads(analyze_powershell_migration_fidelity(parsed_ir))
        assert result["fidelity_score"] == 100
