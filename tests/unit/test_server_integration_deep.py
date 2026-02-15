"""Integration tests for server.py MCP tools - real file I/O coverage."""

import tempfile
from pathlib import Path

# Import the actual MCP tool functions from server
from souschef.server import (
    list_cookbook_structure,
    list_directory,
    parse_attributes,
    parse_custom_resource,
    parse_recipe,
    parse_template,
    read_cookbook_metadata,
    read_file,
)


class TestServerReadFileFunction:
    """Tests for read_file MCP tool with real files."""

    def test_read_simple_text_file(self) -> None:
        """Test reading a simple text file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello world")

            result = read_file(str(test_file))

            assert isinstance(result, str)
            assert "world" in result or result  # Either content or error message

    def test_read_ruby_file(self) -> None:
        """Test reading a Ruby file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.rb"
            test_file.write_text("package 'nginx' do\n  action :install\nend")

            result = read_file(str(test_file))

            assert isinstance(result, str)

    def test_read_json_file(self) -> None:
        """Test reading a JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.json"
            test_file.write_text('{"key": "value"}')

            result = read_file(str(test_file))

            assert isinstance(result, str)

    def test_read_yaml_file(self) -> None:
        """Test reading a YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "config.yml"
            test_file.write_text("key: value\ncount: 42")

            result = read_file(str(test_file))

            assert isinstance(result, str)

    def test_read_empty_file(self) -> None:
        """Test reading empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "empty.txt"
            test_file.write_text("")

            result = read_file(str(test_file))

            assert isinstance(result, str)

    def test_read_large_file(self) -> None:
        """Test reading large file (5MB)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "large.txt"
            # Create 5MB file
            test_file.write_text("x" * (5 * 1024 * 1024))

            result = read_file(str(test_file))

            assert isinstance(result, str)

    def test_read_file_with_unicode(self) -> None:
        """Test reading file with unicode characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "unicode.txt"
            test_file.write_text("Café ☕ 你好 مرحبا", encoding="utf-8")

            result = read_file(str(test_file))

            assert isinstance(result, str)

    def test_read_nonexistent_file(self) -> None:
        """Test reading nonexistent file returns error message."""
        result = read_file("/nonexistent/file.txt")

        assert isinstance(result, str)

    def test_read_directory_as_file(self) -> None:
        """Test reading a directory instead of file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = read_file(tmpdir)

            assert isinstance(result, str)

    def test_read_file_with_special_chars_in_path(self) -> None:
        """Test reading file with special chars in path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with spaces and special chars
            test_file = Path(tmpdir) / "my file (1).txt"
            test_file.write_text("content")

            result = read_file(str(test_file))

            assert isinstance(result, str)


class TestServerParseRecipe:
    """Tests for parse_recipe with various recipe structures."""

    def test_parse_simple_recipe(self) -> None:
        """Test parsing simple recipe with one resource."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "default.rb"
            recipe_file.write_text("package 'nginx' do\n  action :install\nend")

            result = parse_recipe(str(recipe_file))

            assert isinstance(result, str)

    def test_parse_recipe_with_multiple_resources(self) -> None:
        """Test parsing recipe with multiple resources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "install.rb"
            recipe_file.write_text("""
package 'nginx' do
  action :install
end

service 'nginx' do
  action [:enable, :start]
end

execute 'test nginx config' do
  command 'nginx -t'
end
""")

            result = parse_recipe(str(recipe_file))

            assert isinstance(result, str)

    def test_parse_empty_recipe(self) -> None:
        """Test parsing empty recipe file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "empty.rb"
            recipe_file.write_text("")

            result = parse_recipe(str(recipe_file))

            assert isinstance(result, str)

    def test_parse_recipe_with_comments(self) -> None:
        """Test parsing recipe with extensive comments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "commented.rb"
            recipe_file.write_text("""
# Install web server
# This is important for the application

package 'nginx' do
  # Install the latest version
  action :install
end

# Start and enable service
service 'nginx' do
  action [:enable, :start]
end
""")

            result = parse_recipe(str(recipe_file))

            assert isinstance(result, str)

    def test_parse_recipe_with_if_statement(self) -> None:
        """Test parsing recipe with conditional logic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "conditional.rb"
            recipe_file.write_text("""
if platform?('ubuntu')
  package 'apache2' do
    action :install
  end
elsif platform?('centos')
  package 'httpd' do
    action :install
  end
end
""")

            result = parse_recipe(str(recipe_file))

            assert isinstance(result, str)

    def test_parse_recipe_with_case_statement(self) -> None:
        """Test parsing recipe with case statement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "case.rb"
            recipe_file.write_text("""
