"""
Comprehensive tests for SousChef MCP server tools with extensive coverage.

This test suite provides comprehensive coverage of MCP tool implementations
in server.py, focusing on parameter validation, error handling, and edge cases
across all tool categories.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from souschef.server import (
    _MAX_PATH_LENGTH,
    _MAX_PLAN_PATHS,
    _MAX_PLAN_PATHS_LENGTH,
    _convert_ruby_literal,
    _extract_attributes_block,
    _extract_cookbook_constraints,
    _flatten_environment_vars,
    _normalise_plan_paths,
    _normalise_workspace_path,
    _parse_chef_environment_content,
    _parse_quoted_key,
    _parse_simple_value,
    _skip_to_next_item,
    _skip_whitespace,
    _skip_whitespace_and_arrows,
    analyse_chef_databag_usage,
    analyse_chef_environment_usage,
    assess_chef_migration_complexity,
    convert_chef_databag_to_vars,
    convert_chef_environment_to_inventory_group,
    convert_habitat_to_dockerfile,
    convert_inspec_to_test,
    convert_resource_to_task,
    convert_template_with_ai,
    generate_ansible_vault_from_databags,
    generate_compose_from_habitat,
    generate_github_workflow_from_chef,
    generate_gitlab_ci_from_chef,
    generate_inspec_from_recipe,
    generate_inventory_from_chef_environments,
    generate_jenkinsfile_from_chef,
    list_directory,
    parse_attributes,
    parse_cookbook_metadata,
    parse_custom_resource,
    parse_habitat_plan,
    parse_inspec_profile,
    parse_recipe,
    parse_template,
    profile_cookbook_performance,
    profile_parsing_operation,
    read_cookbook_metadata,
    read_file,
)


class TestPathValidationAndNormalisation:
    """Tests for path validation and normalisation functions."""

    def test_validate_path_length_valid(self) -> None:
        """Test path validation with valid length path."""
        from souschef.server import _validate_path_length

        # Should not raise
        _validate_path_length("/valid/path", "Test path")

    def test_validate_path_length_exceeds_max(self) -> None:
        """Test path validation with path exceeding maximum length."""
        from souschef.server import _validate_path_length

        long_path = "/" + "a" * (_MAX_PATH_LENGTH + 1)
        with pytest.raises(ValueError, match="exceeds maximum length"):
            _validate_path_length(long_path, "Test path")

    def test_validate_plan_paths_valid(self) -> None:
        """Test plan paths validation with valid input."""
        from souschef.server import _validate_plan_paths

        # Should not raise
        _validate_plan_paths("/path/one, /path/two")

    def test_validate_plan_paths_exceeds_length(self) -> None:
        """Test plan paths validation with input exceeding length limit."""
        from souschef.server import _validate_plan_paths

        long_input = "," * (_MAX_PLAN_PATHS_LENGTH + 1)
        with pytest.raises(ValueError, match="exceed maximum length"):
            _validate_plan_paths(long_input)

    def test_validate_plan_paths_exceeds_count(self) -> None:
        """Test plan paths validation with too many paths."""
        from souschef.server import _validate_plan_paths

        paths = ", ".join([f"/path{i}" for i in range(_MAX_PLAN_PATHS + 1)])
        with pytest.raises(ValueError, match="Too many Habitat plan paths"):
            _validate_plan_paths(paths)

    def test_normalise_workspace_path_valid(self, tmp_path: Path) -> None:
        """Test normalising a valid workspace path."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            test_dir = tmp_path / "test"
            test_dir.mkdir()
            result = _normalise_workspace_path(str(test_dir), "Test path")
            assert isinstance(result, Path)
            assert result.exists()

    def test_normalise_workspace_path_invalid_length(self) -> None:
        """Test normalising path with excessive length."""
        long_path = "/" + "a" * (_MAX_PATH_LENGTH + 1)
        with pytest.raises(ValueError, match="exceeds maximum length"):
            _normalise_workspace_path(long_path, "Test path")

    def test_normalise_plan_paths_valid(self, tmp_path: Path) -> None:
        """Test normalising valid plan paths."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            path1 = tmp_path / "plan1.sh"
            path2 = tmp_path / "plan2.sh"
            path1.touch()
            path2.touch()
            result = _normalise_plan_paths(f"{str(path1)}, {str(path2)}")
            assert len(result) == 2
            assert all(isinstance(p, str) for p in result)


class TestRubyLiteralConversion:
    """Tests for Ruby literal value conversion."""

    def test_convert_ruby_literal_true(self) -> None:
        """Test converting Ruby true literal."""
        result = _convert_ruby_literal("true")
        assert result is True
        assert isinstance(result, bool)

    def test_convert_ruby_literal_false(self) -> None:
        """Test converting Ruby false literal."""
        result = _convert_ruby_literal("false")
        assert result is False
        assert isinstance(result, bool)

    def test_convert_ruby_literal_nil(self) -> None:
        """Test converting Ruby nil literal."""
        result = _convert_ruby_literal("nil")
        assert result is None

    def test_convert_ruby_literal_integer(self) -> None:
        """Test converting Ruby integer literal."""
        result = _convert_ruby_literal("42")
        assert result == 42
        assert isinstance(result, int)

    def test_convert_ruby_literal_integer_negative(self) -> None:
        """Test converting negative integer literal."""
        result = _convert_ruby_literal("-100")
        assert result == -100

    def test_convert_ruby_literal_float(self) -> None:
        """Test converting Ruby float literal."""
        result = _convert_ruby_literal("3.14")
        assert result == pytest.approx(3.14)
        assert isinstance(result, float)

    def test_convert_ruby_literal_scientific_notation(self) -> None:
        """Test converting scientific notation literal."""
        result = _convert_ruby_literal("1e10")
        assert result == pytest.approx(1e10)
        assert isinstance(result, float)

    def test_convert_ruby_literal_string(self) -> None:
        """Test converting unrecognised string literals."""
        result = _convert_ruby_literal("some_string")
        assert result == "some_string"
        assert isinstance(result, str)


class TestChefEnvironmentParsing:
    """Tests for Chef environment content parsing."""

    def test_parse_chef_environment_basic(self) -> None:
        """Test parsing basic Chef environment."""
        content = """
