"""
Performance profiling and optimization utilities for SousChef.

This module provides tools for profiling parsing operations, identifying bottlenecks,
and generating performance reports for large cookbook migrations.
"""

import cProfile
import io
import pstats
import time
import tracemalloc
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from souschef.core.errors import SousChefError


@dataclass
class ProfileResult:
    """
    Results from a profiling operation.

    Attributes:
        operation_name: Name of the operation profiled.
        execution_time: Total execution time in seconds.
        peak_memory: Peak memory usage in bytes.
        function_stats: Statistics for individual function calls.
        context: Additional context about the operation.

    """

    operation_name: str
    execution_time: float
    peak_memory: int
    function_stats: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """
        Format profile result as readable string.

        Returns:
            Formatted profile summary.

        """
        return f"""
Profile: {self.operation_name}
Execution Time: {self.execution_time:.3f}s
Peak Memory: {self.peak_memory / 1024 / 1024:.2f}MB
Context: {self.context}
"""


@dataclass
class PerformanceReport:
    """
    Comprehensive performance report for cookbook migration.

    Attributes:
        cookbook_name: Name of the cookbook profiled.
        total_time: Total processing time in seconds.
        total_memory: Total peak memory usage in bytes.
        operation_results: Results for individual operations.
        recommendations: Performance optimization recommendations.

    """

    cookbook_name: str
    total_time: float
    total_memory: int
    operation_results: list[ProfileResult] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def add_result(self, result: ProfileResult) -> None:
        """
        Add a profile result to the report.

        Args:
            result: Profile result to add.

        """
        self.operation_results.append(result)

    def add_recommendation(self, recommendation: str) -> None:
        """
        Add a performance recommendation.

        Args:
            recommendation: Recommendation text.

        """
        self.recommendations.append(recommendation)

    def __str__(self) -> str:
        """
        Format performance report as readable string.

        Returns:
            Formatted report.

        """
        report_lines = [
            f"\n{'=' * 80}",
            f"Performance Report: {self.cookbook_name}",
            f"{'=' * 80}",
            f"Total Time: {self.total_time:.3f}s",
            f"Total Peak Memory: {self.total_memory / 1024 / 1024:.2f}MB",
            "\nOperation Breakdown:",
            f"{'-' * 80}",
        ]

        for result in self.operation_results:
            report_lines.extend(
                [
                    f"\n{result.operation_name}:",
                    (
                        f"  Time: {result.execution_time:.3f}s "
                        f"({result.execution_time / self.total_time * 100:.1f}%)"
                    ),
                    f"  Memory: {result.peak_memory / 1024 / 1024:.2f}MB",
                ]
            )
            if result.context:
                for key, value in result.context.items():
                    report_lines.append(f"  {key}: {value}")

        if self.recommendations:
            report_lines.extend([f"\n{'-' * 80}", "Recommendations:", f"{'-' * 80}"])
            for i, rec in enumerate(self.recommendations, 1):
                report_lines.append(f"{i}. {rec}")

        report_lines.append(f"{'=' * 80}\n")
        return "\n".join(report_lines)


@dataclass
class PhaseTiming:
    """
    Timing details for a migration phase.

    Attributes:
        phase_name: Name of the migration phase.
        start_time: Phase start time (perf counter).
        end_time: Phase end time (perf counter).
        duration: Phase duration in seconds.
        metadata: Optional metadata about the phase.

    """

    phase_name: str
    start_time: float
    end_time: float
    duration: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert phase timing to a dictionary.

        Returns:
            Dictionary representation of the phase timing.

        """
        return {
            "phase_name": self.phase_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "metadata": self.metadata,
        }


@dataclass
class MigrationPerformanceProfile:
    """
    Performance profile for a migration.

    Attributes:
        migration_id: Migration identifier.
        total_duration: Total duration in seconds.
        phases: List of recorded phase timings.

    """

    migration_id: str
    total_duration: float
    phases: list[PhaseTiming] = field(default_factory=list)

    def add_phase(self, phase: PhaseTiming) -> None:
        """
        Add a phase timing to the profile.

        Args:
            phase: Phase timing to add.

        """
        self.phases.append(phase)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert profile to a dictionary.

        Returns:
            Dictionary representation of the profile.

        """
        return {
            "migration_id": self.migration_id,
            "total_duration": self.total_duration,
            "phases": [phase.to_dict() for phase in self.phases],
        }


