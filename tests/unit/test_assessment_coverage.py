"""Coverage tests for assessment module."""

import builtins
import importlib
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import souschef.assessment as assessment


def test_optional_requests_import_error_sets_none() -> None:
    """Missing requests should set requests to None on reload."""
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "requests":
            raise ImportError("missing requests")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        reloaded = importlib.reload(assessment)
        assert reloaded.requests is None

    importlib.reload(assessment)


def test_assess_chef_migration_complexity_exception() -> None:
    """Unexpected errors should return formatted error output."""
    with (
        patch("souschef.assessment._validate_assessment_inputs", return_value=None),
        patch(
            "souschef.assessment._process_cookbook_assessment",
            side_effect=RuntimeError("boom"),
        ),
    ):
        result = assessment.assess_chef_migration_complexity("/tmp")

    assert "Error during" in result


def test_parse_assessment_exception_returns_error_dict() -> None:
    """parse_chef_migration_assessment should return error dict on exception."""
    with patch(
        "souschef.assessment._validate_assessment_inputs",
        side_effect=RuntimeError("bad"),
    ):
        result = assessment.parse_chef_migration_assessment("/tmp")

    assert "error" in result


def test_generate_migration_plan_exception_returns_error() -> None:
    """generate_migration_plan should return formatted error on exceptions."""
    with patch(
        "souschef.assessment._parse_and_assess_cookbooks",
        side_effect=RuntimeError("bad"),
    ):
        result = assessment.generate_migration_plan("/tmp", "phased", 4)

    assert "Error during" in result


def test_analyse_cookbook_dependencies_invalid_path() -> None:
    """analyse_cookbook_dependencies should report invalid path errors."""
    with patch("souschef.assessment._normalize_path", side_effect=ValueError("bad")):
        result = assessment.analyse_cookbook_dependencies("/tmp")

    assert "Invalid cookbook path" in result


def test_generate_migration_report_exception_returns_error() -> None:
    """generate_migration_report should return formatted error on exceptions."""
    with patch(
        "souschef.assessment._generate_comprehensive_migration_report",
        side_effect=RuntimeError("bad"),
    ):
        result = assessment.generate_migration_report("{}")

    assert "Error during" in result


def test_validate_conversion_exception_returns_error() -> None:
    """validate_conversion should return formatted error on exceptions."""
    with patch(
        "souschef.assessment.ValidationEngine.validate_conversion",
        side_effect=RuntimeError("bad"),
    ):
        result = assessment.validate_conversion("recipe", "content")

    assert "Error during" in result


def test_count_cookbook_artifacts_glob_error(tmp_path: Path) -> None:
    """Glob errors should be handled and return zero counts."""
    (tmp_path / "recipes").mkdir()
    (tmp_path / "templates").mkdir()
    (tmp_path / "files").mkdir()

    with patch("pathlib.Path.glob", side_effect=OSError("boom")):
        result = assessment._count_cookbook_artifacts(tmp_path)

    assert result["recipe_count"] == 0
    assert result["template_count"] == 0


def test_count_cookbook_artifacts_exists_error(tmp_path: Path) -> None:
    """Existence errors should be handled safely for optional files."""
    (tmp_path / "recipes").mkdir()
    (tmp_path / "templates").mkdir()

    original_exists = Path.exists

    def fake_exists(path: Path) -> bool:
        if path.name in {
            "Berksfile",
            "chefignore",
            "Thorfile",
            ".kitchen.yml",
            "kitchen.yml",
            "test",
            "spec",
        }:
            raise OSError("boom")
        return original_exists(path)

    with patch("pathlib.Path.exists", new=fake_exists):
        result = assessment._count_cookbook_artifacts(tmp_path)

    assert result["has_berksfile"] == 0
    assert result["has_chefignore"] == 0


def test_analyze_recipes_glob_error(tmp_path: Path) -> None:
    """Recipe glob errors should be handled safely."""
    (tmp_path / "recipes").mkdir()
    with patch("pathlib.Path.glob", side_effect=OSError("boom")):
        counts = assessment._analyze_recipes(tmp_path)

    assert counts == (0, 0, 0)