name "production"
description "Production environment"
"""
        result = _parse_chef_environment_content(content)
        assert result["name"] == "production"
        assert result["description"] == "Production environment"

    def test_parse_chef_environment_with_attributes(self) -> None:
        """Test parsing environment with default attributes."""
        content = """
name "staging"
default_attributes (
    {
        "app_version" => "1.0.0",
        "deploy_path" => "/opt/app"
    }
)
"""
        result = _parse_chef_environment_content(content)
        assert result["name"] == "staging"
        assert isinstance(result["default_attributes"], dict)

    def test_parse_chef_environment_cookbook_constraints(self) -> None:
        """Test parsing environment with cookbook constraints."""
        content = """
name "test"
cookbook "nginx", "5.0.0"
cookbook "mysql", "= 3.0.0"
"""
        result = _parse_chef_environment_content(content)
        assert "cookbook_versions" in result
        assert isinstance(result["cookbook_versions"], dict)

    def test_parse_chef_environment_empty(self) -> None:
        """Test parsing empty environment content."""
        result = _parse_chef_environment_content("")
        assert result["name"] == ""
        assert result["description"] == ""

    def test_extract_attributes_block_exists(self) -> None:
        """Test extracting attributes block when present."""
        content = """
default_attributes (
    {
        "key" => "value"
    }
)
"""
        result = _extract_attributes_block(content, "default_attributes")
        assert isinstance(result, dict)

    def test_extract_attributes_block_missing(self) -> None:
        """Test extracting attributes block when absent."""
        content = "name 'test'"
        result = _extract_attributes_block(content, "default_attributes")
        assert result == {}

    def test_extract_cookbook_constraints_multiple(self) -> None:
        """Test extracting multiple cookbook constraints."""
        content = """
