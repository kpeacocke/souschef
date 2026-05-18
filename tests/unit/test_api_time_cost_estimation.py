"""Unit tests for time/cost estimation model."""

from __future__ import annotations

import pytest

from souschef.api.time_cost_estimation import (
    ESTIMATION_MODEL_VERSION,
    EstimationAssumptions,
    EstimationInput,
    WhatIfParameters,
    estimate_time_cost,
)


def _input() -> EstimationInput:
    """Create deterministic baseline input payload."""
    return EstimationInput(
        project_id="proj-1",
        total_items=20,
        average_complexity=60.0,
        average_manual_steps=2.0,
        risk_distribution={"low": 8, "medium": 8, "high": 4},
    )


def test_estimate_time_cost_deterministic_baseline() -> None:
    """Estimator should produce deterministic values for a fixed scenario."""
    result = estimate_time_cost(_input())

    assert result.model_version == ESTIMATION_MODEL_VERSION
    assert result.effort_hours == pytest.approx(136.41, rel=1e-3)
    assert result.cost_amount == pytest.approx(24553.8, rel=1e-3)
    assert (
        result.confidence_low_hours < result.effort_hours < result.confidence_high_hours
    )


def test_estimate_time_cost_supports_what_if_parameters() -> None:
    """What-if automation and productivity should reduce effort and cost."""
    baseline = estimate_time_cost(_input())
    scenario = estimate_time_cost(
        _input(),
        what_if=WhatIfParameters(
            productivity_multiplier=1.2,
            automation_boost_percent=15.0,
            team_size=2,
            parallel_efficiency=0.8,
        ),
    )

    assert scenario.effort_hours < baseline.effort_hours
    assert scenario.cost_amount < baseline.cost_amount
    assert scenario.estimated_duration_weeks < baseline.estimated_duration_weeks


def test_estimate_time_cost_uses_custom_assumptions() -> None:
    """Assumption tuning should materially affect estimate output."""
    default_result = estimate_time_cost(_input())
    custom_result = estimate_time_cost(
        _input(),
        assumptions=EstimationAssumptions(
            hourly_rate=240.0,
            base_hours_per_item=4.0,
            complexity_factor=1.0,
            manual_step_hours=0.4,
            risk_multipliers={"low": 1.0, "medium": 1.25, "high": 1.6},
        ),
    )

    assert custom_result.effort_hours > default_result.effort_hours
    assert custom_result.cost_amount > default_result.cost_amount


def test_estimate_time_cost_validates_inputs() -> None:
    """Invalid scenario parameters should raise clear validation errors."""
    with pytest.raises(ValueError):
        estimate_time_cost(
            EstimationInput(
                project_id="bad",
                total_items=0,
                average_complexity=50.0,
                average_manual_steps=1.0,
                risk_distribution={"low": 1},
            )
        )

    with pytest.raises(ValueError):
        estimate_time_cost(
            _input(), what_if=WhatIfParameters(productivity_multiplier=0.0)
        )
