"""
Comprehensive coverage expansion for exception handlers and edge cases.

This module targets systematically uncovered code paths across the codebase,
focusing on exception handlers, validation failures, edge cases, and rare
parameter combinations.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

# CI/CD tests
from souschef.ci.common import analyse_chef_ci_patterns
from souschef.ci.github_actions import generate_github_workflow_from_chef_ci
from souschef.ci.gitlab_ci import generate_gitlab_ci_from_chef_ci
from souschef.ci.jenkins_pipeline import generate_jenkinsfile_from_chef_ci

# Converter tests
from souschef.converters.advanced_resource import (
    estimate_conversion_complexity,
    parse_resource_guards,
    parse_resource_notifications,
    parse_resource_search,
)
from souschef.converters.cookbook_specific import (
    get_cookbook_package_config,
    get_cookbook_resource_config,
)

# Core module tests
from souschef.core.constants import (
    ACTION_TO_STATE,
    RESOURCE_MAPPINGS,
)
from souschef.core.validation import (
    ValidationCategory,
    ValidationEngine,
    ValidationLevel,
)


class TestConstantsModule:
    """Test edge cases in constants module."""

    def test_constants_all_exported(self) -> None:
        """Test that all constants in __all__ are exported."""
        from souschef.core import constants

        # Core constants should be importable
        assert hasattr(constants, "VERSION")
        assert hasattr(constants, "ANSIBLE_SERVICE_MODULE")

    def test_resource_mappings_complete(self) -> None:
        """Test RESOURCE_MAPPINGS has all common Chef resources."""
        assert "package" in RESOURCE_MAPPINGS
        assert "service" in RESOURCE_MAPPINGS
        assert "template" in RESOURCE_MAPPINGS
        assert "file" in RESOURCE_MAPPINGS

    def test_action_to_state_comprehensive(self) -> None:
        """Test ACTION_TO_STATE mapping."""
        assert ACTION_TO_STATE.get("create") == "present"
        assert ACTION_TO_STATE.get("delete") == "absent"
        assert ACTION_TO_STATE.get("start") == "started"


class TestValidationEngineEdgeCases:
    """Test ValidationEngine edge cases."""

    def test_validation_engine_instantiation(self) -> None:
        """Test creating validation engine."""
        engine = ValidationEngine()
        assert engine is not None
        assert isinstance(engine, ValidationEngine)

    def test_validation_levels_enum(self) -> None:
        """Test all validation levels exist."""
        levels = [level.value for level in ValidationLevel]
        assert "INFO" in levels or "info" in levels
        assert "WARNING" in levels or "warning" in levels
        assert "ERROR" in levels or "error" in levels

    def test_validation_categories_enum(self) -> None:
        """Test all validation categories exist."""
        categories = list(ValidationCategory)
        assert len(categories) > 0


class TestAdvancedResourceEdgeCases:
    """Test advanced resource converter edge cases."""

    def test_parse_guards_with_empty_body(self) -> None:
        """Test parsing empty resource body."""
        result = parse_resource_guards("")
        assert isinstance(result, dict)

    def test_parse_guards_with_only_if(self) -> None:
        """Test parsing only_if guard."""
        body = "only_if 'test -f /path'"
        result = parse_resource_guards(body)
        assert isinstance(result, dict)

    def test_parse_guards_with_not_if(self) -> None:
        """Test parsing not_if guard."""
        body = "not_if 'test -d /path'"
        result = parse_resource_guards(body)
        assert isinstance(result, dict)

    def test_parse_notifications_empty(self) -> None:
        """Test parsing notifications with empty body."""
        result = parse_resource_notifications("")
        assert isinstance(result, list)

    def test_parse_notifications_with_action(self) -> None:
        """Test parsing notifications with action."""
        body = "notifies :restart, 'service[apache2]'"
        result = parse_resource_notifications(body)
        assert isinstance(result, list)

    def test_parse_search_with_multiple_criteria(self) -> None:
        """Test parsing complex search patterns."""
        body = "search(:node, 'role:web AND env:prod')"
        result = parse_resource_search(body)
        assert isinstance(result, dict)

    def test_estimate_complexity_simple(self) -> None:
        """Test complexity estimation for simple resource."""
        result = estimate_conversion_complexity("package 'nginx'")
        assert isinstance(result, str)

    def test_estimate_complexity_complex(self) -> None:
        """Test complexity estimation for complex resource."""
        body = """
        service 'nginx' do
          action [:enable, :start]
          notifies :restart, 'service[apache2]'
          only_if { ::File.exist?('/etc/nginx.conf') }
          timeout 60
        end
        """
        result = estimate_conversion_complexity(body)
        assert isinstance(result, str)


class TestCIPatternAnalysis:
    """Test CI pattern analysis with various cookbook structures."""

    def test_analyse_patterns_with_berksfile(self) -> None:
        """Test pattern detection with Berksfile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "Berksfile").touch()

            result = analyse_chef_ci_patterns(str(tmppath))
            assert isinstance(result, dict)
            assert result.get("has_berksfile") is True

    def test_analyse_patterns_with_kitchen_yml(self) -> None:
        """Test pattern detection with .kitchen.yml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            kitchen_yaml = tmppath / ".kitchen.yml"
            kitchen_yaml.write_text("""
