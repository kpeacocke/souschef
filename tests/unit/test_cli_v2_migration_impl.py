"""Tests for _run_v2_migration implementation function."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from souschef.cli_v2_commands import _run_v2_migration


class TestRunV2Migration:
    """Test _run_v2_migration implementation function."""

    def test_run_v2_migration_invalid_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Invalid cookbook path exits with error."""

        def raise_error(*_args, **_kwargs):
            raise ValueError("Path does not exist")

        monkeypatch.setattr("souschef.cli_v2_commands._validate_user_path", raise_error)

        with pytest.raises(SystemExit) as exc_info:
            _run_v2_migration(
                cookbook_path="/invalid/path",
                chef_version="15.0.0",
                target_platform="awx",
                target_version="2.0.0",
                chef_server_config={},
                output_config={"type": "playbook", "format": "json", "path": None},
                migration_options={
                    "skip_validation": False,
                    "save_state": False,
                    "analysis_id": None,
                },
            )

        assert exc_info.value.code == 1

    def test_run_v2_migration_not_directory(self, tmp_path: Path) -> None:
        """Non-directory cookbook path exits with error."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        with pytest.raises(SystemExit) as exc_info:
            _run_v2_migration(
                cookbook_path=str(file_path),
                chef_version="15.0.0",
                target_platform="awx",
                target_version="2.0.0",
                chef_server_config={},
                output_config={"type": "playbook", "format": "json", "path": None},
                migration_options={
                    "skip_validation": False,
                    "save_state": False,
                    "analysis_id": None,
                },
            )

        assert exc_info.value.code == 1

    def test_run_v2_migration_orchestrator_exception(self, tmp_path: Path) -> None:
        """Orchestrator exception is caught and exits."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()

        with patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch:
            mock_orch.return_value.migrate_cookbook.side_effect = RuntimeError(
                "Migration failed"
            )

            with pytest.raises(SystemExit) as exc_info:
                _run_v2_migration(
                    cookbook_path=str(cookbook_dir),
                    chef_version="15.0.0",
                    target_platform="awx",
                    target_version="2.0.0",
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
                        "save_state": False,
                        "analysis_id": None,
                    },
                )

            assert exc_info.value.code == 1

    def test_run_v2_migration_success_json_output(self, tmp_path: Path, capsys) -> None:
        """Successful migration with json output."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()

        mock_result = MagicMock()
        mock_result.status = "completed"
        mock_result.to_dict.return_value = {"status": "completed", "files_generated": 5}

        with patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch:
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance
            mock_instance.migrate_cookbook.return_value = mock_result

            _run_v2_migration(
                cookbook_path=str(cookbook_dir),
                chef_version="15.0.0",
                target_platform="awx",
                target_version="2.0.0",
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
                    "save_state": False,
                    "analysis_id": None,
                },
            )

        captured = capsys.readouterr()
        # Should output JSON
        output = json.loads(captured.out)
        assert output["status"] == "completed"

    def test_run_v2_migration_save_state(self, tmp_path: Path) -> None:
        """Migration with save_state includes storage_id in output."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()

        mock_result = MagicMock()
        mock_result.status = "completed"
        mock_result.to_dict.return_value = {"status": "completed"}

        with (
            patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch,
            patch("souschef.cli_v2_commands._output_result"),
        ):
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance
            mock_instance.migrate_cookbook.return_value = mock_result
            mock_instance.save_state.return_value = "storage-id-123"

            _run_v2_migration(
                cookbook_path=str(cookbook_dir),
                chef_version="15.0.0",
                target_platform="awx",
                target_version="2.0.0",
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
                    "analysis_id": 42,
                },
            )

            # Verify save_state was called
            mock_instance.save_state.assert_called_once()
            call_args = mock_instance.save_state.call_args
            assert call_args[1]["analysis_id"] == 42

    def test_run_v2_migration_failure_status_exits(self, tmp_path: Path) -> None:
        """Migration with FAILED status exits with code 1."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()

        mock_result = MagicMock()
        mock_result.status = "FAILED"
        mock_result.to_dict.return_value = {"status": "FAILED"}

        with (
            patch("souschef.cli_v2_commands.MigrationOrchestrator") as mock_orch,
            patch("souschef.cli_v2_commands.MigrationStatus") as mock_status,
            pytest.raises(SystemExit) as exc_info,
        ):
            mock_status.FAILED = "FAILED"
            mock_instance = MagicMock()
            mock_orch.return_value = mock_instance
            mock_instance.migrate_cookbook.return_value = mock_result

            _run_v2_migration(
                cookbook_path=str(cookbook_dir),
                chef_version="15.0.0",
                target_platform="awx",
                target_version="2.0.0",
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
                    "save_state": False,
                    "analysis_id": None,
                },
            )

        assert exc_info.value.code == 1
