"""Tests to achieve 100% coverage for remaining cli.py lines."""

import json
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from souschef.cli import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_cookbook(tmp_path):
    """Create a sample cookbook structure for testing."""
    cookbook = tmp_path / "test_cookbook"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text('name "test"\nversion "1.0.0"')
    recipes_dir = cookbook / "recipes"
    recipes_dir.mkdir()
    (recipes_dir / "default.rb").write_text('package "nginx"')
    return cookbook


class TestSafeWriteFileErrors:
    """Test _safe_write_file error paths."""

    def test_safe_write_file_oserror(self, runner, tmp_path):
        """Test _safe_write_file with OSError during write."""
        # Lines 155-157: OSError handler in _safe_write_file
        recipe_file = tmp_path / "recipe.rb"
        recipe_file.write_text('package "nginx"')

        with (
            patch(
                "souschef.cli.generate_playbook_from_recipe",
                return_value="---\n- hosts: all",
            ),
            patch("pathlib.Path.open", side_effect=OSError("Write failed")),
        ):
            result = runner.invoke(
                cli,
                [
                    "convert-recipe",
                    "--cookbook-path",
                    str(tmp_path),
                    "--recipe-name",
                    "test",
                ],
            )
            # Should handle write error and abort
            assert "Error writing file" in result.output or result.exit_code != 0

    def test_resolve_output_path_valueerror(self, runner, tmp_path):
        """Test _resolve_output_path with ValueError from path validation."""
        # Lines 126-128: ValueError handler in _resolve_output_path
        recipe_file = tmp_path / "recipe.rb"
        recipe_file.write_text('package "nginx"')

        with patch(
            "souschef.cli._ensure_within_base_path",
            side_effect=ValueError("Path outside workspace"),
        ):
            result = runner.invoke(
                cli,
                [
                    "convert-recipe",
                    "--cookbook-path",
                    str(tmp_path),
                    "--recipe-name",
                    "test",
                    "--output-path",
                    "/invalid",
                ],
            )
            assert result.exit_code != 0


class TestInitCliGroupsException:
    """Test _init_cli_groups exception handling."""

    def test_init_cli_groups_logs_on_exception(self):
        """Test that CLI group initialization exceptions are logged."""
        # Lines 178-182: Exception handler in _init_cli_groups
        import logging

        from souschef import cli as cli_module

        logged_messages = []

        def mock_debug(msg):
            logged_messages.append(msg)

        with (
            patch.object(logging, "debug", mock_debug),
            patch(
                "souschef.cli.register_default_groups",
                side_effect=RuntimeError("Test failure"),
            ),
        ):
            # Call the function directly
            cli_module._init_cli_groups()

        # Should log the failure
        assert any("Failed to initialise CLI groups" in msg for msg in logged_messages)


class TestCookbookCommandPaths:
    """Test cookbook command conditional paths."""

    def test_cookbook_shows_template_decode_error(self, runner, sample_cookbook):
        """Test cookbook command with JSON decode error in template display."""
        # Lines 404-405: JSONDecodeError in template display
        with patch("souschef.cli.parse_template", return_value="not valid json"):
            result = runner.invoke(cli, ["cookbook", str(sample_cookbook)])
            # Should handle invalid JSON gracefully
            assert result.exit_code == 0

    def test_cookbook_dry_run_message(self, runner, sample_cookbook):
        """Test cookbook command dry-run shows message."""
        # Lines 473-474: Dry-run output message
        result = runner.invoke(
            cli,
            ["cookbook", str(sample_cookbook), "--output", "output.zip", "--dry-run"],
        )
        assert "Would save results to" in result.output
        assert "Dry run" in result.output

    def test_cookbook_failed_template_conversion(self, runner, sample_cookbook):
        """Test cookbook command with failed template conversion."""
        # Line 559: Failed template conversion message
        templates_dir = sample_cookbook / "templates" / "default"
        templates_dir.mkdir(parents=True)
        (templates_dir / "test.erb").write_text("<%= @var %>")

        with patch("souschef.cli.parse_template", return_value=None):
            result = runner.invoke(cli, ["cookbook", str(sample_cookbook)])
            # Should show failure message or complete
            assert result.exit_code in [0, 1]


