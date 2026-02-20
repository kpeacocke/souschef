"""
Integration tests for SousChef v2.0 migration workflows.

Tests real migration scenarios with sample cookbooks.
"""

from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
import requests
import responses

from souschef.api_clients import (
    AAPClient,
    AWXClient,
    ChefServerClient,
)
from souschef.migration_v2 import (
    ChefServerOptions,
    CookbookIngestionOptions,
    MigrationOrchestrator,
    MigrationStatus,
)

FIXTURES_DIR = Path(__file__).parent.parent / "integration" / "fixtures"


def _chef_server_options(**overrides: Any) -> ChefServerOptions:
    """Build Chef Server options for migration tests."""
    defaults: dict[str, Any] = {
        "server_url": "https://chef.example.com",
        "organisation": "default",
        "client_name": "admin",
        "client_key_path": None,
        "client_key": "test-key",
        "query": "*:*",
        "node": None,
        "policy": None,
    }
    defaults.update(overrides)
    return ChefServerOptions(**defaults)


def _ingestion_options(**overrides: Any) -> CookbookIngestionOptions:
    """Build ingestion options for migration tests."""
    defaults: dict[str, Any] = {
        "cookbook_name": None,
        "cookbook_version": None,
        "dependency_depth": "full",
        "use_cache": True,
        "offline_bundle_path": None,
    }
    defaults.update(overrides)
    return CookbookIngestionOptions(**defaults)


class TestFullMigrationWorkflow:
    """Test complete end-to-end migration workflows."""

    def test_migrate_sample_cookbook(self, tmp_path: Path) -> None:
        """Test migrating the sample cookbook."""
        # Use actual fixture or create test cookbook
        cookbook_source = FIXTURES_DIR / "sample_cookbook"

        if not cookbook_source.exists():
            cookbook_source = tmp_path / "sample_cookbook"
            cookbook_source.mkdir()

            # Create recipe files
            recipes = cookbook_source / "recipes"
            recipes.mkdir()
            (recipes / "default.rb").write_text("""
# Install web server
package 'apache2' do
  action :install
end

# Start service
service 'apache2' do
  action [:enable, :start]
end
""")

            # Create attributes
            attributes = cookbook_source / "attributes"
            attributes.mkdir()
            (attributes / "default.rb").write_text("""
default['web']['port'] = 80
default['web']['user'] = 'www-data'
""")

        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        result = orchestrator.migrate_cookbook(
            str(cookbook_source),
            skip_validation=True,
        )

        # Verify migration completed
        assert result.status != MigrationStatus.FAILED
        assert result.metrics.recipes_total > 0
        assert len(result.playbooks_generated) > 0
        assert result.ansible_version == "2.15.0"

    @pytest.mark.parametrize(
        "target_platform,target_version",
        [
            ("tower", "3.8.5"),
            ("awx", "22.0.0"),
            ("awx", "24.6.1"),
            ("aap", "2.4.0"),
        ],
    )
    def test_migrate_to_all_platforms(
        self, target_platform: str, target_version: str, tmp_path: Path
    ) -> None:
        """Test migration to all supported platforms."""
        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()
        recipes = cookbook / "recipes"
        recipes.mkdir()
        (recipes / "default.rb").write_text("package 'curl'")

        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform=target_platform,
            target_version=target_version,
        )

        result = orchestrator.migrate_cookbook(str(cookbook), skip_validation=True)

        assert result.target_platform == target_platform
        assert result.target_version == target_version
        assert result.status != MigrationStatus.FAILED

    def test_large_cookbook_migration(self, tmp_path: Path) -> None:
        """Test migration of a large cookbook with many recipes."""
        cookbook = tmp_path / "large_cookbook"
        cookbook.mkdir()
        recipes = cookbook / "recipes"
        recipes.mkdir()

        # Create 10 recipe files
        for i in range(10):
            (recipes / f"recipe_{i}.rb").write_text(
                f"""
# Recipe {i}
package 'package_{i}'
execute 'command_{i}' do
  command 'echo test_{i}'
end
"""
            )

        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        result = orchestrator.migrate_cookbook(str(cookbook), skip_validation=True)

        assert result.metrics.recipes_total >= 10
        assert (
            "Cookbook migration completed" in result.warnings
            or len(result.playbooks_generated) > 0
        )


