"""Slack/Teams notification templates and dispatch helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import sleep
from typing import Any, Literal

NotificationProvider = Literal["slack", "teams"]


class NotificationConfigError(ValueError):
    """Raised when notification configuration is invalid."""


class TransientNotificationError(RuntimeError):
    """Raised when notification dispatch fails transiently and can be retried."""


@dataclass(frozen=True)
class NotificationConfig:
    """Configuration payload for outbound notifications."""

    provider: NotificationProvider
    webhook_url: str
    channel: str


@dataclass(frozen=True)
class NotificationDispatchResult:
    """Dispatch result with retry/dead-letter status information."""

    status: str
    attempts: int
    dead_lettered: bool
    message: str


def validate_notification_config(config: NotificationConfig) -> None:
    """Validate Slack/Teams channel and webhook configuration."""
    webhook = config.webhook_url.strip()
    if not webhook.startswith("https://"):
        raise NotificationConfigError("Webhook URL must start with https://")

    if config.provider == "slack" and "hooks.slack.com" not in webhook:
        raise NotificationConfigError("Slack webhook URL must target hooks.slack.com")

    if config.provider == "teams" and (
        "office.com" not in webhook and "teams.microsoft.com" not in webhook
    ):
        raise NotificationConfigError(
            "Teams webhook URL must target office.com or teams.microsoft.com"
        )

    if not config.channel.strip():
        raise NotificationConfigError("Channel must not be empty")


def render_notification_message(
    event_type: str,
    payload: Mapping[str, Any],
) -> str:
    """Render outbound notification text for supported key events."""
    event = event_type.strip().lower()
    if event == "release_published":
        version = payload.get("version", "unknown")
        notes = payload.get("notes", "No release notes provided")
        return f"Release published: {version}. Notes: {notes}"

    if event == "migration_milestone":
        milestone = payload.get("milestone", "unknown")
        progress = payload.get("progress", "0%")
        return f"Migration milestone reached: {milestone} ({progress})."

    return f"SousChef event '{event_type}' occurred. Payload: {dict(payload)}"


def dispatch_notification(
    config: NotificationConfig,
    event_type: str,
    payload: Mapping[str, Any],
    max_retries: int = 3,
    base_backoff_seconds: float = 0.25,
    dispatch_fn: (Callable[[NotificationConfig, str], dict[str, Any]] | None) = None,
    sleep_fn: Callable[[float], None] = sleep,
    dead_letter_log: list[dict[str, Any]] | None = None,
) -> NotificationDispatchResult:
    """Dispatch notification with retry and dead-letter logging support."""
    validate_notification_config(config)
    message = render_notification_message(event_type=event_type, payload=payload)

    attempts = 0
    while True:
        attempts += 1
        try:
            if dispatch_fn is None:
                response = {"status": "sent"}
            else:
                response = dispatch_fn(config, message)

            return NotificationDispatchResult(
                status=str(response.get("status", "sent")),
                attempts=attempts,
                dead_lettered=False,
                message=message,
            )
        except TransientNotificationError as exc:
            if attempts > max_retries:
                if dead_letter_log is not None:
                    dead_letter_log.append(
                        {
                            "provider": config.provider,
                            "event_type": event_type,
                            "message": message,
                            "reason": str(exc),
                            "attempts": attempts,
                        }
                    )
                return NotificationDispatchResult(
                    status="dead_lettered",
                    attempts=attempts,
                    dead_lettered=True,
                    message=message,
                )

            sleep_fn(base_backoff_seconds * (2 ** (attempts - 1)))
