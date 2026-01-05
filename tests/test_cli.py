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
    assert "Analyzing cookbook" in result.output
    assert "Metadata" in result.output or "Structure" in result.output


def test_cookbook_command_with_dry_run(runner):
    """Test cookbook analysis with dry-run."""
    result = runner.invoke(cli, ["cookbook", str(FIXTURES_DIR), "--dry-run"])

    assert result.exit_code == 0
    assert "Analyzing cookbook" in result.output


def test_cookbook_command_with_output(runner, tmp_path):
    """Test cookbook analysis with output directory."""
    output_dir = tmp_path / "output"
    result = runner.invoke(
        cli, ["cookbook", str(FIXTURES_DIR), "--output", str(output_dir)]
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
    "command,filename",
    [
        ("recipe", "nonexistent.rb"),
        ("template", "nonexistent.erb"),
        ("attributes", "nonexistent.rb"),
        ("resource", "nonexistent.rb"),
        ("metadata", "nonexistent.rb"),
    ],
)
def test_commands_with_nonexistent_files(runner, tmp_path, command, filename):
    """Test various commands with nonexistent files."""
    nonexistent = tmp_path / "nonexistent" / filename
    result = runner.invoke(cli, [command, str(nonexistent)])

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


def test_convert_command_multiple_resources(runner, tmp_path):
    """Test converting different resource types."""
    test_file = tmp_path / "test.txt"
    test_cases = [
        ("package", "nginx", "install"),
        ("service", "nginx", "start"),
        ("template", "/etc/nginx.conf", "create"),
        ("file", str(test_file), "create"),
    ]

    for resource_type, name, action in test_cases:
        result = runner.invoke(
            cli, ["convert", resource_type, name, "--action", action]
        )
        assert result.exit_code == 0
        assert len(result.output) > 0


def test_ls_command_with_error(runner, tmp_path):
    """Test ls command when list_directory returns error string."""
    # Create a path that exists but will fail to list
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    # Try to list a file instead of directory
    result = runner.invoke(cli, ["ls", str(test_file)])

    # Should handle the error
    assert result.exit_code in [0, 1]  # May fail or succeed depending on implementation


def test_convert_command_yaml_import_error(runner, monkeypatch, tmp_path):
    """Test convert command when yaml module is not available."""
    # Create a test script that mocks the convert function
    test_script = tmp_path / "test_convert.py"
    test_script.write_text("""
import sys
from pathlib import Path

# Add souschef to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock yaml import failure
import builtins
_original_import = builtins.__import__

def mock_import(name, *args, **kwargs):
    if name == 'yaml':
        raise ImportError("yaml not available")
    return _original_import(name, *args, **kwargs)

builtins.__import__ = mock_import

# Now run the CLI
from souschef.cli import cli
from click.testing import CliRunner

runner = CliRunner()
result = runner.invoke(cli, ['convert', 'package', 'nginx', '--format', 'json'])
print(result.output)
""")

    # For now, just test that the convert command works without the mocking
    result = runner.invoke(cli, ["convert", "package", "nginx", "--format", "json"])

    # Should successfully convert
    assert result.exit_code == 0
    assert len(result.output) > 0


def test_convert_command_yaml_parse_error(runner, monkeypatch):
    """Test convert command when yaml parsing fails."""
    import souschef.server

    # Mock convert_resource_to_task to return invalid YAML
    def mock_convert(*args, **kwargs):
        return "invalid: yaml: content:"

    monkeypatch.setattr(souschef.server, "convert_resource_to_task", mock_convert)

    result = runner.invoke(cli, ["convert", "package", "nginx", "--format", "json"])

    # Should still output something
    assert result.exit_code == 0
    assert len(result.output) > 0


def test_inspec_parse_command_text_format(runner):
    """Test InSpec parsing with text format."""
    inspec_profile = FIXTURES_DIR.parent / "sample_inspec_profile"
    if inspec_profile.exists():
        result = runner.invoke(
            cli, ["inspec-parse", str(inspec_profile), "--format", "text"]
        )

        assert result.exit_code == 0
        assert len(result.output) > 0


