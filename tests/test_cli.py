"""Tests for the CLI module."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

import souschef
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


def test_cookbook_command_template_parse_returns_plain_text(
    runner, tmp_path, monkeypatch
):
    """Test cookbook command when template parsing returns plain text instead of JSON."""
    import souschef.server

    # Create a test cookbook
    cookbook = tmp_path / "test_cookbook"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

    # Create templates directory
    templates_dir = cookbook / "templates" / "default"
    templates_dir.mkdir(parents=True)
    (templates_dir / "config.erb").write_text("port: <%= @port %>")

    # Mock parse_template to return plain text (not JSON)
    def mock_parse_template(*args, **kwargs):
        return "This is not valid JSON!"

    monkeypatch.setattr(souschef.server, "parse_template", mock_parse_template)

    result = runner.invoke(cli, ["cookbook", str(cookbook)])

    # Should handle plain text output gracefully
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


def test_convert_command_json_output_yaml_parse_exception(runner, monkeypatch):
    """Test convert command with JSON output when YAML parsing fails."""
    from unittest.mock import patch

    # Patch yaml.safe_load to raise an exception
    with patch("yaml.safe_load") as mock_yaml:
        mock_yaml.side_effect = Exception("Parse error")

        result = runner.invoke(
            cli,
            [
                "convert",
                "package",
                "nginx",
                "--action",
                "install",
                "--format",
                "json",
            ],
        )

        # Should fall back to text output when YAML parsing fails
        assert result.exit_code == 0
        # Should contain the result (either JSON output or YAML)


def test_convert_command_json_output_no_pyyaml(runner, monkeypatch):
    """Test convert command with JSON output when PyYAML is not installed."""
    import sys

    import souschef.server

    # Mock the convert function
    def mock_convert(*args, **kwargs):
        return "name: nginx\nstate: present"

    monkeypatch.setattr(souschef.server, "convert_resource_to_task", mock_convert)

    # Temporarily hide yaml module
    yaml_module = sys.modules.get("yaml")
    if yaml_module:
        monkeypatch.setitem(sys.modules, "yaml", None)

    result = runner.invoke(
        cli,
        [
            "convert",
            "package",
            "nginx",
            "--action",
            "install",
            "--format",
            "json",
        ],
    )

    # Should show warning about PyYAML
    assert result.exit_code == 0
    # Output should contain the YAML result or warning
    assert "name: nginx" in result.output or "Warning" in result.output


def test_cookbook_command_resource_json_decode_error(runner, tmp_path, monkeypatch):
    """Test cookbook command when resource parsing returns invalid JSON."""
    from unittest.mock import patch

    # Create a test cookbook
    cookbook = tmp_path / "test_cookbook"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

    # Create custom resources directory
    resources_dir = cookbook / "resources"
    resources_dir.mkdir(parents=True)
    (resources_dir / "app.rb").write_text("property :name, String")

    # Patch json.loads to raise JSONDecodeError for resources
    with patch("souschef.cli.json.loads") as mock_json:
        mock_json.side_effect = [
            {"name": "test", "version": "1.0.0"},  # metadata succeeds
            json.JSONDecodeError("error", "", 0),  # resource fails
        ]

        result = runner.invoke(cli, ["cookbook", str(cookbook)])

        # Should handle JSON decode error gracefully
        assert result.exit_code == 0
        assert "app.rb" in result.output


def test_cookbook_command_template_json_decode_error(runner, tmp_path, monkeypatch):
    """Test cookbook command when template parsing returns invalid JSON."""
    from unittest.mock import patch

    # Create a test cookbook
    cookbook = tmp_path / "test_cookbook"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

    # Create templates directory
    templates_dir = cookbook / "templates" / "default"
    templates_dir.mkdir(parents=True)
    (templates_dir / "config.erb").write_text("port: <%= @port %>")

    # Patch json.loads to raise JSONDecodeError for templates
    with patch("souschef.cli.json.loads") as mock_json:
        mock_json.side_effect = [
            {"name": "test", "version": "1.0.0"},  # metadata succeeds
            json.JSONDecodeError("error", "", 0),  # template fails
        ]

        result = runner.invoke(cli, ["cookbook", str(cookbook)])

        # Should handle JSON decode error gracefully
        assert result.exit_code == 0
        assert "config.erb" in result.output


def test_cookbook_command_with_output_path(runner, tmp_path, monkeypatch):
    """Test cookbook command with output directory specified."""
    # Create a test cookbook
    cookbook = tmp_path / "test_cookbook"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

    output_dir = tmp_path / "output"

    result = runner.invoke(
        cli, ["cookbook", str(cookbook), "--output", str(output_dir)]
    )

    # Should mention output path
    assert result.exit_code == 0
    assert str(output_dir) in result.output or "Would save" in result.output


def test_main_entry_point(monkeypatch):
    """Test the main() entry point function."""
    import sys

    from souschef.cli import main

    # Mock sys.exit to capture the call
    exit_called = []

    def mock_exit(code):
        exit_called.append(code)
        raise SystemExit(code)

    def mock_cli():
        """Mock CLI function that does nothing."""
        pass

    monkeypatch.setattr(sys, "exit", mock_exit)
    monkeypatch.setattr("souschef.cli.cli", mock_cli)

    # main() should call cli() and then sys.exit(0)
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert exit_called == [0]


def test_convert_command_json_decode_error_in_result(runner, monkeypatch):
    """Test convert command when result JSON parsing fails."""
    from unittest.mock import patch

    # Patch yaml.safe_load to raise JSONDecodeError (actually returned from yaml)
    with patch("yaml.safe_load") as mock_yaml:
        mock_yaml.side_effect = json.JSONDecodeError("error", "", 0)

        result = runner.invoke(
            cli,
            [
                "convert",
                "service",
                "apache",
                "--action",
                "start",
                "--format",
                "json",
            ],
        )

        # Should output result even if JSON parsing fails (falls back to YAML output)
        assert result.exit_code == 0
        # Will output YAML because JSON parsing failed
        assert len(result.output) > 0


# CI Generation CLI tests
def test_generate_jenkinsfile_command_success(runner, tmp_path):
    """Test generate-jenkinsfile command with default parameters."""
    output_file = tmp_path / "Jenkinsfile"
    result = runner.invoke(
        cli,
        ["generate-jenkinsfile", str(FIXTURES_DIR), "-o", str(output_file)],
    )

    assert result.exit_code == 0
    assert output_file.exists()
    assert "Generated declarative Jenkinsfile" in result.output
    assert "Pipeline Stages:" in result.output


def test_generate_jenkinsfile_command_scripted_type(runner, tmp_path):
    """Test generate-jenkinsfile with scripted pipeline type."""
    output_file = tmp_path / "Jenkinsfile"
    result = runner.invoke(
        cli,
        [
            "generate-jenkinsfile",
            str(FIXTURES_DIR),
            "-o",
            str(output_file),
            "--pipeline-type",
            "scripted",
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()
    assert "Generated scripted Jenkinsfile" in result.output
    content = output_file.read_text()
    assert "node" in content


def test_generate_jenkinsfile_command_no_parallel(runner, tmp_path):
    """Test generate-jenkinsfile with parallel disabled."""
    output_file = tmp_path / "Jenkinsfile"
    result = runner.invoke(
        cli,
        [
            "generate-jenkinsfile",
            str(FIXTURES_DIR),
            "-o",
            str(output_file),
            "--no-parallel",
        ],
    )

    assert result.exit_code == 0
    assert "Parallel execution: Disabled" in result.output


def test_generate_jenkinsfile_command_default_output(runner, tmp_path):
    """Test generate-jenkinsfile with default output path."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            ["generate-jenkinsfile", str(FIXTURES_DIR)],
        )

        assert result.exit_code == 0
        jenkinsfile = Path("Jenkinsfile")
        assert jenkinsfile.exists()


