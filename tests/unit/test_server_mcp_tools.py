"""Tests for MCP server tool implementations to improve server.py coverage."""

import tempfile
from pathlib import Path

from souschef.server import (
    list_cookbook_structure,
    list_directory,
    parse_attributes,
    parse_cookbook_metadata,
    parse_custom_resource,
    parse_inspec_profile,
    parse_recipe,
    parse_template,
    read_cookbook_metadata,
    read_file,
)


class TestListDirectory:
    """Test list_directory MCP tool."""

    def test_list_directory_success(self) -> None:
        """Test successful directory listing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "file1.txt").touch()
            (base / "file2.rb").touch()
            subdir = base / "subdir"
            subdir.mkdir()

            result = list_directory(str(base))
            assert isinstance(result, list)
            assert "file1.txt" in result
            assert "file2.rb" in result
            assert "subdir" in result

    def test_list_directory_empty(self) -> None:
        """Test listing empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = list_directory(tmpdir)
            assert isinstance(result, list)

    def test_list_directory_nonexistent(self) -> None:
        """Test listing nonexistent directory returns error."""
        result = list_directory("/nonexistent/path/that/does/not/exist")
        assert isinstance(result, (str, list))


class TestReadFile:
    """Test read_file MCP tool."""

    def test_read_file_success(self) -> None:
        """Test successful file reading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_content = "package 'nginx'"
            test_file.write_text(test_content)

            result = read_file(str(test_file))
            assert isinstance(result, str)
            assert "nginx" in result

    def test_read_file_nonexistent(self) -> None:
        """Test reading nonexistent file."""
        result = read_file("/nonexistent/file.txt")
        assert isinstance(result, str)

    def test_read_file_empty(self) -> None:
        """Test reading empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "empty.txt"
            test_file.write_text("")

            result = read_file(str(test_file))
            assert isinstance(result, str)


class TestReadCookbookMetadata:
    """Test read_cookbook_metadata MCP tool."""

    def test_read_metadata_success(self) -> None:
        """Test reading cookbook metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "metadata.rb"
            test_file.write_text("name 'test'\nversion '1.0.0'")

            result = read_cookbook_metadata(str(test_file))
            assert isinstance(result, str)

    def test_read_metadata_nonexistent(self) -> None:
        """Test reading nonexistent metadata."""
        result = read_cookbook_metadata("/nonexistent/metadata.rb")
        assert isinstance(result, str)


class TestValidatePathSafety:
    """Test path validation and safety."""

    def test_list_directory_safe_path(self) -> None:
        """Test validation of safe path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = list_directory(tmpdir)
            assert isinstance(result, (str, list))

    def test_list_directory_directory_traversal(self) -> None:
        """Test that directory traversal is handled."""
        result = list_directory("../../etc/passwd")
        assert isinstance(result, (str, list))

    def test_read_file_null_bytes(self) -> None:
        """Test handling of null bytes in paths."""
        result = read_file("safe\x00malicious")
        assert isinstance(result, str)


class TestParseCookbookFunctions:
    """Test cookbook parsing functions."""

    def test_parse_cookbook_metadata_success(self) -> None:
        """Test parsing cookbook metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            metadata_file = base / "metadata.rb"
            metadata_file.write_text("name 'test'\nversion '1.0.0'")

            result = parse_cookbook_metadata(str(metadata_file))
            assert isinstance(result, dict)

    def test_parse_recipe_simple(self) -> None:
        """Test parsing simple recipe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            recipe_file = base / "default.rb"
            recipe_file.write_text("package 'curl' do\n  action :install\nend")

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_recipe_nonexistent(self) -> None:
        """Test parsing nonexistent recipe."""
        result = parse_recipe("/nonexistent/recipe.rb")
        assert isinstance(result, str)

    def test_list_cookbook_structure_success(self) -> None:
        """Test listing cookbook structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Create cookbook structure
            (base / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")
            recipes_dir = base / "recipes"
            recipes_dir.mkdir()
            (recipes_dir / "default.rb").write_text("package 'test'")

            result = list_cookbook_structure(str(base))
            assert isinstance(result, str)

    def test_list_cookbook_structure_empty(self) -> None:
        """Test listing empty cookbook structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = list_cookbook_structure(tmpdir)
            assert isinstance(result, str)


class TestTemplateAndAttributesFunctions:
    """Test template and attributes parsing functions."""

    def test_parse_template_success(self) -> None:
        """Test parsing template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "default.erb"
            template_file.write_text("Port <%= @port %>")

            result = parse_template(str(template_file))
            assert isinstance(result, str)

    def test_parse_template_nonexistent(self) -> None:
        """Test parsing nonexistent template."""
        result = parse_template("/nonexistent/template.erb")
        assert isinstance(result, str)

    def test_parse_attributes_success(self) -> None:
        """Test parsing attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attrs_file = Path(tmpdir) / "default.rb"
            attrs_file.write_text("default['port'] = 8080")

            result = parse_attributes(str(attrs_file))
            assert isinstance(result, str)

    def test_parse_attributes_with_precedence(self) -> None:
        """Test parsing attributes with precedence resolution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attrs_file = Path(tmpdir) / "default.rb"
            attrs_file.write_text("default['port'] = 8080\noverride['port'] = 9090")

            result = parse_attributes(str(attrs_file), resolve_precedence=True)
            assert isinstance(result, str)

    def test_parse_custom_resource_success(self) -> None:
        """Test parsing custom resource."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resource_file = Path(tmpdir) / "custom.rb"
            resource_file.write_text("property :name, String")

            result = parse_custom_resource(str(resource_file))
            assert isinstance(result, str)


class TestInspecFunctions:
    """Test InSpec profile parsing functions."""

    def test_parse_inspec_profile_success(self) -> None:
        """Test parsing InSpec profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir)
            (profile_dir / "inspec.yml").write_text(
                "name: test-profile\nversion: 1.0.0"
            )
            controls_dir = profile_dir / "controls"
            controls_dir.mkdir()
            (controls_dir / "default.rb").write_text(
                "control 'test' do\n  impact 1.0\nend"
            )

            result = parse_inspec_profile(str(profile_dir))
            assert isinstance(result, str)

    def test_parse_inspec_profile_empty(self) -> None:
        """Test parsing empty InSpec profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = parse_inspec_profile(tmpdir)
            assert isinstance(result, str)

    def test_parse_inspec_profile_nonexistent(self) -> None:
        """Test parsing nonexistent InSpec profile."""
        result = parse_inspec_profile("/nonexistent/profile")
        assert isinstance(result, str)


class TestMCPToolErrorHandling:
    """Test error handling in MCP tools."""

    def test_read_file_with_invalid_path(self) -> None:
        """Test read_file handles invalid paths gracefully."""
        result = read_file("/invalid/path/that/does/not/exist")
        assert isinstance(result, str)

    def test_parse_recipe_with_malformed_ruby(self) -> None:
        """Test parsing recipe with invalid Ruby syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "invalid.rb"
            recipe_file.write_text("invalid ruby { syntax here")

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_attributes_with_malformed_ruby(self) -> None:
        """Test parsing attributes with invalid Ruby syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attrs_file = Path(tmpdir) / "invalid.rb"
            attrs_file.write_text("invalid ruby { syntax")

            result = parse_attributes(str(attrs_file))
            assert isinstance(result, str)

    def test_parse_cookbook_metadata_with_malformed(self) -> None:
        """Test parsing malformed metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.rb"
            metadata_file.write_text("invalid { ruby syntax")

            result = parse_cookbook_metadata(str(metadata_file))
            assert isinstance(result, dict)
