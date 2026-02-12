"""Comprehensive tests for migration_config.py module to achieve 100% coverage."""

from unittest.mock import patch

import pytest

from souschef.migration_config import (
    DeploymentTarget,
    MigrationConfig,
    MigrationQuestionnaire,
    MigrationStandard,
    ValidationTool,
    get_migration_config_from_cli_args,
    get_migration_config_from_user,
)


class TestDeploymentTargetEnum:
    """Test DeploymentTarget enumeration."""

    def test_deployment_targets(self) -> None:
        """Test all deployment target values."""
        assert DeploymentTarget.APP.value == "app"
        assert DeploymentTarget.AWX.value == "awx"
        assert DeploymentTarget.AAP.value == "aap"
        assert DeploymentTarget.NATIVE.value == "native"

    def test_deployment_target_from_value(self) -> None:
        """Test creating from value."""
        assert DeploymentTarget("awx") == DeploymentTarget.AWX
        assert DeploymentTarget("app") == DeploymentTarget.APP

    def test_deployment_target_invalid(self) -> None:
        """Test invalid deployment target."""
        with pytest.raises(ValueError):
            DeploymentTarget("invalid")  # type: ignore[arg-type]


class TestMigrationStandardEnum:
    """Test MigrationStandard enumeration."""

    def test_migration_standards(self) -> None:
        """Test all migration standards."""
        assert MigrationStandard.STANDARD.value == "standard"
        assert MigrationStandard.FLAT.value == "flat"
        assert MigrationStandard.HYBRID.value == "hybrid"

    def test_migration_standard_from_value(self) -> None:
        """Test creating from value."""
        assert MigrationStandard("flat") == MigrationStandard.FLAT
        assert MigrationStandard("hybrid") == MigrationStandard.HYBRID


class TestValidationToolEnum:
    """Test ValidationTool enumeration."""

    def test_validation_tools(self) -> None:
        """Test all validation tools."""
        assert ValidationTool.TOX_ANSIBLE.value == "tox-ansible"
        assert ValidationTool.MOLECULE.value == "molecule"
        assert ValidationTool.ANSIBLE_LINT.value == "ansible-lint"
        assert ValidationTool.CUSTOM.value == "custom"

    def test_validation_tool_from_value(self) -> None:
        """Test creating from value."""
        assert ValidationTool("molecule") == ValidationTool.MOLECULE
        assert ValidationTool("custom") == ValidationTool.CUSTOM


