"""Unit tests for workspace RBAC API facade."""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from souschef.api.workspace_api import (
    bootstrap_workspace_owner,
    create_analysis_record,
    create_approval_request,
    create_conversion_record,
    decide_approval_request,
    list_workspace_approval_requests,
    list_workspace_audit_events,
    list_workspace_members,
    remove_workspace_member,
    set_workspace_role,
)
from souschef.auth import PermissionDeniedError
from souschef.auth.rbac import has_permission, normalise_role
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


def test_bootstrap_workspace_owner_returns_false_when_members_exist(tmp_path) -> None:
    """Bootstrapping should no-op once a workspace already has members."""
    storage = _new_storage(tmp_path)
    bootstrap_workspace_owner("ws1", "owner-user", storage_manager=storage)

    assert (
        bootstrap_workspace_owner(
            "ws1",
            "another-user",
            storage_manager=storage,
        )
        is False
    )


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


def test_approval_request_approve_branch_with_comment(tmp_path) -> None:
    """Approval requests should support pending to approved transition."""
    storage = _new_storage(tmp_path)
    bootstrap_workspace_owner("ws1", "owner-user", storage_manager=storage)
    set_workspace_role(
        workspace_id="ws1",
        actor_user_id="owner-user",
        target_user_id="editor-user",
        role="editor",
        storage_manager=storage,
    )

    request_id = create_approval_request(
        workspace_id="ws1",
        actor_user_id="editor-user",
        action="production_conversion",
        request_comment="Need approval before deploy",
        storage_manager=storage,
    )
    assert request_id is not None

    decided = decide_approval_request(
        workspace_id="ws1",
        actor_user_id="owner-user",
        request_id=request_id,
        decision="approved",
        decision_comment="Approved after review",
        storage_manager=storage,
    )
    assert decided is not None
    assert decided.status == "approved"
    assert decided.decision_comment == "Approved after review"

    requests = list_workspace_approval_requests(
        workspace_id="ws1",
        actor_user_id="owner-user",
        storage_manager=storage,
    )
    assert requests[0].status == "approved"

    events = list_workspace_audit_events("ws1", "owner-user", storage_manager=storage)
    actions = [event.action for event in events]
    assert "request_created" in actions
    assert "request_approved" in actions


def test_approval_request_reject_branch_requires_decision_permission(tmp_path) -> None:
    """Approval decision should support rejection and deny non-approvers."""
    storage = _new_storage(tmp_path)
    bootstrap_workspace_owner("ws1", "owner-user", storage_manager=storage)
    set_workspace_role(
        workspace_id="ws1",
        actor_user_id="owner-user",
        target_user_id="editor-user",
        role="editor",
        storage_manager=storage,
    )

    request_id = create_approval_request(
        workspace_id="ws1",
        actor_user_id="editor-user",
        action="rotate_credentials",
        request_comment="Need explicit rejection test",
        storage_manager=storage,
    )
    assert request_id is not None

    with pytest.raises(PermissionDeniedError):
        decide_approval_request(
            workspace_id="ws1",
            actor_user_id="editor-user",
            request_id=request_id,
            decision="rejected",
            decision_comment="Editors cannot decide",
            storage_manager=storage,
        )

    decided = decide_approval_request(
        workspace_id="ws1",
        actor_user_id="owner-user",
        request_id=request_id,
        decision="rejected",
        decision_comment="Rejected due to missing change window",
        storage_manager=storage,
    )
    assert decided is not None
    assert decided.status == "rejected"


def test_decide_approval_request_handles_missing_and_mismatched_requests(
    tmp_path,
) -> None:
    """Approval decisions should handle missing and cross-workspace requests."""
    storage = _new_storage(tmp_path)
    bootstrap_workspace_owner("ws1", "owner-user", storage_manager=storage)
    bootstrap_workspace_owner("ws2", "owner-two", storage_manager=storage)
    set_workspace_role(
        workspace_id="ws1",
        actor_user_id="owner-user",
        target_user_id="editor-user",
        role="editor",
        storage_manager=storage,
    )

    assert (
        decide_approval_request(
            workspace_id="ws1",
            actor_user_id="owner-user",
            request_id=9999,
            decision="approved",
            storage_manager=storage,
        )
        is None
    )

    request_id = create_approval_request(
        workspace_id="ws2",
        actor_user_id="owner-two",
        action="rotate_credentials",
        request_comment="Cross-workspace mismatch",
        storage_manager=storage,
    )

    with pytest.raises(ValueError, match="does not belong to workspace"):
        decide_approval_request(
            workspace_id="ws1",
            actor_user_id="owner-user",
            request_id=request_id,
            decision="approved",
            storage_manager=storage,
        )


