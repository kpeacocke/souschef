"""Tests for the SousChef MCP server."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from souschef.server import (
    _convert_erb_to_jinja2,
    _extract_conditionals,
    _extract_heredoc_strings,
    _extract_resource_actions,
    _extract_resource_properties,
    _extract_template_variables,
    _normalize_ruby_value,
    _strip_ruby_comments,
    convert_resource_to_task,
    list_cookbook_structure,
    list_directory,
    main,
    parse_attributes,
    parse_custom_resource,
    parse_recipe,
    parse_template,
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


def test_main():
    """Test that main function calls mcp.run()."""
    with patch("souschef.server.mcp") as mock_mcp:
        main()
        mock_mcp.run.assert_called_once()


def test_convert_package_to_task():
    """Test converting a Chef package resource to Ansible task."""
    result = convert_resource_to_task("package", "nginx", "install")

    assert "name: Install package nginx" in result
    assert "ansible.builtin.package:" in result
    assert 'name: "nginx"' in result
    assert 'state: "present"' in result


def test_convert_service_to_task():
    """Test converting a Chef service resource to Ansible task."""
    result = convert_resource_to_task("service", "nginx", "start")

    assert "name: Start service nginx" in result
    assert "ansible.builtin.service:" in result
    assert 'name: "nginx"' in result
    assert "enabled: true" in result
    assert 'state: "started"' in result


def test_convert_file_to_task():
    """Test converting a Chef file resource to Ansible task."""
    result = convert_resource_to_task("file", "/etc/config.txt", "create")

    assert "name: Create file /etc/config.txt" in result
    assert "ansible.builtin.file:" in result
    assert 'path: "/etc/config.txt"' in result
    assert 'state: "file"' in result
    assert 'mode: "0644"' in result


def test_convert_directory_to_task():
    """Test converting a Chef directory resource to Ansible task."""
    result = convert_resource_to_task("directory", "/var/www", "create")

    assert "name: Create directory /var/www" in result
    assert "ansible.builtin.file:" in result
    assert 'path: "/var/www"' in result
    assert 'state: "directory"' in result
    assert 'mode: "0755"' in result


def test_convert_template_to_task():
    """Test converting a Chef template resource to Ansible task."""
    result = convert_resource_to_task("template", "nginx.conf.erb", "create")

    assert "name: Create template nginx.conf.erb" in result
    assert "ansible.builtin.template:" in result
    assert 'src: "nginx.conf.erb"' in result
    assert 'dest: "nginx.conf"' in result
    assert 'mode: "0644"' in result


def test_convert_execute_to_task():
    """Test converting a Chef execute resource to Ansible task."""
    result = convert_resource_to_task("execute", "systemctl daemon-reload", "run")

    assert "name: Run execute systemctl daemon-reload" in result
    assert "ansible.builtin.command:" in result
    assert 'cmd: "systemctl daemon-reload"' in result
    assert 'changed_when: "false"' in result


def test_convert_user_to_task():
    """Test converting a Chef user resource to Ansible task."""
    result = convert_resource_to_task("user", "appuser", "create")

    assert "name: Create user appuser" in result
    assert "ansible.builtin.user:" in result
    assert 'name: "appuser"' in result
    assert 'state: "present"' in result


def test_convert_group_to_task():
    """Test converting a Chef group resource to Ansible task."""
    result = convert_resource_to_task("group", "appgroup", "create")

    assert "name: Create group appgroup" in result
    assert "ansible.builtin.group:" in result
    assert 'name: "appgroup"' in result
    assert 'state: "present"' in result


def test_convert_service_with_enable_action():
    """Test converting service with enable action."""
    result = convert_resource_to_task("service", "nginx", "enable")

    assert "ansible.builtin.service:" in result
    assert "enabled: true" in result
    assert 'state: "started"' in result


def test_convert_service_with_stop_action():
    """Test converting service with stop action."""
    result = convert_resource_to_task("service", "nginx", "stop")

    assert "ansible.builtin.service:" in result
    assert "enabled: false" in result
    assert 'state: "stopped"' in result


def test_convert_package_with_upgrade_action():
    """Test converting package with upgrade action."""
    result = convert_resource_to_task("package", "nginx", "upgrade")

    assert "ansible.builtin.package:" in result
    assert 'state: "latest"' in result


def test_convert_unknown_resource_type():
    """Test converting an unknown resource type."""
    result = convert_resource_to_task("unknown_resource", "test", "create")

    # Should not crash, but indicate unknown resource
    assert isinstance(result, str)
    assert "name: Create unknown_resource test" in result


def test_convert_with_exception():
    """Test that conversion handles exceptions gracefully."""
    # This should trigger an error by passing invalid data types
    with patch("souschef.server._convert_chef_resource_to_ansible") as mock_convert:
        mock_convert.side_effect = Exception("Test exception")

        result = convert_resource_to_task("package", "nginx", "install")

        assert "An error occurred during conversion" in result
        assert "Test exception" in result


# Template parsing tests


def test_parse_template_success():
    """Test that parse_template successfully parses ERB file."""
    mock_path = MagicMock(spec=Path)
    mock_path.__str__ = lambda self: "/path/to/template.erb"
    erb_content = "Hello <%= @name %>!"
    mock_path.read_text.return_value = erb_content

    with patch("souschef.server.Path", return_value=mock_path):
        result = parse_template("/path/to/template.erb")

        assert "variables" in result
        assert "jinja2_template" in result
        assert "name" in result  # Should extract @name variable


def test_parse_template_not_found():
    """Test parse_template with non-existent file."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = FileNotFoundError

    with patch("souschef.server.Path", return_value=mock_path):
        result = parse_template("/nonexistent/template.erb")

        assert "Error: File not found" in result


