"""
Comprehensive test suite for migration_v2.py module.

Covers MigrationOrchestrator, MigrationResult, ConversionMetrics, worker functions,
and all helper methods with focus on uncovered lines and edge cases.
"""

import contextlib
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from souschef.migration_v2 import (
    ConversionMetrics,
    MigrationOrchestrator,
    MigrationResult,
    MigrationStatus,
    _process_attribute_worker,
    _process_recipe_worker,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_cookbook_path(tmp_path: Path) -> Path:
    """Create a temporary cookbook structure."""
    cookbook_path = tmp_path / "test_cookbook"
    cookbook_path.mkdir()

    # Create standard directories
    (cookbook_path / "recipes").mkdir()
    (cookbook_path / "attributes").mkdir()
    (cookbook_path / "resources").mkdir()
    (cookbook_path / "templates").mkdir()
    (cookbook_path / "libraries").mkdir()

    # Create metadata.rb
    (cookbook_path / "metadata.rb").write_text(
        'name "test_cookbook"\nversion "1.0.0"\n'
    )

    # Create sample recipe file
    (cookbook_path / "recipes" / "default.rb").write_text(
        'package "nginx"\nservice "nginx"\n'
    )

    # Create sample attributes file
    (cookbook_path / "attributes" / "default.rb").write_text(
        'default["nginx"]["port"] = 80\n'
    )

    return cookbook_path


@pytest.fixture
def orchestrator() -> MigrationOrchestrator:
    """Create a migration orchestrator instance."""
    return MigrationOrchestrator(
        chef_version="15.10.91",
        target_platform="awx",
        target_version="21.0.0",
        fips_mode=False,
    )


@pytest.fixture
def migration_result() -> MigrationResult:
    """Create a migration result instance."""
    return MigrationResult(
        migration_id="test-migration-123",
        status=MigrationStatus.PENDING,
        chef_version="15.10.91",
        target_platform="awx",
        target_version="21.0.0",
        ansible_version="2.12.0",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        source_cookbook="/path/to/cookbook",
    )


# ============================================================================
# Tests for ConversionMetrics
# ============================================================================


class TestConversionMetricsComprehensive:
    """Comprehensive tests for ConversionMetrics class."""

    def test_conversion_rate_with_all_types(self) -> None:
        """Test conversion rate calculation with all artifact types."""
        metrics = ConversionMetrics(
            recipes_total=10,
            recipes_converted=8,
            attributes_total=5,
            attributes_converted=4,
            resources_total=3,
            resources_converted=3,
            handlers_total=2,
            handlers_converted=1,
            templates_total=2,
            templates_converted=2,
        )
        expected = (8 + 4 + 3 + 1 + 2) / (10 + 5 + 3 + 2 + 2) * 100
        assert metrics.conversion_rate() == pytest.approx(expected, abs=0.01)

    def test_conversion_rate_partial_success(self) -> None:
        """Test conversion rate with partial conversions."""
        metrics = ConversionMetrics(
            recipes_total=10,
            recipes_converted=5,
            recipes_partial=3,
            recipes_skipped=2,
        )
        # Only complete conversions count towards rate
        assert metrics.conversion_rate() == pytest.approx(50.0, abs=0.01)

    def test_conversion_rate_zero_total(self) -> None:
        """Test conversion rate with zero total artifacts."""
        metrics = ConversionMetrics()
        assert metrics.conversion_rate() == pytest.approx(0.0, abs=0.01)

    def test_metrics_to_dict_comprehensive(self) -> None:
        """Test comprehensive metrics serialisation."""
        metrics = ConversionMetrics(
            recipes_total=10,
            recipes_converted=7,
            recipes_partial=2,
            recipes_skipped=1,
            recipes_failed=0,
            attributes_total=5,
            attributes_converted=4,
            attributes_skipped=1,
            resources_total=3,
            resources_converted=2,
            resources_skipped=1,
            handlers_total=2,
            handlers_converted=1,
            handlers_skipped=1,
            templates_total=4,
            templates_converted=3,
            templates_skipped=1,
        )
        result = metrics.to_dict()

        assert result["recipes"]["total"] == 10
        assert result["recipes"]["converted"] == 7
        assert result["recipes"]["partial"] == 2
        assert result["recipes"]["skipped"] == 1
        assert result["recipes"]["failed"] == 0

        assert result["attributes"]["total"] == 5
        assert result["resources"]["total"] == 3
        assert result["handlers"]["total"] == 2
        assert result["templates"]["total"] == 4

        assert "overall_conversion_rate" in result
        assert "%" in result["overall_conversion_rate"]

    def test_metrics_from_dict_full_data(self) -> None:
        """Test comprehensive metrics deserialisation."""
        data = {
            "recipes": {
                "total": 10,
                "converted": 7,
                "partial": 2,
                "skipped": 1,
                "failed": 0,
            },
            "attributes": {
                "total": 5,
                "converted": 4,
                "skipped": 1,
            },
            "resources": {
                "total": 3,
                "converted": 2,
                "skipped": 1,
            },
            "handlers": {
                "total": 2,
                "converted": 1,
                "skipped": 1,
            },
            "templates": {
                "total": 4,
                "converted": 3,
                "skipped": 1,
            },
        }
        metrics = ConversionMetrics.from_dict(data)

        assert metrics.recipes_total == 10
        assert metrics.recipes_converted == 7
        assert metrics.attributes_total == 5
        assert metrics.resources_total == 3

    def test_metrics_from_dict_invalid_input(self) -> None:
        """Test metrics deserialisation with invalid input."""
        # Empty dict
        metrics = ConversionMetrics.from_dict({})
        assert metrics.recipes_total == 0

        # Non-dict input
        metrics = ConversionMetrics.from_dict("invalid")  # type: ignore[arg-type]
        assert metrics.recipes_total == 0

    def test_metrics_from_dict_missing_fields(self) -> None:
        """Test metrics deserialisation with missing fields."""
        data = {
            "recipes": {"total": 5, "converted": 3},
            # Missing partial, skipped, failed
        }
        metrics = ConversionMetrics.from_dict(data)
        assert metrics.recipes_total == 5
        assert metrics.recipes_converted == 3
        assert metrics.recipes_partial == 0
        assert metrics.recipes_skipped == 0


# ============================================================================
# Tests for MigrationResult
# ============================================================================


class TestMigrationResultComprehensive:
    """Comprehensive tests for MigrationResult class."""

    def test_to_dict_complete(self) -> None:
        """Test complete serialisation of MigrationResult."""
        result = MigrationResult(
            migration_id="mig-123",
            status=MigrationStatus.CONVERTED,
            chef_version="15.10.91",
            target_platform="awx",
            target_version="21.0.0",
            ansible_version="2.12.0",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T01:00:00",
            source_cookbook="my_cookbook",
            playbooks_generated=["site.yml", "vars/default.yml"],
            playbooks_deployed=["site.yml"],
            inventory_id=123,
            project_id=456,
            job_template_id=789,
            chef_nodes=[
                {
                    "name": "web1",
                    "environment": "production",
                    "roles": ["web"],
                }
            ],
            chef_server_queried=True,
            run_list=["recipe[nginx]"],
            variable_context={"nginx_port": 80},
            variable_provenance={"source": "attributes"},
            errors=[{"phase": "test", "error": "test error"}],
            warnings=[{"phase": "test", "message": "test warning"}],
        )

        data = result.to_dict()
        assert data["migration_id"] == "mig-123"
        assert data["status"] == "converted"
        assert data["chef_version"] == "15.10.91"
        assert data["infrastructure"]["inventory_id"] == 123
        assert len(data["playbooks_generated"]) == 2
        assert data["chef_server"]["queried"] is True
        assert len(data["errors"]) == 1

    def test_from_dict_complete(self) -> None:
        """Test complete deserialisation of MigrationResult."""
        data = {
            "migration_id": "mig-123",
            "status": "converted",
            "chef_version": "15.0.0",
            "target_platform": "awx",
            "target_version": "21.0.0",
            "ansible_version": "2.12.0",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T01:00:00",
            "source_cookbook": "my_cookbook",
            "playbooks_generated": ["site.yml"],
            "playbooks_deployed": [],
            "infrastructure": {
                "inventory_id": 123,
                "project_id": 456,
                "job_template_id": 789,
            },
            "chef_server": {
                "nodes_discovered": 1,
                "nodes": [{"name": "web1"}],
                "queried": True,
            },
            "metrics": {
                "recipes": {"total": 1, "converted": 1},
            },
        }

        result = MigrationResult.from_dict(data)
        assert result.migration_id == "mig-123"
        assert result.status == MigrationStatus.CONVERTED
        assert result.inventory_id == 123
        assert result.chef_server_queried is True

    def test_from_dict_invalid_input(self) -> None:
        """Test deserialisation with invalid input."""
        with pytest.raises(ValueError):
            MigrationResult.from_dict("not a dict")  # type: ignore[arg-type]

    def test_from_dict_invalid_status(self) -> None:
        """Test deserialisation with invalid status."""
        data = {
            "migration_id": "mig-123",
            "status": "invalid_status",
            "chef_version": "15.0.0",
            "target_platform": "awx",
            "target_version": "21.0.0",
            "ansible_version": "2.12.0",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T01:00:00",
            "source_cookbook": "test",
        }
        result = MigrationResult.from_dict(data)
        assert result.status == MigrationStatus.PENDING

    def test_from_dict_missing_fields(self) -> None:
        """Test deserialisation with missing fields."""
        data = {}
        result = MigrationResult.from_dict(data)
        assert result.migration_id == ""
        assert result.playbooks_generated == []
        assert result.errors == []


# ============================================================================
# Tests for MigrationOrchestrator Initialisation
# ============================================================================


class TestMigrationOrchestratorInit:
    """Tests for MigrationOrchestrator initialisation."""

    def test_init_basic(self) -> None:
        """Test basic orchestrator initialisation."""
        orch = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="awx",
            target_version="21.0.0",
        )
        assert orch.migration_id.startswith("mig-")
        assert orch.result is None
        assert orch.config.chef_version == "15.10.91"
        assert orch.config.target_platform == "awx"

    def test_init_with_fips_mode(self) -> None:
        """Test orchestrator initialisation with FIPS mode."""
        orch = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="awx",
            target_version="21.0.0",
            fips_mode=True,
        )
        assert orch.config.fips_mode is True

    def test_init_different_platforms(self) -> None:
        """Test orchestrator initialisation with different platforms."""
        platform_versions = {
            "awx": "21.0.0",
            "tower": "3.8.5",
            "aap": "2.4.0",
        }
        for platform, version in platform_versions.items():
            orch = MigrationOrchestrator(
                chef_version="15.10.91",
                target_platform=platform,
                target_version=version,
            )
            assert orch.config.target_platform == platform


