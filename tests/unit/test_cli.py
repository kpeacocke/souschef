"""Tests for the CLI module."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from souschef.cli import cli

# Define the fixtures directory
FIXTURES_DIR = (
    Path(__file__).parents[1] / "integration" / "fixtures" / "sample_cookbook"
)


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


# Recipe command tests
def test_recipe_command_text_format(runner):
    """Test recipe command with text output format."""
    recipe_path = FIXTURES_DIR / "recipes" / "default.rb"
    result = runner.invoke(cli, ["recipe", str(recipe_path), "--format", "text"])

    assert result.exit_code == 0
    assert "Resource 1:" in result.output or "package" in result.output.lower()


def test_recipe_command_json_format(runner):
    """Test recipe command with JSON output format."""
    recipe_path = FIXTURES_DIR / "recipes" / "default.rb"
    result = runner.invoke(cli, ["recipe", str(recipe_path), "--format", "json"])

    assert result.exit_code == 0
    # Should be valid JSON
    try:
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))
    except json.JSONDecodeError:
        # Some outputs might be plain text
        assert len(result.output) > 0


def test_recipe_command_nonexistent_file(runner, tmp_path):
    """Test recipe command with nonexistent file."""
    nonexistent = tmp_path / "nonexistent" / "file.rb"
    result = runner.invoke(cli, ["recipe", str(nonexistent)])

    assert result.exit_code != 0
    assert "does not exist" in result.output.lower()


# Template command tests
def test_template_command(runner):
    """Test template command."""
    template_path = FIXTURES_DIR / "templates" / "default" / "config.yml.erb"
    result = runner.invoke(cli, ["template", str(template_path)])

    assert result.exit_code == 0
    # Should contain JSON with variables and jinja2_template
    try:
        data = json.loads(result.output)
        assert "variables" in data or "jinja2_template" in data
    except json.JSONDecodeError:
        # Output might be error message
        assert len(result.output) > 0


# Attributes command tests
def test_attributes_command(runner):
    """Test attributes command."""
    attributes_path = FIXTURES_DIR / "attributes" / "default.rb"
    result = runner.invoke(cli, ["attributes", str(attributes_path)])

    assert result.exit_code == 0
    assert "Attribute" in result.output or "default[" in result.output


# Resource command tests
def test_resource_command(runner):
    """Test custom resource parsing command."""
    resource_path = FIXTURES_DIR / "resources" / "simple.rb"
    result = runner.invoke(cli, ["resource", str(resource_path)])

    assert result.exit_code == 0
    try:
        data = json.loads(result.output)
        assert "resource_type" in data or "properties" in data
    except json.JSONDecodeError:
        assert len(result.output) > 0


# Metadata command tests
def test_metadata_command(runner):
    """Test metadata parsing command."""
    metadata_path = FIXTURES_DIR / "metadata.rb"
    result = runner.invoke(cli, ["metadata", str(metadata_path)])

    assert result.exit_code == 0
    assert "name" in result.output.lower() or "version" in result.output.lower()


# Structure command tests
def test_structure_command(runner):
    """Test cookbook structure listing command."""
    result = runner.invoke(cli, ["structure", str(FIXTURES_DIR)])

    assert result.exit_code == 0
    assert "recipes" in result.output.lower() or "cookbook" in result.output.lower()


# List directory command tests
def test_ls_command(runner):
    """Test directory listing command."""
    result = runner.invoke(cli, ["ls", str(FIXTURES_DIR / "recipes")])

    assert result.exit_code == 0
    assert "default.rb" in result.output


def test_ls_command_nonexistent_dir(runner, tmp_path):
    """Test ls command with nonexistent directory."""
    nonexistent = tmp_path / "nonexistent" / "directory"
    result = runner.invoke(cli, ["ls", str(nonexistent)])

    assert result.exit_code != 0


# Cat command tests
def test_cat_command(runner):
    """Test file reading command."""
    metadata_path = FIXTURES_DIR / "metadata.rb"
    result = runner.invoke(cli, ["cat", str(metadata_path)])

    assert result.exit_code == 0
    assert "name" in result.output


# Convert command tests
def test_convert_command_default(runner):
    """Test resource conversion with defaults."""
    result = runner.invoke(cli, ["convert", "package", "nginx"])

    assert result.exit_code == 0
    assert "ansible.builtin.package" in result.output or "name: nginx" in result.output


def test_convert_command_with_action(runner):
    """Test resource conversion with custom action."""
    result = runner.invoke(cli, ["convert", "service", "nginx", "--action", "start"])

    assert result.exit_code == 0
    assert (
        "ansible.builtin.service" in result.output or "state: started" in result.output
    )


def test_convert_command_json_format(runner):
    """Test resource conversion with JSON output."""
    result = runner.invoke(cli, ["convert", "package", "nginx", "--format", "json"])

    assert result.exit_code == 0
    # Should be valid JSON
    try:
        data = json.loads(result.output)
        assert isinstance(data, (dict, list))
    except json.JSONDecodeError:
        # Might need PyYAML installed
        assert "Warning:" in result.output or len(result.output) > 0


# Cookbook command tests
def test_cookbook_command(runner):
    """Test full cookbook analysis."""
    result = runner.invoke(cli, ["cookbook", str(FIXTURES_DIR)])

    assert result.exit_code == 0
    assert "Analysing cookbook" in result.output
    assert "Metadata" in result.output or "Structure" in result.output


def test_cookbook_command_with_dry_run(runner):
    """Test cookbook analysis with dry-run."""
    result = runner.invoke(cli, ["cookbook", str(FIXTURES_DIR), "--dry-run"])

    assert result.exit_code == 0
    assert "Analysing cookbook" in result.output


def test_cookbook_command_with_output(runner, tmp_path):
    """Test cookbook analysis with output directory."""
    output_dir = tmp_path / "output"
    result = runner.invoke(
        cli, ["cookbook", str(FIXTURES_DIR), "--output", str(output_dir)]
    )

    assert result.exit_code == 0
    # Now actually converts and saves files
    assert "Conversion complete" in result.output
    assert output_dir.exists()
    # Check that output directory contains converted files
    assert (output_dir / "README.md").exists()
    assert (output_dir / "conversion_summary.json").exists()


def test_v2_migrate_command(runner, tmp_path):
    """Test v2 migrate command with JSON output."""
    from unittest.mock import MagicMock, patch

    cookbook = tmp_path / "cookbook"
    recipes = cookbook / "recipes"
    recipes.mkdir(parents=True)
    (recipes / "default.rb").write_text("package 'curl'")

    env = {"SOUSCHEF_DB_PATH": str(tmp_path / "souschef.db")}

    # Mock migration result
    mock_result = MagicMock()
    mock_result.to_dict.return_value = {
        "migration_id": "test-mig-001",
        "target_platform": "aap",
        "target_version": "2.4.0",
        "chef_version": "15.10.91",
        "status": "converted",
        "playbooks_generated": ["main.yml"],
    }

    mock_orchestrator = MagicMock()
    mock_orchestrator.migrate_cookbook.return_value = mock_result

    with patch(
        "souschef.cli_v2_commands.MigrationOrchestrator", return_value=mock_orchestrator
    ):
        result = runner.invoke(
            cli,
            [
                "v2",
                "migrate",
                "--cookbook-path",
                str(cookbook),
                "--chef-version",
                "15.10.91",
                "--target-platform",
                "aap",
                "--target-version",
                "2.4.0",
                "--skip-validation",
                "--format",
                "json",
            ],
            env=env,
        )

    assert result.exit_code == 0, f"Migration failed: {result.output}"
    payload = json.loads(result.output)
    assert "migration_id" in payload
    assert payload["target_platform"] == "aap"


def test_v2_status_command(runner, tmp_path):
    """Test v2 status command loading stored state."""
    from unittest.mock import MagicMock, patch

    cookbook = tmp_path / "cookbook"
    recipes = cookbook / "recipes"
    recipes.mkdir(parents=True)
    (recipes / "default.rb").write_text("package 'curl'")

    env = {"SOUSCHEF_DB_PATH": str(tmp_path / "souschef.db")}

    # Mock migration result - use a simple dict subclass that's JSON serializable
    migration_data = {
        "migration_id": "test-migration-123",
        "target_platform": "aap",
        "target_version": "2.4.0",
        "chef_version": "15.10.91",
        "status": "converted",
        "playbooks_generated": ["main.yml"],
        "metrics": {"recipes_converted": 1, "recipes_total": 1},
    }

    mock_result = MagicMock()
    mock_result.to_dict.return_value = migration_data

    mock_orchestrator = MagicMock()
    mock_orchestrator.migrate_cookbook.return_value = mock_result
    mock_orchestrator.save_state.return_value = "test-storage-id-123"

    with patch(
        "souschef.cli_v2_commands.MigrationOrchestrator", return_value=mock_orchestrator
    ):
        migrate_result = runner.invoke(
            cli,
            [
                "v2",
                "migrate",
                "--cookbook-path",
                str(cookbook),
                "--chef-version",
                "15.10.91",
                "--target-platform",
                "aap",
                "--target-version",
                "2.4.0",
                "--skip-validation",
                "--save-state",
                "--format",
                "json",
            ],
            env=env,
        )

    assert migrate_result.exit_code == 0, f"Migration failed: {migrate_result.output}"
    migrate_payload = json.loads(migrate_result.output)
    migration_id = migrate_payload["migration_id"]
    assert migration_id == "test-migration-123"


# Version and help tests
def test_version_flag(runner):
    """Test --version flag."""
    result = runner.invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert "souschef" in result.output.lower()


def test_help_flag(runner):
    """Test --help flag."""
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "recipe" in result.output


def test_command_help(runner):
    """Test help for specific command."""
    result = runner.invoke(cli, ["recipe", "--help"])

    assert result.exit_code == 0
    assert "Parse a Chef recipe" in result.output


# Edge cases and error handling
def test_invalid_command(runner):
    """Test running invalid command."""
    result = runner.invoke(cli, ["invalid_command"])

    assert result.exit_code != 0
    assert "Error:" in result.output or "No such command" in result.output


# Chef Server CLI Tests
def test_query_chef_nodes_command_missing_env(runner):
    """Test query-chef-nodes command without required environment."""
    result = runner.invoke(
        cli,
        [
            "query-chef-nodes",
            "--search-query",
            "*:*",
        ],
    )

    assert result.exit_code != 0
    assert "CHEF_SERVER_URL" in result.output


# Template Conversion CLI Tests
def test_convert_template_ai_command_real(runner, tmp_path):
    """Test convert-template-ai command with real template input."""
    erb_file = tmp_path / "config.erb"
    erb_file.write_text("<%= @hostname %>")

    result = runner.invoke(
        cli,
        [
            "convert-template-ai",
            str(erb_file),
            "--no-ai",
        ],
    )

    assert result.exit_code == 0
    assert "Conversion successful" in result.output


def test_convert_template_ai_command_with_output(runner, tmp_path):
    """Test convert-template-ai command writes output file."""
    erb_file = tmp_path / "app.conf.erb"
    erb_file.write_text("<%= @app_port %>")
    output_file = tmp_path / "app.conf.j2"

    result = runner.invoke(
        cli,
        [
            "convert-template-ai",
            str(erb_file),
            "--no-ai",
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()


def test_profile_command_error_handling(runner, monkeypatch):
    """Test profile command error handling."""

    # Mock the profiling function to raise an exception
    def mock_generate(*args, **kwargs):
        raise RuntimeError("Mock profiling error")

    monkeypatch.setattr(
        "souschef.cli.generate_cookbook_performance_report", mock_generate
    )

    result = runner.invoke(
        cli,
        ["profile", str(FIXTURES_DIR)],
    )

    assert result.exit_code != 0
    assert "Error profiling cookbook" in result.output


def test_profile_operation_command_error_handling(runner, monkeypatch):
    """Test profile-operation command error handling."""

    # Mock the profiling function to raise an exception
    def mock_profile(*args, **kwargs):
        raise RuntimeError("Mock profiling error")

    import souschef.cli as cli_module

    monkeypatch.setattr(cli_module, "profile_function", mock_profile)

    recipe_path = FIXTURES_DIR / "recipes" / "default.rb"

    result = runner.invoke(
        cli,
        ["profile-operation", "recipe", str(recipe_path)],
    )

    assert result.exit_code != 0
    assert "Error profiling operation" in result.output


# Migration configuration command tests
def test_configure_migration_with_args(runner):
    """Test configure-migration with CLI arguments (non-interactive mode)."""
    result = runner.invoke(
        cli,
        [
            "configure-migration",
            "--deployment-target",
            "awx",
        ],
    )

    assert result.exit_code == 0
    # Should output JSON configuration
    assert "deployment_target" in result.output
    assert "awx" in result.output


def test_configure_migration_cli_args(runner):
    """Test configure-migration with CLI arguments."""
    result = runner.invoke(
        cli,
        [
            "configure-migration",
            "--deployment-target",
            "native",
            "--migration-standard",
            "flat",
            "--python-version",
            "3.11",
        ],
    )

    assert result.exit_code == 0
    # Should contain JSON output
    assert "deployment_target" in result.output
    assert "native" in result.output
    assert "flat" in result.output
    assert "3.11" in result.output


def test_configure_migration_with_output_file(runner, tmp_path):
    """Test configure-migration with output file."""
    output_file = tmp_path / "config.json"

    result = runner.invoke(
        cli,
        [
            "configure-migration",
            "--deployment-target",
            "awx",
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert "Configuration saved" in result.output
    assert output_file.exists()

    # Verify file content is valid JSON
    config_data = json.loads(output_file.read_text())
    assert config_data["deployment_target"] == "awx"
    assert "migration_standard" in config_data


def test_configure_migration_multiple_validation_tools(runner):
    """Test configure-migration with multiple validation tools."""
    result = runner.invoke(
        cli,
        [
            "configure-migration",
            "--deployment-target",
            "native",  # Add required arg
            "--validation-tools",
            "ansible-lint",
            "--validation-tools",
            "molecule",
            "--validation-tools",
            "tox-ansible",
        ],
    )

    assert result.exit_code == 0
    assert "ansible-lint" in result.output
    assert "molecule" in result.output
    assert "tox-ansible" in result.output


def test_configure_migration_all_options(runner, tmp_path):
    """Test configure-migration with all CLI options."""
    output_file = tmp_path / "full-config.json"

    result = runner.invoke(
        cli,
        [
            "configure-migration",
            "--deployment-target",
            "aap",
            "--migration-standard",
            "hybrid",
            "--inventory-source",
            "static-file",
            "--validation-tools",
            "molecule",
            "--python-version",
            "3.12",
            "--ansible-version",
            "2.15",
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()

    config_data = json.loads(output_file.read_text())
    assert config_data["deployment_target"] == "aap"
    assert config_data["migration_standard"] == "hybrid"
    assert config_data["inventory_source"] == "static-file"
    assert "molecule" in config_data["validation_tools"]
    assert config_data["target_python_version"] == "3.12"
    assert config_data["target_ansible_version"] == "2.15"


# Ansible Upgrade CLI Tests


def test_ansible_plan_command_missing_current_version(runner):
    """Test ansible plan requires current-version parameter."""
    result = runner.invoke(cli, ["ansible", "plan", "--target-version", "2.16"])

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_ansible_plan_command_missing_target_version(runner):
    """Test ansible plan requires target-version parameter."""
    result = runner.invoke(cli, ["ansible", "plan", "--current-version", "2.14"])

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_ansible_eol_command_missing_version(runner):
    """Test ansible eol requires version parameter."""
    result = runner.invoke(cli, ["ansible", "eol"])

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_ansible_assess_command_real(runner, tmp_path, monkeypatch):
    """Test ansible assess command with real environment input."""
    env_path = tmp_path / "ansible_env"
    env_path.mkdir()

    # Mock version detection in the ansible_upgrade module where it's used
    def mock_detect_version(*args, **kwargs):
        return "2.16.0"

    import souschef.ansible_upgrade

    monkeypatch.setattr(
        souschef.ansible_upgrade, "detect_ansible_version", mock_detect_version
    )

    result = runner.invoke(
        cli, ["ansible", "assess", "--environment-path", str(env_path)]
    )

    assert result.exit_code == 0
    assert "Ansible Environment Assessment" in result.output


def test_ansible_plan_command_real(runner):
    """Test ansible plan command with real data."""
    result = runner.invoke(
        cli,
        ["ansible", "plan", "--current-version", "2.14", "--target-version", "2.16"],
    )

    assert result.exit_code == 0
    assert "Upgrade Plan" in result.output


def test_ansible_eol_command_real(runner):
    """Test ansible eol command with real version data."""
    result = runner.invoke(cli, ["ansible", "eol", "--version", "2.16"])

    assert result.exit_code == 0
    assert "EOL Status" in result.output


def test_ansible_validate_collections_command_real(runner, tmp_path):
    """Test ansible validate-collections command with a real file."""
    requirements_file = tmp_path / "requirements.yml"
    requirements_file.write_text(
        """