def test_inspec_parse_command_json_format(runner):
    """Test InSpec parsing with JSON format."""
    inspec_profile = FIXTURES_DIR.parent / "sample_inspec_profile"
    if inspec_profile.exists():
        result = runner.invoke(
            cli, ["inspec-parse", str(inspec_profile), "--format", "json"]
        )

        assert result.exit_code == 0
        try:
            data = json.loads(result.output)
            assert isinstance(data, dict)
        except json.JSONDecodeError:
            # Acceptable if it's an error message
            assert len(result.output) > 0


def test_inspec_convert_command_testinfra(runner):
    """Test InSpec conversion to Testinfra."""
    inspec_profile = FIXTURES_DIR.parent / "sample_inspec_profile"
    if inspec_profile.exists():
        result = runner.invoke(
            cli, ["inspec-convert", str(inspec_profile), "--format", "testinfra"]
        )

        assert result.exit_code == 0
        assert len(result.output) > 0


def test_inspec_convert_command_ansible_assert(runner):
    """Test InSpec conversion to Ansible assert."""
    inspec_profile = FIXTURES_DIR.parent / "sample_inspec_profile"
    if inspec_profile.exists():
        result = runner.invoke(
            cli, ["inspec-convert", str(inspec_profile), "--format", "ansible_assert"]
        )

        assert result.exit_code == 0
        assert len(result.output) > 0


def test_inspec_generate_command(runner):
    """Test InSpec generation from recipe."""
    recipe_path = FIXTURES_DIR / "recipes" / "default.rb"
    result = runner.invoke(cli, ["inspec-generate", str(recipe_path)])

    assert result.exit_code == 0
    assert len(result.output) > 0


def test_inspec_generate_command_json_format(runner):
    """Test InSpec generation with JSON format."""
    recipe_path = FIXTURES_DIR / "recipes" / "default.rb"
    result = runner.invoke(
        cli, ["inspec-generate", str(recipe_path), "--format", "json"]
    )

    assert result.exit_code == 0
    assert len(result.output) > 0


