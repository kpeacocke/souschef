"""Targeted CLI command tests for Bash, PowerShell, and Puppet command branches."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from souschef.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI runner."""
    return CliRunner()


def test_bash_parse_outputs_to_stdout(runner: CliRunner, tmp_path: Path) -> None:
    """Bash parse should echo parser output when no file is requested."""
    script = tmp_path / "script.sh"
    script.write_text("echo hi")

    with patch("souschef.cli.parse_bash_script", return_value="parsed"):
        result = runner.invoke(cli, ["bash", "parse", str(script)])

    assert result.exit_code == 0
    assert "parsed" in result.output


def test_bash_parse_writes_to_file_path(runner: CliRunner, tmp_path: Path) -> None:
    """Bash parse should write via _safe_write_file when output is provided."""
    script = tmp_path / "script.sh"
    script.write_text("echo hi")

    with (
        patch("souschef.cli.parse_bash_script", return_value="parsed"),
        patch("souschef.cli._safe_write_file") as safe_write_mock,
    ):
        result = runner.invoke(cli, ["bash", "parse", str(script), "--output", "x.txt"])

    assert result.exit_code == 0
    safe_write_mock.assert_called_once()


def test_bash_parse_handles_error(runner: CliRunner, tmp_path: Path) -> None:
    """Bash parse should exit with error when parser fails."""
    script = tmp_path / "script.sh"
    script.write_text("echo hi")

    with patch("souschef.cli.parse_bash_script", side_effect=ValueError("bad script")):
        result = runner.invoke(cli, ["bash", "parse", str(script)])

    assert result.exit_code == 1
    assert "Error parsing Bash script" in result.output


def test_bash_convert_prints_warnings(runner: CliRunner, tmp_path: Path) -> None:
    """Bash convert should emit warnings from successful conversion output."""
    script = tmp_path / "script.sh"
    script.write_text("echo hi")
    payload = {
        "status": "success",
        "playbook_yaml": "---\n- hosts: all",
        "warnings": ["manual review needed"],
    }

    with patch(
        "souschef.cli.convert_bash_to_ansible", return_value=json.dumps(payload)
    ):
        result = runner.invoke(cli, ["bash", "convert", str(script)])

    assert result.exit_code == 0
    assert "Warnings:" in result.output


def test_bash_convert_handles_invalid_json(runner: CliRunner, tmp_path: Path) -> None:
    """Bash convert should fail cleanly on invalid JSON from converter."""
    script = tmp_path / "script.sh"
    script.write_text("echo hi")

    with patch("souschef.cli.convert_bash_to_ansible", return_value="not-json"):
        result = runner.invoke(cli, ["bash", "convert", str(script)])

    assert result.exit_code == 1
    assert "invalid JSON" in result.output


