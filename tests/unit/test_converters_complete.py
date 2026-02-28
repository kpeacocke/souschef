"""Comprehensive coverage for converter and server modules."""

from pathlib import Path

from souschef.converters.playbook import generate_playbook_from_recipe
from souschef.server import (
    convert_chef_environment_to_inventory_group,
    convert_inspec_to_test,
    list_cookbook_structure,
    parse_attributes,
    parse_recipe,
    read_cookbook_metadata,
)

# ==============================================================================
# COOKBOOK RECIPE CONVERSION
# ==============================================================================


def test_convert_recipe_to_playbook_simple(tmp_path: Path) -> None:
    """Convert simple recipe to playbook."""
    recipe = tmp_path / "default.rb"
    recipe.write_text("package 'nginx'\n")
    result = generate_playbook_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_convert_recipe_to_playbook_with_cookbook(tmp_path: Path) -> None:
    """Convert recipe with cookbook path."""
    recipe = tmp_path / "default.rb"
    recipe.write_text("package 'nginx'\n")
    result = generate_playbook_from_recipe(str(recipe), cookbook_path=str(tmp_path))
    assert isinstance(result, str)


def test_convert_recipe_to_playbook_multiple_resources(tmp_path: Path) -> None:
    """Convert recipe with multiple resources."""
    recipe = tmp_path / "default.rb"
    recipe.write_text(
        "package 'nginx'\n"
        "service 'nginx' do\n"
        "  action [:enable, :start]\n"
        "end\n"
        "file '/etc/nginx/nginx.conf' do\n"
        "  content 'config'\n"
        "end\n"
    )
    result = generate_playbook_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_convert_recipe_to_playbook_with_conditionals(tmp_path: Path) -> None:
    """Convert recipe with conditionals."""
    recipe = tmp_path / "default.rb"
    recipe.write_text(
        "if node['platform'] == 'ubuntu'\n"
        "  package 'curl'\n"
        "else\n"
        "  package 'curl-devel'\n"
        "end\n"
    )
    result = generate_playbook_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_convert_recipe_to_playbook_with_loops(tmp_path: Path) -> None:
    """Convert recipe with loops."""
    recipe = tmp_path / "default.rb"
    recipe.write_text("node['packages'].each do |pkg|\n  package pkg\nend\n")
    result = generate_playbook_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_convert_recipe_to_playbook_with_attributes(tmp_path: Path) -> None:
    """Convert recipe accessing attributes."""
    recipe = tmp_path / "default.rb"
    recipe.write_text(
        "package node['app']['package_name']\n"
        "directory node['app']['install_path'] do\n"
        "  mode node['app']['dir_mode']\n"
        "end\n"
    )
    result = generate_playbook_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_convert_recipe_to_playbook_empty(tmp_path: Path) -> None:
    """Convert empty recipe."""
    recipe = tmp_path / "default.rb"
    recipe.write_text("")
    result = generate_playbook_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_convert_recipe_to_playbook_invalid() -> None:
    """Convert non-existent recipe."""
    result = generate_playbook_from_recipe("/nonexistent/recipe.rb")
    assert isinstance(result, str)


# ==============================================================================
# ENVIRONMENT CONVERSION VARIATIONS
# ==============================================================================


def test_convert_env_simple() -> None:
    """Convert simple environment."""
    env_content = "name 'production'\n"
    result = convert_chef_environment_to_inventory_group(env_content, "production")
    assert isinstance(result, str)


def test_convert_env_with_attributes() -> None:
    """Convert environment with default attributes."""
    env_content = "name 'production'\ndefault_attributes 'app' => {'version' => '2.0'}"
    result = convert_chef_environment_to_inventory_group(env_content, "production")
    assert isinstance(result, str)


def test_convert_env_with_overrides() -> None:
    """Convert environment with override attributes."""
    env_content = "name 'staging'\noverride_attributes 'debug' => true"
    result = convert_chef_environment_to_inventory_group(env_content, "staging")
    assert isinstance(result, str)


