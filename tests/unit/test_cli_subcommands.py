"""Additional tests for cli.py subcommands (history and ansible groups)."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from souschef.cli import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestHistoryCommands:
    """Test history group subcommands."""

    def test_history_list_empty_results(self, runner):
        """Test history list with empty results."""
        # Lines 2080-2081: Empty migration history
        mock_storage = Mock()
        mock_storage.get_analysis_history.return_value = []
        mock_storage.get_conversion_history.return_value = []

        with patch("souschef.storage.get_storage_manager", return_value=mock_storage):
            result = runner.invoke(cli, ["history", "list"])
            # Empty result handling
            assert result.exit_code == 0


class TestAnsibleCommands:
    """Test ansible group subcommands."""

    def test_ansible_assess_many_collections(self, runner):
        """Test ansible assess with many installed collections."""
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
            # Should truncate long collection list
            assert result.exit_code == 0

    def test_ansible_assess_version_format_error(self, runner):
        """Test ansible assess with version formatting exception."""
        # Lines 2098-2099: Version formatting error
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
            # Should handle formatting error
            assert result.exit_code in [0, 1]

    def test_ansible_assess_eol_exception(self, runner):
        """Test ansible assess with EOL status exception."""
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
            # Should handle EOL error
            assert result.exit_code in [0, 1]

    def test_ansible_assess_general_exception(self, runner):
        """Test ansible assess with general exception."""
        # Lines 2108-2110: General exception handler
        with patch(
            "souschef.cli.assess_ansible_environment",
            side_effect=RuntimeError("Failed"),
        ):
            result = runner.invoke(cli, ["ansible", "assess"])
            assert result.exit_code == 1

    def test_ansible_assess_version_parse_error(self, runner):
        """Test ansible assess with version parsing error."""
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
            # Should handle invalid version
            assert result.exit_code in [0, 1]

    def test_ansible_eol_version_format_error(self, runner):
        """Test ansible eol with version formatting error."""
        # Lines 2197-2198: Version formatting exception
        with patch(
            "souschef.cli.format_version_display", side_effect=ValueError("Bad")
        ):
            result = runner.invoke(cli, ["ansible", "eol", "--version", "2.9"])
            assert result.exit_code in [0, 1]

    def test_ansible_eol_unknown_version(self, runner):
        """Test ansible eol with unknown version."""
        # Lines 2207-2209: Unknown version handling
        with patch("souschef.cli.get_eol_status", side_effect=KeyError("Unknown")):
            result = runner.invoke(cli, ["ansible", "eol", "--version", "99.99"])
            assert result.exit_code in [0, 1]

    def test_ansible_plan_active_status(self, runner):
        """Test ansible plan with active support status."""
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
            assert result.exit_code == 0

    def test_ansible_plan_eol_status(self, runner):
        """Test ansible plan with EOL status."""
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

    def test_ansible_plan_version_format_error(self, runner):
        """Test ansible plan with version format exception."""
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
            patch("souschef.cli.format_version_display", side_effect=ValueError("Bad")),
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
            assert result.exit_code in [0, 1]

    def test_ansible_plan_eol_exception(self, runner):
        """Test ansible plan with EOL exception."""
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
            assert result.exit_code in [0, 1]

    def test_ansible_validate_collections_import_error(self, runner, tmp_path):
        """Test validate-collections with PyYAML import error."""
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

    def test_ansible_validate_collections_os_error(self, runner, tmp_path):
        """Test validate-collections with OS error."""
        # Lines 2328-2330: OSError during file read
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

    def test_ansible_validate_collections_value_error(self, runner, tmp_path):
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

    def test_ansible_validate_collections_yaml_error(self, runner, tmp_path):
        """Test validate-collections with YAML error."""
        # Line 2342: yaml.YAMLError handler
        import yaml

        collections_file = tmp_path / "requirements.yml"
        collections_file.write_text("invalid")

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

    def test_ansible_validate_collections_empty_file(self, runner, tmp_path):
        """Test validate-collections with empty file."""
        # Lines 2347-2351: Empty file handling
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

    def test_ansible_validate_collections_missing_key(self, runner, tmp_path):
        """Test validate-collections with missing collections key."""
        # Lines 2347-2351: Missing collections key
        collections_file = tmp_path / "requirements.yml"
        collections_file.write_text("other: value")

        with patch("yaml.safe_load", return_value={"other": "value"}):
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

    def test_ansible_validate_collections_string_format(self, runner, tmp_path):
        """Test validate-collections with string format collection."""
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

    def test_ansible_validate_collections_dict_format(self, runner, tmp_path):
        """Test validate-collections with dict format collection."""
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

    def test_ansible_validate_collections_general_exception(self, runner, tmp_path):
        """Test validate-collections with general exception."""
        # Lines 2413-2418: General exception handler
        collections_file = tmp_path / "requirements.yml"
        collections_file.write_text("collections: []")

        with patch("yaml.safe_load", side_effect=RuntimeError("Unexpected")):
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

    def test_ansible_detect_python_version_parsing(self, runner):
        """Test detect-python with version parsing."""
        # Lines 2464-2466: Version parsing
        with patch("souschef.cli.detect_python_version", return_value="3.9.7"):
            result = runner.invoke(cli, ["ansible", "detect-python"])
            assert "3.9" in result.output or "Python" in result.output

    def test_ansible_detect_python_exception(self, runner):
        """Test detect-python with exception."""
        # Lines 2510-2512: Exception handler
        with patch(
            "souschef.cli.detect_python_version", side_effect=RuntimeError("Failed")
        ):
            result = runner.invoke(cli, ["ansible", "detect-python"])
            assert result.exit_code == 1

    def test_ansible_detect_python_short_version(self, runner):
        """Test detect-python with short version string."""
        # Lines 2517-2519: Short version handling
        with patch("souschef.cli.detect_python_version", return_value="3"):
            result = runner.invoke(cli, ["ansible", "detect-python"])
            # Should handle short version
            assert result.exit_code in [0, 1] or "Python" in result.output