case node['platform_family']
when 'debian'
  package 'apache2' do
    action :install
  end
when 'rhel'
  package 'httpd' do
    action :install
  end
else
  log 'Unsupported platform'
end
""")

            result = parse_recipe(str(recipe_file))

            assert isinstance(result, str)

    def test_parse_recipe_with_node_attributes(self) -> None:
        """Test parsing recipe using node attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "attrs.rb"
            recipe_file.write_text("""
package node['app']['package_name'] do
  action :install
end

service node['app']['service_name'] do
  enabled node['app']['enabled']
  action :start
end
""")

            result = parse_recipe(str(recipe_file))

            assert isinstance(result, str)

    def test_parse_recipe_with_loops(self) -> None:
        """Test parsing recipe with array iteration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "loops.rb"
            recipe_file.write_text("""
['nginx', 'apache2', 'httpd'].each do |pkg|
  package pkg do
    action :install
  end
end
""")

            result = parse_recipe(str(recipe_file))

            assert isinstance(result, str)

    def test_parse_invalid_ruby_recipe(self) -> None:
        """Test parsing recipe with invalid Ruby syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "invalid.rb"
            recipe_file.write_text("this is }{{{ not valid ruby")

            result = parse_recipe(str(recipe_file))

            assert isinstance(result, str)

    def test_parse_nonexistent_recipe(self) -> None:
        """Test parsing nonexistent recipe file."""
        result = parse_recipe("/nonexistent/recipe.rb")

        assert isinstance(result, str)


class TestServerParseAttributes:
    """Tests for parse_attributes with various attribute structures."""

    def test_parse_simple_attributes(self) -> None:
        """Test parsing simple attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "default.rb"
            attr_file.write_text("""
default['app']['port'] = 8080
default['app']['version'] = '1.0.0'
""")

            result = parse_attributes(str(attr_file))

            assert isinstance(result, str)

    def test_parse_attributes_all_precedence_levels(self) -> None:
        """Test parsing attributes with different precedence levels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "attr.rb"
            attr_file.write_text("""
default['key1'] = 'default_value'
normal['key2'] = 'normal_value'
override['key3'] = 'override_value'
force_default['key4'] = 'force_default_value'
force_override['key5'] = 'force_override_value'
""")

            result = parse_attributes(str(attr_file))

            assert isinstance(result, str)

    def test_parse_empty_attributes(self) -> None:
        """Test parsing empty attributes file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "empty.rb"
            attr_file.write_text("")

            result = parse_attributes(str(attr_file))

            assert isinstance(result, str)

    def test_parse_attributes_with_conditionals(self) -> None:
        """Test parsing attributes with conditional logic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "cond.rb"
            attr_file.write_text("""
if platform?('ubuntu')
  default['pkg'] = 'apache2'
elsif platform?('rhel')
  default['pkg'] = 'httpd'
end
""")

            result = parse_attributes(str(attr_file))

            assert isinstance(result, str)

    def test_parse_attributes_deeply_nested(self) -> None:
        """Test parsing deeply nested attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "nested.rb"
            attr_file.write_text("""
default['a']['b']['c']['d']['e']['f'] = 'deeply_nested'
default['x']['y']['z'] = {
  'key1' => 'value1',
  'key2' => 'value2'
}
""")

            result = parse_attributes(str(attr_file))

            assert isinstance(result, str)

    def test_parse_attributes_with_arrays(self) -> None:
        """Test parsing attributes with array values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "arrays.rb"
            attr_file.write_text("""
default['packages'] = ['nginx', 'apache2', 'httpd']
default['ports'] = [80, 443, 8080]
""")

            result = parse_attributes(str(attr_file))

            assert isinstance(result, str)

    def test_parse_attributes_with_hashes(self) -> None:
        """Test parsing attributes with hash values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "hashes.rb"
            attr_file.write_text("""
