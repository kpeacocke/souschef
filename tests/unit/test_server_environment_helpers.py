"""Tests for Chef environment helper functions in server module."""

from pathlib import Path
from unittest.mock import patch

from souschef.server import (
    _analyse_environments_structure,
    _build_conversion_summary,
    _convert_ruby_literal,
    _find_environment_patterns_in_content,
    _flatten_environment_vars,
    _generate_complete_inventory_from_environments,
    _generate_ini_inventory,
    _generate_inventory_group_from_environment,
    _generate_yaml_inventory,
    _parse_chef_environment_content,
    parse_ruby_hash,
)


def test_convert_ruby_literal_values() -> None:
    """Convert Ruby literal values to Python types."""
    assert _convert_ruby_literal("true") is True
    assert _convert_ruby_literal("false") is False
    assert _convert_ruby_literal("nil") is None
    assert _convert_ruby_literal("42") == 42
    assert _convert_ruby_literal("3.14") == 3.14
    assert _convert_ruby_literal("1e3") == 1000.0
    assert _convert_ruby_literal("string") == "string"


def test_parse_ruby_hash_nested() -> None:
    """Parse Ruby hash with nested values."""
    content = "'a' => '1', 'b' => { 'c' => '2' }, 'd' => 3"
    parsed = parse_ruby_hash(content)

    assert parsed["a"] == "1"
    assert parsed["b"]["c"] == "2"
    assert parsed["d"] == 3


def test_parse_chef_environment_content() -> None:
    """Parse Chef environment content into structured data."""
    content = """
    name 'prod'
    description 'Production environment'
    default_attributes({ 'port' => 80 })
    override_attributes({ 'debug' => true })
    cookbook 'nginx', '~> 1.2'
    """
    env_data = _parse_chef_environment_content(content)

    assert env_data["name"] == "prod"
    assert env_data["description"] == "Production environment"
    assert isinstance(env_data["default_attributes"], dict)
    assert isinstance(env_data["override_attributes"], dict)
    assert env_data["cookbook_versions"].get("nginx") == "~> 1.2"


def test_generate_inventory_group_from_environment() -> None:
    """Generate group vars with constraints and overrides."""
    env_data = {
        "description": "Production",
        "default_attributes": {"app": {"port": 80}},
        "override_attributes": {"app": {"debug": True}},
        "cookbook_versions": {"nginx": "~> 1.2"},
    }
    output = _generate_inventory_group_from_environment(env_data, "prod", True)

    assert "environment_name" in output
    assert "environment_description" in output
    assert "cookbook_version_constraints" in output
    assert "environment_overrides" in output


def test_generate_inventory_group_without_constraints() -> None:
    """Skip cookbook constraints when requested."""
    env_data = {
        "description": "Prod",
        "default_attributes": {"app": {"port": 80}},
        "cookbook_versions": {"nginx": "~> 1.2"},
    }
    output = _generate_inventory_group_from_environment(env_data, "prod", False)

    assert "cookbook_version_constraints" not in output


def test_build_conversion_summary() -> None:
    """Summary includes success and error counts."""
    results = [
        {
            "status": "success",
            "environment": "prod",
            "attributes": 1,
            "overrides": 0,
            "constraints": 1,
        },
        {"status": "error", "environment": "dev", "error": "boom"},
    ]

    summary = _build_conversion_summary(results)

    assert "Total environments processed" in summary
    assert "Successfully converted" in summary
    assert "Failed conversions" in summary
    assert "prod" in summary
    assert "dev" in summary


def test_generate_yaml_and_ini_inventory() -> None:
    """Generate YAML and INI inventory output."""
    envs = {"prod": {"name": "prod", "default_attributes": {"app": 1}}}

    yaml_out = _generate_yaml_inventory(envs)
    ini_out = _generate_ini_inventory(envs)

    assert "YAML Inventory Structure" in yaml_out
    assert "INI Inventory Structure" in ini_out
    assert "[prod]" in ini_out


def test_generate_complete_inventory_from_environments() -> None:
    """Complete inventory output includes summary and guidance."""
    envs = {"prod": {"name": "prod", "default_attributes": {"app": 1}}}
    results = [
        {
            "status": "success",
            "environment": "prod",
            "attributes": 1,
            "overrides": 0,
            "constraints": 0,
        }
    ]

    output = _generate_complete_inventory_from_environments(envs, results, "both")

    assert "Processing Summary" in output
    assert "YAML Inventory Structure" in output
    assert "INI Inventory Structure" in output
    assert "Next Steps" in output


def test_flatten_environment_vars() -> None:
    """Flatten environment variables into inventory vars."""
    env_data = {
        "name": "prod",
        "description": "Production",
        "default_attributes": {"app": {"port": 80}},
        "override_attributes": {"app": {"debug": True}},
        "cookbook_versions": {"nginx": "~> 1.2"},
    }

    flattened = _flatten_environment_vars(env_data)

    assert flattened["environment_name"] == "prod"
    assert flattened["environment_description"] == "Production"
    assert flattened["environment_overrides"]["app"]["debug"] is True
    assert flattened["cookbook_version_constraints"]["nginx"] == "~> 1.2"


def test_find_environment_patterns_in_content() -> None:
    """Detect environment patterns in Ruby content."""
    content = """
    node.chef_environment
    node['environment']
    environment 'prod'
    if node.chef_environment == 'prod'
      log 'prod'
    end
    case node.chef_environment
    when 'prod'
    end
    search(:node, 'environment:prod')
    """

    patterns = _find_environment_patterns_in_content(content, "recipe.rb")

    assert len(patterns) >= 5
    types = [pattern.get("type") for pattern in patterns]
    assert "node.chef_environment" in types
    assert "environment declaration" in types


def test_analyse_environments_structure(tmp_path: Path) -> None:
    """Analyse environments structure with one environment file."""
    env_dir = tmp_path / "environments"
    env_dir.mkdir()
    env_file = env_dir / "prod.rb"
    env_file.write_text("name 'prod'\n")

    structure = _analyse_environments_structure(env_dir)

    assert structure["total_environments"] == 1
    assert "prod" in structure["environments"]


def test_analyse_environments_structure_read_error(tmp_path: Path) -> None:
    """Handle read errors when analysing environments structure."""
    env_dir = tmp_path / "environments"
    env_dir.mkdir()
    env_file = env_dir / "prod.rb"
    env_file.write_text("name 'prod'\n")

    with patch("souschef.server.safe_read_text", side_effect=OSError("read failed")):
        structure = _analyse_environments_structure(env_dir)

    assert "error" in structure["environments"]["prod"]