def test_analyze_recipes_invalid_candidate(tmp_path: Path) -> None:
    """Invalid recipe candidates should be skipped."""
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    (recipes_dir / "default.rb").write_text("package 'nginx'")

    with patch(
        "souschef.assessment._validated_candidate", side_effect=ValueError("bad")
    ):
        counts = assessment._analyze_recipes(tmp_path)

    assert counts == (0, 0, 0)


def test_analyze_recipes_read_error(tmp_path: Path) -> None:
    """Read errors should be handled while analysing recipes."""
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    recipe_file = recipes_dir / "default.rb"
    recipe_file.write_text("package 'nginx'")

    with (
        patch("souschef.assessment._validated_candidate", return_value=recipe_file),
        patch("pathlib.Path.read_text", side_effect=OSError("bad")),
    ):
        counts = assessment._analyze_recipes(tmp_path)

    assert counts == (0, 0, 0)


def test_analyze_attributes_glob_error(tmp_path: Path) -> None:
    """Attribute glob errors should be handled safely."""
    (tmp_path / "attributes").mkdir()
    with patch("pathlib.Path.glob", side_effect=OSError("boom")):
        result = assessment._analyze_attributes(tmp_path)

    assert result == 0


def test_analyze_attributes_invalid_candidate(tmp_path: Path) -> None:
    """Invalid attribute candidates should be skipped."""
    attributes_dir = tmp_path / "attributes"
    attributes_dir.mkdir()
    (attributes_dir / "default.rb").write_text("default['x'] = 1")

    with patch(
        "souschef.assessment._validated_candidate", side_effect=ValueError("bad")
    ):
        result = assessment._analyze_attributes(tmp_path)

    assert result == 0


def test_analyze_attributes_read_error(tmp_path: Path) -> None:
    """Read errors should be handled while analysing attributes."""
    attributes_dir = tmp_path / "attributes"
    attributes_dir.mkdir()
    attr_file = attributes_dir / "default.rb"
    attr_file.write_text("default['x'] = 1")

    with (
        patch("souschef.assessment._validated_candidate", return_value=attr_file),
        patch("pathlib.Path.read_text", side_effect=OSError("bad")),
    ):
        result = assessment._analyze_attributes(tmp_path)

    assert result == 0


def test_analyze_templates_glob_error(tmp_path: Path) -> None:
    """Template glob errors should be handled safely."""
    (tmp_path / "templates").mkdir()
    with patch("pathlib.Path.glob", side_effect=OSError("boom")):
        result = assessment._analyze_templates(tmp_path)

    assert result == 0


def test_analyze_templates_invalid_candidate(tmp_path: Path) -> None:
    """Invalid template candidates should be skipped."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "a.erb").write_text("<%= node['x'] %>")

    with patch(
        "souschef.assessment._validated_candidate", side_effect=ValueError("bad")
    ):
        result = assessment._analyze_templates(tmp_path)

    assert result == 0


def test_analyze_templates_read_error(tmp_path: Path) -> None:
    """Read errors should be handled while analysing templates."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    template_file = templates_dir / "a.erb"
    template_file.write_text("<%= node['x'] %>")

    with (
        patch("souschef.assessment._validated_candidate", return_value=template_file),
        patch("pathlib.Path.read_text", side_effect=OSError("bad")),
    ):
        result = assessment._analyze_templates(tmp_path)

    assert result == 0


def test_analyze_libraries_safe_glob_error(tmp_path: Path) -> None:
    """Library glob errors should be handled safely."""
    (tmp_path / "libraries").mkdir()
    with patch("souschef.assessment.safe_glob", side_effect=OSError("boom")):
        result = assessment._analyze_libraries(tmp_path)

    assert result == 0


