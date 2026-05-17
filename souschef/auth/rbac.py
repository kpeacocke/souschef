"""Workspace role-based access control helpers."""

from __future__ import annotations

from dataclasses import dataclass

from souschef.core.errors import SousChefError

VALID_ROLES = ("owner", "admin", "editor", "viewer")

PERM_ANALYSIS_CREATE = "analysis:create"
PERM_ANALYSIS_DELETE = "analysis:delete"
PERM_CONVERSION_CREATE = "conversion:create"
PERM_CONVERSION_DELETE = "conversion:delete"
PERM_WORKSPACE_MEMBER_VIEW = "workspace:member:view"
PERM_WORKSPACE_ROLE_UPDATE = "workspace:role:update"

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "owner": {
        PERM_ANALYSIS_CREATE,
        PERM_ANALYSIS_DELETE,
        PERM_CONVERSION_CREATE,
        PERM_CONVERSION_DELETE,
        PERM_WORKSPACE_MEMBER_VIEW,
        PERM_WORKSPACE_ROLE_UPDATE,
    },
    "admin": {
        PERM_ANALYSIS_CREATE,
        PERM_ANALYSIS_DELETE,
        PERM_CONVERSION_CREATE,
        PERM_CONVERSION_DELETE,
        PERM_WORKSPACE_MEMBER_VIEW,
    },
    "editor": {
        PERM_ANALYSIS_CREATE,
        PERM_CONVERSION_CREATE,
        PERM_WORKSPACE_MEMBER_VIEW,
    },
    "viewer": {
        PERM_WORKSPACE_MEMBER_VIEW,
    },
}


class PermissionDeniedError(SousChefError):
    """Raised when a user is not allowed to perform an operation."""


@dataclass(frozen=True)
class AccessDecision:
    """Represents the permission decision for an action."""

    user_id: str
    workspace_id: str
    role: str | None
    action: str
    allowed: bool


def normalise_role(role: str) -> str:
    """Normalise and validate role value."""
    role_normalised = role.strip().lower()
    if role_normalised not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}")
    return role_normalised


def has_permission(role: str | None, action: str) -> bool:
    """Return whether role is allowed to perform action."""
    if role is None:
        return False
    role_normalised = role.strip().lower()
    return action in ROLE_PERMISSIONS.get(role_normalised, set())


def require_permission(
    storage_manager,
    workspace_id: str,
    user_id: str,
    action: str,
) -> AccessDecision:
    """Require permission for an action, raising when denied."""
    role = storage_manager.get_workspace_role(workspace_id, user_id)
    allowed = has_permission(role, action)

    decision = AccessDecision(
        user_id=user_id,
        workspace_id=workspace_id,
        role=role,
        action=action,
        allowed=allowed,
    )

    if not allowed:
        raise PermissionDeniedError(
            message=(
                f"Permission denied for action '{action}' in workspace '{workspace_id}'"
            ),
            suggestion=(
                "Ensure the user has a role that grants this action "
                "(owner/admin/editor/viewer)."
            ),
        )

    return decision