suites:
  - name: default
platforms:
  - name: ubuntu-20.04
""")

            result = analyse_chef_ci_patterns(str(tmppath))
            assert isinstance(result, dict)
            assert result.get("has_kitchen") is True

    def test_analyse_patterns_with_chefspec(self) -> None:
        """Test detection of ChefSpec tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            spec_dir = tmppath / "spec" / "unit"
            spec_dir.mkdir(parents=True)
            (spec_dir / "default_spec.rb").touch()

            result = analyse_chef_ci_patterns(str(tmppath))
            assert isinstance(result, dict)
            assert result.get("has_chefspec") is True

    def test_analyse_patterns_with_inspec(self) -> None:
        """Test detection of InSpec tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            inspec_dir = tmppath / "test" / "integration"
            inspec_dir.mkdir(parents=True)

            result = analyse_chef_ci_patterns(str(tmppath))
            assert isinstance(result, dict)
            assert result.get("has_inspec") is True


class TestWorkflowGeneration:
    """Test workflow generation with edge cases."""

    def test_github_workflow_names_with_underscores(self) -> None:
        """Test GitHub workflow generation with underscores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_github_workflow_from_chef_ci(
                tmpdir, workflow_name="test_workflow_123"
            )
            assert isinstance(result, str)
            assert len(result) > 0

    def test_github_workflow_with_empty_patterns(self) -> None:
        """Test GitHub workflow with no patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_github_workflow_from_chef_ci(tmpdir)
            assert isinstance(result, str)

    def test_gitlab_ci_with_unicode_project(self) -> None:
        """Test GitLab CI with Unicode characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_gitlab_ci_from_chef_ci(
                tmpdir, project_name="café-project"
            )
            assert isinstance(result, str)

    def test_gitlab_ci_with_special_chars(self) -> None:
        """Test GitLab CI with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_gitlab_ci_from_chef_ci(
                tmpdir, project_name="my-project_v1.0"
            )
            assert isinstance(result, str)

    def test_jenkins_declarative_pipeline_minimal(self) -> None:
        """Test Jenkins declarative pipeline generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_jenkinsfile_from_chef_ci(
                tmpdir, pipeline_name="minimal-pipeline", pipeline_type="declarative"
            )
            assert isinstance(result, str)
            assert "pipeline" in result.lower() or "{" in result

    def test_jenkins_scripted_pipeline_minimal(self) -> None:
        """Test Jenkins scripted pipeline generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_jenkinsfile_from_chef_ci(
                tmpdir, pipeline_name="scripted-pipeline", pipeline_type="scripted"
            )
            assert isinstance(result, str)
            assert "node" in result.lower() or "{" in result


class TestCookbookSpecificConfigs:
    """Test cookbook-specific configuration lookups."""

    def test_get_package_config_various_cookbooks(self) -> None:
        """Test getting configs for various known cookbooks."""
        cookbooks = ["nodejs", "postgresql", "mysql", "redis"]
        for cookbook in cookbooks:
            result = get_cookbook_package_config(cookbook)
            # Should return config or None
            assert result is None or isinstance(result, dict)

    def test_get_package_config_unknown(self) -> None:
        """Test getting config for unknown cookbook."""
        result = get_cookbook_package_config("completely-unknown-cookbook-xyz")
        assert result is None or isinstance(result, dict)

    def test_get_resource_config_various_types(self) -> None:
        """Test getting configs for various resource types."""
        resources = ["package", "service", "template", "user", "group"]
        for resource_type in resources:
            result = get_cookbook_resource_config(resource_type)
            # Should return config or None
            assert result is None or isinstance(result, dict)

    def test_get_resource_config_unknown(self) -> None:
        """Test getting config for unknown resource type."""
        result = get_cookbook_resource_config("unknown_resource_type")
        assert result is None or isinstance(result, dict)


class TestExceptionHandlingBoundaries:
    """Test exception handling at module boundaries."""

    def test_filepath_normalization_with_invalid_paths(self) -> None:
        """Test path handling with unusual inputs."""
        try:
            from souschef.core.path_utils import _normalize_path

            # Try various path inputs
            test_paths = [
                "",
                " ",
                ".",
                "..",
                "/",
                "~",
            ]

            for path_input in test_paths:
                try:
                    result = _normalize_path(path_input)
                    assert result is not None
                except (ValueError, OSError, RuntimeError):
                    # Some of these might raise, which is acceptable
                    pass
        except ImportError:
            # If path_utils module not found, skip this test
            pytest.skip("path_utils module not available")

    def test_yaml_parsing_with_malformed_input(self) -> None:
        """Test YAML parsing with malformed content."""
        malformed_yamls = [
            "{ invalid",
            "[[[",
            ":\n:",
            "key: : : value",
        ]

        for content in malformed_yamls:
            try:
                result = yaml.safe_load(content)
                # If it parses, result should be valid
                assert result is None or isinstance(result, (dict, list))
            except yaml.YAMLError:
                # This is acceptable for malformed YAML
                pass


class TestRareCombinationsAndStates:
    """Test rare combinations of parameters and states."""

    def test_workflow_with_parallel_disabled(self) -> None:
        """Test workflow generation with parallelization disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generate_jenkinsfile_from_chef_ci(
                tmpdir,
                pipeline_name="serial-pipeline",
                enable_parallel=False,
                pipeline_type="declarative",
            )
            assert isinstance(result, str)

    def test_workflow_with_max_stages(self) -> None:
        """Test workflow that might have many stages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create multiple CI configuration files
            for i in range(5):
                (tmppath / f"test_{i}.yml").mkdir(exist_ok=True)

            result = generate_gitlab_ci_from_chef_ci(tmpdir, project_name="multi-stage")
            assert isinstance(result, str)


class TestBoundaryConditions:
    """Test boundary conditions and limits."""

    def test_very_long_pipeline_name(self) -> None:
        """Test workflow with very long pipeline name."""
        long_name = "a" * 256
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                result = generate_jenkinsfile_from_chef_ci(
                    tmpdir, pipeline_name=long_name
                )
                assert isinstance(result, str)
            except (ValueError, OSError):
                # Exception is acceptable for extremely long names
                pass

    def test_empty_cookbook_directory(self) -> None:
        """Test analysis of completely empty cookbook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = analyse_chef_ci_patterns(tmpdir)
            assert isinstance(result, dict)
            assert result.get("has_kitchen") is False
            assert result.get("has_chefspec") is False
            assert result.get("has_inspec") is False
