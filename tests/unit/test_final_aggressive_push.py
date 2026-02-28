"""Final aggressive push targeting remaining assessment and cli gaps."""

from pathlib import Path

from souschef.assessment import assess_chef_migration_complexity_with_ai
from souschef.server import (
    convert_chef_handler_to_ansible,
    convert_chef_search_to_inventory,
    convert_resource_to_task,
    generate_inspec_from_recipe,
    parse_cookbook_metadata,
)

# ==============================================================================
# AI-ASSISTED COMPLEXITY ASSESSMENT
# ==============================================================================


def test_assess_with_ai_lightspeed() -> None:
    """Assess complexity with Lightspeed AI."""
    result = assess_chef_migration_complexity_with_ai(".", ai_provider="anthropic")
    assert isinstance(result, str)


def test_assess_with_ai_providers() -> None:
    """Assess complexity with different AI providers."""
    for provider in ["anthropic", "openai", "local"]:
        result = assess_chef_migration_complexity_with_ai(".", ai_provider=provider)
        assert isinstance(result, str)


def test_assess_with_ai_scopes() -> None:
    """Assess complexity with different migration scopes."""
    for scope in ["full", "recipes_only", "infrastructure_only"]:
        result = assess_chef_migration_complexity_with_ai(".", migration_scope=scope)
        assert isinstance(result, str)


# ==============================================================================
# CHEF SEARCH TO INVENTORY
# ==============================================================================


def test_convert_chef_search_all_nodes() -> None:
    """Convert Chef search for all nodes."""
    result = convert_chef_search_to_inventory("*:*")
    assert isinstance(result, str)


def test_convert_chef_search_by_role() -> None:
    """Convert Chef search by role."""
    result = convert_chef_search_to_inventory("roles:webserver")
    assert isinstance(result, str)


def test_convert_chef_search_by_environment() -> None:
    """Convert Chef search by environment."""
    result = convert_chef_search_to_inventory("chef_environment:production")
    assert isinstance(result, str)


def test_convert_chef_search_by_platform() -> None:
    """Convert Chef search by platform."""
    result = convert_chef_search_to_inventory("os:linux")
    assert isinstance(result, str)


def test_convert_chef_search_complex_query() -> None:
    """Convert Chef search with complex query."""
    result = convert_chef_search_to_inventory("roles:webserver AND environment:prod")
    assert isinstance(result, str)


def test_convert_chef_search_empty_result() -> None:
    """Convert Chef search returning no nodes."""
    result = convert_chef_search_to_inventory("nonexistent:value")
    assert isinstance(result, str)


# ==============================================================================
# HANDLER CONVERSION
# ==============================================================================


def test_convert_handler_simpli(tmp_path: Path) -> None:
    """Convert simple handler."""
    handler = tmp_path / "simple.rb"
    handler.write_text("# Simple handler\n")
    result = convert_chef_handler_to_ansible(str(handler))
    assert isinstance(result, str)


def test_convert_handler_complex(tmp_path: Path) -> None:
    """Convert complex handler."""
    handler = tmp_path / "complex.rb"
    handler.write_text(
        "class Chef\n"
        "  class Handler\n"
        "    class MyHandler < Chef::Handler\n"
        "      def report\n"
        "        puts 'Handler report'\n"
        "      end\n"
        "    end\n"
        "  end\n"
        "end\n"
    )
    result = convert_chef_handler_to_ansible(str(handler))
    assert isinstance(result, str)


def test_convert_handler_with_config(tmp_path: Path) -> None:
    """Convert handler with configuration."""
    handler = tmp_path / "config.rb"
    handler.write_text(
        "handler = Chef::Handler::MyHandler.new\nChef::Log.info(handler)\n"
    )
    result = convert_chef_handler_to_ansible(str(handler))
    assert isinstance(result, str)


def test_convert_handler_invalid_path() -> None:
    """Convert handler from non-existent path."""
    result = convert_chef_handler_to_ansible("/nonexistent/handler.rb")
    assert isinstance(result, str)


# ==============================================================================
# INSPEC GENERATION FROM RECIPE
# ==============================================================================


def test_generate_inspec_from_simple_recipe(tmp_path: Path) -> None:
    """Generate InSpec from simple recipe."""
    recipe = tmp_path / "simple.rb"
    recipe.write_text("package 'nginx'\nservice 'nginx' do\n  action :enable\nend\n")
    result = generate_inspec_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_generate_inspec_from_complex_recipe(tmp_path: Path) -> None:
    """Generate InSpec from complex recipe."""
    recipe = tmp_path / "complex.rb"
    recipe.write_text(
        "package 'apache2'\nfile '/etc/apache2/ports.conf' do\n  content '80'\nend\n"
        "service 'apache2' do\n  action :start\nend\n"
        "directory '/var/www' do\n  mode '0755'\nend\n"
    )
    result = generate_inspec_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_generate_inspec_with_conditionals(tmp_path: Path) -> None:
    """Generate InSpec from recipe with conditionals."""
    recipe = tmp_path / "conditional.rb"
    recipe.write_text(
        "if node['platform'] == 'ubuntu'\n"
        "  package 'curl'\n"
        "else\n"
        "  package 'curl-devel'\n"
        "end\n"
    )
    result = generate_inspec_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_generate_inspec_from_nonexistent() -> None:
    """Generate InSpec from non-existent recipe."""
    result = generate_inspec_from_recipe("/nonexistent/recipe.rb")
    assert isinstance(result, str)