class TestMigrationWithRealAPIs:
    """Test migration with realistic API interactions."""

    @responses.activate
    def test_deploy_to_aap_with_real_http(self) -> None:
        """Test deployment to AAP with HTTP mocking."""
        # Mock AAP API responses
        responses.add(
            responses.POST,
            "https://aap.example.com/api/v2/inventories/",
            json={"id": 1, "name": "migrated-inv"},
            status=201,
        )

        responses.add(
            responses.POST,
            "https://aap.example.com/api/v2/inventories/1/hosts/",
            json={"id": 100, "hostname": "host-1"},
            status=201,
        )

        responses.add(
            responses.POST,
            "https://aap.example.com/api/v2/projects/",
            json={"id": 2, "name": "migrated-project"},
            status=201,
        )

        responses.add(
            responses.POST,
            "https://aap.example.com/api/v2/execution_environments/",
            json={"id": 3, "name": "migrated-ee"},
            status=201,
        )

        responses.add(
            responses.POST,
            "https://aap.example.com/api/v2/job_templates/",
            json={"id": 4, "name": "migrated-jt"},
            status=201,
        )

        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password="password",
        )

        # Test inventory creation
        inv = client.create_inventory("migrated-inv")
        assert inv["id"] == 1

        # Test project creation
        proj = client.create_project("migrated-project", "git")
        assert proj["id"] == 2

        # Test EE creation
        ee = client.create_execution_environment("migrated-ee")
        assert ee["id"] == 3

    @responses.activate
    def test_deploy_to_awx_22(self) -> None:
        """Test deployment to AWX 22.0.0 without EE."""
        responses.add(
            responses.POST,
            "https://awx.example.com/api/v2/inventories/",
            json={"id": 1, "name": "migrated"},
            status=201,
        )

        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password="password",
            version="22.0.0",
        )

        inv = client.create_inventory("migrated")
        assert inv["id"] == 1

    @patch("souschef.api_clients.CoreChefServerClient")
    def test_query_chef_server(self, mock_core_client: Mock) -> None:
        """Test querying Chef Server for nodes."""
        mock_instance = Mock()
        mock_instance.search_nodes.return_value = [
            {"name": "node-1", "id": 1},
            {"name": "node-2", "id": 2},
        ]
        mock_core_client.return_value = mock_instance

        client = ChefServerClient(
            server_url="https://chef.example.com",
            organization="default",
            client_name="admin",
            client_key="-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
        )

        result = client.search_nodes(query="*:*")
        assert result["total"] == 2


class TestMigrationErrorHandling:
    """Test error handling in migration workflows."""

    def test_missing_cookbook_path(self) -> None:
        """Test migration with missing cookbook."""
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

    @responses.activate
    def test_deployment_api_failure(self) -> None:
        """Test handling of API failures during deployment."""
        responses.add(
            responses.POST,
            "https://aap.example.com/api/v2/inventories/",
            json={"errors": "Invalid request"},
            status=400,
        )

        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password="password",
        )

        with pytest.raises(requests.RequestException):
            client.create_inventory("test")

    def test_invalid_cookbook_structure(self, tmp_path: Path) -> None:
        """Test migration of cookbook with invalid structure."""
        cookbook = tmp_path / "invalid"
        cookbook.mkdir()
        # Empty cookbook - no recipes or attributes

        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        result = orchestrator.migrate_cookbook(str(cookbook), skip_validation=True)

        # Should handle gracefully (may warn but not fail)
        assert result.status != MigrationStatus.FAILED or len(result.warnings) > 0


class TestMigrationStateTracking:
    """Test migration state and history tracking."""

    def test_migration_status_transitions(self, tmp_path: Path) -> None:
        """Test that migration status transitions correctly."""
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

        result = orchestrator.migrate_cookbook(str(cookbook), skip_validation=True)

        # Status should progress through workflow
        assert result.status in (
            MigrationStatus.CONVERTED,
            MigrationStatus.VALIDATED,
        )
        assert result.migration_id is not None
        assert result.created_at is not None
        assert result.updated_at is not None

    def test_migration_result_json_export(self, tmp_path: Path) -> None:
        """Test exporting migration result to JSON."""
        export_file = tmp_path / "result.json"

        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()

        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        result = orchestrator.migrate_cookbook(str(cookbook), skip_validation=True)
        orchestrator.result = result
        orchestrator.export_result(str(export_file))

        assert export_file.exists()
        content = export_file.read_text()
        assert "migration_id" in content
        assert "aap" in content

    def test_multiple_migrations_unique_ids(self, tmp_path: Path) -> None:
        """Test that each migration gets unique ID."""
        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()

        ids = set()
        for _ in range(5):
            orchestrator = MigrationOrchestrator(
                chef_version="15.10.91",
                target_platform="aap",
                target_version="2.4.0",
            )
            ids.add(orchestrator.migration_id)

        assert len(ids) == 5  # All migration IDs are unique


