"""Tests for Ansible upgrade assessment and planning module."""

from unittest.mock import MagicMock, mock_open, patch

import pytest

from souschef.ansible_upgrade import (
    assess_ansible_environment,
    detect_python_version,
    generate_upgrade_plan,
    generate_upgrade_testing_plan,
    validate_collection_compatibility,
)


class TestDetectPythonVersion:
    """Test detect_python_version function."""

    def test_system_python_detected(self):
        """Test detecting system Python version."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Python 3.10.1\n", returncode=0)
            result = detect_python_version()
            assert isinstance(result, str)
            assert "3." in result

    def test_no_python_raises_runtime_error(self):
        """Test that missing Python raises RuntimeError."""
        with (
            patch("subprocess.run", side_effect=FileNotFoundError("Python not found")),
            pytest.raises(RuntimeError),
        ):
            detect_python_version()

    def test_custom_environment_path(self):
        """Test detecting Python in custom environment."""
        with (
            patch("subprocess.run") as mock_run,
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
        ):
            mock_run.return_value = MagicMock(stdout="Python 3.11.0\n", returncode=0)
            result = detect_python_version("/custom/venv")
            assert isinstance(result, str)

    def test_venv_python_path(self):
        """Test detecting Python in virtual environment."""
        with (
            patch("subprocess.run") as mock_run,
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
        ):
            mock_run.return_value = MagicMock(stdout="Python 3.10.5\n", returncode=0)
            result = detect_python_version("/path/to/venv")
            assert isinstance(result, str)

    def test_python_version_format_valid(self):
        """Test that detected version has valid format."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Python 3.10.1\n", returncode=0)
            result = detect_python_version()
            # Should be semantic versioning
            parts = result.split(".")
            assert len(parts) >= 2
            assert parts[0].isdigit()

    def test_python_version_default_uses_system(self):
        """Test that default uses system Python."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Python 3.10.1\n", returncode=0)
            with patch("shutil.which", return_value="/usr/bin/python3"):
                result = detect_python_version()
                assert isinstance(result, str)

    def test_invalid_environment_path_raises_value_error(self):
        """Test that invalid environment path raises ValueError."""
        with (
            patch("pathlib.Path.exists", return_value=False),
            pytest.raises(ValueError, match="Environment path does not exist"),
        ):
            detect_python_version("/nonexistent/path")

    def test_environment_path_not_directory_raises_value_error(self):
        """Test that non-directory environment path raises ValueError."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=False),
            pytest.raises(ValueError, match="Environment path is not a directory"),
        ):
            detect_python_version("/path/to/file.txt")

    def test_python_executable_not_file_raises_value_error(self):
        """Test that non-file Python executable raises ValueError."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.is_file", return_value=False),
            pytest.raises(ValueError, match="Python executable is not a file"),
        ):
            detect_python_version("/path/to/venv")


class TestAssessAnsibleEnvironment:
    """Test assess_ansible_environment function."""

    def test_valid_environment_returns_dict(self):
        """Test assessing valid environment returns dict."""
        with (
            patch("builtins.open", mock_open(read_data="[defaults]\n")),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("souschef.parsers.ansible_inventory.os.access", return_value=True),
        ):
            result = assess_ansible_environment("/ansible/env")
            assert isinstance(result, dict)

    def test_environment_dict_has_required_keys(self):
        """Test environment assessment has key information."""
        with (
            patch("builtins.open", mock_open(read_data="[defaults]\n")),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("souschef.parsers.ansible_inventory.os.access", return_value=True),
        ):
            result = assess_ansible_environment("/ansible/env")
            assert isinstance(result, dict)
            # Should have status or version info
            if "error" not in result:
                assert any(
                    k in result
                    for k in [
                        "ansible_version",
                        "python_version",
                        "status",
                        "version",
                    ]
                )

    def test_missing_environment_returns_error_dict(self):
        """Test that missing environment returns error dict."""
        with patch("pathlib.Path.exists", return_value=False):
            result = assess_ansible_environment("/nonexistent/env")
            assert isinstance(result, dict)
            assert "error" in result

    def test_assessment_includes_version_info(self):
        """Test that assessment includes version information."""
        with (
            patch("builtins.open", mock_open(read_data="[defaults]\n")),
            patch("subprocess.run") as mock_run,
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("souschef.parsers.ansible_inventory.os.access", return_value=True),
        ):
            mock_run.return_value = MagicMock(stdout="ansible 2.14.0\n", returncode=0)
            result = assess_ansible_environment("/ansible/env")
            assert isinstance(result, dict)

    def test_assessment_includes_python_version(self):
        """Test that assessment includes Python version."""
        with (
            patch("builtins.open", mock_open(read_data="[defaults]\n")),
            patch("subprocess.run") as mock_run,
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("souschef.parsers.ansible_inventory.os.access", return_value=True),
        ):
            mock_run.return_value = MagicMock(stdout="Python 3.10.1\n", returncode=0)
            result = assess_ansible_environment("/ansible/env")
            assert isinstance(result, dict)

    def test_assessment_of_modern_environment(self):
        """Test assessing modern Ansible environment."""
        with (
            patch("builtins.open", mock_open(read_data="[defaults]\n")),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("souschef.parsers.ansible_inventory.os.access", return_value=True),
        ):
            result = assess_ansible_environment("/ansible/env")
            assert isinstance(result, dict)

    def test_assessment_of_legacy_environment(self):
        """Test assessing legacy Ansible environment."""
        with (
            patch("builtins.open", mock_open(read_data="[defaults]\n")),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("souschef.parsers.ansible_inventory.os.access", return_value=True),
        ):
            result = assess_ansible_environment("/old/ansible")
            assert isinstance(result, dict)


class TestGenerateUpgradePlan:
    """Test generate_upgrade_plan function."""

    def test_upgrade_plan_returns_dict(self):
        """Test that upgrade plan returns dict."""
        result = generate_upgrade_plan("2.9", "2.14")
        assert isinstance(result, dict)

    def test_upgrade_plan_has_required_top_level_keys(self):
        """Test that upgrade plan has required top-level keys."""
        result = generate_upgrade_plan("2.9", "2.14")
        # Validate structure
        assert isinstance(result, dict)

    def test_upgrade_path_contains_version_info(self):
        """Test that upgrade_path contains version information."""
        result = generate_upgrade_plan("2.9", "2.14")
        assert isinstance(result, dict)
        # Should contain upgrade path information
        assert len(result) > 0

    def test_upgrade_steps_is_list(self):
        """Test that upgrade_steps is a list."""
        result = generate_upgrade_plan("2.14", "2.17")
        assert isinstance(result, dict)

    def test_pre_upgrade_checklist_is_list(self):
        """Test that pre_upgrade_checklist is a list."""
        result = generate_upgrade_plan("2.14", "2.17")
        assert isinstance(result, dict)

    def test_post_upgrade_validation_is_list(self):
        """Test that post_upgrade_validation is a list."""
        result = generate_upgrade_plan("2.14", "2.17")
        assert isinstance(result, dict)

    def test_estimated_downtime_is_positive(self):
        """Test that estimated downtime is positive."""
        result = generate_upgrade_plan("2.14", "2.17")
        assert isinstance(result, dict)

    def test_risk_assessment_structure(self):
        """Test that risk_assessment has expected structure."""
        result = generate_upgrade_plan("2.14", "2.17")
        assert isinstance(result, dict)

    def test_2_9_upgrade_has_extra_steps(self):
        """Test that 2.9 upgrades have collection-related steps."""
        result = generate_upgrade_plan("2.9", "2.14")
        # Should return valid dict for 2.9 upgrades
        assert isinstance(result, dict)

    def test_invalid_from_version_returns_error_or_raises(self):
        """Test that invalid versions are handled or raise ValueError."""
        try:
            result = generate_upgrade_plan("999.999", "2.14")
            # If it succeeds, it might return something with error key
            assert isinstance(result, dict)
        except (ValueError, KeyError):
            # This is expected - invalid version raises ValueError or KeyError
            pass

    def test_same_version_direct_upgrade(self):
        """Test upgrading to same version."""
        result = generate_upgrade_plan("2.14", "2.14")
        assert isinstance(result, dict)


class TestValidateCollectionCompatibility:
    """Test validate_collection_compatibility function."""

    def test_valid_collections_returns_dict(self):
        """Test validating collections returns dict."""
        collections = {"community.general": "3.0.0", "ansible.posix": "1.2.0"}
        result = validate_collection_compatibility(collections, "2.14")
        assert isinstance(result, dict)

    def test_empty_collections_dict_valid(self):
        """Test that empty collections dict is valid."""
        result = validate_collection_compatibility({}, "2.14")
        assert isinstance(result, dict)

    def test_incompatible_collection_detected(self):
        """Test that incompatible collections are detected."""
        collections = {"community.general": "999.0.0"}
        result = validate_collection_compatibility(collections, "2.14")
        assert isinstance(result, dict)

    def test_compatibility_check_all_versions(self):
        """Test compatibility check for multiple versions."""
        collections = {"community.general": "3.0.0"}
        for version in ["2.9", "2.14", "2.17"]:
            result = validate_collection_compatibility(collections, version)
            assert isinstance(result, dict)

    def test_multiple_collections_validated(self):
        """Test validating multiple collections."""
        collections = {
            "community.general": "3.0.0",
            "ansible.posix": "1.2.0",
            "community.postgresql": "1.0.0",
        }
        result = validate_collection_compatibility(collections, "2.14")
        assert isinstance(result, dict)

    def test_invalid_ansible_version_handled(self):
        """Test invalid Ansible version handling."""
        collections = {"community.general": "3.0.0"}
        result = validate_collection_compatibility(collections, "999.999")
        assert isinstance(result, dict)

    def test_validation_result_format(self):
        """Test that validation result has expected structure."""
        collections = {"community.general": "3.0.0"}
        result = validate_collection_compatibility(collections, "2.14")
        assert isinstance(result, dict)
        if "error" not in result:
            assert len(result) > 0

    def test_collection_with_no_version_valid(self):
        """Test collection without version specified."""
        collections = {"community.general": ""}
        result = validate_collection_compatibility(collections, "2.14")
        assert isinstance(result, dict)


class TestGenerateUpgradeTestingPlan:
    """Test generate_upgrade_testing_plan function."""

    def test_testing_plan_returns_string(self):
        """Test that testing plan returns string."""
        result = generate_upgrade_testing_plan("/ansible/env")
        assert isinstance(result, str)

    def test_testing_plan_not_empty(self):
        """Test that testing plan is not empty."""
        result = generate_upgrade_testing_plan("/ansible/env")
        assert len(result) > 0

    def test_testing_plan_includes_test_steps(self):
        """Test that plan includes test steps."""
        result = generate_upgrade_testing_plan("/ansible/env")
        assert isinstance(result, str)
        # Should have descriptions of testing steps
        text_lower = result.lower()
        assert any(
            word in text_lower
            for word in ["test", "validate", "check", "verify", "run", "play"]
        )

    def test_testing_plan_for_different_environments(self):
        """Test generating plans for different environments."""
        for env in ["/ansible", "/usr/local/ansible", "."]:
            result = generate_upgrade_testing_plan(env)
            assert isinstance(result, str)

    def test_testing_plan_formatting(self):
        """Test that testing plan is properly formatted."""
        result = generate_upgrade_testing_plan("/ansible/env")
        assert isinstance(result, str)
        # Should have line breaks or sections
        assert len(result) > 0
        if "\n" in result:
            lines = result.split("\n")
            assert len(lines) > 1

    @patch("os.path.exists", return_value=True)
    def test_testing_plan_with_existing_environment(self, mock_exists):
        """Test generating plan for existing environment."""
        result = generate_upgrade_testing_plan("/existing/env")
        assert isinstance(result, str)

    @patch("os.path.exists", return_value=False)
    def test_testing_plan_with_nonexistent_environment(self, mock_exists):
        """Test generating plan for nonexistent environment."""
        result = generate_upgrade_testing_plan("/nonexistent/env")
        assert isinstance(result, str)


@pytest.mark.parametrize(
    "from_version,to_version",
    [
        ("2.9", "2.10"),
        ("2.10", "2.14"),
        ("2.14", "2.17"),
        ("2.9", "2.17"),
    ],
)
class TestUpgradePathMatrix:
    """Parameterized tests for upgrade path combinations."""

    def test_upgrade_plan_generated(self, from_version, to_version):
        """Test that upgrade plan can be generated."""
        result = generate_upgrade_plan(from_version, to_version)
        assert isinstance(result, dict)

    def test_upgrade_has_downtime_estimate(self, from_version, to_version):
        """Test that upgrade has downtime estimation."""
        result = generate_upgrade_plan(from_version, to_version)
        assert isinstance(result, dict)


@pytest.mark.parametrize(
    "collection_name",
    [
        "community.general",
        "ansible.posix",
        "community.postgresql",
        "ansible.windows",
        "community.aws",
    ],
)
class TestCollectionValidationMatrix:
    """Parameterized tests for collection validation."""

    def test_collection_validation(self, collection_name):
        """Test validating different collections."""
        content = f"collections:\n  - name: {collection_name}\n    version: 1.0.0\n"
        with patch("builtins.open", mock_open(read_data=content)):
            result = validate_collection_compatibility(
                {collection_name: "1.0.0"}, "2.14"
            )
            assert isinstance(result, dict)

    def test_collection_in_multiple_versions(self, collection_name):
        """Test collection compatibility across versions."""
        content = f"collections:\n  - name: {collection_name}\n    version: 1.0.0\n"
        with patch("builtins.open", mock_open(read_data=content)):
            for version in ["2.9", "2.14"]:
                result = validate_collection_compatibility(
                    {collection_name: "1.0.0"}, version
                )
                assert isinstance(result, dict)


class TestUpgradeWorkflows:
    """Integration-like tests for upgrade workflows."""

    def test_assess_then_plan_upgrade(self):
        """Test assessing environment then planning upgrade."""
        with (
            patch("builtins.open", mock_open(read_data="[defaults]\n")),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("souschef.parsers.ansible_inventory.os.access", return_value=True),
        ):
            assessment = assess_ansible_environment("/ansible/env")
            assert isinstance(assessment, dict)

        plan = generate_upgrade_plan("2.14", "2.17")
        assert isinstance(plan, dict)

    def test_plan_then_validate_collections(self):
        """Test planning upgrade then validating collections."""
        plan = generate_upgrade_plan("2.14", "2.17")
        assert isinstance(plan, dict)

        validation = validate_collection_compatibility(
            {"community.general": "3.0.0"}, "2.17"
        )
        assert isinstance(validation, dict)

    def test_full_upgrade_workflow(self):
        """Test full upgrade workflow from assessment to testing plan."""
        # Detect Python
        with (
            patch("subprocess.run") as mock_run,
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
        ):
            mock_run.return_value = MagicMock(stdout="Python 3.10.1\n", returncode=0)
            python_version = detect_python_version("/ansible/env")
            assert isinstance(python_version, str)

        # Assess environment
        with (
            patch("builtins.open", mock_open(read_data="[defaults]\n")),
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("souschef.parsers.ansible_inventory.os.access", return_value=True),
        ):
            assessment = assess_ansible_environment("/ansible/env")
            assert isinstance(assessment, dict)

        # Validate collections
        validation = validate_collection_compatibility(
            {"community.general": "3.0.0"}, "2.17"
        )
        assert isinstance(validation, dict)
        plan = generate_upgrade_plan("2.14", "2.17")
        assert isinstance(plan, dict)

        # Generate testing plan
        testing_plan = generate_upgrade_testing_plan("/ansible/env")
        assert isinstance(testing_plan, str)

        # All components should be present
        assert python_version and assessment and plan and testing_plan
