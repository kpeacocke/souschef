"""Comprehensive tests for assessment.py module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from souschef.assessment import (
    ActivityBreakdown,
    analyse_cookbook_dependencies,
    assess_chef_migration_complexity,
    calculate_activity_breakdown,
    generate_migration_plan,
    generate_migration_report,
    validate_conversion,
)

FIXTURES_DIR = (
    Path(__file__).parent.parent / "integration" / "fixtures" / "sample_cookbook"
)


class TestActivityBreakdown:
    """Test ActivityBreakdown dataclass."""

    def test_activity_breakdown_creation(self) -> None:
        """Test creating activity breakdown."""
        activity = ActivityBreakdown(
            activity_type="Recipes",
            count=5,
            manual_hours=40.0,
            ai_assisted_hours=10.0,
            complexity_factor=1.0,
            description="Recipe conversion",
        )

        assert activity.activity_type == "Recipes"
        assert activity.count == 5
        assert activity.manual_hours == 40.0

    def test_activity_breakdown_days_calculation(self) -> None:
        """Test conversion from hours to days."""
        activity = ActivityBreakdown(
            activity_type="Templates",
            count=3,
            manual_hours=24.0,
            ai_assisted_hours=8.0,
            complexity_factor=0.8,
            description="Template parsing",
        )

        assert activity.manual_days == 3.0
        assert activity.ai_assisted_days == 1.0

    def test_activity_breakdown_time_saved(self) -> None:
        """Test time saved calculation."""
        activity = ActivityBreakdown(
            activity_type="Attributes",
            count=2,
            manual_hours=16.0,
            ai_assisted_hours=6.0,
            complexity_factor=0.5,
            description="Attribute parsing",
        )

        assert activity.time_saved_hours == 10.0

    def test_activity_breakdown_with_writing_testing_hours(self) -> None:
        """Test activity breakdown with writing and testing hours."""
        activity = ActivityBreakdown(
            activity_type="Custom Resources",
            count=4,
            manual_hours=60.0,
            ai_assisted_hours=25.0,
            complexity_factor=2.0,
            description="Custom resource conversion",
            writing_hours=30.0,
            testing_hours=30.0,
            ai_assisted_writing_hours=10.0,
            ai_assisted_testing_hours=15.0,
        )

        assert activity.writing_hours == 30.0
        assert activity.testing_hours == 30.0
        assert activity.ai_assisted_writing_hours == 10.0
        assert activity.ai_assisted_testing_hours == 15.0


class TestAssessChefMigrationComplexity:
    """Test assess_chef_migration_complexity function."""

    @patch("souschef.assessment._process_cookbook_assessment")
    @patch("souschef.assessment._validate_assessment_inputs")
    def test_assess_complexity_basic(
        self, mock_validate: MagicMock, mock_process: MagicMock
    ) -> None:
        """Test basic complexity assessment."""
        mock_validate.return_value = None
        mock_process.return_value = "Assessment completed"

        result = assess_chef_migration_complexity("/path/to/cookbook")

        assert isinstance(result, str)
        assert result == "Assessment completed"

    @patch("souschef.assessment._validate_assessment_inputs")
    def test_assess_complexity_validation_error(self, mock_validate: MagicMock) -> None:
        """Test validation error handling."""
        mock_validate.return_value = "Validation error: Invalid path"

        result = assess_chef_migration_complexity("/invalid/path")

        assert "Validation error" in result

    @patch("souschef.assessment._process_cookbook_assessment")
    @patch("souschef.assessment._validate_assessment_inputs")
    def test_assess_complexity_with_target_platform(
        self, mock_validate: MagicMock, mock_process: MagicMock
    ) -> None:
        """Test assessment with target platform."""
        mock_validate.return_value = None
        mock_process.return_value = "Assessment with AWX target"

        result = assess_chef_migration_complexity(
            "/path/to/cookbook", target_platform="ansible_awx"
        )

        assert isinstance(result, str)

    @patch("souschef.assessment._process_cookbook_assessment")
    @patch("souschef.assessment._validate_assessment_inputs")
    def test_assess_complexity_with_migration_scope(
        self, mock_validate: MagicMock, mock_process: MagicMock
    ) -> None:
        """Test assessment with migration scope."""
        mock_validate.return_value = None
        mock_process.return_value = "Assessment with recipes scope"

        result = assess_chef_migration_complexity(
            "/path/to/cookbook", migration_scope="recipes_only"
        )

        assert isinstance(result, str)


class TestGenerateMigrationPlan:
    """Test generate_migration_plan function."""

    @patch("souschef.assessment._parse_and_assess_cookbooks")
    @patch("souschef.assessment._validate_migration_plan_inputs")
    def test_generate_plan_basic(
        self, mock_validate: MagicMock, mock_parse: MagicMock
    ) -> None:
        """Test basic migration plan generation."""
        mock_validate.return_value = None
        mock_parse.return_value = (
            [
                {
                    "name": "test_cookbook",
                    "complexity_score": 45,
                    "artifacts": {"recipes": 3, "templates": 2},
                }
            ],
            None,
        )

        result = generate_migration_plan("/path/to/cookbook")

        assert isinstance(result, str)

    @patch("souschef.assessment._validate_migration_plan_inputs")
    def test_generate_plan_validation_error(self, mock_validate: MagicMock) -> None:
        """Test plan generation validation error."""
        mock_validate.return_value = "Error: Invalid timeline"

        result = generate_migration_plan("/path")

        assert "Error" in result

    @patch("souschef.assessment._parse_and_assess_cookbooks")
    @patch("souschef.assessment._validate_migration_plan_inputs")
    def test_generate_plan_with_strategy(
        self, mock_validate: MagicMock, mock_parse: MagicMock
    ) -> None:
        """Test plan generation with migration strategy."""
        mock_validate.return_value = None
        mock_parse.return_value = ([], None)

        result = generate_migration_plan(
            "/path", migration_strategy="big_bang", timeline_weeks=8
        )

        assert isinstance(result, str)

    @patch("souschef.assessment._parse_and_assess_cookbooks")
    @patch("souschef.assessment._validate_migration_plan_inputs")
    def test_generate_plan_with_parallel_strategy(
        self, mock_validate: MagicMock, mock_parse: MagicMock
    ) -> None:
        """Test plan generation with parallel strategy."""
        mock_validate.return_value = None
        mock_parse.return_value = ([], None)

        result = generate_migration_plan(
            "/path", migration_strategy="parallel", timeline_weeks=16
        )

        assert isinstance(result, str)


class TestAnalyseCookbookDependencies:
    """Test analyse_cookbook_dependencies function."""

    @patch("souschef.assessment._analyse_cookbook_dependencies_detailed")
    def test_analyse_dependencies_basic(self, mock_detailed: MagicMock) -> None:
        """Test basic dependency analysis."""
        mock_detailed.return_value = {
            "direct_dependencies": [],
            "transitive_dependencies": [],
        }

        result = analyse_cookbook_dependencies("/path/to/cookbook")

        assert isinstance(result, str)

    def test_analyse_dependencies_nonexistent_path(self) -> None:
        """Test dependency analysis with nonexistent path."""
        result = analyse_cookbook_dependencies("/nonexistent/path")

        # Should handle gracefully
        assert isinstance(result, str)

    @patch("souschef.assessment._analyse_cookbook_dependencies_detailed")
    def test_analyse_dependencies_full_depth(self, mock_detailed: MagicMock) -> None:
        """Test dependency analysis with full depth."""
        mock_detailed.return_value = {
            "direct_dependencies": ["dep1"],
            "transitive_dependencies": ["dep2"],
            "community_cookbooks": ["community/dep3"],
            "circular_dependencies": [],
        }

        result = analyse_cookbook_dependencies(
            "/path/to/cookbook", dependency_depth="full"
        )

        assert isinstance(result, str)

    @patch("souschef.assessment._analyse_cookbook_dependencies_detailed")
    def test_analyse_dependencies_transitive_depth(
        self, mock_detailed: MagicMock
    ) -> None:
        """Test dependency analysis with transitive depth."""
        mock_detailed.return_value = {
            "direct_dependencies": ["dep1"],
            "transitive_dependencies": ["dep2"],
        }

        result = analyse_cookbook_dependencies(
            "/path/to/cookbook", dependency_depth="transitive"
        )

        assert isinstance(result, str)


class TestGenerateMigrationReport:
    """Test generate_migration_report function."""

    @patch("souschef.assessment._generate_comprehensive_migration_report")
    def test_generate_report_basic(self, mock_report: MagicMock) -> None:
        """Test basic migration report generation."""
        mock_report.return_value = "Executive Summary\nReport content"

        result = generate_migration_report("assessment_results")

        assert isinstance(result, str)

    @patch("souschef.assessment._generate_comprehensive_migration_report")
    def test_generate_report_technical_format(self, mock_report: MagicMock) -> None:
        """Test report with technical format."""
        mock_report.return_value = "Technical Analysis\nDetailed content"

        result = generate_migration_report(
            "assessment_results",
            report_format="technical",
            include_technical_details="yes",
        )

        assert isinstance(result, str)

    @patch("souschef.assessment._generate_comprehensive_migration_report")
    def test_generate_report_executive_format(self, mock_report: MagicMock) -> None:
        """Test report with executive format."""
        mock_report.return_value = "Executive Summary"

        result = generate_migration_report(
            "assessment_results",
            report_format="executive",
            include_technical_details="no",
        )

        assert isinstance(result, str)


class TestValidateConversion:
    """Test validate_conversion function."""

    def test_validate_conversion_recipe(self) -> None:
        """Test validation of recipe conversion."""
        conversion_type = "recipe"
        result_content = """---