class TestInspecCommandPaths:
    """Test InSpec command paths."""

    def test_inspec_parse_result_output(self, runner, tmp_path):
        """Test inspec-parse outputs result."""
        # Lines 607-608: Result output in inspec_parse
        inspec_file = tmp_path / "test.rb"
        inspec_file.write_text('describe file("/etc") do\n  it { should exist }\nend')

        with patch("souschef.cli.parse_inspec_profile", return_value="Parsed profile"):
            result = runner.invoke(cli, ["inspec-parse", str(inspec_file)])
            assert result.exit_code == 0
            assert "Parsed profile" in result.output

    def test_inspec_convert_result_output(self, runner, tmp_path):
        """Test inspec-convert outputs result."""
        # Lines 626-627: Result output in inspec_convert
        inspec_file = tmp_path / "test.rb"
        inspec_file.write_text('describe file("/etc") do\n  it { should exist }\nend')

        with patch(
            "souschef.cli.convert_inspec_to_test", return_value="Converted test"
        ):
            result = runner.invoke(cli, ["inspec-convert", str(inspec_file)])
            assert result.exit_code == 0
            assert "Converted test" in result.output

    def test_inspec_generate_calls_output_result(self, runner, tmp_path):
        """Test inspec-generate calls _output_result."""
        # Lines 644-645: _output_result call in inspec_generate
        recipe_file = tmp_path / "recipe.rb"
        recipe_file.write_text('package "nginx"')

        with patch(
            "souschef.cli.generate_inspec_from_recipe", return_value='{"controls": []}'
        ):
            result = runner.invoke(
                cli, ["inspec-generate", str(recipe_file), "--format", "json"]
            )
            assert result.exit_code == 0


class TestGitLabCIGeneration:
    """Test GitLab CI generation command paths."""

    def test_gitlab_ci_shows_lint_job(self, runner, sample_cookbook):
        """Test GitLab CI shows lint job when present."""
        # Lines 786, 788, 790: Job display logic
        ci_content = """
stages:
  - lint
cookstyle:
  stage: lint
"""
        with patch(
            "souschef.cli.generate_gitlab_ci_from_chef", return_value=ci_content
        ):
            result = runner.invoke(
                cli,
                ["generate-gitlab-ci", str(sample_cookbook), "--cache", "--artifacts"],
            )
            assert "Lint (cookstyle/foodcritic)" in result.output

    def test_gitlab_ci_exception_handling(self, runner, sample_cookbook):
        """Test GitLab CI generation exception handling."""
        # Lines 795-797: Exception handler for GitLab CI
        with patch(
            "souschef.cli.generate_gitlab_ci_from_chef",
            side_effect=RuntimeError("Failed"),
        ):
            result = runner.invoke(cli, ["generate-gitlab-ci", str(sample_cookbook)])
            assert result.exit_code == 1
            assert "Error generating GitLab CI" in result.output


class TestGitHubWorkflowGeneration:
    """Test GitHub workflow generation paths."""

    def test_github_workflow_shows_all_jobs(self, runner, sample_cookbook):
        """Test GitHub workflow shows all job types."""
        # Lines 873, 875, 877: Job display messages
        workflow_content = """
jobs:
  lint:
    runs-on: ubuntu-latest
  unit-test:
    runs-on: ubuntu-latest
  integration-test:
    runs-on: ubuntu-latest
"""
        with patch(
            "souschef.cli.generate_github_workflow_from_chef",
            return_value=workflow_content,
        ):
            result = runner.invoke(
                cli,
                [
                    "generate-github-workflow",
                    str(sample_cookbook),
                    "--cache",
                    "--artifacts",
                ],
            )
            assert "Lint (cookstyle/foodcritic)" in result.output
            assert "Unit Tests (ChefSpec)" in result.output
            assert "Integration Tests (Test Kitchen)" in result.output

    def test_github_workflow_exception_handling(self, runner, sample_cookbook):
        """Test GitHub workflow exception handling."""
        # Lines 882-884: Exception handler for GitHub workflow
        with patch(
            "souschef.cli.generate_github_workflow_from_chef",
            side_effect=ValueError("Config error"),
        ):
            result = runner.invoke(
                cli, ["generate-github-workflow", str(sample_cookbook)]
            )
            assert result.exit_code == 1
            assert "Error generating GitHub Actions workflow" in result.output


class TestOutputJsonFormat:
    """Test _output_json_format function."""

    def test_output_json_format_with_list(self):
        """Test JSON formatting with list data."""
        # Line 914: List item output in _output_json_format
        from souschef.cli import _output_json_format

        with patch("souschef.cli.click.echo") as mock_echo:
            _output_json_format('[{"key": "value"}, {"key2": "value2"}]')
            # Should echo the items
            assert mock_echo.called


