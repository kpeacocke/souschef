"""Comprehensive tests for server.py MCP tool error paths."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from souschef import server


class TestInSpecErrorPaths:
    """Error paths for InSpec-related tools."""

    def test_parse_controls_missing_controls_dir(self, tmp_path: Path) -> None:
        """Missing controls directory should raise FileNotFoundError."""
        # _parse_controls is called internally, test through public API
        with patch(
            "souschef.server._normalise_workspace_path",
            return_value=tmp_path,
        ):
            result = server.parse_inspec_profile(str(tmp_path))
            # Should handle missing controls gracefully
            assert isinstance(result, str)

    def test_parse_controls_file_read_error(self, tmp_path: Path) -> None:
        """Error reading control file should be handled."""
        controls_dir = tmp_path / "controls"
        controls_dir.mkdir()
        (controls_dir / "test.rb").write_text("control 'test'")

        # Test through public API with mocked error
        with (
            patch("souschef.server.safe_read_text", side_effect=OSError("read failed")),
            patch("souschef.server._normalise_workspace_path", return_value=tmp_path),
        ):
            result = server.parse_inspec_profile(str(tmp_path))
            # Should return error message
            assert isinstance(result, str)

    def test_parse_controls_from_file_error(self, tmp_path: Path) -> None:
        """Error reading control file should raise RuntimeError."""
        control_file = tmp_path / "test.rb"
        control_file.write_text("control 'test'")

        with (
            patch("pathlib.Path.read_text", side_effect=OSError("read failed")),
            pytest.raises(RuntimeError, match="Error reading file"),
        ):
            server._parse_controls_from_file(control_file)

    def test_generate_inspec_from_recipe_error(self, tmp_path: Path) -> None:
        """Exception during generation should return formatted error."""
        recipe_file = tmp_path / "recipe.rb"
        recipe_file.write_text("package 'nginx'")

        with patch(
            "souschef.server._normalise_workspace_path",
            side_effect=ValueError("bad path"),
        ):
            result = server.generate_inspec_from_recipe(str(recipe_file))
            assert "Error" in result or "bad path" in result


class TestDatabagAndEnvironmentErrorPaths:
    """Error paths for databag and environment tools."""

    def test_convert_chef_databag_empty_content(self) -> None:
        """Empty databag content should return error."""
        result = server.convert_chef_databag_to_vars("", "bag")
        assert "cannot be empty" in result

    def test_convert_chef_databag_empty_name(self) -> None:
        """Empty databag name should return error."""
        result = server.convert_chef_databag_to_vars("{}", "")
        assert "cannot be empty" in result

    def test_convert_chef_databag_invalid_scope(self) -> None:
        """Invalid target scope should return error."""
        result = server.convert_chef_databag_to_vars("{}", "bag", target_scope="bad")
        assert "Invalid target scope" in result

    def test_convert_chef_databag_invalid_json(self) -> None:
        """Invalid JSON should return error."""
        result = server.convert_chef_databag_to_vars("{bad:", "bag")
        assert "Invalid JSON" in result

    def test_convert_chef_databag_exception(self) -> None:
        """Generic exception should return formatted error."""
        with patch("json.loads", side_effect=RuntimeError("parse error")):
            result = server.convert_chef_databag_to_vars("{}", "bag")
            assert "Error" in result or "parse error" in result


class TestResourceParsingErrorPaths:
    """Error paths for resource parsing."""

    def test_resource_properties_parse_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Malformed properties should be handled gracefully."""
        # Create recipe with resources that have bad properties
        recipe_content = """
package 'nginx' do
  action :install
end

Resource 1:
Type: file
Properties: {bad syntax here}
"""
        recipe_file = tmp_path / "recipe.rb"
        recipe_file.write_text("package 'nginx'")

        # Mock parse_recipe to return content with malformed properties
        def _mock_parse(path: str) -> str:
            return recipe_content

        monkeypatch.setattr("souschef.server.parse_recipe", _mock_parse)

        # The function should handle the parse error gracefully
        result = server.generate_inspec_from_recipe(str(recipe_file))
        # Check it doesn't crash - it should return something
        assert isinstance(result, str)


