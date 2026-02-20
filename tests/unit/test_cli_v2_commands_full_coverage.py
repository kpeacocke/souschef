"""Tests for v2 CLI commands to improve coverage."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

import souschef.cli_v2_commands as cli_v2
from souschef.migration_v2 import MigrationStatus


class TestPathValidation:
    """Tests for path validation helpers."""

    def test_validate_user_path_none_defaults(self) -> None:
        """It defaults to current working directory."""
        result = cli_v2._validate_user_path(None)
        assert result == Path.cwd()

    def test_validate_user_path_missing(self, tmp_path: Path) -> None:
        """It raises for missing paths."""
        missing = tmp_path / "missing"
        with pytest.raises(ValueError, match="does not exist"):
            cli_v2._validate_user_path(str(missing))

    def test_validate_user_path_os_error(self) -> None:
        """It raises on OS errors."""
        with patch("pathlib.Path.resolve") as mock_resolve:
            mock_resolve.side_effect = OSError("bad")
            with pytest.raises(ValueError, match="Invalid path"):
                cli_v2._validate_user_path("/bad")


class TestOutputPaths:
    """Tests for output path helpers."""

    def test_resolve_output_path_default(self, tmp_path: Path) -> None:
        """It resolves default output within workspace root."""
        default = tmp_path / "out.json"
        with (
            patch("souschef.cli_v2_commands._get_workspace_root") as mock_root,
            patch("souschef.cli_v2_commands._ensure_within_base_path") as mock_safe,
        ):
            mock_root.return_value = tmp_path
            mock_safe.return_value = default
            result = cli_v2._resolve_output_path(None, default)
        assert result == default

    def test_resolve_output_path_invalid(self, tmp_path: Path) -> None:
        """It aborts when output path is invalid."""
        default = tmp_path / "out.json"
        with (
            patch("souschef.cli_v2_commands._get_workspace_root") as mock_root,
            patch("souschef.cli_v2_commands._ensure_within_base_path") as mock_safe,
        ):
            mock_root.return_value = tmp_path
            mock_safe.side_effect = ValueError("bad")
            with pytest.raises(click.Abort):
                cli_v2._resolve_output_path("../bad", default)

    def test_safe_write_file_writes(self, tmp_path: Path) -> None:
        """It writes content to the resolved file path."""
        target = tmp_path / "result.json"
        with patch("souschef.cli_v2_commands._resolve_output_path") as mock_resolve:
            mock_resolve.return_value = target
            result = cli_v2._safe_write_file("content", None, target)
        assert result == target
        assert target.read_text(encoding="utf-8") == "content"

    def test_safe_write_file_os_error(self, tmp_path: Path) -> None:
        """It aborts when file writing fails."""
        target = tmp_path / "result.json"
        with (
            patch("souschef.cli_v2_commands._resolve_output_path") as mock_resolve,
            patch("pathlib.Path.open") as mock_open,
        ):
            mock_resolve.return_value = target
            mock_open.side_effect = OSError("bad")
            with pytest.raises(click.Abort):
                cli_v2._safe_write_file("content", None, target)


class TestOutputResult:
    """Tests for output formatting."""

    def test_output_result_json_valid(self, capsys) -> None:
        """It pretty prints JSON output."""
        cli_v2._output_result(json.dumps({"ok": True}), "json")
        captured = capsys.readouterr()
        assert "ok" in captured.out

    def test_output_result_json_invalid(self) -> None:
        """It exits on invalid JSON output."""
        with pytest.raises(SystemExit):
            cli_v2._output_result("not json", "json")

    def test_output_result_text(self, capsys) -> None:
        """It outputs text unchanged."""
        cli_v2._output_result("hello", "text")
        captured = capsys.readouterr()
        assert captured.out.strip() == "hello"


class TestRunMigration:
    """Tests for v2 migration execution."""

    def test_run_v2_migration_invalid_directory(self) -> None:
        """It exits when cookbook path is not a directory."""
        with patch("souschef.cli_v2_commands._validate_user_path") as mock_validate:
            mock_validate.return_value = Path("/tmp/file")  # NOSONAR
            with pytest.raises(SystemExit):
                cli_v2._run_v2_migration(
                    cookbook_path="/tmp/file",  # NOSONAR
                    chef_version="15",
                    target_platform="awx",
                    target_version="24.6",
                    chef_server_config={},
                    output_config={"type": "playbook", "format": "json", "path": None},
                    migration_options={
                        "skip_validation": False,
                        "save_state": False,
                        "analysis_id": None,
                    },
                )

    def test_run_v2_migration_success(self, tmp_path: Path) -> None:
        """It outputs results when migration succeeds."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        result = SimpleNamespace(
            status=MigrationStatus.CONVERTED,
            to_dict=lambda: {"status": "success"},
        )
        orchestrator = MagicMock()
        orchestrator.migrate_cookbook.return_value = result
        orchestrator.save_state.return_value = "storage-id"

        with (
            patch(
                "souschef.cli_v2_commands._validate_user_path",
                return_value=cookbook_dir,
            ),
            patch(
                "souschef.cli_v2_commands.MigrationOrchestrator",
                return_value=orchestrator,
            ),
            patch("souschef.cli_v2_commands._output_result") as mock_output,
        ):
            cli_v2._run_v2_migration(
                cookbook_path=str(cookbook_dir),
                chef_version="15",
                target_platform="awx",
                target_version="24.6",
                chef_server_config={
                    "url": None,
                    "organisation": None,
                    "client_name": None,
                    "client_key_path": None,
                    "client_key": None,
                    "query": "*",
                },
                output_config={"type": "playbook", "format": "json", "path": None},
                migration_options={
                    "skip_validation": False,
                    "save_state": True,
                    "analysis_id": 1,
                },
            )
            mock_output.assert_called_once()

    def test_run_v2_migration_failed_status(self, tmp_path: Path) -> None:
        """It exits when migration fails."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        result = SimpleNamespace(
            status=MigrationStatus.FAILED,
            to_dict=lambda: {"status": "failed"},
        )
        orchestrator = MagicMock()
        orchestrator.migrate_cookbook.return_value = result

        with (
            patch(
                "souschef.cli_v2_commands._validate_user_path",
                return_value=cookbook_dir,
            ),
            patch(
                "souschef.cli_v2_commands.MigrationOrchestrator",
                return_value=orchestrator,
            ),
            pytest.raises(SystemExit),
        ):
            cli_v2._run_v2_migration(
                cookbook_path=str(cookbook_dir),
                chef_version="15",
                target_platform="awx",
                target_version="24.6",
                chef_server_config={},
                output_config={"type": "playbook", "format": "json", "path": None},
                migration_options={
                    "skip_validation": False,
                    "save_state": False,
                    "analysis_id": None,
                },
            )


class TestStatusAndListing:
    """Tests for status and listing commands."""

    def test_v2_status_not_found(self) -> None:
        """It exits when migration state is missing."""
        runner = CliRunner()
        with patch(
            "souschef.cli_v2_commands.MigrationOrchestrator.load_state",
            return_value=None,
        ):
            result = runner.invoke(
                cli_v2.v2_status,
                ["--migration-id", "missing", "--limit", "10", "--format", "json"],
            )
        assert result.exit_code == 1

    def test_v2_status_output(self, tmp_path: Path) -> None:
        """It writes status output to file when requested."""
        result = SimpleNamespace(to_dict=lambda: {"status": "ok"})
        output_path = tmp_path / "status.json"
        runner = CliRunner()
        with (
            patch(
                "souschef.cli_v2_commands.MigrationOrchestrator.load_state",
                return_value=result,
            ),
            patch("souschef.cli_v2_commands._safe_write_file") as mock_write,
        ):
            result = runner.invoke(
                cli_v2.v2_status,
                [
                    "--migration-id",
                    "id",
                    "--limit",
                    "10",
                    "--format",
                    "json",
                    "--output",
                    str(output_path),
                ],
            )
        assert result.exit_code == 0
        mock_write.assert_called_once()

    def test_v2_list_no_conversions(self) -> None:
        """It reports when no migrations exist."""
        storage = MagicMock(get_conversion_history=MagicMock(return_value=[]))
        runner = CliRunner()
        with patch("souschef.storage.get_storage_manager", return_value=storage):
            result = runner.invoke(cli_v2.v2_list, ["--limit", "10"])
        assert result.exit_code == 0

    def test_v2_list_json(self) -> None:
        """It outputs migration list as JSON."""
        conversion = SimpleNamespace(
            id=1,
            cookbook_name="test",
            output_type="playbook",
            status="success",
            files_generated=1,
            created_at="now",
            conversion_data=json.dumps(
                {"migration_result": {"migration_id": "abc", "status": "ok"}}
            ),
        )
        storage = MagicMock(get_conversion_history=MagicMock(return_value=[conversion]))
        runner = CliRunner()
        with patch("souschef.storage.get_storage_manager", return_value=storage):
            result = runner.invoke(
                cli_v2.v2_list, ["--limit", "10", "--format", "json"]
            )
        assert result.exit_code == 0


class TestRollback:
    """Tests for rollback command."""

    def test_v2_rollback_not_deployed(self) -> None:
        """It exits when migration is not deployed."""
        result = SimpleNamespace(status=MigrationStatus.FAILED)
        runner = CliRunner()
        with patch(
            "souschef.cli_v2_commands.MigrationOrchestrator.load_state",
            return_value=result,
        ):
            result = runner.invoke(
                cli_v2.v2_rollback,
                [
                    "--url",
                    "url",
                    "--username",
                    "user",
                    "--password",
                    "pass",
                    "--migration-id",
                    "id",
                    "--limit",
                    "10",
                ],
            )
        assert result.exit_code == 1

    def test_v2_rollback_success(self) -> None:
        """It reports success after rollback."""
        migration_result = SimpleNamespace(
            status=MigrationStatus.DEPLOYED,
            chef_version="15",
            target_platform="awx",
            target_version="24.6",
            playbooks_generated=["a"],
            errors=[],
        )
        orchestrator = MagicMock()

        def _mark_rolled_back(*_args, **_kwargs):
            migration_result.status = MigrationStatus.ROLLED_BACK
            migration_result.playbooks_generated = ["a"]
            migration_result.errors = []

        orchestrator.rollback.side_effect = _mark_rolled_back

        runner = CliRunner()
        with patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_class:
            mock_class.load_state.return_value = migration_result
            mock_class.return_value = orchestrator
            cli_result = runner.invoke(
                cli_v2.v2_rollback,
                [
                    "--url",
                    "url",
                    "--username",
                    "user",
                    "--password",
                    "pass",
                    "--migration-id",
                    "id",
                    "--limit",
                    "10",
                ],
            )
        assert cli_result.exit_code == 0

    def test_v2_rollback_failure(self) -> None:
        """It exits when rollback fails."""
        migration_result = SimpleNamespace(
            status=MigrationStatus.DEPLOYED,
            chef_version="15",
            target_platform="awx",
            target_version="24.6",
            playbooks_generated=["a"],
            errors=[],
        )
        orchestrator = MagicMock()
        orchestrator.result = SimpleNamespace(
            status=MigrationStatus.FAILED,
            playbooks_generated=[],
            errors=[{"error": "bad"}],
        )

        runner = CliRunner()
        with patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_class:
            mock_class.load_state.return_value = migration_result
            mock_class.return_value = orchestrator
            cli_result = runner.invoke(
                cli_v2.v2_rollback,
                [
                    "--url",
                    "url",
                    "--username",
                    "user",
                    "--password",
                    "pass",
                    "--migration-id",
                    "id",
                    "--limit",
                    "10",
                ],
            )
        assert cli_result.exit_code == 1