cookbook "nginx", "5.0.0"
cookbook "mysql", "3.0.0"
cookbook "postgresql", "= 4.0.0"
"""
        result = _extract_cookbook_constraints(content)
        assert len(result) >= 2
        assert all(isinstance(v, str) for v in result.values())

    def test_flatten_environment_vars_basic(self) -> None:
        """Test flattening environment variables."""
        env_data = {
            "name": "prod",
            "description": "Production",
            "default_attributes": {"app_version": "1.0.0"},
            "override_attributes": {"debug": False},
            "cookbook_versions": {"nginx": "5.0.0"},
        }
        result = _flatten_environment_vars(env_data)
        assert result["environment_name"] == "prod"
        assert result["environment_description"] == "Production"
        assert "environment_overrides" in result or len(result) > 0


class TestHashParsing:
    """Tests for Ruby hash parsing functionality."""

    def test_parse_quoted_key_single_quotes(self) -> None:
        """Test parsing single-quoted key."""
        content = "'key' => value"
        key, idx = _parse_quoted_key(content, 0)
        assert key == "key"
        assert idx == 5

    def test_parse_quoted_key_double_quotes(self) -> None:
        """Test parsing double-quoted key."""
        content = '"key" => value'
        key, idx = _parse_quoted_key(content, 0)
        assert key == "key"
        assert idx == 5

    def test_parse_simple_value_string(self) -> None:
        """Test parsing simple string value."""
        content = '"value", next'
        value, _ = _parse_simple_value(content, 0)
        assert isinstance(value, (str, bool, int, type(None)))

    def test_skip_whitespace_multiple(self) -> None:
        """Test skipping multiple whitespace characters."""
        content = "   hello"
        idx = _skip_whitespace(content, 0)
        assert idx == 3
        assert content[idx] == "h"

    def test_skip_whitespace_none(self) -> None:
        """Test skipping when no whitespace present."""
        content = "hello"
        idx = _skip_whitespace(content, 0)
        assert idx == 0

    def test_skip_whitespace_and_arrows_complex(self) -> None:
        """Test skipping whitespace and arrow operators."""
        content = "  =>  next"
        idx = _skip_whitespace_and_arrows(content, 0)
        assert content[idx] == "n"

    def test_skip_to_next_item_with_comma(self) -> None:
        """Test skipping to next item ending with comma."""
        content = 'value, "next"'
        idx = _skip_to_next_item(content, 0)
        # idx should be at position after the comma (space in this case)
        assert idx >= 5  # At least past the comma
        assert '"' in content[idx:]

    def test_skip_to_next_item_with_brace(self) -> None:
        """Test skipping to next item ending with closing brace."""
        content = "value}"
        idx = _skip_to_next_item(content, 0)
        assert idx == 6


class TestToolParameterValidation:
    """Tests for MCP tool parameter validation."""

    def test_list_directory_invalid_path(self, tmp_path: Path) -> None:
        """Test list_directory with invalid path."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            result = list_directory("/nonexistent/path")
            assert isinstance(result, str)
            assert "Error" in result or "error" in result.lower()

    def test_read_file_invalid_path(self, tmp_path: Path) -> None:
        """Test read_file with invalid path."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            result = read_file("/nonexistent/file.txt")
            assert isinstance(result, str)
            assert "Error" in result or "error" in result.lower()

    def test_parse_template_invalid_path(self, tmp_path: Path) -> None:
        """Test parse_template with invalid path."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            result = parse_template("/nonexistent/template.erb")
            assert isinstance(result, str)
            assert "Error" in result or "error" in result.lower()

    def test_parse_custom_resource_invalid_path(self, tmp_path: Path) -> None:
        """Test parse_custom_resource with invalid path."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            result = parse_custom_resource("/nonexistent/resource.rb")
            assert isinstance(result, str)
            assert "Error" in result or "error" in result.lower()

    def test_read_cookbook_metadata_invalid_path(self, tmp_path: Path) -> None:
        """Test read_cookbook_metadata with invalid path."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            result = read_cookbook_metadata("/nonexistent/metadata.rb")
            assert isinstance(result, str)
            assert "Error" in result or "error" in result.lower()

    def test_parse_cookbook_metadata_invalid_path(self, tmp_path: Path) -> None:
        """Test parse_cookbook_metadata with invalid path."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            result = parse_cookbook_metadata("/nonexistent/metadata.rb")
            assert isinstance(result, dict)
            assert "error" in result

    def test_parse_recipe_invalid_path(self, tmp_path: Path) -> None:
        """Test parse_recipe with invalid path."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            result = parse_recipe("/nonexistent/recipe.rb")
            assert isinstance(result, str)
            assert "Error" in result or "error" in result.lower()

    def test_parse_attributes_invalid_path(self, tmp_path: Path) -> None:
        """Test parse_attributes with invalid path."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            result = parse_attributes("/nonexistent/attributes.rb")
            assert isinstance(result, str)
            assert "Error" in result or "error" in result.lower()

    def test_parse_inspec_profile_invalid_path(self, tmp_path: Path) -> None:
        """Test parse_inspec_profile with invalid path."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            result = parse_inspec_profile("/nonexistent/inspec")
            assert isinstance(result, str)
            assert "Error" in result or "error" in result.lower()

    def test_parse_habitat_plan_invalid_path(self, tmp_path: Path) -> None:
        """Test parse_habitat_plan with invalid path."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            result = parse_habitat_plan("/nonexistent/plan.sh")
            assert isinstance(result, str)


class TestDataBagConversion:
    """Tests for Chef data bag to Ansible variable conversion."""

    def test_convert_chef_databag_to_vars_empty_content(self) -> None:
        """Test converting empty data bag content."""
        result = convert_chef_databag_to_vars("", "test_bag")
        assert "Error" in result or "error" in result.lower()
        assert "empty" in result.lower()

    def test_convert_chef_databag_to_vars_empty_name(self) -> None:
        """Test converting with empty databag name."""
        result = convert_chef_databag_to_vars('{"key": "value"}', "")
        assert "Error" in result or "error" in result.lower()

    def test_convert_chef_databag_to_vars_invalid_json(self) -> None:
        """Test converting invalid JSON content."""
        result = convert_chef_databag_to_vars("{invalid json}", "bag")
        assert "Error" in result or "error" in result.lower()
        assert "JSON" in result or "json" in result.lower()

    def test_convert_chef_databag_to_vars_invalid_scope(self) -> None:
        """Test converting with invalid target scope."""
        result = convert_chef_databag_to_vars(
            '{"key": "value"}', "bag", target_scope="invalid"
        )
        assert "Error" in result or "error" in result.lower()
        assert "scope" in result.lower()

    def test_convert_chef_databag_to_vars_valid_plaintext(self) -> None:
        """Test converting valid plaintext data bag."""
        content = json.dumps(
            {"id": "data", "username": "admin", "credential": "test-credential"}
        )
        result = convert_chef_databag_to_vars(content, "credentials")
        assert isinstance(result, str)
        assert "---" in result or "credentials" in result

    def test_convert_chef_databag_to_vars_valid_encrypted(self) -> None:
        """Test converting valid encrypted data bag."""
        content = json.dumps(
            {
                "id": "data",
                "encrypted_data": "encrypted_value",
                "cipher": "aes-256-cbc",
            }
        )
        result = convert_chef_databag_to_vars(content, "secrets", is_encrypted=True)
        assert isinstance(result, str)
        assert "vault" in result.lower() or "Vault" in result

    @pytest.mark.parametrize(
        "scope",
        ["group_vars", "host_vars", "playbook"],
    )
    def test_convert_chef_databag_to_vars_scopes(self, scope: str) -> None:
        """Test conversion with various target scopes."""
        content = json.dumps({"id": "data", "app_name": "myapp"})
        result = convert_chef_databag_to_vars(content, "app_config", target_scope=scope)
        assert isinstance(result, str)

    def test_analyse_chef_databag_usage_nonexistent_cookbook(
        self, tmp_path: Path
    ) -> None:
        """Test analysing data bag usage in nonexistent cookbook."""
        with patch("souschef.server._normalize_path") as mock_normalize:
            mock_path = MagicMock(spec=Path)
            mock_path.exists.return_value = False
            mock_normalize.return_value = mock_path

            result = analyse_chef_databag_usage("/nonexistent/cookbook")
            assert "Error" in result or "not found" in result.lower()


class TestChefEnvironmentConversion:
    """Tests for Chef environment to Ansible inventory conversion."""

    def test_convert_chef_environment_to_inventory_group_basic(self) -> None:
        """Test basic environment to inventory group conversion."""
        env_content = 'name "production"'
        result = convert_chef_environment_to_inventory_group(env_content, "production")
        assert isinstance(result, str)
        assert "production" in result or "---" in result

    def test_generate_inventory_from_chef_environments_nonexistent_dir(
        self, tmp_path: Path
    ) -> None:
        """Test generating inventory from nonexistent directory."""
        with patch("souschef.server._normalize_path") as mock_normalize:
            mock_path = MagicMock(spec=Path)
            mock_path.exists.return_value = False
            mock_normalize.return_value = mock_path

            result = generate_inventory_from_chef_environments(
                "/nonexistent/environments"
            )
            assert "Error" in result or "not found" in result.lower()

    def test_generate_inventory_from_chef_environments_output_format_yaml(
        self, tmp_path: Path
    ) -> None:
        """Test generating inventory with YAML output format."""
        env_dir = tmp_path / "environments"
        env_dir.mkdir()
        (env_dir / "prod.rb").write_text('name "production"')

        with patch("souschef.server._normalize_path", return_value=env_dir):
            result = generate_inventory_from_chef_environments(
                str(env_dir), output_format="yaml"
            )
            assert isinstance(result, str)

    def test_analyse_chef_environment_usage_nonexistent_cookbook(
        self, tmp_path: Path
    ) -> None:
        """Test analysing environment usage in nonexistent cookbook."""
        with patch("souschef.server._normalize_path") as mock_normalize:
            mock_path = MagicMock(spec=Path)
            mock_path.exists.return_value = False
            mock_normalize.return_value = mock_path

            result = analyse_chef_environment_usage("/nonexistent/cookbook")
            assert "Error" in result or "not found" in result.lower()


class TestResourceConversion:
    """Tests for Chef resource to Ansible task conversion."""

    @pytest.mark.parametrize(
        "resource_type,resource_name,action",
        [
            ("package", "nginx", "install"),
            ("service", "httpd", "start"),
            ("file", "/etc/config", "create"),
            ("template", "/etc/app.conf", "create"),
            ("directory", "/opt/app", "create"),
        ],
    )
    def test_convert_resource_to_task_various(
        self, resource_type: str, resource_name: str, action: str
    ) -> None:
        """Test converting various Chef resource types to tasks."""
        result = convert_resource_to_task(
            resource_type=resource_type,
            resource_name=resource_name,
            action=action,
        )
        assert isinstance(result, str)

    def test_convert_resource_to_task_with_properties(self) -> None:
        """Test converting resource with properties."""
        properties = "{'mode': '0755', 'owner': 'root'}"
        result = convert_resource_to_task(
            resource_type="directory",
            resource_name="/opt/app",
            action="create",
            properties=properties,
        )
        assert isinstance(result, str)


class TestInSpecConversion:
    """Tests for InSpec control conversion."""

    def test_convert_inspec_to_test_invalid_path(self, tmp_path: Path) -> None:
        """Test converting InSpec from nonexistent path."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            result = convert_inspec_to_test("/nonexistent/inspec")
            assert isinstance(result, str)
            assert "Error" in result or "error" in result.lower()

    @pytest.mark.parametrize(
        "output_format",
        ["testinfra", "ansible_assert", "serverspec", "goss"],
    )
    def test_convert_inspec_to_test_formats(self, output_format: str) -> None:
        """Test converting InSpec to various test formats."""
        with patch("souschef.server._convert_inspec_test") as mock_convert:
            mock_convert.return_value = "mock test code"
            result = convert_inspec_to_test(
                "/path/to/inspec", output_format=output_format
            )
            assert isinstance(result, str)
            mock_convert.assert_called()

    def test_generate_inspec_from_recipe_error_handling(self, tmp_path: Path) -> None:
        """Test error handling when parsing recipe fails."""
        with patch("souschef.server._normalise_workspace_path") as mock_normalize:
            mock_path = MagicMock(spec=Path)
            mock_normalize.return_value = mock_path
            with patch("souschef.server.parse_recipe") as mock_parse:
                mock_parse.return_value = "Error: parsing failed"
                result = generate_inspec_from_recipe(str(mock_path))
                assert "Error" in result


