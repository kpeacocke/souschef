"""Tests for the profiling module."""

from pathlib import Path

import pytest

from souschef.profiling import (
    PerformanceReport,
    ProfileResult,
    compare_performance,
    detailed_profile_function,
    generate_cookbook_performance_report,
    profile_function,
    profile_operation,
)
from souschef.server import parse_recipe

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestProfileOperation:
    """Tests for profile_operation context manager."""

    def test_profile_operation_basic(self) -> None:
        """Test basic profiling with context manager."""
        with profile_operation("test_operation") as result:
            # Simulate some work
            _ = [i**2 for i in range(1000)]

        assert result.operation_name == "test_operation"
        assert result.execution_time > 0
        assert result.peak_memory > 0

    def test_profile_operation_with_context(self) -> None:
        """Test profiling with additional context."""
        context = {"file": "test.rb", "size": 1024}

        with profile_operation("parse_test", context=context) as result:
            _ = [i**2 for i in range(100)]

        assert result.context == context
        assert result.operation_name == "parse_test"


class TestProfileFunction:
    """Tests for profile_function."""

    def test_profile_function_basic(self) -> None:
        """Test profiling a simple function."""
        recipe_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"

        result, profile = profile_function(parse_recipe, str(recipe_path))

        assert "Resource" in result  # Check function executed correctly
        assert profile.execution_time > 0
        assert profile.peak_memory > 0
        assert profile.operation_name == "parse_recipe"

    def test_profile_function_custom_name(self) -> None:
        """Test profiling with custom operation name."""
        recipe_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"

        result, profile = profile_function(
            parse_recipe, str(recipe_path), operation_name="custom_parse"
        )

        assert profile.operation_name == "custom_parse"


class TestDetailedProfileFunction:
    """Tests for detailed_profile_function."""

    def test_detailed_profile_includes_stats(self) -> None:
        """Test that detailed profiling includes function statistics."""
        recipe_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"

        result, profile = detailed_profile_function(parse_recipe, str(recipe_path))

        assert "Resource" in result
        assert profile.execution_time > 0
        assert "total_calls" in profile.function_stats
        assert "primitive_calls" in profile.function_stats
        assert "top_functions" in profile.function_stats
        assert profile.function_stats["total_calls"] > 0

    def test_detailed_profile_custom_top_n(self) -> None:
        """Test detailed profiling with custom top_n parameter."""
        recipe_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"

        result, profile = detailed_profile_function(
            parse_recipe, str(recipe_path), top_n=10
        )

        assert profile.function_stats["top_functions"]


class TestProfileResult:
    """Tests for ProfileResult dataclass."""

    def test_profile_result_str_format(self) -> None:
        """Test ProfileResult string formatting."""
        result = ProfileResult(
            operation_name="test_op",
            execution_time=1.234,
            peak_memory=1024 * 1024 * 50,  # 50MB
            context={"file": "test.rb"},
        )

        result_str = str(result)

        assert "test_op" in result_str
        assert "1.234s" in result_str
        assert "50.00MB" in result_str
        assert "test.rb" in result_str


class TestPerformanceReport:
    """Tests for PerformanceReport dataclass."""

    def test_performance_report_creation(self) -> None:
        """Test creating a performance report."""
        report = PerformanceReport(
            cookbook_name="test_cookbook",
            total_time=5.0,
            total_memory=100 * 1024 * 1024,
        )

        assert report.cookbook_name == "test_cookbook"
        assert report.total_time == 5.0
        assert len(report.operation_results) == 0
        assert len(report.recommendations) == 0

    def test_add_result(self) -> None:
        """Test adding results to report."""
        report = PerformanceReport(
            cookbook_name="test", total_time=1.0, total_memory=1024
        )

        result = ProfileResult(
            operation_name="parse_recipe", execution_time=0.5, peak_memory=512
        )

        report.add_result(result)

        assert len(report.operation_results) == 1
        assert report.operation_results[0] == result

    def test_add_recommendation(self) -> None:
        """Test adding recommendations to report."""
        report = PerformanceReport(
            cookbook_name="test", total_time=1.0, total_memory=1024
        )

        report.add_recommendation("Use caching for better performance")

        assert len(report.recommendations) == 1
        assert "caching" in report.recommendations[0]

    def test_report_str_format(self) -> None:
        """Test PerformanceReport string formatting."""
        report = PerformanceReport(
            cookbook_name="test_cookbook", total_time=2.5, total_memory=50 * 1024 * 1024
        )

        result = ProfileResult(
            operation_name="parse_recipes",
            execution_time=1.0,
            peak_memory=20 * 1024 * 1024,
        )
        report.add_result(result)
        report.add_recommendation("Consider parallel processing")

        report_str = str(report)

        assert "test_cookbook" in report_str
        assert "2.500s" in report_str
        assert "parse_recipes" in report_str
        assert "parallel processing" in report_str


