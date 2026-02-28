"""Additional tests for profiling module to cover edge cases."""

from pathlib import Path

import pytest

from souschef.core.errors import SousChefError
from souschef.profiling import (
    MigrationPerformanceProfile,
    MigrationProfiler,
    PerformanceReport,
    PhaseTiming,
    ProfileResult,
    _add_performance_recommendations,
    _profile_directory_files,
    identify_migration_bottlenecks,
)


def test_performance_report_includes_context_in_str() -> None:
    """Ensure report string includes context key-values."""
    report = PerformanceReport(
        cookbook_name="test",
        total_time=2.0,
        total_memory=1024,
    )
    report.add_result(
        ProfileResult(
            operation_name="parse_recipe",
            execution_time=1.0,
            peak_memory=512,
            context={"file": "default.rb"},
        )
    )

    report_str = str(report)

    assert "file: default.rb" in report_str


def test_phase_timing_to_dict() -> None:
    """Test PhaseTiming serialises to dict."""
    phase = PhaseTiming(
        phase_name="analysis",
        start_time=1.0,
        end_time=2.0,
        duration=1.0,
        metadata={"key": "value"},
    )

    phase_dict = phase.to_dict()

    assert phase_dict["phase_name"] == "analysis"
    assert phase_dict["metadata"]["key"] == "value"


def test_migration_performance_profile_add_phase_and_to_dict() -> None:
    """Test adding phases and serialising profile."""
    profile = MigrationPerformanceProfile(migration_id="mig-1", total_duration=2.0)
    phase = PhaseTiming(
        phase_name="analysis",
        start_time=0.0,
        end_time=1.0,
        duration=1.0,
    )

    profile.add_phase(phase)
    profile_dict = profile.to_dict()

    assert len(profile.phases) == 1
    assert profile_dict["phases"][0]["phase_name"] == "analysis"


def test_migration_profiler_rejects_duplicate_phase() -> None:
    """Test duplicate phase start raises error."""
    profiler = MigrationProfiler(migration_id="mig-2")
    profiler.start_phase("analysis")

    with pytest.raises(SousChefError, match="Phase already started"):
        profiler.start_phase("analysis")


def test_identify_migration_bottlenecks_no_duration() -> None:
    """Test no bottlenecks when total duration is zero."""
    profile = MigrationPerformanceProfile(migration_id="mig-3", total_duration=0.0)

    assert identify_migration_bottlenecks(profile) == []


def test_profile_directory_files_returns_none_when_empty(tmp_path: Path) -> None:
    """Test empty directory returns None for profiling helper."""
    result = _profile_directory_files(
        directory=tmp_path,
        parse_func=lambda _path: "",
        operation_name="parse_recipes",
        file_pattern="*.rb",
    )

    assert result is None


def test_add_performance_recommendations_flags_issues() -> None:
    """Test recommendations include slow, memory, and file count guidance."""
    report = PerformanceReport(
        cookbook_name="test",
        total_time=10.0,
        total_memory=200 * 1024 * 1024,
    )
    report.operation_results = [
        ProfileResult(
            operation_name="parse_metadata",
            execution_time=2.0,
            peak_memory=10,
        ),
        ProfileResult(
            operation_name="parse_recipes (total: 50)",
            execution_time=6.0,
            peak_memory=10,
        ),
        ProfileResult(
            operation_name="parse_templates (total: 20)",
            execution_time=4.0,
            peak_memory=10,
        ),
    ]

    _add_performance_recommendations(report)

    recommendations = "\n".join(report.recommendations)

    assert "optimizing or parallelizing" in recommendations
    assert "Peak memory usage" in recommendations
    assert "Large number of recipes detected" in recommendations
    assert "Template parsing is time-consuming" in recommendations
    assert "Use the --cache option" in recommendations
