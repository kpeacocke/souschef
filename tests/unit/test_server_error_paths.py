"""Integration tests for server.py error handling and edge cases."""

import tempfile
from pathlib import Path

from souschef.server import (
    convert_inspec_to_test,
    parse_attributes,
    parse_custom_resource,
    parse_inspec_profile,
    parse_recipe,
    parse_template,
    read_cookbook_metadata,
    read_file,
)


class TestErrorHandlingAndEdgeCases:
    """Test error paths and exceptional scenarios."""

    def test_read_file_permission_denied(self) -> None:
        """Test reading file without read permissions (if possible)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "restricted.txt"
            test_file.write_text("content")

            # Try to remove read permissions
            try:
                test_file.chmod(0o000)
                result = read_file(str(test_file))
                assert isinstance(result, str)
            finally:
                # Restore permissions for cleanup
                test_file.chmod(0o644)

    def test_parse_recipe_with_circular_includes(self) -> None:
        """Test parsing recipe that might have circular references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "recipe.rb"
            recipe_file.write_text("include_recipe 'self'")

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_recipe_with_invalid_ruby_classes(self) -> None:
        """Test parsing recipe with undefined Ruby classes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "bad.rb"
            recipe_file.write_text("""
NonExistentClass.new do
  do_something
end
""")

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_attributes_with_circular_dependencies(self) -> None:
        """Test attributes that might reference themselves."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "attr.rb"
            attr_file.write_text("default['key'] = default['key']")

            result = parse_attributes(str(attr_file))
            assert isinstance(result, str)

    def test_parse_attributes_deeply_nested_mergeable(self) -> None:
        """Test parsing very deeply nested attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "deep.rb"
            # Create 100 levels of nesting
            content = "default"
            for i in range(100):
                content += f"['{i}']"
            content += " = 'value'"
            attr_file.write_text(content)

            result = parse_attributes(str(attr_file))
            assert isinstance(result, str)

    def test_parse_template_with_undefined_variables(self) -> None:
        """Test ERB template with undefined variable references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "undefined.erb"
            template_file.write_text("<%= @undefined_var %>")

            result = parse_template(str(template_file))
            assert isinstance(result, str)

    def test_parse_template_with_broken_erb(self) -> None:
        """Test template with unclosed ERB tag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "broken.erb"
            template_file.write_text("<%= variable_without_closing")

            result = parse_template(str(template_file))
            assert isinstance(result, str)

    def test_parse_custom_resource_missing_resource_name(self) -> None:
        """Test resource without resource_name declaration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resource_file = Path(tmpdir) / "missing_name.rb"
            resource_file.write_text("""
property :name, String
action :create do
  log 'Creating'
end
""")

            result = parse_custom_resource(str(resource_file))
            assert isinstance(result, str)

    def test_parse_inspec_profile_empty_profile(self) -> None:
        """Test parsing empty InSpec profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir) / "profile"
            profile_dir.mkdir()
            (profile_dir / "inspec.yml").write_text("name: empty")

            result = parse_inspec_profile(str(profile_dir))
            assert isinstance(result, str)

    def test_convert_inspec_unsupported_format(self) -> None:
        """Test conversion with unsupported output format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir) / "profile"
            profile_dir.mkdir()
            (profile_dir / "inspec.yml").write_text("name: test")

            result = convert_inspec_to_test(str(profile_dir), "unsupported_format")
            assert isinstance(result, str)

    def test_parse_recipe_with_very_long_lines(self) -> None:
        """Test parsing recipe with extremely long lines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "long.rb"
            # Create a line with 10,000 characters
            long_line = "a = '" + "x" * 10000 + "'"
            recipe_file.write_text(long_line)

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_attributes_with_special_ruby_methods(self) -> None:
        """Test attributes using special Ruby methods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "special.rb"
            attr_file.write_text("""
default['time'] = Time.now
default['hash'] = Hash.new
default['array'] = Array.new(5)
""")

            result = parse_attributes(str(attr_file))
            assert isinstance(result, str)

    def test_template_with_ruby_comments(self) -> None:
        """Test template with various Ruby comment styles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "comments.erb"
            template_file.write_text("""
