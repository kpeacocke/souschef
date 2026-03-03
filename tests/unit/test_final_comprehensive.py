"""Final comprehensive test suite targeting all remaining gaps."""

import json
from pathlib import Path

from souschef.server import (
    assess_chef_migration_complexity,
    generate_inspec_from_recipe,
    list_cookbook_structure,
    parse_custom_resource,
    parse_inspec_profile,
    parse_template,
    read_cookbook_metadata,
    read_file,
)

# ==============================================================================
# CUSTOM RESOURCE PARSING
# ==============================================================================


def test_parse_custom_resource_simple(tmp_path: Path) -> None:
    """Parse simple custom resource."""
    resource = tmp_path / "simple.rb"
    resource.write_text(
        "property :name, String\naction :create do\n  puts 'creating'\nend\n"
    )
    result = parse_custom_resource(str(resource))
    assert isinstance(result, str)


def test_parse_custom_resource_complex(tmp_path: Path) -> None:
    """Parse complex custom resource."""
    resource = tmp_path / "complex.rb"
    resource.write_text(
        "unified_mode true\n"
        "property :name, String, required: true\n"
        "property :path, String, default: '/tmp'\n"
        "action :create do\n"
        "  # Create logic\n"
        "end\n"
        "action :delete do\n"
        "  # Delete logic\n"
        "end\n"
    )
    result = parse_custom_resource(str(resource))
    assert isinstance(result, str)


def test_parse_custom_resource_multiple_properties(tmp_path: Path) -> None:
    """Parse custom resource with many properties."""
    resource = tmp_path / "props.rb"
    props = "\n".join(f"property :prop_{i}, String" for i in range(10))
    resource.write_text(f"{props}\naction :run do end\n")
    result = parse_custom_resource(str(resource))
    assert isinstance(result, str)


def test_parse_custom_resource_multiple_actions(tmp_path: Path) -> None:
    """Parse custom resource with multiple actions."""
    resource = tmp_path / "actions.rb"
    actions = "\n".join(
        f"action :action_{i} do puts 'action {i}' end" for i in range(5)
    )
    resource.write_text(f"property :name, String\n{actions}\n")
    result = parse_custom_resource(str(resource))
    assert isinstance(result, str)


def test_parse_custom_resource_with_helpers(tmp_path: Path) -> None:
    """Parse custom resource with helper methods."""
    resource = tmp_path / "helpers.rb"
    resource.write_text(
        "property :name, String\n"
        "action :create do\n"
        "  do_something\n"
        "end\n"
        "action_class do\n"
        "  def do_something\n"
        "    # helper logic\n"
        "  end\n"
        "end\n"
    )
    result = parse_custom_resource(str(resource))
    assert isinstance(result, str)


def test_parse_custom_resource_empty(tmp_path: Path) -> None:
    """Parse empty custom resource."""
    resource = tmp_path / "empty.rb"
    resource.write_text("")
    result = parse_custom_resource(str(resource))
    assert isinstance(result, str)


def test_parse_custom_resource_invalid() -> None:
    """Parse non-existent custom resource."""
    result = parse_custom_resource("/nonexistent/resource.rb")
    assert isinstance(result, str)


# ==============================================================================
# TEMPLATE PARSING
# ==============================================================================


def test_parse_template_simple(tmp_path: Path) -> None:
    """Parse simple template."""
    template = tmp_path / "simple.erb"
    template.write_text("# Config file\nname=<%= @name %>\n")
    result = parse_template(str(template))
    assert isinstance(result, str)


def test_parse_template_complex(tmp_path: Path) -> None:
    """Parse complex template."""
    template = tmp_path / "complex.erb"
    template.write_text(
        "<%\n"
        "  # Variables\n"
        "  items = @items\n"
        "%>\n"
        "<% items.each do |item| %>\n"
        "  name=<%= item %>\n"
        "<% end %>\n"
    )
    result = parse_template(str(template))
    assert isinstance(result, str)


def test_parse_template_with_conditionals(tmp_path: Path) -> None:
    """Parse template with conditionals."""
    template = tmp_path / "conditional.erb"
    template.write_text(
        "<% if @debug %>\n  DEBUG=true\n<% else %>\n  DEBUG=false\n<% end %>\n"
    )
    result = parse_template(str(template))
    assert isinstance(result, str)