class TestMigrationConfig:
    """Test MigrationConfig dataclass."""

    def test_migration_config_default(self) -> None:
        """Test default configuration."""
        config = MigrationConfig()
        assert config.deployment_target == DeploymentTarget.AWX
        assert config.migration_standard == MigrationStandard.STANDARD
        assert config.inventory_source == "chef-server"
        assert config.validate_post_migration is True
        assert ValidationTool.ANSIBLE_LINT in config.validation_tools
        assert ValidationTool.MOLECULE in config.validation_tools
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

    def test_migration_config_custom(self) -> None:
        """Test custom configuration."""
        config = MigrationConfig(
            deployment_target=DeploymentTarget.NATIVE,
            migration_standard=MigrationStandard.FLAT,
            inventory_source="custom-source",
            validate_post_migration=False,
            validation_tools=[ValidationTool.CUSTOM],
            target_python_version="3.11",
            target_ansible_version="2.15",
            documentation_level="minimal",
        )
        assert config.deployment_target == DeploymentTarget.NATIVE
        assert config.migration_standard == MigrationStandard.FLAT
        assert config.inventory_source == "custom-source"
        assert config.validate_post_migration is False
        assert config.validation_tools == [ValidationTool.CUSTOM]
        assert config.target_python_version == "3.11"
        assert config.target_ansible_version == "2.15"
        assert config.documentation_level == "minimal"

    def test_config_to_dict(self) -> None:
        """Test converting config to dictionary."""
        config = MigrationConfig(
            deployment_target=DeploymentTarget.APP,
            migration_standard=MigrationStandard.HYBRID,
        )
        data = config.to_dict()

        assert isinstance(data, dict)
        assert data["deployment_target"] == "app"
        assert data["migration_standard"] == "hybrid"
        assert all(isinstance(tool, str) for tool in data["validation_tools"])
        assert "ansible-lint" in data["validation_tools"]
        assert data["inventory_source"] == "chef-server"

    def test_config_from_dict_with_enums(self) -> None:
        """Test creating config from dict with string enum values."""
        data = {
            "deployment_target": "aap",
            "migration_standard": "flat",
            "inventory_source": "my-source",
            "validation_tools": ["molecule", "tox-ansible"],
            "target_python_version": "3.10",
            "iterate_until_clean": False,
            "custom_settings": {"key": "value"},
        }
        config = MigrationConfig.from_dict(data)

        assert config.deployment_target == DeploymentTarget.AAP
        assert config.migration_standard == MigrationStandard.FLAT
        assert config.inventory_source == "my-source"
        assert ValidationTool.MOLECULE in config.validation_tools
        assert ValidationTool.TOX_ANSIBLE in config.validation_tools
        assert config.target_python_version == "3.10"
        assert config.iterate_until_clean is False
        assert config.custom_settings == {"key": "value"}

    def test_config_from_dict_with_enum_objects(self) -> None:
        """Test creating config from dict with enum objects."""
        data = {
            "deployment_target": DeploymentTarget.NATIVE,
            "validation_tools": [ValidationTool.CUSTOM, ValidationTool.ANSIBLE_LINT],
        }
        config = MigrationConfig.from_dict(data)

        assert config.deployment_target == DeploymentTarget.NATIVE
        assert ValidationTool.CUSTOM in config.validation_tools
        assert ValidationTool.ANSIBLE_LINT in config.validation_tools

    def test_config_roundtrip(self) -> None:
        """Test converting config to dict and back."""
        original = MigrationConfig(
            deployment_target=DeploymentTarget.AAP,
            migration_standard=MigrationStandard.HYBRID,
            target_python_version="3.12",
            documentation_level="standard",
            custom_settings={"env": "production"},
        )

        data = original.to_dict()
        restored = MigrationConfig.from_dict(data)

        assert restored.deployment_target == original.deployment_target
        assert restored.migration_standard == original.migration_standard
        assert restored.target_python_version == original.target_python_version
        assert restored.documentation_level == original.documentation_level
        assert restored.custom_settings == original.custom_settings


