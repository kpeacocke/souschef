"""Tests for v2 Click commands using CliRunner."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from souschef.cli_v2_commands import create_v2_group


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CliRunner for testing."""
    return CliRunner()


@pytest.fixture
def v2_group():
    """Create the v2 command group."""
    return create_v2_group()


class TestV2MigrateCommand:
    """Test v2 migrate Click command."""

    def test_v2_migrate_missing_required_options(
        self, runner: CliRunner, v2_group
    ) -> None:
        """Migrate command requires mandatory options."""
        result = runner.invoke(v2_group, ["migrate"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "Error" in result.output

    def test_v2_migrate_invalid_cookbook_path(
        self, runner: CliRunner, v2_group
    ) -> None:
        """Invalid cookbook path exits with error."""
        result = runner.invoke(
            v2_group,
            [
                "migrate",
                "--cookbook-path",
                "/nonexistent/path",
                "--chef-version",
                "15.0.0",
                "--target-platform",
                "awx",
                "--target-version",
                "2.0.0",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code != 0


class TestV2StatusCommand:
    """Test v2 status Click command."""

    def test_v2_status_missing_migration_id(self, runner: CliRunner, v2_group) -> None:
        """Status command requires migration-id option."""
        result = runner.invoke(v2_group, ["status"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "Error" in result.output

    def test_v2_status_missing_id_not_found(self, runner: CliRunner, v2_group) -> None:
        """Status command errors when migration ID not found."""
        with patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch:
            mock_orch.load_state.return_value = None

            result = runner.invoke(
                v2_group,
                [
                    "status",
                    "--migration-id",
                    "invalid-id",
                ],
            )

            assert result.exit_code != 0
            assert "not found" in result.output.lower()

    def test_v2_status_success(self, runner: CliRunner, v2_group) -> None:
        """Status command outputs migration state."""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "status": "deployed",
            "migration_id": "mig-123",
        }

        with patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch:
            mock_orch.load_state.return_value = mock_result

            result = runner.invoke(
                v2_group,
                [
                    "status",
                    "--migration-id",
                    "mig-123",
                ],
            )

            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output["status"] == "deployed"


class TestV2ListCommand:
    """Test v2 list Click command."""

    def test_v2_list_empty(self, runner: CliRunner, v2_group) -> None:
        """List command with no migrations."""
        with patch("souschef.storage.get_storage_manager") as mock_storage:
            mock_manager = MagicMock()
            mock_storage.return_value = mock_manager
            mock_manager.get_conversion_history.return_value = []

            result = runner.invoke(v2_group, ["list"])

            assert result.exit_code == 0
            assert "No migrations found" in result.output

    def test_v2_list_with_conversions_text(self, runner: CliRunner, v2_group) -> None:
        """List command outputs conversions in text format."""
        conv = MagicMock()
        conv.id = 1
        conv.cookbook_name = "test-cookbook"
        conv.output_type = "playbook"
        conv.status = "success"
        conv.files_generated = 5
        conv.created_at = "2025-01-01T00:00:00"
        conv.conversion_data = json.dumps(
            {
                "migration_result": {
                    "migration_id": "mig-12345678",
                    "metrics": {"recipes_converted": 5, "recipes_total": 10},
                }
            }
        )

        with patch("souschef.storage.get_storage_manager") as mock_storage:
            mock_manager = MagicMock()
            mock_storage.return_value = mock_manager
            mock_manager.get_conversion_history.return_value = [conv]

            result = runner.invoke(
                v2_group,
                [
                    "list",
                    "--format",
                    "text",
                ],
            )

            assert result.exit_code == 0
            assert "test-cookbook" in result.output

    def test_v2_list_with_conversions_json(self, runner: CliRunner, v2_group) -> None:
        """List command outputs conversions in JSON format."""
        conv = MagicMock()
        conv.id = 1
        conv.cookbook_name = "test-cookbook"
        conv.output_type = "playbook"
        conv.status = "success"
        conv.files_generated = 5
        conv.created_at = "2025-01-01T00:00:00"
        conv.conversion_data = json.dumps(
            {
                "migration_result": {
                    "migration_id": "mig-12345678",
                }
            }
        )

        with patch("souschef.storage.get_storage_manager") as mock_storage:
            mock_manager = MagicMock()
            mock_storage.return_value = mock_manager
            mock_manager.get_conversion_history.return_value = [conv]

            result = runner.invoke(
                v2_group,
                [
                    "list",
                    "--format",
                    "json",
                ],
            )

            assert result.exit_code == 0
            output = json.loads(result.output)
            assert len(output) == 1
            assert output[0]["cookbook_name"] == "test-cookbook"

    def test_v2_list_storage_error(self, runner: CliRunner, v2_group) -> None:
        """List command handles storage errors."""
        with patch("souschef.storage.get_storage_manager") as mock_storage:
            mock_storage.side_effect = RuntimeError("Storage error")

            result = runner.invoke(v2_group, ["list"])

            assert result.exit_code != 0
            assert "Error" in result.output


class TestV2RollbackCommand:
    """Test v2 rollback Click command."""

    def test_v2_rollback_missing_options(self, runner: CliRunner, v2_group) -> None:
        """Rollback command requires all options."""
        result = runner.invoke(v2_group, ["rollback"])

        assert result.exit_code != 0

    def test_v2_rollback_migration_not_found(self, runner: CliRunner, v2_group) -> None:
        """Rollback with non-existent migration ID errors."""
        with patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch:
            mock_orch.load_state.return_value = None

            result = runner.invoke(
                v2_group,
                [
                    "rollback",
                    "--url",
                    "https://tower.example.com",
                    "--username",
                    "admin",
                    "--password",
                    "secret",
                    "--migration-id",
                    "invalid-id",
                ],
            )

            assert result.exit_code != 0
            assert "not found" in result.output.lower()

    def test_v2_rollback_not_deployed_status(self, runner: CliRunner, v2_group) -> None:
        """Rollback errors if migration is not deployed."""
        from souschef.migration_v2 import MigrationStatus as RealStatus

        mock_result = MagicMock()
        mock_result.status = RealStatus.PENDING
        mock_result.chef_version = "15.0.0"
        mock_result.target_platform = "awx"
        mock_result.target_version = "2.0.0"

        with patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch:
            mock_orch.load_state.return_value = mock_result

            result = runner.invoke(
                v2_group,
                [
                    "rollback",
                    "--url",
                    "https://tower.example.com",
                    "--username",
                    "admin",
                    "--password",
                    "secret",
                    "--migration-id",
                    "mig-123",
                ],
            )

            assert result.exit_code != 0
            assert "not deployed" in result.output.lower()

    def test_v2_rollback_success(self, runner: CliRunner, v2_group) -> None:
        """Rollback exception handling."""
        from souschef.migration_v2 import MigrationStatus as RealStatus

        mock_result = MagicMock()
        mock_result.status = RealStatus.DEPLOYED
        mock_result.chef_version = "15.0.0"
        mock_result.target_platform = "awx"
        mock_result.target_version = "2.0.0"

        with patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch:
            # Simulate exception during rollback
            mock_orch.load_state.return_value = mock_result
            mock_orch.return_value.rollback.side_effect = Exception("Connection failed")

            result = runner.invoke(
                v2_group,
                [
                    "rollback",
                    "--url",
                    "https://tower.example.com",
                    "--username",
                    "admin",
                    "--password",
                    "secret",
                    "--migration-id",
                    "mig-123",
                ],
            )

            # Should exit with error
            assert result.exit_code != 0