class TestTemplateConversion:
    """Tests for ERB template conversion."""

    def test_convert_template_with_ai_success(self, tmp_path: Path) -> None:
        """Test template conversion with AI enabled."""
        template_file = tmp_path / "template.erb"
        template_file.write_text("<%= @var %>\n")

        with patch("souschef.server._convert_template_with_ai") as mock_convert:
            mock_convert.return_value = {
                "success": True,
                "jinja2_output": "{{ var }}",
                "warnings": [],
            }
            result = convert_template_with_ai(
                str(template_file), use_ai_enhancement=True
            )
            assert isinstance(result, str)
            mock_convert.assert_called()

    def test_convert_template_with_ai_without_enhancement(self, tmp_path: Path) -> None:
        """Test template conversion without AI enhancement."""
        template_file = tmp_path / "template.erb"
        template_file.write_text("<%= @var %>\n")

        with patch(
            "souschef.converters.template.convert_template_file"
        ) as mock_convert:
            mock_convert.return_value = {
                "success": True,
                "jinja2_output": "{{ var }}",
            }
            result = convert_template_with_ai(
                str(template_file), use_ai_enhancement=False
            )
            assert isinstance(result, str)

    def test_convert_template_with_ai_invalid_path(self, tmp_path: Path) -> None:
        """Test template conversion with invalid path."""
        with patch("souschef.server._normalize_path") as mock_normalize:
            mock_path = MagicMock(spec=Path)
            mock_path.exists.return_value = False
            mock_normalize.return_value = mock_path
            result = convert_template_with_ai("/nonexistent/template.erb")
            assert "Error" in result or "error" in result.lower()


