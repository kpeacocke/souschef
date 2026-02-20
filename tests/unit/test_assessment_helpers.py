"""Tests for assessment.py helper functions."""

import tempfile
from pathlib import Path

from souschef.assessment import (
    _analyze_attributes,
    _analyze_libraries,
    _analyze_recipes,
    _analyze_templates,
    _count_definitions,
    _parse_berksfile,
)


class TestAnalyzeRecipes:
    """Test _analyze_recipes function."""

    def test_analyze_recipes_empty_cookbook(self):
        """Test analyzing cookbook with no recipes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            cookbook_path.mkdir()

            resource_count, ruby_blocks, custom_resources = _analyze_recipes(
                cookbook_path
            )

            assert resource_count == 0
            assert ruby_blocks == 0
            assert custom_resources == 0

    def test_analyze_recipes_with_basic_resources(self):
        """Test analyzing recipes with basic Chef resources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            recipes_dir = cookbook_path / "recipes"
            recipes_dir.mkdir(parents=True)

            recipe_file = recipes_dir / "default.rb"
            recipe_file.write_text("""
package 'apache2' do
  action :install
end

service 'apache2' do
  action [:enable, :start]
end
""")

            resource_count, ruby_blocks, custom_resources = _analyze_recipes(
                cookbook_path
            )

            assert resource_count >= 2  # package and service
            assert ruby_blocks == 0
            assert custom_resources == 0

    def test_analyze_recipes_with_ruby_blocks(self):
        """Test analyzing recipes with ruby_block resources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            recipes_dir = cookbook_path / "recipes"
            recipes_dir.mkdir(parents=True)

            recipe_file = recipes_dir / "default.rb"
            recipe_file.write_text("""
ruby_block 'update config' do
  block do
    # Ruby code here
  end
end

execute 'run command' do
  command 'echo hello'
end

bash 'install deps' do
  code <<-EOH
    apt-get update
  EOH
end
""")

            _, ruby_blocks, _ = _analyze_recipes(cookbook_path)

            assert ruby_blocks >= 3  # ruby_block, execute, bash

    def test_analyze_recipes_with_custom_resources(self):
        """Test analyzing recipes with custom resource declarations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            recipes_dir = cookbook_path / "recipes"
            recipes_dir.mkdir(parents=True)

            recipe_file = recipes_dir / "default.rb"
            recipe_file.write_text("""
provides :my_resource
use_inline_resources

custom_resource 'app' do
  property :path, String
end
""")

            _, _, custom_resources = _analyze_recipes(cookbook_path)

            assert custom_resources >= 1

    def test_analyze_recipes_multiple_files(self):
        """Test analyzing multiple recipe files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            recipes_dir = cookbook_path / "recipes"
            recipes_dir.mkdir(parents=True)

            # Create multiple recipe files
            (recipes_dir / "default.rb").write_text("package 'nginx' do\nend")
            (recipes_dir / "web.rb").write_text("service 'nginx' do\nend")
            (recipes_dir / "db.rb").write_text("package 'mysql' do\nend")

            resource_count, _, _ = _analyze_recipes(cookbook_path)

            assert resource_count >= 3


class TestAnalyzeAttributes:
    """Test _analyze_attributes function."""

    def test_analyze_attributes_empty_cookbook(self):
        """Test analyzing cookbook with no attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            cookbook_path.mkdir()

            complexity = _analyze_attributes(cookbook_path)

            assert complexity == 0

    def test_analyze_attributes_simple_assignments(self):
        """Test analyzing attributes with simple assignments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            attributes_dir = cookbook_path / "attributes"
            attributes_dir.mkdir(parents=True)

            attr_file = attributes_dir / "default.rb"
            attr_file.write_text("""
