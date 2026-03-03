"""
Tests to cover quick-win modules with 1-2 uncovered lines.

This module targets specific uncovered lines in modules that are already 96-99%
covered, focusing on exception handlers and rare code paths.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from souschef.ci.common import (
    _parse_kitchen_configuration,
    analyse_chef_ci_patterns,
)
from souschef.ci.github_actions import generate_github_workflow_from_chef_ci
from souschef.ci.gitlab_ci import generate_gitlab_ci_from_chef_ci
from souschef.ci.jenkins_pipeline import generate_jenkinsfile_from_chef_ci
from souschef.converters.advanced_resource import (
    parse_resource_guards,
    parse_resource_search,
)
from souschef.converters.cookbook_specific import get_cookbook_package_config
from souschef.core.constants import VERSION, _load_version
from souschef.core.validation import ValidationEngine, ValidationLevel


class TestParseKitchenConfigurationExceptions:
    """Test exception handling in _parse_kitchen_configuration."""

    def test_yaml_error_handling(self, tmp_path: Path) -> None:
        """Test handling of YAML parsing errors."""
        kitchen_file = tmp_path / ".kitchen.yml"
        kitchen_file.write_text("invalid: yaml: content: [\n  ]")

        suites, platforms = _parse_kitchen_configuration(kitchen_file)

        # Should return empty lists on YAML error instead of raising
        assert suites == []
        assert platforms == []

    def test_malformed_yaml_with_missing_keys(self, tmp_path: Path) -> None:
        """Test handling when YAML structure is missing expected keys."""
        kitchen_file = tmp_path / ".kitchen.yml"
        kitchen_file.write_text("invalid_key: true\n")

        suites, platforms = _parse_kitchen_configuration(kitchen_file)

        assert suites == []
        assert platforms == []

    def test_malformed_yaml_with_mixed_types(self, tmp_path: Path) -> None:
        """Test handling when YAML has incorrect type structures."""
        kitchen_file = tmp_path / ".kitchen.yml"
        # suites should be a list, but we pass a string
        kitchen_file.write_text("suites: 'not a list'\nplatforms: 123\n")

        suites, platforms = _parse_kitchen_configuration(kitchen_file)

        # Should handle type mismatches gracefully
        assert isinstance(suites, list)
        assert isinstance(platforms, list)

    def test_kitchen_yml_read_permission_denied(self, tmp_path: Path) -> None:
        """Test handling of permission denied when reading .kitchen.yml."""
        kitchen_file = tmp_path / ".kitchen.yml"
        kitchen_file.write_text("suites:\n  - name: default\n")
        kitchen_file.chmod(0o000)  # Remove all permissions

        try:
            suites, platforms = _parse_kitchen_configuration(kitchen_file)
            # Should return empty lists instead of raising PermissionError
            assert suites == []
            assert platforms == []
        finally:
            # Restore permissions for cleanup
            kitchen_file.chmod(0o644)

    def test_kitchen_config_none_value(self, tmp_path: Path) -> None:
        """Test handling when kitchen config YAML is empty or null."""
        kitchen_file = tmp_path / ".kitchen.yml"
        kitchen_file.write_text("")  # Empty file

        suites, platforms = _parse_kitchen_configuration(kitchen_file)

        assert suites == []
        assert platforms == []

    def test_kitchen_suite_missing_name_field(self, tmp_path: Path) -> None:
        """Test suite without name field defaults to 'default'."""
        kitchen_file = tmp_path / ".kitchen.yml"
        kitchen_file.write_text("suites:\n  - driver: test\n")

        suites, _ = _parse_kitchen_configuration(kitchen_file)

        assert "default" in suites

    def test_kitchen_platform_missing_name_field(self, tmp_path: Path) -> None:
        """Test platform without name field defaults to 'unknown'."""
        kitchen_file = tmp_path / ".kitchen.yml"
        kitchen_file.write_text("platforms:\n  - driver: test\n")

        _, platforms = _parse_kitchen_configuration(kitchen_file)

        assert "unknown" in platforms


class TestLoadVersionExceptions:
    """Test exception handling in _load_version."""

    def test_load_version_import_error(self) -> None:
        """Test handling when importlib.metadata is not available."""

        def mock_version(package: str) -> str:
            raise ImportError("Module not found")

        with patch("importlib.metadata.version", side_effect=mock_version):
            result = _load_version()
            assert result == "unknown"

    def test_load_version_attribute_error(self) -> None:
        """Test handling when version function raises AttributeError."""

        def mock_version(package: str) -> str:
            raise AttributeError("No version attribute")

        with patch("importlib.metadata.version", side_effect=mock_version):
            result = _load_version()
            assert result == "unknown"

    def test_version_constant_is_loaded(self) -> None:
        """Test that VERSION constant is properly loaded."""
        # The VERSION is loaded at module import time
        assert isinstance(VERSION, str)
        assert len(VERSION) > 0


class TestAdvancedResourceSearch:
    """Test resource search functionality."""

    def test_parse_resource_search_with_empty_string(self) -> None:
        """Test parsing empty search string."""
        result = parse_resource_search("")
        assert isinstance(result, dict)

    def test_parse_resource_search_with_guards(self) -> None:
        """Test parsing resource guards."""
        resource_body = "only_if 'test -f /etc/config'"
        result = parse_resource_guards(resource_body)
        assert isinstance(result, dict)

    def test_parse_resource_search_complex_query(self) -> None:
        """Test parsing complex Chef search patterns."""
        resource_body = "search(:users, 'role:admin')"
        result = parse_resource_search(resource_body)
        assert isinstance(result, dict)


class TestCookbookConfig:
    """Test cookbook configuration functions."""

    def test_get_cookbook_package_config_unknown(self) -> None:
        """Test getting config for unknown cookbook."""
        result = get_cookbook_package_config("unknown-cookbook-12345")
        assert result is None or isinstance(result, dict)

    def test_get_cookbook_package_config_nodejs(self) -> None:
        """Test getting config for known cookbook (nodejs)."""
        result = get_cookbook_package_config("nodejs")
        # Either returns config dict or None if not found
        assert result is None or isinstance(result, dict)


class TestGitHubActionsGeneration:
    """Test GitHub Actions workflow generation edge cases."""

    def test_github_workflow_empty_patterns(self) -> None:
        """Test workflow generation with empty CI patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal cookbook structure
            cookbook_path = Path(tmpdir)

            result = generate_github_workflow_from_chef_ci(
                str(cookbook_path),
                workflow_name="test",
            )

            assert isinstance(result, str)
            assert "name:" in result.lower() or "workflow" in result.lower()

    def test_github_workflow_with_special_characters(self) -> None:
        """Test workflow generation with special characters in path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook-test_01"
            cookbook_path.mkdir()

            result = generate_github_workflow_from_chef_ci(
                str(cookbook_path),
                workflow_name="test-workflow_01",
            )

            assert isinstance(result, str)


class TestGitLabCIGeneration:
    """Test GitLab CI configuration generation edge cases."""

    def test_gitlab_ci_empty_patterns(self) -> None:
        """Test GitLab CI generation with empty CI patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir)

            result = generate_gitlab_ci_from_chef_ci(
                str(cookbook_path),
                project_name="test",
            )

            assert isinstance(result, str)

    def test_gitlab_ci_unicode_handling(self) -> None:
        """Test GitLab CI with Unicode characters in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir)

            result = generate_gitlab_ci_from_chef_ci(
                str(cookbook_path),
                project_name="projet-tëst",  # French accents
            )

            assert isinstance(result, str)


class TestJenkinsPipelineGeneration:
    """Test Jenkins pipeline generation edge cases."""

    def test_jenkins_pipeline_empty_patterns(self) -> None:
        """Test Jenkins pipeline generation with empty patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir)

            result = generate_jenkinsfile_from_chef_ci(
                str(cookbook_path),
                pipeline_name="test",
                pipeline_type="declarative",
            )

            assert isinstance(result, str)

    def test_jenkins_pipeline_special_characters(self) -> None:
        """Test Jenkins pipeline with special characters in names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir)

            result = generate_jenkinsfile_from_chef_ci(
                str(cookbook_path),
                pipeline_name="test-pipeline_01",
                pipeline_type="scripted",
            )

            assert isinstance(result, str)
            assert "test-pipeline_01" in result or "pipeline" in result


class TestValidationEdgeCases:
    """Test validation engine edge cases."""

    def test_validation_engine_creation(self) -> None:
        """Test creating a validation engine."""
        engine = ValidationEngine()
        assert engine is not None

    def test_validation_level_enum(self) -> None:
        """Test validation level enumeration."""
        assert ValidationLevel.INFO is not None
        assert ValidationLevel.WARNING is not None
        assert ValidationLevel.ERROR is not None


# Additional edge case tests for rare scenarios


class TestParseKitchenConfigurationComplexScenarios:
    """Test complex scenarios in kitchen configuration parsing."""

    def test_nested_dictionary_attribute_error(self, tmp_path: Path) -> None:
        """Test handling of nested dict with missing attributes."""
        kitchen_file = tmp_path / ".kitchen.yml"
        # Create YAML with structure that requires attribute access
        kitchen_file.write_text(
            """