class TestHabitatParsing:
    """Tests for Chef Habitat plan parsing and conversion."""

    def test_parse_habitat_plan_success(self, tmp_path: Path) -> None:
        """Test successful Habitat plan parsing."""
        plan_file = tmp_path / "plan.sh"
        plan_file.write_text(
            """
pkg_name="myapp"
pkg_version="1.0.0"
pkg_origin="myorg"
"""
        )

        with (
            patch("souschef.server._get_workspace_root", return_value=tmp_path),
            patch("souschef.server._parse_habitat_plan") as mock_parse,
        ):
            mock_parse.return_value = '{"success": true}'
            result = parse_habitat_plan(str(plan_file))
            assert isinstance(result, str)

    def test_convert_habitat_to_dockerfile_success(self, tmp_path: Path) -> None:
        """Test successful Habitat to Dockerfile conversion."""
        plan_file = tmp_path / "plan.sh"
        plan_file.write_text('pkg_name="app"')

        with (
            patch("souschef.server._get_workspace_root", return_value=tmp_path),
            patch("souschef.server._convert_habitat_to_dockerfile") as mock_convert,
        ):
            mock_convert.return_value = "FROM ubuntu:22.04"
            result = convert_habitat_to_dockerfile(str(plan_file))
            assert isinstance(result, str)

    def test_convert_habitat_to_dockerfile_custom_base_image(
        self, tmp_path: Path
    ) -> None:
        """Test Dockerfile conversion with custom base image."""
        plan_file = tmp_path / "plan.sh"
        plan_file.write_text('pkg_name="app"')

        with (
            patch("souschef.server._get_workspace_root", return_value=tmp_path),
            patch("souschef.server._convert_habitat_to_dockerfile") as mock_convert,
        ):
            mock_convert.return_value = "FROM alpine:latest"
            result = convert_habitat_to_dockerfile(
                str(plan_file), base_image="alpine:latest"
            )
            assert isinstance(result, str)
            mock_convert.assert_called()

    def test_generate_compose_from_habitat_single_plan(self, tmp_path: Path) -> None:
        """Test Docker Compose generation from single Habitat plan."""
        plan_file = tmp_path / "plan.sh"
        plan_file.write_text('pkg_name="app"')

        with (
            patch("souschef.server._get_workspace_root", return_value=tmp_path),
            patch("souschef.server._generate_compose_from_habitat") as mock_generate,
        ):
            mock_generate.return_value = "version: '3'"
            result = generate_compose_from_habitat(str(plan_file))
            assert isinstance(result, str)

    def test_generate_compose_from_habitat_multiple_plans(self, tmp_path: Path) -> None:
        """Test Docker Compose generation from multiple Habitat plans."""
        plan1 = tmp_path / "plan1.sh"
        plan2 = tmp_path / "plan2.sh"
        plan1.write_text('pkg_name="app1"')
        plan2.write_text('pkg_name="app2"')

        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            paths = f"{str(plan1)}, {str(plan2)}"
            with patch(
                "souschef.server._generate_compose_from_habitat"
            ) as mock_generate:
                mock_generate.return_value = "version: '3'"
                result = generate_compose_from_habitat(paths)
                assert isinstance(result, str)