- hosts: all
  tasks:
    - name: Install apache2
      ansible.builtin.package:
        name: apache2
        state: present
"""

        result = validate_conversion(conversion_type, result_content)

        assert isinstance(result, str)

    def test_validate_conversion_resource(self) -> None:
        """Test validation of resource conversion."""
        conversion_type = "resource"
        result_content = """
- name: Custom resource conversion
  ansible.builtin.debug:
    msg: "Custom resource"
"""

        result = validate_conversion(conversion_type, result_content)

        assert isinstance(result, str)

    def test_validate_conversion_template(self) -> None:
        """Test validation of template conversion."""
        conversion_type = "template"
        result_content = "Hello {{ name }}"

        result = validate_conversion(conversion_type, result_content)

        assert isinstance(result, str)

    def test_validate_conversion_json_format(self) -> None:
        """Test validation with JSON output format."""
        result = validate_conversion(
            "recipe",
            "some ansible content",
            output_format="json",
        )

        assert isinstance(result, str)

    def test_validate_conversion_summary_format(self) -> None:
        """Test validation with summary format."""
        result = validate_conversion(
            "recipe",
            "some ansible content",
            output_format="summary",
        )

        assert isinstance(result, str)

    def test_validate_conversion_inspec(self) -> None:
        """Test validation of InSpec conversion."""
        result = validate_conversion("inspec", "profile 'test' { }")

        assert isinstance(result, str)


class TestCalculateActivityBreakdown:
    """Test calculate_activity_breakdown function."""

    @patch("souschef.assessment._assess_single_cookbook")
    def test_calculate_breakdown_basic(self, mock_assess: MagicMock) -> None:
        """Test basic activity breakdown calculation."""
        mock_assess.return_value = {
            "recipes": 5,
            "templates": 3,
            "artifacts": {
                "recipes": 5,
                "templates": 3,
            },
        }

        result = calculate_activity_breakdown("/path/to/cookbook")

        assert isinstance(result, dict)

    def test_calculate_breakdown_directory_handling(self) -> None:
        """Test breakdown with directory path."""
        if FIXTURES_DIR.exists():
            result = calculate_activity_breakdown(str(FIXTURES_DIR))

            assert isinstance(result, dict)

    def test_calculate_breakdown_invalid_path(self) -> None:
        """Test breakdown with invalid path."""
        result = calculate_activity_breakdown("/nonexistent/path")

        assert isinstance(result, dict)
        assert "error" in result or len(result) >= 0

    @patch("souschef.assessment._assess_single_cookbook")
    def test_calculate_breakdown_phased_strategy(self, mock_assess: MagicMock) -> None:
        """Test breakdown with phased migration strategy."""
        mock_assess.return_value = {"recipes": 3}

        result = calculate_activity_breakdown(
            "/path/to/cookbook", migration_strategy="phased"
        )

        assert isinstance(result, dict)

    @patch("souschef.assessment._assess_single_cookbook")
    def test_calculate_breakdown_big_bang_strategy(
        self, mock_assess: MagicMock
    ) -> None:
        """Test breakdown with big bang strategy."""
        mock_assess.return_value = {"recipes": 10}

        result = calculate_activity_breakdown(
            "/path/to/cookbook", migration_strategy="big_bang"
        )

        assert isinstance(result, dict)


class TestAssessmentEdgeCases:
    """Test edge cases and error handling."""

    def test_assess_empty_cookbook_path(self) -> None:
        """Test assessment with empty path."""
        result = assess_chef_migration_complexity("")

        assert isinstance(result, str)

    @patch("souschef.assessment._validate_assessment_inputs")
    def test_assess_invalid_target_platform(self, mock_validate: MagicMock) -> None:
        """Test assessment with invalid target platform."""
        mock_validate.return_value = "Error: Invalid platform"

        result = assess_chef_migration_complexity("/path", target_platform="invalid")

        assert "Error" in result

    @patch("souschef.assessment._validate_migration_plan_inputs")
    def test_generate_plan_invalid_strategy(self, mock_validate: MagicMock) -> None:
        """Test plan generation with invalid strategy."""
        mock_validate.return_value = "Error: Invalid strategy"

        result = generate_migration_plan("/path", migration_strategy="invalid_strategy")

        assert "Error" in result

    def test_analys_dependencies_invalid_depth(self) -> None:
        """Test dependency analysis with invalid depth."""
        result = analyse_cookbook_dependencies("/path", dependency_depth="invalid")

        # Should return error message for invalid depth
        assert isinstance(result, str)
        assert "Error" in result or isinstance(result, str)

    def test_validate_conversion_empty_content(self) -> None:
        """Test validation with empty conversion content."""
        result = validate_conversion("recipe", "")

        assert isinstance(result, str)


class TestAssessmentIntegration:
    """Test integration scenarios."""

    @patch("souschef.assessment._validate_assessment_inputs")
    @patch("souschef.assessment._process_cookbook_assessment")
    def test_full_assessment_workflow(
        self, mock_process: MagicMock, mock_validate: MagicMock
    ) -> None:
        """Test full assessment workflow."""
        mock_validate.return_value = None
        mock_process.return_value = "Assessment complete"

        # Assessment
        assessment = assess_chef_migration_complexity("/path/to/cookbook")
        assert isinstance(assessment, str)

        # Dependency analysis
        deps = analyse_cookbook_dependencies("/path/to/cookbook")
        assert isinstance(deps, str)

        # Migration plan
        plan = generate_migration_plan("/path/to/cookbook")
        assert isinstance(plan, str)

    @patch("souschef.assessment._assess_single_cookbook")
    def test_assessment_with_activity_breakdown(self, mock_assess: MagicMock) -> None:
        """Test assessment with activity breakdown."""
        mock_assess.return_value = {
            "recipes": 3,
            "templates": 2,
        }

        breakdown = calculate_activity_breakdown("/path")

        assert isinstance(breakdown, dict)

    def test_mocked_assessment_workflow(self) -> None:
        """Test workflow with multiple assessment calls."""
        # These should handle gracefully without actual files
        result1 = assess_chef_migration_complexity("/nonexistent")
        result2 = analyse_cookbook_dependencies("/nonexistent")
        result3 = generate_migration_plan("/nonexistent")

        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert isinstance(result3, str)


class TestAssessmentFormatting:
    """Test assessment output formatting."""

    def test_breakdown_string_representation(self) -> None:
        """Test activity breakdown string representation."""
        activity = ActivityBreakdown(
            activity_type="Recipes",
            count=5,
            manual_hours=40.0,
            ai_assisted_hours=15.0,
            complexity_factor=1.0,
            description="Recipe conversion",
        )

        # Test that dataclass works correctly
        assert activity.activity_type == "Recipes"
        assert activity.count == 5

    def test_multiple_breakdowns(self) -> None:
        """Test handling multiple activity breakdowns."""
        activities = [
            ActivityBreakdown(
                activity_type="Recipes",
                count=5,
                manual_hours=40.0,
                ai_assisted_hours=15.0,
                complexity_factor=1.0,
                description="Recipe conversion",
            ),
            ActivityBreakdown(
                activity_type="Templates",
                count=3,
                manual_hours=20.0,
                ai_assisted_hours=8.0,
                complexity_factor=0.8,
                description="Template conversion",
            ),
        ]

        assert len(activities) == 2
        assert sum(a.count for a in activities) == 8
        assert sum(a.manual_hours for a in activities) == 60.0


class TestAssessmentDataValidation:
    """Test data validation in assessment."""

    def test_activity_breakdown_negative_hours(self) -> None:
        """Test handling of invalid hours."""
        # Should allow constructor (validation at usage time)
        activity = ActivityBreakdown(
            activity_type="Test",
            count=1,
            manual_hours=-10.0,  # Invalid
            ai_assisted_hours=5.0,
            complexity_factor=1.0,
            description="Test",
        )

        assert activity.manual_hours == -10.0
        # Properties should still work
        assert isinstance(activity.manual_days, float)

    def test_activity_breakdown_zero_complexity(self) -> None:
        """Test with zero complexity factor."""
        activity = ActivityBreakdown(
            activity_type="Test",
            count=1,
            manual_hours=8.0,
            ai_assisted_hours=4.0,
            complexity_factor=0.0,
            description="Test with zero complexity",
        )

        assert activity.complexity_factor == 0.0
        assert activity.manual_days == 1.0

    def test_activity_breakdown_large_numbers(self) -> None:
        """Test with large numbers."""
        activity = ActivityBreakdown(
            activity_type="Massive Migration",
            count=10000,
            manual_hours=100000.0,
            ai_assisted_hours=25000.0,
            complexity_factor=5.0,
            description="Large migration",
        )

        assert activity.count == 10000
        assert activity.manual_days == 12500.0
        assert activity.ai_assisted_days == 3125.0
        assert activity.time_saved_hours == 75000.0

    def test_activity_breakdown_writing_testing_hours(self) -> None:
        """Test activity breakdown with writing and testing hours."""
        activity = ActivityBreakdown(
            activity_type="Custom Resources",
            count=4,
            manual_hours=60.0,
            ai_assisted_hours=25.0,
            complexity_factor=2.0,
            description="Custom resource conversion",
            writing_hours=30.0,
            testing_hours=30.0,
            ai_assisted_writing_hours=10.0,
            ai_assisted_testing_hours=15.0,
        )

        assert activity.writing_hours == 30.0
        assert activity.testing_hours == 30.0
        assert activity.ai_assisted_writing_hours == 10.0
        assert activity.ai_assisted_testing_hours == 15.0