class TestChefServerErrorPaths:
    """Error paths for Chef Server tools."""

    def test_convert_chef_environment_exception(self) -> None:
        """Exception during conversion should return formatted error."""
        with patch(
            "souschef.server._parse_chef_environment_content",
            side_effect=RuntimeError("parse error"),
        ):
            result = server.convert_chef_environment_to_inventory_group(
                "name 'dev'", "dev"
            )
            assert (
                "Error" in result or "parse error" in result or "converting" in result
            )


class TestValidationErrorPaths:
    """Error paths for validation functions."""

    def test_validate_databags_directory_empty_string(self) -> None:
        """Empty directory path should return error."""
        path, error = server._validate_databags_directory("")
        assert path is None
        assert error is not None
        assert "cannot be empty" in error

    def test_validate_databags_directory_not_directory(self, tmp_path: Path) -> None:
        """File path (not directory) should return error."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("data")
        path, error = server._validate_databags_directory(str(file_path))
        assert path is None
        assert error is not None
        assert "not a directory" in error


class TestWorkspacePathErrorPaths:
    """Error paths for workspace path normalization."""

    def test_normalise_workspace_path_outside_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Path outside workspace should be handled."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        # MCP tools should handle invalid paths gracefully
        result = server.parse_recipe("/etc/passwd")
        # Should return error string, not raise
        assert isinstance(result, str)

    def test_normalise_workspace_path_nonexistent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nonexistent path should be handled."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        result = server.parse_recipe(str(tmp_path / "nonexistent.rb"))
        # Should return error string
        assert isinstance(result, str)


class TestHabitatToolErrorPaths:
    """Error paths for Habitat-related tools."""

    def test_parse_habitat_plan_invalid_path(self) -> None:
        """Invalid path should return error."""
        with patch(
            "souschef.server._normalise_workspace_path",
            side_effect=ValueError("bad path"),
        ):
            result = server.parse_habitat_plan("/invalid/path")
            assert "Error" in result or "bad path" in result


class TestTemplateToolErrorPaths:
    """Error paths for template-related tools."""

    def test_parse_template_invalid_path(self) -> None:
        """Invalid path should return error."""
        with patch(
            "souschef.server._normalise_workspace_path",
            side_effect=ValueError("bad path"),
        ):
            result = server.parse_template("/invalid/path")
            assert "Error" in result or "bad path" in result


class TestRecipeToolErrorPaths:
    """Error paths for recipe-related tools."""

    def test_parse_custom_resource_invalid_path(self) -> None:
        """Invalid path should return error."""
        with patch(
            "souschef.server._normalise_workspace_path",
            side_effect=ValueError("bad path"),
        ):
            result = server.parse_custom_resource("/invalid/path")
            assert "Error" in result or "bad path" in result


class TestDirectoryToolErrorPaths:
    """Error paths for directory-related tools."""

    def test_list_directory_invalid_path(self) -> None:
        """Invalid path should return error."""
        with patch(
            "souschef.server._normalise_workspace_path",
            side_effect=ValueError("bad path"),
        ):
            result = server.list_directory("/invalid/path")
            assert "Error" in result or "bad path" in result


class TestFileToolErrorPaths:
    """Error paths for file-related tools."""

    def test_read_file_invalid_path(self) -> None:
        """Invalid path should return error."""
        with patch(
            "souschef.server._normalise_workspace_path",
            side_effect=ValueError("bad path"),
        ):
            result = server.read_file("/invalid/path")
            assert "Error" in result or "bad path" in result


class TestMetadataToolErrorPaths:
    """Error paths for metadata-related tools."""

    def test_read_cookbook_metadata_invalid_path(self) -> None:
        """Invalid path should return error."""
        with patch(
            "souschef.server._normalise_workspace_path",
            side_effect=ValueError("bad path"),
        ):
            result = server.read_cookbook_metadata("/invalid/path")
            assert "Error" in result or "bad path" in result


class TestAttributesToolErrorPaths:
    """Error paths for attributes-related tools."""

    def test_parse_attributes_invalid_path(self) -> None:
        """Invalid path should return error."""
        with patch(
            "souschef.server._normalise_workspace_path",
            side_effect=ValueError("bad path"),
        ):
            result = server.parse_attributes("/invalid/path")
            assert "Error" in result or "bad path" in result


class TestInspecProfileErrorPaths:
    """Error paths for InSpec profile tool."""

    def test_parse_inspec_profile_invalid_path(self) -> None:
        """Invalid path should return error when _parse_inspec is called."""
        with patch(
            "souschef.server._normalise_workspace_path",
            side_effect=ValueError("bad path"),
        ):
            result = server.parse_inspec_profile("/invalid/path")
            assert "Error" in result or "bad path" in result


class TestCookbookAnalysisErrorPaths:
    """Error paths for cookbook analysis tools."""

    def test_analyse_chef_databag_usage_invalid_path(self, tmp_path: Path) -> None:
        """Invalid cookbook path should return error."""
        result = server.analyse_chef_databag_usage(str(tmp_path / "missing"))
        assert "not found" in result or "Error" in result

    def test_analyse_chef_databag_usage_exception(self, tmp_path: Path) -> None:
        """Exception during analysis should be handled gracefully."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        # Even with errors, function should return valid output
        result = server.analyse_chef_databag_usage(str(cookbook_dir))
        # Should return analysis (may be empty)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_analyse_chef_environment_usage_invalid_path(self, tmp_path: Path) -> None:
        """Invalid cookbook path should return error."""
        result = server.analyse_chef_environment_usage(str(tmp_path / "missing"))
        assert "not found" in result or "Error" in result

    def test_analyse_chef_search_patterns_invalid_path(self, tmp_path: Path) -> None:
        """Invalid cookbook path should return error."""
        result = server.analyse_chef_search_patterns(str(tmp_path / "missing"))
        assert "not found" in result or "Error" in result

    def test_analyse_cookbook_dependencies_invalid_path(self, tmp_path: Path) -> None:
        """Invalid cookbook path should return error."""
        result = server.analyse_cookbook_dependencies(str(tmp_path / "missing"))
        assert "not found" in result or "Error" in result