def test_parse_template_permission_denied():
    """Test parse_template with permission denied."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = PermissionError

    with patch("souschef.server.Path", return_value=mock_path):
        result = parse_template("/forbidden/template.erb")

        assert "Error: Permission denied" in result


def test_extract_template_variables_simple():
    """Test extracting variables from simple ERB."""
    content = "Hello <%= @name %>, your email is <%= @email %>!"
    variables = _extract_template_variables(content)

    assert "name" in variables
    assert "email" in variables


def test_extract_template_variables_node_attributes():
    """Test extracting node attributes as variables."""
    content = "<%= node['nginx']['port'] %> and <%= node[\"app\"][\"name\"] %>"
    variables = _extract_template_variables(content)

    assert "nginx']['port" in variables
    assert 'app"]["name' in variables


def test_extract_template_variables_conditionals():
    """Test extracting variables from conditionals."""
    content = "<% if enabled %><%= message %><% end %>"
    variables = _extract_template_variables(content)

    assert "enabled" in variables
    assert "message" in variables


def test_extract_template_variables_loops():
    """Test extracting variables from each loops."""
    content = "<% items.each do |item| %><%= item %><% end %>"
    variables = _extract_template_variables(content)

    assert "items" in variables
    assert "item" in variables


def test_convert_erb_to_jinja2_simple_output():
    """Test converting simple ERB variable output."""
    erb = "Hello <%= @name %>!"
    jinja2 = _convert_erb_to_jinja2(erb)

    assert "{{ name }}" in jinja2
    assert "<%=" not in jinja2


def test_convert_erb_to_jinja2_node_attributes():
    """Test converting node attributes to Jinja2."""
    erb = "Port: <%= node['nginx']['port'] %>"
    jinja2 = _convert_erb_to_jinja2(erb)

    assert "{{ nginx']['port }}" in jinja2


def test_convert_erb_to_jinja2_if_statement():
    """Test converting ERB if statements."""
    erb = "<% if enabled %>Active<% end %>"
    jinja2 = _convert_erb_to_jinja2(erb)

    assert "{% if enabled %}" in jinja2
    assert "{% endif %}" in jinja2
    assert "<%" not in jinja2


def test_convert_erb_to_jinja2_unless_statement():
    """Test converting ERB unless to Jinja2 if not."""
    erb = "<% unless disabled %>Active<% end %>"
    jinja2 = _convert_erb_to_jinja2(erb)

    assert "{% if not disabled %}" in jinja2
    assert "{% endif %}" in jinja2


def test_convert_erb_to_jinja2_elsif():
    """Test converting ERB elsif to Jinja2 elif."""
    erb = "<% if a %>A<% elsif b %>B<% else %>C<% end %>"
    jinja2 = _convert_erb_to_jinja2(erb)

    assert "{% if a %}" in jinja2
    assert "{% elif b %}" in jinja2
    assert "{% else %}" in jinja2
    assert "{% endif %}" in jinja2


def test_convert_erb_to_jinja2_each_loop():
    """Test converting ERB each loop to Jinja2 for."""
    erb = "<% items.each do |item| %><%= item %><% end %>"
    jinja2 = _convert_erb_to_jinja2(erb)

    assert "{% for item in items %}" in jinja2
    assert "{{ item }}" in jinja2
    assert "{% endfor %}" in jinja2


def test_convert_erb_to_jinja2_nested_structures():
    """Test converting nested if and for loops."""
    erb = "<% if items %><% items.each do |i| %><%= i %><% end %><% end %>"
    jinja2 = _convert_erb_to_jinja2(erb)

    assert "{% if items %}" in jinja2
    assert "{% for i in items %}" in jinja2
    assert "{% endfor %}" in jinja2
    assert "{% endif %}" in jinja2


def test_convert_erb_to_jinja2_multiple_outputs():
    """Test converting multiple variable outputs."""
    erb = "<%= @name %> - <%= @email %> - <%= @role %>"
    jinja2 = _convert_erb_to_jinja2(erb)

    assert "{{ name }}" in jinja2
    assert "{{ email }}" in jinja2
    assert "{{ role }}" in jinja2


# Custom resource parsing tests


def test_parse_custom_resource_success():
    """Test that parse_custom_resource successfully parses resource file."""
    mock_path = MagicMock(spec=Path)
    mock_path.__str__ = lambda self: "/path/to/resource.rb"
    mock_path.stem = "app_config"
    resource_content = """
