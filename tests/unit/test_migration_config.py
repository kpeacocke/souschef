"""Tests for migration_config module."""

import json

from souschef.migration_config import (
    DeploymentTarget,
    MigrationConfig,
    MigrationStandard,
    ValidationTool,
)


class TestMigrationConfig:
    """Test MigrationConfig dataclass."""

    def test_default_config(self):
        """Test default migration configuration."""
        config = MigrationConfig()

        # Check defaults
        assert config.deployment_target == DeploymentTarget.AWX
        assert config.migration_standard == MigrationStandard.STANDARD
        assert config.inventory_source == "chef-server"
        assert config.validate_post_migration is True
        assert config.validation_tools == [
            ValidationTool.ANSIBLE_LINT,
            ValidationTool.MOLECULE,
        ]
        assert config.iterate_until_clean is True
        assert config.target_python_version == "3.9"
        assert config.target_ansible_version == "2.13"
        assert config.preserve_handlers is True
        assert config.preserve_node_attributes is True
        assert config.convert_templates_to_jinja2 is True
        assert config.generate_pre_checks is True
        assert config.generate_post_checks is True
        assert config.documentation_level == "comprehensive"
        assert config.custom_settings == {}

    def test_custom_config(self):
        """Test creating custom configuration."""
        config = MigrationConfig(
            deployment_target=DeploymentTarget.NATIVE,
            migration_standard=MigrationStandard.FLAT,
            inventory_source="static-file",
            validate_post_migration=False,
            validation_tools=[ValidationTool.TOX_ANSIBLE],
            target_python_version="3.10",
            preserve_handlers=False,
            documentation_level="minimal",
        )

        assert config.deployment_target == DeploymentTarget.NATIVE
        assert config.migration_standard == MigrationStandard.FLAT
        assert config.inventory_source == "static-file"
        assert config.validate_post_migration is False
        assert config.validation_tools == [ValidationTool.TOX_ANSIBLE]
        assert config.target_python_version == "3.10"
        assert config.preserve_handlers is False
        assert config.documentation_level == "minimal"

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = MigrationConfig(
            deployment_target=DeploymentTarget.AAP,
            validation_tools=[ValidationTool.MOLECULE, ValidationTool.ANSIBLE_LINT],
        )

        result = config.to_dict()

        assert isinstance(result, dict)
        assert result["deployment_target"] == "aap"
        assert result["migration_standard"] == "standard"
        assert result["validation_tools"] == ["molecule", "ansible-lint"]
        assert result["inventory_source"] == "chef-server"

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "deployment_target": "native",
            "migration_standard": "hybrid",
            "inventory_source": "chef-server",
            "validate_post_migration": True,
            "validation_tools": ["tox-ansible", "molecule"],
            "iterate_until_clean": False,
            "target_python_version": "3.11",
            "target_ansible_version": "2.14",
            "preserve_handlers": True,
            "preserve_node_attributes": False,
            "convert_templates_to_jinja2": True,
            "generate_pre_checks": False,
            "generate_post_checks": True,
            "documentation_level": "standard",
            "custom_settings": {"key": "value"},
        }

        config = MigrationConfig.from_dict(data)

        assert config.deployment_target == DeploymentTarget.NATIVE
        assert config.migration_standard == MigrationStandard.HYBRID
        assert config.validation_tools == [
            ValidationTool.TOX_ANSIBLE,
            ValidationTool.MOLECULE,
        ]
        assert config.target_python_version == "3.11"
        assert config.preserve_node_attributes is False
        assert config.iterate_until_clean is False

    def test_roundtrip_serialization(self):
        """Test that config can be serialized and deserialized."""
        original = MigrationConfig(
            deployment_target=DeploymentTarget.APP,
            migration_standard=MigrationStandard.FLAT,
            validation_tools=[ValidationTool.CUSTOM],
            target_python_version="3.12",
            documentation_level="minimal",
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = MigrationConfig.from_dict(data)

        assert restored.deployment_target == original.deployment_target
        assert restored.migration_standard == original.migration_standard
        assert restored.validation_tools == original.validation_tools
        assert restored.target_python_version == original.target_python_version
        assert restored.documentation_level == original.documentation_level

    def test_json_serialization(self):
        """Test JSON serialization."""
        config = MigrationConfig(
            deployment_target=DeploymentTarget.AWX,
            validation_tools=[ValidationTool.ANSIBLE_LINT],
        )

        # Convert to JSON string
        json_str = json.dumps(config.to_dict())

        # Parse back
        data = json.loads(json_str)
        restored = MigrationConfig.from_dict(data)

        assert restored.deployment_target == config.deployment_target
        assert restored.validation_tools == config.validation_tools


class TestEnumerations:
    """Test enum classes."""

    def test_deployment_target_values(self):
        """Test DeploymentTarget enum values."""
        assert DeploymentTarget.APP.value == "app"
        assert DeploymentTarget.AWX.value == "awx"
        assert DeploymentTarget.AAP.value == "aap"
        assert DeploymentTarget.NATIVE.value == "native"

    def test_migration_standard_values(self):
        """Test MigrationStandard enum values."""
        assert MigrationStandard.STANDARD.value == "standard"
        assert MigrationStandard.FLAT.value == "flat"
        assert MigrationStandard.HYBRID.value == "hybrid"

    def test_validation_tool_values(self):
        """Test ValidationTool enum values."""
        assert ValidationTool.TOX_ANSIBLE.value == "tox-ansible"
        assert ValidationTool.MOLECULE.value == "molecule"
        assert ValidationTool.ANSIBLE_LINT.value == "ansible-lint"
        assert ValidationTool.CUSTOM.value == "custom"