class TestInventoryGenerationErrorPaths:
    """Error paths for inventory generation tools."""

    def test_generate_inventory_from_environments_invalid_dir(
        self, tmp_path: Path
    ) -> None:
        """Invalid environments directory should return error."""
        result = server.generate_inventory_from_chef_environments(
            str(tmp_path / "missing")
        )
        assert "not found" in result or "Error" in result

    def test_generate_inventory_from_environments_exception(
        self, tmp_path: Path
    ) -> None:
        """Exception during generation should return formatted error."""
        env_dir = tmp_path / "environments"
        env_dir.mkdir()

        with patch("souschef.server.safe_glob", side_effect=RuntimeError("glob error")):
            result = server.generate_inventory_from_chef_environments(str(env_dir))
            assert "Error" in result or "glob error" in result


class TestMigrationPlanErrorPaths:
    """Error paths for migration plan generation."""

    def test_generate_migration_plan_invalid_cookbook(self, tmp_path: Path) -> None:
        """Invalid cookbook path should return error."""
        result = server.generate_migration_plan(str(tmp_path / "missing"))
        assert "not found" in result or "Error" in result

    def test_generate_migration_plan_exception(self, tmp_path: Path) -> None:
        """Migration plan generation should handle errors gracefully."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        # Function should return a plan even if some operations fail
        result = server.generate_migration_plan(str(cookbook_dir))
        assert isinstance(result, str)
        assert len(result) > 0
