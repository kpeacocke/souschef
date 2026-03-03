"""Additional tests for server tool wrappers and path validation."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from souschef import server


class TestServerPathValidation:
    """Tests for server path validation helpers."""

    def test_normalise_workspace_path_rejects_long_path(self):
        """Test rejecting overlong paths."""
        long_path = "a" * (server._MAX_PATH_LENGTH + 1)

        with pytest.raises(ValueError, match="maximum length"):
            server._normalise_workspace_path(long_path, "File path")

    def test_validate_plan_paths_too_many(self):
        """Test rejecting too many plan paths."""
        paths = ["plan" for _ in range(server._MAX_PLAN_PATHS + 1)]
        plan_paths = ",".join(paths)

        with pytest.raises(ValueError, match="Too many Habitat plan paths"):
            server._validate_plan_paths(plan_paths)

    def test_validate_plan_paths_too_long(self):
        """Test rejecting plan paths that exceed length limits."""
        plan_paths = "a" * (server._MAX_PLAN_PATHS_LENGTH + 1)

        with pytest.raises(ValueError, match="Plan paths exceed"):
            server._validate_plan_paths(plan_paths)

    def test_normalise_workspace_path_rejects_escape(self):
        """Test rejecting paths that escape workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            previous_root = os.environ.get("SOUSCHEF_WORKSPACE_ROOT")
            os.environ["SOUSCHEF_WORKSPACE_ROOT"] = tmpdir
            try:
                with pytest.raises(ValueError, match="Path traversal attempt"):
                    server._normalise_workspace_path("../outside", "File path")
            finally:
                if previous_root is None:
                    os.environ.pop("SOUSCHEF_WORKSPACE_ROOT", None)
                else:
                    os.environ["SOUSCHEF_WORKSPACE_ROOT"] = previous_root


class TestServerToolWrappers:
    """Tests for server tool wrapper functions."""

    def test_parse_template_success(self):
        """Test parsing template via server wrapper."""
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmpdir:
            template_path = Path(tmpdir) / "example.erb"
            template_path.write_text("Hello <%= @name %>")

            result = server.parse_template(str(template_path))
            data = json.loads(result)

            assert data["jinja2_template"]
            assert "name" in data["jinja2_template"]

    def test_parse_template_invalid_path(self):
        """Test invalid template path reports error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            previous_root = os.environ.get("SOUSCHEF_WORKSPACE_ROOT")
            os.environ["SOUSCHEF_WORKSPACE_ROOT"] = tmpdir
            try:
                result = server.parse_template("../outside/template.erb")
                assert result.startswith("Error during validating template path")
            finally:
                if previous_root is None:
                    os.environ.pop("SOUSCHEF_WORKSPACE_ROOT", None)
                else:
                    os.environ["SOUSCHEF_WORKSPACE_ROOT"] = previous_root

    def test_parse_custom_resource_success(self):
        """Test parsing custom resource via server wrapper."""
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmpdir:
            resource_path = Path(tmpdir) / "my_resource.rb"
            resource_path.write_text("property :name, String\naction :create do\nend")

            result = server.parse_custom_resource(str(resource_path))
            data = json.loads(result)

            assert data["resource_name"] == "my_resource"
            assert data["resource_type"] == "custom_resource"

    def test_parse_recipe_success(self):
        """Test parsing recipe via server wrapper."""
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmpdir:
            recipe_path = Path(tmpdir) / "default.rb"
            recipe_path.write_text("package 'nginx'")

            result = server.parse_recipe(str(recipe_path))

            assert "Resource" in result or "Warning" in result

    def test_read_cookbook_metadata_success(self):
        """Test reading metadata via server wrapper."""
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmpdir:
            metadata_path = Path(tmpdir) / "metadata.rb"
            metadata_path.write_text("name 'test'\nversion '1.0.0'")

            result = server.read_cookbook_metadata(str(metadata_path))

            assert "name: test" in result
            assert "version: 1.0.0" in result

    def test_parse_cookbook_metadata_success(self):
        """Test parsing metadata to dictionary via server wrapper."""
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmpdir:
            metadata_path = Path(tmpdir) / "metadata.rb"
            metadata_path.write_text("name 'demo'\nversion '2.0.0'")

            result = server.parse_cookbook_metadata(str(metadata_path))

            assert result["name"] == "demo"
            assert result["version"] == "2.0.0"

    def test_list_cookbook_structure_success(self):
        """Test listing cookbook structure via server wrapper."""
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            cookbook_path.mkdir()
            (cookbook_path / "metadata.rb").write_text("name 'cookbook'")
            recipes_dir = cookbook_path / "recipes"
            recipes_dir.mkdir()
            (recipes_dir / "default.rb").write_text("package 'vim'")

            result = server.list_cookbook_structure(str(cookbook_path))

            assert "recipes" in result
            assert "default.rb" in result

    def test_list_directory_success(self):
        """Test listing directory contents via server wrapper."""
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmpdir:
            dir_path = Path(tmpdir)
            (dir_path / "file.txt").write_text("content")

            result = server.list_directory(str(dir_path))

            assert isinstance(result, list)
            assert "file.txt" in result

    def test_list_directory_invalid_path(self):
        """Test listing directory with invalid path returns error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            previous_root = os.environ.get("SOUSCHEF_WORKSPACE_ROOT")
            os.environ["SOUSCHEF_WORKSPACE_ROOT"] = tmpdir
            try:
                result = server.list_directory("../outside")
                assert isinstance(result, str)
                assert result.startswith("Error during validating directory path")
            finally:
                if previous_root is None:
                    os.environ.pop("SOUSCHEF_WORKSPACE_ROOT", None)
                else:
                    os.environ["SOUSCHEF_WORKSPACE_ROOT"] = previous_root

    def test_read_file_success(self):
        """Test reading file contents via server wrapper."""
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmpdir:
            file_path = Path(tmpdir) / "example.txt"
            file_path.write_text("hello")

            result = server.read_file(str(file_path))

            assert result == "hello"

    def test_parse_inspec_profile_invalid_path(self):
        """Test InSpec parsing returns error for invalid path."""
        result = server.parse_inspec_profile("/invalid/path")

        assert result.startswith("Error:")

    def test_convert_inspec_to_test_invalid_path(self):
        """Test InSpec conversion returns error for invalid path."""
        result = server.convert_inspec_to_test("/invalid/path")

        assert result.startswith("Error:")


class TestParseResultExtraction:
    """Tests for parse result extraction helpers."""

    def test_extract_resources_from_parse_result(self):
        """Test extracting resources from parse output."""
        parse_result = """
        Resource 1:
          Type: package
          Name: nginx
          Properties:
            action: install
        Resource 2:
          Type: service
          Name: nginx
          Properties:
            action: start
        """

        resources = server._extract_resources_from_parse_result(parse_result)

        assert len(resources) == 2
        assert resources[0]["type"] == "package"
        assert resources[1]["name"] == "nginx"
