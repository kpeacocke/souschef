"""Tests for activity breakdown functionality in assessment module."""

import pytest

from souschef.assessment import ActivityBreakdown, _calculate_activity_breakdown


class TestActivityBreakdown:
    """Test ActivityBreakdown dataclass."""

    def test_activity_breakdown_initialization(self):
        """Test ActivityBreakdown initialization."""
        activity = ActivityBreakdown(
            activity_type="Recipes",
            count=10,
            manual_hours=30.0,
            ai_assisted_hours=10.5,
            complexity_factor=1.2,
            description="Convert Chef recipes to Ansible playbooks",
        )

        assert activity.activity_type == "Recipes"
        assert activity.count == 10
        assert activity.manual_hours == pytest.approx(30.0)
        assert activity.ai_assisted_hours == pytest.approx(10.5)
        assert activity.complexity_factor == pytest.approx(1.2)

    def test_manual_days_conversion(self):
        """Test conversion from manual hours to days."""
        activity = ActivityBreakdown(
            activity_type="Templates",
            count=5,
            manual_hours=16.0,  # 2 days
            ai_assisted_hours=6.4,
            complexity_factor=1.0,
            description="Template conversion",
        )

        assert activity.manual_days == pytest.approx(2.0)

    def test_ai_assisted_days_conversion(self):
        """Test conversion from AI-assisted hours to days."""
        activity = ActivityBreakdown(
            activity_type="Attributes",
            count=8,
            manual_hours=24.0,
            ai_assisted_hours=7.2,  # 0.9 days
            complexity_factor=1.0,
            description="Attribute extraction",
        )

        assert activity.ai_assisted_days == pytest.approx(0.9)

    def test_time_saved_calculation(self):
        """Test time saved calculation."""
        activity = ActivityBreakdown(
            activity_type="Custom Resources",
            count=3,
            manual_hours=15.0,
            ai_assisted_hours=8.25,
            complexity_factor=1.5,
            description="Custom resource conversion",
        )

        # time_saved_hours is rounded to 1 decimal: 15.0 - 8.25 = 6.75, rounded =6.8
        assert activity.time_saved_hours == pytest.approx(6.8)  # Rounded result

    def test_efficiency_gain_percent(self):
        """Test efficiency gain percentage calculation."""
        activity = ActivityBreakdown(
            activity_type="Libraries",
            count=2,
            manual_hours=8.0,
            ai_assisted_hours=4.8,
            complexity_factor=1.0,
            description="Library porting",
        )

        # (8.0 - 4.8) / 8.0 * 100 = 40%
        assert activity.efficiency_gain_percent == 40

    def test_efficiency_gain_zero_manual_hours(self):
        """Test efficiency gain with zero manual hours."""
        activity = ActivityBreakdown(
            activity_type="Files",
            count=0,
            manual_hours=0.0,
            ai_assisted_hours=0.0,
            complexity_factor=1.0,
            description="Static files",
        )

        assert activity.efficiency_gain_percent == 0

    def test_string_representation(self):
        """Test string representation of activity."""
        activity = ActivityBreakdown(
            activity_type="Handlers",
            count=5,
            manual_hours=5.0,
            ai_assisted_hours=1.25,
            complexity_factor=1.0,
            description="Handler conversion",
        )

        result = str(activity)
        assert "Handlers" in result
        assert "5 items" in result
        assert "5.0h manual" in result
        assert "1.2h with AI" in result  # Rounded to 1 decimal
        assert "3.8h" in result  # time saved


