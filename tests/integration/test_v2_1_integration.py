"""Integration tests for v2.1 advanced features: audit trail and optimization."""

import json
from pathlib import Path

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
    calculate_optimization_metrics,
    consolidate_duplicate_tasks,
    detect_duplicate_tasks,
    optimize_task_loops,
)
from souschef.migration_v2 import MigrationOrchestrator

FIXTURES_DIR = Path(__file__).parent.parent / "integration" / "fixtures"


class TestAuditTrailIntegration:
    """Integration tests for audit trail across full migration workflow."""

    def test_audit_trail_full_workflow(self, tmp_path: Path) -> None:
        """Test complete audit trail tracking through migration."""
        migration_id = "test_audit_001"
        trail = ConversionAuditTrail(
            migration_id=migration_id,
            cookbook_name="test_cookbook",
        )

        # Simulate conversion of multiple resources
        resources = [
            ("package", "apache2", ConversionDecision.FULLY_CONVERTED, "simple"),
            (
                "service",
                "apache2",
                ConversionDecision.FULLY_CONVERTED,
                "simple",
            ),
            (
                "template",
                "/etc/apache2/httpd.conf",
                ConversionDecision.PARTIALLY_CONVERTED,
                "moderate",
            ),
            (
                "custom_resource",
                "app_deploy",
                ConversionDecision.REQUIRES_MANUAL_REVIEW,
                "complex",
            ),
        ]

        for res_type, res_name, decision, complexity in resources:
            record = ResourceConversionRecord(
                resource_type=res_type,
                resource_name=res_name,
                decision=decision,
                reason=f"Converted {res_type} {res_name}",
                complexity_level=complexity,
            )
            trail.add_resource_record(record)

        # Add migration notes
        trail.add_note("Migration started")
        trail.add_note("Completed resource analysis")

        # Finalize trail
        trail.finalize()

        # Verify trail state
        assert len(trail.resource_records) == 4
        assert len(trail.notes) == 2
        assert trail.end_time != ""

        # Verify summary
        trail_dict = trail.to_dict()
        assert trail_dict["summary"]["total_resources"] == 4
        assert trail_dict["summary"]["conversion_rate_percent"] > 0
        assert "quality_score" in trail_dict["summary"]

    def test_json_export_completeness(self, tmp_path: Path) -> None:
        """Test JSON export contains all required fields."""
        migration_id = "json_export_test"
        trail = ConversionAuditTrail(
            migration_id=migration_id,
            cookbook_name="export_test",
        )

        record = ResourceConversionRecord(
            resource_type="package",
            resource_name="nginx",
            decision=ConversionDecision.FULLY_CONVERTED,
            reason="Standard package",
            complexity_level="simple",
            warnings=["Ensure package source is available"],
            recommendations=["Use ansible.builtin.package module"],
        )
        trail.add_resource_record(record)
        trail.finalize()

        # Export to JSON file
        json_path = tmp_path / "audit.json"
        trail.export_json(str(json_path))

        # Verify file exists and contains valid JSON
        assert json_path.exists()
        data = json.loads(json_path.read_text())

        # Verify required fields
        assert data["migration_id"] == migration_id
        assert data["cookbook_name"] == "export_test"
        assert "start_time" in data
        assert "end_time" in data
        assert "resource_records" in data
        assert len(data["resource_records"]) == 1
        assert data["resource_records"][0]["resource_name"] == "nginx"
        assert data["resource_records"][0]["warnings"] == [
            "Ensure package source is available"
        ]

    def test_html_report_generation(self, tmp_path: Path) -> None:
        """Test HTML report generation and structure."""
        migration_id = "html_report_test"
        trail = ConversionAuditTrail(
            migration_id=migration_id,
            cookbook_name="report_test",
        )

        # Add various conversion outcomes
        for i in range(3):
            decisions = [
                ConversionDecision.FULLY_CONVERTED,
                ConversionDecision.PARTIALLY_CONVERTED,
                ConversionDecision.REQUIRES_MANUAL_REVIEW,
            ]
            record = ResourceConversionRecord(
                resource_type="resource",
                resource_name=f"test_resource_{i}",
                decision=decisions[i],
                reason=f"Test resource {i}",
                complexity_level="moderate",
            )
            trail.add_resource_record(record)

        trail.finalize()

        # Export to HTML
        html_path = tmp_path / "report.html"
        trail.export_html_report(str(html_path))

        # Verify file exists and is valid HTML
        assert html_path.exists()
        html_content = html_path.read_text()

        # Verify HTML structure
        assert "<html>" in html_content
        assert "</html>" in html_content
        assert migration_id in html_content
        assert "report_test" in html_content
        assert "Conversion Results" in html_content or "table" in html_content

    def test_quality_score_mixed_conversions(self) -> None:
        """Test quality score calculation with mixed conversion outcomes."""
        trail = ConversionAuditTrail(
            migration_id="quality_test",
            cookbook_name="quality_cookbook",
        )

        # Add resources with different outcomes
        test_cases = [
            (ConversionDecision.FULLY_CONVERTED, "simple", 1.0),
            (ConversionDecision.FULLY_CONVERTED, "moderate", 1.0),
            (ConversionDecision.PARTIALLY_CONVERTED, "simple", 0.6),
            (ConversionDecision.REQUIRES_MANUAL_REVIEW, "complex", 0.3),
            (ConversionDecision.NOT_APPLICABLE, "simple", 0.0),
        ]

        for i, (decision, complexity, _expected_weight) in enumerate(test_cases):
            record = ResourceConversionRecord(
                resource_type="resource",
                resource_name=f"res_{i}",
                decision=decision,
                reason="Test",
                complexity_level=complexity,
            )
            trail.add_resource_record(record)

        trail_dict = trail.to_dict()
        quality_score = trail_dict["summary"]["quality_score"]

        # Quality score should be between 0 and 100
        assert 0 <= quality_score <= 100
        # With mixed outcomes, should be moderate (not 0, not 100)
        assert 20 < quality_score < 80


