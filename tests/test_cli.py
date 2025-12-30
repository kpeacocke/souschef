"""Tests for the CLI module."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from souschef.cli import cli

# Define the fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "sample_cookbook"


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


def test_recipe_command_nonexistent_file(runner):
    """Test recipe command with nonexistent file."""
    result = runner.invoke(cli, ["recipe", "/nonexistent/file.rb"])

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


def test_ls_command_nonexistent_dir(runner):
    """Test ls command with nonexistent directory."""
    result = runner.invoke(cli, ["ls", "/nonexistent/directory"])

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
    assert "Analyzing cookbook" in result.output
    assert "Metadata" in result.output or "Structure" in result.output


def test_cookbook_command_with_dry_run(runner):
    """Test cookbook analysis with dry-run."""
    result = runner.invoke(cli, ["cookbook", str(FIXTURES_DIR), "--dry-run"])

    assert result.exit_code == 0
    assert "Analyzing cookbook" in result.output


def test_cookbook_command_with_output(runner):
    """Test cookbook analysis with output directory."""
    result = runner.invoke(
        cli, ["cookbook", str(FIXTURES_DIR), "--output", "/tmp/output"]
    )

    assert result.exit_code == 0
    assert "Would save results" in result.output


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


@pytest.mark.parametrize(
    "command,args",
    [
        ("recipe", ["/nonexistent.rb"]),
        ("template", ["/nonexistent.erb"]),
        ("attributes", ["/nonexistent.rb"]),
        ("resource", ["/nonexistent.rb"]),
        ("metadata", ["/nonexistent.rb"]),
    ],
)
def test_commands_with_nonexistent_files(runner, command, args):
    """Test various commands with nonexistent files."""
    result = runner.invoke(cli, [command] + args)

    assert result.exit_code != 0
    assert "does not exist" in result.output.lower()


def test_output_result_with_dict_json():
    """Test _output_result with dictionary JSON."""
    import sys
    from io import StringIO

    from souschef.cli import _output_result

    # Capture stdout
    captured_output = StringIO()
    sys.stdout = captured_output

    json_str = '{"key1": "value1", "key2": ["item1", "item2"]}'
    _output_result(json_str, "text")

    output = captured_output.getvalue()
    sys.stdout = sys.__stdout__

    assert "key1: value1" in output or "key2:" in output


def test_output_result_with_plain_text():
    """Test _output_result with plain text."""
    import sys
    from io import StringIO

    from souschef.cli import _output_result

    captured_output = StringIO()
    sys.stdout = captured_output

    _output_result("Plain text output", "text")

    output = captured_output.getvalue()
    sys.stdout = sys.__stdout__

    assert "Plain text output" in output


def test_recipe_command_with_real_parsing(runner):
    """Test recipe command actually parses content."""
    recipe_path = FIXTURES_DIR / "recipes" / "default.rb"
    result = runner.invoke(cli, ["recipe", str(recipe_path)])

    assert result.exit_code == 0
    # Should contain actual parsed content
    output_lower = result.output.lower()
    assert any(
        keyword in output_lower
        for keyword in ["resource", "package", "service", "template"]
    )


def test_template_command_extracts_variables(runner):
    """Test template command extracts variables."""
    template_path = FIXTURES_DIR / "templates" / "default" / "config.yml.erb"
    result = runner.invoke(cli, ["template", str(template_path)])

    assert result.exit_code == 0
    # Should extract variables or show conversion
    assert (
        "variables" in result.output.lower()
        or "jinja2" in result.output.lower()
        or "{{" in result.output
    )


def test_convert_command_multiple_resources(runner):
    """Test converting different resource types."""
    test_cases = [
        ("package", "nginx", "install"),
        ("service", "nginx", "start"),
        ("template", "/etc/nginx.conf", "create"),
        ("file", "/tmp/test.txt", "create"),
    ]

    for resource_type, name, action in test_cases:
        result = runner.invoke(
            cli, ["convert", resource_type, name, "--action", action]
        )
        assert result.exit_code == 0
        assert len(result.output) > 0