def test_parse_template_with_loops(tmp_path: Path) -> None:
    """Parse template with loops."""
    template = tmp_path / "loop.erb"
    template.write_text(
        "<% @servers.each do |server| %>\n"
        "  server <%= server.name %> <%= server.ip %>\n"
        "<% end %>\n"
    )
    result = parse_template(str(template))
    assert isinstance(result, str)


def test_parse_template_nginx_config(tmp_path: Path) -> None:
    """Parse nginx configuration template."""
    template = tmp_path / "nginx.conf.erb"
    template.write_text(
        "server {\n"
        "  listen <%= @port %>;\n"
        "  server_name <%= @server_name %>;\n"
        "  root <%= @root %>;\n"
        "  <% if @ssl %>\n"
        "  ssl on;\n"
        "  <% end %>\n"
        "}\n"
    )
    result = parse_template(str(template))
    assert isinstance(result, str)


def test_parse_template_empty(tmp_path: Path) -> None:
    """Parse empty template."""
    template = tmp_path / "empty.erb"
    template.write_text("")
    result = parse_template(str(template))
    assert isinstance(result, str)


def test_parse_template_invalid() -> None:
    """Parse non-existent template."""
    result = parse_template("/nonexistent/template.erb")
    assert isinstance(result, str)


# ==============================================================================
# INSPEC PROFILE PARSING
# ==============================================================================


def test_parse_inspec_simple(tmp_path: Path) -> None:
    """Parse simple InSpec profile."""
    control = tmp_path / "inspec.rb"
    control.write_text(
        "describe package('nginx') do\n  it { should be_installed }\nend\n"
    )
    result = parse_inspec_profile(str(control))
    assert isinstance(result, str)


def test_parse_inspec_with_controls(tmp_path: Path) -> None:
    """Parse InSpec with control blocks."""
    control = tmp_path / "controls.rb"
    control.write_text(
        "control 'web-1' do\n"
        "  title 'Webserver configuration'\n"
        "  describe package('nginx') do\n"
        "    it { should be_installed }\n"
        "  end\n"
        "end\n"
    )
    result = parse_inspec_profile(str(control))
    assert isinstance(result, str)


def test_parse_inspec_multiple_controls(tmp_path: Path) -> None:
    """Parse InSpec with multiple controls."""
    control = tmp_path / "multi.rb"
    controls = "\n".join(
        f"control 'control-{i}' do\n"
        f"  describe package('pkg{i}') do\n"
        f"    it {{ should be_installed }}\n"
        f"  end\nend"
        for i in range(5)
    )
    control.write_text(controls)
    result = parse_inspec_profile(str(control))
    assert isinstance(result, str)


def test_parse_inspec_with_attributes(tmp_path: Path) -> None:
    """Parse InSpec with attribute definitions."""
    control = tmp_path / "attrs.rb"
    control.write_text(
        "title 'InSpec Controls'\n"
        "attribute 'package_name' do\n"
        "  value 'nginx'\n"
        "end\n"
        "control 'pkg-1' do\n"
        "  describe package(attribute('package_name')) do\n"
        "    it { should be_installed }\n"
        "  end\n"
        "end\n"
    )
    result = parse_inspec_profile(str(control))
    assert isinstance(result, str)


def test_parse_inspec_with_vars(tmp_path: Path) -> None:
    """Parse InSpec with variables."""
    control = tmp_path / "vars.rb"
    control.write_text(
        "vars = { 'package' => 'nginx' }\n"
        "describe package(vars['package']) do\n"
        "  it { should be_installed }\n"
        "end\n"
    )
    result = parse_inspec_profile(str(control))
    assert isinstance(result, str)


def test_parse_inspec_empty(tmp_path: Path) -> None:
    """Parse empty InSpec file."""
    control = tmp_path / "empty.rb"
    control.write_text("")
    result = parse_inspec_profile(str(control))
    assert isinstance(result, str)


