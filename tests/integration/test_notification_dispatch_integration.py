"""Integration-style tests for mocked Slack/Teams dispatch handlers."""

from __future__ import annotations

from souschef.integrations.notification_dispatch import (
    NotificationConfig,
    TransientNotificationError,
    dispatch_notification,
)


def test_slack_dispatch_with_mocked_handler() -> None:
    """Slack dispatch should succeed with mocked provider response."""

    def handler(_config, message):
        assert "Release published" in message
        return {"status": "sent"}

    result = dispatch_notification(
        config=NotificationConfig(
            provider="slack",
            webhook_url="https://hooks.slack.com/services/a/b/c",
            channel="#release",
        ),
        event_type="release_published",
        payload={"version": "7.5.0"},
        dispatch_fn=handler,
    )

    assert result.status == "sent"
    assert not result.dead_lettered


def test_teams_dispatch_with_retry_then_success() -> None:
    """Teams dispatch should retry transient failures before succeeding."""
    attempts = {"count": 0}
    waits: list[float] = []

    def handler(_config, _message):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise TransientNotificationError("temporary")
        return {"status": "sent"}

    result = dispatch_notification(
        config=NotificationConfig(
            provider="teams",
            webhook_url="https://example.office.com/webhook/123",
            channel="ops",
        ),
        event_type="migration_milestone",
        payload={"milestone": "phase-2", "progress": "80%"},
        max_retries=4,
        base_backoff_seconds=0.05,
        dispatch_fn=handler,
        sleep_fn=waits.append,
    )

    assert result.status == "sent"
    assert result.attempts == 3
    assert waits == [0.05, 0.1]
