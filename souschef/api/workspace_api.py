"""Workspace API facade for RBAC-aware mutations and membership management."""

from __future__ import annotations

from datetime import date
from typing import Any, cast

from souschef.audit import log_event, log_role_change
from souschef.auth import normalise_role, require_permission
from souschef.storage import get_storage_manager
from souschef.storage.database import ApprovalRequest, AuditEvent, WorkspaceMembership

PERMISSION_MEMBER_VIEW = "workspace:member:view"


def _resolve_storage(storage_manager=None):
    """Resolve storage manager instance for API operations."""
    return storage_manager if storage_manager is not None else get_storage_manager()


def bootstrap_workspace_owner(
    workspace_id: str,
    user_id: str,
    storage_manager=None,
) -> bool:
    """Create initial owner assignment when a workspace has no members yet."""
    storage = _resolve_storage(storage_manager)
    existing = storage.list_workspace_members(workspace_id)
    if existing:
        return False

    storage.upsert_workspace_role(
        workspace_id=workspace_id,
        user_id=user_id,
        role="owner",
        updated_by=user_id,
    )
    log_event(
        storage_manager=storage,
        workspace_id=workspace_id,
        actor_user_id=user_id,
        event_type="workspace_rbac",
        action="bootstrap_owner",
        target_user_id=user_id,
        details={"role": "owner"},
    )
    return True


def set_workspace_role(
    workspace_id: str,
    actor_user_id: str,
    target_user_id: str,
    role: str,
    storage_manager=None,
) -> None:
    """Assign or update a workspace role, enforcing RBAC and audit logging."""
    storage = _resolve_storage(storage_manager)
    require_permission(storage, workspace_id, actor_user_id, "workspace:role:update")

    new_role = normalise_role(role)
    previous_role = storage.get_workspace_role(workspace_id, target_user_id)

    if previous_role == "owner" and new_role != "owner":
        owner_count = storage.count_workspace_members_with_role(workspace_id, "owner")
        if owner_count <= 1:
            raise ValueError(
                "Cannot reassign the final owner. Assign another owner first."
            )

    storage.upsert_workspace_role(
        workspace_id=workspace_id,
        user_id=target_user_id,
        role=new_role,
        updated_by=actor_user_id,
    )

    log_role_change(
        storage_manager=storage,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        previous_role=previous_role,
        new_role=new_role,
    )


def remove_workspace_member(
    workspace_id: str,
    actor_user_id: str,
    target_user_id: str,
    storage_manager=None,
) -> bool:
    """Remove a workspace member while preserving at least one owner."""
    storage = _resolve_storage(storage_manager)
    require_permission(storage, workspace_id, actor_user_id, "workspace:role:update")

    target_role = storage.get_workspace_role(workspace_id, target_user_id)
    if target_role is None:
        return False

    if target_role == "owner":
        owner_count = storage.count_workspace_members_with_role(workspace_id, "owner")
        if owner_count <= 1:
            raise ValueError("Cannot remove the final owner from a workspace.")

    removed = cast(bool, storage.remove_workspace_member(workspace_id, target_user_id))

    if removed:
        log_event(
            storage_manager=storage,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            event_type="workspace_rbac",
            action="member_removed",
            target_user_id=target_user_id,
            details={"removed_role": target_role},
        )

    return removed


def list_workspace_members(
    workspace_id: str,
    actor_user_id: str,
    storage_manager=None,
) -> list[WorkspaceMembership]:
    """List members in a workspace if actor can view member assignments."""
    storage = _resolve_storage(storage_manager)
    require_permission(storage, workspace_id, actor_user_id, PERMISSION_MEMBER_VIEW)
    members = storage.list_workspace_members(workspace_id)
    return cast(list[WorkspaceMembership], members)


def create_analysis_record(
    workspace_id: str,
    actor_user_id: str,
    cookbook_name: str,
    cookbook_path: str,
    cookbook_version: str,
    complexity: str,
    estimated_hours: float,
    estimated_hours_with_souschef: float,
    recommendations: str,
    analysis_data: dict[str, Any],
    storage_manager=None,
) -> int | None:
    """Create analysis record with RBAC checks and audit event."""
    storage = _resolve_storage(storage_manager)
    require_permission(storage, workspace_id, actor_user_id, "analysis:create")

    analysis_id = storage.save_analysis(
        cookbook_name=cookbook_name,
        cookbook_path=cookbook_path,
        cookbook_version=cookbook_version,
        complexity=complexity,
        estimated_hours=estimated_hours,
        estimated_hours_with_souschef=estimated_hours_with_souschef,
        recommendations=recommendations,
        analysis_data=analysis_data,
    )

    log_event(
        storage_manager=storage,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        event_type="analysis",
        action="create",
        details={"analysis_id": analysis_id, "cookbook_name": cookbook_name},
    )
    return cast(int | None, analysis_id)


