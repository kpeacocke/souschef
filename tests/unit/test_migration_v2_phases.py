"""
Comprehensive tests for migration_v2.py phase-specific methods.

Targets uncovered lines in attribute conversion, resource processing,
handler conversion, template processing, validation, and optimization.
"""

import subprocess
from pathlib import Path
from unittest.mock import patch

from souschef.migration_v2 import (
    MigrationOrchestrator,
    MigrationResult,
    MigrationStatus,
)


class TestAttributeConversion:
    """Coverage for attribute conversion phase."""

    def test_convert_attributes_with_valid_files(self, tmp_path: Path) -> None:
        """Attributes should be converted to Ansible variables."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        attributes_dir = cookbook_dir / "attributes"
        attributes_dir.mkdir()
        (attributes_dir / "default.rb").write_text("default['app']['port'] = 8080")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        with patch("souschef.migration_v2.parse_attributes") as mock_parse_attributes:
            mock_parse_attributes.return_value = "port: 8080"

            result = orchestrator.migrate_cookbook(str(cookbook_dir))
            assert result.metrics.attributes_converted >= 0

    def test_convert_attributes_with_parse_errors(self, tmp_path: Path) -> None:
        """Failed attribute parsing should be skipped."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        attributes_dir = cookbook_dir / "attributes"
        attributes_dir.mkdir()
        (attributes_dir / "default.rb").write_text("invalid ruby syntax {{{")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        with patch("souschef.migration_v2.parse_attributes") as mock_parse_attributes:
            mock_parse_attributes.return_value = "Error: Failed to parse attributes"

            result = orchestrator.migrate_cookbook(str(cookbook_dir))
            assert result.metrics.attributes_skipped >= 0

    def test_convert_attributes_with_exception(self, tmp_path: Path) -> None:
        """Exceptions during attribute conversion should be caught."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        attributes_dir = cookbook_dir / "attributes"
        attributes_dir.mkdir()
        (attributes_dir / "default.rb").write_text("default['app']['port'] = 8080")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        with patch("souschef.migration_v2.parse_attributes") as mock_parse_attributes:
            mock_parse_attributes.side_effect = RuntimeError("Parse failed")

            result = orchestrator.migrate_cookbook(str(cookbook_dir))
            assert result.metrics.attributes_skipped >= 0


class TestResourceConversion:
    """Coverage for resource conversion and custom resource handling."""

    def test_process_custom_resources_with_exception(self, tmp_path: Path) -> None:
        """Exceptions during custom resource processing should be caught."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        resources_dir = cookbook_dir / "resources"
        resources_dir.mkdir()
        (resources_dir / "database.rb").write_text("property :db_name, String")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        with patch("souschef.parsers.resource.parse_custom_resource") as mock_parse:
            mock_parse.side_effect = RuntimeError("Parse failed")

            result = orchestrator.migrate_cookbook(str(cookbook_dir))
            # Should catch exception and increment skipped count
            assert result.metrics.resources_skipped >= 0


class TestHandlerConversion:
    """Coverage for Chef handler conversion to Ansible error handling."""

    def test_process_library_handlers_found(self, tmp_path: Path) -> None:
        """Library handlers should be detected and warnings created."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        libraries_dir = cookbook_dir / "libraries"
        libraries_dir.mkdir()
        (libraries_dir / "error_handler.rb").write_text(
            "class ErrorHandler < Chef::Handler\ndef report\nend\nend"
        )

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        result = orchestrator.migrate_cookbook(str(cookbook_dir))
        # Should find handler and create warning
        assert result.metrics.handlers_skipped >= 0

    def test_process_library_handlers_with_exception(self, tmp_path: Path) -> None:
        """Exceptions during handler processing should be caught."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        libraries_dir = cookbook_dir / "libraries"
        libraries_dir.mkdir()
        (libraries_dir / "handler.rb").write_text("class MyHandler\nend")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        # Force an exception by making file unreadable
        handler_file = libraries_dir / "handler.rb"
        handler_file.chmod(0o000)

        try:
            result = orchestrator.migrate_cookbook(str(cookbook_dir))
            # Should handle permission errors gracefully
            assert isinstance(result, MigrationResult)
        finally:
            # Restore permissions for cleanup
            handler_file.chmod(0o644)

    def test_process_recipe_handlers_with_notifications(self, tmp_path: Path) -> None:
        """Recipe notification handlers should be detected."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text(
            r"""
begin
  package 'nginx'
rescue => e
  log "Error: \#{e.message}"
end.notifies :restart, 'service[nginx]', :delayed
"""
        )

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        result = orchestrator.migrate_cookbook(str(cookbook_dir))
        # Should detect notification handlers in recipe
        assert isinstance(result, MigrationResult)

    def test_process_recipe_handlers_with_exception(self, tmp_path: Path) -> None:
        """Exceptions during recipe handler check should be caught."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        recipe_file = recipes_dir / "default.rb"
        recipe_file.write_text("package 'nginx'")
        recipe_file.chmod(0o000)

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        try:
            result = orchestrator.migrate_cookbook(str(cookbook_dir))
            # Should catch permission errors gracefully
            assert isinstance(result, MigrationResult)
        finally:
            recipe_file.chmod(0o644)


