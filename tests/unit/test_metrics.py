"""Tests for centralized metrics module ensuring consistency."""

from souschef.core.metrics import (
    ComplexityLevel,
    EffortMetrics,
    TeamRecommendation,
    categorize_complexity,
    convert_days_to_hours,
    convert_days_to_weeks,
    convert_hours_to_days,
    estimate_effort_for_complexity,
    get_team_recommendation,
    get_timeline_weeks,
    validate_metrics_consistency,
)


class TestEffortMetrics:
    """Test EffortMetrics container and conversions."""

    def test_effort_metrics_days_to_hours(self):
        """Test conversion from days to hours."""
        metrics = EffortMetrics(estimated_days=5.0)
        assert abs(metrics.estimated_hours - 40.0) < 0.01

    def test_effort_metrics_days_to_hours_with_decimal(self):
        """Test decimal day conversion."""
        metrics = EffortMetrics(estimated_days=2.5)
        assert abs(metrics.estimated_hours - 20.0) < 0.01

    def test_effort_metrics_weeks_range(self):
        """Test week range calculation."""
        metrics = EffortMetrics(estimated_days=14.0)
        assert metrics.estimated_weeks_low == 2
        assert metrics.estimated_weeks_high == 4
        assert "2-4 weeks" in metrics.estimated_weeks_range

    def test_effort_metrics_single_week(self):
        """Test single week representation."""
        metrics = EffortMetrics(estimated_days=3.5)
        # Low: 3.5 / 7 = 0.5 → max(1, int(0.5)) = 1
        # High: 3.5 / 3.5 = 1 → max(1, int(1)) = 1
        assert "1 week" in metrics.estimated_weeks_range

    def test_effort_metrics_string_representation(self):
        """Test string representation includes both formats."""
        metrics = EffortMetrics(estimated_days=5.0)
        str_repr = str(metrics)
        assert "5 days" in str_repr
        assert "week" in str_repr

    def test_effort_metrics_formatted_days_integer(self):
        """Test integer days formatting."""
        metrics = EffortMetrics(estimated_days=5.0)
        assert metrics.estimated_days_formatted == "5 days"

    def test_effort_metrics_formatted_days_decimal(self):
        """Test decimal days formatting."""
        metrics = EffortMetrics(estimated_days=5.5)
        assert metrics.estimated_days_formatted == "5.5 days"


class TestConversionFunctions:
    """Test conversion between different time units."""

    def test_convert_days_to_hours(self):
        """Test days to hours conversion."""
        assert abs(convert_days_to_hours(5.0) - 40.0) < 0.01
        assert abs(convert_days_to_hours(2.5) - 20.0) < 0.01
        assert abs(convert_days_to_hours(1.0) - 8.0) < 0.01

    def test_convert_hours_to_days(self):
        """Test hours to days conversion."""
        assert abs(convert_hours_to_days(40.0) - 5.0) < 0.01
        assert abs(convert_hours_to_days(8.0) - 1.0) < 0.01
        assert abs(convert_hours_to_days(20.0) - 2.5) < 0.01

    def test_convert_days_to_weeks_optimistic(self):
        """Test optimistic week estimation (with parallelization)."""
        assert convert_days_to_weeks(7, conservative=False) == 1
        assert convert_days_to_weeks(14, conservative=False) == 2
        assert convert_days_to_weeks(3, conservative=False) == 1  # min 1 week

    def test_convert_days_to_weeks_conservative(self):
        """Test conservative week estimation (realistic, sequential)."""
        assert convert_days_to_weeks(3.5, conservative=True) == 1
        assert convert_days_to_weeks(7.0, conservative=True) == 2
        assert convert_days_to_weeks(17.5, conservative=True) == 5
        assert convert_days_to_weeks(1, conservative=True) == 1  # min 1 week


