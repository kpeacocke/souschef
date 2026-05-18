"""Unit tests for ticket sync API facade."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from souschef.api.ticket_sync_api import sync_migration_item_ticket


@patch("souschef.api.ticket_sync_api.log_event")
def test_sync_migration_item_ticket_success(mock_log_event) -> None:
    """Ticket sync API should emit audit event and return sync result."""
    storage_manager = MagicMock()
    storage_manager.get_workspace_role.return_value = "owner"

    result = sync_migration_item_ticket(
        workspace_id="ws-1",
        actor_user_id="owner",
        provider="jira",
        credentials={"token": "abc", "project_key": "MIG"},
        migration_item={"item_id": "nginx", "status": "ready", "complexity": "high"},
        storage_manager=storage_manager,
    )

    assert result.provider == "jira"
    assert mock_log_event.called


def test_sync_migration_item_ticket_rejects_unsupported_provider() -> None:
    """Unsupported providers should raise clear validation errors."""
    storage_manager = MagicMock()
    storage_manager.get_workspace_role.return_value = "owner"

    with pytest.raises(ValueError):
        sync_migration_item_ticket(
            workspace_id="ws-1",
            actor_user_id="owner",
            provider="linear",
            credentials={"token": "abc"},
            migration_item={"item_id": "nginx"},
            storage_manager=storage_manager,
        )
