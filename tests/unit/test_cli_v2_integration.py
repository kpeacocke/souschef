"""Comprehensive Click command integration tests for cli_v2_commands."""

from __future__ import annotations

import json
from pathlib import Path
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


class TestV2MigrateCommandIntegration:
    """Integration tests for v2 migrate command."""

    def test_v2_migrate_success_with_mocked_orchestrator(
        self, runner: CliRunner, v2_group, tmp_path: Path
    ) -> None:
        """Test successful migration via Click command."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")

        mock_result = MagicMock()
        mock_result.status = "COMPLETED"
        mock_result.to_dict.return_value = {
            "status": "completed",
            "files_generated": 3,
            "migration_id": "mig-abc123",
        }

        with (
            patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch,
            patch("souschef.cli_v2_commands.MigrationStatus") as mock_status,
        ):
            mock_status.FAILED = "FAILED"
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance
            mock_instance.migrate_cookbook.return_value = mock_result
            mock_instance.save_state.return_value = None

            result = runner.invoke(
                v2_group,
                [
                    "migrate",
                    "--cookbook-path",
                    str(cookbook_dir),
                    "--chef-version",
                    "15.0.0",
                    "--target-platform",
                    "awx",
                    "--target-version",
                    "2.0.0",
                ],
            )

            # Command should succeed
            assert result.exit_code == 0
            # Should output JSON
            assert "migration_id" in result.output

    def test_v2_migrate_with_save_state(
        self, runner: CliRunner, v2_group, tmp_path: Path
    ) -> None:
        """Test migration with save_state flag."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        mock_result = MagicMock()
        mock_result.status = "COMPLETED"
        mock_result.to_dict.return_value = {"status": "completed"}

        with (
            patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch,
            patch("souschef.cli_v2_commands.MigrationStatus") as mock_status,
        ):
            mock_status.FAILED = "FAILED"
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance
            mock_instance.migrate_cookbook.return_value = mock_result
            mock_instance.save_state.return_value = "storage-id-456"

            result = runner.invoke(
                v2_group,
                [
                    "migrate",
                    "--cookbook-path",
                    str(cookbook_dir),
                    "--chef-version",
                    "15.0.0",
                    "--target-platform",
                    "awx",
                    "--target-version",
                    "2.0.0",
                    "--save-state",
                    "--analysis-id",
                    "42",
                ],
            )

            # Should call save_state
            mock_instance.save_state.assert_called_once()
            # Should include storage_id in output
            assert "storage_id" in result.output

    def test_v2_migrate_with_output_file(
        self, runner: CliRunner, v2_group, tmp_path: Path
    ) -> None:
        """Test migration with output file to trigger file save path."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")
        output_file = tmp_path / "migration_result.json"

        mock_result = MagicMock()
        mock_result.status = "COMPLETED"
        mock_result.to_dict.return_value = {"status": "completed", "id": "mig-123"}

        with (
            patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch,
            patch("souschef.cli_v2_commands.MigrationStatus") as mock_status,
        ):
            mock_status.FAILED = "FAILED"
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance
            mock_instance.migrate_cookbook.return_value = mock_result

            result = runner.invoke(
                v2_group,
                [
                    "migrate",
                    "--cookbook-path",
                    str(cookbook_dir),
                    "--chef-version",
                    "15.0.0",
                    "--target-platform",
                    "awx",
                    "--target-version",
                    "2.0.0",
                    "--output",
                    str(output_file),
                ],
            )

            # Should succeed and create output file
            assert result.exit_code == 0
            assert output_file.exists()
            assert "saved to" in result.output.lower()

            # Verify file content
            content = json.loads(output_file.read_text())
            assert content["status"] == "completed"


class TestV2StatusCommandFileOutput:
    """Test v2 status command with file output."""

    def test_v2_status_with_output_file(
        self, runner: CliRunner, v2_group, tmp_path: Path
    ) -> None:
        """Test status command saving to output file."""
        output_file = tmp_path / "status.json"

        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "status": "deployed",
            "migration_id": "mig-xyz",
        }

        with patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch:
            mock_orch.load_state.return_value = mock_result

            result = runner.invoke(
                v2_group,
                [
                    "status",
                    "--migration-id",
                    "mig-xyz",
                    "--output",
                    str(output_file),
                ],
            )

            # Should succeed and create file
            assert result.exit_code == 0
            assert output_file.exists()
            assert "saved to" in result.output.lower()

            # Verify file contents
            content = json.loads(output_file.read_text())
            assert content["status"] == "deployed"

    def test_v2_status_exception_handling(self, runner: CliRunner, v2_group) -> None:
        """Test status command exception handling."""
        with patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch:
            mock_orch.load_state.side_effect = RuntimeError("Database error")

            result = runner.invoke(
                v2_group,
                [
                    "status",
                    "--migration-id",
                    "mig-error",
                ],
            )

            # Should exit with error
            assert result.exit_code != 0
            assert "Error loading migration state" in result.output


class TestV2RollbackSuccess:
    """Test v2 rollback command success paths."""

    def test_v2_rollback_successful_execution(
        self, runner: CliRunner, v2_group
    ) -> None:
        """Test successful rollback with all success conditions."""
        from souschef.migration_v2 import MigrationStatus as RealStatus

        mock_result = MagicMock()
        mock_result.status = RealStatus.DEPLOYED
        mock_result.chef_version = "15.0.0"
        mock_result.target_platform = "awx"
        mock_result.target_version = "2.0.0"
        mock_result.playbooks_generated = ["playbook1.yml", "playbook2.yml"]

        with patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch:
            # Setup load_state to return deployed migration
            mock_orch.load_state.return_value = mock_result

            # Setup orchestrator instance
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance
            mock_instance.result = mock_result

            # Mock successful rollback
            def mock_rollback(url, creds):
                mock_instance.result.status = RealStatus.ROLLED_BACK

            mock_instance.rollback = mock_rollback

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
                    "mig-rollback-test",
                ],
            )

            # Should succeed
            assert result.exit_code == 0
            assert "successful" in result.output.lower()
            assert "Deleted 2 resources" in result.output

    def test_v2_rollback_failed_status(self, runner: CliRunner, v2_group) -> None:
        """Test rollback that doesn't reach ROLLED_BACK status."""
        from souschef.migration_v2 import MigrationStatus as RealStatus

        mock_result = MagicMock()
        mock_result.status = RealStatus.DEPLOYED
        mock_result.chef_version = "15.0.0"
        mock_result.target_platform = "awx"
        mock_result.target_version = "2.0.0"
        mock_result.playbooks_generated = ["playbook1.yml"]
        mock_result.errors = [{"error": "Resource not found"}]

        with patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch:
            mock_orch.load_state.return_value = mock_result

            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance
            mock_instance.result = mock_result

            # Mock failed rollback (status doesn't change to ROLLED_BACK)
            def mock_rollback(url, creds):
                mock_instance.result.status = RealStatus.FAILED

            mock_instance.rollback = mock_rollback

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
                    "mig-failed",
                ],
            )

            # Should exit with error
            assert result.exit_code != 0
            assert "Rollback failed" in result.output
            assert "Resource not found" in result.output
