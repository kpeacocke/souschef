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


def test_start_v2_migration_failure() -> None:
    """Start v2 migration returns failure payload on exception."""
    with patch(
        "souschef.server.MigrationOrchestrator",
        side_effect=RuntimeError("boom"),
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
    assert "boom" in data["error"]
