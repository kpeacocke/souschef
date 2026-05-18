"""Unit tests for API risk scoring engine."""

from __future__ import annotations

import pytest

from souschef.api.risk_scoring import (
    RISK_INPUT_DOCUMENTATION,
    RISK_MODEL_VERSION,
    RiskScoringInput,
    aggregate_risk,
    score_risk,
    serialise_explainability,
)


def _input(
    *,
    item_id: str,
    app: str = "payments",
    team: str = "platform",
    environment: str = "prod",
    complexity_score: float = 50.0,
    dependency_count: int = 5,
    custom_resource_count: int = 2,
    security_hotspots: int = 1,
    test_coverage_percent: float = 80.0,
    manual_steps: int = 2,
) -> RiskScoringInput:
    """Build a standard scoring payload for tests."""
    return RiskScoringInput(
        item_id=item_id,
        app=app,
        team=team,
        environment=environment,
        complexity_score=complexity_score,
        dependency_count=dependency_count,
        custom_resource_count=custom_resource_count,
        security_hotspots=security_hotspots,
        test_coverage_percent=test_coverage_percent,
        manual_steps=manual_steps,
    )


def test_score_risk_includes_versioned_explainability_payload() -> None:
    """Risk scoring should return a model-versioned explainability payload."""
    result = score_risk(_input(item_id="item-1"))

    assert result.model_version == RISK_MODEL_VERSION
    assert len(result.explainability) == len(RISK_INPUT_DOCUMENTATION)
    assert {item.flag for item in result.explainability} == set(
        RISK_INPUT_DOCUMENTATION
    )

    serialised = serialise_explainability(result)
    assert all("contribution" in row for row in serialised)
    assert all("rationale" in row for row in serialised)


def test_score_risk_high_case_has_high_level_and_flags() -> None:
    """Very risky payload should be classified as high risk."""
    result = score_risk(
        _input(
            item_id="item-high",
            complexity_score=95.0,
            dependency_count=24,
            custom_resource_count=11,
            security_hotspots=8,
            test_coverage_percent=10.0,
            manual_steps=12,
        )
    )

    assert result.risk_level == "high"
    assert result.total_score >= 70
    assert any(flag.severity == "high" for flag in result.explainability)


def test_aggregate_risk_by_dimensions() -> None:
    """Risk aggregation should produce summaries by app/team/environment."""
    results = [
        score_risk(
            _input(item_id="a1", app="payments", team="platform", environment="prod")
        ),
        score_risk(
            _input(item_id="a2", app="payments", team="platform", environment="stage")
        ),
        score_risk(
            _input(item_id="a3", app="identity", team="auth", environment="prod")
        ),
    ]

    by_app = aggregate_risk(results, group_by="app")
    by_team = aggregate_risk(results, group_by="team")
    by_env = aggregate_risk(results, group_by="environment")

    assert by_app["payments"]["count"] == 2
    assert by_team["platform"]["count"] == 2
    assert by_env["prod"]["count"] == 2


def test_aggregate_risk_invalid_group_by_raises() -> None:
    """Unsupported grouping dimension should raise ValueError."""
    results = [score_risk(_input(item_id="single"))]
    with pytest.raises(ValueError):
        aggregate_risk(results, group_by="service")