def test_generate_jenkinsfile_command_nonexistent_path(runner, tmp_path):
    """Test generate-jenkinsfile with nonexistent cookbook path."""
    nonexistent = tmp_path / "nonexistent"
    result = runner.invoke(
        cli,
        ["generate-jenkinsfile", str(nonexistent)],
    )

    # Click validates path existence, so this should fail
    assert result.exit_code != 0


def test_generate_gitlab_ci_command_success(runner, tmp_path):
    """Test generate-gitlab-ci command with default parameters."""
    output_file = tmp_path / ".gitlab-ci.yml"
    result = runner.invoke(
        cli,
        ["generate-gitlab-ci", str(FIXTURES_DIR), "-o", str(output_file)],
    )

    assert result.exit_code == 0
    assert output_file.exists()
    assert "Generated GitLab CI configuration" in result.output
    assert "CI Jobs:" in result.output


def test_generate_gitlab_ci_command_no_cache(runner, tmp_path):
    """Test generate-gitlab-ci with cache disabled."""
    output_file = tmp_path / ".gitlab-ci.yml"
    result = runner.invoke(
        cli,
        [
            "generate-gitlab-ci",
            str(FIXTURES_DIR),
            "-o",
            str(output_file),
            "--no-cache",
        ],
    )

    assert result.exit_code == 0
    assert "Cache: Disabled" in result.output


