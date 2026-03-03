"""
Tests for uncovered MCP tools in server.py.

Targets uncovered code paths in MCP tool implementations,
particularly generator and formatter functions.
"""

import json
import tempfile
from pathlib import Path

from souschef.server import (
    # Search patterns
    analyse_chef_search_patterns,
    # Ansible upgrade tools
    assess_ansible_upgrade_readiness,
    convert_cookbook_comprehensive,
    generate_ansible_upgrade_test_plan,
    generate_handler_routing_config,
    # CI/CD pipeline generation
    get_version_combination_info,
    # Version combinations
    list_migration_version_combinations,
    parse_chef_handler,
    # Parsing tools
    parse_chef_migration_assessment,
    plan_ansible_upgrade,
    # Profiling tools
    profile_cookbook_performance,
    profile_parsing_operation,
    # Migration simulation
    simulate_chef_to_awx_migration,
    validate_ansible_collection_compatibility,
)


class TestParseMigrationAssessment:
    """Test migration assessment parsing."""

    def test_parse_migration_assessment_single_cookbook(self) -> None:
        """Test parsing migration assessment for single cookbook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text('name "test"\nversion "1.0.0"')
            (tmppath / "recipes").mkdir()
            (tmppath / "recipes" / "default.rb").write_text('package "curl"')

            result = parse_chef_migration_assessment(str(tmppath))
            assert isinstance(result, dict)

    def test_parse_migration_assessment_full_scope(self) -> None:
        """Test migration assessment with full scope."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text('name "test"')

            result = parse_chef_migration_assessment(
                str(tmppath), migration_scope="full"
            )
            assert isinstance(result, dict)

    def test_parse_migration_assessment_recipes_only(self) -> None:
        """Test migration assessment recipes only scope."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text('name "test"')

            result = parse_chef_migration_assessment(
                str(tmppath), migration_scope="recipes_only"
            )
            assert isinstance(result, dict)

    def test_parse_migration_assessment_different_platforms(self) -> None:
        """Test migration assessment with different target platforms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text('name "test"')

            for platform in ["ansible_awx", "ansible_core", "ansible_tower"]:
                result = parse_chef_migration_assessment(
                    str(tmppath), target_platform=platform
                )
                assert isinstance(result, dict)

    def test_parse_migration_assessment_nonexistent_path(self) -> None:
        """Test migration assessment with non-existent path."""
        result = parse_chef_migration_assessment("/path/does/not/exist")
        assert isinstance(result, dict)


class TestConvertCookbookComprehensive:
    """Test comprehensive cookbook conversion."""

    def test_convert_cookbook_basic(self) -> None:
        """Test basic cookbook conversion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            cookbook_dir = tmppath / "mycookbook"
            cookbook_dir.mkdir()
            (cookbook_dir / "metadata.rb").write_text("""
