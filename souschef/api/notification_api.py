"""API facade for outbound Slack/Teams notifications."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from souschef.audit import log_event
from souschef.integrations.notification_dispatch import (
    NotificationConfig,
    NotificationDispatchResult,
    NotificationProvider,
    dispatch_notification,
)
from souschef.storage import get_storage_manager


def _resolve_storage(storage_manager=None):
    """Resolve storage manager instance for API operations."""
    return storage_manager if storage_manager is not None else get_storage_manager()


def send_event_notification(
    workspace_id: str,
    actor_user_id: str,
    provider: str,
    webhook_url: str,
    channel: str,
    event_type: str,
    payload: Mapping[str, Any],
    max_retries: int = 3,
    storage_manager=None,
) -> NotificationDispatchResult:
    """Send release/migration notifications with audit and retry handling."""
    from souschef.auth import require_permission

    storage = _resolve_storage(storage_manager)
    require_permission(storage, workspace_id, actor_user_id, "conversion:create")

    provider_name = provider.strip().lower()
    if provider_name not in {"slack", "teams"}:
        raise ValueError(f"Unsupported notification provider: {provider}")
    typed_provider = cast(NotificationProvider, provider_name)

    config = NotificationConfig(
        provider=typed_provider,
        webhook_url=webhook_url,
        channel=channel,
    )

    dead_letters: list[dict[str, Any]] = []
    result = dispatch_notification(
        config=config,
        event_type=event_type,
        payload=payload,
        max_retries=max_retries,
        dead_letter_log=dead_letters,
    )

    log_event(
        storage_manager=storage,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        event_type="integration",
        action="notification_dispatched",
        details={
            "provider": provider_name,
            "channel": channel,
            "event_type": event_type,
            "status": result.status,
            "attempts": result.attempts,
            "dead_lettered": result.dead_lettered,
            "dead_letters": dead_letters,
        },
    )

    return result
