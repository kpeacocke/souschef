"""API facade for Jira/ServiceNow ticket sync workflows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from souschef.audit import log_event
from souschef.integrations.ticket_sync import (
    TicketProvider,
    TicketSyncResult,
    format_ticket_sync_status,
    sync_ticket_with_retry,
)
from souschef.storage import get_storage_manager


def _resolve_storage(storage_manager=None):
    """Resolve storage manager instance for API operations."""
    return storage_manager if storage_manager is not None else get_storage_manager()


def sync_migration_item_ticket(
    workspace_id: str,
    actor_user_id: str,
    provider: str,
    credentials: Mapping[str, str],
    migration_item: Mapping[str, Any],
    ticket_id: str | None = None,
    max_retries: int = 3,
    base_backoff_seconds: float = 0.25,
    storage_manager=None,
) -> TicketSyncResult:
    """Sync migration item to Jira/ServiceNow and emit integration audit event."""
    from souschef.auth import require_permission

    storage = _resolve_storage(storage_manager)
    require_permission(storage, workspace_id, actor_user_id, "conversion:create")

    provider_name = provider.strip().lower()
    if provider_name not in {"jira", "servicenow"}:
        raise ValueError(f"Unsupported ticket provider: {provider}")
    typed_provider = cast(TicketProvider, provider_name)

    result = sync_ticket_with_retry(
        provider=typed_provider,
        credentials=credentials,
        migration_item=migration_item,
        ticket_id=ticket_id,
        max_retries=max_retries,
        base_backoff_seconds=base_backoff_seconds,
    )

    log_event(
        storage_manager=storage,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        event_type="integration",
        action="ticket_synced",
        details={
            "provider": result.provider,
            "ticket_id": result.ticket_id,
            "operation": result.operation,
            "sync_status": result.sync_status,
            "retries": result.retries,
            "status_message": format_ticket_sync_status(result),
        },
    )

    return result