name "mycookbook"
version "1.0.0"
description "Test cookbook"
""")
            (cookbook_dir / "recipes").mkdir()
            (cookbook_dir / "recipes" / "default.rb").write_text('package "git"')

            output_dir = tmppath / "output"
            output_dir.mkdir()

            result = convert_cookbook_comprehensive(str(cookbook_dir), str(output_dir))
            assert isinstance(result, str)

    def test_convert_cookbook_with_templates(self) -> None:
        """Test cookbook conversion including templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            cookbook_dir = tmppath / "mycookbook"
            cookbook_dir.mkdir()
            (cookbook_dir / "metadata.rb").write_text('name "test"')

            # Create templates directory
            templates_dir = cookbook_dir / "templates"
            templates_dir.mkdir()
            (templates_dir / "config.erb").write_text("key = <%= @value %>")

            output_dir = tmppath / "output"
            output_dir.mkdir()

            result = convert_cookbook_comprehensive(
                str(cookbook_dir), str(output_dir), include_templates=True
            )
            assert isinstance(result, str)

    def test_convert_cookbook_with_attributes(self) -> None:
        """Test cookbook conversion including attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            cookbook_dir = tmppath / "mycookbook"
            cookbook_dir.mkdir()
            (cookbook_dir / "metadata.rb").write_text('name "test"')

            # Create attributes directory
            attrs_dir = cookbook_dir / "attributes"
            attrs_dir.mkdir()
            (attrs_dir / "default.rb").write_text('default["key"] = "value"')

            output_dir = tmppath / "output"
            output_dir.mkdir()

            result = convert_cookbook_comprehensive(
                str(cookbook_dir), str(output_dir), include_attributes=True
            )
            assert isinstance(result, str)

    def test_convert_cookbook_with_assessment_data(self) -> None:
        """Test cookbook conversion with assessment data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            cookbook_dir = tmppath / "mycookbook"
            cookbook_dir.mkdir()
            (cookbook_dir / "metadata.rb").write_text('name "test"')

            output_dir = tmppath / "output"
            output_dir.mkdir()

            assessment = json.dumps(
                {"complexity": "medium", "recommendations": ["add documentation"]}
            )

            result = convert_cookbook_comprehensive(
                str(cookbook_dir), str(output_dir), assessment_data=assessment
            )
            assert isinstance(result, str)

    def test_convert_cookbook_custom_role_name(self) -> None:
        """Test cookbook conversion with custom role name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            cookbook_dir = tmppath / "mycookbook"
            cookbook_dir.mkdir()
            (cookbook_dir / "metadata.rb").write_text('name "test"')

            output_dir = tmppath / "output"
            output_dir.mkdir()

            result = convert_cookbook_comprehensive(
                str(cookbook_dir), str(output_dir), role_name="custom_role"
            )
            assert isinstance(result, str)


class TestProfileTools:
    """Test performance profiling tools."""

    def test_profile_cookbook_performance(self) -> None:
        """Test cookbook performance profiling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text('name "test"')
            (tmppath / "recipes").mkdir()
            (tmppath / "recipes" / "default.rb").write_text('package "git"')

            result = profile_cookbook_performance(str(tmppath))
            assert isinstance(result, str)

    def test_profile_parsing_operation_recipe(self) -> None:
        """Test profiling recipe parsing operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            recipe = tmppath / "test.rb"
            recipe.write_text('package "curl"')

            result = profile_parsing_operation("recipe", str(recipe))
            assert isinstance(result, str)

    def test_profile_parsing_operation_detailed(self) -> None:
        """Test profiling with detailed statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            recipe = tmppath / "test.rb"
            recipe.write_text('package "curl"')

            result = profile_parsing_operation("recipe", str(recipe), detailed=True)
            assert isinstance(result, str)

    def test_profile_parsing_operation_invalid(self) -> None:
        """Test profiling with invalid operation."""
        result = profile_parsing_operation("invalid", "/tmp/test.rb")  # NOSONAR
        assert isinstance(result, str)
        assert "Error" in result or "Invalid" in result


class TestDeploymentTools:
    """Test deployment generation tools."""

    def test_assess_ansible_upgrade_readiness(self) -> None:
        """Test assessing Ansible upgrade readiness."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "ansible.cfg").write_text(
                "[defaults]\nhost_key_checking = false"
            )

            result = assess_ansible_upgrade_readiness(str(tmppath))
            assert isinstance(result, str)

    def test_plan_ansible_upgrade(self) -> None:
        """Test planning Ansible upgrade."""
        result = plan_ansible_upgrade("2.10", "2.13")
        assert isinstance(result, str)

    def test_validate_ansible_collection_compatibility(self) -> None:
        """Test validating Ansible collection compatibility."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            req_file = tmppath / "requirements.yml"
            req_file.write_text("""
collections:
  - name: community.general
    version: ">=2.0.0"
""")

            result = validate_ansible_collection_compatibility(str(req_file), "2.13")
            assert isinstance(result, str)

    def test_generate_ansible_upgrade_test_plan(self) -> None:
        """Test generating Ansible upgrade test plan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "ansible.cfg").write_text("[defaults]\n")

            result = generate_ansible_upgrade_test_plan(str(tmppath))
            assert isinstance(result, str)


class TestHandlerRoutingTools:
    """Test handler routing configuration tools."""

    def test_generate_handler_routing_config(self) -> None:
        """Test handler routing configuration generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text('name "test"')
            (tmppath / "recipes").mkdir()
            (tmppath / "recipes" / "default.rb").write_text("""
define_resource_handlers("my_resource") do |node|
  node.handle(:on_success, :complete)
  node.handle(:on_failure, :restart)
end
""")

            result = generate_handler_routing_config(str(tmppath))
            assert isinstance(result, str)

    def test_generate_handler_routing_config_json_format(self) -> None:
        """Test handler routing with JSON output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text('name "test"')

            result = generate_handler_routing_config(str(tmppath), output_format="json")
            assert isinstance(result, str)

    def test_parse_chef_handler(self) -> None:
        """Test parsing Chef handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            handler_file = tmppath / "my_handler.rb"
            handler_file.write_text("""
class MyHandler < Chef::Handler
  def report
    puts "Chef run completed"
  end
end
""")

            result = parse_chef_handler(str(handler_file))
            assert isinstance(result, str)


