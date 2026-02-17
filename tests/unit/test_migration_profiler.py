"""Tests for migration performance profiling utilities."""

import time
from collections.abc import Iterator

import pytest

from souschef.core.errors import SousChefError
from souschef.profiling import (
    MigrationPerformanceProfile,
    MigrationProfiler,
    PhaseTiming,
    generate_migration_performance_report,
    generate_migration_timeline,
    identify_migration_bottlenecks,
)


def _time_sequence(values: list[float]) -> Iterator[float]:
    """Yield a predictable sequence of time values."""
    yield from values


def test_migration_profiler_records_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    """Record a single phase with metadata and verify timing."""
    times = _time_sequence([0.0, 1.0, 2.5, 3.0])
    monkeypatch.setattr("souschef.profiling.time.perf_counter", lambda: next(times))

    profiler = MigrationProfiler("mig-123")
    profiler.start_phase("convert", {"count": 2})
    phase = profiler.end_phase("convert")
    profile = profiler.build_profile()

    assert phase.phase_name == "convert"
    assert phase.duration == pytest.approx(1.5)
    assert phase.metadata == {"count": 2}
    assert profile.total_duration == pytest.approx(3.0)
    assert len(profile.phases) == 1


def test_migration_profiler_context_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """Profile a phase using the context manager."""
    times = _time_sequence([0.0, 0.5, 1.0, 1.2])
    monkeypatch.setattr("souschef.profiling.time.perf_counter", lambda: next(times))

    profiler = MigrationProfiler("mig-456")
    with profiler.profile_phase("validate", {"files": 3}):
        # Simulate analysis work
        time.sleep(0.01)

    profile = profiler.build_profile()
    assert len(profile.phases) == 1
    assert profile.phases[0].phase_name == "validate"
    assert profile.phases[0].metadata == {"files": 3}


def test_migration_profiler_errors_on_invalid_phase() -> None:
    """Raise an error when ending a non-started phase."""
    profiler = MigrationProfiler("mig-789")

    with pytest.raises(SousChefError):
        profiler.end_phase("missing")


def test_identify_bottlenecks() -> None:
    """Identify phases exceeding the threshold ratio."""
    profile = MigrationPerformanceProfile(
        migration_id="mig-001",
        total_duration=10.0,
        phases=[
            PhaseTiming("analyse", 0.0, 2.0, 2.0, {}),
            PhaseTiming("convert", 2.0, 8.0, 6.0, {}),
            PhaseTiming("validate", 8.0, 10.0, 2.0, {}),
        ],
    )

    bottlenecks = identify_migration_bottlenecks(profile, threshold_ratio=0.5)

    assert len(bottlenecks) == 1
    assert bottlenecks[0].phase_name == "convert"


def test_generate_timeline() -> None:
    """Generate a timeline for recorded phases."""
    profile = MigrationPerformanceProfile(
        migration_id="mig-002",
        total_duration=5.0,
        phases=[
            PhaseTiming("analyse", 0.0, 1.0, 1.0, {"files": 2}),
            PhaseTiming("convert", 1.0, 5.0, 4.0, {}),
        ],
    )

    timeline = generate_migration_timeline(profile)

    assert timeline == [
        {"phase": "analyse", "duration": 1.0, "metadata": {"files": 2}},
        {"phase": "convert", "duration": 4.0, "metadata": {}},
    ]


def test_generate_migration_performance_report() -> None:
    """Generate a readable performance report."""
    profile = MigrationPerformanceProfile(
        migration_id="mig-003",
        total_duration=4.0,
        phases=[
            PhaseTiming("analyse", 0.0, 1.0, 1.0, {}),
            PhaseTiming("convert", 1.0, 4.0, 3.0, {"recipes": 5}),
        ],
    )

    report = generate_migration_performance_report(profile)

    assert "Migration Performance Report" in report
    assert "Migration ID: mig-003" in report
    assert "convert" in report
    assert "recipes: 5" in report