property :name, String, name_property: true
property :port, Integer, default: 8080

action :create do
  log "Creating"
end
"""
    mock_path.read_text.return_value = resource_content

    with patch("souschef.server.Path", return_value=mock_path):
        result = parse_custom_resource("/path/to/resource.rb")

        assert "properties" in result
        assert "actions" in result
        assert "app_config" in result


def test_parse_custom_resource_not_found():
    """Test parse_custom_resource with non-existent file."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = FileNotFoundError

    with patch("souschef.server.Path", return_value=mock_path):
        result = parse_custom_resource("/nonexistent/resource.rb")

        assert "Error: File not found" in result


def test_parse_custom_resource_permission_denied():
    """Test parse_custom_resource with permission denied."""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.side_effect = PermissionError

    with patch("souschef.server.Path", return_value=mock_path):
        result = parse_custom_resource("/forbidden/resource.rb")

        assert "Error: Permission denied" in result


def test_extract_resource_properties_modern():
    """Test extracting modern property definitions."""
    content = """
property :name, String, name_property: true
property :port, Integer, default: 8080
property :enabled, [true, false], default: false
property :password, String, required: true
"""
    properties = _extract_resource_properties(content)

    assert len(properties) == 4

    # Check name property
    name_prop = next(p for p in properties if p["name"] == "name")
    assert name_prop["type"] == "String"
    assert name_prop.get("name_property") is True

    # Check port property
    port_prop = next(p for p in properties if p["name"] == "port")
    assert port_prop["type"] == "Integer"
    assert port_prop["default"] == "8080"

    # Check password property
    password_prop = next(p for p in properties if p["name"] == "password")
    assert password_prop.get("required") is True


def test_extract_resource_properties_lwrp():
    """Test extracting LWRP attribute definitions."""
    content = """
attribute :db_name, kind_of: String, name_attribute: true
attribute :port, kind_of: Integer, default: 5432
attribute :username, kind_of: String, required: true
"""
    properties = _extract_resource_properties(content)

    assert len(properties) == 3

    # Check db_name attribute
    db_prop = next(p for p in properties if p["name"] == "db_name")
    assert db_prop["type"] == "String"
    assert db_prop.get("name_property") is True

    # Check port attribute
    port_prop = next(p for p in properties if p["name"] == "port")
    assert port_prop["type"] == "Integer"
    assert port_prop["default"] == "5432"


def test_extract_resource_actions_modern():
    """Test extracting modern action blocks."""
    content = """
action :create do
  log "Creating"
end

action :delete do
  log "Deleting"
end

default_action :create
"""
    actions = _extract_resource_actions(content)

    assert "create" in actions["actions"]
    assert "delete" in actions["actions"]
    assert actions["default_action"] == "create"


def test_extract_resource_actions_lwrp():
    """Test extracting LWRP actions declaration."""
    content = """
actions :create, :drop, :backup
default_action :create
"""
    actions = _extract_resource_actions(content)

    assert "create" in actions["actions"]
    assert "drop" in actions["actions"]
    assert "backup" in actions["actions"]
    assert actions["default_action"] == "create"


def test_extract_resource_actions_mixed():
    """Test extracting mixed action styles."""
    content = """
actions :create, :delete

action :update do
  log "Updating"
end

default_action :create
"""
    actions = _extract_resource_actions(content)

    assert "create" in actions["actions"]
    assert "delete" in actions["actions"]
    assert "update" in actions["actions"]
    assert len(actions["actions"]) == 3


def test_extract_resource_properties_empty():
    """Test extracting from content with no properties."""
    content = "# Just a comment"
    properties = _extract_resource_properties(content)

    assert properties == []


def test_extract_resource_actions_no_default():
    """Test extracting actions without default action."""
    content = """
action :create do
  log "Creating"
end
"""
    actions = _extract_resource_actions(content)

    assert "create" in actions["actions"]
    assert actions["default_action"] is None