def create_conversion_record(
    workspace_id: str,
    actor_user_id: str,
    cookbook_name: str,
    output_type: str,
    status: str,
    files_generated: int,
    conversion_data: dict[str, Any],
    analysis_id: int | None = None,
    storage_manager=None,
) -> int | None:
    """Create conversion record with RBAC checks and audit event."""
    storage = _resolve_storage(storage_manager)
    require_permission(storage, workspace_id, actor_user_id, "conversion:create")

    conversion_id = storage.save_conversion(
        analysis_id=analysis_id,
        cookbook_name=cookbook_name,
        output_type=output_type,
        status=status,
        files_generated=files_generated,
        conversion_data=conversion_data,
    )

    log_event(
        storage_manager=storage,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        event_type="conversion",
        action="create",
        details={"conversion_id": conversion_id, "cookbook_name": cookbook_name},
    )
    return cast(int | None, conversion_id)


def list_workspace_audit_events(
    workspace_id: str,
    actor_user_id: str,
    limit: int = 100,
    actor_filter: str | None = None,
    action_filter: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    storage_manager=None,
) -> list[AuditEvent]:
    """List workspace audit events if actor may view workspace membership."""
    storage = _resolve_storage(storage_manager)
    require_permission(storage, workspace_id, actor_user_id, PERMISSION_MEMBER_VIEW)
    events = storage.get_audit_events(workspace_id, limit=limit)
    filtered_events = _filter_audit_events(
        events=cast(list[AuditEvent], events),
        actor_filter=actor_filter,
        action_filter=action_filter,
        date_from=date_from,
        date_to=date_to,
    )
    return filtered_events


def _filter_audit_events(
    events: list[AuditEvent],
    actor_filter: str | None = None,
    action_filter: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[AuditEvent]:
    """Filter audit events by actor, action, and date range."""
    actor_query = (actor_filter or "").strip().lower()
    action_query = (action_filter or "").strip().lower()

    filtered: list[AuditEvent] = []
    for event in events:
        if actor_query and actor_query not in event.user_id.lower():
            continue

        event_action = f"{event.event_type}:{event.action}".lower()
        if action_query and action_query not in event_action:
            continue

        event_day = event.created_at[:10]
        if date_from and event_day < date_from.isoformat():
            continue
        if date_to and event_day > date_to.isoformat():
            continue

        filtered.append(event)

    return filtered


def create_approval_request(
    workspace_id: str,
    actor_user_id: str,
    action: str,
    request_comment: str,
    target_user_id: str | None = None,
    details: dict[str, Any] | None = None,
    storage_manager=None,
) -> int | None:
    """Create a pending approval request with RBAC checks and audit event."""
    storage = _resolve_storage(storage_manager)
    require_permission(storage, workspace_id, actor_user_id, "approval:request:create")

    request_id = storage.create_approval_request(
        workspace_id=workspace_id,
        action=action,
        requested_by=actor_user_id,
        request_comment=request_comment,
        target_user_id=target_user_id,
        details=details,
    )

    log_event(
        storage_manager=storage,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        event_type="approval",
        action="request_created",
        target_user_id=target_user_id,
        details={
            "request_id": request_id,
            "action": action,
            "request_comment": request_comment,
        },
    )
    return cast(int | None, request_id)


def list_workspace_approval_requests(
    workspace_id: str,
    actor_user_id: str,
    status: str | None = None,
    limit: int = 100,
    storage_manager=None,
) -> list[ApprovalRequest]:
    """List workspace approval requests if actor may view workspace membership."""
    storage = _resolve_storage(storage_manager)
    require_permission(storage, workspace_id, actor_user_id, PERMISSION_MEMBER_VIEW)
    requests = storage.list_approval_requests(workspace_id, status=status, limit=limit)
    return cast(list[ApprovalRequest], requests)


def decide_approval_request(
    workspace_id: str,
    actor_user_id: str,
    request_id: int,
    decision: str,
    decision_comment: str | None = None,
    storage_manager=None,
) -> ApprovalRequest | None:
    """Approve or reject a pending request with comments and audit logging."""
    storage = _resolve_storage(storage_manager)
    require_permission(storage, workspace_id, actor_user_id, "approval:decision:update")

    existing_request = storage.get_approval_request(request_id)
    if existing_request is None:
        return None
    if existing_request.workspace_id != workspace_id:
        raise ValueError(
            "Approval request "
            f"{request_id} does not belong to workspace '{workspace_id}'"
        )

    decided = storage.decide_approval_request(
        request_id=request_id,
        decided_by=actor_user_id,
        decision=decision,
        decision_comment=decision_comment,
    )

    if decided is not None:
        log_event(
            storage_manager=storage,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            event_type="approval",
            action=f"request_{decided.status}",
            target_user_id=decided.target_user_id,
            details={
                "request_id": request_id,
                "decision": decided.status,
                "decision_comment": decision_comment,
            },
        )

    return cast(ApprovalRequest | None, decided)