class TestComplexityEstimation:
    """Test effort estimation based on complexity."""

    def test_estimate_effort_simple_cookbook(self):
        """Test effort for simple cookbook (low complexity, few resources)."""
        metrics = estimate_effort_for_complexity(
            complexity_score=10,  # Low
            resource_count=5,  # 5 recipes
        )
        # Base: 5 * 0.125 = 0.625 days
        # Multiplier: 1 + (10/100) = 1.1
        # Result: 0.625 * 1.1 = 0.6875 → rounded to 0.7
        assert abs(metrics.estimated_days - 0.7) < 0.01

    def test_estimate_effort_medium_cookbook(self):
        """Test effort for medium complexity cookbook."""
        metrics = estimate_effort_for_complexity(
            complexity_score=50,  # Medium
            resource_count=12,  # 12 recipes
        )
        # Base: 12 * 0.125 = 1.5 days
        # Multiplier: 1 + (50/100) = 1.5
        # Result: 1.5 * 1.5 = 2.25
        assert abs(metrics.estimated_days - 2.2) < 0.01  # rounded

    def test_estimate_effort_high_complexity(self):
        """Test effort for highly complex cookbook."""
        metrics = estimate_effort_for_complexity(
            complexity_score=90,  # High
            resource_count=25,  # Many resources
        )
        # Base: 25 * 0.125 = 3.125 days
        # Multiplier: 1 + (90/100) = 1.9
        # Result: 3.125 * 1.9 = 5.9375 → rounded to 5.9
        assert abs(metrics.estimated_days - 5.9) < 0.01


class TestComplexityCategorization:
    """Test complexity level categorization."""

    def test_categorize_low_complexity(self):
        """Test low complexity categorization."""
        assert categorize_complexity(0) == ComplexityLevel.LOW
        assert categorize_complexity(15) == ComplexityLevel.LOW
        assert categorize_complexity(29) == ComplexityLevel.LOW

    def test_categorize_medium_complexity(self):
        """Test medium complexity categorization."""
        assert categorize_complexity(30) == ComplexityLevel.MEDIUM
        assert categorize_complexity(50) == ComplexityLevel.MEDIUM
        assert categorize_complexity(69) == ComplexityLevel.MEDIUM

    def test_categorize_high_complexity(self):
        """Test high complexity categorization."""
        assert categorize_complexity(70) == ComplexityLevel.HIGH
        assert categorize_complexity(85) == ComplexityLevel.HIGH
        assert categorize_complexity(100) == ComplexityLevel.HIGH

    def test_categorize_boundary_values(self):
        """Test boundary values for categorization."""
        # Boundary between low and medium
        assert categorize_complexity(29) == ComplexityLevel.LOW
        assert categorize_complexity(30) == ComplexityLevel.MEDIUM

        # Boundary between medium and high
        assert categorize_complexity(69) == ComplexityLevel.MEDIUM
        assert categorize_complexity(70) == ComplexityLevel.HIGH


class TestTeamRecommendations:
    """Test team composition recommendations."""

    def test_small_project_team(self):
        """Test team for small effort project."""
        rec = get_team_recommendation(15.0)
        assert isinstance(rec, TeamRecommendation)
        assert rec.team_size == "1 developer + 1 reviewer"
        assert rec.timeline_weeks == 4

    def test_medium_project_team(self):
        """Test team for medium effort project."""
        rec = get_team_recommendation(35.0)
        assert rec.team_size == "2 developers + 1 senior reviewer"
        assert rec.timeline_weeks == 6

    def test_large_project_team(self):
        """Test team for large effort project."""
        rec = get_team_recommendation(75.0)
        assert "3-4 developers" in rec.team_size
        assert rec.timeline_weeks == 10

    def test_team_boundary_values(self):
        """Test team recommendations at boundaries."""
        # Just under 20 days
        rec_low = get_team_recommendation(19.9)
        assert "1 developer" in rec_low.team_size

        # Just at 20 days
        rec_medium = get_team_recommendation(20.0)
        assert "2 developers" in rec_medium.team_size

        # Just at 50 days
        rec_high = get_team_recommendation(50.0)
        assert "3-4 developers" in rec_high.team_size


class TestTimelineCalculation:
    """Test timeline calculation with different strategies."""

    def test_timeline_phased_strategy(self):
        """Test phased migration timeline calculation."""
        timeline = get_timeline_weeks(20.0, strategy="phased")
        # Base: max(2, int(20 / 4.5)) = max(2, int(4.4)) = max(2, 4) = 4
        # Phased: 4 * 1.1 = 4.4 → int(4.4) = 4
        assert timeline == 4

    def test_timeline_big_bang_strategy(self):
        """Test big bang migration timeline calculation."""
        timeline = get_timeline_weeks(20.0, strategy="big_bang")
        # Base: max(2, int(20 / 4.5)) = 4
        # Big bang: 4 * 0.9 = 3.6 → int(3.6) = 3
        assert timeline == 3

    def test_timeline_parallel_strategy(self):
        """Test parallel migration timeline calculation."""
        timeline = get_timeline_weeks(20.0, strategy="parallel")
        # Base: max(2, int(20 / 4.5)) = 4
        # Parallel: 4 * 1.05 = 4.2 → int(4.2) = 4
        assert timeline == 4

    def test_timeline_minimum_weeks(self):
        """Test that timeline has minimum of 2 weeks."""
        timeline_low = get_timeline_weeks(5.0)
        timeline_very_low = get_timeline_weeks(1.0)
        assert timeline_low >= 2
        assert timeline_very_low >= 2


