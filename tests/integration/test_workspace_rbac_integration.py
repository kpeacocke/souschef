"""Integration tests for persisted workspace RBAC data."""

from __future__ import annotations

from souschef.api.workspace_api import bootstrap_workspace_owner, set_workspace_role
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