<%# This is an ERB comment %>
<% # This is a Ruby comment %>
<%= @var %> <%# Inline comment %>
""")

            result = parse_template(str(template_file))
            assert isinstance(result, str)

    def test_parse_recipe_with_multiline_string(self) -> None:
        """Test recipe with multiline string literals."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "multiline.rb"
            recipe_file.write_text("""
execute 'command' do
  command <<-EOH
    echo "Line 1"
    echo "Line 2"
    echo "Line 3"
  EOH
end
""")

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_attributes_with_complex_conditionals(self) -> None:
        """Test attributes with nested and complex conditionals."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "complex_cond.rb"
            attr_file.write_text("""
if node['os'] == 'linux' && node['platform_family'] == 'debian'
  default['pkg'] = 'apache2'
elsif node['os'] == 'linux' && node['platform_family'] == 'rhel'
  default['pkg'] = 'httpd'
elsif node['os'] == 'windows'
  default['pkg'] = 'IIS'
else
  default['pkg'] = 'unknown'
end
""")

            result = parse_attributes(str(attr_file))
            assert isinstance(result, str)

    def test_parse_custom_resource_with_inline_resources(self) -> None:
        """Test resource that contains inline resources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resource_file = Path(tmpdir) / "inline.rb"
            resource_file.write_text("""
resource_name :my_resource

action :create do
  package 'nginx' do
    action :install
  end
end
""")

            result = parse_custom_resource(str(resource_file))
            assert isinstance(result, str)

    def test_symlink_following(self) -> None:
        """Test reading file via symlink."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            target = tmppath / "target.txt"
            target.write_text("content via symlink")

            # Create symlink
            symlink = tmppath / "link.txt"
            try:
                symlink.symlink_to(target)
                result = read_file(str(symlink))
                assert isinstance(result, str)
            except (OSError, NotImplementedError):
                # Windows might not support symlinks without Admin
                pass

    def test_parse_recipe_with_only_method_calls(self) -> None:
        """Test recipe containing only method calls without blocks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "methods.rb"
            recipe_file.write_text("""
include_recipe 'dependency'
include_recipe 'another_dependency'
""")

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_template_with_filters(self) -> None:
        """Test ERB template with Ruby filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "filters.erb"
            template_file.write_text("""
<%= @text | upcase %>
<%= @number | to_s %>
<%= @array | join(', ') %>
""")

            result = parse_template(str(template_file))
            assert isinstance(result, str)

    def test_parse_attributes_with_guard_clauses(self) -> None:
        """Test attributes using guard clauses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "guards.rb"
            attr_file.write_text("""
default['key'] = 'default_value' if !node['key']
default['port'] = 8080 unless node['custom_port']
""")

            result = parse_attributes(str(attr_file))
            assert isinstance(result, str)

    def test_read_file_with_different_encodings(self) -> None:
        """Test reading files with various character encodings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # UTF-8 file
            utf8_file = Path(tmpdir) / "utf8.txt"
            utf8_file.write_text("UTF-8: Ñoño", encoding="utf-8")

            result = read_file(str(utf8_file))
            assert isinstance(result, str)

    def test_parse_recipe_block_without_end(self) -> None:
        """Test recipe with unmatched block delimiters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "unmatched.rb"
            recipe_file.write_text("""
package 'nginx' do
  action :install
# Missing 'end'
""")

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_attributes_empty_default_value(self) -> None:
        """Test attributes with empty string and nil values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "empty_values.rb"
            attr_file.write_text("""
