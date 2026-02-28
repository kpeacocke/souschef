"""Tests for server formatting and recommendation helpers."""

from souschef.server import (
    _analyse_structure_recommendations,
    _analyse_usage_pattern_recommendations,
    _format_databag_structure,
    _format_environment_structure,
    _format_environment_usage_patterns,
    _format_usage_patterns,
    _generate_environment_migration_recommendations,
)


def test_analyse_usage_pattern_recommendations_empty() -> None:
    """No recommendations for empty usage patterns."""
    assert _analyse_usage_pattern_recommendations([]) == []


def test_analyse_usage_pattern_recommendations_with_patterns() -> None:
    """Recommendations include environment and conditional usage."""
    patterns = [
        {"type": "node.chef_environment"},
        {"type": "environment conditional"},
    ]
    recs = _analyse_usage_pattern_recommendations(patterns)

    assert any("environment references" in rec for rec in recs)
    assert any("conditional" in rec for rec in recs)


def test_analyse_structure_recommendations_empty() -> None:
    """No recommendations when structure is empty."""
    assert _analyse_structure_recommendations({}) == []
    assert _analyse_structure_recommendations({"total_environments": 0}) == []


def test_analyse_structure_recommendations_complex() -> None:
    """Recommendations include note for complex environments."""
    structure = {
        "total_environments": 2,
        "environments": {
            "prod": {
                "default_attributes_count": 6,
                "override_attributes_count": 6,
            },
            "dev": {"default_attributes_count": 1, "override_attributes_count": 1},
        },
    }

    recs = _analyse_structure_recommendations(structure)

    assert any("Convert 2 Chef environments" in rec for rec in recs)
    assert any("split" in rec for rec in recs)


def test_generate_environment_migration_recommendations_combines() -> None:
    """Generated recommendations include general guidance."""
    usage_patterns = [{"type": "node.chef_environment"}]
    env_structure = {"total_environments": 1, "environments": {}}

    result = _generate_environment_migration_recommendations(
        usage_patterns, env_structure
    )

    assert "environment references" in result
    assert "Ansible groups" in result


def test_format_environment_usage_patterns_empty() -> None:
    """Formatting returns default message for empty patterns."""
    result = _format_environment_usage_patterns([])

    assert "No environment usage patterns found" in result


def test_format_environment_usage_patterns_with_errors() -> None:
    """Formatting includes error entries and env names."""
    patterns = [
        {"file": "a.rb", "error": "read failed"},
        {
            "file": "b.rb",
            "line": 10,
            "type": "environment declaration",
            "environment_name": "prod",
        },
    ]

    result = _format_environment_usage_patterns(patterns)

    assert "a.rb" in result
    assert "read failed" in result
    assert "prod" in result


def test_format_environment_usage_patterns_limit() -> None:
    """Formatting shows more patterns message when over limit."""
    patterns = [
        {"file": "f.rb", "line": i, "type": "node.chef_environment"} for i in range(20)
    ]

    result = _format_environment_usage_patterns(patterns)

    assert "more patterns" in result


def test_format_environment_structure_empty() -> None:
    """Formatting returns default message for empty structure."""
    result = _format_environment_structure({})

    assert "No environment structure" in result


def test_format_environment_structure_with_details() -> None:
    """Formatting includes summary and environment details."""
    structure = {
        "total_environments": 9,
        "environments": {
            "prod": {
                "default_attributes_count": 1,
                "override_attributes_count": 0,
                "cookbook_constraints_count": 1,
            },
            **{
                f"env{i}": {
                    "default_attributes_count": 0,
                    "override_attributes_count": 0,
                    "cookbook_constraints_count": 0,
                }
                for i in range(8)
            },
        },
    }

    result = _format_environment_structure(structure)

    assert "Total environments" in result
    assert "Environment Details" in result
    assert "more environments" in result


def test_format_usage_patterns_databags() -> None:
    """Formatting includes more patterns message for data bag usage."""
    patterns = [
        {"file": "f.rb", "line": i, "type": "data_bag()", "databag_name": "bag"}
        for i in range(12)
    ]

    result = _format_usage_patterns(patterns)

    assert "data_bag()" in result
    assert "more patterns" in result


def test_format_databag_structure_empty() -> None:
    """Formatting returns default message for empty structure."""
    result = _format_databag_structure({})

    assert "No data bag structure" in result