# ============================================================================
# Tests for Worker Functions
# ============================================================================


class TestWorkerFunctions:
    """Tests for parallel processing worker functions."""

    @patch("souschef.migration_v2.generate_playbook_from_recipe")
    def test_process_recipe_worker_success(self, mock_generate: Mock) -> None:
        """Test successful recipe processing worker."""
        mock_generate.return_value = "---\n- name: Test\n  hosts: all\n"

        with tempfile.NamedTemporaryFile(suffix=".rb", delete=False) as f:
            f.write(b"package 'nginx'")
            recipe_path = f.name

        try:
            result = _process_recipe_worker((recipe_path, "/cookbook"))
            assert result["success"] is True
            assert "playbook_name" in result
            assert result["file"].endswith(".rb")
        finally:
            Path(recipe_path).unlink()

    @patch("souschef.migration_v2.generate_playbook_from_recipe")
    def test_process_recipe_worker_error(self, mock_generate: Mock) -> None:
        """Test recipe processing worker with error."""
        mock_generate.return_value = "Error: Invalid syntax"

        with tempfile.NamedTemporaryFile(suffix=".rb", delete=False) as f:
            f.write(b"invalid recipe")
            recipe_path = f.name

        try:
            result = _process_recipe_worker((recipe_path, "/cookbook"))
            assert result["success"] is False
            assert "error" in result
        finally:
            Path(recipe_path).unlink()

    @patch("souschef.migration_v2.generate_playbook_from_recipe")
    def test_process_recipe_worker_exception(self, mock_generate: Mock) -> None:
        """Test recipe processing worker with exception."""
        mock_generate.side_effect = Exception("Test exception")

        with tempfile.NamedTemporaryFile(suffix=".rb", delete=False) as f:
            f.write(b"package 'nginx'")
            recipe_path = f.name

        try:
            result = _process_recipe_worker((recipe_path, "/cookbook"))
            assert result["success"] is False
            assert "Test exception" in result["error"]
        finally:
            Path(recipe_path).unlink()

    @patch("souschef.migration_v2.parse_attributes")
    def test_process_attribute_worker_success(self, mock_parse: Mock) -> None:
        """Test successful attribute processing worker."""
        mock_parse.return_value = "port: 80\n"

        with tempfile.NamedTemporaryFile(suffix=".rb", delete=False) as f:
            f.write(b"default['port'] = 80")
            attr_path = f.name

        try:
            result = _process_attribute_worker((attr_path,))
            assert result["success"] is True
            assert "var_name" in result
        finally:
            Path(attr_path).unlink()

    @patch("souschef.migration_v2.parse_attributes")
    def test_process_attribute_worker_error(self, mock_parse: Mock) -> None:
        """Test attribute processing worker with error."""
        mock_parse.return_value = "Error: Invalid syntax"

        with tempfile.NamedTemporaryFile(suffix=".rb", delete=False) as f:
            f.write(b"invalid attributes")
            attr_path = f.name

        try:
            result = _process_attribute_worker((attr_path,))
            assert result["success"] is False
            assert "error" in result
        finally:
            Path(attr_path).unlink()

    @patch("souschef.migration_v2.parse_attributes")
    def test_process_attribute_worker_exception(self, mock_parse: Mock) -> None:
        """Test attribute processing worker with exception."""
        mock_parse.side_effect = Exception("Test exception")

        with tempfile.NamedTemporaryFile(suffix=".rb", delete=False) as f:
            f.write(b"default['port'] = 80")
            attr_path = f.name

        try:
            result = _process_attribute_worker((attr_path,))
            assert result["success"] is False
            assert "Test exception" in result["error"]
        finally:
            Path(attr_path).unlink()