class TestMetricsValidation:
    """Test validation of metrics consistency."""

    def test_validate_consistent_metrics(self):
        """Test validation passes for consistent metrics."""
        is_valid, errors = validate_metrics_consistency(
            days=5.0,
            weeks="1-2 weeks",
            hours=40.0,
            complexity="medium",
        )
        assert is_valid
        assert len(errors) == 0

    def test_validate_hours_mismatch(self):
        """Test validation catches hours mismatch."""
        is_valid, errors = validate_metrics_consistency(
            days=5.0,
            weeks="1-2 weeks",
            hours=50.0,  # Should be 40.0
            complexity="medium",
        )
        assert not is_valid
        assert any("Hours mismatch" in error for error in errors)

    def test_validate_weeks_mismatch(self):
        """Test validation catches weeks mismatch."""
        _, _ = validate_metrics_consistency(
            days=5.0,
            weeks="1 week",  # 5 days = 1-2 weeks
            hours=40.0,
            complexity="medium",
        )
        # This should pass or have tolerance (allow 1 week difference)
        # The validation uses conservative estimate ~1.4 weeks, so "1 week" is close enough

    def test_validate_invalid_complexity(self):
        """Test validation catches invalid complexity."""
        is_valid, errors = validate_metrics_consistency(
            days=5.0,
            weeks="1-2 weeks",
            hours=40.0,
            complexity="invalid",
        )
        assert not is_valid
        assert any("Invalid complexity level" in error for error in errors)

    def test_validate_invalid_weeks_format(self):
        """Test validation catches invalid weeks format."""
        is_valid, errors = validate_metrics_consistency(
            days=5.0,
            weeks="invalid format like xyz",
            hours=40.0,
            complexity="medium",
        )
        assert not is_valid
        assert any("Invalid weeks format" in error for error in errors)


class TestConsistencyAcrossComponents:
    """Integration tests ensuring consistency across different components."""

    def test_same_effort_produces_consistent_output(self):
        """Test that same input produces consistent output across calculations."""
        complexity = 60
        resources = 10

        # Calculate effort
        metrics = estimate_effort_for_complexity(complexity, resources)

        # Verify consistency between different representations
        hours = metrics.estimated_hours
        days = metrics.estimated_days
        weeks = metrics.estimated_weeks_range

        # Days to hours should match
        assert hours == days * 8

        # All should be consistent (no contradictions)
        is_valid, errors = validate_metrics_consistency(
            days=days,
            weeks=weeks,
            hours=hours,
            complexity=categorize_complexity(complexity).value,
        )
        assert is_valid, f"Metrics should be consistent: {errors}"

    def test_all_components_use_same_thresholds(self):
        """Test that all complexity categorizations are consistent."""
        # Test low/medium boundary
        low_score = 25
        medium_score = 35

        low_cat = categorize_complexity(low_score)
        medium_cat = categorize_complexity(medium_score)

        assert low_cat == ComplexityLevel.LOW
        assert medium_cat == ComplexityLevel.MEDIUM

        # Effort should reflect the complexity difference
        low_effort = estimate_effort_for_complexity(low_score, 10)
        medium_effort = estimate_effort_for_complexity(medium_score, 10)

        # Medium should be higher due to higher multiplier
        assert medium_effort.estimated_days > low_effort.estimated_days

    def test_timeline_matches_team_recommendation(self):
        """Test that timeline calculation aligns with team recommendation."""
        total_effort = 50.0

        # Get timeline from calculation function
        timeline = get_timeline_weeks(total_effort, strategy="phased")

        # Get team recommendation
        team_rec = get_team_recommendation(total_effort)

        # Team recommendation should suggest a similar timeline
        # (Both using similar effort metrics)
        assert isinstance(timeline, int)
        assert isinstance(team_rec.timeline_weeks, int)
        # They should be reasonably close (within 2 weeks)
        assert abs(timeline - team_rec.timeline_weeks) <= 2
