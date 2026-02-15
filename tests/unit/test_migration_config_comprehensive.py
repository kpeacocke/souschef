"""Comprehensive unit tests for migration configuration module."""

from unittest.mock import patch

from souschef.migration_config import (
    DeploymentTarget,
    MigrationConfig,
    MigrationQuestionnaire,
    MigrationStandard,
    ValidationTool,
    get_migration_config_from_cli_args,
    get_migration_config_from_user,
)


class TestMigrationConfigFromDict:
    """Tests for MigrationConfig.from_dict() method."""

    def test_from_dict_with_string_enums(self):
        """Test creating config from dictionary with string enum values."""
        data = {
            "deployment_target": "aap",
            "migration_standard": "hybrid",
            "validation_tools": ["tox-ansible", "molecule"],
            "inventory_source": "manual",
            "target_python_version": "3.11",
        }
        config = MigrationConfig.from_dict(data)

        assert config.deployment_target == DeploymentTarget.AAP
        assert config.migration_standard == MigrationStandard.HYBRID
        assert ValidationTool.TOX_ANSIBLE in config.validation_tools
        assert ValidationTool.MOLECULE in config.validation_tools
        assert config.inventory_source == "manual"

    def test_from_dict_with_enum_objects(self):
        """Test creating config from dictionary with enum objects already."""
        data = {
            "deployment_target": DeploymentTarget.NATIVE,
            "migration_standard": MigrationStandard.FLAT,
            "validation_tools": [ValidationTool.ANSIBLE_LINT],
        }
        config = MigrationConfig.from_dict(data)

        assert config.deployment_target == DeploymentTarget.NATIVE
        assert config.migration_standard == MigrationStandard.FLAT
        assert config.validation_tools == [ValidationTool.ANSIBLE_LINT]

    def test_from_dict_with_mixed_validation_tools(self):
        """Test from_dict with mixed string and enum validation tools."""
        data = {
            "validation_tools": ["ansible-lint", ValidationTool.MOLECULE, "custom"],
        }
        config = MigrationConfig.from_dict(data)

        assert ValidationTool.ANSIBLE_LINT in config.validation_tools
        assert ValidationTool.MOLECULE in config.validation_tools
        assert ValidationTool.CUSTOM in config.validation_tools

    def test_from_dict_with_all_custom_settings(self):
        """Test from_dict preserves custom settings dictionary."""
        data = {
            "deployment_target": "awx",
            "custom_settings": {
                "custom_key": "value",
                "enable_feature": True,
                "count": 42,
            },
        }
        config = MigrationConfig.from_dict(data)

        assert config.custom_settings["custom_key"] == "value"
        assert config.custom_settings["enable_feature"] is True
        assert config.custom_settings["count"] == 42


class TestMigrationQuestionnaireDeploymentTarget:
    """Tests for questionnaire deployment target selection."""

    @patch("builtins.input", return_value="1")
    @patch("click.echo")
    def test_ask_deployment_target_app(self, mock_echo, mock_input):
        """Test selecting Ansible App as deployment target."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_deployment_target()

        assert questionnaire.config.deployment_target == DeploymentTarget.APP
        mock_input.assert_called_once()

    @patch("builtins.input", return_value="3")
    @patch("click.echo")
    def test_ask_deployment_target_aap(self, mock_echo, mock_input):
        """Test selecting AAP as deployment target."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_deployment_target()

        assert questionnaire.config.deployment_target == DeploymentTarget.AAP

    @patch("builtins.input", return_value="4")
    @patch("click.echo")
    def test_ask_deployment_target_native(self, mock_echo, mock_input):
        """Test selecting native Ansible as deployment target."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_deployment_target()

        assert questionnaire.config.deployment_target == DeploymentTarget.NATIVE

    @patch("builtins.input", return_value="")
    @patch("click.echo")
    def test_ask_deployment_target_default(self, mock_echo, mock_input):
        """Test default deployment target (AWX)."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_deployment_target()

        assert questionnaire.config.deployment_target == DeploymentTarget.AWX

    @patch("builtins.input", return_value="99")
    @patch("click.echo")
    def test_ask_deployment_target_invalid_fallback(self, mock_echo, mock_input):
        """Test invalid input falls back to AWX."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_deployment_target()

        assert questionnaire.config.deployment_target == DeploymentTarget.AWX


class TestMigrationQuestionnaireMigrationStrategy:
    """Tests for questionnaire migration strategy selection."""

    @patch("builtins.input", return_value="2")
    @patch("click.echo")
    def test_ask_migration_strategy_flat(self, mock_echo, mock_input):
        """Test selecting flat migration strategy."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_migration_strategy()

        assert questionnaire.config.migration_standard == MigrationStandard.FLAT

    @patch("builtins.input", return_value="3")
    @patch("click.echo")
    def test_ask_migration_strategy_hybrid(self, mock_echo, mock_input):
        """Test selecting hybrid migration strategy."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_migration_strategy()

        assert questionnaire.config.migration_standard == MigrationStandard.HYBRID

    @patch("builtins.input", return_value="")
    @patch("click.echo")
    def test_ask_migration_strategy_default(self, mock_echo, mock_input):
        """Test default migration strategy (standard)."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_migration_strategy()

        assert questionnaire.config.migration_standard == MigrationStandard.STANDARD