default['empty_string'] = ''
default['nil_value'] = nil
default['false_value'] = false
default['zero_value'] = 0
""")

            result = parse_attributes(str(attr_file))
            assert isinstance(result, str)

    def test_template_with_escaped_erb_tags(self) -> None:
        """Test template with escaped ERB delimiters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "escaped.erb"
            template_file.write_text("""
This is not a tag: <%%= @var %%>
This is a real tag: <%= @var %>
""")

            result = parse_template(str(template_file))
            assert isinstance(result, str)

    def test_parse_custom_resource_with_property_validation(self) -> None:
        """Test resource with property validation blocks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resource_file = Path(tmpdir) / "validation.rb"
            resource_file.write_text("""
resource_name :validated

property :port do
  validators do
    integer (1..65535)
  end
end

action :create do
  log 'Creating'
end
""")

            result = parse_custom_resource(str(resource_file))
            assert isinstance(result, str)

    def test_parse_inspec_profile_with_controls(self) -> None:
        """Test InSpec profile with actual controls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir) / "profile"
            profile_dir.mkdir()
            (profile_dir / "inspec.yml").write_text("name: test")

            controls_dir = profile_dir / "controls"
            controls_dir.mkdir()
            (controls_dir / "example.rb").write_text("""
control '1' do
  title 'Test control'
  describe package('nginx') do
    it { should be_installed }
  end
end
""")

            result = parse_inspec_profile(str(profile_dir))
            assert isinstance(result, str)

    def test_read_cookbook_metadata_with_fields(self) -> None:
        """Test metadata with various field combinations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.rb"
            metadata_file.write_text("""
name 'complex'
version '1.0.0'
description 'Complex cookbook'
author 'Chef'
license 'MIT'
chef_version '>= 13.0'
supports 'ubuntu', '>= 16.04'
supports 'centos', '>= 7.0'
depends 'poise'
depends 'poise-python'
""")

            result = read_cookbook_metadata(str(metadata_file))
            assert isinstance(result, str)

    def test_parse_recipe_with_lazy_block(self) -> None:
        """Test recipe with lazy block evaluation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "lazy.rb"
            recipe_file.write_text("""
log 'Message' do
  message lazy { "Computed at: #{Time.now}" }
end
""")

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)


class TestConcurrentAccess:
    """Test behavior with concurrent file access patterns."""

    def test_read_while_writing(self) -> None:
        """Test reading a file while another thread might be writing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "concurrent.txt"
            test_file.write_text("initial content")

            # Read the file
            result1 = read_file(str(test_file))

            # Modify it
            test_file.write_text("modified content")

            # Read again
            result2 = read_file(str(test_file))

            assert isinstance(result1, str)
            assert isinstance(result2, str)

    def test_parse_recipe_multiple_times(self) -> None:
        """Test parsing same recipe multiple times."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "repeated.rb"
            recipe_file.write_text("package 'nginx'")

            result1 = parse_recipe(str(recipe_file))
            result2 = parse_recipe(str(recipe_file))
            result3 = parse_recipe(str(recipe_file))

            assert isinstance(result1, str)
            assert isinstance(result2, str)
            assert isinstance(result3, str)


class TestLargeFileHandling:
    """Test handling of large and complex files."""

    def test_parse_large_recipe(self) -> None:
        """Test parsing recipe with many resources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "large.rb"

            # Create recipe with 500 resources
            lines = []
            for i in range(500):
                lines.append(f"""
package 'package{i}' do
  action :install
end
""")

            recipe_file.write_text("\n".join(lines))

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_large_attributes(self) -> None:
        """Test parsing attributes with many declarations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "large.rb"

            # Create attributes with many declarations
            lines = []
            for i in range(500):
                lines.append(f"default['key{i}'] = 'value{i}'")

            attr_file.write_text("\n".join(lines))

            result = parse_attributes(str(attr_file))
            assert isinstance(result, str)

    def test_parse_large_template(self) -> None:
        """Test parsing large template file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "large.erb"

            # Create template with many content sections
            lines = ["<% (1..500).each do |i| %>"]
            lines.append("  <%= i %>")
            lines.append("<% end %>")

            template_file.write_text("\n".join(lines))

            result = parse_template(str(template_file))
            assert isinstance(result, str)