max_connections = 100
timeout = 30
port = 8080
""")

            complexity = _analyze_attributes(cookbook_path)

            assert complexity >= 3

    def test_analyze_attributes_node_attributes(self):
        """Test analyzing attributes with node attribute notation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            attributes_dir = cookbook_path / "attributes"
            attributes_dir.mkdir(parents=True)

            attr_file = attributes_dir / "default.rb"
            attr_file.write_text("""
default['nginx']['version'] = '1.20'
override['nginx']['port'] = 80
node['app']['path'] = '/var/www'
""")

            complexity = _analyze_attributes(cookbook_path)

            assert complexity >= 3

    def test_analyze_attributes_multiple_files(self):
        """Test analyzing multiple attribute files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            attributes_dir = cookbook_path / "attributes"
            attributes_dir.mkdir(parents=True)

            (attributes_dir / "default.rb").write_text("port = 80")
            (attributes_dir / "web.rb").write_text("max_clients = 100")
            (attributes_dir / "db.rb").write_text("pool_size = 10")

            complexity = _analyze_attributes(cookbook_path)

            assert complexity >= 3

    def test_analyze_attributes_array_notation(self):
        """Test analyzing attributes with array notation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            attributes_dir = cookbook_path / "attributes"
            attributes_dir.mkdir(parents=True)

            attr_file = attributes_dir / "default.rb"
            attr_file.write_text("""
default['app']['servers'] = []
override['app']['config'] = {}
""")

            complexity = _analyze_attributes(cookbook_path)

            assert complexity >= 2


class TestAnalyzeTemplates:
    """Test _analyze_templates function."""

    def test_analyze_templates_empty_cookbook(self):
        """Test analyzing cookbook with no templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            cookbook_path.mkdir()

            erb_count = _analyze_templates(cookbook_path)

            assert erb_count == 0

    def test_analyze_templates_with_erb(self):
        """Test analyzing templates with ERB expressions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            templates_dir = cookbook_path / "templates" / "default"
            templates_dir.mkdir(parents=True)

            template_file = templates_dir / "config.conf.erb"
            template_file.write_text("""
port = <%= @port %>
host = <%= @host %>
name = <%= @name %>
""")

            erb_count = _analyze_templates(cookbook_path)

            assert erb_count >= 3

    def test_analyze_templates_with_control_structures(self):
        """Test analyzing templates with ERB control structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            templates_dir = cookbook_path / "templates" / "default"
            templates_dir.mkdir(parents=True)

            template_file = templates_dir / "config.conf.erb"
            template_file.write_text("""
<% if @enabled %>
server {
  port <%= @port %>;
}
<% end %>
""")

            erb_count = _analyze_templates(cookbook_path)

            assert erb_count >= 3  # if, port variable, end

    def test_analyze_templates_multiple_files(self):
        """Test analyzing multiple template files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            templates_dir = cookbook_path / "templates" / "default"
            templates_dir.mkdir(parents=True)

            (templates_dir / "app.conf.erb").write_text("port = <%= @port %>")
            (templates_dir / "db.conf.erb").write_text("host = <%= @host %>")
            (templates_dir / "cache.conf.erb").write_text("ttl = <%= @ttl %>")

            erb_count = _analyze_templates(cookbook_path)

            assert erb_count >= 3

    def test_analyze_templates_nested_directories(self):
        """Test analyzing templates in nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            templates_dir = cookbook_path / "templates" / "default" / "subdir"
            templates_dir.mkdir(parents=True)

            template_file = templates_dir / "nested.erb"
            template_file.write_text("<%= @value %>")

            erb_count = _analyze_templates(cookbook_path)

            assert erb_count >= 1


class TestAnalyzeLibraries:
    """Test _analyze_libraries function."""

    def test_analyze_libraries_empty_cookbook(self):
        """Test analyzing cookbook with no libraries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            cookbook_path.mkdir()

            complexity = _analyze_libraries(cookbook_path)

            assert complexity == 0

    def test_analyze_libraries_with_classes(self):
        """Test analyzing libraries with Ruby classes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            libraries_dir = cookbook_path / "libraries"
            libraries_dir.mkdir(parents=True)

            lib_file = libraries_dir / "helpers.rb"
            lib_file.write_text("""