class TestMigrationAssessment:
    """Tests for Chef to Ansible migration assessment tools."""

    def test_assess_chef_migration_complexity_invalid_paths(
        self, tmp_path: Path
    ) -> None:
        """Test assessment with invalid cookbook paths."""
        with patch("souschef.server._normalize_path") as mock_normalize:
            mock_path = MagicMock(spec=Path)
            mock_path.is_absolute.return_value = False
            mock_normalize.return_value = mock_path

            with pytest.raises(ValueError):
                assess_chef_migration_complexity("/relative/path")


class TestProfilingTools:
    """Tests for cookbook and operation profiling tools."""

    def test_profile_cookbook_performance_invalid_path(self, tmp_path: Path) -> None:
        """Test profiling with invalid cookbook path."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            result = profile_cookbook_performance("/nonexistent/cookbook")
            assert isinstance(result, str)
            assert "Error" in result or "error" in result.lower()

    def test_profile_parsing_operation_invalid_operation(self, tmp_path: Path) -> None:
        """Test profiling with invalid operation type."""
        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            result = profile_parsing_operation("invalid_op", str(tmp_path))
            assert isinstance(result, str)
            assert "Error" in result or "error" in result.lower()
            assert "Invalid operation" in result or "invalid" in result.lower()

    @pytest.mark.parametrize(
        "operation",
        ["recipe", "attributes", "resource", "template"],
    )
    def test_profile_parsing_operation_valid(
        self, operation: str, tmp_path: Path
    ) -> None:
        """Test profiling valid parsing operations."""
        test_file = tmp_path / f"test.{operation}"
        test_file.write_text("test content")

        with (
            patch("souschef.server._get_workspace_root", return_value=tmp_path),
            patch("souschef.profiling.profile_function") as mock_profile,
        ):
            mock_profile.return_value = (None, "profile result")
            result = profile_parsing_operation(operation, str(test_file))
            assert isinstance(result, str)


class TestCICDPipelineGeneration:
    """Tests for CI/CD pipeline generation tools."""

    def test_generate_jenkinsfile_from_chef_success(self, tmp_path: Path) -> None:
        """Test successful Jenkinsfile generation."""
        cookbook = tmp_path / "nginx"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'nginx'\n")

        with (
            patch("souschef.server._get_workspace_root", return_value=tmp_path),
            patch(
                "souschef.ci.jenkins_pipeline.generate_jenkinsfile_from_chef_ci"
            ) as mock_generate,
        ):
            mock_generate.return_value = "node { stage('Test') {} }"
            result = generate_jenkinsfile_from_chef(str(cookbook))
            assert isinstance(result, str)

    def test_generate_jenkinsfile_from_chef_pipeline_type(self, tmp_path: Path) -> None:
        """Test Jenkinsfile generation with specific pipeline type."""
        cookbook = tmp_path / "nginx"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'nginx'\n")

        with (
            patch("souschef.server._get_workspace_root", return_value=tmp_path),
            patch(
                "souschef.ci.jenkins_pipeline.generate_jenkinsfile_from_chef_ci"
            ) as mock_generate,
        ):
            mock_generate.return_value = "pipeline {}"
            result = generate_jenkinsfile_from_chef(
                str(cookbook),
                pipeline_type="declarative",
            )
            assert isinstance(result, str)
            mock_generate.assert_called()

    def test_generate_gitlab_ci_from_chef_success(self, tmp_path: Path) -> None:
        """Test successful GitLab CI generation."""
        cookbook = tmp_path / "nginx"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'nginx'\n")

        with (
            patch("souschef.server._get_workspace_root", return_value=tmp_path),
            patch(
                "souschef.ci.gitlab_ci.generate_gitlab_ci_from_chef_ci"
            ) as mock_generate,
        ):
            mock_generate.return_value = "stages:\n  - test"
            result = generate_gitlab_ci_from_chef(str(cookbook))
            assert isinstance(result, str)

    @pytest.mark.parametrize(
        "enable_cache,enable_artifacts",
        [
            ("yes", "yes"),
            ("no", "no"),
            ("true", "false"),
        ],
    )
    def test_generate_gitlab_ci_from_chef_options(
        self, enable_cache: str, enable_artifacts: str, tmp_path: Path
    ) -> None:
        """Test GitLab CI generation with various options."""
        cookbook = tmp_path / "nginx"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'nginx'\n")

        with (
            patch("souschef.server._get_workspace_root", return_value=tmp_path),
            patch(
                "souschef.ci.gitlab_ci.generate_gitlab_ci_from_chef_ci"
            ) as mock_generate,
        ):
            mock_generate.return_value = "stages: []"
            result = generate_gitlab_ci_from_chef(
                str(cookbook),
                enable_cache=enable_cache,
                enable_artifacts=enable_artifacts,
            )
            assert isinstance(result, str)

    def test_generate_github_workflow_from_chef_success(self, tmp_path: Path) -> None:
        """Test successful GitHub Actions workflow generation."""
        cookbook = tmp_path / "nginx"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'nginx'\n")

        with (
            patch("souschef.server._normalize_path", return_value=cookbook),
            patch(
                "souschef.ci.github_actions.generate_github_workflow_from_chef_ci"
            ) as mock_generate,
        ):
            mock_generate.return_value = "name: Test"
            result = generate_github_workflow_from_chef(str(cookbook))
            assert isinstance(result, str)

    @pytest.mark.parametrize(
        "enable_cache,enable_artifacts",
        [
            ("yes", "yes"),
            ("no", "no"),
        ],
    )
    def test_generate_github_workflow_from_chef_options(
        self, enable_cache: str, enable_artifacts: str, tmp_path: Path
    ) -> None:
        """Test GitHub workflow generation with various options."""
        cookbook = tmp_path / "nginx"
        cookbook.mkdir()

        with (
            patch("souschef.server._normalize_path", return_value=cookbook),
            patch(
                "souschef.ci.github_actions.generate_github_workflow_from_chef_ci"
            ) as mock_generate,
        ):
            mock_generate.return_value = "name: Test"
            result = generate_github_workflow_from_chef(
                str(cookbook),
                enable_cache=enable_cache,
                enable_artifacts=enable_artifacts,
            )
            assert isinstance(result, str)


class TestDeploymentToolsParameterHandling:
    """Tests for deployment and scaffolding tool error handling."""

    def test_generate_ansible_vault_from_databags_empty_directory(
        self, tmp_path: Path
    ) -> None:
        """Test vault generation from empty data bags directory."""
        empty_dir = tmp_path / "databags"
        empty_dir.mkdir()

        with patch("souschef.server._normalize_path", return_value=empty_dir):
            result = generate_ansible_vault_from_databags(str(empty_dir))
            # Should succeed but with no items
            assert isinstance(result, str)

    def test_generate_ansible_vault_from_databags_nonexistent(
        self, tmp_path: Path
    ) -> None:
        """Test vault generation from nonexistent directory."""
        with patch("souschef.server._normalize_path") as mock_normalize:
            mock_path = MagicMock(spec=Path)
            mock_path.exists.return_value = False
            mock_normalize.return_value = mock_path

            result = generate_ansible_vault_from_databags("/nonexistent")
            assert "Error" in result or "not found" in result.lower()


class TestErrorPathsAndEdgeCases:
    """Tests for error handling and edge cases."""

    def test_parse_attributes_resolve_precedence_true(self, tmp_path: Path) -> None:
        """Test attribute parsing with precedence resolution enabled."""
        attr_file = tmp_path / "attributes.rb"
        attr_file.write_text(
            """