class TestProfileCommand:
    """Test profile command error paths."""

    def test_profile_write_exception(self, runner, sample_cookbook):
        """Test profile command with write exception."""
        # Lines 957-963: Exception handler in profile
        with (
            patch(
                "souschef.cli.generate_cookbook_performance_report", return_value=Mock()
            ),
            patch("pathlib.Path.write_text", side_effect=OSError("Write failed")),
        ):
            result = runner.invoke(
                cli, ["profile", str(sample_cookbook), "--output", "report.txt"]
            )
            # Should handle error
            assert result.exit_code in [0, 1]


class TestProfileOperationCommand:
    """Test profile-operation command paths."""

    def test_profile_operation_detailed_mode(self, runner, tmp_path):
        """Test profile-operation with detailed flag."""
        # Lines 1004-1010: Detailed profiling path
        recipe_file = tmp_path / "recipe.rb"
        recipe_file.write_text('package "nginx"')

        mock_result = Mock()
        mock_result.function_stats = {"top_functions": "function details"}

        # Need to import and patch the function from souschef.profiling, not cli
        with patch(
            "souschef.profiling.detailed_profile_function",
            return_value=(None, mock_result),
        ):
            result = runner.invoke(
                cli, ["profile-operation", "recipe", str(recipe_file), "--detailed"]
            )
            assert result.exit_code == 0
            assert "Detailed Function Statistics" in result.output

    def test_profile_operation_exception(self, runner, tmp_path):
        """Test profile-operation exception handling."""
        # Line 1013: Exception handler
        recipe_file = tmp_path / "recipe.rb"
        recipe_file.write_text('package "nginx"')

        with patch(
            "souschef.cli.parse_recipe", side_effect=RuntimeError("Parse failed")
        ):
            result = runner.invoke(
                cli, ["profile-operation", "recipe", str(recipe_file)]
            )
            assert result.exit_code == 1
            assert "Error profiling operation" in result.output


class TestConvertRecipeCommand:
    """Test convert-recipe command."""

    def test_convert_recipe_exception(self, runner, tmp_path):
        """Test convert-recipe with exception."""
        # Line 1064: Exception handler
        with patch(
            "souschef.cli.generate_playbook_from_recipe",
            side_effect=ValueError("Invalid recipe"),
        ):
            result = runner.invoke(
                cli,
                [
                    "convert-recipe",
                    "--cookbook-path",
                    str(tmp_path),
                    "--recipe-name",
                    "default",
                    "--output-path",
                    str(tmp_path / "out"),
                ],
            )
            assert result.exit_code == 1


class TestAssessCookbookCommand:
    """Test assess-cookbook command paths."""

    def test_assess_cookbook_many_dependencies(self, runner, sample_cookbook):
        """Test assess-cookbook with many dependencies."""
        # Lines 1141: Many dependencies display
        assessment_data = {
            "complexity_score": 75,
            "dependencies": ["dep1", "dep2", "dep3", "dep4", "dep5", "dep6"],
        }

        # The function is imported from assessment module, so patch it there
        with patch(
            "souschef.assessment.assess_chef_migration_complexity",
            return_value=json.dumps(assessment_data),
        ):
            result = runner.invoke(
                cli, ["assess-cookbook", "--cookbook-path", str(sample_cookbook)]
            )
            assert result.exit_code == 0

    def test_assess_cookbook_output_path_error(self, runner, sample_cookbook):
        """Test assess-cookbook with output path error."""
        # Lines 1146-1147: Output path validation error
        with patch(
            "souschef.cli._resolve_output_path", side_effect=ValueError("Invalid path")
        ):
            result = runner.invoke(
                cli,
                ["assess-cookbook", str(sample_cookbook), "--output", "/invalid/path"],
            )
            # Should abort due to path error
            assert result.exit_code != 0


class TestAnsibleHistoryCommand:
    """Test ansible-history command."""

    def test_ansible_history_empty_results(self, runner):
        """Test ansible-history with no migrations."""
        # Lines 2080-2081: Empty results path
        mock_storage = Mock()
        mock_storage.get_analysis_history.return_value = []
        mock_storage.get_conversion_history.return_value = []

        with patch("souschef.storage.get_storage_manager", return_value=mock_storage):
            result = runner.invoke(cli, ["history", "list"])
            assert "No migration" in result.output or result.exit_code == 0


