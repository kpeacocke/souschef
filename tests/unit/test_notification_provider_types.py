"""Regression test for notification provider type safety."""

import pytest

from souschef.integrations.notification_dispatch import (
    NotificationConfig,
    NotificationConfigError,
    validate_notification_config,
)


@pytest.mark.parametrize(
    "provider,webhook",
    [
        ("slack", "https://hooks.slack.com/services/abc"),
        ("teams", "https://teams.microsoft.com/l/abc"),
    ],
)
def test_notification_config_accepts_valid_providers(provider, webhook):
    config = NotificationConfig(
        provider=provider, webhook_url=webhook, channel="#general"
    )
    # Should not raise
    validate_notification_config(config)


def test_notification_config_rejects_invalid_provider():
    config = NotificationConfig(
        provider="discord",
        webhook_url="https://discord.com/api/webhooks/abc",
        channel="#general",
    )  # type: ignore
    with pytest.raises(
        NotificationConfigError, match=r"Unsupported notification provider: discord"
    ):
        validate_notification_config(config)