class TestMigrationQuestionnaire:
    """Test MigrationQuestionnaire class."""

    def test_questionnaire_initialization(self) -> None:
        """Test questionnaire initialization."""
        questionnaire = MigrationQuestionnaire()
        assert questionnaire.config is not None
        assert questionnaire.config.deployment_target == DeploymentTarget.AWX

    @patch("builtins.input", return_value="1")
    def test_ask_deployment_target(self, mock_input) -> None:
        """Test asking about deployment target."""
        questionnaire = MigrationQuestionnaire()

        with patch("souschef.migration_config.click.echo"):
            questionnaire.ask_deployment_target()

        # Verify config was updated based on input
        assert questionnaire.config.deployment_target == DeploymentTarget.APP

    @patch("builtins.input", return_value="3")
    def test_ask_migration_strategy(self, mock_input) -> None:
        """Test asking about migration strategy."""
        questionnaire = MigrationQuestionnaire()

        with patch("souschef.migration_config.click.echo"):
            questionnaire.ask_migration_strategy()

        assert questionnaire.config.migration_standard == MigrationStandard.HYBRID

    @patch("builtins.input", return_value="2")
    def test_ask_inventory_source(self, mock_input) -> None:
        """Test asking about inventory source."""
        questionnaire = MigrationQuestionnaire()

        with patch("souschef.migration_config.click.echo"):
            questionnaire.ask_inventory_source()

        assert questionnaire.config.inventory_source == "manual"

    @patch("builtins.input", side_effect=["n", "", ""])
    def test_ask_validation_strategy_disabled(self, mock_input) -> None:
        """Test validation strategy when disabled."""
        questionnaire = MigrationQuestionnaire()

        with patch("souschef.migration_config.click.echo"):
            questionnaire.ask_validation_strategy()

        assert questionnaire.config.validate_post_migration is False

    @patch("builtins.input", side_effect=["y", "1,3", "y"])
    def test_ask_validation_strategy_enabled(self, mock_input) -> None:
        """Test validation strategy when enabled."""
        questionnaire = MigrationQuestionnaire()

        with patch("souschef.migration_config.click.echo"):
            questionnaire.ask_validation_strategy()

        assert questionnaire.config.validate_post_migration is True
        assert ValidationTool.ANSIBLE_LINT in questionnaire.config.validation_tools
        assert ValidationTool.TOX_ANSIBLE in questionnaire.config.validation_tools
        assert questionnaire.config.iterate_until_clean is True

    @patch("builtins.input", side_effect=["3.11", "2.14"])
    def test_ask_python_ansible_versions(self, mock_input) -> None:
        """Test asking about Python and Ansible versions."""
        questionnaire = MigrationQuestionnaire()

        with patch("souschef.migration_config.click.echo"):
            questionnaire.ask_python_ansible_versions()

        assert questionnaire.config.target_python_version == "3.11"
        assert questionnaire.config.target_ansible_version == "2.14"

    @patch("builtins.input", side_effect=["n", "n", "n"])
    def test_ask_preservation_options(self, mock_input) -> None:
        """Test asking about preservation options."""
        questionnaire = MigrationQuestionnaire()

        with patch("souschef.migration_config.click.echo"):
            questionnaire.ask_preservation_options()

        assert questionnaire.config.preserve_handlers is False
        assert questionnaire.config.preserve_node_attributes is False
        assert questionnaire.config.convert_templates_to_jinja2 is False

    @patch("builtins.input", side_effect=["n", "n", "1"])
    def test_ask_checks_and_documentation(self, mock_input) -> None:
        """Test asking about checks and documentation."""
        questionnaire = MigrationQuestionnaire()

        with patch("souschef.migration_config.click.echo"):
            questionnaire.ask_checks_and_documentation()

        assert questionnaire.config.generate_pre_checks is False
        assert questionnaire.config.generate_post_checks is False
        assert questionnaire.config.documentation_level == "minimal"

    @patch(
        "builtins.input",
        side_effect=[
            "2",
            "2",
            "1",
            "y",
            "1,2",
            "y",
            "3.10",
            "2.13",
            "y",
            "y",
            "y",
            "y",
            "y",
            "2",
        ],
    )
    def test_run_interactive(self, mock_input) -> None:
        """Test running the complete questionnaire."""
        questionnaire = MigrationQuestionnaire()

        with patch("souschef.migration_config.click.echo"):
            config = questionnaire.run_interactive()

        assert isinstance(config, MigrationConfig)
        assert config is questionnaire.config

    @patch(
        "builtins.input",
        side_effect=[
            "2",
            "2",
            "1",
            "y",
            "1,2",
            "y",
            "3.10",
            "2.13",
            "y",
            "y",
            "y",
            "y",
            "y",
            "2",
        ],
    )
    def test_print_summary(self, mock_input) -> None:
        """Test printing configuration summary."""
        questionnaire = MigrationQuestionnaire()

        with patch("souschef.migration_config.click.echo"):
            questionnaire.run_interactive()
            # _print_summary is called within run_interactive
            # If we got here without exception, summary printed successfully

        # Verify some config values were set
        assert questionnaire.config.deployment_target is not None


