"""Integration-style tests for mocked Jira/ServiceNow ticket sync APIs."""

from __future__ import annotations

from souschef.integrations.ticket_sync import (
    TransientTicketSyncError,
    sync_ticket_with_retry,
)


def test_jira_sync_with_mocked_api_handler() -> None:
    """Jira provider handler should map ticket metadata in create flow."""

    def handler(provider, operation, payload):
        assert provider == "jira"
        assert operation == "create"
        return {"ticket_id": "MIG-101", "status": "created"}

    result = sync_ticket_with_retry(
        provider="jira",
        credentials={"token": "abc", "project_key": "MIG"},
        migration_item={"item_id": "cookbook-redis", "status": "ready"},
        api_handler=handler,
    )

    assert result.ticket_id == "MIG-101"
    assert result.sync_status == "created"


def test_servicenow_sync_retries_then_succeeds_with_mocked_api_handler() -> None:
    """ServiceNow handler should retry transient errors before success."""
    call_count = {"count": 0}

    def handler(provider, operation, payload):
        call_count["count"] += 1
        assert provider == "servicenow"
        assert operation == "update"
        if call_count["count"] < 2:
            raise TransientTicketSyncError("temporary")
        return {"ticket_id": payload["ticket_id"], "status": "updated"}

    waits: list[float] = []
    result = sync_ticket_with_retry(
        provider="servicenow",
        credentials={"token": "abc", "instance": "dev123"},
        migration_item={"item_id": "cookbook-nginx", "status": "in_progress"},
        ticket_id="INC001111",
        max_retries=3,
        base_backoff_seconds=0.05,
        sleep_fn=waits.append,
        api_handler=handler,
    )

    assert result.ticket_id == "INC001111"
    assert result.retries == 1
    assert waits == [0.05]
