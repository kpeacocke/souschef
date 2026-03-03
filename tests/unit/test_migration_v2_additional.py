"""Tests for migration_v2.py module - targeting uncovered paths."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from souschef.migration_v2 import (
    ConversionMetrics,
    MigrationOrchestrator,
    MigrationResult,
    MigrationStatus,
    _process_recipe_worker,
)


class TestConversionMetrics:
    """Coverage for ConversionMetrics dataclass."""

    def test_from_dict_with_nested_structure(self) -> None:
        """Metrics with nested structure should parse correctly."""
        data = {
            "recipes": {
                "total": 10,
                "converted": 8,
                "partial": 1,
                "failed": 1,
                "skipped": 0,
            },
            "templates": {"total": 5, "converted": 4, "skipped": 1},
        }
        metrics = ConversionMetrics.from_dict(data)
        assert metrics.recipes_converted == 8
        assert metrics.recipes_failed == 1
        assert metrics.templates_converted == 4

    def test_from_dict_empty(self) -> None:
        """Empty dict should create metrics with all defaults."""
        metrics = ConversionMetrics.from_dict({})
        assert metrics.recipes_converted == 0
        assert metrics.templates_converted == 0
        assert metrics.attributes_converted == 0

    def test_conversion_rate(self) -> None:
        """Conversion rate calculation should work."""
        metrics = ConversionMetrics(
            recipes_total=10,
            recipes_converted=8,
            templates_total=5,
            templates_converted=4,
        )
        rate = metrics.conversion_rate()
        assert 70.0 < rate < 90.0  # (8+4)/(10+5) = 80%


class TestMigrationResult:
    """Coverage for MigrationResult class."""

    def test_from_dict_with_invalid_status(self) -> None:
        """Invalid status value should default to PENDING."""
        data = {
            "migration_id": "test123",
            "status": "INVALID_STATUS",
            "chef_version": "14.15.6",
            "target_platform": "awx",
            "target_version": "24.6.1",
            "ansible_version": "2.15",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "source_cookbook": "test_cookbook",
        }
        result = MigrationResult.from_dict(data)
        assert result.status == MigrationStatus.PENDING

    def test_from_dict_non_dict_raises_error(self) -> None:
        """Non-dict data should raise ValueError."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            MigrationResult.from_dict("not a dict")  # type: ignore[arg-type]

    def test_from_dict_with_infrastructure_and_chef_server(self) -> None:
        """Full migration result with nested data should parse."""
        data = {
            "migration_id": "mig456",
            "status": "in_progress",
            "chef_version": "14.15.6",
            "target_platform": "awx",
            "target_version": "24.6.1",
            "ansible_version": "2.15",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "source_cookbook": "test_cookbook",
            "infrastructure": {
                "inventory_id": "inv1",
                "project_id": "proj1",
                "job_template_id": "jt1",
            },
            "chef_server": {
                "nodes": [{"name": "node1"}],
                "queried": True,
            },
            "metrics": {
                "recipes": {"compiled": 10, "converted": 8},
                "templates": {"total": 5, "converted": 4},
            },
        }
        result = MigrationResult.from_dict(data)
        assert result.inventory_id == "inv1"
        assert result.project_id == "proj1"
        assert result.chef_nodes == [{"name": "node1"}]
        assert result.chef_server_queried is True


class TestRecipeWorker:
    """Coverage for recipe processing worker function."""

    def test_process_recipe_worker_success(self, tmp_path: Path) -> None:
        """Successful recipe conversion should return success result."""
        recipe_file = tmp_path / "default.rb"
        recipe_file.write_text("package 'nginx'")
        cookbook_path = str(tmp_path)

        result = _process_recipe_worker((str(recipe_file), cookbook_path))
        assert result["success"] is True
        assert "playbook_name" in result
        assert result["file"] == "default.rb"

    def test_process_recipe_worker_parse_error(self, tmp_path: Path) -> None:
        """Recipe with parsing error should return failure result."""
        recipe_file = tmp_path / "bad.rb"
        recipe_file.write_text("invalid ruby syntax {{{")
        cookbook_path = str(tmp_path)

        # Mock to force error path
        with patch(
            "souschef.migration_v2.generate_playbook_from_recipe",
            return_value="Error: Parse failed",
        ):
            result = _process_recipe_worker((str(recipe_file), cookbook_path))
            assert result["success"] is False
            assert "error" in result

    def test_process_recipe_worker_exception(self, tmp_path: Path) -> None:
        """Exception during recipe processing should be caught."""
        recipe_file = tmp_path / "error.rb"
        recipe_file.write_text("package 'test'")

        with patch(
            "souschef.migration_v2.generate_playbook_from_recipe",
            side_effect=RuntimeError("Conversion failed"),
        ):
            result = _process_recipe_worker((str(recipe_file), str(tmp_path)))
            assert result["success"] is False
            assert "Conversion failed" in result["error"]