def test_convert_env_with_both_attributes() -> None:
    """Convert environment with both default and override attributes."""
    env_content = (
        "name 'development'\n"
        "default_attributes 'app' => {'mode' => 'development'}\n"
        "override_attributes 'debug' => true"
    )
    result = convert_chef_environment_to_inventory_group(env_content, "development")
    assert isinstance(result, str)


def test_convert_env_nested_attributes() -> None:
    """Convert environment with deeply nested attributes."""
    env_content = (
        "name 'complex'\n"
        "default_attributes "
        "'db' => {'primary' => {'host' => 'db1.prod', "
        "'port' => 5432}}, "
        "'app' => {'services' => ['web', 'api']}"
    )
    result = convert_chef_environment_to_inventory_group(env_content, "complex")
    assert isinstance(result, str)


def test_convert_env_json_attributes() -> None:
    """Convert environment with JSON-style attributes."""
    env_content = (
        "name 'json_env'\n"
        "default_attributes('key' => 'value', "
        "'nested' => {'deep' => 'data'})"
    )
    result = convert_chef_environment_to_inventory_group(env_content, "json_env")
    assert isinstance(result, str)


def test_convert_env_empty_attrs() -> None:
    """Environment with empty attribute blocks."""
    env_content = "name 'empty'\ndefault_attributes()\noverride_attributes()"
    result = convert_chef_environment_to_inventory_group(env_content, "empty")
    assert isinstance(result, str)


def test_convert_env_with_constraints(tmp_path: Path) -> None:
    """Convert environment with include_constraints."""
    env_content = "name 'constrained'\ndefault_attributes 'app' => {'version' => '1.0'}"
    result = convert_chef_environment_to_inventory_group(
        env_content, "constrained", include_constraints=True
    )
    assert isinstance(result, str)


def test_convert_env_without_constraints(tmp_path: Path) -> None:
    """Convert environment without constraints."""
    env_content = (
        "name 'unconstrained'\ndefault_attributes 'app' => {'version' => '2.0'}"
    )
    result = convert_chef_environment_to_inventory_group(
        env_content, "unconstrained", include_constraints=False
    )
    assert isinstance(result, str)


# ==============================================================================
# RECIPE AND STRUCTURE PARSING
# ==============================================================================


def test_parse_recipe_simple(tmp_path: Path) -> None:
    """Parse simple recipe file."""
    recipe = tmp_path / "default.rb"
    recipe.write_text("package 'nginx'\n")
    result = parse_recipe(str(recipe))
    assert isinstance(result, str)


def test_parse_recipe_multiple_resources(tmp_path: Path) -> None:
    """Parse recipe with multiple resources."""
    recipe = tmp_path / "default.rb"
    recipe.write_text(
        "package 'nginx'\nservice 'nginx' do\n  action [:enable, :start]\nend\n"
    )
    result = parse_recipe(str(recipe))
    assert isinstance(result, str)


def test_list_cookbook_structure(tmp_path: Path) -> None:
    """List cookbook structure."""
    cookbook = tmp_path / "app"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'app'\nversion '1.0'")
    (cookbook / "recipes").mkdir()
    (cookbook / "recipes" / "default.rb").write_text("package 'nginx'")

    result = list_cookbook_structure(str(cookbook))
    assert isinstance(result, str)


def test_list_cookbook_structure_complex(tmp_path: Path) -> None:
    """List complex cookbook structure."""
    cookbook = tmp_path / "complex"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'complex'\nversion '2.0'")
    (cookbook / "recipes").mkdir()
    (cookbook / "recipes" / "default.rb").write_text("# recipe")
    (cookbook / "recipes" / "setup.rb").write_text("# setup")
    (cookbook / "attributes").mkdir()
    (cookbook / "attributes" / "default.rb").write_text("# attrs")
    (cookbook / "templates").mkdir()
    (cookbook / "templates" / "config.erb").write_text("# template")
    (cookbook / "files").mkdir()
    (cookbook / "files" / "config").write_text("# file")

    result = list_cookbook_structure(str(cookbook))
    assert isinstance(result, str)


