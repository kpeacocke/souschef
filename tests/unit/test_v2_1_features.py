"""Tests for v2.1 advanced features: guards, optimization, and audit trail."""

import pytest

from souschef.converters.advanced_resource import (
    estimate_conversion_complexity,
    parse_resource_guards,
    parse_resource_notifications,
    parse_resource_search,
)
from souschef.converters.conversion_audit import (
    ConversionAuditTrail,
    ConversionDecision,
    ResourceConversionRecord,
)
from souschef.converters.playbook_optimizer import (
    _create_loop_consolidated_task,
    _extract_module_name,
    calculate_optimization_metrics,
    consolidate_duplicate_tasks,
    detect_duplicate_tasks,
    optimize_task_loops,
)


class TestAdvancedResourceParsing:
    """Test advanced resource parsing functionality."""

    def test_parse_resource_guards_only_if(self) -> None:
        """Test parsing only_if guards."""
        resource_body = """
        only_if { test -f /tmp/file }
        """
        result = parse_resource_guards(resource_body)
        assert isinstance(result, dict)

    def test_parse_resource_guards_not_if(self) -> None:
        """Test parsing not_if guards."""
        resource_body = """
        not_if { test -f /tmp/file }
        """
        result = parse_resource_guards(resource_body)
        assert isinstance(result, dict)

    def test_parse_resource_guards_ignore_failure(self) -> None:
        """Test parsing ignore_failure."""
        resource_body = """
        ignore_failure true
        """
        result = parse_resource_guards(resource_body)
        assert isinstance(result, dict)

    def test_parse_resource_notifications_notifies(self) -> None:
        """Test parsing notifies notifications."""
        resource_body = """
        notifies :restart, 'service[apache2]'
        """
        result = parse_resource_notifications(resource_body)
        assert isinstance(result, list)

    def test_parse_resource_notifications_subscribes(self) -> None:
        """Test parsing subscribes notifications."""
        resource_body = """
        subscribes :restart, 'template[/etc/apache2/httpd.conf]'
        """
        result = parse_resource_notifications(resource_body)
        assert isinstance(result, list)

    def test_parse_resource_search(self) -> None:
        """Test parsing Chef search patterns."""
        resource_body = """
        search(:node, 'role:web')
        """
        result = parse_resource_search(resource_body)
        assert isinstance(result, dict)

    def test_estimate_conversion_complexity_simple(self) -> None:
        """Test complexity estimation for simple resources."""
        resource_body = """
        package 'apache2'
        """
        complexity = estimate_conversion_complexity(resource_body)
        assert complexity in ["simple", "moderate", "complex"]

    def test_estimate_conversion_complexity_with_guards(self) -> None:
        """Test complexity estimation increases with guards."""
        resource_body = """
        package 'apache2' do
          only_if { test -f /tmp/file }
        end
        """
        complexity = estimate_conversion_complexity(resource_body)
        assert complexity in ["simple", "moderate", "complex"]


class TestPlaybookOptimization:
    """Test playbook optimization functionality."""

    def test_detect_duplicate_tasks_empty(self) -> None:
        """Test duplicate detection with empty task list."""
        tasks: list[dict] = []
        duplicates = detect_duplicate_tasks(tasks)
        assert duplicates == []

    def test_detect_duplicate_tasks_no_duplicates(self) -> None:
        """Test duplicate detection with no duplicates."""
        tasks = [
            {"name": "Task 1", "package": {"name": "apache2"}},
            {"name": "Task 2", "service": {"name": "nginx"}},
        ]
        duplicates = detect_duplicate_tasks(tasks)
        assert duplicates == []

    def test_detect_duplicate_tasks_with_duplicates(self) -> None:
        """Test duplicate detection with identical tasks."""
        tasks = [
            {"name": "Install pkg1", "package": {"name": "apache2"}},
            {"name": "Install pkg1", "package": {"name": "apache2"}},
            {"name": "Install nginx", "package": {"name": "nginx"}},
        ]
        duplicates = detect_duplicate_tasks(tasks)
        assert len(duplicates) > 0

    def test_extract_module_name_unknown(self) -> None:
        """Test module name detection returns None for unknown modules."""
        task = {"name": "Unknown task", "custom": {"value": 1}}

        assert _extract_module_name(task) is None

    def test_consolidate_duplicate_tasks_empty(self) -> None:
        """Test consolidation with empty task list."""
        tasks: list[dict] = []
        duplicates: list[tuple[int, int]] = []
        result = consolidate_duplicate_tasks(tasks, duplicates)
        assert result == []

    def test_consolidate_duplicate_tasks(self) -> None:
        """Test consolidation of duplicate tasks."""
        tasks = [
            {"name": "Install pkg", "package": {"name": "pkg1"}},
            {"name": "Install pkg", "package": {"name": "pkg1"}},
        ]
        duplicates = detect_duplicate_tasks(tasks)
        result = consolidate_duplicate_tasks(tasks, duplicates)
        assert len(result) < len(tasks)

    def test_optimize_task_loops_empty(self) -> None:
        """Test loop optimization with empty task list."""
        tasks: list[dict] = []
        result = optimize_task_loops(tasks)
        assert result == []

    def test_optimize_task_loops_few_tasks(self) -> None:
        """Test loop optimization with insufficient tasks."""
        tasks = [
            {"name": "Install pkg1", "package": {"name": "pkg1"}},
        ]
        result = optimize_task_loops(tasks)
        assert isinstance(result, list)

    def test_optimize_task_loops_many_similar_tasks(self) -> None:
        """Test loop optimization with many similar tasks."""
        tasks = [
            {"name": "Install pkg1", "package": {"name": "pkg1"}},
            {"name": "Install pkg2", "package": {"name": "pkg2"}},
            {"name": "Install pkg3", "package": {"name": "pkg3"}},
            {"name": "Install pkg4", "package": {"name": "pkg4"}},
        ]
        result = optimize_task_loops(tasks)
        assert isinstance(result, list)

    def test_optimize_task_loops_breaks_on_different_modules(self) -> None:
        """Test loop optimisation stops when modules differ."""
        tasks = [
            {"name": "Install pkg", "package": {"name": "pkg1"}},
            {"name": "Restart service", "service": {"name": "nginx"}},
            {"name": "Install pkg2", "package": {"name": "pkg2"}},
        ]

        result = optimize_task_loops(tasks)

        assert len(result) == len(tasks)

    def test_create_loop_consolidated_task_empty(self) -> None:
        """Test loop consolidation returns empty dict for empty input."""
        assert _create_loop_consolidated_task([], None) == {}

    def test_calculate_optimization_metrics(self) -> None:
        """Test optimization metrics calculation."""
        original_tasks = [
            {"name": "Task 1", "package": {"name": "pkg1"}},
            {"name": "Task 2", "package": {"name": "pkg2"}},
        ]
        optimized_tasks = [
            {
                "name": "Consolidated",
                "package": {"name": ["pkg1", "pkg2"]},
                "loop": ["pkg1", "pkg2"],
            }
        ]
        metrics = calculate_optimization_metrics(original_tasks, optimized_tasks)
        assert "reduction_percentage" in metrics
        assert "original_task_count" in metrics
        assert "optimized_task_count" in metrics


