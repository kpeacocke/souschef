"""Tests for AI assessment workflow paths."""

from pathlib import Path
from unittest.mock import patch

from souschef import assessment as assessment_module
from souschef.assessment import (
    _analyse_cookbook_metrics_with_ai,
    _call_ai_api,
    _get_ai_cookbook_analysis,
    _get_metadata_content,
    _get_recipe_content_sample,
    _is_ai_available,
    _process_cookbook_assessment_with_ai,
)


def test_is_ai_available_without_api_key() -> None:
    """Test AI availability requires an API key."""
    assert _is_ai_available("anthropic", "") is False
    assert _is_ai_available("openai", "") is False
    assert _is_ai_available("watson", "") is False


def test_is_ai_available_with_requests() -> None:
    """Test AI availability when requests library exists."""
    with patch.object(assessment_module, "requests", object()):
        assert _is_ai_available("anthropic", "key") is True
        assert _is_ai_available("openai", "key") is True


def test_is_ai_available_watson_without_client() -> None:
    """Test AI availability for Watson without API client."""
    with patch.object(assessment_module, "APIClient", None):
        assert _is_ai_available("watson", "key") is False


def test_analyse_cookbook_metrics_with_ai_aggregates() -> None:
    """Test metrics aggregation across multiple cookbooks."""
    assessments = [
        {
            "metrics": {"recipe_count": 4, "resource_count": 10},
            "complexity_score": 40,
            "estimated_effort_days": 2.0,
        },
        {
            "metrics": {"recipe_count": 2, "resource_count": 5},
            "complexity_score": 80,
            "estimated_effort_days": 4.0,
        },
    ]

    with patch(
        "souschef.assessment._assess_single_cookbook_with_ai",
        side_effect=assessments,
    ):
        cookbook_assessments, overall_metrics = _analyse_cookbook_metrics_with_ai(
            valid_paths=[Path("/tmp/c1"), Path("/tmp/c2")],
            ai_provider="anthropic",
            api_key="key",
            model="model",
            temperature=0.2,
            max_tokens=1000,
        )

    assert cookbook_assessments == assessments
    assert overall_metrics["total_cookbooks"] == 2
    assert overall_metrics["total_recipes"] == 6
    assert overall_metrics["total_resources"] == 15
    assert overall_metrics["complexity_score"] == 120
    assert overall_metrics["estimated_effort_days"] == 6.0
    assert overall_metrics["avg_complexity"] == 60


def test_process_cookbook_assessment_with_ai_pipeline() -> None:
    """Test assessment pipeline returns formatted report."""
    fake_assessments = [{"cookbook_name": "demo"}]
    fake_metrics = {"total_cookbooks": 1, "estimated_effort_days": 2}

    with (
        patch(
            "souschef.assessment._parse_cookbook_paths",
            return_value=[Path("/tmp/demo")],
        ),
        patch(
            "souschef.assessment._analyse_cookbook_metrics_with_ai",
            return_value=(fake_assessments, fake_metrics),
        ) as mock_analyse,
        patch(
            "souschef.assessment._generate_ai_migration_recommendations",
            return_value="Recommendations",
        ) as mock_recs,
        patch(
            "souschef.assessment._create_ai_migration_roadmap",
            return_value="Roadmap",
        ) as mock_roadmap,
        patch(
            "souschef.assessment._format_ai_assessment_report",
            return_value="Final Report",
        ) as mock_format,
    ):
        result = _process_cookbook_assessment_with_ai(
            cookbook_paths="/tmp/demo",
            migration_scope="full",
            target_platform="ansible_awx",
            ai_provider="anthropic",
            api_key="key",
            model="model",
            temperature=0.3,
            max_tokens=1000,
        )

    assert result == "Final Report"
    mock_analyse.assert_called_once()
    mock_recs.assert_called_once()
    mock_roadmap.assert_called_once()
    mock_format.assert_called_once()


def test_get_ai_cookbook_analysis_parses_json(tmp_path: Path) -> None:
    """Test AI cookbook analysis parses JSON responses."""
    with (
        patch(
            "souschef.assessment._get_recipe_content_sample",
            return_value="sample recipe",
        ),
        patch(
            "souschef.assessment._get_metadata_content",
            return_value="metadata",
        ),
        patch(
            "souschef.assessment._call_ai_api",
            return_value='{"complexity_score": 50, "estimated_effort_days": 4}',
        ),
    ):
        result = _get_ai_cookbook_analysis(
            cookbook_path=tmp_path,
            metrics={"recipe_count": 1},
            ai_provider="anthropic",
            api_key="key",
            model="model",
            temperature=0.2,
            max_tokens=1000,
        )

    assert result is not None
    assert result["complexity_score"] == 50
    assert result["estimated_effort_days"] == 4


