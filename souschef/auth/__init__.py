"""Authentication component for SousChef architecture boundaries."""

from souschef.auth.rbac import (
    ROLE_PERMISSIONS,
    VALID_ROLES,
    AccessDecision,
    PermissionDeniedError,
    has_permission,
    normalise_role,
    require_permission,
)

__all__ = [
    "VALID_ROLES",
    "ROLE_PERMISSIONS",
    "PermissionDeniedError",
    "AccessDecision",
    "normalise_role",
    "has_permission",
    "require_permission",
]