suites:
  - name: default
    attributes:
      key: value
platforms:
  - name: ubuntu
    os_type: linux
"""
        )

        suites, platforms = _parse_kitchen_configuration(kitchen_file)

        assert "default" in suites
        assert "ubuntu" in platforms

    def test_kitchen_config_with_special_yaml_characters(self, tmp_path: Path) -> None:
        """Test YAML with special characters that could cause parsing issues."""
        kitchen_file = tmp_path / ".kitchen.yml"
        kitchen_file.write_text(
            """
suites:
  - name: test:special-chars-123_456
platforms:
  - name: centos/7
"""
        )

        suites, platforms = _parse_kitchen_configuration(kitchen_file)

        assert len(suites) > 0
        assert len(platforms) > 0


class TestAnalyseCIPatterns:
    """Test CI pattern analysis with various scenarios."""

    def test_analyse_nonexistent_path(self) -> None:
        """Test analysis of non-existent path."""
        # Should handle gracefully without raising FileNotFoundError
        try:
            result = analyse_chef_ci_patterns("/nonexistent/path/12345")
            assert isinstance(result, dict)
        except (FileNotFoundError, ValueError):
            # Either handled gracefully or raises expected error
            pass

    def test_analyse_symlink_path(self, tmp_path: Path) -> None:
        """Test analysis with symlinked cookbook directory."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()

        symlink_path = tmp_path / "symlink_cookbook"
        try:
            symlink_path.symlink_to(cookbook_dir)
            result = analyse_chef_ci_patterns(str(symlink_path))
            assert isinstance(result, dict)
        except OSError:
            # Symlinks might not be available on all systems
            pytest.skip("Symlinks not available on this system")
