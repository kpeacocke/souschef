"""Edge case and error path tests for server.py to improve coverage."""

import tempfile
from pathlib import Path

from souschef.server import (
    convert_resource_to_task,
    generate_inspec_from_recipe,
    list_cookbook_structure,
    parse_attributes,
    parse_cookbook_metadata,
    parse_custom_resource,
    parse_inspec_profile,
    parse_recipe,
    parse_template,
    read_cookbook_metadata,
    read_file,
)


class TestServerEdgeCases:
    """Test edge cases and error conditions in server.py."""

    def test_read_file_with_special_characters(self) -> None:
        """Test reading file with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "special_chars_€_ñ.txt"
            test_file.write_text("package 'test' # Comment with special chars: €, ñ")
            result = read_file(str(test_file))
            assert isinstance(result, str)

    def test_parse_recipe_with_inline_comments(self) -> None:
        """Test parsing recipe with inline comments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "comments.rb"
            recipe_file.write_text("""
package 'nginx' do  # Install nginx
  action :install
end  # End of package resource
            """)
            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_attributes_file_with_multiple_precedence_levels(self) -> None:
        """Test parsing attributes with all precedence levels."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attrs_file = Path(tmpdir) / "complex_attrs.rb"
            attrs_file.write_text("""
default['key1'] = 'value1'
normal['key2'] = 'value2'
override['key3'] = 'value3'
force_override['key4'] = 'value4'
            """)
            result = parse_attributes(str(attrs_file), resolve_precedence=True)
            assert isinstance(result, str)

    def test_parse_cookbook_metadata_with_maintainers(self) -> None:
        """Test parsing metadata with maintainer blocks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.rb"
            metadata_file.write_text("""
name 'test'
version '1.0.0'
maintainer 'John Doe'
maintainer_email 'john@example.com'
license 'Apache-2.0'
            """)
            result = parse_cookbook_metadata(str(metadata_file))
            assert isinstance(result, dict)

    def test_parse_cookbook_metadata_with_issues_url(self) -> None:
        """Test parsing metadata with issues_url."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.rb"
            metadata_file.write_text("""
name 'test'
version '1.0.0'
issues_url 'https://github.com/example/example/issues'
source_url 'https://github.com/example/example'
            """)
            result = parse_cookbook_metadata(str(metadata_file))
            assert isinstance(result, dict)

    def test_list_cookbook_structure_with_files_and_subdirs(self) -> None:
        """Test listing cookbook with deeply nested structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "metadata.rb").write_text("name 'test'")

            # Create nested structure
            recipes = base / "recipes"
            recipes.mkdir()
            (recipes / "default.rb").write_text("package 'test'")
            (recipes / "other.rb").write_text("service 'nginx'")

            attrs = base / "attributes"
            attrs.mkdir()
            (attrs / "default.rb").write_text("default['x'] = 1")

            templates = base / "templates"
            templates.mkdir()
            (templates / "test.erb").write_text("Hello <%= @name %>")

            resources = base / "resources"
            resources.mkdir()
            (resources / "custom.rb").write_text("property :name")

            result = list_cookbook_structure(str(base))
            assert isinstance(result, str)

    def test_parse_template_with_ruby_code(self) -> None:
        """Test parsing template with Ruby expressions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "complex.erb"
            template_file.write_text("""
<% if @debug %>
  DEBUG_MODE=true
  PORT=<%= @port %>
<% else %>
  DEBUG_MODE=false
  PORT=<%= @default_port %>
<% end %>

<% @servers.each do |server| %>
  Server: <%= server %>
<% end %>
            """)
            result = parse_template(str(template_file))
            assert isinstance(result, str)

    def test_parse_custom_resource_with_multiple_properties(self) -> None:
        """Test parsing custom resource with many properties."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resource_file = Path(tmpdir) / "complex_resource.rb"
            resource_file.write_text("""
property :name, String, required: true
property :port, Integer, default: 8080
property :debug, [true, false], default: false
action :create do
  file 'test'
end
            """)
            result = parse_custom_resource(str(resource_file))
            assert isinstance(result, str)

    def test_parse_inspec_profile_with_multiple_controls(self) -> None:
        """Test parsing InSpec profile with multiple controls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir)
            (profile_dir / "inspec.yml").write_text("name: test")

            controls = profile_dir / "controls"
            controls.mkdir()
            (controls / "default.rb").write_text("""
