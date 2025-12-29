"""Tests for the SousChef MCP server."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from souschef.server import (
    list_cookbook_structure,
    list_directory,
    parse_attributes,
    parse_recipe,
    read_cookbook_metadata,
    read_file,
)


def test_list_directory_success():
    """Test that list_directory returns a list of files."""
    mock_path = MagicMock(spec=Path)
    mock_file1 = MagicMock()
    mock_file1.name = "file1.txt"
    mock_file2 = MagicMock()
    mock_file2.name = "file2.txt"
    mock_path.iterdir.return_value = [mock_file1, mock_file2]

    with patch("souschef.server.Path", return_value=mock_path):
        result = list_directory(".")
        assert result == ["file1.txt", "file2.txt"]


def test_list_directory_empty():
    """Test that list_directory returns an empty list for empty directories."""
    mock_path = MagicMock(spec=Path)
    mock_path.iterdir.return_value = []

    with patch("souschef.server.Path", return_value=mock_path):
        result = list_directory("/empty")
        assert result == []


def test_list_directory_not_found():
    """Test that list_directory returns an error when directory not found."""
    mock_path = MagicMock(spec=Path)
    mock_path.iterdir.side_effect = FileNotFoundError

    with patch("souschef.server.Path", return_value=mock_path):
        result = list_directory("non_existent_directory")
        assert "Error: Directory not found" in result


def test_list_directory_not_a_directory():
    """Test that list_directory returns an error when path is a file."""
    mock_path = MagicMock(spec=Path)
    mock_path.iterdir.side_effect = NotADirectoryError

    with patch("souschef.server.Path", return_value=mock_path):
        result = list_directory("file.txt")
        assert "Error:" in result
        assert "is not a directory" in result


def test_list_directory_permission_denied():
    """Test that list_directory returns an error on permission denied."""
    mock_path = MagicMock(spec=Path)
    mock_path.iterdir.side_effect = PermissionError

    with patch("souschef.server.Path", return_value=mock_path):
        result = list_directory("/root")
        assert "Error: Permission denied" in result


def test_list_directory_other_exception():
    """Test that list_directory returns an error on other exceptions."""
    mock_path = MagicMock(spec=Path)
    mock_path.iterdir.side_effect = Exception("A test exception")

    with patch("souschef.server.Path", return_value=mock_path):
        result = list_directory(".")
        assert "An error occurred: A test exception" in result


def test_read_file_success():
    """Test that read_file returns the file contents."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.return_value = "file contents here"

    with patch("souschef.server.Path", return_value=mock_path):
        result = read_file("test.txt")
        assert result == "file contents here"
        mock_path.read_text.assert_called_once_with(encoding="utf-8")


def test_read_file_not_found():
    """Test that read_file returns an error when file not found."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = FileNotFoundError

    with patch("souschef.server.Path", return_value=mock_path):
        result = read_file("missing.txt")
        assert "Error: File not found" in result


def test_read_file_is_directory():
    """Test that read_file returns an error when path is a directory."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = IsADirectoryError

    with patch("souschef.server.Path", return_value=mock_path):
        result = read_file("somedir")
        assert "Error:" in result
        assert "is a directory" in result


def test_read_file_permission_denied():
    """Test that read_file returns an error on permission denied."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = PermissionError

    with patch("souschef.server.Path", return_value=mock_path):
        result = read_file("protected.txt")
        assert "Error: Permission denied" in result


def test_read_file_unicode_decode_error():
    """Test that read_file returns an error on unicode decode failure."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")

    with patch("souschef.server.Path", return_value=mock_path):
        result = read_file("binary.dat")
        assert "Error: Unable to decode" in result
        assert "UTF-8" in result


def test_read_file_other_exception():
    """Test that read_file returns an error on other exceptions."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = Exception("Unexpected error")

    with patch("souschef.server.Path", return_value=mock_path):
        result = read_file("test.txt")
        assert "An error occurred: Unexpected error" in result


def test_read_cookbook_metadata_success():
    """Test read_cookbook_metadata with valid metadata.rb."""
    metadata_content = """
name 'apache2'
maintainer 'Chef Software, Inc.'
version '8.0.0'
description 'Installs and configures Apache'
license 'Apache-2.0'
depends 'logrotate'
depends 'iptables'
supports 'ubuntu'
supports 'debian'
    """
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.return_value = metadata_content

        result = read_cookbook_metadata("/cookbook/metadata.rb")

        assert "name: apache2" in result
        assert "maintainer: Chef Software, Inc." in result
        assert "version: 8.0.0" in result
        assert "description: Installs and configures Apache" in result
        assert "license: Apache-2.0" in result
        assert "depends: logrotate, iptables" in result
        assert "supports: ubuntu, debian" in result


def test_read_cookbook_metadata_minimal():
    """Test read_cookbook_metadata with minimal metadata."""
    metadata_content = "name 'simple'"
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.return_value = metadata_content

        result = read_cookbook_metadata("/cookbook/metadata.rb")

        assert "name: simple" in result
        assert "depends" not in result


def test_read_cookbook_metadata_empty():
    """Test read_cookbook_metadata with empty file."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.return_value = ""

        result = read_cookbook_metadata("/cookbook/metadata.rb")

        assert "Warning: No metadata found" in result


