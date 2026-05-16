"""Audit event helpers for workspace operations."""

from __future__ import annotations

from typing import Any, cast


def log_event(
    storage_manager,
    workspace_id: str,
    actor_user_id: str,
    event_type: str,
    action: str,
    target_user_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> int | None:
    """Persist a generic workspace audit event."""
    event_id = storage_manager.add_audit_event(
        workspace_id=workspace_id,
        user_id=actor_user_id,
        event_type=event_type,
        action=action,
        target_user_id=target_user_id,
        details=details,
    )
    return cast(int | None, event_id)


def log_role_change(
    storage_manager,
    workspace_id: str,
    actor_user_id: str,
    target_user_id: str,
    previous_role: str | None,
    new_role: str,
) -> int | None:
    """Persist a role-change audit event."""
    return log_event(
        storage_manager=storage_manager,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        event_type="workspace_rbac",
        action="role_change",
        target_user_id=target_user_id,
        details={
            "previous_role": previous_role,
            "new_role": new_role,
        },
    )