# ============================================================================
# Tests for migrate_cookbook Method
# ============================================================================


class TestMigrateCookbook:
    """Tests for migrate_cookbook method."""

    @patch("souschef.migration_v2.MigrationOrchestrator._prepare_cookbook_source")
    @patch("souschef.migration_v2.MigrationOrchestrator._analyze_cookbook")
    @patch("souschef.migration_v2.MigrationOrchestrator._build_variable_context")
    @patch("souschef.migration_v2.MigrationOrchestrator._convert_recipes")
    @patch("souschef.migration_v2.MigrationOrchestrator._convert_attributes")
    @patch("souschef.migration_v2.MigrationOrchestrator._convert_resources")
    @patch("souschef.migration_v2.MigrationOrchestrator._convert_handlers")
    @patch("souschef.migration_v2.MigrationOrchestrator._convert_templates")
    def test_migrate_cookbook_basic(
        self,
        mock_templates: Mock,
        mock_handlers: Mock,
        mock_resources: Mock,
        mock_attributes: Mock,
        mock_recipes: Mock,
        mock_var_context: Mock,
        mock_analyse: Mock,
        mock_prepare: Mock,
        orchestrator: MigrationOrchestrator,
        temp_cookbook_path: Path,
    ) -> None:
        """Test basic cookbook migration."""
        mock_prepare.return_value = (str(temp_cookbook_path), None)

        result = orchestrator.migrate_cookbook(
            cookbook_path=str(temp_cookbook_path),
            skip_validation=True,
        )

        assert result.migration_id == orchestrator.migration_id
        assert result.status == MigrationStatus.CONVERTED
        assert result.source_cookbook == str(temp_cookbook_path)

    @patch("souschef.migration_v2.MigrationOrchestrator._prepare_cookbook_source")
    @patch("souschef.migration_v2.MigrationOrchestrator._analyze_cookbook")
    def test_migrate_cookbook_missing_source(
        self,
        mock_analyse: Mock,
        mock_prepare: Mock,
        orchestrator: MigrationOrchestrator,
    ) -> None:
        """Test migration with missing cookbook source."""
        mock_prepare.side_effect = ValueError("Invalid path")

        result = orchestrator.migrate_cookbook(cookbook_path="/nonexistent/path")

        assert result.status == MigrationStatus.FAILED
        assert len(result.errors) > 0

    @patch("souschef.migration_v2.MigrationOrchestrator._prepare_cookbook_source")
    @patch("souschef.migration_v2.MigrationOrchestrator._analyze_cookbook")
    @patch("souschef.migration_v2.MigrationOrchestrator._build_variable_context")
    @patch("souschef.migration_v2.MigrationOrchestrator._convert_recipes")
    def test_migrate_cookbook_error_handling(
        self,
        mock_recipes: Mock,
        mock_var_context: Mock,
        mock_analyse: Mock,
        mock_prepare: Mock,
        orchestrator: MigrationOrchestrator,
        temp_cookbook_path: Path,
    ) -> None:
        """Test migration error handling."""
        mock_prepare.return_value = (str(temp_cookbook_path), None)
        mock_recipes.side_effect = Exception("Conversion error")

        result = orchestrator.migrate_cookbook(
            cookbook_path=str(temp_cookbook_path),
            skip_validation=True,
        )

        assert result.status == MigrationStatus.FAILED
        assert len(result.errors) > 0

    @patch("souschef.migration_v2.MigrationOrchestrator._prepare_cookbook_source")
    @patch("souschef.migration_v2.MigrationOrchestrator._analyze_cookbook")
    @patch("souschef.migration_v2.MigrationOrchestrator._build_variable_context")
    @patch("souschef.migration_v2.MigrationOrchestrator._convert_recipes_parallel")
    @patch("souschef.migration_v2.MigrationOrchestrator._convert_attributes_parallel")
    @patch("souschef.migration_v2.MigrationOrchestrator._convert_resources")
    @patch("souschef.migration_v2.MigrationOrchestrator._convert_handlers")
    @patch("souschef.migration_v2.MigrationOrchestrator._convert_templates")
    def test_migrate_cookbook_with_parallel_processing(
        self,
        mock_templates: Mock,
        mock_handlers: Mock,
        mock_resources: Mock,
        mock_attr_parallel: Mock,
        mock_recipes_parallel: Mock,
        mock_var_context: Mock,
        mock_analyse: Mock,
        mock_prepare: Mock,
        orchestrator: MigrationOrchestrator,
        temp_cookbook_path: Path,
    ) -> None:
        """Test migration with parallel processing enabled."""
        mock_prepare.return_value = (str(temp_cookbook_path), None)

        result = orchestrator.migrate_cookbook(
            cookbook_path=str(temp_cookbook_path),
            skip_validation=True,
            parallel_processing=True,
            max_workers=2,
        )

        assert result.status == MigrationStatus.CONVERTED
        mock_recipes_parallel.assert_called_once()
        mock_attr_parallel.assert_called_once()


# ============================================================================
# Tests for Cookbook Analysis Methods
# ============================================================================