def test_read_cookbook_metadata_not_found():
    """Test read_cookbook_metadata with non-existent file."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = FileNotFoundError()

        result = read_cookbook_metadata("/nonexistent/metadata.rb")

        assert "Error: File not found" in result


def test_read_cookbook_metadata_is_directory():
    """Test read_cookbook_metadata when path is a directory."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = IsADirectoryError()

        result = read_cookbook_metadata("/some/directory")

        assert "Error:" in result
        assert "is a directory" in result


def test_read_cookbook_metadata_permission_denied():
    """Test read_cookbook_metadata with permission error."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = PermissionError()

        result = read_cookbook_metadata("/forbidden/metadata.rb")

        assert "Error: Permission denied" in result


def test_read_cookbook_metadata_unicode_error():
    """Test read_cookbook_metadata with unicode decode error."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = UnicodeDecodeError(
            "utf-8", b"", 0, 1, "invalid"
        )

        result = read_cookbook_metadata("/binary/file")

        assert "Error: Unable to decode" in result
        assert "UTF-8" in result


def test_read_cookbook_metadata_other_exception():
    """Test read_cookbook_metadata with unexpected exception."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = Exception("Unexpected")

        result = read_cookbook_metadata("/some/path/metadata.rb")

        assert "An error occurred: Unexpected" in result


def test_parse_recipe_success():
    """Test parse_recipe with a valid Chef recipe."""
    recipe_content = """
package 'nginx' do
  action :install
  version '1.18.0'
end

service 'nginx' do
  action :start
end

template '/etc/nginx/nginx.conf' do
  source 'nginx.conf.erb'
  action :create
end
    """
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.return_value = recipe_content

        result = parse_recipe("/cookbook/recipes/default.rb")

        assert "Resource 1:" in result
        assert "Type: package" in result
        assert "Name: nginx" in result
        assert "Action: install" in result
        assert "Resource 2:" in result
        assert "Type: service" in result
        assert "Resource 3:" in result
        assert "Type: template" in result


def test_parse_recipe_empty():
    """Test parse_recipe with no resources."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.return_value = "# Just comments"

        result = parse_recipe("/cookbook/recipes/empty.rb")

        assert "Warning: No Chef resources found" in result


def test_parse_recipe_not_found():
    """Test parse_recipe with non-existent file."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = FileNotFoundError()

        result = parse_recipe("/nonexistent/recipe.rb")

        assert "Error: File not found" in result


def test_parse_recipe_is_directory():
    """Test parse_recipe when path is a directory."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = IsADirectoryError()

        result = parse_recipe("/some/directory")

        assert "Error:" in result
        assert "is a directory" in result


def test_parse_recipe_permission_denied():
    """Test parse_recipe with permission error."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = PermissionError()

        result = parse_recipe("/forbidden/recipe.rb")

        assert "Error: Permission denied" in result


def test_parse_recipe_unicode_error():
    """Test parse_recipe with unicode decode error."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = UnicodeDecodeError(
            "utf-8", b"", 0, 1, "invalid"
        )

        result = parse_recipe("/binary/file.rb")

        assert "Error: Unable to decode" in result
        assert "UTF-8" in result


def test_parse_recipe_other_exception():
    """Test parse_recipe with unexpected exception."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = Exception("Unexpected")

        result = parse_recipe("/some/path/recipe.rb")

        assert "An error occurred: Unexpected" in result


def test_parse_attributes_success():
    """Test parse_attributes with valid attributes file."""
    attributes_content = """
default['nginx']['port'] = 80
default['nginx']['ssl_port'] = 443
override['nginx']['worker_processes'] = 4
default['nginx']['user'] = 'www-data'
    """
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.return_value = attributes_content

        result = parse_attributes("/cookbook/attributes/default.rb")

        assert "default[nginx.port] = 80" in result
        assert "default[nginx.ssl_port] = 443" in result
        assert "override[nginx.worker_processes] = 4" in result
        assert "default[nginx.user] = 'www-data'" in result


def test_parse_attributes_empty():
    """Test parse_attributes with no attributes."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.return_value = "# Just comments"

        result = parse_attributes("/cookbook/attributes/empty.rb")

        assert "Warning: No attributes found" in result


