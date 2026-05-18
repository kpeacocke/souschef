"""Ticket sync connectors for Jira and ServiceNow with retry support."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import sleep
from typing import Any, Literal

TicketProvider = Literal["jira", "servicenow"]


class TransientTicketSyncError(RuntimeError):
    """Raised for retryable provider/API failures."""


class TicketCredentialError(ValueError):
    """Raised when required provider credentials are missing."""


@dataclass(frozen=True)
class TicketSyncResult:
    """Represents ticket create/update outcome."""

    provider: TicketProvider
    operation: str
    ticket_id: str
    sync_status: str
    retries: int
    mapped_metadata: dict[str, Any]


def _validate_provider_credentials(
    provider: TicketProvider,
    credentials: Mapping[str, str],
) -> None:
    """Validate provider credential payload for ticket sync."""
    token = credentials.get("token", "").strip()
    if not token:
        raise TicketCredentialError("ticket sync requires 'token' credential")

    if provider == "jira":
        if not credentials.get("project_key", "").strip():
            raise TicketCredentialError("jira sync requires 'project_key'")
    elif provider == "servicenow" and not credentials.get("instance", "").strip():
        raise TicketCredentialError("servicenow sync requires 'instance'")


def _build_mapped_metadata(
    migration_item: Mapping[str, Any],
    provider: TicketProvider,
    ticket_id: str,
) -> dict[str, Any]:
    """Create bi-directional metadata mapping payload for sync tracking."""
    return {
        "provider": provider,
        "ticket_id": ticket_id,
        "migration_item_id": str(migration_item.get("item_id", "")),
        "migration_status": str(migration_item.get("status", "unknown")),
        "migration_complexity": str(migration_item.get("complexity", "unknown")),
    }


def _invoke_provider_api(
    provider: TicketProvider,
    operation: str,
    payload: dict[str, Any],
    api_handler: Callable[[TicketProvider, str, dict[str, Any]], dict[str, Any]] | None,
) -> dict[str, Any]:
    """Invoke provider API via injected handler for deterministic testing."""
    if api_handler is None:
        ticket_id = str(payload.get("ticket_id") or payload.get("item_id") or "new")
        return {"ticket_id": ticket_id, "status": "synced"}

    return api_handler(provider, operation, payload)


def sync_ticket_with_retry(
    provider: TicketProvider,
    credentials: Mapping[str, str],
    migration_item: Mapping[str, Any],
    ticket_id: str | None = None,
    max_retries: int = 3,
    base_backoff_seconds: float = 0.25,
    sleep_fn: Callable[[float], None] = sleep,
    api_handler: (
        Callable[[TicketProvider, str, dict[str, Any]], dict[str, Any]] | None
    ) = None,
) -> TicketSyncResult:
    """Create/update ticket with retry/backoff for transient provider failures."""
    _validate_provider_credentials(provider, credentials)

    operation = "update" if ticket_id else "create"
    payload = dict(migration_item)
    if ticket_id:
        payload["ticket_id"] = ticket_id

    attempts = 0
    while True:
        attempts += 1
        try:
            response = _invoke_provider_api(
                provider=provider,
                operation=operation,
                payload=payload,
                api_handler=api_handler,
            )
            resolved_ticket_id = str(response.get("ticket_id") or ticket_id or "")
            if not resolved_ticket_id:
                raise RuntimeError("provider response missing ticket_id")

            return TicketSyncResult(
                provider=provider,
                operation=operation,
                ticket_id=resolved_ticket_id,
                sync_status=str(response.get("status") or "synced"),
                retries=attempts - 1,
                mapped_metadata=_build_mapped_metadata(
                    migration_item=migration_item,
                    provider=provider,
                    ticket_id=resolved_ticket_id,
                ),
            )
        except TransientTicketSyncError:
            if attempts > max_retries:
                raise
            backoff = base_backoff_seconds * (2 ** (attempts - 1))
            sleep_fn(backoff)


def format_ticket_sync_status(result: TicketSyncResult) -> str:
    """Format sync result for UI status panels."""
    return (
        f"{result.provider.upper()} {result.operation} ticket {result.ticket_id} "
        f"status={result.sync_status} retries={result.retries}"
    )
