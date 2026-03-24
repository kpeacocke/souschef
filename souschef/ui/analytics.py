"""
Analytics tracking for migration operations and UI interactions.

Tracks conversion success rates, patterns, timings, and user interactions
to power smart recommendations and identify risky conversions.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

LOGGER = logging.getLogger(__name__)

ANALYTICS_DIR = Path.home() / ".souschef" / "analytics"
ANALYTICS_EVENTS_FILE = ANALYTICS_DIR / "events.jsonl"
ANALYTICS_PATTERNS_FILE = ANALYTICS_DIR / "patterns.json"


def _ensure_analytics_dir() -> None:
    """Ensure analytics directory exists."""
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)


def track_event(
    event_type: str,
    tool: str,
    status: str,
    duration_seconds: float | None = None,
    resource_count: int | None = None,
    pattern: str | None = None,
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Track a conversion/operation event for analytics.

    Args:
        event_type: Type of event ('conversion', 'validation', 'recommendation', etc.)
        tool: Tool used (Chef, Puppet, PowerShell, Salt, Bash)
        status: Result status ('success', 'partial_success', 'failure')
        duration_seconds: How long the operation took
        resource_count: Number of resources processed
        pattern: Specific pattern/construct detected
        error_message: Error message if failed
        metadata: Additional context

    """
    _ensure_analytics_dir()

    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "tool": tool,
        "status": status,
        "duration_seconds": duration_seconds,
        "resource_count": resource_count,
        "pattern": pattern,
        "error_message": error_message,
        **(metadata or {}),
    }

    try:
        with ANALYTICS_EVENTS_FILE.open("a") as f:
            f.write(json.dumps(event) + "\n")
    except OSError as e:
        LOGGER.warning(f"Could not write analytics event: {e}")


def get_conversion_stats(tool: str | None = None) -> dict[str, Any]:
    """
    Get conversion statistics for a tool.

    Args:
        tool: Tool name to filter by, or None for all tools.

    Returns:
        Dictionary with success_rate, total_conversions, avg_duration, common_patterns.

    """
    _ensure_analytics_dir()

    if not ANALYTICS_EVENTS_FILE.exists():
        return {
            "success_rate": 0.0,
            "total_conversions": 0,
            "avg_duration": 0.0,
            "common_patterns": [],
        }

    conversions = {"success": 0, "partial_success": 0, "failure": 0, "total": 0}
    durations: list[float] = []
    patterns: dict[str, int] = {}

    try:
        with ANALYTICS_EVENTS_FILE.open() as f:
            for line in f:
                try:
                    event = json.loads(line)
                    if event.get("event_type") != "conversion":
                        continue
                    if tool and event.get("tool") != tool:
                        continue

                    conversions["total"] += 1
                    status = event.get("status", "unknown")
                    if status in conversions:
                        conversions[status] += 1

                    if event.get("duration_seconds"):
                        durations.append(event["duration_seconds"])

                    if event.get("pattern"):
                        pattern_key = event["pattern"]
                        patterns[pattern_key] = patterns.get(pattern_key, 0) + 1
                except json.JSONDecodeError:
                    continue
    except OSError as e:
        LOGGER.warning(f"Could not read analytics: {e}")

    success_count = conversions["success"] + conversions["partial_success"]
    success_rate = (
        (success_count / conversions["total"] * 100) if conversions["total"] > 0 else 0
    )
    avg_duration = (sum(durations) / len(durations)) if durations else 0.0

    # Top 5 patterns
    top_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "success_rate": round(success_rate, 1),
        "total_conversions": conversions["total"],
        "successful_conversions": success_count,
        "failed_conversions": conversions["failure"],
        "avg_duration": round(avg_duration, 2),
        "common_patterns": [{"pattern": p, "count": c} for p, c in top_patterns],
    }


def get_pattern_risk_level(tool: str, pattern: str) -> str:
    """
    Get risk level for a specific pattern based on historical data.

    Args:
        tool: Tool name
        pattern: Pattern/construct name

    Returns:
        Risk level: 'low', 'medium', 'high', or 'unknown'.

    """
    pattern_stats = _count_pattern_outcomes(tool, pattern)
    return _risk_level_from_failure_rate(pattern_stats)


def _count_pattern_outcomes(tool: str, pattern: str) -> dict[str, int]:
    """
    Count success/failure outcomes for a pattern.

    Args:
        tool: Tool name
        pattern: Pattern name

    Returns:
        Dictionary with 'success' and 'failure' counts.

    """
    _ensure_analytics_dir()

    if not ANALYTICS_EVENTS_FILE.exists():
        return {"success": 0, "failure": 0}

    pattern_stats = {"success": 0, "failure": 0}

    try:
        with ANALYTICS_EVENTS_FILE.open() as f:
            for line in f:
                try:
                    event = json.loads(line)
                    if (
                        event.get("tool") == tool
                        and event.get("pattern") == pattern
                        and event.get("event_type") == "conversion"
                    ):
                        status = event.get("status", "unknown")
                        if status == "success":
                            pattern_stats["success"] += 1
                        elif status in ("failure", "partial_success"):
                            pattern_stats["failure"] += 1
                except json.JSONDecodeError:
                    continue
    except OSError as e:
        LOGGER.warning(f"Could not read analytics: {e}")

    return pattern_stats


def _risk_level_from_failure_rate(pattern_stats: dict[str, int]) -> str:
    """
    Convert failure rate to risk level.

    Args:
        pattern_stats: Dictionary with 'success' and 'failure' counts.

    Returns:
        Risk level string.

    """
    total = pattern_stats["success"] + pattern_stats["failure"]
    if total == 0:
        return "unknown"

    failure_rate = pattern_stats["failure"] / total
    if failure_rate >= 0.5:
        return "high"
    elif failure_rate >= 0.25:
        return "medium"
    else:
        return "low"


def clear_analytics() -> None:
    """Clear all analytics data (for testing/reset)."""
    _ensure_analytics_dir()
    try:
        if ANALYTICS_EVENTS_FILE.exists():
            ANALYTICS_EVENTS_FILE.unlink()
        if ANALYTICS_PATTERNS_FILE.exists():
            ANALYTICS_PATTERNS_FILE.unlink()
    except OSError as e:
        LOGGER.warning(f"Could not clear analytics: {e}")


def init_session_tracking() -> None:
    """Initialize analytics session state."""
    if "analytics_session_id" not in st.session_state:
        st.session_state.analytics_session_id = datetime.now().isoformat()
    if "conversion_start_time" not in st.session_state:
        st.session_state.conversion_start_time = None