# ==============================================================================
# METADATA AND ATTRIBUTES READING
# ==============================================================================


def test_read_metadata_complete(tmp_path: Path) -> None:
    """Read complete metadata file."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text(
        "name 'complete'\n"
        "version '1.2.3'\n"
        "description 'Complete metadata'\n"
        "author 'Test Author'\n"
        "license 'Apache-2.0'\n"
        "depends 'base'\n"
        "supports 'ubuntu', '>= 20.04'"
    )
    result = read_cookbook_metadata(str(metadata))
    assert isinstance(result, str)


def test_read_metadata_minimal(tmp_path: Path) -> None:
    """Read minimal metadata file."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text("name 'minimal'\nversion '0.1.0'")
    result = read_cookbook_metadata(str(metadata))
    assert isinstance(result, str)


def test_read_metadata_multiple_deps(tmp_path: Path) -> None:
    """Read metadata with multiple dependencies."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text(
        "name 'multi_dep'\n"
        "version '1.0'\n"
        "depends 'base', '~> 1.0'\n"
        "depends 'database', '>= 2.0'\n"
        "depends 'cache', '= 1.5.0'\n"
        "depends 'app'"
    )
    result = read_cookbook_metadata(str(metadata))
    assert isinstance(result, str)


def test_read_metadata_multiple_support(tmp_path: Path) -> None:
    """Read metadata with multiple platform support."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text(
        "name 'multi_platform'\n"
        "version '1.0'\n"
        "supports 'ubuntu', '>= 18.04'\n"
        "supports 'centos', '>= 7.0'\n"
        "supports 'debian', '>= 10.0'"
    )
    result = read_cookbook_metadata(str(metadata))
    assert isinstance(result, str)


