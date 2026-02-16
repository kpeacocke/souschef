"""
Tests for SousChef v2.0 Migration Orchestrator and API Clients.

Tests complete migration workflows with real and mocked APIs.
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, call, patch

import pytest

from souschef.api_clients import (
    AAPClient,
    AWXClient,
    ChefServerClient,
    TowerClient,
    get_ansible_client,
)
from souschef.migration_v2 import (
    ConversionMetrics,
    MigrationOrchestrator,
    MigrationResult,
    MigrationStatus,
)
from souschef.storage.database import StorageManager


class TestConversionMetrics:
    """Test conversion metrics tracking."""

    def test_conversion_rate_calculation(self) -> None:
        """Test conversion rate calculation."""
        metrics = ConversionMetrics(
            recipes_total=10,
            recipes_converted=8,
            attributes_total=5,
            attributes_converted=5,
        )
        assert metrics.conversion_rate() == pytest.approx(86.67, abs=0.01)

    def test_conversion_rate_zero(self) -> None:
        """Test conversion rate with no artifacts."""
        metrics = ConversionMetrics()
        assert metrics.conversion_rate() == 0.0

    def test_metrics_to_dict(self) -> None:
        """Test metrics serialization."""
        metrics = ConversionMetrics(
            recipes_total=10,
            recipes_converted=7,
            recipes_partial=2,
            recipes_skipped=1,
        )
        result = metrics.to_dict()

        assert result["recipes"]["total"] == 10
        assert result["recipes"]["converted"] == 7
        assert result["recipes"]["partial"] == 2
        assert "overall_conversion_rate" in result

    def test_metrics_from_dict(self) -> None:
        """Test metrics deserialisation."""
        data = {
            "recipes": {
                "total": 3,
                "converted": 2,
                "partial": 1,
                "skipped": 0,
                "failed": 0,
            },
            "attributes": {"total": 1, "converted": 0, "skipped": 1},
            "resources": {"total": 2, "converted": 0, "skipped": 2},
            "handlers": {"total": 1, "converted": 0, "skipped": 1},
            "templates": {"total": 2, "converted": 1, "skipped": 1},
        }

        metrics = ConversionMetrics.from_dict(data)

        assert metrics.recipes_total == 3
        assert metrics.attributes_skipped == 1
        assert metrics.resources_skipped == 2
        assert metrics.handlers_skipped == 1
        assert metrics.templates_skipped == 1


class TestMigrationResult:
    """Test migration result tracking."""

    def test_migration_result_creation(self) -> None:
        """Test creating migration result."""
        result = MigrationResult(
            migration_id="test-001",
            status=MigrationStatus.PENDING,
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
            ansible_version="2.15.0",
            created_at="2026-02-16T10:00:00",
            updated_at="2026-02-16T10:00:00",
            source_cookbook="/path/to/cookbook",
        )

        assert result.migration_id == "test-001"
        assert result.status == MigrationStatus.PENDING

    def test_migration_result_to_dict(self) -> None:
        """Test result serialization."""
        result = MigrationResult(
            migration_id="test-001",
            status=MigrationStatus.CONVERTED,
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
            ansible_version="2.15.0",
            created_at="2026-02-16T10:00:00",
            updated_at="2026-02-16T10:00:00",
            source_cookbook="/path/to/cookbook",
            playbooks_generated=["main.yml", "config.yml"],
            inventory_id=1,
        )

        result_dict = result.to_dict()
        assert result_dict["status"] == "converted"
        assert len(result_dict["playbooks_generated"]) == 2
        assert result_dict["infrastructure"]["inventory_id"] == 1

    def test_migration_result_from_dict(self) -> None:
        """Test result deserialisation."""
        result = MigrationResult(
            migration_id="test-002",
            status=MigrationStatus.VALIDATED,
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
            ansible_version="2.15.0",
            created_at="2026-02-16T10:00:00",
            updated_at="2026-02-16T10:30:00",
            source_cookbook="/path/to/cookbook",
            playbooks_generated=["site.yml"],
            inventory_id=2,
        )

        payload = result.to_dict()
        restored = MigrationResult.from_dict(payload)

        assert restored.migration_id == result.migration_id
        assert restored.status == MigrationStatus.VALIDATED
        assert restored.inventory_id == 2
        assert restored.playbooks_generated == ["site.yml"]


class TestMigrationOrchestrator:
    """Test migration orchestration."""

    def test_orchestrator_initialization(self) -> None:
        """Test orchestrator setup."""
        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        assert orchestrator.config.chef_version == "15.10.91"
        assert orchestrator.config.target_platform == "aap"
        assert orchestrator.config.ansible_version == "2.15.0"

    def test_migrate_cookbook_analyzes_structure(self, tmp_path: Path) -> None:
        """Test that migration analyzes cookbook structure."""
        # Create test cookbook structure
        cookbook = tmp_path / "test_cookbook"
        cookbook.mkdir()
        recipes = cookbook / "recipes"
        recipes.mkdir()
        (recipes / "default.rb").write_text("execute 'test'")
        (recipes / "setup.rb").write_text("package 'git'")

        attributes = cookbook / "attributes"
        attributes.mkdir()
        (attributes / "default.rb").write_text("default['app'] = 'value'")

        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        result = orchestrator.migrate_cookbook(str(cookbook), skip_validation=True)

        assert result.metrics.recipes_total == 2
        assert result.metrics.attributes_total == 1
        assert result.status in (
            MigrationStatus.CONVERTED,
            MigrationStatus.VALIDATED,
        )

    @patch("souschef.migration_v2.get_chef_nodes")
    def test_migrate_cookbook_queries_chef_server(
        self, mock_get_nodes: Mock, tmp_path: Path
    ) -> None:
        """Test that migration queries Chef Server when configured."""
        cookbook = tmp_path / "test_cookbook"
        recipes = cookbook / "recipes"
        recipes.mkdir(parents=True)
        (recipes / "default.rb").write_text("package 'curl'")

        mock_get_nodes.return_value = [{"name": "node-1"}]

        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        result = orchestrator.migrate_cookbook(
            str(cookbook),
            skip_validation=True,
            chef_server_url="https://chef.example.com",
            chef_organisation="default",
            chef_client_name="validator",
            chef_client_key="dummy-key",
            chef_query="*:*",
        )

        assert result.chef_server_queried is True
        assert result.chef_nodes == [{"name": "node-1"}]
        mock_get_nodes.assert_called_once_with(
            search_query="*:*",
            server_url="https://chef.example.com",
            organisation="default",
            client_name="validator",
            client_key_path=None,
            client_key="dummy-key",
        )

    def test_migrate_cookbook_warns_on_missing_chef_key(self, tmp_path: Path) -> None:
        """Test warning when Chef Server config is incomplete."""
        cookbook = tmp_path / "test_cookbook"
        recipes = cookbook / "recipes"
        recipes.mkdir(parents=True)
        (recipes / "default.rb").write_text("package 'curl'")

        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        result = orchestrator.migrate_cookbook(
            str(cookbook),
            skip_validation=True,
            chef_server_url="https://chef.example.com",
            chef_organisation="default",
            chef_client_name="validator",
        )

        assert result.chef_server_queried is False
        assert any(
            "missing client key" in warning.get("message", "")
            for warning in result.warnings
        )

    def test_populate_inventory_from_chef_nodes(self) -> None:
        """Test inventory population from Chef nodes."""
        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        orchestrator.result = MigrationResult(
            migration_id="test-001",
            status=MigrationStatus.CONVERTED,
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
            ansible_version="2.15.0",
            created_at="2026-02-16T10:00:00",
            updated_at="2026-02-16T10:00:00",
            source_cookbook="/path/to/cookbook",
            chef_nodes=[
                {
                    "name": "node-1",
                    "ipaddress": "10.0.0.1",
                    "environment": "production",
                    "roles": ["web"],
                    "platform": "ubuntu",
                },
                {
                    "fqdn": "db.example.com",
                    "ipaddress": "10.0.0.2",
                },
                {
                    "ipaddress": "10.0.0.3",
                },
            ],
            chef_server_queried=True,
        )

        mock_client = Mock()

        orchestrator._populate_inventory_from_chef_nodes(mock_client, 1)

        expected_vars_node1 = json.dumps(
            {
                "ansible_host": "10.0.0.1",
                "chef_environment": "production",
                "chef_roles": ["web"],
                "chef_platform": "ubuntu",
            }
        )
        expected_vars_node2 = json.dumps({"ansible_host": "10.0.0.2"})

        assert mock_client.add_host.call_count == 3
        mock_client.add_host.assert_has_calls(
            [
                call(1, "node-1", variables=expected_vars_node1),
                call(1, "db.example.com", variables=expected_vars_node2),
                call(1, "10.0.0.3"),
            ],
            any_order=True,
        )

    def test_migrate_cookbook_handles_missing_path(self) -> None:
        """Test migration with non-existent cookbook."""
        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        result = orchestrator.migrate_cookbook(
            "/nonexistent/path",
            skip_validation=True,
        )

        assert result.status == MigrationStatus.FAILED
        assert len(result.errors) > 0

    def test_migrate_cookbook_tracks_converted_artifacts(self, tmp_path: Path) -> None:
        """Test that migration tracks converted artifacts."""
        cookbook = tmp_path / "test_cookbook"
        cookbook.mkdir()
        recipes = cookbook / "recipes"
        recipes.mkdir()
        (recipes / "default.rb").write_text("execute 'test'")

        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        result = orchestrator.migrate_cookbook(str(cookbook), skip_validation=True)

        assert result.metrics.recipes_converted > 0
        assert "default.yml" in result.playbooks_generated

    def test_orchestrator_tracks_migration_id(self) -> None:
        """Test that migration ID is tracked."""
        orchestrator1 = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )
        orchestrator2 = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        assert orchestrator1.migration_id != orchestrator2.migration_id

    def test_result_export(self, tmp_path: Path) -> None:
        """Test exporting migration result to JSON."""
        output_file = tmp_path / "migration.json"

        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()

        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        result = orchestrator.migrate_cookbook(str(cookbook), skip_validation=True)
        orchestrator.result = result
        orchestrator.export_result(str(output_file))

        assert output_file.exists()
        exported = json.loads(output_file.read_text())
        assert exported["migration_id"] == orchestrator.migration_id

    def test_save_and_load_state(self, tmp_path: Path) -> None:
        """Test saving and loading migration state."""
        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()
        recipes = cookbook / "recipes"
        recipes.mkdir()
        (recipes / "default.rb").write_text("package 'curl'")

        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        result = orchestrator.migrate_cookbook(str(cookbook), skip_validation=True)
        orchestrator.result = result

        storage = StorageManager(db_path=tmp_path / "souschef.db")
        conversion_id = orchestrator.save_state(storage_manager=storage)

        assert conversion_id is not None

        restored = MigrationOrchestrator.load_state(
            result.migration_id,
            storage_manager=storage,
        )
        assert restored is not None
        assert restored.migration_id == result.migration_id
        assert restored.status == result.status

        storage.close()

    @pytest.mark.parametrize(
        "chef_ver,platform,target_ver",
        [
            ("12.19.36", "tower", "3.8.5"),
            ("14.15.6", "awx", "22.0.0"),
            ("15.10.91", "aap", "2.4.0"),
        ],
    )
    def test_migration_supports_all_versions(
        self, chef_ver: str, platform: str, target_ver: str, tmp_path: Path
    ) -> None:
        """Test that migration works for all supported versions."""
        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()

        orchestrator = MigrationOrchestrator(
            chef_version=chef_ver,
            target_platform=platform,
            target_version=target_ver,
        )

        assert orchestrator.config.chef_version == chef_ver
        assert orchestrator.config.target_platform == platform


class TestChefServerClient:
    """Test Chef Server API client."""

    @patch("souschef.api_clients.CoreChefServerClient")
    def test_search_nodes(self, mock_core_client: Mock) -> None:
        """Test searching nodes on Chef Server."""
        mock_instance = Mock()
        mock_instance.search_nodes.return_value = [
            {
                "name": "node-1",
                "platform": "ubuntu",
            }
        ]
        mock_core_client.return_value = mock_instance

        client = ChefServerClient(
            server_url="https://chef.example.com",
            organization="default",
            client_name="admin",
            client_key="-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
        )

        result = client.search_nodes(query="environment:production")
        assert result["total"] == 1
        assert len(result["rows"]) == 1

    @patch("souschef.api_clients.CoreChefServerClient")
    def test_get_node(self, mock_core_client: Mock) -> None:
        """Test retrieving node details."""
        mock_instance = Mock()
        mock_instance.search_nodes.return_value = [
            {
                "name": "node-1",
                "ipaddress": "10.0.0.1",
            }
        ]
        mock_core_client.return_value = mock_instance

        client = ChefServerClient(
            server_url="https://chef.example.com",
            organization="default",
            client_name="admin",
            client_key="-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
        )

        result = client.get_node("node-1")
        assert result["name"] == "node-1"


class TestAnsibleClients:
    """Test Ansible Platform API clients."""

    def test_get_ansible_client_tower(self) -> None:
        """Test getting Tower client."""
        client = get_ansible_client(
            server_url="https://tower.example.com",
            platform="tower",
            platform_version="3.8.5",
            username="admin",
            password="password",
        )

        assert isinstance(client, TowerClient)

    def test_get_ansible_client_awx(self) -> None:
        """Test getting AWX client."""
        client = get_ansible_client(
            server_url="https://awx.example.com",
            platform="awx",
            platform_version="24.6.1",
            username="admin",
            password="password",
        )

        assert isinstance(client, AWXClient)

    def test_get_ansible_client_aap(self) -> None:
        """Test getting AAP client."""
        client = get_ansible_client(
            server_url="https://aap.example.com",
            platform="aap",
            platform_version="2.4.0",
            username="admin",
            password="password",
        )

        assert isinstance(client, AAPClient)

    def test_get_ansible_client_invalid_platform(self) -> None:
        """Test error with invalid platform."""
        with pytest.raises(ValueError):
            get_ansible_client(
                server_url="https://invalid.example.com",
                platform="invalid",
                platform_version="1.0.0",
                username="admin",
                password="password",
            )

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_inventory(self, mock_post: Mock) -> None:
        """Test creating inventory."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": 1, "name": "inventory"}
        mock_post.return_value = mock_response

        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password="password",
        )

        result = client.create_inventory("test-inv")
        assert result["id"] == 1

    @patch("souschef.api_clients.requests.Session.delete")
    def test_delete_infrastructure(self, mock_delete: Mock) -> None:
        """Test deleting infrastructure."""
        mock_response = Mock()
        mock_delete.return_value = mock_response

        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password="password",
        )

        result = client.delete_inventory(1)
        assert result is True

    @patch("souschef.api_clients.requests.Session.post")
    def test_awx_execution_environment_creation(self, mock_post: Mock) -> None:
        """Test AWX 21+ execution environment creation."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": 42, "name": "ee"}
        mock_post.return_value = mock_response

        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password="password",
            version="24.6.1",
        )

        result = client.create_execution_environment("test-ee")
        assert result["id"] == 42

    def test_awx_20_no_execution_environment(self) -> None:
        """Test that AWX 20 doesn't support execution environments."""
        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password="password",
            version="20.1.0",
        )

        with pytest.raises(NotImplementedError):
            client.create_execution_environment("test-ee")