def test_parse_attributes_not_found():
    """Test parse_attributes with non-existent file."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = FileNotFoundError()

        result = parse_attributes("/nonexistent/attributes.rb")

        assert "Error: File not found" in result


def test_parse_attributes_is_directory():
    """Test parse_attributes when path is a directory."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = IsADirectoryError()

        result = parse_attributes("/some/directory")

        assert "Error:" in result
        assert "is a directory" in result


def test_parse_attributes_permission_denied():
    """Test parse_attributes with permission error."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = PermissionError()

        result = parse_attributes("/forbidden/attributes.rb")

        assert "Error: Permission denied" in result


def test_parse_attributes_unicode_error():
    """Test parse_attributes with unicode decode error."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = UnicodeDecodeError(
            "utf-8", b"", 0, 1, "invalid"
        )

        result = parse_attributes("/binary/file.rb")

        assert "Error: Unable to decode" in result
        assert "UTF-8" in result


def test_parse_attributes_other_exception():
    """Test parse_attributes with unexpected exception."""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.side_effect = Exception("Unexpected")

        result = parse_attributes("/some/path/attributes.rb")

        assert "An error occurred: Unexpected" in result


def test_list_cookbook_structure_success():
    """Test list_cookbook_structure with valid cookbook."""
    with patch("souschef.server.Path") as mock_path:
        mock_cookbook = MagicMock()
        mock_path.return_value = mock_cookbook
        mock_cookbook.is_dir.return_value = True

        # Mock the various subdirectories
        mock_recipes = MagicMock()
        mock_recipes.exists.return_value = True
        mock_recipes.is_dir.return_value = True
        mock_recipe_file1 = MagicMock()
        mock_recipe_file1.is_file.return_value = True
        mock_recipe_file1.name = "default.rb"
        mock_recipe_file2 = MagicMock()
        mock_recipe_file2.is_file.return_value = True
        mock_recipe_file2.name = "install.rb"
        mock_recipes.iterdir.return_value = [mock_recipe_file1, mock_recipe_file2]

        mock_attributes = MagicMock()
        mock_attributes.exists.return_value = True
        mock_attributes.is_dir.return_value = True
        mock_attr_file = MagicMock()
        mock_attr_file.is_file.return_value = True
        mock_attr_file.name = "default.rb"
        mock_attributes.iterdir.return_value = [mock_attr_file]

        mock_metadata = MagicMock()
        mock_metadata.exists.return_value = True

        # Mock the truediv operator for path joining
        def mock_truediv(self, other):
            if other == "recipes":
                return mock_recipes
            elif other == "attributes":
                return mock_attributes
            elif other == "metadata.rb":
                return mock_metadata
            else:
                mock_dir = MagicMock()
                mock_dir.exists.return_value = False
                return mock_dir

        mock_cookbook.__truediv__ = mock_truediv

        result = list_cookbook_structure("/cookbooks/nginx")

        assert "recipes/" in result
        assert "default.rb" in result
        assert "install.rb" in result
        assert "attributes/" in result
        assert "metadata/" in result


def test_list_cookbook_structure_empty():
    """Test list_cookbook_structure with empty directory."""
    with patch("souschef.server.Path") as mock_path:
        mock_cookbook = MagicMock()
        mock_path.return_value = mock_cookbook
        mock_cookbook.is_dir.return_value = True

        def mock_truediv(self, other):
            mock_dir = MagicMock()
            mock_dir.exists.return_value = False
            return mock_dir

        mock_cookbook.__truediv__ = mock_truediv

        result = list_cookbook_structure("/empty/cookbook")

        assert "Warning: No standard cookbook structure found" in result


def test_list_cookbook_structure_not_directory():
    """Test list_cookbook_structure with non-directory path."""
    with patch("souschef.server.Path") as mock_path:
        mock_cookbook = MagicMock()
        mock_path.return_value = mock_cookbook
        mock_cookbook.is_dir.return_value = False

        result = list_cookbook_structure("/some/file.txt")

        assert "Error:" in result
        assert "is not a directory" in result


def test_list_cookbook_structure_permission_denied():
    """Test list_cookbook_structure with permission error."""
    with patch("souschef.server.Path") as mock_path:
        mock_cookbook = MagicMock()
        mock_path.return_value = mock_cookbook
        mock_cookbook.is_dir.side_effect = PermissionError()

        result = list_cookbook_structure("/forbidden/cookbook")

        assert "Error: Permission denied" in result


def test_list_cookbook_structure_other_exception():
    """Test list_cookbook_structure with unexpected exception."""
    with patch("souschef.server.Path") as mock_path:
        mock_cookbook = MagicMock()
        mock_path.return_value = mock_cookbook
        mock_cookbook.is_dir.side_effect = Exception("Unexpected")

        result = list_cookbook_structure("/some/path")

        assert "An error occurred: Unexpected" in result