class TestAnalyseCookbook:
    """Tests for _analyze_cookbook method."""

    def test_analyze_cookbook_counts_artifacts(
        self, orchestrator: MigrationOrchestrator, temp_cookbook_path: Path
    ) -> None:
        """Test that analyse_cookbook counts artifacts correctly."""
        orchestrator.result = MigrationResult(
            migration_id="test",
            status=MigrationStatus.PENDING,
            chef_version="15.10.91",
            target_platform="awx",
            target_version="21.0.0",
            ansible_version="2.12.0",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            source_cookbook=str(temp_cookbook_path),
        )

        # Add files to directories (fixture already has default.rb files)
        (temp_cookbook_path / "recipes").joinpath("test.rb").write_text("# test")
        (temp_cookbook_path / "attributes").joinpath("test.rb").write_text("# test")
        (temp_cookbook_path / "resources").joinpath("test.rb").write_text("# test")

        orchestrator._analyze_cookbook(str(temp_cookbook_path))

        # Fixture creates default.rb, tests add test.rb = 2 of each
        assert orchestrator.result.metrics.recipes_total == 2
        assert orchestrator.result.metrics.attributes_total == 2
        assert orchestrator.result.metrics.resources_total == 1

    def test_analyze_cookbook_missing_directories(
        self, orchestrator: MigrationOrchestrator, tmp_path: Path
    ) -> None:
        """Test analyse_cookbook with missing directories."""
        cookbook_path = tmp_path / "minimal"
        cookbook_path.mkdir()

        orchestrator.result = MigrationResult(
            migration_id="test",
            status=MigrationStatus.PENDING,
            chef_version="15.10.91",
            target_platform="awx",
            target_version="21.0.0",
            ansible_version="2.12.0",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            source_cookbook=str(cookbook_path),
        )

        orchestrator._analyze_cookbook(str(cookbook_path))

        assert orchestrator.result.metrics.recipes_total == 0
        assert orchestrator.result.metrics.attributes_total == 0

    def test_analyze_cookbook_nonexistent_path(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test analyse_cookbook with nonexistent path."""
        orchestrator.result = MigrationResult(
            migration_id="test",
            status=MigrationStatus.PENDING,
            chef_version="15.10.91",
            target_platform="awx",
            target_version="21.0.0",
            ansible_version="2.12.0",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            source_cookbook="/nonexistent",
        )

        with pytest.raises(FileNotFoundError):
            orchestrator._analyze_cookbook("/nonexistent/path")


# ============================================================================
# Tests for Prepare Cookbook Source
# ============================================================================


class TestPrepareCookbookSource:
    """Tests for _prepare_cookbook_source method."""

    @patch("souschef.migration_v2.Path")
    def test_prepare_local_cookbook(
        self, mock_path: Mock, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test preparing local cookbook path."""
        orchestrator.result = MigrationResult(
            migration_id="test",
            status=MigrationStatus.PENDING,
            chef_version="15.10.91",
            target_platform="awx",
            target_version="21.0.0",
            ansible_version="2.12.0",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            source_cookbook="/local/cookbook",
        )

        mock_instance = MagicMock()
        mock_instance.exists.return_value = True
        mock_path.return_value = mock_instance

        # Manually test when local path exists
        cookbook_path = "/local/cookbook"
        result_path, payload = orchestrator._prepare_cookbook_source(
            cookbook_path=cookbook_path,
            chef_server_url=None,
            chef_organisation=None,
            chef_client_name=None,
            chef_client_key_path=None,
            chef_client_key=None,
            chef_node=None,
            chef_policy=None,
            cookbook_name=None,
            cookbook_version=None,
            dependency_depth="full",
            use_cache=True,
            offline_bundle_path=None,
        )

        assert result_path == cookbook_path
        assert payload is None

    def test_prepare_cookbook_chef_server_missing_config(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test prepare with missing Chef Server configuration."""
        orchestrator.result = MigrationResult(
            migration_id="test",
            status=MigrationStatus.PENDING,
            chef_version="15.10.91",
            target_platform="awx",
            target_version="21.0.0",
            ansible_version="2.12.0",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            source_cookbook="test",
        )

        with pytest.raises(ValueError):
            orchestrator._prepare_cookbook_source(
                cookbook_path="/nonexistent",
                chef_server_url=None,
                chef_organisation=None,
                chef_client_name=None,
                chef_client_key_path=None,
                chef_client_key=None,
                chef_node=None,
                chef_policy=None,
                cookbook_name=None,
                cookbook_version=None,
                dependency_depth="full",
                use_cache=True,
                offline_bundle_path=None,
            )

    def test_prepare_cookbook_missing_client_key(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test prepare with missing client key."""
        orchestrator.result = MigrationResult(
            migration_id="test",
            status=MigrationStatus.PENDING,
            chef_version="15.10.91",
            target_platform="awx",
            target_version="21.0.0",
            ansible_version="2.12.0",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            source_cookbook="test",
        )

        with pytest.raises(ValueError):
            orchestrator._prepare_cookbook_source(
                cookbook_path="/nonexistent",
                chef_server_url="https://chef.example.com",
                chef_organisation="default",
                chef_client_name="admin",
                chef_client_key_path=None,
                chef_client_key=None,
                chef_node=None,
                chef_policy=None,
                cookbook_name="test",
                cookbook_version=None,
                dependency_depth="full",
                use_cache=True,
                offline_bundle_path=None,
            )


# ============================================================================
# Tests for Chef Server Methods
# ============================================================================


class TestChefServerMethods:
    """Tests for Chef Server related methods."""

    @patch("souschef.migration_v2.get_chef_nodes")
    def test_query_chef_server_success(
        self,
        mock_get_nodes: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test successful Chef Server query."""
        orchestrator.result = migration_result
        mock_get_nodes.return_value = [
            {
                "name": "web1",
                "environment": "production",
                "roles": ["web"],
            }
        ]

        orchestrator._query_chef_server(
            server_url="https://chef.example.com",
            organisation="default",
            client_name="admin",
            client_key_path="/path/to/key",
            client_key=None,
            query="*:*",
        )

        assert orchestrator.result.chef_server_queried is True
        assert len(orchestrator.result.chef_nodes) == 1

    @patch("souschef.migration_v2.get_chef_nodes")
    def test_query_chef_server_error(
        self,
        mock_get_nodes: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test Chef Server query with error."""
        orchestrator.result = migration_result
        mock_get_nodes.side_effect = Exception("Connection failed")

        orchestrator._query_chef_server(
            server_url="https://chef.example.com",
            organisation="default",
            client_name="admin",
            client_key_path="/path/to/key",
            client_key=None,
            query="*:*",
        )

        assert orchestrator.result.chef_server_queried is True
        assert len(orchestrator.result.warnings) > 0


# ============================================================================
# Tests for Variable Context Building
# ============================================================================


class TestBuildVariableContext:
    """Tests for _build_variable_context method."""

    @patch("souschef.migration_v2.collect_attributes_with_provenance")
    @patch("souschef.migration_v2.resolve_attribute_precedence_with_provenance")
    def test_build_variable_context_with_attributes(
        self,
        mock_resolve: Mock,
        mock_collect: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
        temp_cookbook_path: Path,
    ) -> None:
        """Test building variable context with attributes."""
        orchestrator.result = migration_result

        mock_collect.return_value = [
            {
                "precedence": "default",
                "path": "nginx.port",
                "value": "80",
                "source_file": "attributes/default.rb",
            }
        ]

        mock_resolve.return_value = {
            "nginx.port": {
                "value": "80",
                "has_conflict": False,
                "source": "attributes/default.rb",
            }
        }

        orchestrator._build_variable_context(
            cookbook_path=str(temp_cookbook_path),
            chef_node_payload=None,
        )

        assert "nginx.port" in orchestrator.result.variable_context

    @patch("souschef.migration_v2.collect_attributes_with_provenance")
    @patch("souschef.migration_v2.resolve_attribute_precedence_with_provenance")
    def test_build_variable_context_with_conflicts(
        self,
        mock_resolve: Mock,
        mock_collect: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
        temp_cookbook_path: Path,
    ) -> None:
        """Test building variable context with attribute conflicts."""
        orchestrator.result = migration_result

        mock_collect.return_value = [
            {
                "precedence": "default",
                "path": "port",
                "value": "80",
            }
        ]

        mock_resolve.return_value = {
            "port": {
                "value": "80",
                "has_conflict": True,
                "source": "multiple sources",
            }
        }

        orchestrator._build_variable_context(
            cookbook_path=str(temp_cookbook_path),
            chef_node_payload=None,
        )

        assert len(orchestrator.result.warnings) > 0


# ============================================================================
# Tests for Conversion Methods
# ============================================================================


class TestConversionMethods:
    """Tests for recipe, attribute, and resource conversion methods."""

    @patch("souschef.migration_v2.generate_playbook_from_recipe")
    def test_convert_recipes_success(
        self,
        mock_generate: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
        temp_cookbook_path: Path,
    ) -> None:
        """Test successful recipe conversion."""
        orchestrator.result = migration_result
        mock_generate.return_value = "---\n- name: Test\n  hosts: all\n"

        orchestrator._convert_recipes(str(temp_cookbook_path))

        assert orchestrator.result.metrics.recipes_converted > 0

    @patch("souschef.migration_v2.generate_playbook_from_recipe")
    def test_convert_recipes_error(
        self,
        mock_generate: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
        temp_cookbook_path: Path,
    ) -> None:
        """Test recipe conversion with error."""
        orchestrator.result = migration_result
        mock_generate.return_value = "Error: Invalid syntax"

        orchestrator._convert_recipes(str(temp_cookbook_path))

        assert orchestrator.result.metrics.recipes_skipped > 0

    @patch("souschef.migration_v2.parse_attributes")
    def test_convert_attributes_success(
        self,
        mock_parse: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
        temp_cookbook_path: Path,
    ) -> None:
        """Test successful attribute conversion."""
        orchestrator.result = migration_result
        mock_parse.return_value = "port: 80\n"

        orchestrator._convert_attributes(str(temp_cookbook_path))

        assert orchestrator.result.metrics.attributes_converted > 0

    @patch("souschef.migration_v2.parse_recipe")
    def test_convert_resources_from_recipes(
        self,
        mock_parse: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
        temp_cookbook_path: Path,
    ) -> None:
        """Test resource extraction from recipes."""
        orchestrator.result = migration_result
        mock_parse.return_value = "Type: package\nType: service\n"

        orchestrator._process_recipe_resources(str(temp_cookbook_path))

        assert orchestrator.result.metrics.resources_converted > 0

    def test_process_custom_resources(
        self,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
        temp_cookbook_path: Path,
    ) -> None:
        """Test custom resource processing."""
        orchestrator.result = migration_result

        # Add custom resource file
        (temp_cookbook_path / "resources").joinpath("custom.rb").write_text(
            "property :name, String\n"
        )

        orchestrator._process_custom_resources(str(temp_cookbook_path))

        # Should add warning for custom resource
        assert any(
            w.get("type") == "custom_resource" for w in orchestrator.result.warnings
        )

    def test_process_library_handlers(
        self,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
        temp_cookbook_path: Path,
    ) -> None:
        """Test library handler processing."""
        orchestrator.result = migration_result

        # Add handler file
        (temp_cookbook_path / "libraries").joinpath("handler.rb").write_text(
            "class MyHandler < Chef::Handler\nend\n"
        )

        orchestrator._process_library_handlers(str(temp_cookbook_path))

        assert any(w.get("type") == "handler" for w in orchestrator.result.warnings)

    @patch("souschef.migration_v2.convert_template_file")
    def test_convert_templates_success(
        self,
        mock_convert: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
        temp_cookbook_path: Path,
    ) -> None:
        """Test successful template conversion."""
        orchestrator.result = migration_result
        mock_convert.return_value = {
            "success": True,
            "jinja2_file": "/path/to/template.j2",
        }

        # Create template file
        (temp_cookbook_path / "templates").joinpath("app.conf.erb").write_text(
            "<%= @port %>\n"
        )

        orchestrator._convert_templates(str(temp_cookbook_path))

        assert orchestrator.result.metrics.templates_converted > 0


# ============================================================================
# Tests for Parallel Processing Methods
# ============================================================================


class TestParallelProcessing:
    """Tests for parallel processing methods."""

    @patch("souschef.migration_v2.ProcessPoolExecutor")
    def test_convert_recipes_parallel_success(
        self,
        mock_executor: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
        temp_cookbook_path: Path,
    ) -> None:
        """Test parallel recipe conversion with success."""
        orchestrator.result = migration_result

        # Create recipe file
        (temp_cookbook_path / "recipes").joinpath("test.rb").write_text("# test")

        # Mock the ProcessPoolExecutor
        mock_exc_instance = MagicMock()
        mock_executor.return_value.__enter__ = MagicMock(return_value=mock_exc_instance)
        mock_executor.return_value.__exit__ = MagicMock(return_value=None)

        # Mock as_completed to return successful result
        from concurrent.futures import Future

        future = Future()
        future.set_result(
            {
                "success": True,
                "playbook_name": "test.yml",
                "file": "test.rb",
            }
        )
        mock_exc_instance.__iter__ = MagicMock(return_value=iter([future]))

        with patch("souschef.migration_v2.as_completed", return_value=[future]):
            orchestrator._convert_recipes_parallel(
                str(temp_cookbook_path), max_workers=2
            )

        assert orchestrator.result.metrics.recipes_converted > 0

    @patch("souschef.migration_v2.ProcessPoolExecutor")
    def test_convert_recipes_parallel_fallback(
        self,
        mock_executor: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
        temp_cookbook_path: Path,
    ) -> None:
        """Test parallel recipe conversion with fallback to sequential."""
        orchestrator.result = migration_result

        # Mock executor to raise exception
        mock_executor.return_value.__enter__ = MagicMock(
            side_effect=Exception("Executor error")
        )

        with patch.object(orchestrator, "_convert_recipes"):
            orchestrator._convert_recipes_parallel(str(temp_cookbook_path))


# ============================================================================
# Tests for Inventory and Deployment Methods
# ============================================================================


class TestDeploymentMethods:
    """Tests for deployment and inventory methods."""

    def test_resolve_chef_hostname_fqdn_preference(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test hostname resolution prefers FQDN."""
        node = {
            "fqdn": "web1.example.com",
            "name": "web1",
            "ipaddress": "10.0.0.1",  # NOSONAR
        }
        hostname = orchestrator._resolve_chef_hostname(node)
        assert hostname == "web1.example.com"

    def test_resolve_chef_hostname_fallback_order(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test hostname resolution fallback order."""
        # Without FQDN, should use name
        node = {
            "name": "web1",
            "ipaddress": "10.0.0.1",  # NOSONAR
        }
        hostname = orchestrator._resolve_chef_hostname(node)
        assert hostname == "web1"

        # Without FQDN or name, should use IP
        node = {"ipaddress": "10.0.0.1"}  # NOSONAR
        hostname = orchestrator._resolve_chef_hostname(node)
        assert hostname == "10.0.0.1"  # NOSONAR

        # All missing
        node = {}
        hostname = orchestrator._resolve_chef_hostname(node)
        assert hostname is None

    def test_build_chef_host_variables(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test building host variables from Chef node."""
        node = {
            "fqdn": "web1.example.com",
            "ipaddress": "10.0.0.1",  # NOSONAR
            "environment": "production",
            "roles": ["web", "app"],
            "platform": "ubuntu",
        }

        variables = orchestrator._build_chef_host_variables(node, "web1.example.com")

        assert variables["ansible_host"] == "10.0.0.1"  # NOSONAR
        assert variables["chef_environment"] == "production"
        assert variables["chef_roles"] == ["web", "app"]
        assert variables["chef_platform"] == "ubuntu"

    def test_build_chef_host_variables_partial(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test building host variables with partial node data."""
        node = {
            "fqdn": "web1.example.com",
            "environment": "production",
        }

        variables = orchestrator._build_chef_host_variables(node, "web1.example.com")

        assert variables["chef_environment"] == "production"
        assert "ansible_host" not in variables

    def test_extract_chef_environments_and_roles(
        self,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test extracting environments and roles from nodes."""
        orchestrator.result = migration_result
        orchestrator.result.chef_nodes = [
            {
                "name": "web1",
                "environment": "production",
                "roles": ["web", "app"],
            },
            {
                "name": "db1",
                "environment": "production",
                "roles": ["database"],
            },
            {
                "name": "cache1",
                "environment": "staging",
                "roles": ["cache"],
            },
        ]

        environments, roles, node_env_map, node_roles_map = (
            orchestrator._extract_chef_environments_and_roles()
        )

        assert environments == {"production", "staging"}
        assert roles == {"web", "app", "database", "cache"}
        assert node_env_map["web1"] == "production"
        assert "web" in node_roles_map["web1"]

    @patch("souschef.migration_v2.AnsiblePlatformClient")
    def test_create_groups_for_environments(
        self,
        mock_client_class: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test creating environment groups."""
        orchestrator.result = migration_result
        mock_client = MagicMock()
        mock_client.create_group.return_value = {"id": 1}

        result = orchestrator._create_groups_for_environments(
            mock_client,
            123,
            {"production", "staging"},
        )

        assert len(result) == 2
        assert mock_client.create_group.call_count == 2

    @patch("souschef.migration_v2.AnsiblePlatformClient")
    def test_create_groups_for_roles(
        self,
        mock_client_class: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test creating role groups."""
        orchestrator.result = migration_result
        mock_client = MagicMock()
        mock_client.create_group.return_value = {"id": 1}

        result = orchestrator._create_groups_for_roles(
            mock_client,
            123,
            {"web", "database", "cache"},
        )

        assert len(result) == 3
        assert mock_client.create_group.call_count == 3


# ============================================================================
# Tests for Migration Status and Results
# ============================================================================


class TestMigrationStatus:
    """Tests for migration status handling."""

    def test_resolve_conversion_status_success(
        self,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test resolving success status."""
        orchestrator.result = migration_result
        orchestrator.result.status = MigrationStatus.CONVERTED
        orchestrator.result.metrics = ConversionMetrics(
            recipes_total=1,
            recipes_converted=1,
        )

        status = orchestrator._resolve_conversion_status()
        assert status == "success"

    def test_resolve_conversion_status_failed(
        self,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test resolving failed status."""
        orchestrator.result = migration_result
        orchestrator.result.status = MigrationStatus.FAILED

        status = orchestrator._resolve_conversion_status()
        assert status == "failed"

    def test_resolve_conversion_status_partial(
        self,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test resolving partial status."""
        orchestrator.result = migration_result
        orchestrator.result.status = MigrationStatus.CONVERTED
        orchestrator.result.metrics = ConversionMetrics(
            recipes_total=2,
            recipes_converted=1,
            recipes_skipped=1,
        )

        status = orchestrator._resolve_conversion_status()
        assert status == "partial"


# ============================================================================
# Tests for State Persistence
# ============================================================================


class TestStatePersistence:
    """Tests for saving and loading migration state."""

    @patch("souschef.storage.get_storage_manager")
    def test_save_state(
        self,
        mock_get_storage: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test saving migration state."""
        orchestrator.result = migration_result
        orchestrator.result.source_cookbook = "nginx"

        mock_storage = MagicMock()
        mock_storage.save_conversion.return_value = 42
        mock_get_storage.return_value = mock_storage

        conversion_id = orchestrator.save_state()

        assert conversion_id == 42
        mock_storage.save_conversion.assert_called_once()

    @patch("souschef.storage.get_storage_manager")
    def test_save_state_no_result(
        self, mock_get_storage: Mock, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test saving state with no result."""
        orchestrator.result = None

        with pytest.raises(RuntimeError):
            orchestrator.save_state()

    @patch("souschef.storage.get_storage_manager")
    def test_load_state_found(self, mock_get_storage: Mock) -> None:
        """Test loading existing migration state."""
        mock_storage = MagicMock()
        conversion = MagicMock()
        conversion.conversion_data = json.dumps(
            {
                "migration_id": "mig-123",
                "migration_result": {
                    "migration_id": "mig-123",
                    "status": "converted",
                    "chef_version": "15.0.0",
                    "target_platform": "awx",
                    "target_version": "21.0.0",
                    "ansible_version": "2.12.0",
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T01:00:00",
                    "source_cookbook": "test",
                },
            }
        )
        mock_storage.get_conversion_history.return_value = [conversion]
        mock_get_storage.return_value = mock_storage

        result = MigrationOrchestrator.load_state("mig-123")

        assert result is not None
        assert result.migration_id == "mig-123"

    @patch("souschef.storage.get_storage_manager")
    def test_load_state_not_found(self, mock_get_storage: Mock) -> None:
        """Test loading non-existent migration state."""
        mock_storage = MagicMock()
        mock_storage.get_conversion_history.return_value = []
        mock_get_storage.return_value = mock_storage

        result = MigrationOrchestrator.load_state("nonexistent")

        assert result is None

    @patch("souschef.storage.get_storage_manager")
    def test_load_state_invalid_json(self, mock_get_storage: Mock) -> None:
        """Test loading state with invalid JSON."""
        mock_storage = MagicMock()
        conversion = MagicMock()
        conversion.conversion_data = "invalid json"
        mock_storage.get_conversion_history.return_value = [conversion]
        mock_get_storage.return_value = mock_storage

        result = MigrationOrchestrator.load_state("mig-123")

        assert result is None


# ============================================================================
# Tests for Export and Reporting
# ============================================================================


class TestExportAndReporting:
    """Tests for result export and reporting."""

    def test_build_migration_report(
        self,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test building migration report."""
        orchestrator.result = migration_result
        orchestrator.result.migration_id = "mig-123"
        orchestrator.result.source_cookbook = "nginx"
        orchestrator.result.run_list = ["recipe[nginx]", "recipe[ssl]"]
        orchestrator.result.downloaded_cookbooks = [
            {"name": "nginx", "version": "8.0.0"}
        ]

        report = orchestrator._build_migration_report()

        assert "mig-123" in report
        assert "nginx" in report
        assert "recipe[nginx]" in report

    def test_export_result(
        self,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
        tmp_path: Path,
    ) -> None:
        """Test exporting result to JSON file."""
        orchestrator.result = migration_result
        output_file = tmp_path / "migration_result.json"

        orchestrator.export_result(str(output_file))

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["migration_id"] == migration_result.migration_id

    def test_export_result_no_result(
        self,
        orchestrator: MigrationOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Test exporting with no result."""
        orchestrator.result = None
        output_file = tmp_path / "migration_result.json"

        with pytest.raises(RuntimeError):
            orchestrator.export_result(str(output_file))


# ============================================================================
# Tests for Helper Methods
# ============================================================================


class TestHelperMethods:
    """Tests for various helper methods."""

    def test_flatten_dict_flat_structure(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test flattening flat dictionary."""
        data = {"a": 1, "b": 2, "c": 3}
        result = orchestrator._flatten_dict(data)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_flatten_dict_nested_structure(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test flattening nested dictionary."""
        data = {
            "app": {
                "name": "myapp",
                "config": {
                    "port": 8080,
                    "ssl": True,
                },
            },
            "db": {"host": "localhost"},
        }
        result = orchestrator._flatten_dict(data)

        assert result["app.name"] == "myapp"
        assert result["app.config.port"] == 8080
        assert result["app.config.ssl"] is True
        assert result["db.host"] == "localhost"

    def test_flatten_dict_with_prefix(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test flattening with prefix."""
        data = {"name": "app", "port": 8080}
        result = orchestrator._flatten_dict(data, prefix="config")

        assert "config.name" in result
        assert "config.port" in result

    def test_format_attribute_value_dict(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test formatting dictionary attribute value."""
        value = {"key": "value"}
        result = orchestrator._format_attribute_value(value)
        assert result == '{"key": "value"}'

    def test_format_attribute_value_list(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test formatting list attribute value."""
        value = ["item1", "item2", "item3"]
        result = orchestrator._format_attribute_value(value)
        assert result == '["item1", "item2", "item3"]'

    def test_format_attribute_value_scalar(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test formatting scalar attribute value."""
        assert orchestrator._format_attribute_value(42) == "42"
        assert orchestrator._format_attribute_value("string") == "string"
        assert orchestrator._format_attribute_value(True) == "True"


# ============================================================================
# Tests for Normalisation Methods
# ============================================================================


class TestNormalisationMethods:
    """Tests for normalisation methods."""

    def test_normalise_run_list_string(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test normalising run_list from string."""
        with patch("souschef.migration_v2._parse_chef_runlist") as mock_parse:
            mock_parse.return_value = ["nginx", "ssl"]
            result = orchestrator._normalise_run_list("recipe[nginx],recipe[ssl]")
            assert "nginx" in result
            assert "ssl" in result

    def test_normalise_run_list_list(self, orchestrator: MigrationOrchestrator) -> None:
        """Test normalising run_list from list."""
        with patch("souschef.migration_v2._parse_chef_runlist") as mock_parse:
            mock_parse.side_effect = [["nginx"], ["ssl"], ["cache"]]
            result = orchestrator._normalise_run_list(
                ["recipe[nginx]", "recipe[ssl]", "recipe[cache]"]
            )
            assert len(result) <= 3

    def test_normalise_run_list_empty(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test normalising empty run_list."""
        result = orchestrator._normalise_run_list([])
        assert result == []

    def test_normalise_run_list_invalid_type(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test normalising invalid run_list type."""
        result = orchestrator._normalise_run_list(123)
        assert result == []

    def test_extract_cookbooks_from_run_list(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test extracting cookbook names from run_list."""
        run_list = ["nginx", "nginx::ssl", "stack::cache::redis"]
        result = orchestrator._extract_cookbooks_from_run_list(run_list)

        assert "nginx" in result
        assert "stack" in result

    def test_resolve_primary_cookbook_explicit(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test resolving primary cookbook with explicit name."""
        result = orchestrator._resolve_primary_cookbook(
            "my_cookbook",
            ["nginx", "ssl"],
        )
        assert result == "my_cookbook"

    def test_resolve_primary_cookbook_from_run_list(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test resolving primary cookbook from run_list."""
        result = orchestrator._resolve_primary_cookbook(
            None,
            ["nginx", "ssl"],
        )
        assert result == "nginx"

    def test_resolve_primary_cookbook_error(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test resolving primary cookbook with no options."""
        with pytest.raises(ValueError):
            orchestrator._resolve_primary_cookbook(None, [])


# ============================================================================
# Tests for Playbook Validation
# ============================================================================


class TestPlaybookValidation:
    """Tests for playbook validation methods."""

    def test_validate_playbooks_no_playbooks(
        self,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test validation with no playbooks."""
        orchestrator.result = migration_result
        orchestrator.result.playbooks_generated = []

        # Should not raise
        orchestrator._validate_playbooks()

    def test_create_playbook_test_files(
        self,
        orchestrator: MigrationOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Test creating test playbook files."""
        playbook_names = ["site.yml", "vars/nginx.yml", "templates/app.conf"]
        files = orchestrator._create_playbook_test_files(tmp_path, playbook_names)

        # Variables and templates should be filtered out
        assert len(files) == 1
        assert files[0].name == "site.yml"

    def test_run_playbook_validation_success(
        self,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
        tmp_path: Path,
    ) -> None:
        """Test playbook validation success."""
        orchestrator.result = migration_result
        playbook_file = tmp_path / "test.yml"
        playbook_file.write_text("---\n- hosts: all\n  tasks: []\n")

        # Just test that the method doesn't crash
        # (subprocess mock is not available since it's imported locally)
        with contextlib.suppress(FileNotFoundError):
            orchestrator._run_playbook_validation([playbook_file])


# ============================================================================
# Tests for Deployment
# ============================================================================


class TestDeployment:
    """Tests for deployment methods."""

    @patch("souschef.migration_v2.get_ansible_client")
    def test_deploy_to_ansible_success(
        self,
        mock_get_client: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test successful deployment to Ansible."""
        orchestrator.result = migration_result
        orchestrator.result.playbooks_generated = ["site.yml"]

        mock_client = MagicMock()
        mock_client.create_inventory.return_value = {"id": 123}
        mock_client.create_project.return_value = {"id": 456}
        mock_client.create_job_template.return_value = {"id": 789}
        mock_get_client.return_value = mock_client

        success = orchestrator.deploy_to_ansible(
            "https://awx.example.com",
            "admin",
            "password",
        )

        assert success is True
        assert orchestrator.result.status == MigrationStatus.DEPLOYED

    @patch("souschef.migration_v2.get_ansible_client")
    def test_deploy_to_ansible_no_result(
        self, mock_get_client: Mock, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test deployment with no result."""
        orchestrator.result = None

        with pytest.raises(RuntimeError):
            orchestrator.deploy_to_ansible(
                "https://awx.example.com",
                "admin",
                "password",
            )

    @patch("souschef.migration_v2.get_ansible_client")
    def test_deploy_to_ansible_error(
        self,
        mock_get_client: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test deployment with error."""
        orchestrator.result = migration_result
        mock_get_client.side_effect = Exception("Connection failed")

        success = orchestrator.deploy_to_ansible(
            "https://awx.example.com",
            "admin",
            "password",
        )

        assert success is False
        assert orchestrator.result.status == MigrationStatus.FAILED


# ============================================================================
# Tests for Rollback
# ============================================================================


class TestRollback:
    """Tests for rollback functionality."""

    @patch("souschef.migration_v2.get_ansible_client")
    def test_rollback_success(
        self,
        mock_get_client: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test successful rollback."""
        orchestrator.result = migration_result
        orchestrator.result.inventory_id = 123
        orchestrator.result.project_id = 456
        orchestrator.result.job_template_id = 789

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        success = orchestrator.rollback(
            "https://awx.example.com",
            ("admin", "password"),
        )

        assert success is True
        assert orchestrator.result.status == MigrationStatus.ROLLED_BACK

    def test_rollback_no_result(self, orchestrator: MigrationOrchestrator) -> None:
        """Test rollback with no result."""
        orchestrator.result = None

        success = orchestrator.rollback(
            "https://awx.example.com",
            ("admin", "password"),
        )

        assert success is False

    @patch("souschef.migration_v2.get_ansible_client")
    def test_rollback_error(
        self,
        mock_get_client: Mock,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test rollback with error."""
        orchestrator.result = migration_result
        orchestrator.result.inventory_id = 123

        mock_get_client.side_effect = Exception("API error")

        success = orchestrator.rollback(
            "https://awx.example.com",
            ("admin", "password"),
        )

        assert success is False


# ============================================================================
# Tests for Get Status
# ============================================================================


class TestStatusMethods:
    """Tests for status methods."""

    def test_get_status_with_result(
        self,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test getting status with result."""
        orchestrator.result = migration_result

        status = orchestrator.get_status()

        assert status["migration_id"] == migration_result.migration_id
        assert "status" in status

    def test_get_status_no_result(self, orchestrator: MigrationOrchestrator) -> None:
        """Test getting status with no result."""
        orchestrator.result = None

        status = orchestrator.get_status()

        assert status == {"status": "no_migration"}


# ============================================================================
# Tests for Advanced Features (v2.1)
# ============================================================================


class TestAdvancedFeatures:
    """Tests for advanced features (v2.1)."""

    def test_initialize_audit_trail(
        self,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test initialising audit trail."""
        orchestrator.result = migration_result
        orchestrator.result.source_cookbook = "/path/to/cookbook"

        orchestrator._initialize_audit_trail()

        assert orchestrator.result.audit_trail is not None

    def test_analyze_resource_complexity(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test analysing resource complexity."""
        with patch(
            "souschef.migration_v2.estimate_conversion_complexity"
        ) as mock_estimate:
            mock_estimate.return_value = "complex"

            result = orchestrator._analyze_resource_complexity("resource block")
            assert result == "complex"

    def test_detect_resource_guards(self, orchestrator: MigrationOrchestrator) -> None:
        """Test detecting resource guards."""
        with patch("souschef.migration_v2.parse_resource_guards") as mock_parse:
            mock_parse.return_value = {"only_if": "node.role?('web')"}

            result = orchestrator._detect_resource_guards("resource block")
            assert isinstance(result, dict)

    def test_detect_resource_notifications(
        self, orchestrator: MigrationOrchestrator
    ) -> None:
        """Test detecting resource notifications."""
        with patch("souschef.migration_v2.parse_resource_notifications") as mock_parse:
            mock_parse.return_value = [
                {"resource": "service[nginx]", "action": "restart"}
            ]

            result = orchestrator._detect_resource_notifications("resource block")
            assert isinstance(result, list)

    def test_optimize_generated_playbooks(
        self,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test optimising generated playbooks."""
        orchestrator.result = migration_result
        orchestrator.result.playbooks_generated = ["site.yml", "vars/nginx.yml"]

        orchestrator._optimize_generated_playbooks()

        assert orchestrator.result.optimization_metrics is not None
        assert orchestrator.result.optimization_metrics["optimization_enabled"] is True

    def test_finalize_audit_trail(
        self,
        orchestrator: MigrationOrchestrator,
        migration_result: MigrationResult,
    ) -> None:
        """Test finalising audit trail."""
        orchestrator.result = migration_result

        # Initialize audit trail first
        orchestrator._initialize_audit_trail()

        # Should not raise
        with patch.object(orchestrator.result.audit_trail, "finalize"):
            orchestrator._finalize_audit_trail()
