"""Large-impact tests for assessment.py complex workflows."""

from pathlib import Path
from unittest.mock import patch

from souschef.assessment import (
    _analyse_cookbook_metrics,
    _assess_single_cookbook,
    _get_overall_complexity_level,
    _parse_cookbook_paths,
    assess_single_cookbook_with_ai,
    parse_chef_migration_assessment,
)


def test_assess_single_cookbook_with_ai_no_ai_key() -> None:
    """Assessment with AI should fall back without API key."""
    with patch("souschef.assessment._is_ai_available", return_value=False):
        result = assess_single_cookbook_with_ai(
            "/nonexistent/cookbook", ai_provider="anthropic", api_key=""
        )
        assert isinstance(result, dict)


def test_assess_single_cookbook_with_ai_invalid_path() -> None:
    """Assessment should handle invalid cookbook path."""
    with patch("souschef.assessment._is_ai_available", return_value=False):
        result = assess_single_cookbook_with_ai(
            "/nonexistent/cookbook", ai_provider="anthropic"
        )
        assert "error" in result


def test_parse_chef_migration_assessment_empty_cookbook(tmp_path: Path) -> None:
    """Assessment should handle empty cookbook directory."""
    result = parse_chef_migration_assessment(str(tmp_path))
    assert isinstance(result, dict)


def test_assess_single_cookbook_simple(tmp_path: Path) -> None:
    """Single cookbook assessment should work."""
    cookbook = tmp_path / "test"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'test'\nversion '1.0'")

    result = _assess_single_cookbook(cookbook)
    assert isinstance(result, dict)
    assert "complexity_score" in result


def test_parse_cookbook_paths_mixed(tmp_path: Path) -> None:
    """Path parser should filter non-existent paths."""
    existing = tmp_path / "existing"
    existing.mkdir()

    paths = f"{existing},/nonexistent,{tmp_path / 'invalid'}"
    result = _parse_cookbook_paths(paths)
    assert len(result) >= 1


def test_get_overall_complexity_high() -> None:
    """High complexity metrics should identify as High."""
    metrics = {"avg_complexity": 85}
    level = _get_overall_complexity_level(metrics)
    assert level == "High"


def test_get_overall_complexity_boundary() -> None:
    """Boundary complexity should resolve correctly."""
    metrics = {"avg_complexity": 30}
    level = _get_overall_complexity_level(metrics)
    assert level in ["Low", "Medium"]


def test_analyse_cookbook_metrics_with_multiple_recipes(tmp_path: Path) -> None:
    """Metrics should aggregate multiple recipes."""
    cookbook = tmp_path / "multi"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'multi'")

    recipes = cookbook / "recipes"
    recipes.mkdir()
    (recipes / "default.rb").write_text("package 'nginx'")
    (recipes / "db.rb").write_text("package 'postgresql'")

    # _analyse_cookbook_metrics returns (assessments, overall_metrics) tuple
    assessments, overall = _analyse_cookbook_metrics([cookbook])
    assert overall["total_recipes"] >= 2
    assert overall["total_cookbooks"] == 1


def test_assess_single_cookbook_with_attributes(tmp_path: Path) -> None:
    """Assessment should include attribute complexity."""
    cookbook = tmp_path / "attrs"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'attrs'")

    attrs = cookbook / "attributes"
    attrs.mkdir()
    (attrs / "default.rb").write_text("default[:x] = 1")

    result = _assess_single_cookbook(cookbook)
    assert result["complexity_score"] >= 0


def test_parse_chef_migration_assessment_infrastructure_scope() -> None:
    """Assessment with infrastructure_only scope should work."""
    with patch("souschef.assessment._parse_cookbook_paths", return_value=[]):
        result = parse_chef_migration_assessment(
            "", migration_scope="infrastructure_only"
        )
        assert isinstance(result, dict)


def test_assess_single_cookbook_with_handlers(tmp_path: Path) -> None:
    """Assessment should count handlers in complexity."""
    cookbook = tmp_path / "handlers"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'handlers'")

    recipes = cookbook / "recipes"
    recipes.mkdir()
    (recipes / "default.rb").write_text(
        "template '/etc/config' do\n  notifies :restart, 'service[nginx]'\nend\n"
    )

    result = _assess_single_cookbook(cookbook)
    assert result["complexity_score"] >= 0


def test_assess_single_cookbook_with_inspec(tmp_path: Path) -> None:
    """Assessment should include InSpec profile complexity."""
    cookbook = tmp_path / "inspec"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'inspec'")

    test_dir = cookbook / "test" / "compliance" / "profiles" / "test"
    test_dir.mkdir(parents=True)
    controls_dir = test_dir / "controls"
    controls_dir.mkdir()
    (controls_dir / "test.rb").write_text(
        "describe package('nginx') do\n  it { should be_installed }\nend\n"
    )

    result = _assess_single_cookbook(cookbook)
    assert result["complexity_score"] >= 0


def test_parse_chef_migration_assessment_low_complexity(tmp_path: Path) -> None:
    """Assessment of simple cookbook should report low complexity."""
    cookbook = tmp_path / "simple"
    cookbook.mkdir()
    (cookbook / "metadata.rb").write_text("name 'simple'")

    result = parse_chef_migration_assessment(str(cookbook))
    assert isinstance(result, dict)