def test_analyze_libraries_read_error(tmp_path: Path) -> None:
    """Read errors should be handled while analysing libraries."""
    libraries_dir = tmp_path / "libraries"
    libraries_dir.mkdir()
    lib_file = libraries_dir / "a.rb"
    lib_file.write_text("class X\nend")

    with (
        patch("souschef.assessment.safe_glob", return_value=[lib_file]),
        patch("pathlib.Path.read_text", side_effect=OSError("bad")),
    ):
        result = assessment._analyze_libraries(tmp_path)

    assert result == 0


def test_count_definitions_safe_glob_error(tmp_path: Path) -> None:
    """Definition glob errors should be handled safely."""
    (tmp_path / "definitions").mkdir()
    with patch("souschef.assessment.safe_glob", side_effect=OSError("boom")):
        result = assessment._count_definitions(tmp_path)

    assert result == 0


def test_parse_berksfile_read_error(tmp_path: Path) -> None:
    """Berksfile read errors should be handled safely."""
    berksfile = tmp_path / "Berksfile"
    berksfile.write_text("cookbook 'nginx'")

    with patch("pathlib.Path.read_text", side_effect=OSError("bad")):
        result = assessment._parse_berksfile(tmp_path)

    assert result["dependencies"] == []


def test_parse_chefignore_read_error(tmp_path: Path) -> None:
    """Chefignore read errors should be handled safely."""
    chefignore = tmp_path / "chefignore"
    chefignore.write_text("*.log")

    with patch("pathlib.Path.read_text", side_effect=OSError("bad")):
        result = assessment._parse_chefignore(tmp_path)

    assert result["patterns"] == []


def test_parse_thorfile_missing(tmp_path: Path) -> None:
    """Missing Thorfile should return empty results."""
    result = assessment._parse_thorfile(tmp_path)
    assert result["tasks"] == []


def test_parse_thorfile_read_error(tmp_path: Path) -> None:
    """Thorfile read errors should be handled safely."""
    thorfile = tmp_path / "Thorfile"
    thorfile.write_text("desc 'x'\ndef x; end")

    with patch("pathlib.Path.read_text", side_effect=OSError("bad")):
        result = assessment._parse_thorfile(tmp_path)

    assert result["tasks"] == []


def test_parse_metadata_file_read_error(tmp_path: Path) -> None:
    """Metadata read errors should be handled safely."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text("name 'x'")

    with patch("pathlib.Path.read_text", side_effect=OSError("bad")):
        result = assessment._parse_metadata_file(tmp_path)

    assert result["name"] == ""


def test_format_activity_breakdown_empty() -> None:
    """Empty activity list should return empty string."""
    assert assessment._format_activity_breakdown([]) == ""


def test_generate_recommendations_effort_and_custom() -> None:
    """Recommendations should include effort and custom resource guidance."""
    assessments = [
        {
            "metrics": {"custom_resources": 1},
            "complexity_score": 40,
            "estimated_effort_days": 40,
            "migration_priority": "medium",
            "cookbook_name": "cb",
        }
    ]
    metrics = {"estimated_effort_days": 40, "avg_complexity": 40}

    result = assessment._generate_migration_recommendations_from_assessment(
        assessments, metrics, "ansible_awx"
    )

    assert "dedicated migration team" in result
    assert "custom resource" in result


def test_assess_timeline_risks_large_scope() -> None:
    """Large scope should add a timeline risk."""
    assessments = [{"estimated_effort_days": 60}]
    risks = assessment._assess_timeline_risks(assessments)

    assert any("Large migration scope" in risk for risk in risks)


def test_estimate_resource_requirements_mid_and_high() -> None:
    """Resource requirements should handle mid and high effort bands."""
    mid = assessment._estimate_resource_requirements(
        {"estimated_effort_days": 40}, "ansible_awx"
    )
    high = assessment._estimate_resource_requirements(
        {"estimated_effort_days": 120}, "ansible_awx"
    )

    assert "2 developers" in mid
    assert "3-4 developers" in high
    assert "1-2 developers" in mid
    assert "2-3 developers" in high


def test_format_migration_order_empty() -> None:
    """Empty order should return default message."""
    assert assessment._format_migration_order([]) == "No order analysis available."


def test_format_circular_dependencies_non_empty() -> None:
    """Circular dependencies should include cookbook names."""
    circular = [{"cookbook1": "a", "cookbook2": "b", "type": "potential"}]
    result = assessment._format_circular_dependencies(circular)

    assert "a" in result
    assert "b" in result


def test_dependency_migration_impact_multiple_factors() -> None:
    """Impact analysis should mention multiple dependency risks."""
    analysis = {
        "community_cookbooks": ["nginx"],
        "circular_dependencies": ["x"],
        "direct_dependencies": ["a", "b", "c", "d", "e", "f"],
    }
    impact = assessment._analyse_dependency_migration_impact(analysis)

    assert "community cookbooks" in impact
    assert "circular dependencies" in impact
    assert "High dependency count" in impact


def test_is_ai_available_with_missing_key() -> None:
    """Missing API key should disable AI."""
    assert assessment._is_ai_available("anthropic", "") is False


def test_is_ai_available_with_requests_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing requests should disable AI for anthropic/openai."""
    monkeypatch.setattr(assessment, "requests", None)
    assert assessment._is_ai_available("anthropic", "key") is False


