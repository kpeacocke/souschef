"""Unit tests for the interactive CLI migration wizard."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from souschef.migration_wizard import (
    _confirm_configuration,
    _prompt_cookbook_path,
    _prompt_output_directory,
    _yes_no_prompt,
    generate_migration_config,
    setup_wizard,
    validate_inputs,
)


class TestValidateInputs:
    """Test configuration validation."""

    def test_validate_inputs_success(self, tmp_path: Path) -> None:
        """Test validation with valid configuration."""
        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()

        config = {
            "cookbook_path": str(cookbook_path),
            "output_dir": str(tmp_path / "output"),
            "chef_version": "14.15.6",
            "ansible_version": "2.12",
            "resource_patterns": {"package": True, "service": False},
        }

        is_valid, errors = validate_inputs(config)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_inputs_missing_cookbook_path(self) -> None:
        """Test validation fails when cookbook_path is missing."""
        config = {
            "output_dir": "/tmp/output",  # NOSONAR - test fixture
            "chef_version": "14.15.6",
            "ansible_version": "2.12",
        }

        is_valid, errors = validate_inputs(config)
        assert is_valid is False
        assert any("cookbook_path" in error for error in errors)

    def test_validate_inputs_nonexistent_cookbook_path(self) -> None:
        """Test validation fails when cookbook path doesn't exist."""
        config = {
            "cookbook_path": "/nonexistent/path",
            "output_dir": "/tmp/output",  # NOSONAR - test fixture
            "chef_version": "14.15.6",
            "ansible_version": "2.12",
        }

        is_valid, errors = validate_inputs(config)
        assert is_valid is False
        assert any("does not exist" in error for error in errors)

    def test_validate_inputs_missing_output_dir(self, tmp_path: Path) -> None:
        """Test validation fails when output_dir is missing."""
        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()

        config = {
            "cookbook_path": str(cookbook_path),
            "chef_version": "14.15.6",
            "ansible_version": "2.12",
        }

        is_valid, errors = validate_inputs(config)
        assert is_valid is False
        assert any("output_dir" in error for error in errors)

    def test_validate_inputs_missing_chef_version(self, tmp_path: Path) -> None:
        """Test validation fails when chef_version is missing."""
        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()

        config = {
            "cookbook_path": str(cookbook_path),
            "output_dir": str(tmp_path / "output"),
            "ansible_version": "2.12",
        }

        is_valid, errors = validate_inputs(config)
        assert is_valid is False
        assert any("chef_version" in error for error in errors)

    def test_validate_inputs_invalid_chef_version(self, tmp_path: Path) -> None:
        """Test validation fails with invalid Chef version format."""
        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()

        config = {
            "cookbook_path": str(cookbook_path),
            "output_dir": str(tmp_path / "output"),
            "chef_version": "invalid",
            "ansible_version": "2.12",
        }

        is_valid, errors = validate_inputs(config)
        assert is_valid is False
        assert any("Invalid Chef version" in error for error in errors)

    def test_validate_inputs_missing_ansible_version(self, tmp_path: Path) -> None:
        """Test validation fails when ansible_version is missing."""
        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()

        config = {
            "cookbook_path": str(cookbook_path),
            "output_dir": str(tmp_path / "output"),
            "chef_version": "14.15.6",
        }

        is_valid, errors = validate_inputs(config)
        assert is_valid is False
        assert any("ansible_version" in error for error in errors)

    def test_validate_inputs_no_resource_patterns_enabled(self, tmp_path: Path) -> None:
        """Test validation fails when no resource patterns are enabled."""
        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()

        config = {
            "cookbook_path": str(cookbook_path),
            "output_dir": str(tmp_path / "output"),
            "chef_version": "14.15.6",
            "ansible_version": "2.12",
            "resource_patterns": {
                "package": False,
                "service": False,
                "file": False,
            },
        }

        is_valid, errors = validate_inputs(config)
        assert is_valid is False
        assert any("at least one resource pattern" in error.lower() for error in errors)

    def test_validate_inputs_valid_chef_version_formats(self, tmp_path: Path) -> None:
        """Test validation accepts various valid version formats."""
        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()

        versions = ["12.19", "14.15.6", "15.0"]

        for version in versions:
            config = {
                "cookbook_path": str(cookbook_path),
                "output_dir": str(tmp_path / "output"),
                "chef_version": version,
                "ansible_version": "2.12",
                "resource_patterns": {"package": True},
            }

            is_valid, _ = validate_inputs(config)
            assert is_valid is True, f"Version {version} should be valid"