class TestVersionCombinations:
    """Test migrations for all supported version combinations."""

    @pytest.mark.parametrize(
        "chef_ver,target_platform,target_ver,ansible_ver",
        [
            ("12.19.36", "tower", "3.8.5", "2.9.0"),
            ("12.19.36", "awx", "24.6.1", "2.16.0"),
            ("14.15.6", "awx", "22.0.0", "2.12.0"),
            ("14.15.6", "aap", "2.4.0", "2.15.0"),
            ("15.10.91", "aap", "2.4.0", "2.15.0"),
        ],
    )
    def test_version_combinations(
        self,
        chef_ver: str,
        target_platform: str,
        target_ver: str,
        ansible_ver: str,
        tmp_path: Path,
    ) -> None:
        """Test migration for specific version combinations."""
        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()
        recipes = cookbook / "recipes"
        recipes.mkdir()
        (recipes / "default.rb").write_text("package 'curl'")

        orchestrator = MigrationOrchestrator(
            chef_version=chef_ver,
            target_platform=target_platform,
            target_version=target_ver,
        )

        result = orchestrator.migrate_cookbook(str(cookbook), skip_validation=True)

        assert result.chef_version == chef_ver
        assert result.target_platform == target_platform
        assert result.target_version == target_ver
        assert result.ansible_version == ansible_ver
        assert result.status != MigrationStatus.FAILED


