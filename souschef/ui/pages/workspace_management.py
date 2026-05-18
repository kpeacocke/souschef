"""Workspace membership and role management page."""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING, Any

from souschef.api import (
    bootstrap_workspace_owner,
    create_approval_request,
    decide_approval_request,
    list_workspace_approval_requests,
    list_workspace_audit_events,
    list_workspace_members,
    remove_workspace_member,
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


def _render_remove_member_form(workspace_id: str, actor_user_id: str) -> None:
    """Render controls for removing workspace members."""
    st.subheader("Remove Member")

    target_user_id = st.text_input(
        "User ID to Remove",
        key="workspace_remove_target_user_id",
        placeholder="e.g. alice",
        help="Removes the selected user from this workspace.",
    ).strip()

    if st.button("Remove Member", key="workspace_remove_member"):
        if not _require_context(workspace_id, actor_user_id):
            return
        if not target_user_id:
            st.error("User ID to Remove is required.")
            return

        try:
            removed = remove_workspace_member(
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
            )
        except PermissionDeniedError as exc:
            st.error(str(exc))
            return
        except ValueError as exc:
            st.error(str(exc))
            return

        if not removed:
            st.info(f"User {target_user_id} is not a member of this workspace.")
            return

        st.success(f"Removed member {target_user_id} from workspace.")
        st.rerun()


def _render_approval_request_form(workspace_id: str, actor_user_id: str) -> None:
    """Render form to create a new approval request."""
    st.subheader("Create Approval Request")

    action_name = st.text_input(
        "Sensitive Action",
        key="workspace_approval_action",
        placeholder="e.g. production_conversion",
        help="Operation requiring reviewer approval.",
    ).strip()
    target_user_id = st.text_input(
        "Target User ID (optional)",
        key="workspace_approval_target_user",
        placeholder="e.g. alice",
    ).strip()
    request_comment = st.text_area(
        "Request Comment",
        key="workspace_approval_request_comment",
        placeholder="Describe why this action needs approval.",
    ).strip()

    if st.button("Submit Approval Request", key="workspace_submit_approval"):
        if not _require_context(workspace_id, actor_user_id):
            return
        if not action_name:
            st.error("Sensitive Action is required.")
            return

        try:
            request_id = create_approval_request(
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                action=action_name,
                request_comment=request_comment,
                target_user_id=target_user_id or None,
                details={"source": "workspace_ui"},
            )
        except PermissionDeniedError as exc:
            st.error(str(exc))
            return

        st.success(f"Approval request #{request_id} created.")
        st.rerun()


def _render_approval_decision_panel(workspace_id: str, actor_user_id: str) -> None:
    """Render approval decision controls for pending requests."""
    st.subheader("Approve or Reject Requests")

    if not _require_context(workspace_id, actor_user_id):
        return

    try:
        pending_requests = list_workspace_approval_requests(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            status="pending",
            limit=100,
        )
    except PermissionDeniedError as exc:
        st.error(str(exc))
        return

    if not pending_requests:
        st.info("No pending approval requests.")
        return

    request_options = {
        f"#{req.id} {req.action} (by {req.requested_by})": req.id
        for req in pending_requests
        if req.id is not None
    }
    selected_label = st.selectbox(
        "Pending Request",
        options=list(request_options.keys()),
        key="workspace_pending_request_select",
    )
    selected_request_id = request_options[selected_label]
    selected_request = next(
        request for request in pending_requests if request.id == selected_request_id
    )

    st.caption(
        "Requested at "
        f"{selected_request.requested_at} by {selected_request.requested_by}"
    )
    if selected_request.request_comment:
        st.markdown(f"**Request comment:** {selected_request.request_comment}")

    decision_choice = st.radio(
        "Decision",
        options=["approved", "rejected"],
        horizontal=True,
        key="workspace_decision_choice",
    )
    decision_comment = st.text_area(
        "Decision Comment",
        key="workspace_decision_comment",
        placeholder="Optional decision rationale.",
    ).strip()

    if st.button("Apply Decision", key="workspace_apply_decision"):
        try:
            decided = decide_approval_request(
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                request_id=selected_request_id,
                decision=decision_choice,
                decision_comment=decision_comment or None,
            )
        except PermissionDeniedError as exc:
            st.error(str(exc))
            return
        except ValueError as exc:
            st.error(str(exc))
            return

        if decided is None:
            st.error("Approval request no longer exists.")
            return
        st.success(f"Request #{selected_request_id} {decided.status}.")
        st.rerun()


def _render_approval_requests_table(workspace_id: str, actor_user_id: str) -> None:
    """Render recent approval requests table."""
    st.subheader("Approval Requests")

    if not _require_context(workspace_id, actor_user_id):
        return

    try:
        requests = list_workspace_approval_requests(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            limit=100,
        )
    except PermissionDeniedError as exc:
        st.error(str(exc))
        return

    if not requests:
        st.info("No approval requests yet.")
        return

    rows = [
        {
            "Request ID": request.id,
            "Action": request.action,
            "Status": request.status,
            "Requested By": request.requested_by,
            "Requested At": request.requested_at,
            "Decided By": request.decided_by or "-",
            "Decided At": request.decided_at or "-",
            "Request Comment": request.request_comment,
            "Decision Comment": request.decision_comment or "-",
        }
        for request in requests
    ]
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

    actor_filter_col, action_filter_col = st.columns(2)
    with actor_filter_col:
        actor_filter = st.text_input(
            "Filter by actor",
            key="workspace_audit_actor_filter",
            placeholder="e.g. alice",
        ).strip()
    with action_filter_col:
        action_filter = st.text_input(
            "Filter by action",
            key="workspace_audit_action_filter",
            placeholder="e.g. approval:request_approved",
        ).strip()

    date_col1, date_col2 = st.columns(2)
    with date_col1:
        date_from = st.date_input(
            "From date",
            key="workspace_audit_date_from",
            value=None,
        )
    with date_col2:
        date_to = st.date_input(
            "To date",
            key="workspace_audit_date_to",
            value=None,
        )

    normalised_date_from = date_from if isinstance(date_from, date) else None
    normalised_date_to = date_to if isinstance(date_to, date) else None

    try:
        events = list_workspace_audit_events(
            workspace_id,
            actor_user_id,
            limit=200,
            actor_filter=actor_filter or None,
            action_filter=action_filter or None,
            date_from=normalised_date_from,
            date_to=normalised_date_to,
        )
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

    _render_approval_request_form(workspace_id, actor_user_id)
    st.divider()

    _render_approval_decision_panel(workspace_id, actor_user_id)
    st.divider()

    _render_approval_requests_table(workspace_id, actor_user_id)
    st.divider()

    _render_remove_member_form(workspace_id, actor_user_id)
    st.divider()

    _render_members_table(workspace_id, actor_user_id)
    st.divider()

    _render_audit_timeline(workspace_id, actor_user_id)
