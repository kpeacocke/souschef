"""
# Metrics Consistency Guide

## Overview

This guide explains how to use the centralized metrics module to ensure consistency across migration planning, dependency mapping, and validation reports.

## Problem Solved

Previously, different components used different time representations:
- Days with decimals vs. week ranges vs. hours
- Different complexity thresholds (30/70 vs. other values)
- Inconsistent multipliers for effort calculation
- Different conversions between formats

This caused contradictions like:
- Planning said "5 days" but reports said "2-3 weeks"
- Dependency mapping calculated "12 days" but validation showed "1 week"
- Effort estimates varied depending on which component calculated them

## Solution: Single Source of Truth

The `souschef/core/metrics.py` module provides:

1. **EffortMetrics class** - Container holding all representations
2. **Conversion functions** - Consistent day ↔ hours ↔ weeks conversions
3. **Categorization** - Standard complexity levels (low/medium/high)
4. **Recommendations** - Team size and timeline based on effort
5. **Validation** - Check for contradictions in metrics

## Usage Examples

### For Migration Planning

```python
from souschef.core.metrics import estimate_effort_for_complexity, get_timeline_weeks

# Calculate effort from complexity
complexity_score = 65  # 0-100
recipe_count = 12
metrics = estimate_effort_for_complexity(complexity_score, recipe_count)

# Output all formats automatically
print(f"Effort: {metrics}")  # "1.5 days (0-1 weeks)" or custom format
print(f"Days: {metrics.estimated_days_formatted}")  # "1.5 days"
print(f"Weeks: {metrics.estimated_weeks_range}")  # "0-1 weeks"
print(f"Hours: {metrics.estimated_hours}")  # 12.0

# Get timeline recommendation
timeline = get_timeline_weeks(metrics.estimated_days, strategy="phased")
```

### For Dependency Mapping

```python
from souschef.core.metrics import estimate_effort_for_complexity, categorize_complexity

# Analyze dependencies with consistent effort
effort = estimate_effort_for_complexity(complexity=75, resource_count=20)
priority = categorize_complexity(75)

# Display in dependency mapping UI
print(f"Priority: {priority.value}")  # "high"
print(f"Estimated: {effort.estimated_weeks_range}")  # "4-8 weeks"

# Migration order based on consistent metrics
dependencies = analyze_dependencies(cookbook)
total_effort = sum(estimate_effort_for_complexity(c.score, c.resources)
                   for c in dependencies)
```

### For Validation Reports

```python
from souschef.core.metrics import validate_metrics_consistency

# Validate that metrics don't contradict
is_valid, errors = validate_metrics_consistency(
    days=5.0,
    weeks="1-2 weeks",
    hours=40.0,
    complexity="medium"
)

if not is_valid:
    for error in errors:
        report.add_warning(error)
```

## Key Constants (Single Source of Truth)

```python
HOURS_PER_WORKDAY = 8           # Standard workday
DAYS_PER_WEEK = 7               # Calendar days per week
COMPLEXITY_THRESHOLD_LOW = 30   # < 30: low complexity
COMPLEXITY_THRESHOLD_HIGH = 70  # >= 70: high complexity
EFFORT_MULTIPLIER_PER_RESOURCE = 0.125  # 1 resource = 0.125 days (1 hour)
```

## Implementation Checklist

To refactor existing components for consistency:

### 1. **Assessment Module** (`assessment.py`)
   - [ ] Replace hardcoded week ranges with `estimated_weeks_range`
   - [ ] Use `EffortMetrics` in assessment dicts
   - [ ] Use `categorize_complexity()` for priority determination
   - [ ] Replace `"Estimated Effort: X days"` with `metrics.estimated_days_formatted`

### 2. **Deployment Module** (`deployment.py`)
   - [ ] Replace `_assess_complexity_from_resource_count()` with `estimate_effort_for_complexity()`
   - [ ] Remove hardcoded ranges ("1-2 weeks", "2-3 weeks", etc.)
   - [ ] Use `get_team_recommendation()` for team sizing

### 3. **UI Components** (`cookbook_analysis.py`, `validation_reports.py`)
   - [ ] Use `EffortMetrics` throughout
   - [ ] Display consistent formats: days + weeks range
   - [ ] Validate metrics before displaying with `validate_metrics_consistency()`

### 4. **Playbook Converter** (`playbook.py`)
   - [ ] Use `estimate_effort_for_complexity()` for project effort
   - [ ] Replace `project_effort_days` calculations with centralized function

## Consistency Rules

1. **All effort calculations** → Use `estimate_effort_for_complexity()`
2. **All complexity categorization** → Use `categorize_complexity()`
3. **All time conversions** → Use conversion functions (not manual math)
4. **All team recommendations** → Use `get_team_recommendation()`
5. **All timelines** → Use `get_timeline_weeks()` with strategy parameter
6. **All reports** → Validate with `validate_metrics_consistency()`

## Why This Maintains Quality

- **Single formula** ensures mathematical consistency
- **Validated thresholds** prevent arbitrary categorization
- **Explicit conversions** make assumptions clear (8-hour day, etc.)
- **Type-safe** EffortMetrics prevents mixing units
- **Testable** each function can be independently verified
- **Transparent** users see all representations (days + weeks + hours)
- **Flexible** supports different strategies (phased, big-bang, parallel)

## Testing

All components should include tests validating:

```python
from souschef.core.metrics import estimate_effort_for_complexity

def test_consistency():
    """Validate metrics don't contradict."""
    effort = estimate_effort_for_complexity(complexity=50, resources=10)

    # All these should be consistent
    assert effort.estimated_hours == effort.estimated_days * 8
    assert effort.estimated_weeks_low <= effort.estimated_weeks_high
    assert "weeks" in effort.estimated_weeks_range
```

## Migration Path

1. **Phase 1**: Create metrics module (DONE)
2. **Phase 2**: Refactor assessment.py to use centralized metrics
3. **Phase 3**: Refactor deployment.py for consistency
4. **Phase 4**: Update UI components to validate and display consistently
5. **Phase 5**: Add validation tests ensuring no contradictions

## Benefits

- **No more contradictions** between planning and reports
- **Easier maintenance** - change one formula, all components update
- **Better UX** - consistent language and formats
- **Transparent math** - users see conversion logic
- **Quality preserved** - detailed metrics still available
- **Performance** - centralized caching possible if needed