class TestFactoryFunctions:
    """Test factory functions for getting migration config."""

    @patch(
        "builtins.input",
        side_effect=[
            "2",
            "2",
            "1",
            "y",
            "1,2",
            "y",
            "3.9",
            "2.13",
            "y",
            "y",
            "y",
            "y",
            "y",
            "3",
        ],
    )
    def test_get_migration_config_from_user(self, mock_input) -> None:
        """Test getting config from user interaction."""
        with patch("souschef.migration_config.click.echo"):
            config = get_migration_config_from_user()

        assert isinstance(config, MigrationConfig)

    def test_get_migration_config_from_cli_args_empty(self) -> None:
        """Test getting config from empty CLI args."""
        config = get_migration_config_from_cli_args({})

        assert isinstance(config, MigrationConfig)
        # Should have defaults
        assert config.deployment_target == DeploymentTarget.AWX

    def test_get_migration_config_from_cli_args_with_target(self) -> None:
        """Test getting config with deployment target."""
        args = {"deployment_target": "app"}
        config = get_migration_config_from_cli_args(args)

        assert config.deployment_target == DeploymentTarget.APP

    def test_get_migration_config_from_cli_args_with_standard(self) -> None:
        """Test getting config with migration standard."""
        args = {"migration_standard": "flat"}
        config = get_migration_config_from_cli_args(args)

        assert config.migration_standard == MigrationStandard.FLAT

    def test_get_migration_config_from_cli_args_with_python_version(self) -> None:
        """Test getting config with Python version."""
        args = {"python_version": "3.12"}
        config = get_migration_config_from_cli_args(args)

        assert config.target_python_version == "3.12"

    def test_get_migration_config_from_cli_args_with_ansible_version(self) -> None:
        """Test getting config with Ansible version."""
        args = {"ansible_version": "2.15"}
        config = get_migration_config_from_cli_args(args)

        assert config.target_ansible_version == "2.15"

    def test_get_migration_config_from_cli_args_with_inventory(self) -> None:
        """Test getting config with inventory source."""
        args = {"inventory_source": "terraform"}
        config = get_migration_config_from_cli_args(args)

        assert config.inventory_source == "terraform"

    def test_get_migration_config_from_cli_args_with_validation(self) -> None:
        """Test getting config with validation settings."""
        args = {
            "validate": False,
            "validation_tools": ["molecule"],
        }
        config = get_migration_config_from_cli_args(args)

        assert config.validate_post_migration is False
        assert ValidationTool.MOLECULE in config.validation_tools

    def test_get_migration_config_from_cli_args_multiple(self) -> None:
        """Test getting config with multiple CLI args."""
        args = {
            "deployment_target": "aap",
            "migration_standard": "hybrid",
            "python_version": "3.11",
            "ansible_version": "2.14",
            "inventory_source": "dynamic",
        }
        config = get_migration_config_from_cli_args(args)

        assert config.deployment_target == DeploymentTarget.AAP
        assert config.migration_standard == MigrationStandard.HYBRID
        assert config.target_python_version == "3.11"
        assert config.target_ansible_version == "2.14"
        assert config.inventory_source == "dynamic"


class TestMigrationConfigEdgeCases:
    """Test edge cases and error conditions."""

    def test_config_with_empty_validation_tools(self) -> None:
        """Test config with empty validation tools list."""
        config = MigrationConfig(validation_tools=[])
        assert config.validation_tools == []
        data = config.to_dict()
        assert data["validation_tools"] == []

    def test_config_with_all_validation_tools(self) -> None:
        """Test config with all validation tools."""
        all_tools = list(ValidationTool)
        config = MigrationConfig(validation_tools=all_tools)
        assert len(config.validation_tools) == 4

    def test_config_from_dict_missing_fields(self) -> None:
        """Test creating config from dict with missing fields."""
        minimal_data = {"deployment_target": "native"}
        config = MigrationConfig.from_dict(minimal_data)

        # Should use defaults for missing fields
        assert config.deployment_target == DeploymentTarget.NATIVE
        assert config.migration_standard == MigrationStandard.STANDARD

    def test_config_complex_custom_settings(self) -> None:
        """Test config with complex custom settings."""
        complex_settings = {
            "nested": {"key": "value", "numbers": [1, 2, 3]},
            "flags": {"enabled": True, "disabled": False},
            "list": ["a", "b", "c"],
        }
        config = MigrationConfig(custom_settings=complex_settings)

        data = config.to_dict()
        restored = MigrationConfig.from_dict(data)

        assert restored.custom_settings == complex_settings

    def test_questionnaire_returns_config(self) -> None:
        """Test that questionnaire.config is accessible."""
        questionnaire = MigrationQuestionnaire()
        config = questionnaire.config

        assert isinstance(config, MigrationConfig)
        assert config is questionnaire.config