class TestChefServerIntegration:
    """Test Chef Server node discovery and inventory population."""

    @patch("souschef.migration_v2.get_chef_nodes")
    def test_chef_node_discovery_and_inventory_population(
        self,
        mock_get_nodes: Mock,
        tmp_path: Path,
    ) -> None:
        """Test complete workflow: discover Chef nodes → populate inventory."""
        # Mock Chef nodes discovery
        mock_chef_nodes = [
            {
                "name": "web-1.example.com",
                "fqdn": "web-1.example.com",
                "ipaddress": "192.168.1.10",  # NOSONAR - test fixture
                "environment": "production",
                "roles": ["web", "common"],
                "platform": "ubuntu",
                "platform_version": "20.04",
            },
            {
                "name": "db-1.example.com",
                "fqdn": "db-1.example.com",
                "ipaddress": "192.168.1.20",  # NOSONAR - test fixture
                "environment": "production",
                "roles": ["database", "common"],
                "platform": "ubuntu",
                "platform_version": "18.04",
            },
            {
                "name": "cache-1",
                "ipaddress": "192.168.1.30",  # NOSONAR - test fixture
                "environment": "staging",
                "roles": ["cache", "common"],
                "platform": "centos",
                "platform_version": "7",
            },
        ]
        mock_get_nodes.return_value = mock_chef_nodes

        # Create test cookbook
        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()
        recipes = cookbook / "recipes"
        recipes.mkdir()
        (recipes / "default.rb").write_text("""
package 'curl'
service 'ssh' do
  action :enable
end
""")

        # Create orchestrator and migrate with Chef Server params
        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        result = orchestrator.migrate_cookbook(
            str(cookbook),
            skip_validation=True,
            chef_server=_chef_server_options(
                client_key="-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
                query="*:*",
            ),
            ingestion=_ingestion_options(),
        )

        # Verify Chef Server was queried
        assert result.chef_server_queried
        assert len(result.chef_nodes) == 3
        assert result.chef_nodes[0]["name"] == "web-1.example.com"
        assert result.chef_nodes[1]["environment"] == "production"

        # Verify get_chef_nodes was called with correct parameters
        mock_get_nodes.assert_called_once_with(
            search_query="*:*",
            server_url="https://chef.example.com",
            organisation="default",
            client_name="admin",
            client_key_path=None,
            client_key="-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
        )

    @patch("souschef.migration_v2.get_ansible_client")
    @patch("souschef.migration_v2.get_chef_nodes")
    def test_inventory_populated_with_chef_nodes_variables(
        self,
        mock_get_nodes: Mock,
        mock_get_client: Mock,
        tmp_path: Path,
    ) -> None:
        """Test that inventory hosts are created with Chef node variables."""
        # Mock Chef nodes
        mock_chef_nodes = [
            {
                "name": "web-server",
                "fqdn": "web-server.prod.example.com",
                "ipaddress": "10.0.1.5",  # NOSONAR - test fixture
                "environment": "production",
                "roles": ["web", "common"],
                "platform": "ubuntu",
                "platform_version": "22.04",
            },
        ]
        mock_get_nodes.return_value = mock_chef_nodes

        # Mock Ansible API client
        mock_client = Mock()
        mock_client.create_inventory.return_value = {"id": 1, "name": "test-inv"}
        mock_client.create_project.return_value = {"id": 2, "name": "test-proj"}
        mock_client.create_job_template.return_value = {"id": 3, "name": "test-jt"}
        mock_get_client.return_value = mock_client

        # Create test cookbook
        cookbook = tmp_path / "cookbook"
        cookbook.mkdir()
        recipes = cookbook / "recipes"
        recipes.mkdir()
        (recipes / "default.rb").write_text("package 'apache2'")

        # Run migration with deployment
        orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

        result = orchestrator.migrate_cookbook(
            str(cookbook),
            skip_validation=True,
            chef_server=_chef_server_options(),
            ingestion=_ingestion_options(),
        )

        # Deploy to Ansible
        deployment_success = orchestrator.deploy_to_ansible(
            "https://aap.example.com",
            "admin",
            "password",
        )

        assert deployment_success
        assert result.inventory_id == 1

        # Verify add_host was called with correct variables
        mock_client.add_host.assert_called_once()
        call_args = mock_client.add_host.call_args
        assert call_args[0][0] == 1  # inventory_id
        assert (
            call_args[0][1] == "web-server.prod.example.com"
        )  # hostname (fqdn preferred)

        # Verify variables include Chef metadata
        import json

        variables_json = call_args[1]["variables"]
        variables = json.loads(variables_json)
        assert (
            variables["ansible_host"] == "10.0.1.5"  # NOSONAR
        )  # IP address  # NOSONAR - test fixture
        assert variables["chef_environment"] == "production"
        assert variables["chef_roles"] == ["web", "common"]
        assert variables["chef_platform"] == "ubuntu"

    @patch("souschef.migration_v2.get_chef_nodes")
    def test_chef_nodes_fallback_to_name_then_ip(
        self,
        mock_get_nodes: Mock,
        tmp_path: Path,
    ) -> None:
        """Test hostname resolution fallback: fqdn → name → ipaddress."""
        # Nodes with different hostname priorities
        mock_chef_nodes = [
            {
                "name": "node-with-fqdn",
                "fqdn": "node-with-fqdn.example.com",
                "ipaddress": "10.0.1.1",  # NOSONAR - test fixture
                "environment": "test",
                "roles": [],
            },
            {
                "name": "node-name-only",
                "ipaddress": "10.0.1.2",  # NOSONAR - test fixture
                "environment": "test",
                "roles": [],
            },
            {
                "ipaddress": "10.0.1.3",  # NOSONAR - test fixture
                "environment": "test",
                "roles": [],
            },
        ]
        mock_get_nodes.return_value = mock_chef_nodes

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

        result = orchestrator.migrate_cookbook(
            str(cookbook),
            skip_validation=True,
            chef_server=_chef_server_options(),
            ingestion=_ingestion_options(),
        )

        # Verify nodes were discovered
        assert result.chef_server_queried
        assert len(result.chef_nodes) == 3

        # Verify hostname resolution logic by deploying
        with patch("souschef.migration_v2.get_ansible_client") as mock_get_client:
            mock_client = Mock()
            mock_client.create_inventory.return_value = {"id": 1}
            mock_client.create_project.return_value = {"id": 2}
            mock_client.create_job_template.return_value = {"id": 3}
            mock_get_client.return_value = mock_client

            orchestrator.deploy_to_ansible(
                "https://aap.example.com",
                "admin",
                "password",
            )

            # Verify add_host calls with correct hostname resolution
            calls = mock_client.add_host.call_args_list
            assert len(calls) == 3

            # First node: should use fqdn
            assert calls[0][0][1] == "node-with-fqdn.example.com"

            # Second node: should use name (no fqdn)
            assert calls[1][0][1] == "node-name-only"

            # Third node: should use ipaddress (no name or fqdn)
            assert calls[2][0][1] == "10.0.1.3"  # NOSONAR - test fixture

    @patch("souschef.migration_v2.get_chef_nodes")
    def test_chef_server_query_failure_warning(
        self,
        mock_get_nodes: Mock,
        tmp_path: Path,
    ) -> None:
        """Test handling of Chef Server query failures with warnings."""
        # Simulate Chef Server query failure
        mock_get_nodes.side_effect = Exception("Authentication failed")

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

        result = orchestrator.migrate_cookbook(
            str(cookbook),
            skip_validation=True,
            chef_server=_chef_server_options(client_key="invalid-key"),
            ingestion=_ingestion_options(),
        )

        # Verify failure was captured as warning (not fatal)
        assert result.chef_server_queried
        assert len(result.chef_nodes) == 0
        assert any(
            "Chef Server query failed" in w.get("message", "") for w in result.warnings
        )