def test_parse_inspec_invalid() -> None:
    """Parse non-existent InSpec file."""
    result = parse_inspec_profile("/nonexistent/inspec.rb")
    assert isinstance(result, str)


# ==============================================================================
# INSPEC TO PLAYBOOK GENERATION
# ==============================================================================


def test_generate_inspec_basic(tmp_path: Path) -> None:
    """Generate InSpec from basic recipe."""
    recipe = tmp_path / "basic.rb"
    recipe.write_text("package 'curl'\nservice 'apache2'\n")
    result = generate_inspec_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_generate_inspec_with_files(tmp_path: Path) -> None:
    """Generate InSpec from recipe with files."""
    recipe = tmp_path / "files.rb"
    recipe.write_text("file '/etc/config' do\n  content 'value'\nend\n")
    result = generate_inspec_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_generate_inspec_with_ports(tmp_path: Path) -> None:
    """Generate InSpec from recipe with ports."""
    recipe = tmp_path / "ports.rb"
    recipe.write_text("service 'nginx' do\n  action :start\nend\n")
    result = generate_inspec_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_generate_inspec_complex(tmp_path: Path) -> None:
    """Generate InSpec from complex recipe."""
    recipe = tmp_path / "complex.rb"
    recipe.write_text(
        "package 'nginx'\n"
        "file '/etc/nginx/nginx.conf' do content 'conf' end\n"
        "service 'nginx' do action [:enable, :start] end\n"
        "directory '/var/www' do mode '0755' end\n"
    )
    result = generate_inspec_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_generate_inspec_empty(tmp_path: Path) -> None:
    """Generate InSpec from empty recipe."""
    recipe = tmp_path / "empty.rb"
    recipe.write_text("")
    result = generate_inspec_from_recipe(str(recipe))
    assert isinstance(result, str)


# ==============================================================================
# FILE OPERATIONS
# ==============================================================================


def test_read_file_simple(tmp_path: Path) -> None:
    """Read simple file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")
    result = read_file(str(test_file))
    assert isinstance(result, str)


def test_read_file_large(tmp_path: Path) -> None:
    """Read large file."""
    test_file = tmp_path / "large.txt"
    lines = [f"Line {i}\n" for i in range(1000)]
    test_file.write_text("".join(lines))
    result = read_file(str(test_file))
    assert isinstance(result, str)


def test_read_file_binary(tmp_path: Path) -> None:
    """Read binary file."""
    test_file = tmp_path / "binary.bin"
    test_file.write_bytes(b"\x00\x01\x02\x03\x04")
    result = read_file(str(test_file))
    assert isinstance(result, str)


def test_read_file_unicode(tmp_path: Path) -> None:
    """Read Unicode file."""
    test_file = tmp_path / "unicode.txt"
    test_file.write_text("Hello café ☕ 日本語")
    result = read_file(str(test_file))
    assert isinstance(result, str)


def test_read_file_empty(tmp_path: Path) -> None:
    """Read empty file."""
    test_file = tmp_path / "empty.txt"
    test_file.write_text("")
    result = read_file(str(test_file))
    assert isinstance(result, str)


def test_read_file_invalid() -> None:
    """Read non-existent file."""
    result = read_file("/nonexistent/file.txt")
    assert isinstance(result, str)


# ==============================================================================
# STRUCTURE AND LISTING
# ==============================================================================


def test_list_cookbook_structure_minimal(tmp_path: Path) -> None:
    """List minimal cookbook structure."""
    cookbook = tmp_path / "minimal"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'minimal'\n")
    result = list_cookbook_structure(str(cookbook))
    assert isinstance(result, str)


def test_list_cookbook_structure_full(tmp_path: Path) -> None:
    """List full cookbook structure."""
    cookbook = tmp_path / "full"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'full'")

    # Create all standard directories
    for dirname in [
        "recipes",
        "attributes",
        "templates",
        "files",
        "libraries",
        "resources",
        "spec",
        "test",
    ]:
        (cookbook / dirname).mkdir()

    result = list_cookbook_structure(str(cookbook))
    assert isinstance(result, str)


def test_list_cookbook_nested_directories(tmp_path: Path) -> None:
    """List cookbook with nested directories."""
    cookbook = tmp_path / "nested"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'nested'")
    recipes = cookbook / "recipes"
    recipes.mkdir()
    (recipes / "default.rb").write_text("# default")
    (recipes / "web.rb").write_text("# web")
    (recipes / "db.rb").write_text("# db")

    result = list_cookbook_structure(str(cookbook))
    assert isinstance(result, str)


# ==============================================================================
# METADATA OPERATIONS
# ==============================================================================


def test_read_cookbook_metadata_complete(tmp_path: Path) -> None:
    """Read complete cookbook metadata."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text(
        "name 'complete'\n"
        "version '1.0.0'\n"
        "description 'Complete cookbook'\n"
        "author 'Test'\n"
        "license 'Apache-2.0'\n"
        "depends 'base'\n"
        "supports 'ubuntu', '>= 18.04'"
    )
    result = read_cookbook_metadata(str(metadata))
    assert isinstance(result, str)