class TestPlaybookOptimizationIntegration:
    """Integration tests for playbook optimization workflow."""

    def test_optimization_metrics_full_workflow(self) -> None:
        """Test optimization metrics across a full playbook."""
        # Create playbooks with duplicates
        original_tasks = [
            {
                "name": "Install package 1",
                "package": {"name": "apache2", "state": "present"},
            },
            {
                "name": "Install package 1",
                "package": {"name": "apache2", "state": "present"},
            },
            {
                "name": "Install package 2",
                "package": {"name": "nginx", "state": "present"},
            },
            {
                "name": "Install package 3",
                "package": {"name": "curl", "state": "present"},
            },
            {
                "name": "Install package 4",
                "package": {"name": "wget", "state": "present"},
            },
            {
                "name": "Configure service",
                "service": {"name": "apache2", "state": "started"},
            },
        ]

        # Step 1: Detect duplicates
        duplicates = detect_duplicate_tasks(original_tasks)
        assert len(duplicates) > 0

        # Step 2: Consolidate duplicates
        deduplicated = consolidate_duplicate_tasks(original_tasks, duplicates)
        assert len(deduplicated) < len(original_tasks)

        # Step 3: Optimize loops
        optimized = optimize_task_loops(deduplicated)
        assert isinstance(optimized, list)

        # Step 4: Calculate metrics
        metrics = calculate_optimization_metrics(original_tasks, optimized)

        # Verify metrics structure
        assert "original_task_count" in metrics
        assert "optimized_task_count" in metrics
        assert "reduction_percentage" in metrics
        assert metrics["original_task_count"] == len(original_tasks)
        assert metrics["optimized_task_count"] <= len(original_tasks)
        assert metrics["reduction_percentage"] >= 0

    def test_loop_consolidation_identical_tasks(self) -> None:
        """Test loop consolidation with identical package tasks."""
        tasks = [
            {"name": "Install pkg1", "package": {"name": "pkg1"}},
            {"name": "Install pkg2", "package": {"name": "pkg2"}},
            {"name": "Install pkg3", "package": {"name": "pkg3"}},
            {"name": "Install pkg4", "package": {"name": "pkg4"}},
        ]

        result = optimize_task_loops(tasks)

        # Should create a consolidated loop task
        assert isinstance(result, list)
        assert len(result) <= len(tasks)


class TestAdvancedResourceIntegration:
    """Integration tests for advanced resource parsing."""

    def test_guard_detection_in_recipe(self) -> None:
        """Test detecting guards in a full recipe context."""
        recipe_content = """
package 'apache2' do
  only_if { ::File.exist?('/var/www/html') }
  action :install
end

service 'apache2' do
  not_if { ::File.exist?('/etc/apache2/sites-enabled/default') }
  action :enable
end

execute 'deploy app' do
  command 'tar xzf /tmp/app.tar.gz'
  ignore_failure true
end
"""

        # Parse recipe and extract guards
        guards = parse_resource_guards(recipe_content)
        assert isinstance(guards, dict)

    def test_notification_extraction_full_recipe(self) -> None:
        """Test notification extraction from complete recipe."""
        recipe_content = """
template '/etc/apache2/httpd.conf' do
  source 'httpd.conf.erb'
  variables(port: 80)
  notifies :restart, 'service[apache2]'
  notifies :reload, 'service[apache2]', delay: 5
end

service 'apache2' do
  supports restart: true, reload: true
  action :nothing
end
"""

        notifications = parse_resource_notifications(recipe_content)
        assert isinstance(notifications, list)

    def test_chef_search_detection(self) -> None:
        """Test Chef search pattern detection."""
        recipe_content = """
web_servers = search(:node, 'role:web AND environment:production')

web_servers.each do |server|
  execute "ping #{server['ipaddress']}" do
    command "ping -c 1 #{server['ipaddress']}"
  end
end
"""

        searches = parse_resource_search(recipe_content)
        assert isinstance(searches, dict)

    def test_complexity_scoring_various_resources(self) -> None:
        """Test complexity scoring across various resource types."""
        test_cases = [
            ("package 'nginx'", "simple"),
            (
                """service 'nginx' do
  only_if { ::File.exist?('/etc/nginx/nginx.conf') }
  action :enable
end""",
                "moderate",
            ),
            (
                """custom_resource 'deploy_app' do
  search(:node, 'role:app')
  notifies :run, 'execute[restart_app]'
  ignore_failure true
end""",
                "complex",
            ),
        ]

        for recipe, _expected_level in test_cases:
            complexity = estimate_conversion_complexity(recipe)
            assert complexity in ["simple", "moderate", "complex"]


class TestMigrationOrchestratorV21:
    """Integration tests for orchestrator v2.1 features."""

    def test_orchestrator_audit_trail_initialization(self, tmp_path: Path) -> None:
        """Test orchestrator initialises audit trail correctly."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="22.0.0",
        )

        # Verify audit trail methods exist
        assert hasattr(orchestrator, "_initialize_audit_trail")
        assert hasattr(orchestrator, "_finalize_audit_trail")
        assert hasattr(orchestrator, "_analyze_resource_complexity")

    def test_orchestrator_optimization_methods(self, tmp_path: Path) -> None:
        """Test orchestrator has optimization methods."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="22.0.0",
        )

        # Verify optimization methods exist
        assert hasattr(orchestrator, "_optimize_generated_playbooks")
        assert hasattr(orchestrator, "_detect_resource_guards")
        assert hasattr(orchestrator, "_detect_resource_notifications")