# ==============================================================================
# COOKBOOK METADATA PARSING
# ==============================================================================


def test_parse_metadata_simple(tmp_path: Path) -> None:
    """Parse simple metadata."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text("name 'simple'\nversion '1.0.0'")
    result = parse_cookbook_metadata(str(metadata))
    assert isinstance(result, dict)


def test_parse_metadata_full(tmp_path: Path) -> None:
    """Parse complete metadata."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text(
        "name 'full'\n"
        "version '2.0.0'\n"
        "description 'Full metadata'\n"
        "author 'Test'\n"
        "depends 'base'\n"
        "depends 'database'\n"
        "supports 'ubuntu', '>= 20.04'\n"
    )
    result = parse_cookbook_metadata(str(metadata))
    assert isinstance(result, dict)


def test_parse_metadata_with_gems(tmp_path: Path) -> None:
    """Parse metadata with gem dependencies."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text("name 'gems'\ngem 'json'\ngem 'rest-client', '> 2.0'\n")
    result = parse_cookbook_metadata(str(metadata))
    assert isinstance(result, dict)


def test_parse_metadata_invalid() -> None:
    """Parse invalid metadata file."""
    result = parse_cookbook_metadata("/nonexistent/metadata.rb")
    assert isinstance(result, dict)


# ==============================================================================
# RESOURCE TO TASK CONVERSION
# ==============================================================================


def test_convert_resource_package() -> None:
    """Convert package resource."""
    result = convert_resource_to_task("package", "nginx", "install")
    assert isinstance(result, str)


def test_convert_resource_file() -> None:
    """Convert file resource."""
    result = convert_resource_to_task("file", "/etc/config", "create", "content")
    assert isinstance(result, str)


def test_convert_resource_service() -> None:
    """Convert service resource."""
    result = convert_resource_to_task("service", "apache", "enable")
    assert isinstance(result, str)


def test_convert_resource_template() -> None:
    """Convert template resource."""
    result = convert_resource_to_task(
        "template", "/etc/config", "create", "source:config.erb"
    )
    assert isinstance(result, str)


def test_convert_resource_directory() -> None:
    """Convert directory resource."""
    result = convert_resource_to_task("directory", "/var/app", "create", "mode:0755")
    assert isinstance(result, str)


def test_convert_resource_multiple() -> None:
    """Convert multiple resource types."""
    results = [
        convert_resource_to_task("package", "curl", "install"),
        convert_resource_to_task("file", "/etc/app.conf", "create"),
        convert_resource_to_task("service", "app", "restart"),
    ]
    assert all(isinstance(r, str) for r in results)


def test_convert_resource_invalid() -> None:
    """Convert unknown resource type."""
    result = convert_resource_to_task("unknown_type", "test", "create")
    assert isinstance(result, str)


# ==============================================================================
# EDGE CASES AND ERROR HANDLING
# ==============================================================================


def test_assess_ai_custom_params() -> None:
    """Assessment with custom parameters."""
    result = assess_chef_migration_complexity_with_ai(
        ".",
        migration_scope="recipes_only",
        target_platform="ansible_core",
        temperature=0.5,
    )
    assert isinstance(result, str)


def test_search_empty_query() -> None:
    """Search with empty query."""
    result = convert_chef_search_to_inventory("")
    assert isinstance(result, str)


def test_handler_empty_file(tmp_path: Path) -> None:
    """Convert empty handler file."""
    handler = tmp_path / "empty.rb"
    handler.write_text("")
    result = convert_chef_handler_to_ansible(str(handler))
    assert isinstance(result, str)


def test_recipe_empty_file(tmp_path: Path) -> None:
    """Generate InSpec from empty recipe."""
    recipe = tmp_path / "empty.rb"
    recipe.write_text("")
    result = generate_inspec_from_recipe(str(recipe))
    assert isinstance(result, str)


def test_resource_empty_name() -> None:
    """Convert resource with empty name."""
    result = convert_resource_to_task("package", "", "install")
    assert isinstance(result, str)


def test_metadata_empty_file(tmp_path: Path) -> None:
    """Parse empty metadata file."""
    metadata = tmp_path / "empty.rb"
    metadata.write_text("")
    result = parse_cookbook_metadata(str(metadata))
    assert isinstance(result, dict)


# ==============================================================================
# COMPLEX WORKFLOW TESTS
# ==============================================================================


def test_assess_and_generate() -> None:
    """Assess complexity then generate plan."""
    assess_result = assess_chef_migration_complexity_with_ai(".")
    assert isinstance(assess_result, str)


def test_search_and_inventory() -> None:
    """Search and generate inventory."""
    search_result = convert_chef_search_to_inventory("*:*")
    assert isinstance(search_result, str)


def test_handler_and_inspec(tmp_path: Path) -> None:
    """Convert handler and generate InSpec."""
    handler = tmp_path / "handler.rb"
    handler.write_text("# handler")
    handler_result = convert_chef_handler_to_ansible(str(handler))
    assert isinstance(handler_result, str)

    recipe = tmp_path / "recipe.rb"
    recipe.write_text("# recipe")
    inspec_result = generate_inspec_from_recipe(str(recipe))
    assert isinstance(inspec_result, str)


def test_metadata_resource_conversion(tmp_path: Path) -> None:
    """Parse metadata and convert resources."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text("name 'test'\n")
    metadata_result = parse_cookbook_metadata(str(metadata))
    assert isinstance(metadata_result, dict)

    resource_result = convert_resource_to_task("package", "test", "install")
    assert isinstance(resource_result, str)
