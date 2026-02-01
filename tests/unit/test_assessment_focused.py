"""Focused tests for assessment.py validation and utility functions."""

from pathlib import Path
from unittest.mock import patch

from souschef.assessment import (
    _analyse_cookbook_metrics,
    _get_overall_complexity_level,
    _normalize_cookbook_root,
    _parse_cookbook_paths,
    _validate_assessment_inputs,
)


class TestValidateAssessmentInputs:
    """Tests for _validate_assessment_inputs function."""

    def test_empty_cookbook_paths(self):
        """Test validation with empty cookbook paths."""
        result = _validate_assessment_inputs("", "full", "ansible_core")
        assert result is not None
        assert "Cookbook paths cannot be empty" in result

    def test_whitespace_cookbook_paths(self):
        """Test validation with whitespace-only paths."""
        result = _validate_assessment_inputs("   ", "full", "ansible_core")
        assert result is not None
        assert "Cookbook paths cannot be empty" in result

    def test_invalid_migration_scope(self):
        """Test validation with invalid migration scope."""
        result = _validate_assessment_inputs("/path", "invalid_scope", "ansible_core")
        assert result is not None
        assert "Invalid migration scope" in result
        assert "full, recipes_only, infrastructure_only" in result

    def test_invalid_platform(self):
        """Test validation with invalid target platform."""
        result = _validate_assessment_inputs("/path", "full", "invalid_platform")
        assert result is not None
        assert "Invalid target platform" in result
        assert "ansible_awx, ansible_core, ansible_tower" in result

    def test_valid_inputs_full(self):
        """Test validation with all valid inputs (full scope)."""
        result = _validate_assessment_inputs("/path", "full", "ansible_core")
        assert result is None

    def test_valid_inputs_recipes_only(self):
        """Test validation with recipes_only scope."""
        result = _validate_assessment_inputs("/path", "recipes_only", "ansible_awx")
        assert result is None

    def test_valid_inputs_infrastructure_only(self):
        """Test validation with infrastructure_only scope."""
        result = _validate_assessment_inputs(
            "/path", "infrastructure_only", "ansible_tower"
        )
        assert result is None


class TestGetOverallComplexityLevel:
    """Tests for _get_overall_complexity_level function."""

    def test_low_complexity(self):
        """Test low complexity determination."""
        metrics = {"avg_complexity": 15}
        result = _get_overall_complexity_level(metrics)
        assert result == "Low"

    def test_medium_complexity(self):
        """Test medium complexity determination."""
        metrics = {"avg_complexity": 50}
        result = _get_overall_complexity_level(metrics)
        assert result == "Medium"

    def test_high_complexity(self):
        """Test high complexity determination."""
        metrics = {"avg_complexity": 75}
        result = _get_overall_complexity_level(metrics)
        assert result == "High"

    def test_boundary_low_medium(self):
        """Test boundary between low and medium."""
        metrics = {"avg_complexity": 30}
        result = _get_overall_complexity_level(metrics)
        assert result == "Medium"  # At boundary, should be Medium

    def test_missing_avg_complexity(self):
        """Test with missing avg_complexity key."""
        metrics = {}
        result = _get_overall_complexity_level(metrics)
        assert result == "Low"  # Defaults to 0, which is < 30