class TestInventoryGrouping:
    """Test inventory grouping from Chef environments and roles."""

    @patch("souschef.migration_v2.get_ansible_client")
    @patch("souschef.migration_v2.get_chef_nodes")
    def test_inventory_groups_created_from_chef_environments_and_roles(
        self,
        mock_get_nodes: Mock,
        mock_get_client: Mock,
        tmp_path: Path,
    ) -> None:
        """Test complete workflow: discover → populate hosts → create groups → assign hosts."""
        # Mock Chef nodes with diverse environments and roles
        mock_chef_nodes = [
            {
                "name": "web-1",
                "fqdn": "web-1.prod.example.com",
                "ipaddress": "10.0.1.10",  # NOSONAR - test fixture
                "environment": "production",
                "roles": ["web", "common"],
            },
            {
                "name": "web-2",
                "fqdn": "web-2.prod.example.com",
                "ipaddress": "10.0.1.11",  # NOSONAR - test fixture
                "environment": "production",
                "roles": ["web", "common"],
            },
            {
                "name": "db-1",
                "fqdn": "db-1.prod.example.com",
                "ipaddress": "10.0.2.10",  # NOSONAR - test fixture
                "environment": "production",
                "roles": ["database", "common"],
            },
            {
                "name": "cache-1",
                "ipaddress": "10.0.3.10",  # NOSONAR - test fixture
                "environment": "staging",
                "roles": ["cache"],
            },
            {
                "name": "dev-1",
                "ipaddress": "10.0.4.10",  # NOSONAR - test fixture
                "environment": "development",
                "roles": ["dev", "common"],
            },
        ]
        mock_get_nodes.return_value = mock_chef_nodes

        # Mock Ansible API client with group and host operations
        mock_client = Mock()
        mock_client.server_url = "https://aap.example.com"
        mock_client.session = Mock()

        # Track created groups
        created_groups: dict[str, int] = {}

        def create_group_side_effect(
            inventory_id: int, name: str, **kwargs: Any
        ) -> dict[str, Any]:
            group_id = len(created_groups) + 100
            created_groups[name] = group_id
            return {"id": group_id, "name": name}

        mock_client.create_group.side_effect = create_group_side_effect

        # Mock host listing to return hosts we "added"
        def get_hosts_side_effect(url: str) -> Mock:
            response = Mock()
            response.json.return_value = {
                "results": [
                    {"id": 1, "name": "web-1.prod.example.com"},
                    {"id": 2, "name": "web-2.prod.example.com"},
                    {"id": 3, "name": "db-1.prod.example.com"},
                    {"id": 4, "name": "10.0.3.10"},  # NOSONAR - test fixture
                    {"id": 5, "name": "10.0.4.10"},  # NOSONAR - test fixture
                ]
            }
            return response

        mock_client.session.get.side_effect = get_hosts_side_effect

        # Mock other operations
        mock_client.create_inventory.return_value = {"id": 1}
        mock_client.create_project.return_value = {"id": 2}
        mock_client.create_job_template.return_value = {"id": 3}

        mock_get_client.return_value = mock_client

        # Create cookbook and run migration
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

        # Run migration with Chef Server
        orchestrator.migrate_cookbook(
            str(cookbook),
            skip_validation=True,
            chef_server=_chef_server_options(),
            ingestion=_ingestion_options(),
        )

        # Deploy to Ansible (triggers group creation)
        deployment_success = orchestrator.deploy_to_ansible(
            "https://aap.example.com",
            "admin",
            "password",
        )

        assert deployment_success
        assert orchestrator.result is not None
        assert orchestrator.result.status == MigrationStatus.DEPLOYED

        # Verify environment groups were created
        env_group_calls = [
            c for c in mock_client.create_group.call_args_list if "env_" in str(c)
        ]
        assert len(env_group_calls) >= 3  # production, staging, development

        # Verify role groups were created
        role_group_calls = [
            c for c in mock_client.create_group.call_args_list if "role_" in str(c)
        ]
        assert len(role_group_calls) >= 4  # web, database, cache, dev, common

        # Verify hosts were assigned to groups
        assert mock_client.add_host_to_group.called
        # Should have multiple assignments (each host to env + each role)
        assert mock_client.add_host_to_group.call_count >= 8

    @patch("souschef.migration_v2.get_ansible_client")
    @patch("souschef.migration_v2.get_chef_nodes")
    def test_inventory_grouping_with_duplicate_roles_across_environments(
        self,
        mock_get_nodes: Mock,
        mock_get_client: Mock,
        tmp_path: Path,
    ) -> None:
        """Test grouping correctly deduplicates roles across environments."""
        # Nodes with same role in different environments
        mock_chef_nodes = [
            {
                "name": "web-prod",
                "ipaddress": "10.0.1.1",  # NOSONAR - test fixture
                "environment": "production",
                "roles": ["web", "common"],
            },
            {
                "name": "web-staging",
                "ipaddress": "10.0.2.1",  # NOSONAR - test fixture
                "environment": "staging",
                "roles": ["web", "common"],
            },
            {
                "name": "web-dev",
                "ipaddress": "10.0.3.1",  # NOSONAR - test fixture
                "environment": "development",
                "roles": ["web", "common"],
            },
        ]
        mock_get_nodes.return_value = mock_chef_nodes

        # Mock client
        mock_client = Mock()
        mock_client.server_url = "https://aap.example.com"
        mock_client.session = Mock()

        # Track group creation
        created_groups = []

        def create_group_side_effect(
            inventory_id: int, name: str, **kwargs: Any
        ) -> dict[str, Any]:
            created_groups.append(name)
            return {"id": len(created_groups) + 100, "name": name}

        mock_client.create_group.side_effect = create_group_side_effect

        # Mock host listing
        mock_client.session.get.return_value = Mock(
            json=Mock(
                return_value={
                    "results": [
                        {"id": 1, "name": "10.0.1.1"},  # NOSONAR - test fixture
                        {"id": 2, "name": "10.0.2.1"},  # NOSONAR - test fixture
                        {"id": 3, "name": "10.0.3.1"},  # NOSONAR - test fixture
                    ]
                }
            )
        )

        # Mock other operations
        mock_client.create_inventory.return_value = {"id": 1}
        mock_client.create_project.return_value = {"id": 2}
        mock_client.create_job_template.return_value = {"id": 3}

        mock_get_client.return_value = mock_client

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

        orchestrator.migrate_cookbook(
            str(cookbook),
            skip_validation=True,
            chef_server=_chef_server_options(),
            ingestion=_ingestion_options(),
        )

        orchestrator.deploy_to_ansible(
            "https://aap.example.com",
            "admin",
            "password",
        )

        # Verify role_web is created only once (not once per environment)
        web_role_count = created_groups.count("role_web")
        assert web_role_count == 1, f"Expected 1 role_web group, got {web_role_count}"

        # Verify role_common is created only once
        common_role_count = created_groups.count("role_common")
        assert common_role_count == 1, (
            f"Expected 1 role_common group, got {common_role_count}"
        )

        # Verify each environment group is created
        assert "env_production" in created_groups
        assert "env_staging" in created_groups
        assert "env_development" in created_groups