class MyHelper
  def initialize
  end

  def process
  end
end

class AnotherHelper
  def run
  end
end
""")

            complexity = _analyze_libraries(cookbook_path)

            # 2 classes * 2 + 3 methods = 7
            assert complexity >= 7

    def test_analyze_libraries_with_methods_only(self):
        """Test analyzing libraries with methods only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            libraries_dir = cookbook_path / "libraries"
            libraries_dir.mkdir(parents=True)

            lib_file = libraries_dir / "utils.rb"
            lib_file.write_text("""
def helper_method
end

def another_helper
end
""")

            complexity = _analyze_libraries(cookbook_path)

            assert complexity >= 2

    def test_analyze_libraries_multiple_files(self):
        """Test analyzing multiple library files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            libraries_dir = cookbook_path / "libraries"
            libraries_dir.mkdir(parents=True)

            (libraries_dir / "utils.rb").write_text("def util\nend")
            (libraries_dir / "helpers.rb").write_text("def helper\nend")
            (libraries_dir / "formatters.rb").write_text("def format\nend")

            complexity = _analyze_libraries(cookbook_path)

            assert complexity >= 3


class TestCountDefinitions:
    """Test _count_definitions function."""

    def test_count_definitions_empty_cookbook(self):
        """Test counting definitions in empty cookbook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            cookbook_path.mkdir()

            count = _count_definitions(cookbook_path)

            assert count == 0

    def test_count_definitions_with_files(self):
        """Test counting definition files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            definitions_dir = cookbook_path / "definitions"
            definitions_dir.mkdir(parents=True)

            (definitions_dir / "app.rb").write_text("define :app do\nend")
            (definitions_dir / "service.rb").write_text("define :service do\nend")
            (definitions_dir / "database.rb").write_text("define :database do\nend")

            count = _count_definitions(cookbook_path)

            assert count == 3

    def test_count_definitions_ignores_non_rb_files(self):
        """Test that non-.rb files are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            definitions_dir = cookbook_path / "definitions"
            definitions_dir.mkdir(parents=True)

            (definitions_dir / "app.rb").write_text("define :app do\nend")
            (definitions_dir / "readme.txt").write_text("This is a readme")
            (definitions_dir / "config.yml").write_text("key: value")

            count = _count_definitions(cookbook_path)

            assert count == 1


class TestParseBerksfile:
    """Test _parse_berksfile function."""

    def test_parse_berksfile_no_file(self):
        """Test parsing when no Berksfile exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            cookbook_path.mkdir()

            result = _parse_berksfile(cookbook_path)

            assert result["dependencies"] == []
            assert result["external_cookbooks"] == []
            assert result["complexity"] == 0

    def test_parse_berksfile_simple_dependencies(self):
        """Test parsing Berksfile with simple dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            cookbook_path.mkdir()

            berks_file = cookbook_path / "Berksfile"
            berks_file.write_text("""
source 'https://supermarket.chef.io'

cookbook 'nginx'
cookbook 'mysql'
cookbook 'postgresql'
""")

            result = _parse_berksfile(cookbook_path)

            assert len(result["dependencies"]) >= 3
            assert "nginx" in result["dependencies"]
            assert "mysql" in result["dependencies"]

    def test_parse_berksfile_with_versions(self):
        """Test parsing Berksfile with version constraints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            cookbook_path.mkdir()

            berks_file = cookbook_path / "Berksfile"
            berks_file.write_text("""
source 'https://supermarket.chef.io'