class TestMigrationQuestionnaireInventorySource:
    """Tests for questionnaire inventory source selection."""

    @patch("builtins.input", return_value="2")
    @patch("click.echo")
    def test_ask_inventory_source_manual(self, mock_echo, mock_input):
        """Test selecting manual inventory source."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_inventory_source()

        assert questionnaire.config.inventory_source == "manual"

    @patch("builtins.input", return_value="3")
    @patch("click.echo")
    def test_ask_inventory_source_cloud(self, mock_echo, mock_input):
        """Test selecting cloud provider inventory source."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_inventory_source()

        assert questionnaire.config.inventory_source == "cloud-provider"

    @patch("builtins.input", return_value="")
    @patch("click.echo")
    def test_ask_inventory_source_default(self, mock_echo, mock_input):
        """Test default inventory source (chef-server)."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_inventory_source()

        assert questionnaire.config.inventory_source == "chef-server"


class TestMigrationQuestionnaireValidation:
    """Tests for questionnaire validation strategy selection."""

    @patch("builtins.input", side_effect=["n"])
    @patch("click.echo")
    def test_ask_validation_strategy_no_validation(self, mock_echo, mock_input):
        """Test disabling post-migration validation."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_validation_strategy()

        assert questionnaire.config.validate_post_migration is False
        assert mock_input.call_count == 1

    @patch("builtins.input", side_effect=["y", "1,3", "y"])
    @patch("click.echo")
    def test_ask_validation_strategy_custom_tools(self, mock_echo, mock_input):
        """Test selecting custom validation tools."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_validation_strategy()

        assert questionnaire.config.validate_post_migration is True
        assert ValidationTool.ANSIBLE_LINT in questionnaire.config.validation_tools
        assert ValidationTool.TOX_ANSIBLE in questionnaire.config.validation_tools
        assert ValidationTool.MOLECULE not in questionnaire.config.validation_tools

    @patch("builtins.input", side_effect=["y", "", "n"])
    @patch("click.echo")
    def test_ask_validation_strategy_no_iteration(self, mock_echo, mock_input):
        """Test disabling iteration until clean."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_validation_strategy()

        assert questionnaire.config.validate_post_migration is True
        assert questionnaire.config.iterate_until_clean is False

    @patch("builtins.input", side_effect=["y", "1,2,3", "y"])
    @patch("click.echo")
    def test_ask_validation_strategy_all_tools(self, mock_echo, mock_input):
        """Test selecting all validation tools."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_validation_strategy()

        assert len(questionnaire.config.validation_tools) == 3
        assert ValidationTool.ANSIBLE_LINT in questionnaire.config.validation_tools
        assert ValidationTool.MOLECULE in questionnaire.config.validation_tools
        assert ValidationTool.TOX_ANSIBLE in questionnaire.config.validation_tools

    @patch("builtins.input", side_effect=["y", "99,invalid", "y"])
    @patch("click.echo")
    def test_ask_validation_strategy_invalid_tools_fallback(
        self, mock_echo, mock_input
    ):
        """Test invalid tool selections fall back to defaults."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_validation_strategy()

        assert ValidationTool.ANSIBLE_LINT in questionnaire.config.validation_tools
        assert ValidationTool.MOLECULE in questionnaire.config.validation_tools


class TestMigrationQuestionnaireVersions:
    """Tests for questionnaire Python and Ansible version selection."""

    @patch("builtins.input", side_effect=["3.11", "2.15"])
    @patch("click.echo")
    def test_ask_python_ansible_versions_custom(self, mock_echo, mock_input):
        """Test custom Python and Ansible versions."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_python_ansible_versions()

        assert questionnaire.config.target_python_version == "3.11"
        assert questionnaire.config.target_ansible_version == "2.15"

    @patch("builtins.input", side_effect=["", ""])
    @patch("click.echo")
    def test_ask_python_ansible_versions_default(self, mock_echo, mock_input):
        """Test default Python and Ansible versions."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_python_ansible_versions()

        assert questionnaire.config.target_python_version == "3.9"
        assert questionnaire.config.target_ansible_version == "2.13"