class TestInventoryGrouping:
    """Test inventory grouping from Chef nodes."""

    @patch("souschef.migration_v2.get_ansible_client")
    @patch("souschef.migration_v2.get_chef_nodes")
    def test_create_inventory_groups_from_chef_nodes(
        self,
        mock_get_nodes: Mock,
        mock_get_client: Mock,
        tmp_path: Path,
    ) -> None:
        """Test creating inventory groups from Chef environments and roles."""
        # Mock Chef nodes with various environments and roles
        mock_chef_nodes = [
            {
                "name": "web-1",
                "fqdn": "web-1.example.com",
                "ipaddress": "10.0.1.1",
                "environment": "production",
                "roles": ["web", "common"],
            },
            {
                "name": "web-2",
                "fqdn": "web-2.example.com",
                "ipaddress": "10.0.1.2",
                "environment": "production",
                "roles": ["web", "common"],
            },
            {
                "name": "db-1",
                "fqdn": "db-1.example.com",
                "ipaddress": "10.0.2.1",
                "environment": "production",
                "roles": ["database", "common"],
            },
            {
                "name": "cache-1",
                "ipaddress": "10.0.3.1",
                "environment": "staging",
                "roles": ["cache"],
            },
        ]
        mock_get_nodes.return_value = mock_chef_nodes

        # Mock Ansible API client with group creation
        mock_client = Mock()
        mock_client.server_url = "https://aap.example.com"
        mock_client.session = Mock()

        # Mock group creation responses
        def create_group_side_effect(
            inventory_id: int, name: str, **kwargs: Any
        ) -> dict[str, Any]:
            return {"id": hash(name) % 1000, "name": name}

        mock_client.create_group.side_effect = create_group_side_effect

        # Mock host listing response
        mock_host_response = Mock()
        mock_host_response.json.return_value = {
            "results": [
                {"id": 1, "name": "web-1.example.com"},
                {"id": 2, "name": "web-2.example.com"},
                {"id": 3, "name": "db-1.example.com"},
                {"id": 4, "name": "10.0.3.1"},
            ],
        }
        mock_client.session.get.return_value = mock_host_response

        mock_get_client.return_value = mock_client

        # Create cookbook and migrate
        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()
        recipes = cookbook / "recipes"
        recipes.mkdir()
        (recipes / "default.rb").write_text("package 'test'")

        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        orchestrator.migrate_cookbook(
            str(cookbook),
            skip_validation=True,
            chef_server_url="https://chef.example.com",
            chef_organisation="default",
            chef_client_name="admin",
            chef_client_key="test-key",
        )

        # Deploy and test group creation
        with patch("souschef.migration_v2.get_ansible_client") as mock_get_client2:
            mock_client.create_inventory.return_value = {"id": 1}
            mock_client.create_project.return_value = {"id": 2}
            mock_client.create_job_template.return_value = {"id": 3}
            mock_get_client2.return_value = mock_client

            orchestrator.deploy_to_ansible(
                "https://aap.example.com",
                "admin",
                "password",
            )

        # Verify groups were created for environments
        env_calls = [
            c for c in mock_client.create_group.call_args_list if "env_" in str(c)
        ]
        assert len(env_calls) >= 2  # production and staging

        # Verify groups were created for roles
        role_calls = [
            c for c in mock_client.create_group.call_args_list if "role_" in str(c)
        ]
        assert len(role_calls) >= 3  # web, database, cache, common

        # Verify hosts were added to groups
        assert mock_client.add_host_to_group.called

    @patch("souschef.migration_v2.get_ansible_client")
    @patch("souschef.migration_v2.get_chef_nodes")
    def test_inventory_grouping_graceful_failure(
        self,
        mock_get_nodes: Mock,
        mock_get_client: Mock,
        tmp_path: Path,
    ) -> None:
        """Test graceful handling of group creation failures."""
        mock_chef_nodes = [
            {
                "name": "node-1",
                "environment": "production",
                "roles": ["web"],
            },
        ]
        mock_get_nodes.return_value = mock_chef_nodes

        # Mock client that fails on group creation
        mock_client = Mock()
        mock_client.server_url = "https://aap.example.com"
        mock_client.create_group.side_effect = Exception("API error")
        mock_client.session = Mock()

        # But host listing succeeds
        mock_host_response = Mock()
        mock_host_response.json.return_value = {
            "results": [{"id": 1, "name": "node-1"}],
        }
        mock_client.session.get.return_value = mock_host_response

        mock_get_client.return_value = mock_client

        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()
        recipes = cookbook / "recipes"
        recipes.mkdir()
        (recipes / "default.rb").write_text("package 'test'")

        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        orchestrator.migrate_cookbook(
            str(cookbook),
            skip_validation=True,
            chef_server_url="https://chef.example.com",
            chef_organisation="default",
            chef_client_name="admin",
            chef_client_key="test-key",
        )

        with patch("souschef.migration_v2.get_ansible_client") as mock_get_client2:
            mock_client.create_inventory.return_value = {"id": 1}
            mock_client.create_project.return_value = {"id": 2}
            mock_client.create_job_template.return_value = {"id": 3}
            mock_get_client2.return_value = mock_client

            # Should not raise exception despite group creation failure
            orchestrator.deploy_to_ansible(
                "https://aap.example.com",
                "admin",
                "password",
            )

        # Deployment should still succeed or report warnings
        assert orchestrator.result is not None
        assert orchestrator.result.status in (
            MigrationStatus.DEPLOYED,
            MigrationStatus.IN_PROGRESS,
        )
        # Check that failure was logged as warning
        assert any(
            "Failed to create" in str(w.get("message", ""))
            for w in orchestrator.result.warnings
        )