class TestParseBookPaths:
    """Tests for _parse_cookbook_paths function."""

    def test_single_path(self, tmp_path):
        """Test parsing single cookbook path."""
        cookbook = tmp_path / "cookbook1"
        cookbook.mkdir()

        result = _parse_cookbook_paths(str(cookbook))
        assert len(result) == 1
        assert result[0] == cookbook

    def test_multiple_paths(self, tmp_path):
        """Test parsing multiple cookbook paths."""
        cookbook1 = tmp_path / "cookbook1"
        cookbook2 = tmp_path / "cookbook2"
        cookbook1.mkdir()
        cookbook2.mkdir()

        paths = f"{cookbook1},{cookbook2}"
        result = _parse_cookbook_paths(paths)
        assert len(result) == 2
        assert cookbook1 in result
        assert cookbook2 in result

    def test_nonexistent_paths_filtered(self, tmp_path):
        """Test that nonexistent paths are filtered out."""
        cookbook1 = tmp_path / "cookbook1"
        cookbook2 = tmp_path / "cookbook2"
        cookbook1.mkdir()
        # cookbook2 deliberately not created

        paths = f"{cookbook1},{cookbook2}"
        result = _parse_cookbook_paths(paths)
        assert len(result) == 1
        assert cookbook1 in result

    def test_whitespace_handling(self, tmp_path):
        """Test that whitespace is properly stripped."""
        cookbook = tmp_path / "cookbook1"
        cookbook.mkdir()

        paths = f"  {cookbook}  ,  {cookbook}  "
        result = _parse_cookbook_paths(paths)
        assert len(result) == 2


class TestNormalizeCookbookRoot:
    """Tests for _normalize_cookbook_root function."""

    def test_string_path(self):
        """Test normalization of string path."""
        result = _normalize_cookbook_root("/path/to/cookbook")
        assert isinstance(result, Path)
        assert str(result) == "/path/to/cookbook"

    def test_path_object(self):
        """Test normalization of Path object."""
        path = Path("/path/to/cookbook")
        result = _normalize_cookbook_root(path)
        assert isinstance(result, Path)
        assert result == path


class TestAnalyseCookbookMetrics:
    """Tests for _analyse_cookbook_metrics function."""

    def test_empty_paths(self):
        """Test with empty cookbook paths list."""
        cookbook_assessments, overall_metrics = _analyse_cookbook_metrics([])
        assert len(cookbook_assessments) == 0
        assert overall_metrics["total_cookbooks"] == 0
        assert overall_metrics["total_recipes"] == 0

    @patch("souschef.assessment._assess_single_cookbook")
    def test_single_cookbook(self, mock_assess):
        """Test metrics for single cookbook."""
        mock_assess.return_value = {
            "metrics": {"recipe_count": 5, "resource_count": 10},
            "complexity_score": 25,
            "estimated_effort_days": 3,
        }

        paths = [Path("/fake/cookbook")]
        cookbook_assessments, overall_metrics = _analyse_cookbook_metrics(paths)

        assert len(cookbook_assessments) == 1
        assert overall_metrics["total_cookbooks"] == 1
        assert overall_metrics["total_recipes"] == 5
        assert overall_metrics["total_resources"] == 10
        assert overall_metrics["complexity_score"] == 25
        assert overall_metrics["estimated_effort_days"] == 3
        assert overall_metrics["avg_complexity"] == 25

    @patch("souschef.assessment._assess_single_cookbook")
    def test_multiple_cookbooks_aggregation(self, mock_assess):
        """Test metrics aggregation for multiple cookbooks."""
        mock_assess.side_effect = [
            {
                "metrics": {"recipe_count": 5, "resource_count": 10},
                "complexity_score": 20,
                "estimated_effort_days": 2,
            },
            {
                "metrics": {"recipe_count": 10, "resource_count": 20},
                "complexity_score": 40,
                "estimated_effort_days": 4,
            },
        ]

        paths = [Path("/fake/cookbook1"), Path("/fake/cookbook2")]
        cookbook_assessments, overall_metrics = _analyse_cookbook_metrics(paths)

        assert len(cookbook_assessments) == 2
        assert overall_metrics["total_cookbooks"] == 2
        assert overall_metrics["total_recipes"] == 15
        assert overall_metrics["total_resources"] == 30
        assert overall_metrics["complexity_score"] == 60
        assert overall_metrics["estimated_effort_days"] == 6
        assert overall_metrics["avg_complexity"] == 30  # (20 + 40) / 2


# TestFormatAssessmentReport removed - too complex with many dependencies
# The function is already well-tested through integration tests