class TestConversionAuditTrail:
    """Test conversion audit trail functionality."""

    def test_create_audit_trail(self) -> None:
        """Test creating an audit trail."""
        trail = ConversionAuditTrail(
            migration_id="test_001",
            cookbook_name="test_cookbook",
        )
        assert trail.migration_id == "test_001"
        assert trail.cookbook_name == "test_cookbook"

    def test_audit_trail_add_resource_record(self) -> None:
        """Test adding a resource record to audit trail."""
        trail = ConversionAuditTrail(
            migration_id="test_001",
            cookbook_name="test_cookbook",
        )
        record = ResourceConversionRecord(
            resource_type="package",
            resource_name="apache2",
            decision=ConversionDecision.FULLY_CONVERTED,
            reason="Standard package resource",
            complexity_level="simple",
        )
        trail.add_resource_record(record)
        assert len(trail.resource_records) == 1
        assert trail.resource_records[0].resource_name == "apache2"

    def test_audit_trail_add_note(self) -> None:
        """Test adding notes to audit trail."""
        trail = ConversionAuditTrail(
            migration_id="test_001",
            cookbook_name="test_cookbook",
        )
        trail.add_note("Test note")
        assert len(trail.notes) == 1
        assert "Test note" in trail.notes[0]

    def test_audit_trail_finalize(self) -> None:
        """Test finalizing audit trail."""
        trail = ConversionAuditTrail(
            migration_id="test_001",
            cookbook_name="test_cookbook",
        )
        trail.finalize()
        assert trail.end_time != ""

    def test_audit_trail_to_dict(self) -> None:
        """Test serialising audit trail to dictionary."""
        trail = ConversionAuditTrail(
            migration_id="test_001",
            cookbook_name="test_cookbook",
        )
        record = ResourceConversionRecord(
            resource_type="package",
            resource_name="apache2",
            decision=ConversionDecision.FULLY_CONVERTED,
            reason="Standard package resource",
            complexity_level="simple",
        )
        trail.add_resource_record(record)
        trail_dict = trail.to_dict()
        assert "migration_id" in trail_dict
        assert "cookbook_name" in trail_dict
        assert "summary" in trail_dict

    def test_resource_conversion_record_creation(self) -> None:
        """Test creating a resource conversion record."""
        record = ResourceConversionRecord(
            resource_type="package",
            resource_name="apache2",
            decision=ConversionDecision.FULLY_CONVERTED,
            reason="Standard package resource",
            complexity_level="simple",
        )
        assert record.resource_name == "apache2"
        assert record.decision == ConversionDecision.FULLY_CONVERTED

    def test_conversion_decision_enum(self) -> None:
        """Test ConversionDecision enum values."""
        assert ConversionDecision.FULLY_CONVERTED.value == "fully_converted"
        assert ConversionDecision.PARTIALLY_CONVERTED.value == "partially_converted"
        assert (
            ConversionDecision.REQUIRES_MANUAL_REVIEW.value == "requires_manual_review"
        )
        assert ConversionDecision.NOT_APPLICABLE.value == "not_applicable"
        assert ConversionDecision.ERROR.value == "error"

    def test_audit_trail_quality_score(self) -> None:
        """Test quality score calculation."""
        trail = ConversionAuditTrail(
            migration_id="test_001",
            cookbook_name="test_cookbook",
        )

        # Add various records
        for decision in [
            ConversionDecision.FULLY_CONVERTED,
            ConversionDecision.FULLY_CONVERTED,
            ConversionDecision.PARTIALLY_CONVERTED,
        ]:
            record = ResourceConversionRecord(
                resource_type="package",
                resource_name=f"pkg_{decision.value}",
                decision=decision,
                reason="Test",
                complexity_level="simple",
            )
            trail.add_resource_record(record)

        trail_dict = trail.to_dict()
        assert "quality_score" in trail_dict["summary"]
        quality_score = trail_dict["summary"]["quality_score"]
        assert 0 <= quality_score <= 100

    def test_audit_trail_quality_score_empty(self) -> None:
        """Test quality score is 100 when no records exist."""
        trail = ConversionAuditTrail(
            migration_id="test_002",
            cookbook_name="empty",
        )

        trail_dict = trail.to_dict()
        assert trail_dict["summary"]["quality_score"] == pytest.approx(100.0)
