"""
Time and cost estimation model for migration analytics.

Provides deterministic estimation with:
- tunable assumptions
- confidence ranges
- what-if parameter support
"""

from __future__ import annotations

from dataclasses import dataclass

ESTIMATION_MODEL_VERSION = "2026-05-v1"


@dataclass(frozen=True)
class EstimationAssumptions:
    """Tunable assumptions that drive estimation behaviour."""

    hourly_rate: float = 180.0
    base_hours_per_item: float = 3.5
    complexity_factor: float = 0.8
    manual_step_hours: float = 0.3
    risk_multipliers: dict[str, float] | None = None

    def resolved_risk_multipliers(self) -> dict[str, float]:
        """Return risk multipliers with defaults when omitted."""
        if self.risk_multipliers is None:
            return {"low": 1.0, "medium": 1.2, "high": 1.5}
        return self.risk_multipliers


@dataclass(frozen=True)
class WhatIfParameters:
    """What-if knobs for scenario analysis without changing base assumptions."""

    productivity_multiplier: float = 1.0
    automation_boost_percent: float = 0.0
    team_size: int = 1
    parallel_efficiency: float = 0.75


@dataclass(frozen=True)
class EstimationInput:
    """Input payload for migration effort and cost estimation."""

    project_id: str
    total_items: int
    average_complexity: float
    average_manual_steps: float
    risk_distribution: dict[str, int]


@dataclass(frozen=True)
class EstimationResult:
    """Output payload for effort, cost, and confidence bounds."""

    project_id: str
    model_version: str
    effort_hours: float
    estimated_duration_weeks: float
    cost_amount: float
    confidence_low_hours: float
    confidence_high_hours: float
    confidence_low_cost: float
    confidence_high_cost: float


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp numeric value to an inclusive range."""
    return max(low, min(high, value))


def _risk_weight(
    risk_distribution: dict[str, int],
    multipliers: dict[str, float],
) -> float:
    """Compute weighted risk multiplier for all inventory items."""
    total = max(sum(risk_distribution.values()), 1)
    weighted = 0.0
    for level in ("low", "medium", "high"):
        weighted += risk_distribution.get(level, 0) * multipliers.get(level, 1.0)
    return weighted / total


def _uncertainty_factor(total_items: int, risk_distribution: dict[str, int]) -> float:
    """Estimate confidence uncertainty from project size and risk mix."""
    total = max(total_items, 1)
    high_ratio = risk_distribution.get("high", 0) / total
    medium_ratio = risk_distribution.get("medium", 0) / total
    base = 0.08 + (high_ratio * 0.25) + (medium_ratio * 0.1)
    return _clamp(base, 0.08, 0.45)


def estimate_time_cost(
    input_data: EstimationInput,
    assumptions: EstimationAssumptions | None = None,
    what_if: WhatIfParameters | None = None,
) -> EstimationResult:
    """Estimate migration effort and cost with confidence ranges."""
    assumptions = assumptions or EstimationAssumptions()
    what_if = what_if or WhatIfParameters()

    if input_data.total_items <= 0:
        raise ValueError("total_items must be greater than zero")
    if what_if.productivity_multiplier <= 0:
        raise ValueError("productivity_multiplier must be greater than zero")
    if what_if.team_size <= 0:
        raise ValueError("team_size must be greater than zero")

    multipliers = assumptions.resolved_risk_multipliers()

    base_effort = input_data.total_items * assumptions.base_hours_per_item
    complexity_adjustment = (
        base_effort * _clamp(input_data.average_complexity / 100.0, 0.0, 1.0)
    ) * assumptions.complexity_factor
    manual_adjustment = (
        input_data.total_items
        * input_data.average_manual_steps
        * assumptions.manual_step_hours
    )

    risk_multiplier = _risk_weight(input_data.risk_distribution, multipliers)
    effort_hours = (
        base_effort + complexity_adjustment + manual_adjustment
    ) * risk_multiplier

    automation_factor = 1.0 - _clamp(what_if.automation_boost_percent / 100.0, 0.0, 0.8)
    effort_hours = effort_hours * automation_factor
    effort_hours = effort_hours / what_if.productivity_multiplier

    adjusted_parallel_capacity = max(
        1.0,
        what_if.team_size * _clamp(what_if.parallel_efficiency, 0.1, 1.0),
    )
    duration_weeks = effort_hours / (40.0 * adjusted_parallel_capacity)

    uncertainty = _uncertainty_factor(
        input_data.total_items,
        input_data.risk_distribution,
    )
    low_hours = effort_hours * (1.0 - uncertainty)
    high_hours = effort_hours * (1.0 + uncertainty)

    cost_amount = effort_hours * assumptions.hourly_rate
    low_cost = low_hours * assumptions.hourly_rate
    high_cost = high_hours * assumptions.hourly_rate

    return EstimationResult(
        project_id=input_data.project_id,
        model_version=ESTIMATION_MODEL_VERSION,
        effort_hours=round(effort_hours, 2),
        estimated_duration_weeks=round(duration_weeks, 2),
        cost_amount=round(cost_amount, 2),
        confidence_low_hours=round(low_hours, 2),
        confidence_high_hours=round(high_hours, 2),
        confidence_low_cost=round(low_cost, 2),
        confidence_high_cost=round(high_cost, 2),
    )