def test_get_ai_cookbook_analysis_extracts_embedded_json(tmp_path: Path) -> None:
    """Test AI cookbook analysis extracts embedded JSON."""
    response_text = 'Analysis: {"complexity_score": 70, "estimated_effort_days": 7}'

    with (
        patch(
            "souschef.assessment._get_recipe_content_sample",
            return_value="sample recipe",
        ),
        patch(
            "souschef.assessment._get_metadata_content",
            return_value="metadata",
        ),
        patch(
            "souschef.assessment._call_ai_api",
            return_value=response_text,
        ),
    ):
        result = _get_ai_cookbook_analysis(
            cookbook_path=tmp_path,
            metrics={"recipe_count": 1},
            ai_provider="openai",
            api_key="key",
            model="model",
            temperature=0.2,
            max_tokens=1000,
        )

    assert result is not None
    assert result["complexity_score"] == 70
    assert result["estimated_effort_days"] == 7


def test_get_ai_cookbook_analysis_invalid_json_returns_none(tmp_path: Path) -> None:
    """Test AI cookbook analysis returns None for invalid JSON."""
    with (
        patch(
            "souschef.assessment._get_recipe_content_sample",
            return_value="sample recipe",
        ),
        patch(
            "souschef.assessment._get_metadata_content",
            return_value="metadata",
        ),
        patch(
            "souschef.assessment._call_ai_api",
            return_value="not json",
        ),
    ):
        result = _get_ai_cookbook_analysis(
            cookbook_path=tmp_path,
            metrics={"recipe_count": 1},
            ai_provider="anthropic",
            api_key="key",
            model="model",
            temperature=0.2,
            max_tokens=1000,
        )

    assert result is None


def test_get_recipe_content_sample_no_recipes(tmp_path: Path) -> None:
    """Test recipe content sample when recipes directory is missing."""
    result = _get_recipe_content_sample(tmp_path)

    assert "No recipes directory found" in result


def test_get_recipe_content_sample_empty_directory(tmp_path: Path) -> None:
    """Test recipe content sample when recipes directory is empty."""
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()

    result = _get_recipe_content_sample(tmp_path)

    assert "No recipe files found" in result


def test_get_recipe_content_sample_reads_recipes(tmp_path: Path) -> None:
    """Test recipe content sample reads available recipes."""
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    (recipes_dir / "default.rb").write_text("package 'nginx'\n")
    (recipes_dir / "web.rb").write_text("service 'nginx'\n")

    result = _get_recipe_content_sample(tmp_path)

    assert "default.rb" in result
    assert "web.rb" in result
    assert "package 'nginx'" in result


def test_get_recipe_content_sample_truncates_large_content(tmp_path: Path) -> None:
    """Test recipe content sample truncates very large recipes."""
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    large_content = "a" * 10000
    (recipes_dir / "large.rb").write_text(large_content)

    result = _get_recipe_content_sample(tmp_path)

    assert "large.rb" in result
    assert result.endswith("...")


def test_get_metadata_content_missing_file(tmp_path: Path) -> None:
    """Test metadata content when metadata file is missing."""
    result = _get_metadata_content(tmp_path)

    assert "No metadata.rb found" in result


def test_get_metadata_content_read_error(tmp_path: Path) -> None:
    """Test metadata content handles read errors."""
    metadata_file = tmp_path / "metadata.rb"
    metadata_file.write_text("name 'app'\n")

    with patch("pathlib.Path.read_text", side_effect=OSError("read failed")):
        result = _get_metadata_content(tmp_path)

    assert "Could not read metadata" in result


def test_call_ai_api_watson_invalid_base_url() -> None:
    """Test Watson AI call returns None for invalid base URL."""
    with patch(
        "souschef.assessment.validate_user_provided_url",
        side_effect=ValueError("bad url"),
    ):
        result = _call_ai_api(
            prompt="test",
            ai_provider="watson",
            api_key="key",
            model="model",
            temperature=0.2,
            max_tokens=1000,
            project_id="proj",
            base_url="bad://url",
        )

    assert result is None


def test_call_ai_api_watson_valid_base_url() -> None:
    """Test Watson AI call uses validated base URL."""
    with (
        patch(
            "souschef.assessment.validate_user_provided_url",
            return_value="https://validated.example",
        ),
        patch(
            "souschef.assessment._call_watson_api",
            return_value="ok",
        ),
    ):
        result = _call_ai_api(
            prompt="test",
            ai_provider="watson",
            api_key="key",
            model="model",
            temperature=0.2,
            max_tokens=1000,
            project_id="proj",
            base_url="https://raw.example",
        )

    assert result == "ok"


def test_call_ai_api_unknown_provider() -> None:
    """Test unknown AI provider returns None."""
    result = _call_ai_api(
        prompt="test",
        ai_provider="unknown",
        api_key="key",
        model="model",
        temperature=0.2,
        max_tokens=1000,
    )

    assert result is None


def test_call_ai_api_handles_provider_exception() -> None:
    """Test AI call returns None when provider call raises."""
    with patch(
        "souschef.assessment._call_anthropic_api",
        side_effect=RuntimeError("boom"),
    ):
        result = _call_ai_api(
            prompt="test",
            ai_provider="anthropic",
            api_key="key",
            model="model",
            temperature=0.2,
            max_tokens=1000,
        )

    assert result is None