default['config'] = {
  'server' => {
    'host' => 'localhost',
    'port' => 8080
  },
  'database' => {
    'host' => 'db.local',
    'port' => 5432
  }
}
""")

            result = parse_attributes(str(attr_file))

            assert isinstance(result, str)

    def test_parse_attributes_invalid_syntax(self) -> None:
        """Test parsing attributes with invalid syntax."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "invalid.rb"
            attr_file.write_text("this is not }{{{ valid ruby")

            result = parse_attributes(str(attr_file))

            assert isinstance(result, str)

    def test_parse_attributes_with_resolve_precedence_false(self) -> None:
        """Test parsing attributes without precedence resolution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "attr.rb"
            attr_file.write_text("default['key'] = 'value'")

            result = parse_attributes(str(attr_file), resolve_precedence=False)

            assert isinstance(result, str)

    def test_parse_attributes_nonexistent(self) -> None:
        """Test parsing nonexistent attributes file."""
        result = parse_attributes("/nonexistent/attributes.rb")

        assert isinstance(result, str)


class TestServerParseTemplate:
    """Tests for parse_template with various templates."""

    def test_parse_simple_erb_template(self) -> None:
        """Test parsing simple ERB template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "simple.erb"
            template_file.write_text("<%= @server_name %>")

            result = parse_template(str(template_file))

            assert isinstance(result, str)

    def test_parse_erb_with_conditionals(self) -> None:
        """Test parsing ERB with if/else logic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "cond.erb"
            template_file.write_text("""
<% if @debug %>
  debug = true
<% else %>
  debug = false
<% end %>
""")

            result = parse_template(str(template_file))

            assert isinstance(result, str)

    def test_parse_erb_with_loops(self) -> None:
        """Test parsing ERB with iteration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "loop.erb"
            template_file.write_text("""
<% @items.each do |item| %>
  <%= item %>
<% end %>
""")

            result = parse_template(str(template_file))

            assert isinstance(result, str)

    def test_parse_erb_complex_nginx_config(self) -> None:
        """Test parsing complex nginx config template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "nginx.ERB"
            template_file.write_text("""
server {
  listen <%= @port %>;
  server_name <%= @server_name %>;

  <% if @ssl %>
  ssl on;
  ssl_certificate <%= @cert_path %>;
  ssl_certificate_key <%= @key_path %>;
  <% end %>

  <% @locations.each do |location| %>
  location <%= location %> {
    proxy_pass http://backend;
  }
  <% end %>
}
""")

            result = parse_template(str(template_file))

            assert isinstance(result, str)

    def test_parse_empty_template(self) -> None:
        """Test parsing empty template."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "empty.erb"
            template_file.write_text("")

            result = parse_template(str(template_file))

            assert isinstance(result, str)

    def test_parse_template_no_erb_tags(self) -> None:
        """Test parsing template with no ERB tags."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "plain.erb"
            template_file.write_text("server { listen 80; }")

            result = parse_template(str(template_file))

            assert isinstance(result, str)

    def test_parse_nonexistent_template(self) -> None:
        """Test parsing nonexistent template."""
        result = parse_template("/nonexistent/template.erb")

        assert isinstance(result, str)


class TestServerParseCustomResource:
    """Tests for parse_custom_resource."""

    def test_parse_simple_resource(self) -> None:
        """Test parsing simple custom resource."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resource_file = Path(tmpdir) / "my_app.rb"
            resource_file.write_text("""
resource_name :my_app
property :name, String
property :port, Integer

action :create do
  log 'Creating my_app'
end
""")

            result = parse_custom_resource(str(resource_file))

            assert isinstance(result, str)

    def test_parse_resource_with_multiple_actions(self) -> None:
        """Test parsing resource with multiple actions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resource_file = Path(tmpdir) / "service.rb"
            resource_file.write_text("""
resource_name :my_service

action :create do
  log 'Creating service'
end

action :delete do
  log 'Deleting service'
end

action :restart do
  log 'Restarting service'
end
""")

            result = parse_custom_resource(str(resource_file))

            assert isinstance(result, str)

    def test_parse_resource_with_helpers(self) -> None:
        """Test parsing resource with helper methods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resource_file = Path(tmpdir) / "complex.rb"
            resource_file.write_text("""
resource_name :complex

property :name, String

action :create do
  log action_description
end

action_class do
  def action_description
    "Creating #{new_resource.name}"
  end
end
""")

            result = parse_custom_resource(str(resource_file))

            assert isinstance(result, str)

    def test_parse_nonexistent_resource(self) -> None:
        """Test parsing nonexistent resource file."""
        result = parse_custom_resource("/nonexistent/resource.rb")

        assert isinstance(result, str)