def test_cannot_demote_final_owner(tmp_path) -> None:
    """Role reassignment should prevent demoting the final owner in a workspace."""
    storage = _new_storage(tmp_path)
    bootstrap_workspace_owner("ws1", "owner-user", storage_manager=storage)

    with pytest.raises(ValueError, match="final owner"):
        set_workspace_role(
            workspace_id="ws1",
            actor_user_id="owner-user",
            target_user_id="owner-user",
            role="admin",
            storage_manager=storage,
        )


def test_remove_workspace_member_and_audit_event(tmp_path) -> None:
    """Removing a member should revoke access and emit an audit event."""
    storage = _new_storage(tmp_path)
    bootstrap_workspace_owner("ws1", "owner-user", storage_manager=storage)
    set_workspace_role(
        workspace_id="ws1",
        actor_user_id="owner-user",
        target_user_id="editor-user",
        role="editor",
        storage_manager=storage,
    )

    removed = remove_workspace_member(
        workspace_id="ws1",
        actor_user_id="owner-user",
        target_user_id="editor-user",
        storage_manager=storage,
    )
    assert removed
    assert storage.get_workspace_role("ws1", "editor-user") is None

    events = list_workspace_audit_events("ws1", "owner-user", storage_manager=storage)
    assert any(event.action == "member_removed" for event in events)


def test_remove_workspace_member_returns_false_when_target_missing(tmp_path) -> None:
    """Removing a non-member should return False without raising."""
    storage = _new_storage(tmp_path)
    bootstrap_workspace_owner("ws1", "owner-user", storage_manager=storage)

    assert (
        remove_workspace_member(
            workspace_id="ws1",
            actor_user_id="owner-user",
            target_user_id="missing-user",
            storage_manager=storage,
        )
        is False
    )


def test_list_workspace_audit_events_applies_filters(tmp_path) -> None:
    """Audit event listing should honour actor, action, and date filters."""
    storage = _new_storage(tmp_path)
    bootstrap_workspace_owner("ws1", "owner-user", storage_manager=storage)
    set_workspace_role(
        workspace_id="ws1",
        actor_user_id="owner-user",
        target_user_id="editor-user",
        role="editor",
        storage_manager=storage,
    )

    all_events = list_workspace_audit_events(
        "ws1",
        "owner-user",
        storage_manager=storage,
    )
    assert all_events

    actor_filtered = list_workspace_audit_events(
        "ws1",
        "owner-user",
        actor_filter="owner-user",
        storage_manager=storage,
    )
    assert actor_filtered
    assert all(event.user_id == "owner-user" for event in actor_filtered)

    actor_no_match = list_workspace_audit_events(
        "ws1",
        "owner-user",
        actor_filter="no-such-user",
        storage_manager=storage,
    )
    assert actor_no_match == []

    action_filtered = list_workspace_audit_events(
        "ws1",
        "owner-user",
        action_filter="bootstrap_owner",
        storage_manager=storage,
    )
    assert action_filtered
    assert all(event.action == "bootstrap_owner" for event in action_filtered)

    action_no_match = list_workspace_audit_events(
        "ws1",
        "owner-user",
        action_filter="no-such-action",
        storage_manager=storage,
    )
    assert action_no_match == []

    future_filtered = list_workspace_audit_events(
        "ws1",
        "owner-user",
        date_from=date.today() + timedelta(days=1),
        storage_manager=storage,
    )
    assert future_filtered == []

    past_filtered = list_workspace_audit_events(
        "ws1",
        "owner-user",
        date_to=date.today() - timedelta(days=1),
        storage_manager=storage,
    )
    assert past_filtered == []


def test_cannot_remove_final_owner(tmp_path) -> None:
    """Workspace must retain at least one owner when removing members."""
    storage = _new_storage(tmp_path)
    bootstrap_workspace_owner("ws1", "owner-user", storage_manager=storage)

    with pytest.raises(ValueError, match="final owner"):
        remove_workspace_member(
            workspace_id="ws1",
            actor_user_id="owner-user",
            target_user_id="owner-user",
            storage_manager=storage,
        )


def test_normalise_role_rejects_invalid_role() -> None:
    """Role normalisation should reject unsupported roles."""
    with pytest.raises(ValueError, match="Invalid role"):
        normalise_role("guest")


def test_has_permission_returns_false_for_missing_role() -> None:
    """Permission checks should deny access when no role is assigned."""
    assert has_permission(None, "analysis:create") is False