default['app']['version'] = '1.0.0'
"""
        )

        with (
            patch("souschef.server._get_workspace_root", return_value=tmp_path),
            patch("souschef.server._parse_attributes") as mock_parse,
        ):
            mock_parse.return_value = "attributes: ..."
            result = parse_attributes(str(attr_file), resolve_precedence=True)
            assert isinstance(result, str)
            mock_parse.assert_called()

    def test_parse_attributes_resolve_precedence_false(self, tmp_path: Path) -> None:
        """Test attribute parsing without precedence resolution."""
        attr_file = tmp_path / "attributes.rb"
        attr_file.write_text(
            """
default['app']['version'] = '1.0.0'
"""
        )

        with (
            patch("souschef.server._get_workspace_root", return_value=tmp_path),
            patch("souschef.server._parse_attributes") as mock_parse,
        ):
            mock_parse.return_value = "attributes: ..."
            result = parse_attributes(str(attr_file), resolve_precedence=False)
            assert isinstance(result, str)
            mock_parse.assert_called()

    def test_list_cookbooks_structure_valid_path(self, tmp_path: Path) -> None:
        """Test listing cookbook structure with valid path."""
        from souschef.server import list_cookbook_structure

        cookbook = tmp_path / "nginx"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'nginx'\n")

        with (
            patch("souschef.server._get_workspace_root", return_value=tmp_path),
            patch("souschef.server._list_cookbook_structure") as mock_list,
        ):
            mock_list.return_value = "structure: ..."
            result = list_cookbook_structure(str(cookbook))
            assert isinstance(result, str)
            mock_list.assert_called()

    def test_list_cookbook_structure_invalid_path(self, tmp_path: Path) -> None:
        """Test listing cookbook structure with invalid path."""
        from souschef.server import list_cookbook_structure

        with patch("souschef.server._get_workspace_root", return_value=tmp_path):
            result = list_cookbook_structure("/nonexistent/cookbook")
            assert isinstance(result, str)
            assert "Error" in result or "error" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
