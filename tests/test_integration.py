"""Integration tests using real files and fixtures."""

from pathlib import Path

import pytest

from souschef.server import (
    list_cookbook_structure,
    list_directory,
    parse_attributes,
    parse_recipe,
    read_cookbook_metadata,
    read_file,
)

# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_COOKBOOK = FIXTURES_DIR / "sample_cookbook"


class TestRealFileOperations:
    """Test actual file operations with real fixtures."""

    def test_read_real_metadata(self):
        """Test reading a real metadata.rb file."""
        result = read_cookbook_metadata(str(SAMPLE_COOKBOOK / "metadata.rb"))

        assert "name: nginx" in result
        assert "maintainer: Chef Software, Inc." in result
        assert "version: 12.0.0" in result
        assert "depends: logrotate, systemd" in result
        assert "supports: ubuntu, debian, centos, redhat" in result

    def test_read_real_recipe(self):
        """Test reading a real recipe file."""
        content = read_file(str(SAMPLE_COOKBOOK / "recipes" / "default.rb"))

        assert isinstance(content, str)
        assert "package 'nginx' do" in content
        assert "service 'nginx' do" in content
        assert "template '/etc/nginx/nginx.conf' do" in content

    def test_parse_real_recipe(self):
        """Test parsing a real recipe with multiple resources."""
        result = parse_recipe(str(SAMPLE_COOKBOOK / "recipes" / "default.rb"))

        # Should find multiple resources
        assert "Resource 1:" in result
        assert "Type: package" in result
        assert "Name: nginx" in result
        assert "Type: service" in result
        assert "Type: template" in result
        assert "Type: directory" in result
        assert "Type: file" in result

    def test_parse_real_attributes(self):
        """Test parsing a real attributes file."""
        result = parse_attributes(str(SAMPLE_COOKBOOK / "attributes" / "default.rb"))

        assert "default[nginx.port] = 80" in result
        assert "default[nginx.ssl_port] = 443" in result
        assert "override[nginx.worker_rlimit_nofile] = 65536" in result
        assert "normal[nginx.server_tokens] = 'off'" in result
        # Test nested attributes
        assert "nginx.ssl.protocols" in result

    def test_list_real_cookbook_structure(self):
        """Test listing a real cookbook structure."""
        result = list_cookbook_structure(str(SAMPLE_COOKBOOK))

        assert "recipes/" in result
        assert "default.rb" in result
        assert "attributes/" in result
        assert "metadata/" in result
        assert "metadata.rb" in result

    def test_list_real_directory(self):
        """Test listing a real directory."""
        result = list_directory(str(SAMPLE_COOKBOOK))

        assert isinstance(result, list)
        assert "metadata.rb" in result
        assert "recipes" in result
        assert "attributes" in result


@pytest.mark.parametrize(
    "invalid_path",
    [
        "/nonexistent/path",
        str(FIXTURES_DIR / "does_not_exist"),
    ],
)
def test_invalid_paths(invalid_path):
    """Test that invalid paths return error messages."""
    result = read_file(invalid_path)
    assert isinstance(result, str)
    assert "Error:" in result or "An error occurred:" in result


@pytest.mark.parametrize(
    "file_path,expected_content",
    [
        ("metadata.rb", "name 'nginx'"),
        ("recipes/default.rb", "package 'nginx'"),
        ("attributes/default.rb", "default['nginx']['port']"),
    ],
)
def test_read_various_files(file_path, expected_content):
    """Test reading various file types from the cookbook."""
    full_path = SAMPLE_COOKBOOK / file_path
    content = read_file(str(full_path))

    assert isinstance(content, str)
    assert expected_content in content


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_directory(self, tmp_path):
        """Test listing an empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = list_directory(str(empty_dir))
        assert result == []

    def test_directory_with_hidden_files(self, tmp_path):
        """Test listing directory with hidden files."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / ".hidden").write_text("hidden")
        (test_dir / "visible.txt").write_text("visible")

        result = list_directory(str(test_dir))
        assert ".hidden" in result
        assert "visible.txt" in result

    def test_recipe_with_no_resources(self, tmp_path):
        """Test parsing a recipe file with only comments."""
        recipe_file = tmp_path / "empty.rb"
        recipe_file.write_text("# Only comments\n# No resources here\n")

        result = parse_recipe(str(recipe_file))
        assert "Warning: No Chef resources found" in result

    def test_attributes_with_no_attributes(self, tmp_path):
        """Test parsing an attributes file with no attributes."""
        attr_file = tmp_path / "empty.rb"
        attr_file.write_text("# Only comments\n")

        result = parse_attributes(str(attr_file))
        assert "Warning: No attributes found" in result

    def test_cookbook_with_no_structure(self, tmp_path):
        """Test a directory that's not a cookbook."""
        not_cookbook = tmp_path / "not_cookbook"
        not_cookbook.mkdir()

        result = list_cookbook_structure(str(not_cookbook))
        assert "Warning: No standard cookbook structure found" in result


class TestAttributeParsing:
    """Test various attribute declaration patterns."""

    @pytest.mark.parametrize(
        "attr_line,expected_in_result",
        [
            ("default['nginx']['port'] = 80", "nginx.port"),
            ("override['app']['timeout'] = 30", "app.timeout"),
            ("normal['service']['name'] = 'web'", "service.name"),
            ("default['deep']['nested']['attr'] = 'value'", "deep.nested.attr"),
        ],
    )
    def test_various_attribute_patterns(self, tmp_path, attr_line, expected_in_result):
        """Test parsing different attribute declaration patterns."""
        attr_file = tmp_path / "test.rb"
        attr_file.write_text(attr_line)

        result = parse_attributes(str(attr_file))
        assert expected_in_result in result


class TestRecipeParsing:
    """Test various recipe resource patterns."""

    @pytest.mark.parametrize(
        "resource_type",
        [
            "package",
            "service",
            "template",
            "file",
            "directory",
            "execute",
            "user",
            "group",
        ],
    )
    def test_various_resource_types(self, tmp_path, resource_type):
        """Test parsing different Chef resource types."""
        recipe_file = tmp_path / "test.rb"
        recipe_content = f"{resource_type} 'test_resource' do\n  action :create\nend\n"
        recipe_file.write_text(recipe_content)

        result = parse_recipe(str(recipe_file))
        assert f"Type: {resource_type}" in result
        assert "Name: test_resource" in result


def test_benchmark_parse_recipe(benchmark):
    """Benchmark recipe parsing performance."""
    recipe_path = str(SAMPLE_COOKBOOK / "recipes" / "default.rb")

    result = benchmark(parse_recipe, recipe_path)

    # Ensure it still works correctly
    assert "Resource 1:" in result


def test_benchmark_parse_attributes(benchmark):
    """Benchmark attribute parsing performance."""
    attr_path = str(SAMPLE_COOKBOOK / "attributes" / "default.rb")

    result = benchmark(parse_attributes, attr_path)

    # Ensure it still works correctly
    assert "nginx.port" in result
