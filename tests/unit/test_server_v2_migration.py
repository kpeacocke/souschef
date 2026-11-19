"""Tests for v2 migration orchestrator handler."""

import json
from unittest.mock import MagicMock, patch

from souschef.server import start_v2_migration


def test_start_v2_migration_success() -> None:
    """Start v2 migration returns orchestrator result."""
    mock_orchestrator = MagicMock()
    mock_result = MagicMock()
    mock_result.to_dict.return_value = {"status": "ok", "id": "m1"}
    mock_orchestrator.migrate_cookbook.return_value = mock_result

    with patch(
        "souschef.server.MigrationOrchestrator",
        return_value=mock_orchestrator,
    ):
        result = start_v2_migration(
            cookbook_path="/tmp/cookbook",
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
            fips_mode="yes",
        )

    data = json.loads(result)
    assert data["status"] == "ok"
    assert data["id"] == "m1"


def test_start_v2_migration_failure_redacts_credential() -> None:
    """Start v2 migration returns failure payload on exception."""
    with patch(
        "souschef.server.MigrationOrchestrator",
        side_effect=RuntimeError("password=do-not-leak"),
    ):
        result = start_v2_migration(
            cookbook_path="/tmp/cookbook",
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

    data = json.loads(result)
    assert data["status"] == "failed"
    assert data["phase"] == "initialization"
    assert "do-not-leak" not in data["error"]


def test_start_v2_migration_rejects_outside_cookbook_before_orchestrating(
    tmp_path,
) -> None:
    """A cookbook outside the configured workspace is rejected before orchestration."""
    outside_path = tmp_path.parent / "outside-cookbook"
    with (
        patch.dict("os.environ", {"SOUSCHEF_WORKSPACE_ROOT": str(tmp_path)}),
        patch("souschef.server.MigrationOrchestrator") as mock_orchestrator,
    ):
        result = start_v2_migration(
            cookbook_path=str(outside_path),
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

    data = json.loads(result)
    assert data["status"] == "failed"
    assert "escapes" in data["error"]
    mock_orchestrator.assert_not_called()
