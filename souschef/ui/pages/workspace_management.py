"""Workspace membership and role management page."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from souschef.api import (
    bootstrap_workspace_owner,
    list_workspace_audit_events,
    list_workspace_members,
    set_workspace_role,
)
from souschef.auth import VALID_ROLES, PermissionDeniedError

if TYPE_CHECKING:
    import streamlit as st
else:
    try:
        import streamlit as st
    except ImportError:
        st = None


def _render_page_header() -> None:
    """Render page header and navigation controls."""
    col1, _col2 = st.columns([1, 4])
    with col1:
        if st.button(
            "Back to Dashboard",
            key="back_to_dashboard_from_workspace",
            help="Return to main dashboard",
        ):
            st.session_state.current_page = "Dashboard"
            st.rerun()

    st.markdown(
        """
Manage workspace members and roles.
Use this page to invite or assign users and review workspace audit activity.
        """
    )


def _get_workspace_context() -> tuple[str, str]:
    """Collect workspace and actor user context from input fields."""
    st.subheader("Workspace Context")
    col1, col2 = st.columns(2)

    with col1:
        workspace_id = st.text_input(
            "Workspace ID",
            value=st.session_state.get("workspace_id", "default"),
            key="workspace_id_input",
            help="Unique workspace identifier.",
        ).strip()

    with col2:
        actor_user_id = st.text_input(
            "Your User ID",
            value=st.session_state.get("workspace_actor_user_id", ""),
            key="workspace_actor_user_id_input",
            help="User ID used for role checks and audit logging.",
        ).strip()

    st.session_state.workspace_id = workspace_id
    st.session_state.workspace_actor_user_id = actor_user_id
    return workspace_id, actor_user_id


def _require_context(workspace_id: str, actor_user_id: str) -> bool:
    """Validate required workspace and actor fields are provided."""
    missing = []
    if not workspace_id:
        missing.append("Workspace ID")
    if not actor_user_id:
        missing.append("Your User ID")

    if missing:
        st.error(f"Missing required fields: {', '.join(missing)}")
        return False
    return True


def _render_bootstrap_actions(workspace_id: str, actor_user_id: str) -> None:
    """Render workspace bootstrap controls for initial owner setup."""
    if st.button(
        "Bootstrap Workspace Owner",
        key="workspace_bootstrap_owner",
        help="Assign yourself as owner when workspace has no members yet.",
    ):
        if not _require_context(workspace_id, actor_user_id):
            return

        created = bootstrap_workspace_owner(workspace_id, actor_user_id)
        if created:
            st.success("Workspace owner bootstrap complete.")
        else:
            st.info("Workspace already has members. Bootstrap skipped.")


def _render_member_invite_form(workspace_id: str, actor_user_id: str) -> None:
    """Render invite and role assignment form."""
    st.subheader("Invite or Assign Member")

    col1, col2 = st.columns([2, 1])
    with col1:
        target_user_id = st.text_input(
            "User ID",
            key="workspace_target_user_id",
            placeholder="e.g. alice",
            help="Identifier for user to invite/assign.",
        ).strip()

    with col2:
        selected_role = st.selectbox(
            "Role",
            options=[role.title() for role in VALID_ROLES],
            key="workspace_target_role",
            help="Role to assign to the user.",
        )

    if st.button("Invite / Assign", key="workspace_invite_assign"):
        if not _require_context(workspace_id, actor_user_id):
            return

        if not target_user_id:
            st.error("User ID is required.")
            return

        try:
            set_workspace_role(
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                role=selected_role,
            )
        except PermissionDeniedError as exc:
            st.error(str(exc))
            return
        except ValueError as exc:
            st.error(str(exc))
            return

        st.success(f"Assigned role {selected_role.lower()} to {target_user_id}.")
        st.rerun()


def _render_members_table(workspace_id: str, actor_user_id: str) -> None:
    """Render member list for the selected workspace."""
    st.subheader("Workspace Members")

    if not _require_context(workspace_id, actor_user_id):
        return

    try:
        members = list_workspace_members(workspace_id, actor_user_id)
    except PermissionDeniedError as exc:
        st.error(str(exc))
        return

    if not members:
        st.info("No members assigned in this workspace yet.")
        return

    rows: list[dict[str, Any]] = []
    for member in members:
        rows.append(
            {
                "User": member.user_id,
                "Role": member.role,
                "Updated By": member.updated_by or "-",
                "Updated At": member.updated_at,
            }
        )

    st.dataframe(rows, hide_index=True, width="stretch")


def _format_event_details(raw_details: str) -> str:
    """Format audit event details from JSON blob to display text."""
    try:
        parsed = json.loads(raw_details or "{}")
        if isinstance(parsed, dict) and parsed:
            return ", ".join(f"{key}={value}" for key, value in parsed.items())
    except json.JSONDecodeError:
        pass
    return "-"


def _render_audit_timeline(workspace_id: str, actor_user_id: str) -> None:
    """Render recent workspace audit events."""
    st.subheader("Audit Timeline")

    if not _require_context(workspace_id, actor_user_id):
        return

    try:
        events = list_workspace_audit_events(workspace_id, actor_user_id, limit=50)
    except PermissionDeniedError as exc:
        st.error(str(exc))
        return

    if not events:
        st.info("No audit events for this workspace yet.")
        return

    rows = [
        {
            "When": event.created_at,
            "Action": f"{event.event_type}:{event.action}",
            "Actor": event.user_id,
            "Target": event.target_user_id or "-",
            "Details": _format_event_details(event.details),
        }
        for event in events
    ]
    st.dataframe(rows, hide_index=True, width="stretch")


def show_workspace_management_page() -> None:
    """Show workspace management UI page."""
    _render_page_header()
    workspace_id, actor_user_id = _get_workspace_context()

    _render_bootstrap_actions(workspace_id, actor_user_id)
    st.divider()

    _render_member_invite_form(workspace_id, actor_user_id)
    st.divider()

    _render_members_table(workspace_id, actor_user_id)
    st.divider()

    _render_audit_timeline(workspace_id, actor_user_id)