class TestGenerateCookbookPerformanceReport:
    """Tests for generate_cookbook_performance_report."""

    def test_generate_report_for_cookbook(self) -> None:
        """Test generating performance report for a cookbook."""
        cookbook_path = FIXTURES_DIR / "sample_cookbook"

        report = generate_cookbook_performance_report(str(cookbook_path))

        assert report.cookbook_name == "sample_cookbook"
        assert report.total_time > 0
        assert report.total_memory >= 0
        assert len(report.operation_results) > 0
        assert len(report.recommendations) > 0

    def test_report_includes_cookbook_structure(self) -> None:
        """Test that report includes cookbook structure analysis."""
        cookbook_path = FIXTURES_DIR / "sample_cookbook"

        report = generate_cookbook_performance_report(str(cookbook_path))

        # Check that cookbook structure was profiled
        operation_names = [r.operation_name for r in report.operation_results]
        assert any("cookbook_structure" in name for name in operation_names)

    def test_report_includes_metadata_if_exists(self) -> None:
        """Test that report includes metadata parsing if file exists."""
        cookbook_path = FIXTURES_DIR / "sample_cookbook"

        report = generate_cookbook_performance_report(str(cookbook_path))

        operation_names = [r.operation_name for r in report.operation_results]
        assert any("metadata" in name for name in operation_names)

    def test_report_with_recipes(self) -> None:
        """Test report includes recipe parsing stats."""
        cookbook_path = FIXTURES_DIR / "sample_cookbook"

        report = generate_cookbook_performance_report(str(cookbook_path))

        operation_names = [r.operation_name for r in report.operation_results]
        recipe_ops = [op for op in operation_names if "recipe" in op]
        assert len(recipe_ops) > 0

    def test_invalid_cookbook_path(self) -> None:
        """Test error handling for invalid cookbook path."""
        from souschef.core.errors import SousChefError

        with pytest.raises(SousChefError):
            generate_cookbook_performance_report("/nonexistent/path")

    def test_report_recommendations_generated(self) -> None:
        """Test that recommendations are generated based on results."""
        cookbook_path = FIXTURES_DIR / "sample_cookbook"

        report = generate_cookbook_performance_report(str(cookbook_path))

        # Should have at least general recommendations
        assert len(report.recommendations) > 0
        # Should mention caching
        has_cache_rec = any("cache" in rec.lower() for rec in report.recommendations)
        assert has_cache_rec


class TestComparePerformance:
    """Tests for compare_performance."""

    def test_compare_profile_results(self) -> None:
        """Test comparing two ProfileResult objects."""
        before = ProfileResult(
            operation_name="test", execution_time=2.0, peak_memory=100 * 1024 * 1024
        )

        after = ProfileResult(
            operation_name="test", execution_time=1.0, peak_memory=50 * 1024 * 1024
        )

        comparison = compare_performance(before, after)

        assert "2.000s" in comparison
        assert "1.000s" in comparison
        assert "100.00MB" in comparison
        assert "50.00MB" in comparison
        assert "faster" in comparison.lower()

    def test_compare_performance_reports(self) -> None:
        """Test comparing two PerformanceReport objects."""
        before = PerformanceReport(
            cookbook_name="test", total_time=5.0, total_memory=200 * 1024 * 1024
        )

        after = PerformanceReport(
            cookbook_name="test", total_time=3.0, total_memory=100 * 1024 * 1024
        )

        comparison = compare_performance(before, after)

        assert "5.000s" in comparison
        assert "3.000s" in comparison
        assert "%" in comparison  # Should show percentage improvement

    def test_compare_shows_regression(self) -> None:
        """Test comparison shows when performance gets worse."""
        before = ProfileResult(
            operation_name="test", execution_time=1.0, peak_memory=50 * 1024 * 1024
        )

        after = ProfileResult(
            operation_name="test", execution_time=2.0, peak_memory=100 * 1024 * 1024
        )

        comparison = compare_performance(before, after)

        assert "slower" in comparison.lower() or "-" in comparison


class TestProfilingIntegration:
    """Integration tests for profiling functionality."""

    def test_profile_multiple_operations(self) -> None:
        """Test profiling multiple different operations."""
        from souschef.server import parse_attributes, parse_template

        recipe_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"
        attrs_path = FIXTURES_DIR / "sample_cookbook" / "attributes" / "default.rb"
        template_path = (
            FIXTURES_DIR
            / "sample_cookbook"
            / "templates"
            / "default"
            / "config.yml.erb"
        )

        _, recipe_profile = profile_function(parse_recipe, str(recipe_path))
        _, attrs_profile = profile_function(parse_attributes, str(attrs_path))
        _, template_profile = profile_function(parse_template, str(template_path))

        # All should complete successfully
        assert recipe_profile.execution_time > 0
        assert attrs_profile.execution_time > 0
        assert template_profile.execution_time > 0

    def test_profiling_memory_cleanup(self) -> None:
        """Test that profiling doesn't leak memory."""
        recipe_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"

        # Profile multiple times
        profiles = []
        for _ in range(5):
            _, profile = profile_function(parse_recipe, str(recipe_path))
            profiles.append(profile)

        # Memory usage shouldn't grow linearly
        first_memory = profiles[0].peak_memory
        last_memory = profiles[-1].peak_memory

        # Allow some variation but not 5x growth
        assert last_memory < first_memory * 3