def test_assess_single_cookbook_ai_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """AI fallback should return rule-based assessment."""
    monkeypatch.setattr(assessment, "_is_ai_available", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        assessment,
        "parse_chef_migration_assessment",
        lambda *_args, **_kwargs: {"fallback": True},
    )

    result = assessment.assess_single_cookbook_with_ai("/tmp")

    assert result.get("fallback") is True


def test_assess_single_cookbook_ai_high_complexity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AI assessment should map high complexity to High label."""
    cookbook = tmp_path / "cb"
    cookbook.mkdir()

    monkeypatch.setattr(assessment, "_is_ai_available", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        assessment,
        "_assess_single_cookbook_with_ai",
        lambda *_args, **_kwargs: {
            "complexity_score": 80,
            "estimated_effort_days": 10,
            "activity_breakdown": [],
        },
    )

    result = assessment.assess_single_cookbook_with_ai(str(cookbook))

    assert result["complexity"] == "High"


def test_assess_single_cookbook_ai_exception() -> None:
    """Exceptions should be formatted in AI assessment."""
    with patch("souschef.assessment._normalize_path", side_effect=ValueError("bad")):
        result = assessment.assess_single_cookbook_with_ai("/tmp")

    assert "error" in result


def test_assess_complexity_with_ai_invalid_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid inputs should return validation error."""
    monkeypatch.setattr(
        assessment,
        "_validate_assessment_inputs",
        lambda *_args, **_kwargs: "Error: bad",
    )

    result = assessment.assess_chef_migration_complexity_with_ai("/tmp")

    assert result.startswith("Error:")


def test_assess_complexity_with_ai_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """AI unavailability should fall back to rule-based assessment."""
    monkeypatch.setattr(assessment, "_is_ai_available", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        assessment,
        "assess_chef_migration_complexity",
        lambda *_args, **_kwargs: "fallback",
    )

    result = assessment.assess_chef_migration_complexity_with_ai("/tmp")

    assert result == "fallback"


def test_get_ai_cookbook_analysis_returns_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Missing AI response should return None."""
    monkeypatch.setattr(assessment, "_call_ai_api", lambda *_args, **_kwargs: None)
    result = assessment._get_ai_cookbook_analysis(
        tmp_path, {}, "anthropic", "key", "m", 0.1, 100
    )

    assert result is None


def test_get_ai_cookbook_analysis_bad_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Invalid AI JSON should return None."""
    monkeypatch.setattr(
        assessment, "_call_ai_api", lambda *_args, **_kwargs: "not json"
    )
    result = assessment._get_ai_cookbook_analysis(
        tmp_path, {}, "anthropic", "key", "m", 0.1, 100
    )

    assert result is None


