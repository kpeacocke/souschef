"""
Comprehensive test suite targeting uncovered lines in assessment.py.

This module focuses on maximal coverage of assessment.py, targeting:

- Error handling paths (uncovered conditional branches)
- Rare code paths and edge cases
- AI-related functions with mocked dependencies
- Helper functions for formatting and analysis
- Validation functions with invalid inputs
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from souschef.assessment import (
    ActivityBreakdown,
    _analyse_cookbook_dependencies_detailed,
    _analyse_cookbook_metrics,
    _analyze_attributes,
    _analyze_libraries,
    _analyze_recipes,
    _analyze_templates,
    _assess_custom_resource_risks,
    _assess_migration_risks,
    _assess_single_cookbook,
    _assess_technical_complexity_risks,
    _assess_timeline_risks,
    _build_validation_header,
    _calculate_activity_breakdown,
    _calculate_complexity_score,
    _call_ai_api,
    _call_anthropic_api,
    _call_openai_api,
    _call_watson_api,
    _collect_berks_dependencies,
    _collect_metadata_dependencies,
    _count_cookbook_artifacts,
    _create_migration_roadmap,
    _determine_migration_order,
    _determine_migration_priority,
    _format_activity_breakdown,
    _format_circular_dependencies,
    _format_community_cookbooks,
    _format_dependency_graph,
    _format_dependency_overview,
    _format_external_dependencies,
    _format_migration_order,
    _format_overall_metrics,
    _generate_migration_recommendations_from_assessment,
    _get_ai_cookbook_analysis,
    _get_metadata_content,
    _get_recipe_content_sample,
    _identify_circular_dependencies,
    _identify_migration_challenges,
    _identify_top_challenges,
    _is_ai_available,
    _parse_berksfile,
    _parse_chefignore,
    _parse_cookbook_paths,
    _parse_metadata_file,
    _parse_thorfile,
    validate_conversion,
)


class TestActivityBreakdown:
    """Test ActivityBreakdown dataclass properties and methods."""

    def test_activity_breakdown_manual_days_property(self) -> None:
        """Test manual_days property conversion."""
        activity = ActivityBreakdown(
            activity_type="Recipes",
            count=5,
            manual_hours=24.0,
            ai_assisted_hours=8.0,
            complexity_factor=1.0,
            description="Test",
        )
        assert activity.manual_days == pytest.approx(3.0)

    def test_activity_breakdown_ai_assisted_days_property(self) -> None:
        """Test ai_assisted_days property conversion."""
        activity = ActivityBreakdown(
            activity_type="Templates",
            count=3,
            manual_hours=16.0,
            ai_assisted_hours=4.0,
            complexity_factor=1.0,
            description="Test",
        )
        assert activity.ai_assisted_days == pytest.approx(0.5)

    def test_activity_breakdown_time_saved_hours(self) -> None:
        """Test time_saved_hours calculation."""
        activity = ActivityBreakdown(
            activity_type="Custom Resources",
            count=2,
            manual_hours=20.0,
            ai_assisted_hours=10.0,
            complexity_factor=1.0,
            description="Test",
        )
        assert activity.time_saved_hours == pytest.approx(10.0)

    def test_activity_breakdown_efficiency_gain_percent(self) -> None:
        """Test efficiency_gain_percent calculation."""
        activity = ActivityBreakdown(
            activity_type="Recipes",
            count=5,
            manual_hours=20.0,
            ai_assisted_hours=5.0,
            complexity_factor=1.0,
            description="Test",
        )
        assert activity.efficiency_gain_percent == 75

    def test_activity_breakdown_efficiency_gain_zero_hours(self) -> None:
        """Test efficiency_gain_percent with zero manual hours."""
        activity = ActivityBreakdown(
            activity_type="Files",
            count=0,
            manual_hours=0.0,
            ai_assisted_hours=0.0,
            complexity_factor=1.0,
            description="Test",
        )
        assert activity.efficiency_gain_percent == 0

    def test_activity_breakdown_string_representation(self) -> None:
        """Test __str__ method."""
        activity = ActivityBreakdown(
            activity_type="Recipes",
            count=5,
            manual_hours=15.0,
            ai_assisted_hours=5.0,
            complexity_factor=1.0,
            description="Test",
        )
        result = str(activity)
        assert "Recipes" in result
        assert "15.0h" in result
        assert "5.0h" in result
        assert "5 items" in result


class TestCookbookArtifactCounting:
    """Test _count_cookbook_artifacts with various directory structures."""

    def test_count_cookbook_artifacts_empty_cookbook(self, tmp_path: Path) -> None:
        """Test counting artifacts in empty cookbook."""
        cookbook = tmp_path / "empty_cookbook"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'empty'")

        result = _count_cookbook_artifacts(cookbook)
        assert result["recipe_count"] == 0
        assert result["template_count"] == 0
        assert result["attributes_count"] == 0

    def test_count_cookbook_artifacts_with_all_types(self, tmp_path: Path) -> None:
        """Test counting all artifact types."""
        cookbook = tmp_path / "full_cookbook"
        cookbook.mkdir()

        # Create all artifact types
        (cookbook / "metadata.rb").write_text("name 'full'")
        recipes_dir = cookbook / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")
        (recipes_dir / "web.rb").write_text("package 'apache2'")

        templates_dir = cookbook / "templates"
        templates_dir.mkdir()
        (templates_dir / "config.erb").write_text("<%= @var %>")

        attributes_dir = cookbook / "attributes"
        attributes_dir.mkdir()
        (attributes_dir / "default.rb").write_text("default[:key] = 'value'")

        libraries_dir = cookbook / "libraries"
        libraries_dir.mkdir()
        (libraries_dir / "helper.rb").write_text("module Helper; end")

        result = _count_cookbook_artifacts(cookbook)
        assert result["recipe_count"] == 2
        assert result["template_count"] == 1
        assert result["attributes_count"] == 1
        assert result["libraries_count"] == 1
        assert result["has_berksfile"] == 0

    def test_count_cookbook_artifacts_with_nested_templates(
        self, tmp_path: Path
    ) -> None:
        """Test counting nested template files."""
        cookbook = tmp_path / "nested_cookbook"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'nested'")

        templates_dir = cookbook / "templates"
        nested = templates_dir / "ubuntu" / "20.04"
        nested.mkdir(parents=True)
        (nested / "nginx.erb").write_text("<%= @config %>")
        (templates_dir / "default.erb").write_text("<%= @default %>")

        result = _count_cookbook_artifacts(cookbook)
        assert result["template_count"] == 2

    def test_count_cookbook_artifacts_with_berksfile(self, tmp_path: Path) -> None:
        """Test detecting Berksfile presence."""
        cookbook = tmp_path / "berks_cookbook"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'berks'")
        (cookbook / "Berksfile").write_text("cookbook 'nginx'")

        result = _count_cookbook_artifacts(cookbook)
        assert result["has_berksfile"] == 1

    def test_count_cookbook_artifacts_with_kitchen_yml(self, tmp_path: Path) -> None:
        """Test detecting .kitchen.yml presence."""
        cookbook = tmp_path / "kitchen_cookbook"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'kitchen'")
        (cookbook / ".kitchen.yml").write_text("driver:\n  name: vagrant")

        result = _count_cookbook_artifacts(cookbook)
        assert result["has_kitchen_yml"] == 1

    def test_count_cookbook_artifacts_with_test_directory(self, tmp_path: Path) -> None:
        """Test detecting test directory."""
        cookbook = tmp_path / "test_cookbook"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'tested'")
        test_dir = cookbook / "test"
        test_dir.mkdir()
        (test_dir / "integration").mkdir()

        result = _count_cookbook_artifacts(cookbook)
        assert result["has_test_dir"] == 1


class TestRecipeAnalysis:
    """Test _analyze_recipes and related recipe analysis functions."""

    def test_analyze_recipes_empty_directory(self, tmp_path: Path) -> None:
        """Test analyzing recipes in empty directory."""
        cookbook = tmp_path / "empty"
        cookbook.mkdir()

        resource_count, ruby_blocks, custom_resources = _analyze_recipes(cookbook)
        assert resource_count == 0
        assert ruby_blocks == 0
        assert custom_resources == 0

    def test_analyze_recipes_with_resources(self, tmp_path: Path) -> None:
        """Test analyzing recipes with various resource types."""
        cookbook = tmp_path / "recipes"
        cookbook.mkdir()
        recipes_dir = cookbook / "recipes"
        recipes_dir.mkdir()

        (recipes_dir / "default.rb").write_text(
            'package "nginx" do\n  action :install\nend\n'
            'service "apache2" do\n  action :start\nend'
        )

        resource_count, _, _ = _analyze_recipes(cookbook)
        assert resource_count > 0

    def test_analyze_recipes_with_ruby_blocks(self, tmp_path: Path) -> None:
        """Test analyzing recipes with ruby blocks."""
        cookbook = tmp_path / "ruby_blocks"
        cookbook.mkdir()
        recipes_dir = cookbook / "recipes"
        recipes_dir.mkdir()

        (recipes_dir / "default.rb").write_text(
            "ruby_block 'execute' do\n  block { puts 'test' }\nend\n"
            "execute 'echo test' do\nend"
        )

        _, ruby_blocks, _ = _analyze_recipes(cookbook)
        assert ruby_blocks > 0

    def test_analyze_recipes_with_custom_resources(self, tmp_path: Path) -> None:
        """Test analyzing recipes with custom resources."""
        cookbook = tmp_path / "custom"
        cookbook.mkdir()
        recipes_dir = cookbook / "recipes"
        recipes_dir.mkdir()

        (recipes_dir / "default.rb").write_text(
            "provides :my_resource\n"
            "use_inline_resources\n"
            "action :create do\n  converge_by 'test'\nend"
        )

        _, _, custom_resources = _analyze_recipes(cookbook)
        assert custom_resources > 0


class TestAttributeAnalysis:
    """Test _analyze_attributes function."""

    def test_analyze_attributes_empty_directory(self, tmp_path: Path) -> None:
        """Test analyzing attributes in empty directory."""
        cookbook = tmp_path / "empty"
        cookbook.mkdir()

        result = _analyze_attributes(cookbook)
        assert result == 0

    def test_analyze_attributes_with_assignments(self, tmp_path: Path) -> None:
        """Test analyzing attributes with value assignments."""
        cookbook = tmp_path / "attrs"
        cookbook.mkdir()
        attrs_dir = cookbook / "attributes"
        attrs_dir.mkdir()

        (attrs_dir / "default.rb").write_text(
            "default[:nginx][:version] = '1.0'\n"
            "default[:nginx][:port] = 8080\n"
            "node[:app][:config] = {}"
        )

        result = _analyze_attributes(cookbook)
        assert result > 0


class TestTemplateAnalysis:
    """Test _analyze_templates function."""

    def test_analyze_templates_empty_directory(self, tmp_path: Path) -> None:
        """Test analyzing templates in empty directory."""
        cookbook = tmp_path / "empty"
        cookbook.mkdir()

        result = _analyze_templates(cookbook)
        assert result == 0

    def test_analyze_templates_with_erb(self, tmp_path: Path) -> None:
        """Test analyzing templates with ERB expressions."""
        cookbook = tmp_path / "templates"
        cookbook.mkdir()
        templates_dir = cookbook / "templates"
        templates_dir.mkdir()

        (templates_dir / "config.erb").write_text(
            "<%= @var1 %>\n<%= @var2 %>\n<%# comment %>\n"
        )

        result = _analyze_templates(cookbook)
        assert result > 0


class TestLibraryAnalysis:
    """Test _analyze_libraries function."""

    def test_analyze_libraries_empty_directory(self, tmp_path: Path) -> None:
        """Test analyzing libraries in empty directory."""
        cookbook = tmp_path / "empty"
        cookbook.mkdir()

        result = _analyze_libraries(cookbook)
        assert result == 0

    def test_analyze_libraries_with_classes_and_methods(self, tmp_path: Path) -> None:
        """Test analyzing libraries with classes and methods."""
        cookbook = tmp_path / "libraries"
        cookbook.mkdir()
        lib_dir = cookbook / "libraries"
        lib_dir.mkdir()

        (lib_dir / "helpers.rb").write_text(
            "module Helpers\n  class ServiceHelper\n    def self.get_status\n"
            "    end\n    def format_output\n    end\n  end\nend"
        )

        result = _analyze_libraries(cookbook)
        assert result > 0


class TestComplexityCalculation:
    """Test complexity scoring and priority determination."""

    def test_calculate_complexity_score_low(self) -> None:
        """Test complexity score calculation for low complexity cookbook."""
        metrics = {
            "recipe_count": 1,
            "resource_count": 5,
            "custom_resources": 0,
            "ruby_blocks": 0,
            "template_count": 0,
            "file_count": 0,
        }
        score = _calculate_complexity_score(metrics)
        assert score < 30

    def test_calculate_complexity_score_high(self) -> None:
        """Test complexity score calculation for high complexity cookbook."""
        metrics = {
            "recipe_count": 10,
            "resource_count": 50,
            "custom_resources": 5,
            "ruby_blocks": 10,
            "template_count": 20,
            "file_count": 30,
        }
        score = _calculate_complexity_score(metrics)
        assert score > 50

    def test_determine_migration_priority_low(self) -> None:
        """Test priority determination for low complexity."""
        priority = _determine_migration_priority(20)
        assert priority == "low"

    def test_determine_migration_priority_medium(self) -> None:
        """Test priority determination for medium complexity."""
        priority = _determine_migration_priority(50)
        assert priority == "medium"

    def test_determine_migration_priority_high(self) -> None:
        """Test priority determination for high complexity."""
        priority = _determine_migration_priority(80)
        assert priority == "high"

    def test_identify_migration_challenges_with_custom_resources(self) -> None:
        """Test challenge identification with custom resources."""
        metrics = {
            "recipe_count": 5,
            "resource_count": 20,
            "custom_resources": 3,
            "ruby_blocks": 2,
            "template_count": 5,
            "file_count": 10,
        }
        challenges = _identify_migration_challenges(metrics, 50)
        assert len(challenges) > 0
        assert any("custom resource" in c.lower() for c in challenges)

    def test_identify_migration_challenges_with_ruby_blocks(self) -> None:
        """Test challenge identification with many ruby blocks."""
        metrics = {
            "recipe_count": 5,
            "resource_count": 20,
            "custom_resources": 0,
            "ruby_blocks": 10,
            "template_count": 5,
            "file_count": 10,
        }
        challenges = _identify_migration_challenges(metrics, 50)
        assert any("ruby block" in c.lower() for c in challenges)

    def test_identify_migration_challenges_high_complexity(self) -> None:
        """Test challenge identification with high complexity."""
        metrics = {
            "recipe_count": 5,
            "resource_count": 20,
            "custom_resources": 0,
            "ruby_blocks": 0,
            "template_count": 5,
            "file_count": 10,
        }
        challenges = _identify_migration_challenges(metrics, 80)
        assert any("expert review" in c.lower() for c in challenges)


class TestMetadataFileParsing:
    """Test _parse_metadata_file function."""

    def test_parse_metadata_file_nonexistent(self, tmp_path: Path) -> None:
        """Test parsing nonexistent metadata file."""
        cookbook = tmp_path / "no_metadata"
        cookbook.mkdir()

        result = _parse_metadata_file(cookbook)
        assert result["name"] == ""
        assert result["version"] == ""
        assert result["complexity"] == 0

    def test_parse_metadata_file_with_dependencies(self, tmp_path: Path) -> None:
        """Test parsing metadata with cookbook dependencies."""
        cookbook = tmp_path / "with_deps"
        cookbook.mkdir()

        (cookbook / "metadata.rb").write_text(
            "name 'my-cookbook'\n"
            "version '1.0.0'\n"
            "depends 'nginx', '~> 2.0'\n"
            "depends 'apache2'\n"
            "supports 'ubuntu', '>= 20.04'\n"
            "recipe 'default', 'Main recipe'\n"
            "attribute 'key', 'Description'"
        )

        result = _parse_metadata_file(cookbook)
        assert result["name"] == "my-cookbook"
        assert result["version"] == "1.0.0"
        assert len(result["dependencies"]) == 2
        assert len(result["supports"]) == 1
        assert result["recipes"] == 1
        assert result["attributes"] == 1


class TestBerksfileParsing:
    """Test _parse_berksfile function."""

    def test_parse_berksfile_nonexistent(self, tmp_path: Path) -> None:
        """Test parsing nonexistent Berksfile."""
        cookbook = tmp_path / "no_berks"
        cookbook.mkdir()

        result = _parse_berksfile(cookbook)
        assert result["dependencies"] == []
        assert result["complexity"] == 0

    def test_parse_berksfile_with_dependencies(self, tmp_path: Path) -> None:
        """Test parsing Berksfile with dependencies."""
        cookbook = tmp_path / "with_berks"
        cookbook.mkdir()

        (cookbook / "Berksfile").write_text(
            "source 'https://supermarket.chef.io'\n"
            "cookbook 'nginx', '~> 2.0'\n"
            "cookbook 'apache2', git: 'https://github.com/chef-cookbook/apache2.git'\n"
            "cookbook 'local', path: './cookbooks/local'"
        )

        result = _parse_berksfile(cookbook)
        assert len(result["dependencies"]) == 3
        assert result["has_git_sources"] is True
        assert result["has_path_sources"] is True


class TestChefignoreParsing:
    """Test _parse_chefignore function."""

    def test_parse_chefignore_nonexistent(self, tmp_path: Path) -> None:
        """Test parsing nonexistent chefignore."""
        cookbook = tmp_path / "no_ignore"
        cookbook.mkdir()

        result = _parse_chefignore(cookbook)
        assert result["patterns"] == []
        assert result["complexity"] == 0

    def test_parse_chefignore_with_patterns(self, tmp_path: Path) -> None:
        """Test parsing chefignore with patterns."""
        cookbook = tmp_path / "with_ignore"
        cookbook.mkdir()

        (cookbook / "chefignore").write_text(
            "# Comment\n*.swp\n*~\n**/.git\ntest/\nspec/"
        )

        result = _parse_chefignore(cookbook)
        assert len(result["patterns"]) == 5
        assert result["has_wildcards"] is True
        assert result["pattern_count"] == 5


class TestThorfileParsing:
    """Test _parse_thorfile function."""

    def test_parse_thorfile_nonexistent(self, tmp_path: Path) -> None:
        """Test parsing nonexistent Thorfile."""
        cookbook = tmp_path / "no_thor"
        cookbook.mkdir()

        result = _parse_thorfile(cookbook)
        assert result["tasks"] == []
        assert result["complexity"] == 0

    def test_parse_thorfile_with_tasks(self, tmp_path: Path) -> None:
        """Test parsing Thorfile with tasks."""
        cookbook = tmp_path / "with_thor"
        cookbook.mkdir()

        (cookbook / "Thorfile").write_text(
            "desc 'Run all tests'\n"
            "def test\n"
            "  system 'rspec'\n"
            "end\n"
            "desc 'Lint cookbook'\n"
            "def lint\n"
            "  system 'cookstyle'\n"
            "end"
        )

        result = _parse_thorfile(cookbook)
        assert result["tasks"] == 2
        assert result["methods"] >= 2
        assert result["has_tasks"] is True


class TestDependencyAnalysis:
    """Test cookbook dependency analysis functions."""

    def test_collect_metadata_dependencies_none(self, tmp_path: Path) -> None:
        """Test collecting dependencies when none exist."""
        cookbook = tmp_path / "no_deps"
        cookbook.mkdir()

        result = _collect_metadata_dependencies(cookbook)
        assert result == []

    def test_collect_metadata_dependencies_multiple(self, tmp_path: Path) -> None:
        """Test collecting multiple metadata dependencies."""
        cookbook = tmp_path / "multi_deps"
        cookbook.mkdir()

        (cookbook / "metadata.rb").write_text(
            "name 'multi'\n"
            "depends 'nginx'\n"
            "depends 'apache2', '~> 2.0'\n"
            "depends 'mysql'"
        )

        result = _collect_metadata_dependencies(cookbook)
        assert len(result) == 3

    def test_collect_berks_dependencies_multiple(self, tmp_path: Path) -> None:
        """Test collecting multiple Berksfile dependencies."""
        cookbook = tmp_path / "berks_multi"
        cookbook.mkdir()

        (cookbook / "Berksfile").write_text(
            "cookbook 'nginx'\ncookbook 'apache2'\ncookbook 'mysql'"
        )

        result = _collect_berks_dependencies(cookbook)
        assert len(result) == 3

    def test_analyse_cookbook_dependencies_detailed_simple(
        self, tmp_path: Path
    ) -> None:
        """Test detailed dependency analysis for simple cookbook."""
        cookbook = tmp_path / "simple"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'simple'\ndepends 'nginx'")

        result = _analyse_cookbook_dependencies_detailed(cookbook)
        assert result["cookbook_name"] == "simple"
        assert len(result["direct_dependencies"]) == 1

    def test_identify_circular_dependencies_no_circular(self) -> None:
        """Test identifying circular dependencies when none exist."""
        analysis = {
            "cookbook_name": "my_cookbook",
            "direct_dependencies": ["nginx", "apache2"],
            "transitive_dependencies": [],
            "external_dependencies": [],
            "community_cookbooks": [],
            "circular_dependencies": [],
        }
        result = _identify_circular_dependencies(analysis)
        assert len(result) == 0

    def test_determine_migration_order_no_dependencies(self) -> None:
        """Test migration order for cookbook with no dependencies."""
        analysis = {
            "cookbook_name": "standalone",
            "direct_dependencies": [],
            "transitive_dependencies": [],
            "external_dependencies": [],
            "community_cookbooks": [],
            "circular_dependencies": [],
        }
        result = _determine_migration_order(analysis)
        assert len(result) > 0
        assert result[0]["priority"] == 1


class TestFormatFunctions:
    """Test various formatting helper functions."""

    def test_format_overall_metrics(self) -> None:
        """Test formatting overall metrics."""
        metrics = {
            "total_cookbooks": 3,
            "total_recipes": 15,
            "total_resources": 50,
            "avg_complexity": 45.0,
            "estimated_effort_days": 10.0,
        }
        result = _format_overall_metrics(metrics)
        assert "3" in result
        assert "15" in result
        assert "50" in result

    def test_format_dependency_overview(self) -> None:
        """Test formatting dependency overview."""
        analysis = {
            "cookbook_name": "test",
            "direct_dependencies": ["nginx", "apache2"],
            "external_dependencies": ["community"],
            "community_cookbooks": ["nginx"],
            "circular_dependencies": [],
        }
        result = _format_dependency_overview(analysis)
        assert "Direct Dependencies: 2" in result
        assert "External Dependencies: 1" in result

    def test_format_dependency_graph(self) -> None:
        """Test formatting dependency graph."""
        analysis = {
            "cookbook_name": "my_cookbook",
            "direct_dependencies": ["dep1", "dep2"],
            "external_dependencies": [],
            "community_cookbooks": [],
            "circular_dependencies": [],
        }
        result = _format_dependency_graph(analysis)
        assert "my_cookbook" in result
        assert "dep1" in result

    def test_format_migration_order(self) -> None:
        """Test formatting migration order."""
        order = [
            {
                "cookbook": "nginx",
                "priority": 1,
                "reason": "No dependencies",
            },
            {
                "cookbook": "app",
                "priority": 2,
                "reason": "Depends on nginx",
            },
        ]
        result = _format_migration_order(order)
        assert "nginx" in result
        assert "app" in result

    def test_format_circular_dependencies_empty(self) -> None:
        """Test formatting empty circular dependencies."""
        result = _format_circular_dependencies([])
        assert "No circular dependencies detected" in result

    def test_format_circular_dependencies_detected(self) -> None:
        """Test formatting detected circular dependencies."""
        circular = [{"cookbook1": "a", "cookbook2": "b", "type": "potential"}]
        result = _format_circular_dependencies(circular)
        assert "a" in result
        assert "b" in result

    def test_format_external_dependencies_empty(self) -> None:
        """Test formatting external dependencies when empty."""
        analysis = {"external_dependencies": []}
        result = _format_external_dependencies(analysis)
        assert "No external dependencies" in result

    def test_format_community_cookbooks_none(self) -> None:
        """Test formatting community cookbooks when none identified."""
        analysis = {"community_cookbooks": []}
        result = _format_community_cookbooks(analysis)
        assert "No community cookbooks" in result

    def test_format_community_cookbooks_identified(self) -> None:
        """Test formatting identified community cookbooks."""
        analysis = {"community_cookbooks": ["nginx", "apache2"]}
        result = _format_community_cookbooks(analysis)
        assert "nginx" in result
        assert "apache2" in result


class TestRiskAssessment:
    """Test risk assessment functions."""

    def test_assess_technical_complexity_risks_low(self) -> None:
        """Test risk assessment for low complexity cookbooks."""
        assessments = [
            {"complexity_score": 20, "metrics": {}, "estimated_effort_days": 2}
        ]
        result = _assess_technical_complexity_risks(assessments)
        assert len(result) == 0

    def test_assess_technical_complexity_risks_high(self) -> None:
        """Test risk assessment for high complexity cookbooks."""
        assessments = [
            {"complexity_score": 80, "metrics": {}, "estimated_effort_days": 10}
        ]
        result = _assess_technical_complexity_risks(assessments)
        assert len(result) > 0

    def test_assess_custom_resource_risks_multiple(self) -> None:
        """Test custom resource risk assessment."""
        assessments = [
            {
                "complexity_score": 50,
                "metrics": {"custom_resources": 5, "ruby_blocks": 15},
                "estimated_effort_days": 5,
            }
        ]
        result = _assess_custom_resource_risks(assessments)
        assert len(result) > 0

    def test_assess_timeline_risks_large_effort(self) -> None:
        """Test timeline risk assessment for large effort."""
        assessments = [
            {"complexity_score": 50, "metrics": {}, "estimated_effort_days": 100}
        ]
        result = _assess_timeline_risks(assessments)
        assert len(result) > 0

    def test_assess_platform_risks_awx(self) -> None:
        """Test platform risk assessment for AWX."""
        result = _assess_migration_risks([], "ansible_awx")
        assert len(result) > 0

    def test_identify_top_challenges(self) -> None:
        """Test identifying top migration challenges."""
        assessments = [
            {
                "challenges": ["Challenge A", "Challenge B"],
            },
            {
                "challenges": ["Challenge A", "Challenge C"],
            },
        ]
        result = _identify_top_challenges(assessments)
        assert "Challenge A" in result


class TestValidationFunctions:
    """Test validation and output functions."""

    def test_build_validation_header(self) -> None:
        """Test building validation header."""
        summary = {"errors": 2, "warnings": 5, "info": 1}
        result = _build_validation_header("recipe", summary)
        assert len(result) > 0
        assert "2" in "\n".join(result)

    def test_validate_conversion_recipe(self) -> None:
        """Test converting a recipe validation."""
        content = "package 'nginx' do\n  action :install\nend"
        result = validate_conversion("recipe", content, "text")
        assert isinstance(result, str)

    def test_validate_conversion_json_output(self) -> None:
        """Test conversion validation with JSON output."""
        content = "package 'nginx'"
        result = validate_conversion("resource", content, "json")
        # Should be valid JSON or error message
        assert isinstance(result, str)


class TestActivityBreakdownCalculation:
    """Test _calculate_activity_breakdown function."""

    def test_calculate_activity_breakdown_recipes(self) -> None:
        """Test activity breakdown for recipes."""
        metrics = {
            "recipe_count": 5,
            "template_count": 0,
            "attributes_count": 0,
            "custom_resources": 0,
            "libraries_count": 0,
            "resource_count": 20,
            "file_count": 0,
            "definition_count": 0,
        }
        result = _calculate_activity_breakdown(metrics, 50)
        assert len(result) > 0
        recipe_activity = next(
            (a for a in result if a.activity_type == "Recipes"), None
        )
        assert recipe_activity is not None

    def test_calculate_activity_breakdown_multiple_types(self) -> None:
        """Test activity breakdown with multiple artifact types."""
        metrics = {
            "recipe_count": 5,
            "template_count": 3,
            "attributes_count": 2,
            "custom_resources": 1,
            "libraries_count": 1,
            "resource_count": 20,
            "file_count": 10,
            "definition_count": 1,
        }
        result = _calculate_activity_breakdown(metrics, 60)
        assert len(result) >= 4

    def test_format_activity_breakdown_output(self) -> None:
        """Test formatting activity breakdown."""
        activities = [
            ActivityBreakdown(
                activity_type="Recipes",
                count=5,
                manual_hours=20.0,
                ai_assisted_hours=7.0,
                complexity_factor=1.0,
                description="Recipe conversion",
            ),
            ActivityBreakdown(
                activity_type="Templates",
                count=3,
                manual_hours=10.0,
                ai_assisted_hours=4.0,
                complexity_factor=1.0,
                description="Template conversion",
            ),
        ]
        result = _format_activity_breakdown(activities)
        assert "Recipes" in result
        assert "Templates" in result


class TestAIIntegration:
    """Test AI-related functions with mocking."""

    def test_is_ai_available_no_api_key(self) -> None:
        """Test AI availability check with no API key."""
        result = _is_ai_available("anthropic", "")
        assert result is False

    def test_is_ai_available_anthropic_with_requests(self) -> None:
        """Test AI availability for Anthropic with requests."""
        with patch("souschef.assessment.requests", Mock()):
            result = _is_ai_available("anthropic", "test_key")
            assert result is True

    def test_is_ai_available_watson_no_client(self) -> None:
        """Test AI availability for Watson without client."""
        with patch("souschef.assessment.APIClient", None):
            result = _is_ai_available("watson", "test_key")
            assert result is False

    def test_call_ai_api_unsupported_provider(self) -> None:
        """Test calling unsupported AI provider."""
        result = _call_ai_api("prompt", "unsupported", "key", "model", 0.5, 1000)
        assert result is None

    @patch("souschef.assessment.requests")
    def test_call_anthropic_api_success(self, mock_requests: Mock) -> None:
        """Test successful Anthropic API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": '{"complexity_score": 50}'}]
        }
        mock_requests.post.return_value = mock_response

        result = _call_anthropic_api("prompt", "key", "model", 0.5, 1000)
        assert result is not None

    @patch("souschef.assessment.requests")
    def test_call_anthropic_api_failure(self, mock_requests: Mock) -> None:
        """Test failed Anthropic API call."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_requests.post.return_value = mock_response

        result = _call_anthropic_api("prompt", "key", "model", 0.5, 1000)
        assert result is None

    @patch("souschef.assessment.requests")
    def test_call_openai_api_success(self, mock_requests: Mock) -> None:
        """Test successful OpenAI API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"complexity_score": 50}'}}]
        }
        mock_requests.post.return_value = mock_response

        result = _call_openai_api("prompt", "key", "model", 0.5, 1000)
        assert result is not None

    @patch("souschef.assessment.requests")
    def test_call_openai_api_failure(self, mock_requests: Mock) -> None:
        """Test failed OpenAI API call."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_requests.post.return_value = mock_response

        result = _call_openai_api("prompt", "key", "model", 0.5, 1000)
        assert result is None

    def test_call_watson_api_no_client(self) -> None:
        """Test Watson API call with no client available."""
        with patch("souschef.assessment.APIClient", None):
            result = _call_watson_api("prompt", "key", "model", 0.5, 1000, "project_id")
            assert result is None

    def test_get_recipe_content_sample_no_recipes(self, tmp_path: Path) -> None:
        """Test getting recipe content when no recipes exist."""
        cookbook = tmp_path / "no_recipes"
        cookbook.mkdir()

        result = _get_recipe_content_sample(cookbook)
        assert "No recipes directory found" in result or "No recipe files" in result

    def test_get_recipe_content_sample_with_recipes(self, tmp_path: Path) -> None:
        """Test getting recipe content sample."""
        cookbook = tmp_path / "with_recipes"
        cookbook.mkdir()
        recipes_dir = cookbook / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")

        result = _get_recipe_content_sample(cookbook)
        assert "default.rb" in result or "nginx" in result

    def test_get_metadata_content_no_metadata(self, tmp_path: Path) -> None:
        """Test getting metadata content when none exists."""
        cookbook = tmp_path / "no_metadata"
        cookbook.mkdir()

        result = _get_metadata_content(cookbook)
        assert "No metadata.rb found" in result

    def test_get_metadata_content_with_metadata(self, tmp_path: Path) -> None:
        """Test getting metadata content."""
        cookbook = tmp_path / "with_metadata"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'test'")

        result = _get_metadata_content(cookbook)
        assert "test" in result

    def test_get_ai_cookbook_analysis_no_requests(self, tmp_path: Path) -> None:
        """Test AI cookbook analysis without requests library."""
        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'test'")

        with patch("souschef.assessment.requests", None):
            result = _get_ai_cookbook_analysis(
                cookbook, {}, "anthropic", "key", "model", 0.5, 1000
            )
            assert result is None


class TestMigrationRecommendations:
    """Test migration recommendation generation."""

    def test_generate_migration_recommendations_basic(self) -> None:
        """Test basic migration recommendations."""
        assessments = [{"complexity_score": 50, "metrics": {"custom_resources": 0}}]
        metrics = {"estimated_effort_days": 10.0, "avg_complexity": 50}
        result = _generate_migration_recommendations_from_assessment(
            assessments, metrics, "ansible_awx"
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_create_migration_roadmap_low_complexity(self) -> None:
        """Test migration roadmap creation for low complexity."""
        assessments = [
            {
                "cookbook_name": "simple",
                "complexity_score": 20,
                "estimated_effort_days": 2,
            }
        ]
        result = _create_migration_roadmap(assessments)
        assert isinstance(result, str)
        assert "simple" in result


class TestMiscHelpers:
    """Test miscellaneous helper functions."""

    def test_parse_cookbook_paths_valid(self, tmp_path: Path) -> None:
        """Test parsing valid cookbook paths."""
        cb1 = tmp_path / "cookbook1"
        cb1.mkdir()
        (cb1 / "metadata.rb").write_text("name 'cb1'")

        result = _parse_cookbook_paths(str(cb1))
        assert len(result) == 1

    def test_parse_cookbook_paths_multiple(self, tmp_path: Path) -> None:
        """Test parsing multiple cookbook paths."""
        cb1 = tmp_path / "cookbook1"
        cb1.mkdir()
        (cb1 / "metadata.rb").write_text("name 'cb1'")

        cb2 = tmp_path / "cookbook2"
        cb2.mkdir()
        (cb2 / "metadata.rb").write_text("name 'cb2'")

        result = _parse_cookbook_paths(f"{cb1},{cb2}")
        assert len(result) == 2

    def test_analyise_cookbook_metrics_empty_list(self) -> None:
        """Test analyzing cookbook metrics with empty list."""
        assessments, metrics = _analyse_cookbook_metrics([])
        assert len(assessments) == 0
        assert metrics["total_cookbooks"] == 0

    def test_assess_single_cookbook_basic(self, tmp_path: Path) -> None:
        """Test assessing a single cookbook."""
        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()
        (cookbook / "metadata.rb").write_text("name 'test'")
        recipes_dir = cookbook / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")

        result = _assess_single_cookbook(cookbook)
        assert result["cookbook_name"] == "cookbook"
        assert result["complexity_score"] >= 0
        assert result["estimated_effort_days"] > 0