class MigrationProfiler:
    """
    Profile migration phases with timing data.

    Tracks phase start/end times and provides helpers for reporting.

    """

    def __init__(self, migration_id: str) -> None:
        """
        Initialise migration profiler.

        Args:
            migration_id: Migration identifier.

        """
        self.migration_id = migration_id
        self._start_time = time.perf_counter()
        self._in_progress: dict[str, float] = {}
        self._metadata: dict[str, dict[str, Any]] = {}
        self._phases: list[PhaseTiming] = []

    def start_phase(
        self, phase_name: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Mark the start of a migration phase.

        Args:
            phase_name: Name of the phase.
            metadata: Optional metadata about the phase.

        Raises:
            SousChefError: If the phase is already started.

        """
        if phase_name in self._in_progress:
            raise SousChefError(
                f"Phase already started: {phase_name}",
                suggestion="Call end_phase before restarting the same phase",
            )

        self._in_progress[phase_name] = time.perf_counter()
        if metadata is not None:
            self._metadata[phase_name] = metadata

    def end_phase(self, phase_name: str) -> PhaseTiming:
        """
        Mark the end of a migration phase.

        Args:
            phase_name: Name of the phase.

        Returns:
            PhaseTiming for the completed phase.

        Raises:
            SousChefError: If the phase was not started.

        """
        if phase_name not in self._in_progress:
            raise SousChefError(
                f"Phase not started: {phase_name}",
                suggestion="Call start_phase before end_phase",
            )

        start_time = self._in_progress.pop(phase_name)
        end_time = time.perf_counter()
        metadata = self._metadata.pop(phase_name, {})

        phase = PhaseTiming(
            phase_name=phase_name,
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            metadata=metadata,
        )
        self._phases.append(phase)
        return phase

    @contextmanager
    def profile_phase(
        self, phase_name: str, metadata: dict[str, Any] | None = None
    ) -> Iterator[PhaseTiming]:
        """
        Context manager to profile a migration phase.

        Args:
            phase_name: Name of the phase.
            metadata: Optional metadata about the phase.

        Yields:
            Placeholder PhaseTiming while the phase runs. The completed
            phase timing is recorded and available via build_profile.

        """
        self.start_phase(phase_name, metadata)
        try:
            yield PhaseTiming(
                phase_name=phase_name,
                start_time=0.0,
                end_time=0.0,
                duration=0.0,
                metadata=metadata or {},
            )
        finally:
            self.end_phase(phase_name)

    def build_profile(self) -> MigrationPerformanceProfile:
        """
        Build a migration performance profile.

        Returns:
            MigrationPerformanceProfile with aggregated phase timings.

        """
        total_duration = time.perf_counter() - self._start_time
        profile = MigrationPerformanceProfile(
            migration_id=self.migration_id,
            total_duration=total_duration,
            phases=list(self._phases),
        )
        return profile


def identify_migration_bottlenecks(
    profile: MigrationPerformanceProfile, threshold_ratio: float = 0.25
) -> list[PhaseTiming]:
    """
    Identify slow migration phases by relative duration.

    Args:
        profile: Migration performance profile.
        threshold_ratio: Minimum fraction of total duration for a phase to
            be flagged as a bottleneck.

    Returns:
        List of phase timings considered bottlenecks.

    """
    if profile.total_duration <= 0:
        return []

    bottlenecks = [
        phase
        for phase in profile.phases
        if (phase.duration / profile.total_duration) >= threshold_ratio
    ]
    return bottlenecks


def generate_migration_timeline(
    profile: MigrationPerformanceProfile,
) -> list[dict[str, Any]]:
    """
    Generate a timeline summary of migration phases.

    Args:
        profile: Migration performance profile.

    Returns:
        List of timeline entries with phase details.

    """
    timeline = []
    for phase in profile.phases:
        timeline.append(
            {
                "phase": phase.phase_name,
                "duration": phase.duration,
                "metadata": phase.metadata,
            }
        )
    return timeline


def generate_migration_performance_report(
    profile: MigrationPerformanceProfile,
) -> str:
    """
    Generate a text report for migration performance.

    Args:
        profile: Migration performance profile.

    Returns:
        Formatted report string.

    """
    lines = [
        "Migration Performance Report",
        "=" * 80,
        f"Migration ID: {profile.migration_id}",
        f"Total Duration: {profile.total_duration:.3f}s",
        "",
        "Phase Breakdown:",
        "-" * 80,
    ]

    for phase in profile.phases:
        lines.append(
            f"{phase.phase_name}: {phase.duration:.3f}s "
            f"({(phase.duration / profile.total_duration * 100):.1f}%)"
            if profile.total_duration > 0
            else f"{phase.phase_name}: {phase.duration:.3f}s"
        )
        if phase.metadata:
            for key, value in phase.metadata.items():
                lines.append(f"  {key}: {value}")

    bottlenecks = identify_migration_bottlenecks(profile)
    if bottlenecks:
        lines.extend(["", "Bottlenecks:", "-" * 80])
        for phase in bottlenecks:
            lines.append(
                f"{phase.phase_name} ({phase.duration:.3f}s, "
                f"{phase.duration / profile.total_duration * 100:.1f}% of total)"
            )

    lines.append("=" * 80)
    return "\n".join(lines)


@contextmanager
def profile_operation(
    operation_name: str, context: dict[str, Any] | None = None
) -> Iterator[ProfileResult]:
    """
    Context manager for profiling an operation.

    Args:
        operation_name: Name of the operation being profiled.
        context: Additional context information.

    Yields:
        ProfileResult that will be populated with profiling data.

    Example:
        >>> with profile_operation("parse_recipe", {"file": "default.rb"}) as result:
        ...     parse_recipe("/path/to/recipe.rb")
        >>> print(result.execution_time)

    """
    result = ProfileResult(
        operation_name=operation_name,
        execution_time=0.0,
        peak_memory=0,
        context=context or {},
    )

    tracemalloc.start()
    start_time = time.perf_counter()

    try:
        yield result
    finally:
        end_time = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result.execution_time = end_time - start_time
        result.peak_memory = peak


def profile_function(
    func: Callable[..., Any],
    *args: Any,
    operation_name: str | None = None,
    **kwargs: Any,
) -> tuple[Any, ProfileResult]:
    """
    Profile a function call and return result with profiling data.

    Args:
        func: Function to profile.
        *args: Positional arguments for the function.
        operation_name: Name for the operation (defaults to function name).
        **kwargs: Keyword arguments for the function.

    Returns:
        Tuple of (function_result, profile_result).

    Example:
        >>> result, profile = profile_function(parse_recipe, "/path/to/recipe.rb")
        >>> print(f"Took {profile.execution_time:.3f}s")

    """
    op_name = operation_name or func.__name__

    with profile_operation(op_name) as profile:
        result = func(*args, **kwargs)

    return result, profile


def detailed_profile_function(
    func: Callable[..., Any],
    *args: Any,
    operation_name: str | None = None,
    top_n: int = 20,
    **kwargs: Any,
) -> tuple[Any, ProfileResult]:
    """
    Profile a function with detailed call statistics.

    Args:
        func: Function to profile.
        *args: Positional arguments for the function.
        operation_name: Name for the operation (defaults to function name).
        top_n: Number of top functions to include in stats.
        **kwargs: Keyword arguments for the function.

    Returns:
        Tuple of (function_result, profile_result with detailed stats).

    Example:
        >>> result, profile = detailed_profile_function(parse_recipe, path)
        >>> print(profile.function_stats["total_calls"])

    """
    op_name = operation_name or func.__name__

    # Memory and time profiling
    tracemalloc.start()
    start_time = time.perf_counter()

    # Function call profiling
    profiler = cProfile.Profile()
    profiler.enable()

    try:
        result = func(*args, **kwargs)
    finally:
        profiler.disable()
        end_time = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    # Extract statistics
    stats_buffer = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_buffer)
    stats.strip_dirs()
    stats.sort_stats("cumulative")
    stats.print_stats(top_n)

    # Get call counts from stats
    # pstats.Stats has a stats attribute that's a dict in runtime,
    # but mypy doesn't recognize it. We use getattr to bypass type checking.
    stats_dict = getattr(stats, "stats", {})
    total_calls = sum(cc[0] for cc in stats_dict.values()) if stats_dict else 0
    primitive_calls = sum(cc[1] for cc in stats_dict.values()) if stats_dict else 0

    profile_result = ProfileResult(
        operation_name=op_name,
        execution_time=end_time - start_time,
        peak_memory=peak,
        function_stats={
            "total_calls": total_calls,
            "primitive_calls": primitive_calls,
            "top_functions": stats_buffer.getvalue(),
        },
    )

    return result, profile_result


def _profile_directory_files(
    directory: Path,
    parse_func: Callable[[str], str],
    operation_name: str,
    file_pattern: str = "*.rb",
) -> ProfileResult | None:
    """
    Profile parsing operations for files in a directory.

    Args:
        directory: Directory containing files to parse.
        parse_func: Function to parse individual files.
        operation_name: Name for the profiling operation.
        file_pattern: Glob pattern to match files.

    Returns:
        ProfileResult with aggregated stats, or None if no files found.

    """
    if not directory.exists():  # NOSONAR
        return None

    file_count = 0
    total_time = 0.0

    for file_path in directory.glob(file_pattern):
        with profile_operation(operation_name, {"file": file_path.name}) as result:
            parse_func(str(file_path))
        file_count += 1
        total_time += result.execution_time

    if file_count > 0:
        return ProfileResult(
            operation_name=f"{operation_name} (total: {file_count})",
            execution_time=total_time,
            peak_memory=0,
            context={"avg_per_file": total_time / file_count},
        )

    return None


def generate_cookbook_performance_report(
    cookbook_path: str,
) -> PerformanceReport:
    """
    Generate comprehensive performance report for a cookbook.

    Profiles all parsing operations for a cookbook and provides
    optimization recommendations based on the results.

    Args:
        cookbook_path: Path to the cookbook to profile.

    Returns:
        PerformanceReport with detailed profiling information.

    Raises:
        SousChefError: If cookbook path is invalid or profiling fails.

    Example:
        >>> report = generate_cookbook_performance_report("/path/to/cookbook")
        >>> print(report)

    """
    from souschef.parsers.attributes import parse_attributes
    from souschef.parsers.metadata import (
        list_cookbook_structure,
        read_cookbook_metadata,
    )
    from souschef.parsers.recipe import parse_recipe
    from souschef.parsers.resource import parse_custom_resource
    from souschef.parsers.template import parse_template

    path = Path(cookbook_path)
    if not path.exists():  # NOSONAR
        raise SousChefError(
            f"Cookbook path not found: {cookbook_path}",
            suggestion="Verify the cookbook path exists and is accessible",
        )

    report = PerformanceReport(cookbook_name=path.name, total_time=0.0, total_memory=0)

    overall_start = time.perf_counter()
    overall_memory_start = 0

    tracemalloc.start()
    overall_memory_start = tracemalloc.get_traced_memory()[1]

    try:
        # Profile cookbook structure analysis
        with profile_operation(
            "list_cookbook_structure", {"path": cookbook_path}
        ) as result:
            list_cookbook_structure(cookbook_path)
        report.add_result(result)

        # Profile metadata parsing
        metadata_path = path / "metadata.rb"
        if metadata_path.exists():  # NOSONAR
            with profile_operation(
                "read_cookbook_metadata", {"file": str(metadata_path)}
            ) as result:
                read_cookbook_metadata(str(metadata_path))
            report.add_result(result)

        # Profile recipe parsing
        recipe_result = _profile_directory_files(
            path / "recipes", parse_recipe, "parse_recipes"
        )
        if recipe_result:
            report.add_result(recipe_result)

        # Profile attribute parsing
        attr_result = _profile_directory_files(
            path / "attributes", parse_attributes, "parse_attributes"
        )
        if attr_result:
            report.add_result(attr_result)

        # Profile custom resource parsing
        resource_result = _profile_directory_files(
            path / "resources", parse_custom_resource, "parse_custom_resources"
        )
        if resource_result:
            report.add_result(resource_result)

        # Profile template parsing
        templates_dir = path / "templates"
        if templates_dir.exists():  # NOSONAR
            template_count = 0
            template_total_time = 0.0

            for template_file in templates_dir.rglob("*.erb"):
                with profile_operation(
                    "parse_template", {"file": template_file.name}
                ) as result:
                    parse_template(str(template_file))
                template_count += 1
                template_total_time += result.execution_time

            if template_count > 0:
                report.add_result(
                    ProfileResult(
                        operation_name=f"parse_templates (total: {template_count})",
                        execution_time=template_total_time,
                        peak_memory=0,
                        context={
                            "avg_per_template": template_total_time / template_count
                        },
                    )
                )

    finally:
        _, overall_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    # Total memory is the peak during profiling, ensuring non-negative
    report.total_time = time.perf_counter() - overall_start
    report.total_memory = max(0, overall_peak - overall_memory_start)

    # Generate recommendations
    _add_performance_recommendations(report)

    return report


def _add_performance_recommendations(report: PerformanceReport) -> None:
    """
    Add performance recommendations based on profiling results.

    Args:
        report: Performance report to add recommendations to.

    """
    # Check for slow operations
    slow_threshold = 1.0  # 1 second
    for result in report.operation_results:
        if result.execution_time > slow_threshold:
            report.add_recommendation(
                f"Operation '{result.operation_name}' took "
                f"{result.execution_time:.2f}s. "
                f"Consider optimizing or parallelizing this operation."
            )

    # Check for high memory usage
    memory_threshold = 100 * 1024 * 1024  # 100MB
    if report.total_memory > memory_threshold:
        report.add_recommendation(
            f"Peak memory usage is {report.total_memory / 1024 / 1024:.0f}MB. "
            "Consider processing files in batches or implementing streaming "
            "for large cookbooks."
        )

    # Check for many files
    for result in report.operation_results:
        if "total:" in result.operation_name:
            # Extract count from operation name like "parse_recipes (total: 50)"
            if "parse_recipes" in result.operation_name and result.execution_time > 5.0:
                report.add_recommendation(
                    "Large number of recipes detected. Consider using parallel "
                    "processing or caching intermediate results for faster re-runs."
                )
            elif (
                "parse_templates" in result.operation_name
                and result.execution_time > 3.0
            ):
                report.add_recommendation(
                    "Template parsing is time-consuming. Consider caching parsed "
                    "templates or using a template compilation cache."
                )

    # Always provide general recommendations
    report.add_recommendation(
        "Use the --cache option (if available) to cache parsing results for "
        "faster subsequent runs."
    )
    report.add_recommendation(
        "For very large cookbooks, consider splitting into smaller, focused cookbooks."
    )


def compare_performance(
    before: ProfileResult | PerformanceReport,
    after: ProfileResult | PerformanceReport,
) -> str:
    """
    Compare performance before and after optimization.

    Args:
        before: Performance metrics before optimization.
        after: Performance metrics after optimization.

    Returns:
        Formatted comparison report.

    Example:
        >>> comparison = compare_performance(before_profile, after_profile)
        >>> print(comparison)

    """
    time_before = (
        before.total_time
        if isinstance(before, PerformanceReport)
        else before.execution_time
    )
    time_after = (
        after.total_time
        if isinstance(after, PerformanceReport)
        else after.execution_time
    )

    memory_before = (
        before.total_memory
        if isinstance(before, PerformanceReport)
        else before.peak_memory
    )
    memory_after = (
        after.total_memory
        if isinstance(after, PerformanceReport)
        else after.peak_memory
    )

    time_improvement = (
        ((time_before - time_after) / time_before * 100) if time_before > 0 else 0
    )
    memory_improvement = (
        ((memory_before - memory_after) / memory_before * 100)
        if memory_before > 0
        else 0
    )

    return f"""
Performance Comparison
{"=" * 80}
Execution Time:
  Before: {time_before:.3f}s
  After:  {time_after:.3f}s
  Change: {time_improvement:+.1f}% {"(faster)" if time_improvement > 0 else "(slower)"}

Memory Usage:
  Before: {memory_before / 1024 / 1024:.2f}MB
  After:  {memory_after / 1024 / 1024:.2f}MB
  Change: {memory_improvement:+.1f}% {"(less)" if memory_improvement > 0 else "(more)"}
{"=" * 80}
"""
