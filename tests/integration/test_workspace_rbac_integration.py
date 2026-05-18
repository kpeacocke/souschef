"""Integration tests for persisted workspace RBAC data."""

from __future__ import annotations

import pytest

from souschef.api.workspace_api import (
    bootstrap_workspace_owner,
    create_approval_request,
    decide_approval_request,
    remove_workspace_member,
    set_workspace_role,
)
from souschef.storage.database import StorageManager


def test_workspace_roles_persist_across_manager_instances(tmp_path) -> None:
    """Workspace role assignments should persist and be retrievable from DB."""
    db_path = tmp_path / "workspace-rbac.db"

    first = StorageManager(db_path=db_path)
    assert bootstrap_workspace_owner("ws-persist", "alice", storage_manager=first)
    set_workspace_role(
        workspace_id="ws-persist",
        actor_user_id="alice",
        target_user_id="bob",
        role="admin",
        storage_manager=first,
    )

    second = StorageManager(db_path=db_path)
    assert second.get_workspace_role("ws-persist", "alice") == "owner"
    assert second.get_workspace_role("ws-persist", "bob") == "admin"

    events = second.get_audit_events("ws-persist")
    actions = [event.action for event in events]
    assert "bootstrap_owner" in actions
    assert "role_change" in actions


def test_approval_requests_persist_across_manager_instances(tmp_path) -> None:
    """Approval request state transitions should persist in storage."""
    db_path = tmp_path / "workspace-approval.db"

    first = StorageManager(db_path=db_path)
    assert bootstrap_workspace_owner("ws-approval", "alice", storage_manager=first)
    set_workspace_role(
        workspace_id="ws-approval",
        actor_user_id="alice",
        target_user_id="bob",
        role="editor",
        storage_manager=first,
    )

    request_id = create_approval_request(
        workspace_id="ws-approval",
        actor_user_id="bob",
        action="production_release",
        request_comment="Requesting approval",
        storage_manager=first,
    )
    assert request_id is not None

    decide_approval_request(
        workspace_id="ws-approval",
        actor_user_id="alice",
        request_id=request_id,
        decision="approved",
        decision_comment="Approved in integration test",
        storage_manager=first,
    )

    second = StorageManager(db_path=db_path)
    requests = second.list_approval_requests("ws-approval")
    assert requests
    assert requests[0].status == "approved"


def test_workspace_retains_at_least_one_owner(tmp_path) -> None:
    """Member removal should block deleting the final owner role assignment."""
    db_path = tmp_path / "workspace-owner-guard.db"

    storage = StorageManager(db_path=db_path)
    assert bootstrap_workspace_owner("ws-owner-guard", "alice", storage_manager=storage)

    with pytest.raises(ValueError, match="final owner"):
        remove_workspace_member(
            workspace_id="ws-owner-guard",
            actor_user_id="alice",
            target_user_id="alice",
            storage_manager=storage,
        )