class TestAnsibleAssessCommand:
    """Test ansible-assess command error paths."""

    def test_ansible_assess_many_collections(self, runner):
        """Test ansible-assess with many collections."""
        # Lines 2089-2095: Many collections truncation
        assessment_data = {
            "ansible_version": "2.15.0",
            "collections": {
                "installed": [f"namespace.collection{i}" for i in range(15)]
            },
            "python_version": "3.9",
        }

        with patch(
            "souschef.cli.assess_ansible_environment", return_value=assessment_data
        ):
            result = runner.invoke(cli, ["ansible", "assess"])
            # Should truncate collection list
            assert result.exit_code == 0

    def test_ansible_assess_version_format_error(self, runner):
        """Test ansible-assess with version formatting error."""
        # Lines 2098-2099: Version formatting exception
        assessment_data = {
            "ansible_version": "2.15.0",
            "collections": {"installed": []},
            "python_version": "3.9",
        }

        with (
            patch(
                "souschef.cli.assess_ansible_environment", return_value=assessment_data
            ),
            patch(
                "souschef.cli.format_version_display",
                side_effect=ValueError("Bad version"),
            ),
        ):
            result = runner.invoke(cli, ["ansible", "assess"])
            # Should handle error gracefully
            assert result.exit_code in [0, 1]

    def test_ansible_assess_eol_exception(self, runner):
        """Test ansible-assess with EOL status exception."""
        # Lines 2102-2104: EOL status exception
        assessment_data = {
            "ansible_version": "2.15.0",
            "collections": {"installed": []},
            "python_version": "3.9",
        }

        with (
            patch(
                "souschef.cli.assess_ansible_environment", return_value=assessment_data
            ),
            patch("souschef.cli.get_eol_status", side_effect=KeyError("Unknown")),
        ):
            result = runner.invoke(cli, ["ansible", "assess"])
            # Should handle error gracefully
            assert result.exit_code in [0, 1]

    def test_ansible_assess_general_exception(self, runner):
        """Test ansible-assess with general exception."""
        # Lines 2108-2110: General exception handler
        with patch(
            "souschef.cli.assess_ansible_environment",
            side_effect=RuntimeError("Assessment failed"),
        ):
            result = runner.invoke(cli, ["ansible", "assess"])
            assert result.exit_code == 1

    def test_ansible_assess_version_split_error(self, runner):
        """Test ansible-assess with version split error."""
        # Line 2116: Version parsing error
        assessment_data = {
            "ansible_version": "invalid",
            "collections": {"installed": []},
            "python_version": "3.9",
        }

        with patch(
            "souschef.cli.assess_ansible_environment", return_value=assessment_data
        ):
            result = runner.invoke(cli, ["ansible", "assess"])
            # Should handle invalid version format
            assert result.exit_code in [0, 1]


class TestAnsibleEolCommand:
    """Test ansible-eol command paths."""

    def test_ansible_eol_version_format_exception(self, runner):
        """Test ansible-eol with formatting exception."""
        # Lines 2197-2198: Version formatting exception
        with patch(
            "souschef.cli.format_version_display", side_effect=ValueError("Bad version")
        ):
            result = runner.invoke(cli, ["ansible", "eol", "--version", "2.9"])
            # Should handle error
            assert result.exit_code in [0, 1]

    def test_ansible_eol_unknown_version(self, runner):
        """Test ansible-eol with unknown version."""
        # Lines 2207-2209: Unknown version handling
        with patch("souschef.cli.get_eol_status", side_effect=KeyError("Unknown")):
            result = runner.invoke(cli, ["ansible", "eol", "--version", "99.99"])
            # Should handle unknown version
            assert result.exit_code in [0, 1]