class TestCalculateActivityBreakdown:
    """Test _calculate_activity_breakdown function."""

    def test_empty_metrics(self):
        """Test with empty metrics."""
        metrics = {
            "recipe_count": 0,
            "template_count": 0,
            "attributes_count": 0,
            "custom_resources": 0,
            "resource_count": 0,
            "libraries_count": 0,
            "file_count": 0,
            "definition_count": 0,
        }
        complexity_score = 50

        activities = _calculate_activity_breakdown(metrics, complexity_score)

        # Should return empty list when no items
        assert len(activities) == 0

    def test_recipe_only_breakdown(self):
        """Test breakdown with only recipes."""
        metrics = {
            "recipe_count": 10,
            "template_count": 0,
            "attributes_count": 0,
            "custom_resources": 0,
            "resource_count": 0,
            "libraries_count": 0,
            "file_count": 0,
            "definition_count": 0,
        }
        complexity_score = 30  # Low complexity

        activities = _calculate_activity_breakdown(metrics, complexity_score)

        # Should have 2 activities: Recipes and Handlers (estimated from resources)
        # With 0 resources, no handlers, so just recipes
        assert len(activities) == 1
        assert activities[0].activity_type == "Recipes"
        assert activities[0].count == 10

        # Base rate: 3h/recipe * 10 recipes * complexity_multiplier
        # Complexity multiplier: 1.0 + (30/200) = 1.15
        expected_manual = 10 * 3.0 * 1.15
        assert activities[0].manual_hours == pytest.approx(expected_manual, rel=0.01)

    def test_complete_cookbook_breakdown(self):
        """Test breakdown with all component types."""
        metrics = {
            "recipe_count": 5,
            "template_count": 8,
            "attributes_count": 3,
            "custom_resources": 2,
            "resource_count": 20,  # Will generate 2 handlers (20//10=2)
            "libraries_count": 1,
            "file_count": 10,
            "definition_count": 2,
        }
        complexity_score = 50  # Medium complexity

        activities = _calculate_activity_breakdown(metrics, complexity_score)

        # Should have 8 activity types
        assert len(activities) == 8

        activity_types = {a.activity_type for a in activities}
        expected_types = {
            "Recipes",
            "Templates",
            "Attributes",
            "Custom Resources",
            "Libraries",
            "Handlers",
            "Files",
            "Definitions",
        }
        assert activity_types == expected_types

    def test_complexity_multiplier_effect(self):
        """Test that complexity score affects effort estimates."""
        metrics = {
            "recipe_count": 10,
            "template_count": 0,
            "attributes_count": 0,
            "custom_resources": 0,
            "resource_count": 0,
            "libraries_count": 0,
            "file_count": 0,
            "definition_count": 0,
        }

        # Low complexity
        low_activities = _calculate_activity_breakdown(metrics, 20)
        low_effort = low_activities[0].manual_hours

        # High complexity
        high_activities = _calculate_activity_breakdown(metrics, 80)
        high_effort = high_activities[0].manual_hours

        # High complexity should require more effort
        assert high_effort > low_effort

    def test_ai_efficiency_by_activity_type(self):
        """Test that different activity types have different AI efficiency."""
        metrics_recipes = {
            "recipe_count": 10,
            "template_count": 0,
            "attributes_count": 0,
            "custom_resources": 0,
            "resource_count": 0,
            "libraries_count": 0,
            "file_count": 0,
            "definition_count": 0,
        }

        metrics_files = {
            "recipe_count": 0,
            "template_count": 0,
            "attributes_count": 0,
            "custom_resources": 0,
            "resource_count": 0,
            "libraries_count": 0,
            "file_count": 10,
            "definition_count": 0,
        }

        complexity_score = 50

        recipe_activities = _calculate_activity_breakdown(
            metrics_recipes, complexity_score
        )
        file_activities = _calculate_activity_breakdown(metrics_files, complexity_score)

        # Recipes: AI handles 65%, so AI effort is 35% of manual
        recipe_efficiency = (
            recipe_activities[0].ai_assisted_hours / recipe_activities[0].manual_hours
        )

        # Files: AI handles 80%, so AI effort is 20% of manual
        file_efficiency = (
            file_activities[0].ai_assisted_hours / file_activities[0].manual_hours
        )

        # Files should have better AI efficiency (lower ratio)
        assert file_efficiency < recipe_efficiency

    def test_custom_resources_complexity(self):
        """Test that custom resources are treated as more complex."""
        metrics = {
            "recipe_count": 0,
            "template_count": 0,
            "attributes_count": 0,
            "custom_resources": 5,
            "resource_count": 0,
            "libraries_count": 0,
            "file_count": 0,
            "definition_count": 0,
        }
        complexity_score = 50

        activities = _calculate_activity_breakdown(metrics, complexity_score)

        # Custom resources should have high base rate (5h per item)
        custom_resource_activity = activities[0]
        assert custom_resource_activity.activity_type == "Custom Resources"

        # With complexity multiplier 1.25 (50/200 + 1.0)
        expected_manual = 5 * 5.0 * 1.25
        assert custom_resource_activity.manual_hours == pytest.approx(
            expected_manual, rel=0.01
        )

    def test_handlers_estimation_from_resources(self):
        """Test that handlers are estimated from resource count."""
        metrics = {
            "recipe_count": 0,
            "template_count": 0,
            "attributes_count": 0,
            "custom_resources": 0,
            "resource_count": 100,  # Should generate 10 handlers (100/10)
            "libraries_count": 0,
            "file_count": 0,
            "definition_count": 0,
        }
        complexity_score = 50

        activities = _calculate_activity_breakdown(metrics, complexity_score)

        handler_activity = next(
            (a for a in activities if a.activity_type == "Handlers"), None
        )
        assert handler_activity is not None
        assert handler_activity.count == 10  # 100 resource_count // 10

    def test_all_counts_set_correctly(self):
        """Test that counts match input metrics."""
        metrics = {
            "recipe_count": 7,
            "template_count": 4,
            "attributes_count": 5,
            "custom_resources": 3,
            "resource_count": 50,  # For handler estimation (50//10=5)
            "libraries_count": 2,
            "file_count": 15,
            "definition_count": 1,
        }
        complexity_score = 50

        activities = _calculate_activity_breakdown(metrics, complexity_score)

        # Create lookup dictionary
        activity_dict = {a.activity_type: a for a in activities}

        assert activity_dict["Recipes"].count == 7
        assert activity_dict["Templates"].count == 4
        assert activity_dict["Attributes"].count == 5
        assert activity_dict["Custom Resources"].count == 3
        assert activity_dict["Libraries"].count == 2
        assert activity_dict["Handlers"].count == 5  # 50 resource_count //10
        assert activity_dict["Files"].count == 15
        assert activity_dict["Definitions"].count == 1
        assert activity_dict["Definitions"].count == 1
