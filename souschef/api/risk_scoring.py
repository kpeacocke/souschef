"""
Risk scoring engine for migration analytics.

This module provides a versioned risk model with:
- documented scoring inputs
- explainability payloads for each risk flag
- aggregation helpers by app/team/environment
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean

RISK_MODEL_VERSION = "2026-05-v1"

# Input documentation is kept alongside the model version so callers can surface
# exactly how scoring was computed for a given release.
RISK_INPUT_DOCUMENTATION: dict[str, str] = {
    "complexity_score": "Complexity score from 0-100.",
    "dependency_count": "Count of external dependencies used by the migration.",
    "custom_resource_count": "Count of bespoke/custom resources requiring translation.",
    "security_hotspots": "Count of known security hotspots in the source.",
    "test_coverage_percent": "Estimated test coverage percentage (0-100).",
    "manual_steps": "Count of manual migration steps still required.",
}

RISK_WEIGHTS: dict[str, float] = {
    "complexity_score": 0.24,
    "dependency_count": 0.16,
    "custom_resource_count": 0.2,
    "security_hotspots": 0.16,
    "test_coverage_percent": 0.14,
    "manual_steps": 0.1,
}


@dataclass(frozen=True)
class RiskScoringInput:
    """Structured risk scoring input payload."""

    item_id: str
    app: str
    team: str
    environment: str
    complexity_score: float
    dependency_count: int
    custom_resource_count: int
    security_hotspots: int
    test_coverage_percent: float
    manual_steps: int


@dataclass(frozen=True)
class RiskFlagExplanation:
    """Explainability payload for a single risk factor."""

    flag: str
    raw_value: float
    normalised_value: float
    weight: float
    contribution: float
    severity: str
    rationale: str


@dataclass(frozen=True)
class RiskScoreResult:
    """Versioned risk score output for an item."""

    item_id: str
    app: str
    team: str
    environment: str
    model_version: str
    total_score: float
    risk_level: str
    explainability: list[RiskFlagExplanation]


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a value into a bounded range."""
    return max(low, min(high, value))


def _severity_for_contribution(contribution: float) -> str:
    """Map contribution amount to severity."""
    if contribution >= 20:
        return "high"
    if contribution >= 10:
        return "medium"
    return "low"


def _risk_level_from_score(total_score: float) -> str:
    """Map numeric score to high/medium/low risk labels."""
    if total_score >= 70:
        return "high"
    if total_score >= 40:
        return "medium"
    return "low"


def _explanation(
    flag: str,
    raw_value: float,
    normalised_value: float,
    rationale: str,
) -> RiskFlagExplanation:
    """Create a single explainability object for a risk factor."""
    weight = RISK_WEIGHTS[flag]
    contribution = round(normalised_value * weight * 100.0, 2)
    return RiskFlagExplanation(
        flag=flag,
        raw_value=raw_value,
        normalised_value=normalised_value,
        weight=weight,
        contribution=contribution,
        severity=_severity_for_contribution(contribution),
        rationale=rationale,
    )


def score_risk(input_data: RiskScoringInput) -> RiskScoreResult:
    """Score a migration item and return versioned explainability output."""
    complexity = _clamp(input_data.complexity_score / 100.0, 0.0, 1.0)
    dependencies = _clamp(input_data.dependency_count / 20.0, 0.0, 1.0)
    custom_resources = _clamp(input_data.custom_resource_count / 10.0, 0.0, 1.0)
    hotspots = _clamp(input_data.security_hotspots / 5.0, 0.0, 1.0)
    coverage_gap = _clamp((100.0 - input_data.test_coverage_percent) / 100.0, 0.0, 1.0)
    manual_steps = _clamp(input_data.manual_steps / 10.0, 0.0, 1.0)

    explanations = [
        _explanation(
            flag="complexity_score",
            raw_value=input_data.complexity_score,
            normalised_value=complexity,
            rationale="Higher complexity increases migration uncertainty.",
        ),
        _explanation(
            flag="dependency_count",
            raw_value=float(input_data.dependency_count),
            normalised_value=dependencies,
            rationale="More dependencies increase breakage surface area.",
        ),
        _explanation(
            flag="custom_resource_count",
            raw_value=float(input_data.custom_resource_count),
            normalised_value=custom_resources,
            rationale="Custom resources require manual translation effort.",
        ),
        _explanation(
            flag="security_hotspots",
            raw_value=float(input_data.security_hotspots),
            normalised_value=hotspots,
            rationale="Known security hotspots raise implementation risk.",
        ),
        _explanation(
            flag="test_coverage_percent",
            raw_value=input_data.test_coverage_percent,
            normalised_value=coverage_gap,
            rationale=(
                "Lower test coverage reduces confidence in migration correctness."
            ),
        ),
        _explanation(
            flag="manual_steps",
            raw_value=float(input_data.manual_steps),
            normalised_value=manual_steps,
            rationale="Manual steps increase process and handoff risk.",
        ),
    ]

    total_score = round(sum(item.contribution for item in explanations), 2)
    return RiskScoreResult(
        item_id=input_data.item_id,
        app=input_data.app,
        team=input_data.team,
        environment=input_data.environment,
        model_version=RISK_MODEL_VERSION,
        total_score=total_score,
        risk_level=_risk_level_from_score(total_score),
        explainability=explanations,
    )


def aggregate_risk(
    results: list[RiskScoreResult],
    group_by: str,
) -> dict[str, dict[str, object]]:
    """Aggregate risk results by app, team, or environment."""
    if group_by not in {"app", "team", "environment"}:
        raise ValueError(f"Unsupported group_by value: {group_by}")

    grouped: dict[str, list[RiskScoreResult]] = {}
    for result in results:
        key = getattr(result, group_by)
        grouped.setdefault(key, []).append(result)

    aggregated: dict[str, dict[str, object]] = {}
    for key, items in grouped.items():
        scores = [item.total_score for item in items]
        levels = [item.risk_level for item in items]
        if "high" in levels:
            highest_risk = "high"
        elif "medium" in levels:
            highest_risk = "medium"
        else:
            highest_risk = "low"

        aggregated[key] = {
            "count": len(items),
            "average_score": round(mean(scores), 2),
            "highest_risk": highest_risk,
            "distribution": {
                "high": levels.count("high"),
                "medium": levels.count("medium"),
                "low": levels.count("low"),
            },
            "model_version": RISK_MODEL_VERSION,
        }

    return aggregated


def serialise_explainability(result: RiskScoreResult) -> list[dict[str, object]]:
    """Serialise explainability payload for API responses."""
    return [asdict(item) for item in result.explainability]