def test_read_metadata_empty(tmp_path: Path) -> None:
    """Read empty metadata file."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text("")
    result = read_cookbook_metadata(str(metadata))
    assert isinstance(result, str)


def test_read_metadata_invalid() -> None:
    """Read non-existent metadata file."""
    result = read_cookbook_metadata("/nonexistent/metadata.rb")
    assert isinstance(result, str)


def test_parse_attributes_simple(tmp_path: Path) -> None:
    """Parse simple attributes file."""
    attrs = tmp_path / "default.rb"
    attrs.write_text("default['app'] = 'test'")
    result = parse_attributes(str(attrs))
    assert isinstance(result, str)


def test_parse_attributes_multiple(tmp_path: Path) -> None:
    """Parse attributes with multiple keys."""
    attrs = tmp_path / "default.rb"
    attrs.write_text(
        "default['app']['name'] = 'myapp'\n"
        "default['app']['port'] = 8080\n"
        "default['app']['enabled'] = true"
    )
    result = parse_attributes(str(attrs))
    assert isinstance(result, str)


def test_parse_attributes_nested(tmp_path: Path) -> None:
    """Parse deeply nested attributes."""
    attrs = tmp_path / "default.rb"
    attrs.write_text(
        "default['db']['primary']['host'] = 'db1.example.com'\n"
        "default['db']['primary']['port'] = 5432\n"
        "default['db']['replica']['host'] = 'db2.example.com'"
    )
    result = parse_attributes(str(attrs))
    assert isinstance(result, str)


def test_parse_attributes_with_conditionals(tmp_path: Path) -> None:
    """Parse attributes with conditionals."""
    attrs = tmp_path / "default.rb"
    attrs.write_text(
        "if node['platform'] == 'ubuntu'\n"
        "  default['package'] = 'curl'\n"
        "else\n"
        "  default['package'] = 'curl-devel'\n"
        "end"
    )
    result = parse_attributes(str(attrs))
    assert isinstance(result, str)


def test_parse_attributes_with_variables(tmp_path: Path) -> None:
    """Parse attributes using variables."""
    attrs = tmp_path / "default.rb"
    attrs.write_text(
        "version = '1.0'\n"
        "default['app']['version'] = version\n"
        "default['app']['path'] = \"/opt/app-#{version}\""
    )
    result = parse_attributes(str(attrs))
    assert isinstance(result, str)


def test_parse_attributes_empty(tmp_path: Path) -> None:
    """Parse empty attributes file."""
    attrs = tmp_path / "default.rb"
    attrs.write_text("")
    result = parse_attributes(str(attrs))
    assert isinstance(result, str)


def test_parse_attributes_invalid() -> None:
    """Parse non-existent attributes file."""
    result = parse_attributes("/nonexistent/attributes.rb")
    assert isinstance(result, str)


# ==============================================================================
# INSPEC CONVERSION
# ==============================================================================


def test_convert_inspec_testinfra(tmp_path: Path) -> None:
    """Convert InSpec to testinfra."""
    inspec = tmp_path / "default.rb"
    inspec.write_text(
        "describe package('nginx') do\n  it { should be_installed }\nend\n"
    )
    result = convert_inspec_to_test(str(inspec), output_format="testinfra")
    assert isinstance(result, str)


def test_convert_inspec_serverspec(tmp_path: Path) -> None:
    """Convert InSpec to serverspec."""
    inspec = tmp_path / "default.rb"
    inspec.write_text(
        "describe package('curl') do\n  it { should be_installed }\nend\n"
    )
    result = convert_inspec_to_test(str(inspec), output_format="serverspec")
    assert isinstance(result, str)


def test_convert_inspec_goss(tmp_path: Path) -> None:
    """Convert InSpec to goss."""
    inspec = tmp_path / "default.rb"
    inspec.write_text(
        "describe service('nginx') do\n  it { should be_installed }\nend\n"
    )
    result = convert_inspec_to_test(str(inspec), output_format="goss")
    assert isinstance(result, str)


def test_convert_inspec_ansible_assert(tmp_path: Path) -> None:
    """Convert InSpec to Ansible assert."""
    inspec = tmp_path / "default.rb"
    inspec.write_text("describe port(80) do\n  it { should be_listening }\nend\n")
    result = convert_inspec_to_test(str(inspec), output_format="ansible_assert")
    assert isinstance(result, str)


def test_convert_inspec_empty(tmp_path: Path) -> None:
    """Convert empty InSpec file."""
    inspec = tmp_path / "empty.rb"
    inspec.write_text("")
    result = convert_inspec_to_test(str(inspec))
    assert isinstance(result, str)


def test_convert_inspec_invalid() -> None:
    """Convert non-existent InSpec file."""
    result = convert_inspec_to_test("/nonexistent/inspec.rb")
    assert isinstance(result, str)


# ==============================================================================
# EDGE CASES AND ERROR HANDLING
# ==============================================================================


def test_recipe_unicode_content(tmp_path: Path) -> None:
    """Recipe with Unicode characters."""
    recipe = tmp_path / "default.rb"
    recipe.write_text(
        "# Unicode comment: café, naïve, résumé\npackage 'nginx'  # 安装 nginx"
    )
    result = generate_playbook_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_recipe_special_chars(tmp_path: Path) -> None:
    """Recipe with special characters."""
    recipe = tmp_path / "default.rb"
    recipe.write_text(
        "file '/path/with spaces' do\n  content \"Special chars: @#$%^&*()\"\nend\n"
    )
    result = generate_playbook_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_attributes_large_file(tmp_path: Path) -> None:
    """Parse very large attributes file."""
    attrs = tmp_path / "default.rb"
    content = "\n".join(f"default['key_{i}'] = 'value_{i}'" for i in range(100))
    attrs.write_text(content)
    result = parse_attributes(str(attrs))
    assert isinstance(result, str)


def test_metadata_with_platforms(tmp_path: Path) -> None:
    """Metadata with many platform declarations."""
    metadata = tmp_path / "metadata.rb"
    platforms = "\n".join(
        f"supports '{os}', '>= {version}'"
        for os, version in [
            ("ubuntu", "18.04"),
            ("centos", "7.0"),
            ("debian", "10.0"),
            ("amazon", "2.0"),
            ("redhat", "8.0"),
        ]
    )
    metadata.write_text(f"name 'multiplatform'\nversion '1.0'\n{platforms}")
    result = read_cookbook_metadata(str(metadata))
    assert isinstance(result, str)


def test_environment_with_complex_nesting() -> None:
    """Environment with very deeply nested attributes."""
    env_content = (
        "name 'nested'\n"
        "default_attributes "
        "'a' => {'b' => {'c' => {'d' => {'e' => {'f' => 'value'}}}}}"
    )
    result = convert_chef_environment_to_inventory_group(env_content, "nested")
    assert isinstance(result, str)


# ==============================================================================
# WORKFLOW COMBINATIONS
# ==============================================================================


def test_recipe_to_playbook_and_parse(tmp_path: Path) -> None:
    """Recipe to playbook and vice versa."""
    recipe = tmp_path / "default.rb"
    recipe.write_text("package 'nginx'\nservice 'nginx' do action :enable end")

    playbook_result = generate_playbook_from_recipe(str(recipe))
    parse_result = parse_recipe(str(recipe))

    assert isinstance(playbook_result, str)
    assert isinstance(parse_result, str)


def test_metadata_and_attributes_workflow(tmp_path: Path) -> None:
    """Read metadata and parse related attributes."""
    cookbook = tmp_path / "app"
    cookbook.mkdir()

    metadata = cookbook / "metadata.rb"
    metadata.write_text("name 'app'\nversion '1.0'\ndepends 'base'")

    attrs = cookbook / "attributes/default.rb"
    attrs.parent.mkdir()
    attrs.write_text("default['app']['port'] = 8080")

    metadata_result = read_cookbook_metadata(str(metadata))
    attrs_result = parse_attributes(str(attrs))
    structure_result = list_cookbook_structure(str(cookbook))

    assert isinstance(metadata_result, str)
    assert isinstance(attrs_result, str)
    assert isinstance(structure_result, str)


def test_complete_cookbook_parsing(tmp_path: Path) -> None:
    """Complete cookbook parsing workflow."""
    cookbook = tmp_path / "complete"
    cookbook.mkdir()

    # Create all files
    (cookbook / "metadata.rb").write_text("name 'complete'\nversion '2.0'")
    (cookbook / "recipes").mkdir()
    (cookbook / "recipes" / "default.rb").write_text("package 'curl'")
    (cookbook / "attributes").mkdir()
    (cookbook / "attributes" / "default.rb").write_text("default['app'] = 'test'")

    # Parse all
    metadata_result = read_cookbook_metadata(str(cookbook / "metadata.rb"))
    recipe_result = parse_recipe(str(cookbook / "recipes" / "default.rb"))
    attrs_result = parse_attributes(str(cookbook / "attributes" / "default.rb"))
    playbook_result = generate_playbook_from_recipe(
        str(cookbook / "recipes" / "default.rb"), cookbook_path=str(cookbook)
    )
    structure_result = list_cookbook_structure(str(cookbook))

    assert all(
        isinstance(r, str)
        for r in [
            metadata_result,
            recipe_result,
            attrs_result,
            playbook_result,
            structure_result,
        ]
    )


def test_environment_inventory_workflow() -> None:
    """Environment to inventory conversion workflow."""
    for env_name in ["production", "staging", "development"]:
        env_content = f"name '{env_name}'\ndefault_attributes 'env' => '{env_name}'"
        result = convert_chef_environment_to_inventory_group(env_content, env_name)
        assert isinstance(result, str)