class TestMigrationQuestionnairePreservation:
    """Tests for questionnaire preservation options."""

    @patch("builtins.input", side_effect=["n", "n", "n"])
    @patch("click.echo")
    def test_ask_preservation_options_all_disabled(self, mock_echo, mock_input):
        """Test disabling all preservation options."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_preservation_options()

        assert questionnaire.config.preserve_handlers is False
        assert questionnaire.config.preserve_node_attributes is False
        assert questionnaire.config.convert_templates_to_jinja2 is False

    @patch("builtins.input", side_effect=["y", "y", "y"])
    @patch("click.echo")
    def test_ask_preservation_options_all_enabled(self, mock_echo, mock_input):
        """Test enabling all preservation options."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_preservation_options()

        assert questionnaire.config.preserve_handlers is True
        assert questionnaire.config.preserve_node_attributes is True
        assert questionnaire.config.convert_templates_to_jinja2 is True

    @patch("builtins.input", side_effect=["", "", ""])
    @patch("click.echo")
    def test_ask_preservation_options_defaults(self, mock_echo, mock_input):
        """Test default preservation options (all enabled)."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_preservation_options()

        assert questionnaire.config.preserve_handlers is True
        assert questionnaire.config.preserve_node_attributes is True
        assert questionnaire.config.convert_templates_to_jinja2 is True


class TestMigrationQuestionnaireChecksAndDocs:
    """Tests for questionnaire checks and documentation options."""

    @patch("builtins.input", side_effect=["n", "n", "1"])
    @patch("click.echo")
    def test_ask_checks_and_documentation_minimal(self, mock_echo, mock_input):
        """Test minimal documentation with no checks."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_checks_and_documentation()

        assert questionnaire.config.generate_pre_checks is False
        assert questionnaire.config.generate_post_checks is False
        assert questionnaire.config.documentation_level == "minimal"

    @patch("builtins.input", side_effect=["y", "y", "2"])
    @patch("click.echo")
    def test_ask_checks_and_documentation_standard(self, mock_echo, mock_input):
        """Test standard documentation with checks enabled."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_checks_and_documentation()

        assert questionnaire.config.generate_pre_checks is True
        assert questionnaire.config.generate_post_checks is True
        assert questionnaire.config.documentation_level == "standard"

    @patch("builtins.input", side_effect=["", "", ""])
    @patch("click.echo")
    def test_ask_checks_and_documentation_defaults(self, mock_echo, mock_input):
        """Test default checks and documentation (comprehensive)."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_checks_and_documentation()

        assert questionnaire.config.generate_pre_checks is True
        assert questionnaire.config.generate_post_checks is True
        assert questionnaire.config.documentation_level == "comprehensive"

    @patch("builtins.input", side_effect=["y", "y", "99"])
    @patch("click.echo")
    def test_ask_checks_and_documentation_invalid_fallback(self, mock_echo, mock_input):
        """Test invalid documentation level falls back to comprehensive."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.ask_checks_and_documentation()

        assert questionnaire.config.documentation_level == "comprehensive"


class TestMigrationQuestionnaireInteractive:
    """Tests for full interactive questionnaire flow."""

    @patch(
        "builtins.input",
        side_effect=[
            "1",
            "1",
            "1",
            "y",
            "1,2",
            "y",
            "3.10",
            "2.14",
            "y",
            "y",
            "y",
            "y",
            "y",
            "3",
        ],
    )
    @patch("click.echo")
    def test_run_interactive_full_flow(self, mock_echo, mock_input):
        """Test complete interactive questionnaire flow."""
        questionnaire = MigrationQuestionnaire()
        config = questionnaire.run_interactive()

        assert config.deployment_target == DeploymentTarget.APP
        assert config.migration_standard == MigrationStandard.STANDARD
        assert config.inventory_source == "chef-server"
        assert config.validate_post_migration is True
        assert config.iterate_until_clean is True
        assert config.target_python_version == "3.10"
        assert config.target_ansible_version == "2.14"
        assert config.preserve_handlers is True
        assert config.preserve_node_attributes is True
        assert config.convert_templates_to_jinja2 is True
        assert config.generate_pre_checks is True
        assert config.generate_post_checks is True
        assert config.documentation_level == "comprehensive"

    @patch(
        "builtins.input",
        side_effect=["4", "2", "3", "n", "", "", "n", "n", "n", "n", "n", "1"],
    )
    @patch("click.echo")
    def test_run_interactive_minimal_config(self, mock_echo, mock_input):
        """Test interactive questionnaire with minimal configuration."""
        questionnaire = MigrationQuestionnaire()
        config = questionnaire.run_interactive()

        assert config.deployment_target == DeploymentTarget.NATIVE
        assert config.migration_standard == MigrationStandard.FLAT
        assert config.inventory_source == "cloud-provider"
        assert config.validate_post_migration is False
        assert config.preserve_handlers is False
        assert config.preserve_node_attributes is False
        assert config.convert_templates_to_jinja2 is False
        assert config.generate_pre_checks is False
        assert config.generate_post_checks is False
        assert config.documentation_level == "minimal"

    @patch(
        "builtins.input",
        side_effect=[
            "2",
            "3",
            "2",
            "y",
            "3",
            "n",
            "3.12",
            "2.16",
            "y",
            "n",
            "y",
            "n",
            "y",
            "2",
        ],
    )
    @patch("click.echo")
    def test_run_interactive_mixed_config(self, mock_echo, mock_input):
        """Test interactive questionnaire with mixed configuration."""
        questionnaire = MigrationQuestionnaire()
        config = questionnaire.run_interactive()

        assert config.deployment_target == DeploymentTarget.AWX
        assert config.migration_standard == MigrationStandard.HYBRID
        assert config.inventory_source == "manual"
        assert config.validate_post_migration is True
        assert ValidationTool.TOX_ANSIBLE in config.validation_tools
        assert config.iterate_until_clean is False
        assert config.preserve_handlers is True
        assert config.preserve_node_attributes is False
        assert config.convert_templates_to_jinja2 is True
        assert config.generate_pre_checks is False
        assert config.generate_post_checks is True
        assert config.documentation_level == "standard"


class TestMigrationQuestionnairePrintSummary:
    """Tests for questionnaire summary printing."""

    @patch("click.echo")
    def test_print_summary_with_validation(self, mock_echo):
        """Test summary printing with validation enabled."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.config.validate_post_migration = True
        questionnaire.config.validation_tools = [
            ValidationTool.ANSIBLE_LINT,
            ValidationTool.MOLECULE,
        ]
        questionnaire._print_summary()

        # Verify key information is printed
        calls = [str(call_obj) for call_obj in mock_echo.call_args_list]
        summary_text = "\n".join(calls)

        assert "awx" in summary_text.lower()
        assert "standard" in summary_text.lower()
        assert "chef-server" in summary_text.lower()
        assert "true" in summary_text.lower()

    @patch("click.echo")
    def test_print_summary_without_validation(self, mock_echo):
        """Test summary printing with validation disabled."""
        questionnaire = MigrationQuestionnaire()
        questionnaire.config.validate_post_migration = False
        questionnaire._print_summary()

        calls = [str(call_obj) for call_obj in mock_echo.call_args_list]
        summary_text = "\n".join(calls)

        assert "false" in summary_text.lower()


