"""Unit tests for notification templates, validation, and dispatch retries."""

from __future__ import annotations

import pytest

from souschef.integrations.notification_dispatch import (
    NotificationConfig,
    NotificationConfigError,
    TransientNotificationError,
    dispatch_notification,
    render_notification_message,
    validate_notification_config,
)


def test_render_notification_message_templates() -> None:
    """Release and milestone events should map to explicit templates."""
    release_message = render_notification_message(
        "release_published",
        {"version": "7.3.0", "notes": "Hardening"},
    )
    milestone_message = render_notification_message(
        "migration_milestone",
        {"milestone": "50%", "progress": "50%"},
    )

    assert "Release published" in release_message
    assert "Migration milestone" in milestone_message


def test_validate_notification_config_enforces_provider_webhooks() -> None:
    """Provider config validation should reject invalid webhook targets."""
    validate_notification_config(
        NotificationConfig(
            provider="slack",
            webhook_url="https://hooks.slack.com/services/a/b/c",
            channel="#migrations",
        )
    )

    with pytest.raises(NotificationConfigError):
        validate_notification_config(
            NotificationConfig(
                provider="teams",
                webhook_url="https://hooks.slack.com/services/a/b/c",
                channel="ops",
            )
        )


def test_dispatch_notification_retries_and_dead_letters() -> None:
    """Dispatch should retry transient failures and dead-letter terminal failures."""
    attempts = {"count": 0}
    waits: list[float] = []
    dead_letters: list[dict] = []

    def failing_dispatch(_config, _message):
        attempts["count"] += 1
        raise TransientNotificationError("temporary failure")

    result = dispatch_notification(
        config=NotificationConfig(
            provider="teams",
            webhook_url="https://example.office.com/webhook/123",
            channel="migrations",
        ),
        event_type="release_published",
        payload={"version": "7.3.1"},
        max_retries=2,
        base_backoff_seconds=0.1,
        dispatch_fn=failing_dispatch,
        sleep_fn=waits.append,
        dead_letter_log=dead_letters,
    )

    assert result.dead_lettered
    assert result.status == "dead_lettered"
    assert waits == [0.1, 0.2]
    assert dead_letters


def test_validate_notification_config_rejects_invalid_inputs() -> None:
    """Notification validation should reject invalid schemes, providers, and channels."""
    with pytest.raises(NotificationConfigError, match="https://"):
        validate_notification_config(
            NotificationConfig(
                provider="slack",
                webhook_url="http://hooks.slack.com/services/a/b/c",
                channel="#migrations",
            )
        )

    with pytest.raises(NotificationConfigError, match="Slack webhook URL"):
        validate_notification_config(
            NotificationConfig(
                provider="slack",
                webhook_url="https://example.com/webhook",
                channel="#migrations",
            )
        )

    with pytest.raises(NotificationConfigError, match="Channel must not be empty"):
        validate_notification_config(
            NotificationConfig(
                provider="teams",
                webhook_url="https://teams.microsoft.com/webhook/123",
                channel=" ",
            )
        )


def test_render_notification_message_uses_fallback_template() -> None:
    """Unrecognised events should use the generic fallback template."""
    message = render_notification_message("custom_event", {"value": 1})

    assert "custom_event" in message
    assert "value" in message