control 'test-1' do
  impact 1.0
  describe file('/etc/hosts') do
    it { should exist }
  end
end

control 'test-2' do
  impact 0.5
  describe package('nginx') do
    it { should be_installed }
  end
end
            """)
            result = parse_inspec_profile(str(profile_dir))
            assert isinstance(result, str)

    def test_convert_resource_to_task_with_properties(self) -> None:
        """Test converting resource to Ansible task."""
        result = convert_resource_to_task("package", "curl", "install", "")
        assert isinstance(result, str)

    def test_generate_inspec_from_recipe_empty_recipe(self) -> None:
        """Test generating InSpec from empty recipe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "empty.rb"
            recipe_file.write_text("")

            result = generate_inspec_from_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_recipe_with_blocks_and_conditionals(self) -> None:
        """Test parsing recipe with nested blocks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "complex.rb"
            recipe_file.write_text("""
if node['roles'].include?('web')
  package 'apache2' do
    action :install
  end

  template '/etc/apache2/apache2.conf' do
    source 'apache2.conf.erb'
    variables lazy {
      {
        port: node['apache']['port'],
        user: node['apache']['user']
      }
    }
  end
end

case node['platform']
when 'debian', 'ubuntu'
  service 'apache2'
when 'centos', 'fedora'
  service 'httpd'
end
            """)
            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_read_cookbook_metadata_large_file(self) -> None:
        """Test reading large metadata file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.rb"
            content = "name 'test'\n" * 100 + "version '1.0.0'\n"
            metadata_file.write_text(content)

            result = read_cookbook_metadata(str(metadata_file))
            assert isinstance(result, str)

    def test_list_cookbook_structure_with_hidden_files(self) -> None:
        """Test listing cookbook structure with hidden files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "metadata.rb").write_text("name 'test'")
            (base / ".hidden").write_text("hidden")
            (base / ".git").mkdir()
            (base / ".gitignore").write_text("*.pyc")

            result = list_cookbook_structure(str(base))
            assert isinstance(result, str)

    def test_parse_attributes_with_nested_hashes(self) -> None:
        """Test parsing attributes with nested hash structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attrs_file = Path(tmpdir) / "nested.rb"
            attrs_file.write_text("""
default['app'] = {
  'name' => 'MyApp',
  'db' => {
    'host' => 'localhost',
    'port' => 5432,
    'credentials' => {
      'user' => 'admin',
      'pass' => 'secret'
    }
  }
}
            """)
            result = parse_attributes(str(attrs_file), resolve_precedence=True)
            assert isinstance(result, str)

    def test_parse_recipe_with_guard_clauses(self) -> None:
        """Test parsing recipe with guard clauses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "guards.rb"
            recipe_file.write_text("""
package 'nginx' do
  action :install
  only_if { node['install_nginx'] }
end

service 'nginx' do
  action :start
  not_if { node['skip_services'] }
end
            """)
            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_convert_resource_to_task_package_resource(self) -> None:
        """Test converting package resource."""
        result = convert_resource_to_task(
            "package", "nginx", "install", "version='1.18'"
        )
        assert isinstance(result, str)

    def test_parse_inspec_profile_with_attributes(self) -> None:
        """Test parsing InSpec profile with attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir)
            (profile_dir / "inspec.yml").write_text("name: test")

            # Create attributes file
            attrs_file = profile_dir / "attributes.yml"
            attrs_file.write_text("""
port:
  description: 'Server port'
  value: 8080
            """)

            controls = profile_dir / "controls"
            controls.mkdir()
            (controls / "default.rb").write_text("""
control 'test' do
  describe port(input('port')) do
    it { should be_listening }
  end
end
            """)
            result = parse_inspec_profile(str(profile_dir))
            assert isinstance(result, str)