def test_get_ai_cookbook_analysis_exception(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AI analysis exceptions should return None."""
    monkeypatch.setattr(
        assessment,
        "_get_recipe_content_sample",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad")),  # noqa: S7500
    )
    result = assessment._get_ai_cookbook_analysis(
        tmp_path, {}, "anthropic", "key", "m", 0.1, 100
    )

    assert result is None


def test_get_recipe_content_sample_path_traversal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Path traversal should raise RuntimeError."""
    monkeypatch.setattr(os.path, "commonpath", lambda *_args, **_kwargs: "/other")

    with pytest.raises(RuntimeError, match="Path traversal"):
        assessment._get_recipe_content_sample(tmp_path)


def test_get_recipe_content_sample_read_error(tmp_path: Path) -> None:
    """Read errors should return a fallback message."""
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    recipe_file = recipes_dir / "default.rb"
    recipe_file.write_text("content")

    with patch("pathlib.Path.read_text", side_effect=OSError("bad")):
        result = assessment._get_recipe_content_sample(tmp_path)

    assert result == "Could not read recipe content"


def test_get_metadata_content_path_traversal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Path traversal should raise RuntimeError for metadata."""
    monkeypatch.setattr(os.path, "commonpath", lambda *_args, **_kwargs: "/other")

    with pytest.raises(RuntimeError, match="Path traversal"):
        assessment._get_metadata_content(tmp_path)


def test_get_metadata_content_read_error(tmp_path: Path) -> None:
    """Read errors should return fallback message."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text("name 'x'")

    with patch("pathlib.Path.read_text", side_effect=OSError("bad")):
        result = assessment._get_metadata_content(tmp_path)

    assert result == "Could not read metadata"


def test_call_ai_api_watson_invalid_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid watson base URL should return None."""
    monkeypatch.setattr(
        assessment,
        "validate_user_provided_url",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad")),  # noqa: S7500
    )
    result = assessment._call_ai_api(
        "prompt",
        "watson",
        "key",
        "m",
        0.1,
        100,
        project_id="p",
        base_url="bad",
    )

    assert result is None


def test_call_anthropic_api_requests_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing requests should return None for anthropic."""
    monkeypatch.setattr(assessment, "requests", None)
    assert assessment._call_anthropic_api("p", "k", "m", 0.1, 100) is None


def test_call_anthropic_api_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-200 responses should return None."""
    mock_response = MagicMock(status_code=500)
    monkeypatch.setattr(
        assessment, "requests", MagicMock(post=MagicMock(return_value=mock_response))
    )

    assert assessment._call_anthropic_api("p", "k", "m", 0.1, 100) is None


def test_call_openai_api_requests_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing requests should return None for openai."""
    monkeypatch.setattr(assessment, "requests", None)
    assert assessment._call_openai_api("p", "k", "m", 0.1, 100) is None


def test_call_openai_api_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAI errors should return None."""
    mock_requests = MagicMock()
    mock_requests.post.side_effect = RuntimeError("bad")
    monkeypatch.setattr(assessment, "requests", mock_requests)

    assert assessment._call_openai_api("p", "k", "m", 0.1, 100) is None


def test_call_watson_api_no_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing APIClient should return None."""
    monkeypatch.setattr(assessment, "APIClient", None)
    assert assessment._call_watson_api("p", "k", "m", 0.1, 100) is None


def test_call_watson_api_no_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Watson API with no response should return None."""

    class Dummy:
        def __init__(self, *args, **kwargs):  # noqa: S1186
            pass  # Intentionally empty - this is a dummy class for mocking purposes

    monkeypatch.setattr(assessment, "APIClient", Dummy)
    result = assessment._call_watson_api("p", "k", "m", 0.1, 100)

    assert result is None


def test_call_watson_api_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Watson API errors should return None."""

    class Dummy:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("bad")

    monkeypatch.setattr(assessment, "APIClient", Dummy)
    result = assessment._call_watson_api("p", "k", "m", 0.1, 100)

    assert result is None


def test_generate_ai_recommendations_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """AI recommendation fallback should use rule-based output."""
    monkeypatch.setattr(assessment, "_call_ai_api", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        assessment,
        "_generate_migration_recommendations_from_assessment",
        lambda *_args, **_kwargs: "fallback",
    )
    result = assessment._generate_ai_migration_recommendations(
        [],
        {"total_cookbooks": 0, "estimated_effort_days": 0},
        "ansible_awx",
        "anthropic",
        "key",
        "m",
        0.1,
        100,
    )

    assert result == "fallback"


def test_generate_ai_recommendations_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """AI recommendation errors should fall back to rule-based output."""
    monkeypatch.setattr(
        assessment,
        "_call_ai_api",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad")),  # noqa: S7500
    )
    monkeypatch.setattr(
        assessment,
        "_generate_migration_recommendations_from_assessment",
        lambda *_args, **_kwargs: "fallback",
    )
    result = assessment._generate_ai_migration_recommendations(
        [],
        {"total_cookbooks": 0, "estimated_effort_days": 0},
        "ansible_awx",
        "anthropic",
        "key",
        "m",
        0.1,
        100,
    )

    assert result == "fallback"


def test_create_ai_roadmap_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """AI roadmap fallback should use rule-based output."""
    monkeypatch.setattr(assessment, "_call_ai_api", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        assessment, "_create_migration_roadmap", lambda *_args, **_kwargs: "fallback"
    )

    result = assessment._create_ai_migration_roadmap(
        [], "anthropic", "key", "m", 0.1, 100
    )

    assert result == "fallback"


def test_create_ai_roadmap_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """AI roadmap errors should fall back to rule-based output."""
    monkeypatch.setattr(
        assessment,
        "_call_ai_api",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad")),  # noqa: S7500
    )
    monkeypatch.setattr(
        assessment, "_create_migration_roadmap", lambda *_args, **_kwargs: "fallback"
    )

    result = assessment._create_ai_migration_roadmap(
        [], "anthropic", "key", "m", 0.1, 100
    )

    assert result == "fallback"


def test_format_ai_assessment_report_contains_header() -> None:
    """AI assessment report should contain header text."""
    result = assessment._format_ai_assessment_report(
        "full",
        "ansible_awx",
        {
            "total_cookbooks": 0,
            "total_recipes": 0,
            "total_resources": 0,
            "estimated_effort_days": 0,
        },
        [],
        "recs",
        "roadmap",
    )

    assert "AI-Enhanced" in result


def test_format_ai_cookbook_assessments_empty() -> None:
    """Empty AI cookbook list should return default message."""
    assert assessment._format_ai_cookbook_assessments([]) == "No cookbooks assessed."


def test_format_ai_cookbook_assessments_with_insights() -> None:
    """AI cookbook assessment should include insights section."""
    assessments = [
        {
            "cookbook_name": "cb",
            "migration_priority": "high",
            "complexity_score": 80,
            "estimated_effort_days": 10,
            "metrics": {"recipe_count": 1, "resource_count": 2, "custom_resources": 0},
            "challenges": [],
            "ai_insights": "note",
        }
    ]
    result = assessment._format_ai_cookbook_assessments(assessments)

    assert "note" in result


def test_format_ai_complexity_analysis_empty() -> None:
    """Empty list should return default analysis message."""
    assert (
        assessment._format_ai_complexity_analysis([])
        == "No complexity analysis available."
    )


def test_format_ai_complexity_analysis_with_insights() -> None:
    """Analysis should include AI assessment summary."""
    assessments = [
        {"complexity_score": 10, "ai_insights": "x", "challenges": []},
        {"complexity_score": 80, "ai_insights": "y", "challenges": []},
    ]
    result = assessment._format_ai_complexity_analysis(assessments)

    assert "AI-Enhanced Assessments" in result


def test_calculate_activity_breakdown_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Errors should be returned as error dict in activity breakdown."""
    monkeypatch.setattr(
        assessment,
        "_normalize_path",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad")),  # noqa: S7500
    )
    result = assessment.calculate_activity_breakdown("/tmp")

    assert "error" in result


def test_analyze_libraries_success_counts(tmp_path: Path) -> None:
    """Library analysis should count classes and methods."""
    libraries_dir = tmp_path / "libraries"
    libraries_dir.mkdir()
    lib_file = libraries_dir / "a.rb"
    lib_file.write_text("class X\n  def y\n  end\nend")

    with patch("souschef.assessment.safe_glob", return_value=[lib_file]):
        result = assessment._analyze_libraries(tmp_path)

    assert result > 0


def test_collect_metadata_dependencies_invalid_candidate(tmp_path: Path) -> None:
    """Invalid metadata candidate should return empty dependencies."""
    metadata = tmp_path / "metadata.rb"
    metadata.write_text("depends 'nginx'")

    with patch(
        "souschef.assessment._validated_candidate", side_effect=ValueError("bad")
    ):
        result = assessment._collect_metadata_dependencies(tmp_path)

    assert result == []


def test_collect_berks_dependencies_invalid_candidate(tmp_path: Path) -> None:
    """Invalid Berksfile candidate should return empty dependencies."""
    berksfile = tmp_path / "Berksfile"
    berksfile.write_text("cookbook 'nginx'")

    with patch(
        "souschef.assessment._validated_candidate", side_effect=ValueError("bad")
    ):
        result = assessment._collect_berks_dependencies(tmp_path)

    assert result == []


def test_identify_circular_dependencies_potential() -> None:
    """Potential circular dependency should be detected."""
    analysis = {
        "cookbook_name": "web",
        "direct_dependencies": ["web_base"],
    }

    result = assessment._identify_circular_dependencies(analysis)

    assert result


def test_assess_single_cookbook_ai_medium_complexity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AI assessment should map medium complexity to Medium label."""
    cookbook = tmp_path / "cb"
    cookbook.mkdir()

    monkeypatch.setattr(assessment, "_is_ai_available", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        assessment,
        "_assess_single_cookbook_with_ai",
        lambda *_args, **_kwargs: {
            "complexity_score": 50,
            "estimated_effort_days": 10,
            "activity_breakdown": [],
        },
    )

    result = assessment.assess_single_cookbook_with_ai(str(cookbook))

    assert result["complexity"] == "Medium"


def test_assess_complexity_with_ai_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """AI availability should use AI assessment workflow."""
    monkeypatch.setattr(
        assessment,
        "_validate_assessment_inputs",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(assessment, "_is_ai_available", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        assessment,
        "_process_cookbook_assessment_with_ai",
        lambda *_args, **_kwargs: "ai-report",
    )

    result = assessment.assess_chef_migration_complexity_with_ai("/tmp")

    assert result == "ai-report"


def test_is_ai_available_unknown_provider() -> None:
    """Unknown provider should return False."""
    assert assessment._is_ai_available("unknown", "key") is False


def test_assess_single_cookbook_with_ai_uses_ai_analysis(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AI analysis data should be used when present."""
    cookbook = tmp_path / "cb"
    cookbook.mkdir()

    monkeypatch.setattr(
        assessment,
        "_count_cookbook_artifacts",
        lambda *_args, **_kwargs: {
            "recipe_count": 1,
            "resource_count": 2,
            "custom_resources": 0,
            "ruby_blocks": 0,
            "template_count": 0,
            "file_count": 0,
        },
    )
    monkeypatch.setattr(
        assessment,
        "_analyse_recipe_complexity",
        lambda *_args, **_kwargs: {
            "resource_count": 2,
            "custom_resources": 0,
            "ruby_blocks": 0,
        },
    )
    monkeypatch.setattr(
        assessment,
        "_get_ai_cookbook_analysis",
        lambda *_args, **_kwargs: {
            "complexity_score": 90,
            "estimated_effort_days": 12,
            "challenges": ["x"],
            "migration_priority": "high",
            "insights": "note",
        },
    )

    result = assessment._assess_single_cookbook_with_ai(
        cookbook, "anthropic", "key", "m", 0.1, 100
    )

    assert result["complexity_score"] == 90
    assert result["estimated_effort_days"] == 12


def test_call_ai_api_openai_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAI branch should call the OpenAI API helper."""
    monkeypatch.setattr(assessment, "_call_openai_api", lambda *_args, **_kwargs: "ok")
    result = assessment._call_ai_api("p", "openai", "k", "m", 0.1, 100)

    assert result == "ok"


def test_call_anthropic_api_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Anthropic API errors should return None."""
    mock_requests = MagicMock()
    mock_requests.post.side_effect = RuntimeError("bad")
    monkeypatch.setattr(assessment, "requests", mock_requests)

    assert assessment._call_anthropic_api("p", "k", "m", 0.1, 100) is None


def test_generate_ai_recommendations_ai_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AI recommendations should return response when present."""
    monkeypatch.setattr(assessment, "_call_ai_api", lambda *_args, **_kwargs: "ai")
    result = assessment._generate_ai_migration_recommendations(
        [],
        {"total_cookbooks": 0, "estimated_effort_days": 0},
        "ansible_awx",
        "anthropic",
        "key",
        "m",
        0.1,
        100,
    )

    assert result == "ai"


def test_create_ai_roadmap_ai_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """AI roadmap should return response when present."""
    monkeypatch.setattr(assessment, "_call_ai_api", lambda *_args, **_kwargs: "ai")
    result = assessment._create_ai_migration_roadmap(
        [], "anthropic", "key", "m", 0.1, 100
    )

    assert result == "ai"


def test_format_ai_cookbook_assessments_priority_icons() -> None:
    """Priority icons should render for medium and low priorities."""
    assessments = [
        {
            "cookbook_name": "cb1",
            "migration_priority": "medium",
            "complexity_score": 40,
            "estimated_effort_days": 10,
            "metrics": {"recipe_count": 1, "resource_count": 2, "custom_resources": 0},
            "challenges": [],
        },
        {
            "cookbook_name": "cb2",
            "migration_priority": "low",
            "complexity_score": 10,
            "estimated_effort_days": 5,
            "metrics": {"recipe_count": 1, "resource_count": 1, "custom_resources": 0},
            "challenges": [],
        },
    ]

    result = assessment._format_ai_cookbook_assessments(assessments)

    assert "cb1" in result
    assert "cb2" in result


def test_assess_complexity_with_ai_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """AI assessment exceptions should return formatted error."""
    monkeypatch.setattr(
        assessment,
        "_validate_assessment_inputs",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(assessment, "_is_ai_available", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        assessment,
        "_process_cookbook_assessment_with_ai",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad")),  # noqa: S7500
    )

    result = assessment.assess_chef_migration_complexity_with_ai("/tmp")

    assert "Error during" in result


def test_assess_single_cookbook_with_ai_no_ai_analysis(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Missing AI analysis should use rule-based effort calculation."""
    cookbook = tmp_path / "cb"
    cookbook.mkdir()

    monkeypatch.setattr(
        assessment,
        "_count_cookbook_artifacts",
        lambda *_args, **_kwargs: {
            "recipe_count": 8,
            "resource_count": 4,
            "custom_resources": 0,
            "ruby_blocks": 0,
            "template_count": 0,
            "file_count": 0,
        },
    )
    monkeypatch.setattr(
        assessment,
        "_analyse_recipe_complexity",
        lambda *_args, **_kwargs: {
            "resource_count": 4,
            "custom_resources": 0,
            "ruby_blocks": 0,
        },
    )
    monkeypatch.setattr(
        assessment, "_get_ai_cookbook_analysis", lambda *_args, **_kwargs: None
    )

    result = assessment._assess_single_cookbook_with_ai(
        cookbook, "anthropic", "key", "m", 0.1, 100
    )

    assert result["estimated_effort_days"] > 0