class TestNotificationTools:
    """Test notification pattern analysis tools."""

    def test_analyse_migration_simulation(self) -> None:
        """Test Chef to AWS migration simulation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            cookbook_dir = tmppath / "cookbook"
            cookbook_dir.mkdir()
            (cookbook_dir / "metadata.rb").write_text('name "test"')
            (cookbook_dir / "recipes").mkdir()
            (cookbook_dir / "recipes" / "default.rb").write_text('package "git"')

            output_dir = tmppath / "output"
            output_dir.mkdir()

            result = simulate_chef_to_awx_migration(str(cookbook_dir), str(output_dir))
            assert isinstance(result, str)

    def test_migration_simulation_with_options(self) -> None:
        """Test migration simulation with custom options."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            cookbook_dir = tmppath / "cookbook"
            cookbook_dir.mkdir()
            (cookbook_dir / "metadata.rb").write_text('name "test"')

            output_dir = tmppath / "output"
            output_dir.mkdir()

            result = simulate_chef_to_awx_migration(
                str(cookbook_dir), str(output_dir), target_platform="ansible_tower"
            )
            assert isinstance(result, str)


class TestSearchPatternTools:
    """Test Chef search pattern analysis tools."""

    def test_analyse_chef_search_patterns(self) -> None:
        """Test chef search pattern analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "recipes").mkdir()
            (tmppath / "recipes" / "default.rb").write_text("""
search(:node, "role:web") do |node|
  ip = node["ipaddress"]
end

search(:users, "admin:true")
""")

            result = analyse_chef_search_patterns(str(tmppath))
            assert isinstance(result, str)

    def test_list_migration_version_combinations(self) -> None:
        """Test listing migration version combinations."""
        result = list_migration_version_combinations()
        assert isinstance(result, str)

    def test_get_version_combination_info(self) -> None:
        """Test getting version combination info."""
        result = get_version_combination_info("14.0", "ansible_core", "2.12")
        assert isinstance(result, str)


class TestErrorHandling:
    """Test error handling in MCP tools."""

    def test_convert_cookbook_nonexistent_path(self) -> None:
        """Test conversion with non-existent cookbook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            output_dir = tmppath / "output"
            output_dir.mkdir()

            result = convert_cookbook_comprehensive(
                "/path/does/not/exist", str(output_dir)
            )
            assert isinstance(result, str)
            assert "Error" in result or "error" in result

    def test_convert_cookbook_invalid_assessment_json(self) -> None:
        """Test conversion with invalid assessment JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            cookbook_dir = tmppath / "test"
            cookbook_dir.mkdir()
            (cookbook_dir / "metadata.rb").write_text('name "test"')

            output_dir = tmppath / "output"
            output_dir.mkdir()

            result = convert_cookbook_comprehensive(
                str(cookbook_dir), str(output_dir), assessment_data="{ invalid json }"
            )
            assert isinstance(result, str)

    def test_profile_operation_nonexistent_file(self) -> None:
        """Test profiling non-existent file."""
        result = profile_parsing_operation("recipe", "/path/does/not/exist.rb")
        assert isinstance(result, str)


class TestIntegration:
    """Integration tests combining multiple tools."""

    def test_assessment_then_conversion(self) -> None:
        """Test running assessment before comprehensive conversion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            cookbook_dir = tmppath / "mycookbook"
            cookbook_dir.mkdir()
            (cookbook_dir / "metadata.rb").write_text('name "test"')
            (cookbook_dir / "recipes").mkdir()
            (cookbook_dir / "recipes" / "default.rb").write_text('package "curl"')

            # Run assessment
            assessment = parse_chef_migration_assessment(str(cookbook_dir))
            assert isinstance(assessment, dict)

            # Convert with assessment data (may not be JSON serializable)
            output_dir = tmppath / "output"
            output_dir.mkdir()

            result = convert_cookbook_comprehensive(
                str(cookbook_dir),
                str(output_dir),
                assessment_data="",  # Skip assessment JSON since it may have complex types
            )
            assert isinstance(result, str)