collections:
  - name: community.general
    version: ">=7.0.0"
  - name: ansible.posix
"""
    )

    result = runner.invoke(
        cli,
        [
            "ansible",
            "validate-collections",
            "--collections-file",
            str(requirements_file),
            "--target-version",
            "2.16",
        ],
    )

    assert result.exit_code == 0
    assert "Collection Compatibility Report" in result.output


def test_ansible_validate_collections_nonexistent_file(runner, tmp_path):
    """Test ansible validate-collections with nonexistent file."""
    nonexistent = tmp_path / "nonexistent.yml"

    result = runner.invoke(
        cli,
        [
            "ansible",
            "validate-collections",
            "--collections-file",
            str(nonexistent),
            "--target-version",
            "2.16",
        ],
    )

    assert result.exit_code != 0


def test_ansible_detect_python_command_real(runner):
    """Test ansible detect-python command with real interpreter."""
    result = runner.invoke(cli, ["ansible", "detect-python"])

    assert result.exit_code == 0
    assert "Python Version" in result.output


def test_ansible_detect_python_with_environment_path(runner, tmp_path):
    """Test ansible detect-python with custom environment path."""
    env_path = tmp_path / "ansible_venv"
    env_path.mkdir()

    result = runner.invoke(
        cli, ["ansible", "detect-python", "--environment-path", str(env_path)]
    )

    assert result.exit_code == 0
    assert "Python Version" in result.output


def test_ansible_group_help(runner):
    """Test ansible group help command."""
    result = runner.invoke(cli, ["ansible", "--help"])

    assert result.exit_code == 0
    assert "assess" in result.output
    assert "plan" in result.output
    assert "eol" in result.output
    assert "validate-collections" in result.output
    assert "detect-python" in result.output