def test_bash_convert_error_status_and_output_write(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """Bash convert should handle status error and output-file writes."""
    script = tmp_path / "script.sh"
    script.write_text("echo hi")

    error_payload = {"status": "error", "error": "conversion failed"}
    with patch(
        "souschef.cli.convert_bash_to_ansible",
        return_value=json.dumps(error_payload),
    ):
        error_result = runner.invoke(cli, ["bash", "convert", str(script)])

    success_payload = {"status": "success", "playbook_yaml": "---\n- hosts: all"}
    with (
        patch(
            "souschef.cli.convert_bash_to_ansible",
            return_value=json.dumps(success_payload),
        ),
        patch("souschef.cli._safe_write_file") as safe_write_mock,
    ):
        success_result = runner.invoke(
            cli,
            ["bash", "convert", str(script), "--output", "playbook.yml"],
        )

    assert error_result.exit_code == 1
    assert "Error: conversion failed" in error_result.output
    assert success_result.exit_code == 0
    safe_write_mock.assert_called_once()


def test_bash_role_writes_files_to_output_dir(
    runner: CliRunner, tmp_path: Path
) -> None:
    """Bash role should write generated files when output-dir is provided."""
    script = tmp_path / "script.sh"
    script.write_text("echo hi")
    output_dir = tmp_path / "out"
    payload = {
        "status": "success",
        "files": {"tasks/main.yml": "- debug: msg='hi'"},
    }

    with (
        patch(
            "souschef.cli.generate_ansible_role_from_bash",
            return_value=json.dumps(payload),
        ),
        patch("souschef.cli._get_workspace_root", return_value=tmp_path),
        patch("souschef.cli.safe_write_text") as write_mock,
    ):
        result = runner.invoke(
            cli,
            ["bash", "role", str(script), "--output-dir", str(output_dir)],
        )

    assert result.exit_code == 0
    assert "Role written to" in result.output
    write_mock.assert_called()


def test_bash_role_error_and_stdout_paths(runner: CliRunner, tmp_path: Path) -> None:
    """Bash role should handle converter errors and stdout rendering mode."""
    script = tmp_path / "script.sh"
    script.write_text("echo hi")

    with patch(
        "souschef.cli.generate_ansible_role_from_bash",
        return_value=json.dumps({"status": "error", "error": "role failed"}),
    ):
        error_result = runner.invoke(cli, ["bash", "role", str(script)])

    with patch(
        "souschef.cli.generate_ansible_role_from_bash",
        return_value=json.dumps(
            {
                "status": "success",
                "files": {"tasks/main.yml": "- debug: msg='ok'"},
            }
        ),
    ):
        stdout_result = runner.invoke(cli, ["bash", "role", str(script)])

    assert error_result.exit_code == 1
    assert "Error: role failed" in error_result.output
    assert stdout_result.exit_code == 0
    assert "# --- tasks/main.yml ---" in stdout_result.output


def test_powershell_parse_calls_output_result(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """powershell-parse should route parser output through _output_result."""
    script = tmp_path / "setup.ps1"
    script.write_text("Write-Output 'ok'")

    with (
        patch(
            "souschef.server.parse_powershell_script", return_value='{"actions": []}'
        ),
        patch("souschef.cli._output_result") as output_mock,
    ):
        result = runner.invoke(
            cli, ["powershell-parse", str(script), "--format", "json"]
        )

    assert result.exit_code == 0
    output_mock.assert_called_once()


def test_powershell_convert_writes_output_and_stats(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """powershell-convert should write playbook and print conversion stats."""
    script = tmp_path / "setup.ps1"
    script.write_text("Write-Output 'ok'")
    output_file = tmp_path / "playbook.yml"
    payload = {
        "playbook_yaml": "---\n- hosts: windows",
        "tasks_generated": 2,
        "win_shell_fallbacks": 1,
        "warnings": ["check manually"],
    }

    with (
        patch(
            "souschef.server.convert_powershell_to_ansible",
            return_value=json.dumps(payload),
        ),
        patch("souschef.cli._get_workspace_root", return_value=tmp_path),
        patch("souschef.cli.safe_write_text") as write_mock,
    ):
        result = runner.invoke(
            cli,
            ["powershell-convert", str(script), "--output", str(output_file)],
        )

    assert result.exit_code == 0
    assert "Playbook written to" in result.output
    assert "Tasks generated" in result.output
    write_mock.assert_called_once()


def test_powershell_convert_handles_invalid_json(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """powershell-convert should return error when conversion output is invalid JSON."""
    script = tmp_path / "setup.ps1"
    script.write_text("Write-Output 'ok'")

    with patch("souschef.server.convert_powershell_to_ansible", return_value="{bad"):
        result = runner.invoke(
            cli,
            ["powershell-convert", str(script), "--output", "out.yml"],
        )

    assert result.exit_code == 1
    assert "Error parsing conversion result" in result.output


def test_powershell_convert_write_error_and_stdout_fallback(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """powershell-convert should handle output write errors and stdout mode."""
    script = tmp_path / "setup.ps1"
    script.write_text("Write-Output 'ok'")
    payload = {
        "playbook_yaml": "---\n- hosts: windows",
        "tasks_generated": 1,
        "win_shell_fallbacks": 0,
    }

    with (
        patch(
            "souschef.server.convert_powershell_to_ansible",
            return_value=json.dumps(payload),
        ),
        patch("souschef.cli._get_workspace_root", return_value=tmp_path),
        patch(
            "souschef.cli._ensure_within_base_path", side_effect=ValueError("bad path")
        ),
    ):
        write_error_result = runner.invoke(
            cli,
            ["powershell-convert", str(script), "--output", "out.yml"],
        )

    with (
        patch(
            "souschef.server.convert_powershell_to_ansible",
            return_value=json.dumps(payload),
        ),
        patch("souschef.cli._output_result") as output_mock,
    ):
        stdout_result = runner.invoke(cli, ["powershell-convert", str(script)])

    assert write_error_result.exit_code == 1
    assert "Error writing output file" in write_error_result.output
    assert stdout_result.exit_code == 0
    output_mock.assert_called_once()


def test_powershell_convert_handles_unexpected_output_exception(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """powershell-convert should handle unexpected output-path exceptions."""
    script = tmp_path / "setup.ps1"
    script.write_text("Write-Output 'ok'")
    payload = {
        "playbook_yaml": "---\n- hosts: windows",
        "tasks_generated": 1,
        "win_shell_fallbacks": 0,
    }

    with (
        patch(
            "souschef.server.convert_powershell_to_ansible",
            return_value=json.dumps(payload),
        ),
        patch("souschef.cli._get_workspace_root", return_value=tmp_path),
        patch(
            "souschef.cli._ensure_within_base_path", side_effect=RuntimeError("boom")
        ),
    ):
        result = runner.invoke(
            cli,
            ["powershell-convert", str(script), "--output", "out.yml"],
        )

    assert result.exit_code == 1
    assert "Unexpected error during output" in result.output


def test_powershell_inventory_output_write_error(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """powershell-inventory should fail when output write path validation fails."""
    with (
        patch(
            "souschef.generators.powershell.generate_windows_inventory",
            return_value="[windows]\nwin01",
        ),
        patch("souschef.cli._get_workspace_root", return_value=tmp_path),
        patch(
            "souschef.cli._ensure_within_base_path", side_effect=ValueError("bad path")
        ),
    ):
        result = runner.invoke(cli, ["powershell-inventory", "--output", "inv.ini"])

    assert result.exit_code == 1
    assert "Error writing inventory file" in result.output


def test_powershell_inventory_output_success(runner: CliRunner, tmp_path: Path) -> None:
    """powershell-inventory should write successfully when output path is valid."""
    with (
        patch(
            "souschef.generators.powershell.generate_windows_inventory",
            return_value="[windows]\nwin01",
        ),
        patch("souschef.cli._get_workspace_root", return_value=tmp_path),
        patch(
            "souschef.cli._ensure_within_base_path", return_value=tmp_path / "inv.ini"
        ),
        patch("souschef.cli.safe_write_text") as write_mock,
    ):
        result = runner.invoke(cli, ["powershell-inventory", "--output", "inv.ini"])

    assert result.exit_code == 0
    assert "Inventory written to" in result.output
    write_mock.assert_called_once()


def test_powershell_requirements_output_write_error(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """powershell-requirements should fail on output write errors."""
    script = tmp_path / "setup.ps1"
    script.write_text("Write-Output 'ok'")

    with (
        patch(
            "souschef.parsers.powershell.parse_powershell_script",
            return_value='{"actions": []}',
        ),
        patch(
            "souschef.generators.powershell.generate_ansible_requirements",
            return_value="---\ncollections: []",
        ),
        patch("souschef.cli._get_workspace_root", return_value=tmp_path),
        patch(
            "souschef.cli._ensure_within_base_path", side_effect=ValueError("bad path")
        ),
    ):
        result = runner.invoke(
            cli,
            ["powershell-requirements", str(script), "--output", "requirements.yml"],
        )

    assert result.exit_code == 1
    assert "Error writing requirements file" in result.output


def test_powershell_requirements_output_success(
    runner: CliRunner, tmp_path: Path
) -> None:
    """powershell-requirements should write output on success."""
    script = tmp_path / "setup.ps1"
    script.write_text("Write-Output 'ok'")

    with (
        patch(
            "souschef.parsers.powershell.parse_powershell_script",
            return_value='{"actions": []}',
        ),
        patch(
            "souschef.generators.powershell.generate_ansible_requirements",
            return_value="---\ncollections: []",
        ),
        patch("souschef.cli._get_workspace_root", return_value=tmp_path),
        patch(
            "souschef.cli._ensure_within_base_path",
            return_value=tmp_path / "requirements.yml",
        ),
        patch("souschef.cli.safe_write_text") as write_mock,
    ):
        result = runner.invoke(
            cli,
            ["powershell-requirements", str(script), "--output", "requirements.yml"],
        )

    assert result.exit_code == 0
    assert "requirements.yml written to" in result.output
    write_mock.assert_called_once()


def test_powershell_role_handles_parser_error(
    runner: CliRunner, tmp_path: Path
) -> None:
    """powershell-role should stop when parser returns an Error payload."""
    script = tmp_path / "setup.ps1"
    script.write_text("Write-Output 'ok'")

    with patch(
        "souschef.parsers.powershell.parse_powershell_script",
        return_value="Error: parse failed",
    ):
        result = runner.invoke(cli, ["powershell-role", str(script)])

    assert result.exit_code == 1
    assert "Error:" in result.output


def test_powershell_role_writes_files(runner: CliRunner, tmp_path: Path) -> None:
    """powershell-role should write generated files and summary when output-dir is set."""
    script = tmp_path / "setup.ps1"
    script.write_text("Write-Output 'ok'")

    with (
        patch(
            "souschef.parsers.powershell.parse_powershell_script",
            return_value='{"actions": []}',
        ),
        patch(
            "souschef.generators.powershell.generate_powershell_role_structure",
            return_value={"roles/windows/tasks/main.yml": "- name: x"},
        ),
        patch("souschef.cli._get_workspace_root", return_value=tmp_path),
        patch("souschef.cli.safe_write_text") as write_mock,
    ):
        result = runner.invoke(
            cli,
            ["powershell-role", str(script), "--output-dir", str(tmp_path / "role")],
        )

    assert result.exit_code == 0
    assert "Files generated:" in result.output
    write_mock.assert_called()


def test_powershell_role_output_dir_error_path(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """powershell-role should map output write errors to CLI failures."""
    script = tmp_path / "setup.ps1"
    script.write_text("Write-Output 'ok'")

    with (
        patch(
            "souschef.parsers.powershell.parse_powershell_script",
            return_value='{"actions": []}',
        ),
        patch(
            "souschef.generators.powershell.generate_powershell_role_structure",
            return_value={"roles/windows/tasks/main.yml": "- name: x"},
        ),
        patch("souschef.cli._get_workspace_root", return_value=tmp_path),
        patch("souschef.cli.safe_write_text", side_effect=OSError("blocked")),
    ):
        result = runner.invoke(
            cli,
            ["powershell-role", str(script), "--output-dir", str(tmp_path / "role")],
        )

    assert result.exit_code == 1
    assert "Error writing role files" in result.output


def test_powershell_job_template_write_error(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """powershell-job-template should fail when writing output fails."""
    script = tmp_path / "setup.ps1"
    script.write_text("Write-Output 'ok'")

    with (
        patch(
            "souschef.parsers.powershell.parse_powershell_script",
            return_value='{"actions": []}',
        ),
        patch(
            "souschef.generators.powershell.generate_powershell_awx_job_template",
            return_value="{}",
        ),
        patch("souschef.cli._get_workspace_root", return_value=tmp_path),
        patch(
            "souschef.cli._ensure_within_base_path", side_effect=ValueError("bad path")
        ),
    ):
        result = runner.invoke(
            cli,
            ["powershell-job-template", str(script), "--output", "job.json"],
        )

    assert result.exit_code == 1
    assert "Error writing job template file" in result.output


def test_powershell_job_template_handles_parser_error(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """powershell-job-template should stop if parser returns an Error payload."""
    script = tmp_path / "setup.ps1"
    script.write_text("Write-Output 'ok'")

    with patch(
        "souschef.parsers.powershell.parse_powershell_script",
        return_value="Error: parse failed",
    ):
        result = runner.invoke(cli, ["powershell-job-template", str(script)])

    assert result.exit_code == 1
    assert "Error:" in result.output


def test_powershell_fidelity_handles_parser_error(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """powershell-fidelity should stop on parser Error payloads."""
    script = tmp_path / "setup.ps1"
    script.write_text("Write-Output 'ok'")

    with patch(
        "souschef.parsers.powershell.parse_powershell_script",
        return_value="Error: parse failed",
    ):
        result = runner.invoke(cli, ["powershell-fidelity", str(script)])

    assert result.exit_code == 1
    assert "Error:" in result.output


def test_puppet_parse_and_convert_error_paths(
    runner: CliRunner, tmp_path: Path
) -> None:
    """Puppet parse/convert commands should map exceptions to CLI errors."""
    manifest = tmp_path / "site.pp"
    manifest.write_text("notify { 'x': }")

    with patch("souschef.server.parse_puppet_manifest", side_effect=ValueError("bad")):
        parse_result = runner.invoke(cli, ["puppet", "parse", str(manifest)])
    with patch(
        "souschef.server.convert_puppet_manifest_to_ansible",
        side_effect=OSError("bad"),
    ):
        convert_result = runner.invoke(cli, ["puppet", "convert", str(manifest)])

    assert parse_result.exit_code == 1
    assert "Error parsing Puppet manifest" in parse_result.output
    assert convert_result.exit_code == 1
    assert "Error converting Puppet manifest" in convert_result.output


def test_puppet_parse_and_convert_output_paths(
    runner: CliRunner, tmp_path: Path
) -> None:
    """Puppet parse/convert should write via _safe_write_file when output is set."""
    manifest = tmp_path / "site.pp"
    manifest.write_text("notify { 'x': }")

    with (
        patch("souschef.server.parse_puppet_manifest", return_value="parsed"),
        patch("souschef.server.convert_puppet_manifest_to_ansible", return_value="---"),
        patch("souschef.cli._safe_write_file") as safe_write_mock,
    ):
        parse_result = runner.invoke(
            cli,
            ["puppet", "parse", str(manifest), "--output", "analysis.txt"],
        )
        convert_result = runner.invoke(
            cli,
            ["puppet", "convert", str(manifest), "--output", "playbook.yml"],
        )

    assert parse_result.exit_code == 0
    assert convert_result.exit_code == 0
    assert safe_write_mock.call_count == 2


def test_puppet_parse_and_convert_stdout_paths(
    runner: CliRunner, tmp_path: Path
) -> None:
    """Puppet parse/convert should echo to stdout when output is not set."""
    manifest = tmp_path / "site.pp"
    manifest.write_text("notify { 'x': }")

    with patch("souschef.server.parse_puppet_manifest", return_value="parsed"):
        parse_result = runner.invoke(cli, ["puppet", "parse", str(manifest)])
    with patch(
        "souschef.server.convert_puppet_manifest_to_ansible", return_value="---"
    ):
        convert_result = runner.invoke(cli, ["puppet", "convert", str(manifest)])

    assert parse_result.exit_code == 0
    assert "parsed" in parse_result.output
    assert convert_result.exit_code == 0
    assert "---" in convert_result.output


def test_puppet_parse_module_error_and_list_types(
    runner: CliRunner, tmp_path: Path
) -> None:
    """Puppet parse-module error handling and list-types output."""
    module_dir = tmp_path / "m"
    module_dir.mkdir()

    with patch("souschef.server.parse_puppet_module", side_effect=ValueError("bad")):
        parse_mod_result = runner.invoke(
            cli, ["puppet", "parse-module", str(module_dir)]
        )
    with patch(
        "souschef.server.list_puppet_supported_resource_types",
        return_value="package\nservice",
    ):
        list_types_result = runner.invoke(cli, ["puppet", "list-types"])

    assert parse_mod_result.exit_code == 1
    assert "Error parsing Puppet module" in parse_mod_result.output
    assert list_types_result.exit_code == 0
    assert "package" in list_types_result.output


def test_puppet_parse_module_output_path(runner: CliRunner, tmp_path: Path) -> None:
    """Puppet parse-module should write output when requested."""
    module_dir = tmp_path / "m"
    module_dir.mkdir()

    with (
        patch("souschef.server.parse_puppet_module", return_value="parsed module"),
        patch("souschef.cli._safe_write_file") as safe_write_mock,
    ):
        result = runner.invoke(
            cli,
            ["puppet", "parse-module", str(module_dir), "--output", "module.txt"],
        )

    assert result.exit_code == 0
    safe_write_mock.assert_called_once()


def test_puppet_parse_module_stdout_path(runner: CliRunner, tmp_path: Path) -> None:
    """Puppet parse-module should echo output when no file path is supplied."""
    module_dir = tmp_path / "m"
    module_dir.mkdir()

    with patch("souschef.server.parse_puppet_module", return_value="parsed module"):
        result = runner.invoke(cli, ["puppet", "parse-module", str(module_dir)])

    assert result.exit_code == 0
    assert "parsed module" in result.output


def test_puppet_convert_module_output_dir_and_error(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """Puppet convert-module should support output-dir writes and error mapping."""
    module_dir = tmp_path / "m"
    module_dir.mkdir()

    with patch(
        "souschef.server.convert_puppet_module_to_ansible",
        return_value="---\n- hosts: all",
    ):
        success_result = runner.invoke(
            cli,
            [
                "puppet",
                "convert-module",
                str(module_dir),
                "--output-dir",
                str(tmp_path / "out"),
            ],
        )

    with patch(
        "souschef.server.convert_puppet_module_to_ansible",
        side_effect=ValueError("bad"),
    ):
        error_result = runner.invoke(cli, ["puppet", "convert-module", str(module_dir)])

    assert success_result.exit_code == 0
    assert "Playbook written to" in success_result.output
    assert error_result.exit_code == 1
    assert "Error converting Puppet module" in error_result.output


def test_puppet_convert_module_output_and_stdout_paths(
    runner: CliRunner,
    tmp_path: Path,
) -> None:
    """Puppet convert-module should support explicit output and stdout fallback."""
    module_dir = tmp_path / "m"
    module_dir.mkdir()

    with (
        patch(
            "souschef.server.convert_puppet_module_to_ansible",
            return_value="---\n- hosts: all",
        ),
        patch("souschef.cli._safe_write_file") as safe_write_mock,
    ):
        output_result = runner.invoke(
            cli,
            ["puppet", "convert-module", str(module_dir), "--output", "playbook.yml"],
        )

    with patch(
        "souschef.server.convert_puppet_module_to_ansible",
        return_value="---\n- hosts: all",
    ):
        stdout_result = runner.invoke(
            cli, ["puppet", "convert-module", str(module_dir)]
        )

    assert output_result.exit_code == 0
    safe_write_mock.assert_called_once()
    assert stdout_result.exit_code == 0
    assert "hosts: all" in stdout_result.output
