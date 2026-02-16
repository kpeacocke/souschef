"""
Integration tests for SousChef v2.0 migration workflows.

Tests real migration scenarios with sample cookbooks.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
import responses

from souschef.api_clients import (
    AAPClient,
    AWXClient,
    ChefServerClient,
)
from souschef.migration_v2 import MigrationOrchestrator, MigrationStatus

FIXTURES_DIR = Path(__file__).parent.parent / "integration" / "fixtures"


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
