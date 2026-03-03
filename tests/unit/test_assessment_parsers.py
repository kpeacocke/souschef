"""Targeted tests for assessment parsing helpers."""

from pathlib import Path

from souschef.assessment import (
    _calculate_complexity_score,
    _determine_migration_priority,
    _get_metadata_content,
    _get_recipe_content_sample,
    _identify_migration_challenges,
    _is_ai_available,
    _parse_berksfile,
    _parse_chefignore,
    _parse_metadata_file,
    _parse_thorfile,
)


def test_parse_berksfile_missing(tmp_path: Path) -> None:
    """Missing Berksfile should return empty dependency data."""
    cookbook_dir = tmp_path / "cookbook"
    cookbook_dir.mkdir()

    result = _parse_berksfile(cookbook_dir)
    assert result["dependencies"] == []
    assert result["complexity"] == 0


def test_parse_berksfile_with_sources(tmp_path: Path) -> None:
    """Berksfile with git and path sources should increase complexity."""
    cookbook_dir = tmp_path / "cookbook"
    cookbook_dir.mkdir()
    berksfile = cookbook_dir / "Berksfile"
    berksfile.write_text(
        "cookbook 'nginx'\n"
        "cookbook 'myapp', git: 'https://example.com/repo.git'\n"
        "cookbook 'local', path: './cookbooks/local'\n"
    )

    result = _parse_berksfile(cookbook_dir)
    assert "nginx" in result["dependencies"]
    assert result["has_git_sources"] is True
    assert result["has_path_sources"] is True
    assert result["complexity"] > 0


def test_parse_chefignore_patterns(tmp_path: Path) -> None:
    """Chefignore patterns should be extracted and counted."""
    cookbook_dir = tmp_path / "cookbook"
    cookbook_dir.mkdir()
    chefignore = cookbook_dir / "chefignore"
    chefignore.write_text("# comment\ntmp/*\nvendor/\ncache?\n")

    result = _parse_chefignore(cookbook_dir)
    assert result["pattern_count"] == 3
    assert result["has_wildcards"] is True
    assert "tmp/*" in result["patterns"]


def test_parse_thorfile_tasks(tmp_path: Path) -> None:
    """Thorfile should report tasks and methods."""
    cookbook_dir = tmp_path / "cookbook"
    cookbook_dir.mkdir()
    thorfile = cookbook_dir / "Thorfile"
    thorfile.write_text("desc 'Build'\ndef build\nend\n")

    result = _parse_thorfile(cookbook_dir)
    assert result["tasks"] == 1
    assert result["methods"] == 1
    assert result["has_tasks"] is True


def test_parse_metadata_file_content(tmp_path: Path) -> None:
    """Metadata parsing should capture dependencies and supports."""
    cookbook_dir = tmp_path / "cookbook"
    cookbook_dir.mkdir()
    metadata = cookbook_dir / "metadata.rb"
    metadata.write_text(
        "name 'test'\n"
        "version '1.2.3'\n"
        "depends 'nginx'\n"
        "supports 'ubuntu'\n"
        "recipe 'default', 'Default recipe'\n"
        "attribute 'port', display_name: 'Port'\n"
    )

    result = _parse_metadata_file(cookbook_dir)
    assert result["name"] == "test"
    assert result["version"] == "1.2.3"
    assert "nginx" in result["dependencies"]
    assert "ubuntu" in result["supports"]
    assert result["complexity"] > 0


def test_calculate_complexity_score() -> None:
    """Complexity score should aggregate metrics."""
    metrics = {
        "recipe_count": 5,
        "resource_count": 20,
        "custom_resources": 1,
        "ruby_blocks": 2,
        "template_count": 3,
        "file_count": 4,
    }
    score = _calculate_complexity_score(metrics)
    assert score > 0


def test_identify_migration_challenges() -> None:
    """Challenges should reflect custom resources, Ruby blocks, and high complexity."""
    metrics = {
        "custom_resources": 2,
        "ruby_blocks": 6,
    }
    challenges = _identify_migration_challenges(metrics, complexity_score=80)
    assert len(challenges) == 3
    assert any("custom resources" in c for c in challenges)
    assert any("Ruby blocks" in c for c in challenges)
    assert any("High complexity" in c for c in challenges)


def test_determine_migration_priority() -> None:
    """Priority should map to complexity ranges."""
    assert _determine_migration_priority(10) == "low"
    assert _determine_migration_priority(50) == "medium"
    assert _determine_migration_priority(90) == "high"


def test_get_recipe_content_sample_no_recipes(tmp_path: Path) -> None:
    """Recipe sample should report missing recipes directory."""
    cookbook_dir = tmp_path / "cookbook"
    cookbook_dir.mkdir()

    result = _get_recipe_content_sample(cookbook_dir)
    assert "recipes" in result.lower()


def test_get_metadata_content_missing(tmp_path: Path) -> None:
    """Metadata content should report missing metadata.rb."""
    cookbook_dir = tmp_path / "cookbook"
    cookbook_dir.mkdir()

    result = _get_metadata_content(cookbook_dir)
    assert "metadata" in result.lower()


def test_is_ai_available_requires_key() -> None:
    """AI availability should be false without an API key."""
    assert _is_ai_available("anthropic", "") is False
