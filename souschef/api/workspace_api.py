"""Workspace API facade for RBAC-aware mutations and membership management."""

from __future__ import annotations

from typing import Any, cast

from souschef.audit import log_event, log_role_change
from souschef.auth import normalise_role, require_permission
from souschef.storage import get_storage_manager
from souschef.storage.database import AuditEvent, WorkspaceMembership


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


def list_workspace_members(
    workspace_id: str,
    actor_user_id: str,
    storage_manager=None,
) -> list[WorkspaceMembership]:
    """List members in a workspace if actor can view member assignments."""
    storage = _resolve_storage(storage_manager)
    require_permission(storage, workspace_id, actor_user_id, "workspace:member:view")
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
    storage_manager=None,
) -> list[AuditEvent]:
    """List workspace audit events if actor may view workspace membership."""
    storage = _resolve_storage(storage_manager)
    require_permission(storage, workspace_id, actor_user_id, "workspace:member:view")
    events = storage.get_audit_events(workspace_id, limit=limit)
    return cast(list[AuditEvent], events)