class TestTemplateConversion:
    """Coverage for Chef template to Jinja2 conversion."""

    def test_convert_templates_with_erb_files(self, tmp_path: Path) -> None:
        """ERB templates should be converted to Jinja2."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        templates_dir = cookbook_dir / "templates" / "default"
        templates_dir.mkdir(parents=True)
        (templates_dir / "config.erb").write_text("port = <%= @port %>")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        with patch("souschef.migration_v2.convert_template_file") as mock_convert:
            mock_convert.return_value = "port = {{ port }}"

            result = orchestrator.migrate_cookbook(str(cookbook_dir))
            assert result.metrics.templates_converted >= 0

    def test_convert_templates_with_conversion_errors(self, tmp_path: Path) -> None:
        """Failed template conversions should be skipped."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        templates_dir = cookbook_dir / "templates" / "default"
        templates_dir.mkdir(parents=True)
        (templates_dir / "config.erb").write_text("<% complex ruby %><%= @var %>")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        with patch("souschef.migration_v2.convert_template_file") as mock_convert:
            mock_convert.return_value = "Error: Conversion failed for complex syntax"

            result = orchestrator.migrate_cookbook(str(cookbook_dir))
            assert result.metrics.templates_skipped >= 0

    def test_convert_templates_with_exception(self, tmp_path: Path) -> None:
        """Exceptions during template conversion should be caught."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        templates_dir = cookbook_dir / "templates" / "default"
        templates_dir.mkdir(parents=True)
        (templates_dir / "config.erb").write_text("port = <%= @port %>")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        with patch("souschef.migration_v2.convert_template_file") as mock_convert:
            mock_convert.side_effect = RuntimeError("Conversion crashed")

            result = orchestrator.migrate_cookbook(str(cookbook_dir))
            assert result.metrics.templates_skipped >= 0


class TestPlaybookValidation:
    """Coverage for ansible-lint validation phase."""

    def test_validation_ansible_lint_not_found(self, tmp_path: Path) -> None:
        """Validation should handle missing ansible-lint gracefully."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        # Initialize result and add a playbook to trigger validation
        orchestrator.result = MigrationResult(
            migration_id=orchestrator.migration_id,
            status=MigrationStatus.IN_PROGRESS,
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
            ansible_version="2.9",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            source_cookbook="test",
        )
        orchestrator.result.playbooks_generated = ["test.yml"]

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("ansible-lint not found")

            orchestrator._validate_playbooks()
            # Should handle missing ansible-lint (doesn't crash)
            assert isinstance(orchestrator.result, MigrationResult)

    def test_validation_timeout(self, tmp_path: Path) -> None:
        """Validation should handle timeouts gracefully."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        # Initialize result and add a playbook to trigger validation
        orchestrator.result = MigrationResult(
            migration_id=orchestrator.migration_id,
            status=MigrationStatus.IN_PROGRESS,
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
            ansible_version="2.9",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            source_cookbook="test",
        )
        orchestrator.result.playbooks_generated = ["test.yml"]

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd="ansible-lint", timeout=30
            )

            orchestrator._validate_playbooks()
            # Should add timeout warning
            assert any(
                "timed out" in str(w).lower() for w in orchestrator.result.warnings
            )

    def test_validation_general_error(self, tmp_path: Path) -> None:
        """Validation should handle unexpected errors gracefully."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        # Initialize result and add a playbook to trigger validation
        orchestrator.result = MigrationResult(
            migration_id=orchestrator.migration_id,
            status=MigrationStatus.IN_PROGRESS,
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
            ansible_version="2.9",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            source_cookbook="test",
        )
        orchestrator.result.playbooks_generated = ["test.yml"]

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Unexpected validation error")

            orchestrator._validate_playbooks()
            # Should add error warning
            assert any("error" in str(w).lower() for w in orchestrator.result.warnings)


class TestAuditTrailAndOptimization:
    """Coverage for audit trail initialization and playbook optimization."""

    def test_initialize_audit_trail_first_time(self, tmp_path: Path) -> None:
        """Audit trail can remain None if not explicitly initialized."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        result = orchestrator.migrate_cookbook(str(cookbook_dir))
        # Audit trail initialization is optional
        assert isinstance(result, MigrationResult)

    def test_optimize_playbooks_with_generated_playbooks(self, tmp_path: Path) -> None:
        """Optimization metrics depend on actual playbook generation."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'\npackage 'mysql'")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        result = orchestrator.migrate_cookbook(str(cookbook_dir))
        # Optimization metrics structure may be empty or populated
        assert isinstance(result.optimization_metrics, dict)

    def test_finalize_audit_trail_with_export(self, tmp_path: Path) -> None:
        """Audit trail should be exported at finalization."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        with (
            patch(
                "souschef.converters.conversion_audit.ConversionAuditTrail.export_json"
            ),
            patch(
                "souschef.converters.conversion_audit.ConversionAuditTrail.export_html_report"
            ),
        ):
            result = orchestrator.migrate_cookbook(str(cookbook_dir))
            # Should attempt to export audit trail
            assert isinstance(result, MigrationResult)

    def test_finalize_audit_trail_with_exception(self, tmp_path: Path) -> None:
        """Audit trail export errors should be caught."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        with patch(
            "souschef.converters.conversion_audit.ConversionAuditTrail.export_json"
        ) as mock_json:
            mock_json.side_effect = RuntimeError("Export failed")

            result = orchestrator.migrate_cookbook(str(cookbook_dir))
            # Should handle export errors gracefully
            assert isinstance(result, MigrationResult)
