"""Unit tests for notification API facade."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from souschef.api.notification_api import send_event_notification


@patch("souschef.api.notification_api.log_event")
def test_send_event_notification_success(mock_log_event) -> None:
    """Notification API should dispatch and emit integration audit event."""
    storage_manager = MagicMock()
    storage_manager.get_workspace_role.return_value = "owner"

    result = send_event_notification(
        workspace_id="ws-1",
        actor_user_id="owner",
        provider="slack",
        webhook_url="https://hooks.slack.com/services/a/b/c",
        channel="#release",
        event_type="release_published",
        payload={"version": "7.4.0", "notes": "release"},
        storage_manager=storage_manager,
    )

    assert result.status == "sent"
    assert mock_log_event.called


def test_send_event_notification_rejects_invalid_provider() -> None:
    """Unsupported notification providers should raise validation errors."""
    storage_manager = MagicMock()
    storage_manager.get_workspace_role.return_value = "owner"

    with pytest.raises(ValueError):
        send_event_notification(
            workspace_id="ws-1",
            actor_user_id="owner",
            provider="discord",
            webhook_url="https://example.com",
            channel="ops",
            event_type="release_published",
            payload={"version": "7.4.0"},
            storage_manager=storage_manager,
        )