class TestGetMigrationConfigFromUser:
    """Tests for get_migration_config_from_user function."""

    @patch(
        "builtins.input",
        side_effect=[
            "1",
            "1",
            "1",
            "y",
            "1",
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
    @patch("click.echo")
    def test_get_migration_config_from_user(self, mock_echo, mock_input):
        """Test getting migration config from user interaction."""
        config = get_migration_config_from_user()

        assert isinstance(config, MigrationConfig)
        assert config.deployment_target == DeploymentTarget.APP


class TestGetMigrationConfigFromCliArgs:
    """Tests for get_migration_config_from_cli_args function."""

    def test_get_migration_config_from_cli_args_full(self):
        """Test creating config from complete CLI arguments."""
        args = {
            "deployment_target": "aap",
            "migration_standard": "hybrid",
            "inventory_source": "cloud",
            "validate": False,
            "validation_tools": ["ansible-lint", "tox-ansible"],
            "iterate": False,
            "python_version": "3.11",
            "ansible_version": "2.15",
        }
        config = get_migration_config_from_cli_args(args)

        assert config.deployment_target == DeploymentTarget.AAP
        assert config.migration_standard == MigrationStandard.HYBRID
        assert config.inventory_source == "cloud"
        assert config.validate_post_migration is False
        assert ValidationTool.ANSIBLE_LINT in config.validation_tools
        assert ValidationTool.TOX_ANSIBLE in config.validation_tools
        assert config.iterate_until_clean is False
        assert config.target_python_version == "3.11"
        assert config.target_ansible_version == "2.15"

    def test_get_migration_config_from_cli_args_partial(self):
        """Test creating config from partial CLI arguments."""
        args = {
            "deployment_target": "native",
            "python_version": "3.12",
        }
        config = get_migration_config_from_cli_args(args)

        assert config.deployment_target == DeploymentTarget.NATIVE
        assert config.target_python_version == "3.12"
        # Verify defaults are used for omitted fields
        assert config.migration_standard == MigrationStandard.STANDARD
        assert config.validate_post_migration is True

    def test_get_migration_config_from_cli_args_empty(self):
        """Test creating config from empty CLI arguments uses defaults."""
        args = {}
        config = get_migration_config_from_cli_args(args)

        assert config.deployment_target == DeploymentTarget.AWX
        assert config.migration_standard == MigrationStandard.STANDARD
        assert config.inventory_source == "chef-server"
        assert config.validate_post_migration is True