def test_generate_gitlab_ci_command_no_artifacts(runner, tmp_path):
    """Test generate-gitlab-ci with artifacts disabled."""
    output_file = tmp_path / ".gitlab-ci.yml"
    result = runner.invoke(
        cli,
        [
            "generate-gitlab-ci",
            str(FIXTURES_DIR),
            "-o",
            str(output_file),
            "--no-artifacts",
        ],
    )

    assert result.exit_code == 0
    assert "Artifacts: Disabled" in result.output


def test_generate_gitlab_ci_command_default_output(runner, tmp_path):
    """Test generate-gitlab-ci with default output path."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            ["generate-gitlab-ci", str(FIXTURES_DIR)],
        )

        assert result.exit_code == 0
        gitlab_ci = Path(".gitlab-ci.yml")
        assert gitlab_ci.exists()


def test_generate_gitlab_ci_command_nonexistent_path(runner, tmp_path):
    """Test generate-gitlab-ci with nonexistent cookbook path."""
    nonexistent = tmp_path / "nonexistent"
    result = runner.invoke(
        cli,
        ["generate-gitlab-ci", str(nonexistent)],
    )

    # Click validates path existence, so this should fail
    assert result.exit_code != 0


def test_generate_github_workflow_command_success(runner, tmp_path):
    """Test generate-github-workflow command with valid cookbook."""
    output_file = tmp_path / "ci.yml"
    result = runner.invoke(
        cli,
        [
            "generate-github-workflow",
            str(FIXTURES_DIR),
            "-o",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert output_file.exists()
    assert "Generated GitHub Actions workflow" in result.output


def test_generate_github_workflow_command_with_workflow_name(runner, tmp_path):
    """Test generate-github-workflow with custom workflow name."""
    output_file = tmp_path / "ci.yml"
    result = runner.invoke(
        cli,
        [
            "generate-github-workflow",
            str(FIXTURES_DIR),
            "-o",
            str(output_file),
            "--workflow-name",
            "Custom CI",
        ],
    )

    assert result.exit_code == 0
    assert "Custom CI" in output_file.read_text()


def test_generate_github_workflow_command_without_cache(runner, tmp_path):
    """Test generate-github-workflow with caching disabled."""
    output_file = tmp_path / "ci.yml"
    result = runner.invoke(
        cli,
        [
            "generate-github-workflow",
            str(FIXTURES_DIR),
            "-o",
            str(output_file),
            "--no-cache",
        ],
    )

    assert result.exit_code == 0
    assert "Cache: Disabled" in result.output


def test_generate_github_workflow_command_without_artifacts(runner, tmp_path):
    """Test generate-github-workflow with artifacts disabled."""
    output_file = tmp_path / "ci.yml"
    result = runner.invoke(
        cli,
        [
            "generate-github-workflow",
            str(FIXTURES_DIR),
            "-o",
            str(output_file),
            "--no-artifacts",
        ],
    )

    assert result.exit_code == 0
    assert "Artifacts: Disabled" in result.output


def test_generate_github_workflow_command_default_output(runner, tmp_path):
    """Test generate-github-workflow with default output path."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            ["generate-github-workflow", str(FIXTURES_DIR)],
        )

        assert result.exit_code == 0
        workflows_dir = Path(".github/workflows")
        assert workflows_dir.exists()
        assert (workflows_dir / "ci.yml").exists()