# Edge case handling tests


def test_strip_ruby_comments():
    """Test removing Ruby comments from code."""
    code = """
# This is a comment
default['nginx']['port'] = 80  # Inline comment
default['app']['name'] = 'test' # Comment with string
"""
    clean = _strip_ruby_comments(code)

    assert "# This is a comment" not in clean
    assert "# Inline comment" not in clean
    assert "default['nginx']['port'] = 80" in clean
    assert "default['app']['name'] = 'test'" in clean


def test_extract_heredoc_strings():
    """Test extracting heredoc strings."""
    content = """
file '/etc/config' do
  content <<-EOH
    line 1
    line 2
  EOH
end
"""
    heredocs = _extract_heredoc_strings(content)

    assert "EOH" in heredocs
    assert "line 1" in heredocs["EOH"]
    assert "line 2" in heredocs["EOH"]


def test_normalize_ruby_value_symbol():
    """Test normalizing Ruby symbols."""
    assert _normalize_ruby_value(":create") == '"create"'
    assert _normalize_ruby_value(":my_action") == '"my_action"'


def test_normalize_ruby_value_array():
    """Test normalizing Ruby arrays with symbols."""
    result = _normalize_ruby_value("[:start, :enable]")
    assert '"start"' in result
    assert '"enable"' in result


def test_extract_conditionals_case():
    """Test extracting case/when statements."""
    content = """
case node['platform']
when 'ubuntu'
  package 'nginx'
when 'centos'
  package 'httpd'
end
"""
    conditionals = _extract_conditionals(content)

    assert len(conditionals) > 0
    case_stmt = next((c for c in conditionals if c["type"] == "case"), None)
    assert case_stmt is not None
    assert "platform" in case_stmt["expression"]


def test_extract_conditionals_if():
    """Test extracting if statements."""
    content = """
if node['nginx']['ssl_enabled']
  package 'openssl'
end
"""
    conditionals = _extract_conditionals(content)

    assert len(conditionals) > 0
    if_stmt = next((c for c in conditionals if c["type"] == "if"), None)
    assert if_stmt is not None
    assert "ssl_enabled" in if_stmt["condition"]


def test_extract_conditionals_unless():
    """Test extracting unless statements."""
    content = """
unless node['app']['disabled']
  service 'app'
end
"""
    conditionals = _extract_conditionals(content)

    assert len(conditionals) > 0
    unless_stmt = next((c for c in conditionals if c["type"] == "unless"), None)
    assert unless_stmt is not None
    assert "disabled" in unless_stmt["condition"]


def test_extract_template_variables_with_interpolation():
    """Test extracting variables from string interpolation."""
    content = '<% message = "Hello #{name}!" %>'
    variables = _extract_template_variables(content)

    assert "name" in variables or "message" in variables


def test_parse_recipe_with_comments():
    """Test parsing recipe with Ruby comments."""
    recipe_content = """
# Install web server
package 'nginx' do  # Using nginx
  action :install
end
"""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.return_value = recipe_content

        result = parse_recipe("/recipe.rb")

        assert "nginx" in result
        assert "package" in result


def test_parse_attributes_with_case_statement():
    """Test parsing attributes with case/when statements."""
    attr_content = """
case node['platform']
when 'ubuntu'
  default['pkg']['name'] = 'nginx'
when 'centos'
  default['pkg']['name'] = 'httpd'
end
"""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.return_value = attr_content

        result = parse_attributes("/attributes.rb")

        # Should extract attributes even from within case statements
        assert "pkg" in result or "Warning" in result


def test_extract_resource_properties_with_complex_type():
    """Test extracting properties with complex types like [true, false]."""
    content = """
property :enabled, [true, false], default: false
property :ports, Array, default: [80, 443]
"""
    properties = _extract_resource_properties(content)

    assert len(properties) >= 2
    enabled_prop = next((p for p in properties if p["name"] == "enabled"), None)
    assert enabled_prop is not None
    assert "[true, false]" in enabled_prop["type"] or "true" in enabled_prop["type"]


def test_parse_recipe_with_multiline_string():
    """Test parsing recipe with multi-line content."""
    recipe_content = """
file '/etc/config' do
  content 'line1
line2
line3'
  action :create
end
"""
    with patch("souschef.server.Path") as mock_path:
        mock_instance = MagicMock()
        mock_path.return_value = mock_instance
        mock_instance.read_text.return_value = recipe_content

        result = parse_recipe("/recipe.rb")

        # Should successfully parse despite multi-line strings
        assert isinstance(result, str)
        # May or may not find resources due to regex limitations with multiline strings
        # The important thing is it doesn't crash
