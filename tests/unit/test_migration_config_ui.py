"""Unit tests for migration configuration public API functions."""

import json

import pytest

from souschef.assessment import calculate_activity_breakdown
from souschef.migration_config import (
    DeploymentTarget,
    MigrationConfig,
    MigrationStandard,
    ValidationTool,
)


@pytest.fixture
def sample_migration_config():
    """Create a sample migration configuration."""
    return MigrationConfig(
        deployment_target=DeploymentTarget.AWX,
        migration_standard=MigrationStandard.STANDARD,
        inventory_source="hosts.ini",
        validation_tools=[ValidationTool.ANSIBLE_LINT, ValidationTool.MOLECULE],
        target_python_version="3.10",
        target_ansible_version="2.15+",
    )


def test_migration_config_export_to_json(sample_migration_config):
    """Test that migration config can be exported to valid JSON."""
    config_dict = sample_migration_config.to_dict()
    json_str = json.dumps(config_dict, indent=2)

    # Verify JSON is valid
    parsed = json.loads(json_str)
    assert parsed["deployment_target"] == "awx"
    assert parsed["target_python_version"] == "3.10"
    assert len(parsed["validation_tools"]) == 2


def test_migration_config_all_fields(sample_migration_config):
    """Test that all configuration fields are accessible."""
    assert sample_migration_config.deployment_target == DeploymentTarget.AWX
    assert sample_migration_config.migration_standard == MigrationStandard.STANDARD
    assert sample_migration_config.inventory_source == "hosts.ini"
    assert ValidationTool.ANSIBLE_LINT in sample_migration_config.validation_tools
    assert sample_migration_config.target_python_version == "3.10"
    assert sample_migration_config.target_ansible_version == "2.15+"


def test_calculate_activity_breakdown_with_valid_cookbook(tmp_path):
    """Test activity breakdown calculation with a valid cookbook."""
    # Create a minimal cookbook structure
    cookbook_dir = tmp_path / "test_cookbook"
    cookbook_dir.mkdir()

    # Create metadata.rb
    metadata_file = cookbook_dir / "metadata.rb"
    metadata_file.write_text("""name 'test_cookbook'
version '1.0.0'
maintainer 'Test'
""")

    # Create a recipes directory with a recipe
    recipes_dir = cookbook_dir / "recipes"
    recipes_dir.mkdir()
    recipe_file = recipes_dir / "default.rb"
    recipe_file.write_text("""package 'nginx' do
  action :install
end
""")

    # Call the function
    result = calculate_activity_breakdown(
        str(cookbook_dir), {"deployment_target": "awx"}, "phased"
    )

    # Verify structure
    assert "summary" in result
    assert "activities" in result
    assert "total_manual_hours" in result["summary"]
    assert "total_ai_assisted_hours" in result["summary"]

    if result["activities"]:
        activity = result["activities"][0]
        assert "count" in activity
        assert "description" in activity


def test_calculate_activity_breakdown_with_invalid_path():
    """Test activity breakdown with invalid cookbook path."""
    result = calculate_activity_breakdown(
        "/nonexistent/path", {"deployment_target": "awx"}, "phased"
    )

    # Should return error
    assert "error" in result


def test_migration_config_json_structure():
    """Test that exported JSON has all required fields."""
    config = MigrationConfig(
        deployment_target=DeploymentTarget.NATIVE,
        migration_standard=MigrationStandard.FLAT,
        inventory_source="inventory.yml",
        validation_tools=[ValidationTool.ANSIBLE_LINT],
        target_python_version="3.11",
        target_ansible_version="2.16+",
    )

    config_dict = config.to_dict()

    # Verify all fields present
    assert "deployment_target" in config_dict
    assert "migration_standard" in config_dict
    assert "inventory_source" in config_dict
    assert "validation_tools" in config_dict
    assert "target_python_version" in config_dict
    assert "target_ansible_version" in config_dict

    assert config_dict["deployment_target"] == "native"
    assert config_dict["migration_standard"] == "flat"
    assert isinstance(config_dict["validation_tools"], list)