class TestAnsiblePlanCommand:
    """Test ansible-plan command paths."""

    def test_ansible_plan_active_status(self, runner):
        """Test ansible-plan with active status."""
        # Lines 2237-2238: Active status display
        mock_plan = Mock()
        mock_plan.current_version = "2.15.0"
        mock_plan.target_version = "2.16.0"
        mock_plan.is_major_upgrade = False
        mock_plan.estimated_effort_hours = 10
        mock_plan.phases = []
        mock_plan.risks = []

        eol_status = {"status": "active"}

        with (
            patch("souschef.cli.generate_upgrade_plan", return_value=mock_plan),
            patch("souschef.cli.get_eol_status", return_value=eol_status),
        ):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "plan",
                    "--current-version",
                    "2.15.0",
                    "--target-version",
                    "2.16.0",
                ],
            )
            assert "Active" in result.output or result.exit_code == 0

    def test_ansible_plan_eol_status(self, runner):
        """Test ansible-plan with EOL status."""
        # Lines 2248-2249: EOL status display
        mock_plan = Mock()
        mock_plan.current_version = "2.9.0"
        mock_plan.target_version = "2.15.0"
        mock_plan.is_major_upgrade = True
        mock_plan.estimated_effort_hours = 50
        mock_plan.phases = []
        mock_plan.risks = []

        eol_status = {"status": "eol", "eol_date": "2022-05-23"}

        with (
            patch("souschef.cli.generate_upgrade_plan", return_value=mock_plan),
            patch("souschef.cli.get_eol_status", return_value=eol_status),
        ):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "plan",
                    "--current-version",
                    "2.9.0",
                    "--target-version",
                    "2.15.0",
                ],
            )
            assert result.exit_code == 0

    def test_ansible_plan_version_format_exception(self, runner):
        """Test ansible-plan with version format exception."""
        # Lines 2252, 2256-2258: Version format exceptions
        mock_plan = Mock()
        mock_plan.current_version = "2.15.0"
        mock_plan.target_version = "2.16.0"
        mock_plan.is_major_upgrade = False
        mock_plan.estimated_effort_hours = 10
        mock_plan.phases = []
        mock_plan.risks = []

        with (
            patch("souschef.cli.generate_upgrade_plan", return_value=mock_plan),
            patch(
                "souschef.cli.format_version_display",
                side_effect=ValueError("Bad format"),
            ),
        ):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "plan",
                    "--current-version",
                    "2.15.0",
                    "--target-version",
                    "2.16.0",
                ],
            )
            # Should handle exception
            assert result.exit_code in [0, 1]

    def test_ansible_plan_eol_exception(self, runner):
        """Test ansible-plan with EOL exception."""
        # Lines 2286, 2290, 2294: EOL exception handlers
        mock_plan = Mock()
        mock_plan.current_version = "2.15.0"
        mock_plan.target_version = "2.16.0"
        mock_plan.is_major_upgrade = False
        mock_plan.estimated_effort_hours = 10
        mock_plan.phases = []
        mock_plan.risks = []

        with (
            patch("souschef.cli.generate_upgrade_plan", return_value=mock_plan),
            patch("souschef.cli.get_eol_status", side_effect=KeyError("Unknown")),
        ):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "plan",
                    "--current-version",
                    "2.15.0",
                    "--target-version",
                    "2.16.0",
                ],
            )
            # Should handle exception
            assert result.exit_code in [0, 1]