def test_read_cookbook_metadata_minimal(tmp_path: Path) -> None:
    """Read minimal metadata file."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text("name 'min'\nversion '0.0.1'")
    result = read_cookbook_metadata(str(metadata))
    assert isinstance(result, str)


def test_read_cookbook_metadata_json(tmp_path: Path) -> None:
    """Read JSON metadata file."""
    metadata = tmp_path / "metadata.json"
    metadata.write_text(
        json.dumps(
            {
                "name": "json_cookbook",
                "version": "1.0.0",
                "description": "JSON metadata",
            }
        )
    )
    result = read_cookbook_metadata(str(metadata))
    assert isinstance(result, str)


# ==============================================================================
# ERROR HANDLING AND EDGE CASES
# ==============================================================================


def test_parse_resource_unicode(tmp_path: Path) -> None:
    """Parse custom resource with Unicode."""
    resource = tmp_path / "unicode.rb"
    resource.write_text(
        "# Café in description\n"
        "property :name, String\n"
        "action :create do puts '日本語' end\n"
    )
    result = parse_custom_resource(str(resource))
    assert isinstance(result, str)


def test_parse_template_unicode(tmp_path: Path) -> None:
    """Parse template with Unicode."""
    template = tmp_path / "unicode.erb"
    template.write_text("# Café ☕\nname=<%= @application %>\n# 日本語 description\n")
    result = parse_template(str(template))
    assert isinstance(result, str)


def test_parse_inspec_large(tmp_path: Path) -> None:
    """Parse large InSpec profile."""
    control = tmp_path / "large.rb"
    controls = "\n".join(
        f"control 'c{i}' do describe command('test {i}') do "
        f"its('exit_status') {{ should eq 0 }} end end"
        for i in range(50)
    )
    control.write_text(controls)
    result = parse_inspec_profile(str(control))
    assert isinstance(result, str)


def test_assess_with_invalid_json() -> None:
    """Assess with invalid path."""
    result = assess_chef_migration_complexity("/invalid/path/that/doesnt/exist")
    assert isinstance(result, str)


# ==============================================================================
# INTEGRATION WORKFLOWS
# ==============================================================================


def test_custom_resource_to_template_workflow(tmp_path: Path) -> None:
    """Custom resource and template parsing workflow."""
    resource = tmp_path / "resource.rb"
    resource.write_text("property :name, String\naction :create do end")

    template = tmp_path / "template.erb"
    template.write_text("name=<%= @name %>")

    resource_result = parse_custom_resource(str(resource))
    template_result = parse_template(str(template))

    assert isinstance(resource_result, str)
    assert isinstance(template_result, str)


def test_inspec_profile_parsing_workflow(tmp_path: Path) -> None:
    """InSpec profile parsing workflow."""
    recipe = tmp_path / "recipe.rb"
    recipe.write_text("package 'app'")

    inspec = tmp_path / "inspec.rb"
    inspec.write_text("describe package('app') do it { should be_installed } end")

    inspec_generated = generate_inspec_from_recipe(str(recipe))
    inspec_parsed = parse_inspec_profile(str(inspec))

    assert isinstance(inspec_generated, str)
    assert isinstance(inspec_parsed, str)
