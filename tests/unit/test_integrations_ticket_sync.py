"""Unit tests for ticket sync connector and retry logic."""

from __future__ import annotations

from typing import Any

import pytest

from souschef.integrations.ticket_sync import (
    TicketCredentialError,
    TransientTicketSyncError,
    format_ticket_sync_status,
    sync_ticket_with_retry,
)


def _item() -> dict[str, Any]:
    return {"item_id": "cookbook-nginx", "status": "ready", "complexity": "high"}


def test_sync_ticket_create_success_default_handler() -> None:
    """Default sync path should create ticket result with metadata mapping."""
    result = sync_ticket_with_retry(
        provider="jira",
        credentials={"token": "abc", "project_key": "MIG"},
        migration_item=_item(),
    )

    assert result.operation == "create"
    assert result.sync_status == "synced"
    assert result.mapped_metadata["migration_item_id"] == "cookbook-nginx"


def test_sync_ticket_update_with_retry_backoff() -> None:
    """Transient failures should retry with backoff and then succeed."""
    attempts = {"count": 0}
    waits: list[float] = []

    def handler(_provider, _operation, payload):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise TransientTicketSyncError("temporary")
        return {"ticket_id": payload["ticket_id"], "status": "updated"}

    result = sync_ticket_with_retry(
        provider="servicenow",
        credentials={"token": "abc", "instance": "dev123"},
        migration_item=_item(),
        ticket_id="INC001234",
        max_retries=4,
        base_backoff_seconds=0.1,
        sleep_fn=waits.append,
        api_handler=handler,
    )

    assert result.operation == "update"
    assert result.ticket_id == "INC001234"
    assert result.retries == 2
    assert waits == [0.1, 0.2]


def test_sync_ticket_raises_when_credentials_invalid() -> None:
    """Missing required provider credentials should fail validation."""
    with pytest.raises(TicketCredentialError):
        sync_ticket_with_retry(
            provider="jira",
            credentials={"token": "abc"},
            migration_item=_item(),
        )


def test_format_ticket_sync_status() -> None:
    """UI status formatter should include provider, ticket, and retries."""
    result = sync_ticket_with_retry(
        provider="jira",
        credentials={"token": "abc", "project_key": "MIG"},
        migration_item=_item(),
    )

    summary = format_ticket_sync_status(result)
    assert "JIRA" in summary
    assert "retries=0" in summary