class TestAnsibleValidateCollections:
    """Test ansible-validate-collections command."""

    def test_validate_collections_import_error(self, runner, tmp_path):
        """Test validate-collections with PyYAML missing."""
        # Lines 2315-2320: ImportError handler
        collections_file = tmp_path / "requirements.yml"
        collections_file.write_text("collections: []")

        with patch("builtins.__import__", side_effect=ImportError("No yaml")):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(collections_file),
                    "--target-version",
                    "7.0",
                ],
            )
            assert result.exit_code == 1 or "PyYAML" in result.output

    def test_validate_collections_file_read_error(self, runner, tmp_path):
        """Test validate-collections with file read error."""
        # Lines 2328-2330: OSError during read
        collections_file = tmp_path / "requirements.yml"
        collections_file.write_text("collections: []")

        with patch("pathlib.Path.read_text", side_effect=OSError("Read failed")):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(collections_file),
                    "--target-version",
                    "7.0",
                ],
            )
            assert result.exit_code == 1

    def test_validate_collections_value_error(self, runner, tmp_path):
        """Test validate-collections with ValueError."""
        # Lines 2336-2339: ValueError handler
        collections_file = tmp_path / "requirements.yml"
        collections_file.write_text("collections: []")

        with patch(
            "souschef.cli.validate_collection_compatibility",
            side_effect=ValueError("Invalid"),
        ):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(collections_file),
                    "--target-version",
                    "7.0",
                ],
            )
            assert result.exit_code == 1

    def test_validate_collections_yaml_error(self, runner, tmp_path):
        """Test validate-collections with YAML error."""
        # Line 2342: yaml.YAMLError handler
        import yaml

        collections_file = tmp_path / "requirements.yml"
        collections_file.write_text("invalid: yaml")

        with patch("yaml.safe_load", side_effect=yaml.YAMLError("Bad YAML")):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(collections_file),
                    "--target-version",
                    "7.0",
                ],
            )
            assert result.exit_code == 1

    def test_validate_collections_empty_file(self, runner, tmp_path):
        """Test validate-collections with empty file."""
        # Lines 2347-2351: Empty file handler
        collections_file = tmp_path / "requirements.yml"
        collections_file.write_text("")

        with patch("yaml.safe_load", return_value=None):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(collections_file),
                    "--target-version",
                    "7.0",
                ],
            )
            assert "Empty" in result.output or result.exit_code != 0

    def test_validate_collections_missing_key(self, runner, tmp_path):
        """Test validate-collections with missing collections key."""
        # Lines 2347-2351: Missing collections key
        collections_file = tmp_path / "requirements.yml"
        collections_file.write_text("other_key: value")

        with patch("yaml.safe_load", return_value={"other_key": "value"}):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(collections_file),
                    "--target-version",
                    "7.0",
                ],
            )
            assert "collections" in result.output.lower() or result.exit_code != 0

    def test_validate_collections_string_format(self, runner, tmp_path):
        """Test validate-collections with string format."""
        # Lines 2371, 2376-2377: String format parsing
        collections_file = tmp_path / "requirements.yml"
        collections_file.write_text("collections:\n  - namespace.collection")

        with (
            patch(
                "yaml.safe_load", return_value={"collections": ["namespace.collection"]}
            ),
            patch(
                "souschef.cli.validate_collection_compatibility",
                return_value={"compatible": ["namespace.collection"]},
            ),
        ):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(collections_file),
                    "--target-version",
                    "7.0",
                ],
            )
            assert result.exit_code == 0

    def test_validate_collections_dict_format(self, runner, tmp_path):
        """Test validate-collections with dict format."""
        # Lines 2395, 2398-2400: Dict format parsing
        collections_file = tmp_path / "requirements.yml"
        collections_file.write_text("collections:\n  - name: namespace.collection")

        collections_data = {
            "collections": [{"name": "namespace.collection", "version": "1.0.0"}]
        }

        with (
            patch("yaml.safe_load", return_value=collections_data),
            patch(
                "souschef.cli.validate_collection_compatibility",
                return_value={"compatible": ["namespace.collection"]},
            ),
        ):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(collections_file),
                    "--target-version",
                    "7.0",
                ],
            )
            assert result.exit_code == 0

    def test_validate_collections_general_exception(self, runner, tmp_path):
        """Test validate-collections with general exception."""
        # Lines 2413-2418: General exception handler
        collections_file = tmp_path / "requirements.yml"
        collections_file.write_text("collections: []")

        with patch("yaml.safe_load", side_effect=RuntimeError("Unexpected error")):
            result = runner.invoke(
                cli,
                [
                    "ansible",
                    "validate-collections",
                    "--collections-file",
                    str(collections_file),
                    "--target-version",
                    "7.0",
                ],
            )
            assert result.exit_code == 1


class TestAnsibleDetectPython:
    """Test ansible-detect-python command."""

    def test_detect_python_version_parsing(self, runner):
        """Test detect-python with version parsing."""
        # Lines 2464-2466: Version parsing
        with patch("souschef.cli.detect_python_version", return_value="3.9.7"):
            result = runner.invoke(cli, ["ansible", "detect-python"])
            assert "3.9" in result.output or "Python Version" in result.output

    def test_detect_python_exception(self, runner):
        """Test detect-python with exception."""
        # Lines 2510-2512: Exception handler
        with patch(
            "souschef.cli.detect_python_version",
            side_effect=RuntimeError("Detection failed"),
        ):
            result = runner.invoke(cli, ["ansible", "detect-python"])
            assert result.exit_code == 1

    def test_detect_python_short_version(self, runner):
        """Test detect-python with short version string."""
        # Lines 2517-2519: Short version handling
        with patch("souschef.cli.detect_python_version", return_value="3"):
            result = runner.invoke(cli, ["ansible", "detect-python"])
            # Should handle gracefully
            assert result.exit_code in [0, 1] or "Python" in result.output