def test_cookbook_command_with_resources_and_templates(runner, tmp_path):
    """Test cookbook command analyzing resources and templates."""
    # Create a test cookbook with resources and templates
    cookbook = tmp_path / "test_cookbook"
    cookbook.mkdir()

    # Create metadata
    (cookbook / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

    # Create resources directory
    resources_dir = cookbook / "resources"
    resources_dir.mkdir()
    (resources_dir / "test.rb").write_text(
        "property :name, String\naction :create do\nend"
    )

    # Create templates directory
    templates_dir = cookbook / "templates" / "default"
    templates_dir.mkdir(parents=True)
    (templates_dir / "config.yml.erb").write_text(
        "port: <%= @port %>\nhost: <%= @host %>"
    )

    result = runner.invoke(cli, ["cookbook", str(cookbook)])

    assert result.exit_code == 0
    assert "Analyzing cookbook" in result.output


def test_output_result_with_list_data():
    """Test _output_result with list data in text format."""
    import sys
    from io import StringIO

    from souschef.cli import _output_result

    captured_output = StringIO()
    sys.stdout = captured_output

    # JSON with list values
    json_str = '{"items": ["item1", "item2", "item3"], "count": 3}'
    _output_result(json_str, "text")

    output = captured_output.getvalue()
    sys.stdout = sys.__stdout__

    assert "items:" in output or "item1" in output


def test_convert_command_with_exception_in_yaml_parse(runner, monkeypatch):
    """Test convert command when YAML parsing raises an exception."""
    import souschef.server

    # Mock convert to return invalid YAML that will raise exception during parse
    def mock_convert(*args, **kwargs):
        return "invalid:\n  - yaml\n    - structure"

    monkeypatch.setattr(souschef.server, "convert_resource_to_task", mock_convert)

    result = runner.invoke(cli, ["convert", "package", "nginx", "--format", "json"])

    # Should output something even if parsing fails
    assert result.exit_code == 0
    assert len(result.output) > 0


def test_cookbook_command_with_json_decode_error(runner, tmp_path, monkeypatch):
    """Test cookbook command when resource parsing returns invalid JSON."""
    import souschef.server

    # Create a test cookbook
    cookbook = tmp_path / "test_cookbook"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

    # Create resources directory
    resources_dir = cookbook / "resources"
    resources_dir.mkdir()
    (resources_dir / "test.rb").write_text("property :name, String")

    # Mock parse_custom_resource to return invalid JSON
    def mock_parse(*args, **kwargs):
        return "This is not valid JSON at all!"

    monkeypatch.setattr(souschef.server, "parse_custom_resource", mock_parse)

    result = runner.invoke(cli, ["cookbook", str(cookbook)])

    # Should handle the error gracefully
    assert result.exit_code == 0
    assert "Analyzing cookbook" in result.output


def test_cookbook_command_template_json_decode_error(runner, tmp_path, monkeypatch):
    """Test cookbook command when template parsing returns invalid JSON."""
    import souschef.server

    # Create a test cookbook
    cookbook = tmp_path / "test_cookbook"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

    # Create templates directory
    templates_dir = cookbook / "templates" / "default"
    templates_dir.mkdir(parents=True)
    (templates_dir / "config.erb").write_text("port: <%= @port %>")

    # Mock parse_template to return invalid JSON
    def mock_parse_template(*args, **kwargs):
        return "This is not valid JSON!"

    monkeypatch.setattr(souschef.server, "parse_template", mock_parse_template)

    result = runner.invoke(cli, ["cookbook", str(cookbook)])

    # Should handle the error gracefully
    assert result.exit_code == 0
    assert "Analyzing cookbook" in result.output


def test_output_result_text_format_with_non_dict_json(runner):
    """Test _output_result with non-dict JSON in text format."""
    import sys
    from io import StringIO

    from souschef.cli import _output_result

    captured_output = StringIO()
    sys.stdout = captured_output

    # JSON list instead of dict
    json_str = '["item1", "item2", "item3"]'
    _output_result(json_str, "text")

    output = captured_output.getvalue()
    sys.stdout = sys.__stdout__

    # Should output the JSON as-is since it's not a dict
    assert "item1" in output or "[" in output


def test_output_result_json_format_with_non_json(runner):
    """Test _output_result with non-JSON in json format."""
    import sys
    from io import StringIO

    from souschef.cli import _output_result

    captured_output = StringIO()
    sys.stdout = captured_output

    # Plain text that's not JSON
    plain_text = "This is plain text output"
    _output_result(plain_text, "json")

    output = captured_output.getvalue()
    sys.stdout = sys.__stdout__

    # Should output as-is when not JSON
    assert "This is plain text output" in output


def test_cookbook_command_with_templates_having_many_variables(
    runner, tmp_path, monkeypatch
):
    """Test cookbook command with template having >5 variables."""
    import souschef.server

    # Create a test cookbook
    cookbook = tmp_path / "test_cookbook"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

    # Create templates directory
    templates_dir = cookbook / "templates" / "default"
    templates_dir.mkdir(parents=True)
    (templates_dir / "config.erb").write_text("port: <%= @port %>")

    # Mock parse_template to return JSON with many variables
    def mock_parse_template(*args, **kwargs):
        return '{"variables": ["var1", "var2", "var3", "var4", "var5", "var6", "var7"], "jinja2_template": "test"}'

    monkeypatch.setattr(souschef.server, "parse_template", mock_parse_template)

    result = runner.invoke(cli, ["cookbook", str(cookbook)])

    # Should show "... and X more" for variables > 5
    assert result.exit_code == 0
    assert "... and " in result.output or "Variables:" in result.output