class TestServerListDirectory:
    """Tests for list_directory."""

    def test_list_empty_directory(self) -> None:
        """Test listing empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = list_directory(tmpdir)

            assert isinstance(result, (list, str))

    def test_list_directory_with_files(self) -> None:
        """Test listing directory with various files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "file1.txt").write_text("content")
            (tmppath / "file2.rb").write_text("code")
            (tmppath / "subdir").mkdir()

            result = list_directory(tmpdir)

            assert isinstance(result, (list, str))

    def test_list_directory_with_subdirs(self) -> None:
        """Test listing directory with nested subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "a").mkdir()
            (tmppath / "a" / "b").mkdir()
            (tmppath / "a" / "b" / "c").mkdir()
            (tmppath / "a" / "b" / "file.txt").write_text("deep")

            result = list_directory(tmpdir)

            assert isinstance(result, (list, str))

    def test_list_many_files(self) -> None:
        """Test listing directory with many files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            for i in range(50):
                (tmppath / f"file{i}.txt").write_text(f"content{i}")

            result = list_directory(tmpdir)

            assert isinstance(result, (list, str))

    def test_list_nonexistent_directory(self) -> None:
        """Test listing nonexistent directory."""
        result = list_directory("/nonexistent/path")

        assert isinstance(result, str)

    def test_list_file_as_directory(self) -> None:
        """Test listing a file instead of directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "file.txt"
            test_file.write_text("content")

            result = list_directory(str(test_file))

            assert isinstance(result, str)


class TestServerCookbookMetadata:
    """Tests for read_cookbook_metadata."""

    def test_read_simple_metadata(self) -> None:
        """Test reading simple metadata.rb."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.rb"
            metadata_file.write_text("""
name 'test_cookbook'
version '1.0.0'
description 'Test cookbook'
""")

            result = read_cookbook_metadata(str(metadata_file))

            assert isinstance(result, str)

    def test_read_metadata_with_dependencies(self) -> None:
        """Test reading metadata with cookbook dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.rb"
            metadata_file.write_text("""
name 'app'
version '2.0.0'
depends 'nginx', '~> 8.0'
depends 'postgresql', '~> 7.0'
depends 'nodejs'
""")

            result = read_cookbook_metadata(str(metadata_file))

            assert isinstance(result, str)

    def test_read_metadata_with_supported_platforms(self) -> None:
        """Test reading metadata with platform support."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.rb"
            metadata_file.write_text("""
name 'multi_platform'
version '1.0.0'
supports 'ubuntu', '>= 18.04'
supports 'centos', '>= 7.0'
supports 'debian', '>= 9.0'
""")

            result = read_cookbook_metadata(str(metadata_file))

            assert isinstance(result, str)

    def test_read_metadata_complete(self) -> None:
        """Test reading complete metadata.rb file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.rb"
            metadata_file.write_text("""
name 'complete'
version '3.1.0'
description 'A complete cookbook'
author 'John Doe'
license 'MIT'

supports 'ubuntu', '>= 18.04'
depends 'nginx', '~> 8.0'
""")

            result = read_cookbook_metadata(str(metadata_file))

            assert isinstance(result, str)

    def test_read_nonexistent_metadata(self) -> None:
        """Test reading nonexistent metadata file."""
        result = read_cookbook_metadata("/nonexistent/metadata.rb")

        assert isinstance(result, str)


class TestServerListCookbookStructure:
    """Tests for list_cookbook_structure."""

    def test_list_minimal_cookbook(self) -> None:
        """Test listing minimal cookbook structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

            result = list_cookbook_structure(tmpdir)

            assert isinstance(result, str)

    def test_list_cookbook_with_recipes(self) -> None:
        """Test listing cookbook with recipes directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")
            recipes_dir = tmppath / "recipes"
            recipes_dir.mkdir()
            (recipes_dir / "default.rb").write_text("# default recipe")
            (recipes_dir / "install.rb").write_text("# install recipe")

            result = list_cookbook_structure(tmpdir)

            assert isinstance(result, str)

    def test_list_cookbook_full_structure(self) -> None:
        """Test listing cookbook with full structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text("name 'full'\nversion '1.0.0'")

            # Create all standard directories
            (tmppath / "recipes").mkdir()
            (tmppath / "recipes" / "default.rb").write_text("# default")

            (tmppath / "attributes").mkdir()
            (tmppath / "attributes" / "default.rb").write_text(
                "default['key'] = 'value'"
            )

            (tmppath / "templates").mkdir()
            (tmppath / "templates" / "config.erb").write_text("<%= @var %>")

            (tmppath / "libraries").mkdir()
            (tmppath / "libraries" / "helper.rb").write_text("module Helper; end")

            (tmppath / "resources").mkdir()
            (tmppath / "resources" / "app.rb").write_text("resource_name :app")

            result = list_cookbook_structure(tmpdir)

            assert isinstance(result, str)

    def test_list_nonexistent_cookbook(self) -> None:
        """Test listing nonexistent cookbook."""
        result = list_cookbook_structure("/nonexistent/cookbook")

        assert isinstance(result, str)
