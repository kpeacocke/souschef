"""Centralized metrics and effort calculation module for consistent time estimations."""

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

__all__ = [
    "ComplexityLevel",
    "EffortMetrics",
    "convert_days_to_hours",
    "convert_days_to_weeks",
    "convert_hours_to_days",
    "estimate_effort_for_complexity",
    "get_team_recommendation",
    "get_timeline_weeks",
]


class ComplexityLevel(str, Enum):
    """Standard complexity levels used across all components."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class EffortMetrics:
    """
    Centralized container for all effort estimates.

    Provides consistent representations across different formats:
    - Base unit: person-days (with decimal precision)
    - Derived: hours, weeks with consistent conversion factors
    - Ranges: For display purposes, converting days to week ranges

    Ensures all components (migration planning, dependency mapping,
    validation reports) use the same underlying numbers.
    """

    estimated_days: float
    """Base unit: person-days (e.g., 2.5, 5.0, 10.0)"""

    @property
    def estimated_hours(self) -> float:
        """Convert days to hours using standard 8-hour workday."""
        return self.estimated_days * 8

    @property
    def estimated_weeks_low(self) -> int:
        """Conservative estimate: assumes optimal parallelization."""
        return max(1, int(self.estimated_days / 7))

    @property
    def estimated_weeks_high(self) -> int:
        """Realistic estimate: assumes sequential/limited parallelization."""
        return max(1, int(self.estimated_days / 3.5))

    @property
    def estimated_weeks_range(self) -> str:
        """Human-readable week range (e.g., '2-4 weeks')."""
        low = self.estimated_weeks_low
        high = self.estimated_weeks_high
        if low == high:
            return f"{low} week{'s' if low != 1 else ''}"
        return f"{low}-{high} weeks"

    @property
    def estimated_days_formatted(self) -> str:
        """Formatted days with appropriate precision."""
        if self.estimated_days == int(self.estimated_days):
            return f"{int(self.estimated_days)} days"
        return f"{self.estimated_days:.1f} days"

    def __str__(self) -> str:
        """Return a string representation of effort metrics."""
        return f"{self.estimated_days_formatted} ({self.estimated_weeks_range})"


class TeamRecommendation(NamedTuple):
    """Team composition and timeline recommendation."""

    team_size: str
    """e.g., '1 developer + 1 reviewer'"""

    timeline_weeks: int
    """Recommended timeline in weeks"""

    description: str
    """Human-readable description of the recommendation"""


# Conversion constants - Single source of truth
HOURS_PER_WORKDAY = 8
DAYS_PER_WEEK = 7

# Complexity thresholds for automatic categorization
COMPLEXITY_THRESHOLD_LOW = 30
COMPLEXITY_THRESHOLD_HIGH = 70

# Effort multiplier per resource (base 1 resource = baseline effort)
EFFORT_MULTIPLIER_PER_RESOURCE = 0.125  # 0.125 days = 1 hour per resource


def convert_days_to_hours(days: float) -> float:
    """Convert person-days to hours using standard 8-hour workday."""
    return days * HOURS_PER_WORKDAY


def convert_hours_to_days(hours: float) -> float:
    """Convert hours to person-days using standard 8-hour workday."""
    return hours / HOURS_PER_WORKDAY


def convert_days_to_weeks(days: float, conservative: bool = False) -> int:
    """
    Convert days to weeks estimate.

    Args:
        days: Number of person-days
        conservative: If True, use realistic estimate (1 engineer, limited
            parallelization). If False, use optimistic estimate (full
            parallelization)

    Returns:
        Number of weeks (integer)

    """
    weeks = days / 3.5 if conservative else days / DAYS_PER_WEEK
    return max(1, int(weeks))


def estimate_effort_for_complexity(
    complexity_score: float, resource_count: int = 1
) -> EffortMetrics:
    """
    Estimate effort based on complexity score and resource count.

    Provides consistent effort estimation across all components.

    Formula:
    - Base effort: resource_count * 0.125 days per recipe/resource
    - Complexity multiplier: 1.0 + (complexity_score / 100)
    - Final effort: base_effort * complexity_multiplier

    Args:
        complexity_score: Score from 0-100 (0=simple, 100=complex)
        resource_count: Number of resources to migrate (recipes, templates, etc.)

    Returns:
        EffortMetrics object with all representations

    """
    base_effort = resource_count * EFFORT_MULTIPLIER_PER_RESOURCE
    complexity_multiplier = 1.0 + (complexity_score / 100)
    estimated_days = base_effort * complexity_multiplier

    return EffortMetrics(estimated_days=round(estimated_days, 1))


def categorize_complexity(score: float) -> ComplexityLevel:
    """
    Categorize complexity score into standard levels.

    Consistent thresholds across all components:
    - Low: 0-29
    - Medium: 30-69
    - High: 70-100

    Args:
        score: Complexity score from 0-100

    Returns:
        ComplexityLevel enum value

    """
    if score < COMPLEXITY_THRESHOLD_LOW:
        return ComplexityLevel.LOW
    elif score < COMPLEXITY_THRESHOLD_HIGH:
        return ComplexityLevel.MEDIUM
    else:
        return ComplexityLevel.HIGH


def get_team_recommendation(total_effort_days: float) -> TeamRecommendation:
    """
    Get team composition and timeline recommendation based on total effort.

    Consistent recommendations across all components.

    Args:
        total_effort_days: Total person-days of effort

    Returns:
        TeamRecommendation with team size and timeline

    """
    if total_effort_days < 20:
        return TeamRecommendation(
            team_size="1 developer + 1 reviewer",
            timeline_weeks=4,
            description="Single developer with oversight",
        )
    elif total_effort_days < 50:
        return TeamRecommendation(
            team_size="2 developers + 1 senior reviewer",
            timeline_weeks=6,
            description="Small dedicated team",
        )
    else:
        return TeamRecommendation(
            team_size="3-4 developers + 1 tech lead + 1 architect",
            timeline_weeks=10,
            description="Large dedicated migration team",
        )


def get_timeline_weeks(total_effort_days: float, strategy: str = "phased") -> int:
    """
    Calculate recommended timeline in weeks based on effort and strategy.

    Consistent timeline calculation across planning, dependency mapping, and reports.

    Args:
        total_effort_days: Total person-days estimated
        strategy: Migration strategy ('phased', 'big_bang', 'parallel')

    Returns:
        Recommended timeline in weeks

    """
    # Base calculation: distribute effort across team capacity
    # Assume 3-5 person-days of output per week with normal team capacity
    base_weeks = max(2, int(total_effort_days / 4.5))

    # Apply strategy adjustments
    if strategy == "phased":
        # Phased adds overhead for testing between phases
        return int(base_weeks * 1.1)
    elif strategy == "big_bang":
        # Big bang is faster but riskier
        return int(base_weeks * 0.9)
    else:  # parallel
        # Parallel has some overhead for coordination
        return int(base_weeks * 1.05)


def validate_metrics_consistency(
    days: float, weeks: str, hours: float, complexity: str
) -> tuple[bool, list[str]]:
    """
    Validate that different metric representations are consistent.

    Used for validation reports to catch contradictions.

    Args:
        days: Days estimate
        weeks: Weeks range string (e.g., "2-4 weeks")
        hours: Hours estimate
        complexity: Complexity level string

    Returns:
        Tuple of (is_valid, list_of_errors)

    """
    errors = []

    # Check hours consistency
    expected_hours = days * 8
    if abs(hours - expected_hours) > 1.0:  # Allow 1 hour tolerance
        errors.append(
            f"Hours mismatch: {hours:.1f} hours but {days} days = "
            f"{expected_hours:.1f} hours"
        )

    # Check weeks consistency (loose check due to range)
    # Valid formats: "1 week", "1-2 weeks"
    if "week" not in weeks.lower():
        errors.append(f"Invalid weeks format: {weeks}")
    elif "-" in weeks:
        # Range format: "X-Y weeks"
        try:
            parts = weeks.replace(" weeks", "").replace(" week", "").split("-")
            week_min = int(parts[0].strip())
            week_max = int(parts[1].strip())
            expected_weeks = int(days / 3.5)  # Conservative estimate

            if not (week_min <= expected_weeks <= week_max + 1):
                errors.append(
                    f"Weeks mismatch: {weeks} but {days} days should be "
                    f"approximately {expected_weeks} weeks"
                )
        except (ValueError, IndexError):
            errors.append(f"Invalid weeks format: {weeks}")
    else:
        # Single week format: "X week" or "X weeks"
        try:
            num = int(weeks.replace(" weeks", "").replace(" week", "").strip())
            expected_weeks = int(days / 3.5)
            if num != expected_weeks and abs(num - expected_weeks) > 2:
                errors.append(
                    f"Weeks mismatch: {weeks} but {days} days should be "
                    f"approximately {expected_weeks} weeks"
                )
        except ValueError:
            errors.append(f"Invalid weeks format: {weeks}")

    # Check complexity is valid
    valid_complexities = {level.value for level in ComplexityLevel}
    if complexity.lower() not in valid_complexities:
        errors.append(f"Invalid complexity level: {complexity}")

    return len(errors) == 0, errors
