"""Unit tests for workspace RBAC API facade."""

from __future__ import annotations

import json

import pytest

from souschef.api.workspace_api import (
    bootstrap_workspace_owner,
    create_analysis_record,
    create_conversion_record,
    list_workspace_audit_events,
    list_workspace_members,
    set_workspace_role,
)
from souschef.auth import PermissionDeniedError
from souschef.storage.database import StorageManager


def _new_storage(tmp_path):
    """Create isolated storage manager for RBAC tests."""
    return StorageManager(db_path=tmp_path / "rbac.db")


def test_bootstrap_and_role_assignment_with_audit(tmp_path) -> None:
    """Workspace role assignment should persist and emit role-change audit events."""
    storage = _new_storage(tmp_path)

    assert bootstrap_workspace_owner("ws1", "owner-user", storage_manager=storage)

    set_workspace_role(
        workspace_id="ws1",
        actor_user_id="owner-user",
        target_user_id="editor-user",
        role="editor",
        storage_manager=storage,
    )

    members = list_workspace_members("ws1", "owner-user", storage_manager=storage)
    roles = {member.user_id: member.role for member in members}
    assert roles["owner-user"] == "owner"
    assert roles["editor-user"] == "editor"

    events = list_workspace_audit_events("ws1", "owner-user", storage_manager=storage)
    role_events = [event for event in events if event.action == "role_change"]
    assert role_events
    details = json.loads(role_events[0].details)
    assert details["new_role"] == "editor"


def test_mutating_operations_require_permissions(tmp_path) -> None:
    """Mutating operations should deny users without the required role permissions."""
    storage = _new_storage(tmp_path)
    bootstrap_workspace_owner("ws1", "owner-user", storage_manager=storage)
    set_workspace_role(
        workspace_id="ws1",
        actor_user_id="owner-user",
        target_user_id="viewer-user",
        role="viewer",
        storage_manager=storage,
    )

    with pytest.raises(PermissionDeniedError):
        create_analysis_record(
            workspace_id="ws1",
            actor_user_id="viewer-user",
            cookbook_name="cb1",
            cookbook_path="/opt/souschef/cb1",
            cookbook_version="1.0.0",
            complexity="medium",
            estimated_hours=10.0,
            estimated_hours_with_souschef=5.0,
            recommendations="review",
            analysis_data={"ok": True},
            storage_manager=storage,
        )

    analysis_id = create_analysis_record(
        workspace_id="ws1",
        actor_user_id="owner-user",
        cookbook_name="cb1",
        cookbook_path="/opt/souschef/cb1",
        cookbook_version="1.0.0",
        complexity="medium",
        estimated_hours=10.0,
        estimated_hours_with_souschef=5.0,
        recommendations="review",
        analysis_data={"ok": True},
        storage_manager=storage,
    )
    assert analysis_id is not None

    with pytest.raises(PermissionDeniedError):
        create_conversion_record(
            workspace_id="ws1",
            actor_user_id="viewer-user",
            cookbook_name="cb1",
            output_type="playbook",
            status="success",
            files_generated=3,
            conversion_data={"ok": True},
            analysis_id=analysis_id,
            storage_manager=storage,
        )

    conversion_id = create_conversion_record(
        workspace_id="ws1",
        actor_user_id="owner-user",
        cookbook_name="cb1",
        output_type="playbook",
        status="success",
        files_generated=3,
        conversion_data={"ok": True},
        analysis_id=analysis_id,
        storage_manager=storage,
    )
    assert conversion_id is not None