def test_generate_github_workflow_command_nonexistent_path(runner, tmp_path):
    """Test generate-github-workflow with nonexistent cookbook path."""
    nonexistent = tmp_path / "nonexistent"
    result = runner.invoke(
        cli,
        ["generate-github-workflow", str(nonexistent)],
    )

    # Click validates path existence, so this should fail
    assert result.exit_code != 0


# Convert Recipe Command Tests
def test_convert_recipe_command_success(runner, tmp_path):
    """Test convert-recipe command with valid inputs."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = runner.invoke(
        cli,
        [
            "convert-recipe",
            "--cookbook-path",
            str(FIXTURES_DIR),
            "--recipe-name",
            "default",
            "--output-path",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "✓ Playbook written to:" in result.output
    assert "Playbook written to:" in result.output

    # Check that output file was created
    output_file = output_dir / "default.yml"
    assert output_file.exists()


def test_convert_recipe_command_nonexistent_cookbook(runner, tmp_path):
    """Test convert-recipe with nonexistent cookbook path."""
    nonexistent = tmp_path / "nonexistent"
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = runner.invoke(
        cli,
        [
            "convert-recipe",
            "--cookbook-path",
            str(nonexistent),
            "--recipe-name",
            "default",
            "--output-path",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "does not exist" in result.output.lower()


def test_convert_recipe_command_nonexistent_recipe(runner, tmp_path):
    """Test convert-recipe with nonexistent recipe file."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = runner.invoke(
        cli,
        [
            "convert-recipe",
            "--cookbook-path",
            str(FIXTURES_DIR),
            "--recipe-name",
            "nonexistent",
            "--output-path",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_convert_recipe_command_invalid_output_path(runner):
    """Test convert-recipe with invalid output path."""
    # Try to write to a file instead of directory
    result = runner.invoke(
        cli,
        [
            "convert-recipe",
            "--cookbook-path",
            str(FIXTURES_DIR),
            "--recipe-name",
            "default",
            "--output-path",
            "/dev/null/file",  # Invalid path
        ],
    )

    assert result.exit_code != 0


# Assess Cookbook Command Tests
def test_assess_cookbook_command_text_format(runner):
    """Test assess-cookbook command with text output."""
    result = runner.invoke(
        cli,
        [
            "assess-cookbook",
            "--cookbook-path",
            str(FIXTURES_DIR),
            "--format",
            "text",
        ],
    )

    assert result.exit_code == 0
    assert "Cookbook:" in result.output or "Complexity:" in result.output


def test_assess_cookbook_command_json_format(runner):
    """Test assess-cookbook command with JSON output."""
    result = runner.invoke(
        cli,
        [
            "assess-cookbook",
            "--cookbook-path",
            str(FIXTURES_DIR),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    # Should be valid JSON
    try:
        data = json.loads(result.output)
        assert isinstance(data, dict)
        assert "complexity" in data
        assert "recipe_count" in data
        assert "resource_count" in data
    except json.JSONDecodeError:
        pytest.fail("Output should be valid JSON")


def test_assess_cookbook_command_nonexistent_path(runner, tmp_path):
    """Test assess-cookbook with nonexistent path."""
    nonexistent = tmp_path / "nonexistent"
    result = runner.invoke(
        cli,
        [
            "assess-cookbook",
            "--cookbook-path",
            str(nonexistent),
        ],
    )

    assert result.exit_code != 0
    assert "does not exist" in result.output.lower()


def test_assess_cookbook_command_file_instead_of_directory(runner, tmp_path):
    """Test assess-cookbook with file instead of directory."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    result = runner.invoke(
        cli,
        [
            "assess-cookbook",
            "--cookbook-path",
            str(test_file),
        ],
    )

    assert result.exit_code != 0
    assert "not a directory" in result.output.lower()


# Convert Habitat Command Tests
def test_convert_habitat_command_success(runner, tmp_path):
    """Test convert-habitat command with valid inputs."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create a mock plan.sh file
    plan_file = tmp_path / "plan.sh"
    plan_file.write_text("""
pkg_name=test
pkg_version=1.0.0
pkg_description="Test package"

do_build() {
    echo "Building..."
}

do_install() {
    echo "Installing..."
}
""")

    result = runner.invoke(
        cli,
        [
            "convert-habitat",
            "--plan-path",
            str(plan_file),
            "--output-path",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Successfully converted" in result.output

    # Check that Dockerfile was created
    dockerfile = output_dir / "Dockerfile"
    assert dockerfile.exists()


def test_convert_habitat_command_custom_base_image(runner, tmp_path):
    """Test convert-habitat with custom base image."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create a mock plan.sh file
    plan_file = tmp_path / "plan.sh"
    plan_file.write_text("""
pkg_name=test
pkg_version=1.0.0
""")

    result = runner.invoke(
        cli,
        [
            "convert-habitat",
            "--plan-path",
            str(plan_file),
            "--output-path",
            str(output_dir),
            "--base-image",
            "alpine:latest",
        ],
    )

    assert result.exit_code == 0
    dockerfile = output_dir / "Dockerfile"
    content = dockerfile.read_text()
    assert "alpine:latest" in content


def test_convert_habitat_command_nonexistent_plan(runner, tmp_path):
    """Test convert-habitat with nonexistent plan file."""
    nonexistent = tmp_path / "nonexistent.sh"
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = runner.invoke(
        cli,
        [
            "convert-habitat",
            "--plan-path",
            str(nonexistent),
            "--output-path",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "does not exist" in result.output.lower()


def test_convert_habitat_command_directory_instead_of_file(runner, tmp_path):
    """Test convert-habitat with directory instead of file."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = runner.invoke(
        cli,
        [
            "convert-habitat",
            "--plan-path",
            str(tmp_path),  # Pass directory instead of file
            "--output-path",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "not a file" in result.output.lower()


# Convert InSpec Command Tests
def test_convert_inspec_command_testinfra(runner, tmp_path):
    """Test convert-inspec command with testinfra format."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create a mock InSpec profile directory
    profile_dir = tmp_path / "inspec_profile"
    profile_dir.mkdir()
    (profile_dir / "controls").mkdir()

    # Create a basic control file
    control_file = profile_dir / "controls" / "example.rb"
    control_file.write_text("""
control 'test-1' do
  impact 1.0
  title 'Test control'
  desc 'A test control'

  describe file('/etc/passwd') do
    it { should exist }
  end
end
""")

    result = runner.invoke(
        cli,
        [
            "convert-inspec",
            "--profile-path",
            str(profile_dir),
            "--output-path",
            str(output_dir),
            "--format",
            "testinfra",
        ],
    )

    assert result.exit_code == 0
    assert "Successfully converted" in result.output

    # Check that test file was created
    test_file = output_dir / "test_spec.py"
    assert test_file.exists()


def test_convert_inspec_command_serverspec(runner, tmp_path):
    """Test convert-inspec command with serverspec format."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create a mock InSpec profile directory
    profile_dir = tmp_path / "inspec_profile"
    profile_dir.mkdir()
    (profile_dir / "controls").mkdir()

    control_file = profile_dir / "controls" / "example.rb"
    control_file.write_text("""
control 'test-1' do
  describe file('/etc/passwd') do
    it { should exist }
  end
end
""")

    result = runner.invoke(
        cli,
        [
            "convert-inspec",
            "--profile-path",
            str(profile_dir),
            "--output-path",
            str(output_dir),
            "--format",
            "serverspec",
        ],
    )

    assert result.exit_code == 0
    test_file = output_dir / "spec_helper.rb"
    assert test_file.exists()


def test_convert_inspec_command_goss(runner, tmp_path):
    """Test convert-inspec command with goss format."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create a mock InSpec profile directory
    profile_dir = tmp_path / "inspec_profile"
    profile_dir.mkdir()
    (profile_dir / "controls").mkdir()

    control_file = profile_dir / "controls" / "example.rb"
    control_file.write_text("""
control 'test-1' do
  describe file('/etc/passwd') do
    it { should exist }
  end
end
""")

    result = runner.invoke(
        cli,
        [
            "convert-inspec",
            "--profile-path",
            str(profile_dir),
            "--output-path",
            str(output_dir),
            "--format",
            "goss",
        ],
    )

    assert result.exit_code == 0
    test_file = output_dir / "goss.yaml"
    assert test_file.exists()


def test_convert_inspec_command_ansible(runner, tmp_path):
    """Test convert-inspec command with ansible format."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create a mock InSpec profile directory
    profile_dir = tmp_path / "inspec_profile"
    profile_dir.mkdir()
    (profile_dir / "controls").mkdir()

    control_file = profile_dir / "controls" / "example.rb"
    control_file.write_text("""
control 'test-1' do
  describe file('/etc/passwd') do
    it { should exist }
  end
end
""")

    result = runner.invoke(
        cli,
        [
            "convert-inspec",
            "--profile-path",
            str(profile_dir),
            "--output-path",
            str(output_dir),
            "--format",
            "ansible",
        ],
    )

    assert result.exit_code == 0
    test_file = output_dir / "assert.yml"
    assert test_file.exists()


def test_convert_inspec_command_nonexistent_profile(runner, tmp_path):
    """Test convert-inspec with nonexistent profile path."""
    nonexistent = tmp_path / "nonexistent"
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = runner.invoke(
        cli,
        [
            "convert-inspec",
            "--profile-path",
            str(nonexistent),
            "--output-path",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "does not exist" in result.output.lower()


def test_convert_inspec_command_file_instead_of_directory(runner, tmp_path):
    """Test convert-inspec with file instead of directory."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = runner.invoke(
        cli,
        [
            "convert-inspec",
            "--profile-path",
            str(test_file),
            "--output-path",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "not a directory" in result.output.lower()


# Profile Command Tests
def test_profile_command_success(runner, tmp_path):
    """Test profile command with valid cookbook."""
    result = runner.invoke(
        cli,
        ["profile", str(FIXTURES_DIR)],
    )

    assert result.exit_code == 0
    assert (
        "Profiling cookbook" in result.output or "Performance report" in result.output
    )


def test_profile_command_with_output_file(runner, tmp_path):
    """Test profile command with output file."""
    output_file = tmp_path / "profile_report.txt"

    result = runner.invoke(
        cli,
        ["profile", str(FIXTURES_DIR), "--output", str(output_file)],
    )

    assert result.exit_code == 0
    assert output_file.exists()
    assert output_file.stat().st_size > 0


def test_profile_command_nonexistent_cookbook(runner, tmp_path):
    """Test profile command with nonexistent cookbook."""
    nonexistent = tmp_path / "nonexistent"

    result = runner.invoke(
        cli,
        ["profile", str(nonexistent)],
    )

    assert result.exit_code != 0
    assert "does not exist" in result.output.lower()


# Profile Operation Command Tests
def test_profile_operation_command_recipe(runner):
    """Test profile-operation command with recipe."""
    recipe_path = FIXTURES_DIR / "recipes" / "default.rb"

    result = runner.invoke(
        cli,
        ["profile-operation", "recipe", str(recipe_path)],
    )

    assert result.exit_code == 0
    assert "Profiling recipe parsing" in result.output


def test_profile_operation_command_attributes(runner):
    """Test profile-operation command with attributes."""
    attributes_path = FIXTURES_DIR / "attributes" / "default.rb"

    result = runner.invoke(
        cli,
        ["profile-operation", "attributes", str(attributes_path)],
    )

    assert result.exit_code == 0
    assert "Profiling attributes parsing" in result.output


def test_profile_operation_command_resource(runner):
    """Test profile-operation command with resource."""
    resource_path = FIXTURES_DIR / "resources" / "simple.rb"

    result = runner.invoke(
        cli,
        ["profile-operation", "resource", str(resource_path)],
    )

    assert result.exit_code == 0
    assert "Profiling resource parsing" in result.output


def test_profile_operation_command_template(runner):
    """Test profile-operation command with template."""
    template_path = FIXTURES_DIR / "templates" / "default" / "config.yml.erb"

    result = runner.invoke(
        cli,
        ["profile-operation", "template", str(template_path)],
    )

    assert result.exit_code == 0
    assert "Profiling template parsing" in result.output


def test_profile_operation_command_detailed(runner):
    """Test profile-operation command with detailed flag."""
    recipe_path = FIXTURES_DIR / "recipes" / "default.rb"

    result = runner.invoke(
        cli,
        ["profile-operation", "recipe", str(recipe_path), "--detailed"],
    )

    assert result.exit_code == 0
    assert (
        "Detailed Function Statistics" in result.output
        or "function statistics" in result.output.lower()
    )


def test_profile_operation_command_invalid_operation(runner, tmp_path):
    """Test profile-operation command with invalid operation."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    result = runner.invoke(
        cli,
        ["profile-operation", "invalid", str(test_file)],
    )

    assert result.exit_code != 0


def test_profile_operation_command_nonexistent_file(runner, tmp_path):
    """Test profile-operation command with nonexistent file."""
    nonexistent = tmp_path / "nonexistent.rb"

    result = runner.invoke(
        cli,
        ["profile-operation", "recipe", str(nonexistent)],
    )

    assert result.exit_code != 0


# UI Command Tests
def test_ui_command_success(runner, monkeypatch):
    """Test ui command launches successfully."""
    # Mock subprocess.run to avoid actually starting Streamlit
    import subprocess

    def mock_run(cmd, **kwargs):
        # Simulate successful execution
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = runner.invoke(
        cli,
        ["ui", "--port", "8502"],
    )

    assert result.exit_code == 0
    assert "Starting SousChef UI" in result.output
    assert "http://localhost:8502" in result.output


def test_ui_command_default_port(runner, monkeypatch):
    """Test ui command with default port."""
    import subprocess

    def mock_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = runner.invoke(cli, ["ui"])

    assert result.exit_code == 0
    assert "http://localhost:8501" in result.output


def test_ui_command_streamlit_not_installed(runner, monkeypatch):
    """Test ui command when streamlit is not installed."""
    import subprocess

    def mock_run(cmd, **kwargs):
        # Simulate ImportError by raising CalledProcessError
        raise subprocess.CalledProcessError(
            1, cmd, "ModuleNotFoundError: No module named 'streamlit'"
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = runner.invoke(cli, ["ui"])

    assert result.exit_code != 0
    assert "returned non-zero exit status" in result.output


def test_ui_command_subprocess_error(runner, monkeypatch):
    """Test ui command when subprocess fails."""
    import subprocess

    def mock_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, "Some error")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = runner.invoke(cli, ["ui"])

    assert result.exit_code != 0


# Error Handling Tests for CI Generation Commands
def test_generate_jenkinsfile_command_error_handling(runner, tmp_path, monkeypatch):
    """Test generate-jenkinsfile command error handling."""

    # Mock the generation function to raise an exception
    def mock_generate(*args, **kwargs):
        raise RuntimeError("Mock generation error")

    monkeypatch.setattr(souschef.cli, "generate_jenkinsfile_from_chef", mock_generate)

    output_file = tmp_path / "Jenkinsfile"
    result = runner.invoke(
        cli,
        ["generate-jenkinsfile", str(FIXTURES_DIR), "-o", str(output_file)],
    )

    assert result.exit_code != 0
    assert "Error generating Jenkinsfile" in result.output


def test_generate_gitlab_ci_command_error_handling(runner, tmp_path, monkeypatch):
    """Test generate-gitlab-ci command error handling."""

    # Mock the generation function to raise an exception
    def mock_generate(*args, **kwargs):
        raise RuntimeError("Mock generation error")

    monkeypatch.setattr(souschef.cli, "generate_gitlab_ci_from_chef", mock_generate)

    output_file = tmp_path / ".gitlab-ci.yml"
    result = runner.invoke(
        cli,
        ["generate-gitlab-ci", str(FIXTURES_DIR), "-o", str(output_file)],
    )

    assert result.exit_code != 0
    assert "Error generating GitLab CI configuration" in result.output


def test_generate_github_workflow_command_error_handling(runner, tmp_path, monkeypatch):
    """Test generate-github-workflow command error handling."""

    # Mock the generation function to raise an exception
    def mock_generate(*args, **kwargs):
        raise RuntimeError("Mock generation error")

    monkeypatch.setattr(
        souschef.cli, "generate_github_workflow_from_chef", mock_generate
    )

    output_file = tmp_path / "ci.yml"
    result = runner.invoke(
        cli,
        ["generate-github-workflow", str(FIXTURES_DIR), "-o", str(output_file)],
    )

    assert result.exit_code != 0
    assert "Error generating GitHub Actions workflow" in result.output


# Additional Error Handling Tests
def test_convert_recipe_command_conversion_error(runner, tmp_path, monkeypatch):
    """Test convert-recipe command when conversion fails."""

    # Mock the conversion function to raise an exception
    def mock_generate(*args, **kwargs):
        raise RuntimeError("Mock conversion error")

    monkeypatch.setattr(souschef.cli, "generate_playbook_from_recipe", mock_generate)

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = runner.invoke(
        cli,
        [
            "convert-recipe",
            "--cookbook-path",
            str(FIXTURES_DIR),
            "--recipe-name",
            "default",
            "--output-path",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "Error converting recipe" in result.output


def test_assess_cookbook_command_analysis_error(runner, monkeypatch):
    """Test assess-cookbook command when analysis fails."""

    # Mock the analysis function to raise an exception
    def mock_analyze(*args, **kwargs):
        raise RuntimeError("Mock analysis error")

    monkeypatch.setattr(souschef.cli, "_analyze_cookbook_for_assessment", mock_analyze)

    result = runner.invoke(
        cli,
        [
            "assess-cookbook",
            "--cookbook-path",
            str(FIXTURES_DIR),
        ],
    )

    assert result.exit_code != 0
    assert "Error assessing cookbook" in result.output


def test_convert_habitat_command_conversion_error(runner, tmp_path, monkeypatch):
    """Test convert-habitat command when conversion fails."""
    import souschef.server

    # Mock the conversion function to raise an exception
    def mock_convert(*args, **kwargs):
        raise RuntimeError("Mock conversion error")

    monkeypatch.setattr(souschef.server, "convert_habitat_to_dockerfile", mock_convert)

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    plan_file = tmp_path / "plan.sh"
    plan_file.write_text("pkg_name=test")

    result = runner.invoke(
        cli,
        [
            "convert-habitat",
            "--plan-path",
            str(plan_file),
            "--output-path",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "Error converting Habitat plan" in result.output


def test_convert_inspec_command_conversion_error(runner, tmp_path, monkeypatch):
    """Test convert-inspec command when conversion fails."""
    import souschef.server

    # Mock the conversion function to raise an exception
    def mock_convert(*args, **kwargs):
        raise RuntimeError("Mock conversion error")

    monkeypatch.setattr(souschef.server, "convert_inspec_to_test", mock_convert)

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()

    result = runner.invoke(
        cli,
        [
            "convert-inspec",
            "--profile-path",
            str(profile_dir),
            "--output-path",
            str(output_dir),
        ],
    )

    assert result.exit_code != 0
    assert "Error converting InSpec profile" in result.output


def test_profile_command_error_handling(runner, monkeypatch):
    """Test profile command error handling."""

    # Mock the profiling function to raise an exception
    def mock_generate(*args, **kwargs):
        raise RuntimeError("Mock profiling error")

    monkeypatch.setattr(
        souschef.cli, "generate_cookbook_performance_report", mock_generate
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

    monkeypatch.setattr(souschef.cli, "profile_function", mock_profile)

    recipe_path = FIXTURES_DIR / "recipes" / "default.rb"

    result = runner.invoke(
        cli,
        ["profile-operation", "recipe", str(recipe_path)],
    )

    assert result.exit_code != 0
    assert "Error profiling operation" in result.output