class TestGenerateMigrationConfig:
    """Test configuration file generation."""

    def test_generate_migration_config_basic(self) -> None:
        """Test generating basic configuration."""
        config = {
            "cookbook_path": "/path/to/cookbook",
            "chef_version": "14.15.6",
            "output_dir": "/path/to/output",
            "ansible_version": "2.12",
            "resource_patterns": {
                "package": True,
                "service": True,
                "file": False,
            },
            "conversion_options": {
                "preserve_comments": True,
                "add_annotations": False,
            },
            "validation_options": {
                "syntax_check": True,
                "lint_check": False,
            },
            "optimization_options": {
                "deduplicate_tasks": True,
                "consolidate_loops": False,
            },
        }

        yaml_content = generate_migration_config(config)

        assert "cookbook:" in yaml_content
        assert "/path/to/cookbook" in yaml_content
        assert "chef_version: '14.15.6'" in yaml_content
        assert "ansible_version: '2.12'" in yaml_content
        assert "package: true" in yaml_content
        assert "service: true" in yaml_content
        assert "file: false" in yaml_content

    def test_generate_migration_config_contains_all_sections(self) -> None:
        """Test that generated config includes all required sections."""
        config = {
            "cookbook_path": "/cookbook",
            "chef_version": "14.15.6",
            "output_dir": "/output",
            "ansible_version": "2.12",
            "resource_patterns": {"package": True},
            "conversion_options": {"preserve_comments": True},
            "validation_options": {"syntax_check": True},
            "optimization_options": {"deduplicate_tasks": True},
        }

        yaml_content = generate_migration_config(config)

        assert "cookbook:" in yaml_content
        assert "output:" in yaml_content
        assert "resource_patterns:" in yaml_content
        assert "conversion:" in yaml_content
        assert "validation:" in yaml_content
        assert "optimization:" in yaml_content

    def test_generate_migration_config_boolean_lowercase(self) -> None:
        """Test that boolean values are lowercase."""
        config = {
            "cookbook_path": "/cookbook",
            "chef_version": "14.15.6",
            "output_dir": "/output",
            "ansible_version": "2.12",
            "resource_patterns": {"package": True, "service": False},
            "conversion_options": {"preserve_comments": True},
            "validation_options": {"syntax_check": False},
            "optimization_options": {"deduplicate_tasks": True},
        }

        yaml_content = generate_migration_config(config)

        assert "true" in yaml_content
        assert "false" in yaml_content
        assert "True" not in yaml_content
        assert "False" not in yaml_content

    def test_generate_migration_config_empty_options(self) -> None:
        """Empty option sections should still render headers."""
        config = {
            "cookbook_path": "/cookbook",
            "chef_version": "14.15.6",
            "output_dir": "/output",
            "ansible_version": "2.12",
            "resource_patterns": {},
            "conversion_options": {},
            "validation_options": {},
            "optimization_options": {},
        }

        yaml_content = generate_migration_config(config)

        assert "resource_patterns:" in yaml_content
        assert "conversion:" in yaml_content
        assert "validation:" in yaml_content
        assert "optimization:" in yaml_content