cookbook 'nginx', '~> 1.0'
cookbook 'mysql', '>= 2.0.0'
""")

            result = _parse_berksfile(cookbook_path)

            assert result["complexity"] >= 2  # Complex dependencies

    def test_parse_berksfile_with_git_sources(self):
        """Test parsing Berksfile with git sources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            cookbook_path.mkdir()

            berks_file = cookbook_path / "Berksfile"
            berks_file.write_text("""
cookbook 'myapp', git: 'https://github.com/user/cookbook.git'
cookbook 'otherapp', git: 'git@github.com:user/other.git'
""")

            result = _parse_berksfile(cookbook_path)

            assert result.get("has_git_sources", False) is True
            assert result["complexity"] >= 4  # Git sources add complexity

    def test_parse_berksfile_with_path_sources(self):
        """Test parsing Berksfile with local path sources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            cookbook_path.mkdir()

            berks_file = cookbook_path / "Berksfile"
            berks_file.write_text("""
cookbook 'local_app', path: '../cookbooks/myapp'
cookbook 'shared', path: '/opt/cookbooks/shared'
""")

            result = _parse_berksfile(cookbook_path)

            assert result.get("has_path_sources", False) is True
            assert result["complexity"] >= 4  # Path sources add complexity

    def test_parse_berksfile_mixed_sources(self):
        """Test parsing Berksfile with mixed source types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            cookbook_path.mkdir()

            berks_file = cookbook_path / "Berksfile"
            berks_file.write_text("""
source 'https://supermarket.chef.io'

cookbook 'nginx'
cookbook 'myapp', git: 'https://github.com/user/app.git'
cookbook 'local', path: '../local'
cookbook 'mysql', '~> 2.0'
""")

            result = _parse_berksfile(cookbook_path)

            assert len(result["dependencies"]) >= 4
            assert result.get("has_git_sources", False) is True
            assert result.get("has_path_sources", False) is True
            assert result["complexity"] > 0


class TestHelperEdgeCases:
    """Test edge cases for helper functions."""

    def test_analyze_recipes_with_invalid_syntax(self):
        """Test that invalid Ruby syntax doesn't crash analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            recipes_dir = cookbook_path / "recipes"
            recipes_dir.mkdir(parents=True)

            recipe_file = recipes_dir / "broken.rb"
            recipe_file.write_text("package 'test' do\n  # Missing end")

            resource_count, ruby_blocks, custom_resources = _analyze_recipes(
                cookbook_path
            )

            # Should still return values (may be zero or partial)
            assert isinstance(resource_count, int)
            assert isinstance(ruby_blocks, int)
            assert isinstance(custom_resources, int)

    def test_analyze_attributes_with_binary_file(self):
        """Test that binary files don't crash attribute analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            attributes_dir = cookbook_path / "attributes"
            attributes_dir.mkdir(parents=True)

            # Create a binary file
            attr_file = attributes_dir / "binary.rb"
            attr_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe")

            complexity = _analyze_attributes(cookbook_path)

            # Should return without crashing
            assert isinstance(complexity, int)

    def test_analyze_templates_with_non_erb_files(self):
        """Test that non-ERB files are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            templates_dir = cookbook_path / "templates" / "default"
            templates_dir.mkdir(parents=True)

            (templates_dir / "config.erb").write_text("<%= @value %>")
            (templates_dir / "readme.txt").write_text("No ERB here")
            (templates_dir / "data.json").write_text("{}")

            erb_count = _analyze_templates(cookbook_path)

            # Should only count .erb files
            assert erb_count >= 1

    def test_parse_berksfile_with_comments(self):
        """Test parsing Berksfile with comments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cookbook_path = Path(tmpdir) / "cookbook"
            cookbook_path.mkdir()

            berks_file = cookbook_path / "Berksfile"
            berks_file.write_text("""
# This is a comment
source 'https://supermarket.chef.io'

# Production dependencies
cookbook 'nginx'
# cookbook 'disabled'  # This is commented out
cookbook 'mysql'
""")

            result = _parse_berksfile(cookbook_path)

            # Should parse properly despite comments
            assert "nginx" in result["dependencies"]
            assert "mysql" in result["dependencies"]