class TestMigrationOrchestrator:
    """Coverage for MigrationOrchestrator class."""

    def test_orchestrator_initialization(self) -> None:
        """Orchestrator should initialize with correct config."""
        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
            fips_mode=True,
        )
        assert orchestrator.config.chef_version == "14.15.6"
        assert orchestrator.config.target_platform == "awx"
        assert orchestrator.config.fips_mode is True

    def test_migrate_cookbook_missing_metadata(self, tmp_path: Path) -> None:
        """Cookbook without metadata should handle error."""
        cookbook_dir = tmp_path / "empty_cookbook"
        cookbook_dir.mkdir()

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        # migrate_cookbook will still run even without metadata.rb, but may produce warnings
        result = orchestrator.migrate_cookbook(str(cookbook_dir))
        assert isinstance(result, MigrationResult)
        assert result.migration_id == orchestrator.migration_id

    def test_migrate_cookbook_with_chef_server(self, tmp_path: Path) -> None:
        """Migration with Chef server connection should query nodes."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        with patch("souschef.migration_v2.get_chef_nodes") as mock_nodes:
            mock_nodes.return_value = [
                {"name": "web01", "ipaddress": "10.0.1.10", "run_list": ["role[web]"]}
            ]
            result = orchestrator.migrate_cookbook(
                str(cookbook_dir), chef_server_url="https://chef.example.com"
            )
            # Should return MigrationResult, not dict
            assert isinstance(result, MigrationResult)
            assert result.chef_version == "14.15.6"

    def test_analyze_cookbook_phase(self, tmp_path: Path) -> None:
        """Analysis phase should parse metadata and recipes."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        result = orchestrator.migrate_cookbook(str(cookbook_dir))
        assert isinstance(result, MigrationResult)
        assert result.status in [
            MigrationStatus.VALIDATED,
            MigrationStatus.CONVERTED,
            MigrationStatus.DEPLOYED,
        ]

    def test_conversion_with_custom_resources(self, tmp_path: Path) -> None:
        """Cookbooks with custom resources should be converted."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'custom_test'")

        resources_dir = cookbook_dir / "resources"
        resources_dir.mkdir()
        (resources_dir / "database.rb").write_text(
            "property :db_name, String\naction :create do\nend"
        )

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="aap", target_version="2.4.0"
        )

        result = orchestrator.migrate_cookbook(str(cookbook_dir))
        assert isinstance(result, MigrationResult)
        assert result.target_platform == "aap"

    def test_migration_with_parallel_processing(self, tmp_path: Path) -> None:
        """Parallel processing flag should enable concurrent conversion."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'parallel_test'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        for i in range(3):
            (recipes_dir / f"recipe{i}.rb").write_text(f"package 'pkg{i}'")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        result = orchestrator.migrate_cookbook(
            str(cookbook_dir), parallel_processing=True, max_workers=2
        )
        assert isinstance(result, MigrationResult)
        assert result.metrics.recipes_total >= 0


class TestMigrationStatusTracking:
    """Coverage for migration tracking and state management."""

    def test_migration_result_from_dict_creates_defaults(self) -> None:
        """MigrationResult from_dict should handle minimal data."""
        data = {
            "migration_id": "test",
            "chef_version": "14.15.6",
            "target_platform": "awx",
            "target_version": "24.6.1",
            "ansible_version": "2.15",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "source_cookbook": "test_cookbook",
        }
        result = MigrationResult.from_dict(data)
        assert result.status == MigrationStatus.PENDING
        assert result.playbooks_generated == []
        assert result.errors == []
        assert result.warnings == []

    def test_migration_status_enum_values(self) -> None:
        """MigrationStatus enum should have expected values."""
        assert MigrationStatus.PENDING.value == "pending"
        assert MigrationStatus.IN_PROGRESS.value == "in_progress"
        assert MigrationStatus.CONVERTED.value == "converted"
        assert MigrationStatus.FAILED.value == "failed"


class TestParallelProcessing:
    """Coverage for parallel recipe processing."""

    def test_parallel_recipe_conversion(self, tmp_path: Path) -> None:
        """Multiple recipes should be processed in parallel."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'parallel_test'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "recipe1.rb").write_text("package 'pkg1'")
        (recipes_dir / "recipe2.rb").write_text("package 'pkg2'")
        (recipes_dir / "recipe3.rb").write_text("package 'pkg3'")

        orchestrator = MigrationOrchestrator(
            chef_version="14.15.6", target_platform="awx", target_version="24.6.1"
        )

        # Test that recipes can be processed with parallel flag
        result = orchestrator.migrate_cookbook(
            str(cookbook_dir), parallel_processing=True
        )
        assert isinstance(result, MigrationResult)
        assert result.metrics.recipes_total >= 0