class TestWizardPrompts:
    """Test interactive prompt helpers."""

    def test_prompt_output_directory_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty input should return default output directory."""
        monkeypatch.setattr("builtins.input", lambda _prompt: "")
        result = _prompt_output_directory()
        assert "ansible_output" in result

    def test_yes_no_prompt_invalid_then_yes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Invalid response should reprompt until valid."""
        responses = iter(["maybe", "y"])
        monkeypatch.setattr("builtins.input", lambda _prompt: next(responses))
        assert _yes_no_prompt("Proceed? ") is True

    def test_confirm_configuration_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Confirmation should honour a negative response."""
        monkeypatch.setattr(
            "souschef.migration_wizard._yes_no_prompt", lambda *_args, **_kwargs: False
        )
        config = {
            "cookbook_path": "/tmp/cookbook",
            "output_dir": "/tmp/output",
            "chef_version": "14.15.6",
            "ansible_version": "2.12",
            "resource_patterns": {"package": True},
            "conversion_options": {"preserve_comments": True},
            "validation_options": {"syntax_check": True},
            "optimization_options": {"deduplicate_tasks": True},
        }
        assert _confirm_configuration(config) is False

    def test_prompt_cookbook_path_success(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Prompt should return valid path when validation passes."""
        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'test'")

        monkeypatch.setattr("builtins.input", lambda _prompt: str(cookbook))
        result = _prompt_cookbook_path()
        assert str(cookbook.resolve()) == result

    def test_prompt_cookbook_path_retry_then_exit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Prompt should exit when validation returns exit."""
        responses = iter(["/missing", "n"])
        monkeypatch.setattr("builtins.input", lambda _prompt: next(responses))

        with pytest.raises(SystemExit):
            _prompt_cookbook_path()


class TestSetupWizard:
    """Test interactive wizard functionality."""

    @patch("souschef.migration_wizard.input")
    @patch("souschef.migration_wizard._confirm_configuration")
    def test_setup_wizard_success(
        self, mock_confirm: MagicMock, mock_input: MagicMock, tmp_path: Path
    ) -> None:
        """Test successful wizard completion."""
        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()
        (cookbook_path / "metadata.rb").touch()

        # Mock user inputs
        mock_input.side_effect = [
            str(cookbook_path),  # cookbook path
            "",  # output dir (use default)
            "",  # chef version (use default)
            "",  # ansible version (use default)
            "y",  # package resources
            "y",  # service resources
            "y",  # file resources
            "y",  # template resources
            "y",  # directory resources
            "y",  # execute resources
            "y",  # custom resources
            "y",  # preserve comments
            "y",  # add annotations
            "y",  # generate handlers
            "n",  # custom modules
            "y",  # conversion rules
            "y",  # syntax check
            "n",  # lint check
            "y",  # generate report
            "y",  # deduplicate
            "y",  # consolidate loops
            "y",  # optimize handlers
            "n",  # parallel processing
        ]
        mock_confirm.return_value = True

        config = setup_wizard()

        assert config is not None
        assert "cookbook_path" in config
        assert "output_dir" in config
        assert "chef_version" in config
        assert "ansible_version" in config
        assert "resource_patterns" in config
        assert "conversion_options" in config

    @patch("souschef.migration_wizard.input")
    @patch("souschef.migration_wizard._confirm_configuration")
    @patch("souschef.migration_wizard.sys.exit")
    def test_setup_wizard_user_cancels(
        self,
        mock_exit: MagicMock,
        mock_confirm: MagicMock,
        mock_input: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test wizard cancellation by user."""
        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()
        (cookbook_path / "metadata.rb").touch()

        mock_input.side_effect = [
            str(cookbook_path),
            "",
            "",
            "",
            "y",
            "y",
            "y",
            "y",
            "y",
            "y",
            "y",
            "y",
            "y",
            "y",
            "n",
            "y",
            "y",
            "n",
            "y",
            "y",
            "y",
            "y",
            "n",
        ]
        mock_confirm.return_value = False

        setup_wizard()

        # Check sys.exit was called with 0 (cancel)
        mock_exit.assert_called_once_with(0)

    @pytest.mark.skip(reason="Complex mocking of interactive prompts")
    @patch("souschef.migration_wizard.input")
    @patch("souschef.migration_wizard.sys.exit")
    def test_setup_wizard_invalid_cookbook_path(
        self, mock_exit: MagicMock, mock_input: MagicMock
    ) -> None:
        """Test wizard with invalid cookbook path."""
        # Invalid path triggers retry prompt
        # First: Enter invalid path
        # Second: Retry prompt - answer 'n' (no)
        mock_input.side_effect = [
            "/nonexistent/path",  # Cookbook path attempt (fails)
            "n",  # Would you like to try again? -> No (should exit)
        ]

        setup_wizard()

        # Should exit when user chooses not to retry
        mock_exit.assert_called_once_with(1)


class TestWizardIntegration:
    """Integration tests for full wizard workflow."""

    @patch("souschef.migration_wizard.input")
    @patch("souschef.migration_wizard._confirm_configuration")
    def test_complete_wizard_flow_with_defaults(
        self, mock_confirm: MagicMock, mock_input: MagicMock, tmp_path: Path
    ) -> None:
        """Test complete wizard flow using default values."""
        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()
        (cookbook_path / "metadata.rb").touch()

        # Use all defaults by pressing enter
        mock_input.side_effect = [
            str(cookbook_path),  # cookbook path
        ] + [""] * 22  # All other prompts use defaults

        mock_confirm.return_value = True

        config = setup_wizard()

        # Verify defaults are applied
        assert config["chef_version"] == "14.15.6"
        assert config["ansible_version"] == "2.12"
        assert "ansible_output" in config["output_dir"]

        # Verify resource patterns default to True
        assert config["resource_patterns"]["package"] is True
        assert config["resource_patterns"]["service"] is True

    def test_validate_and_generate_config_workflow(self, tmp_path: Path) -> None:
        """Test workflow of validation followed by config generation."""
        cookbook_path = tmp_path / "cookbook"
        cookbook_path.mkdir()

        config = {
            "cookbook_path": str(cookbook_path),
            "output_dir": str(tmp_path / "output"),
            "chef_version": "14.15.6",
            "ansible_version": "2.12",
            "resource_patterns": {"package": True, "service": True},
            "conversion_options": {"preserve_comments": True},
            "validation_options": {"syntax_check": True},
            "optimization_options": {"deduplicate_tasks": True},
        }

        # Validate first
        is_valid, _ = validate_inputs(config)
        assert is_valid is True

        # Then generate config
        yaml_content = generate_migration_config(config)
        assert len(yaml_content) > 0
        assert "package: true" in yaml_content
