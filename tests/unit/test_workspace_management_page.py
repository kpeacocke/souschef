"""Tests for workspace management UI page."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

from souschef.auth import PermissionDeniedError


class SessionState(dict):
    """Session state helper with attribute access."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value


def _ctx() -> MagicMock:
    """Return a generic context manager mock."""
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=ctx)
    ctx.__exit__ = Mock(return_value=None)
    return ctx


@patch("souschef.ui.pages.workspace_management.st")
def test_show_workspace_management_page_happy_path(mock_st) -> None:
    """Page should render members and audit timeline for valid context."""
    from souschef.ui.pages.workspace_management import show_workspace_management_page

    mock_st.session_state = SessionState()
    mock_st.columns.side_effect = [
        [_ctx(), _ctx()],
        [_ctx(), _ctx()],
        [_ctx(), _ctx()],
        [_ctx(), _ctx()],
        [_ctx(), _ctx()],
    ]
    mock_st.text_input.side_effect = [
        "ws-a",
        "owner-user",
        "editor-user",
        "production_conversion",
        "",
        "",
        "",
        "",
        "",
    ]
    mock_st.text_area.side_effect = ["", ""]
    mock_st.date_input.side_effect = [None, None]
    mock_st.selectbox.return_value = "Editor"
    mock_st.button.side_effect = [False, False, True, False, False]

    member = MagicMock()
    member.user_id = "editor-user"
    member.role = "editor"
    member.updated_by = "owner-user"
    member.updated_at = "2026-05-16T08:00:00Z"

    event = MagicMock()
    event.created_at = "2026-05-16T08:00:01Z"
    event.event_type = "workspace_rbac"
    event.action = "role_change"
    event.user_id = "owner-user"
    event.target_user_id = "editor-user"
    event.details = '{"new_role":"editor"}'

    with (
        patch(
            "souschef.ui.pages.workspace_management.set_workspace_role"
        ) as set_role_mock,
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_members",
            return_value=[member],
        ),
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_audit_events",
            return_value=[event],
        ),
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_approval_requests",
            return_value=[],
        ),
        patch(
            "souschef.ui.pages.workspace_management.remove_workspace_member",
            return_value=False,
        ),
        patch(
            "souschef.ui.pages.workspace_management.bootstrap_workspace_owner",
            return_value=False,
        ),
    ):
        show_workspace_management_page()

    set_role_mock.assert_called_once_with(
        workspace_id="ws-a",
        actor_user_id="owner-user",
        target_user_id="editor-user",
        role="Editor",
    )
    assert mock_st.dataframe.call_count >= 2


@patch("souschef.ui.pages.workspace_management.st")
def test_show_workspace_management_page_validation_error(mock_st) -> None:
    """Invite action should show validation error when user ID is missing."""
    from souschef.ui.pages.workspace_management import show_workspace_management_page

    mock_st.session_state = SessionState()
    mock_st.columns.side_effect = [
        [_ctx(), _ctx()],
        [_ctx(), _ctx()],
        [_ctx(), _ctx()],
        [_ctx(), _ctx()],
        [_ctx(), _ctx()],
    ]
    mock_st.text_input.side_effect = [
        "ws-a",
        "owner-user",
        "",
        "production_conversion",
        "",
        "",
        "",
        "",
        "",
    ]
    mock_st.text_area.side_effect = ["", ""]
    mock_st.date_input.side_effect = [None, None]
    mock_st.selectbox.return_value = "Viewer"
    mock_st.button.side_effect = [False, False, True, False, False]

    with (
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_members",
            return_value=[],
        ),
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_audit_events",
            return_value=[],
        ),
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_approval_requests",
            return_value=[],
        ),
        patch(
            "souschef.ui.pages.workspace_management.remove_workspace_member",
            return_value=False,
        ),
        patch(
            "souschef.ui.pages.workspace_management.bootstrap_workspace_owner",
            return_value=False,
        ),
    ):
        show_workspace_management_page()

    mock_st.error.assert_called_with("User ID is required.")


@patch("souschef.ui.pages.workspace_management.st")
def test_show_workspace_management_page_remove_member(mock_st) -> None:
    """Remove member action should call API and show success."""
    from souschef.ui.pages.workspace_management import show_workspace_management_page

    mock_st.session_state = SessionState()
    mock_st.columns.side_effect = [
        [_ctx(), _ctx()],
        [_ctx(), _ctx()],
        [_ctx(), _ctx()],
        [_ctx(), _ctx()],
        [_ctx(), _ctx()],
    ]
    mock_st.text_input.side_effect = [
        "ws-a",
        "owner-user",
        "",
        "production_conversion",
        "",
        "editor-user",
        "",
        "",
    ]
    mock_st.text_area.side_effect = ["", ""]
    mock_st.date_input.side_effect = [None, None]
    mock_st.selectbox.return_value = "Viewer"
    mock_st.button.side_effect = [False, False, False, False, True]

    with (
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_members",
            return_value=[],
        ),
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_audit_events",
            return_value=[],
        ),
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_approval_requests",
            return_value=[],
        ),
        patch(
            "souschef.ui.pages.workspace_management.remove_workspace_member",
            return_value=True,
        ) as remove_member_mock,
        patch(
            "souschef.ui.pages.workspace_management.bootstrap_workspace_owner",
            return_value=False,
        ),
    ):
        show_workspace_management_page()

    remove_member_mock.assert_called_once_with(
        workspace_id="ws-a",
        actor_user_id="owner-user",
        target_user_id="editor-user",
    )
    mock_st.success.assert_any_call("Removed member editor-user from workspace.")


@patch("souschef.ui.pages.workspace_management.st")
def test_require_context_reports_missing_fields(mock_st) -> None:
    """Context validation should report both missing required fields."""
    from souschef.ui.pages.workspace_management import _require_context

    valid = _require_context("", "")

    assert valid is False
    mock_st.error.assert_called_once_with(
        "Missing required fields: Workspace ID, Your User ID"
    )


@patch("souschef.ui.pages.workspace_management.st")
def test_render_bootstrap_actions_skips_and_informs(mock_st) -> None:
    """Bootstrap action should no-op on invalid context and inform on existing members."""
    from souschef.ui.pages.workspace_management import _render_bootstrap_actions

    mock_st.button.side_effect = [True, True]

    with (
        patch(
            "souschef.ui.pages.workspace_management._require_context",
            side_effect=[False, True],
        ),
        patch(
            "souschef.ui.pages.workspace_management.bootstrap_workspace_owner",
            return_value=False,
        ) as bootstrap_mock,
    ):
        _render_bootstrap_actions("ws-a", "owner-user")
        _render_bootstrap_actions("ws-a", "owner-user")

    bootstrap_mock.assert_called_once_with("ws-a", "owner-user")
    mock_st.info.assert_called_with("Workspace already has members. Bootstrap skipped.")


@patch("souschef.ui.pages.workspace_management.st")
def test_render_member_invite_form_handles_permission_and_value_errors(mock_st) -> None:
    """Invite form should surface both permission and value errors."""
    from souschef.ui.pages.workspace_management import _render_member_invite_form

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.text_input.return_value = "editor-user"
    mock_st.selectbox.return_value = "Editor"
    mock_st.button.return_value = True

    with (
        patch(
            "souschef.ui.pages.workspace_management._require_context", return_value=True
        ),
        patch(
            "souschef.ui.pages.workspace_management.set_workspace_role",
            side_effect=PermissionDeniedError("no access"),
        ),
    ):
        _render_member_invite_form("ws-a", "owner-user")

    with (
        patch(
            "souschef.ui.pages.workspace_management._require_context", return_value=True
        ),
        patch(
            "souschef.ui.pages.workspace_management.set_workspace_role",
            side_effect=ValueError("invalid role"),
        ),
    ):
        _render_member_invite_form("ws-a", "owner-user")

    assert mock_st.error.call_count >= 2


@patch("souschef.ui.pages.workspace_management.st")
def test_render_remove_member_form_handles_empty_and_absent_member(mock_st) -> None:
    """Remove member form should validate required user ID and handle missing members."""
    from souschef.ui.pages.workspace_management import _render_remove_member_form

    mock_st.button.return_value = True
    mock_st.text_input.side_effect = ["", "ghost-user"]

    with patch(
        "souschef.ui.pages.workspace_management._require_context", return_value=True
    ):
        _render_remove_member_form("ws-a", "owner-user")

    with (
        patch(
            "souschef.ui.pages.workspace_management._require_context", return_value=True
        ),
        patch(
            "souschef.ui.pages.workspace_management.remove_workspace_member",
            return_value=False,
        ),
    ):
        _render_remove_member_form("ws-a", "owner-user")

    mock_st.error.assert_any_call("User ID to Remove is required.")
    mock_st.info.assert_any_call("User ghost-user is not a member of this workspace.")


@patch("souschef.ui.pages.workspace_management.st")
def test_render_approval_request_form_requires_action(mock_st) -> None:
    """Approval request form should require a non-empty action name."""
    from souschef.ui.pages.workspace_management import _render_approval_request_form

    mock_st.text_input.side_effect = ["", ""]
    mock_st.text_area.return_value = "needs approval"
    mock_st.button.return_value = True

    with patch(
        "souschef.ui.pages.workspace_management._require_context", return_value=True
    ):
        _render_approval_request_form("ws-a", "owner-user")

    mock_st.error.assert_called_with("Sensitive Action is required.")


@patch("souschef.ui.pages.workspace_management.st")
def test_render_approval_decision_panel_handles_no_pending_and_missing_request(
    mock_st,
) -> None:
    """Decision panel should handle no pending requests and disappeared requests."""
    from souschef.ui.pages.workspace_management import _render_approval_decision_panel

    request = MagicMock()
    request.id = 7
    request.action = "production_conversion"
    request.requested_by = "editor-user"
    request.requested_at = "2026-05-19T10:00:00Z"
    request.request_comment = "approve please"

    mock_st.button.return_value = True
    mock_st.selectbox.return_value = "#7 production_conversion (by editor-user)"
    mock_st.radio.return_value = "approved"
    mock_st.text_area.return_value = ""

    with (
        patch(
            "souschef.ui.pages.workspace_management._require_context", return_value=True
        ),
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_approval_requests",
            side_effect=[[], [request]],
        ),
        patch(
            "souschef.ui.pages.workspace_management.decide_approval_request",
            return_value=None,
        ),
    ):
        _render_approval_decision_panel("ws-a", "owner-user")
        _render_approval_decision_panel("ws-a", "owner-user")

    mock_st.info.assert_any_call("No pending approval requests.")
    mock_st.error.assert_any_call("Approval request no longer exists.")


@patch("souschef.ui.pages.workspace_management.st")
def test_render_approval_requests_table_and_event_details_formatting(mock_st) -> None:
    """Approval request table should render rows and event details parser should fallback safely."""
    from souschef.ui.pages.workspace_management import (
        _format_event_details,
        _render_approval_requests_table,
    )

    request = MagicMock()
    request.id = 12
    request.action = "production_conversion"
    request.status = "pending"
    request.requested_by = "editor-user"
    request.requested_at = "2026-05-19T10:00:00Z"
    request.decided_by = None
    request.decided_at = None
    request.request_comment = "please approve"
    request.decision_comment = None

    with (
        patch(
            "souschef.ui.pages.workspace_management._require_context", return_value=True
        ),
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_approval_requests",
            return_value=[request],
        ),
    ):
        _render_approval_requests_table("ws-a", "owner-user")

    mock_st.dataframe.assert_called_once()
    assert _format_event_details("not-json") == "-"


@patch("souschef.ui.pages.workspace_management.st")
def test_render_page_header_back_button_navigates(mock_st) -> None:
    """Header back button should navigate to dashboard and rerun."""
    from souschef.ui.pages.workspace_management import _render_page_header

    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.button.return_value = True
    mock_st.session_state = SessionState()

    _render_page_header()

    assert mock_st.session_state.current_page == "Dashboard"
    mock_st.rerun.assert_called_once()


@patch("souschef.ui.pages.workspace_management.st")
def test_render_bootstrap_actions_success_path(mock_st) -> None:
    """Bootstrap action should show success when owner assignment is created."""
    from souschef.ui.pages.workspace_management import _render_bootstrap_actions

    mock_st.button.return_value = True
    with (
        patch(
            "souschef.ui.pages.workspace_management._require_context", return_value=True
        ),
        patch(
            "souschef.ui.pages.workspace_management.bootstrap_workspace_owner",
            return_value=True,
        ),
    ):
        _render_bootstrap_actions("ws-a", "owner-user")

    mock_st.success.assert_called_with("Workspace owner bootstrap complete.")


@patch("souschef.ui.pages.workspace_management.st")
def test_render_members_table_handles_context_and_permission_errors(mock_st) -> None:
    """Members table should return early on missing context and report permission errors."""
    from souschef.ui.pages.workspace_management import _render_members_table

    with (
        patch(
            "souschef.ui.pages.workspace_management._require_context",
            side_effect=[False, True],
        ),
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_members",
            side_effect=PermissionDeniedError("no access"),
        ),
    ):
        _render_members_table("ws-a", "owner-user")
        _render_members_table("ws-a", "owner-user")

    mock_st.error.assert_called_with("no access")


@patch("souschef.ui.pages.workspace_management.st")
def test_render_remove_member_form_handles_context_and_exceptions(mock_st) -> None:
    """Remove member form should surface permission and value errors."""
    from souschef.ui.pages.workspace_management import _render_remove_member_form

    mock_st.button.return_value = True
    mock_st.text_input.side_effect = ["editor-user", "editor-user", "editor-user"]

    with (
        patch(
            "souschef.ui.pages.workspace_management._require_context",
            side_effect=[False, True, True],
        ),
        patch(
            "souschef.ui.pages.workspace_management.remove_workspace_member",
            side_effect=[
                PermissionDeniedError("no access"),
                ValueError("cannot remove"),
            ],
        ),
    ):
        _render_remove_member_form("ws-a", "owner-user")
        _render_remove_member_form("ws-a", "owner-user")
        _render_remove_member_form("ws-a", "owner-user")

    mock_st.error.assert_any_call("no access")
    mock_st.error.assert_any_call("cannot remove")


@patch("souschef.ui.pages.workspace_management.st")
def test_render_approval_request_form_handles_context_permission_and_success(
    mock_st,
) -> None:
    """Approval request form should handle context failures, permission errors, and success."""
    from souschef.ui.pages.workspace_management import _render_approval_request_form

    mock_st.button.return_value = True
    mock_st.text_input.side_effect = [
        "production_conversion",
        "editor-user",
        "production_conversion",
        "editor-user",
        "production_conversion",
        "editor-user",
    ]
    mock_st.text_area.return_value = "review this"

    with (
        patch(
            "souschef.ui.pages.workspace_management._require_context",
            side_effect=[False, True, True],
        ),
        patch(
            "souschef.ui.pages.workspace_management.create_approval_request",
            side_effect=[PermissionDeniedError("no access"), 42],
        ),
    ):
        _render_approval_request_form("ws-a", "owner-user")
        _render_approval_request_form("ws-a", "owner-user")
        _render_approval_request_form("ws-a", "owner-user")

    mock_st.error.assert_any_call("no access")
    mock_st.success.assert_any_call("Approval request #42 created.")
    assert mock_st.rerun.call_count >= 1


@patch("souschef.ui.pages.workspace_management.st")
def test_render_approval_decision_panel_handles_context_permission_exceptions_and_success(
    mock_st,
) -> None:
    """Decision panel should handle context, permission, errors, and success paths."""
    from souschef.ui.pages.workspace_management import _render_approval_decision_panel

    request = MagicMock()
    request.id = 7
    request.action = "production_conversion"
    request.requested_by = "editor-user"
    request.requested_at = "2026-05-19T10:00:00Z"
    request.request_comment = "approve please"
    request.status = "approved"

    mock_st.button.return_value = True
    mock_st.selectbox.return_value = "#7 production_conversion (by editor-user)"
    mock_st.radio.return_value = "approved"
    mock_st.text_area.return_value = "looks good"

    with (
        patch(
            "souschef.ui.pages.workspace_management._require_context",
            side_effect=[False, True, True, True, True],
        ),
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_approval_requests",
            side_effect=[
                PermissionDeniedError("no access"),
                [request],
                [request],
                [request],
            ],
        ),
        patch(
            "souschef.ui.pages.workspace_management.decide_approval_request",
            side_effect=[
                PermissionDeniedError("cannot decide"),
                ValueError("bad request"),
                request,
            ],
        ),
    ):
        _render_approval_decision_panel("ws-a", "owner-user")
        _render_approval_decision_panel("ws-a", "owner-user")
        _render_approval_decision_panel("ws-a", "owner-user")
        _render_approval_decision_panel("ws-a", "owner-user")
        _render_approval_decision_panel("ws-a", "owner-user")

    mock_st.error.assert_any_call("no access")
    mock_st.error.assert_any_call("cannot decide")
    mock_st.error.assert_any_call("bad request")
    mock_st.success.assert_any_call("Request #7 approved.")


@patch("souschef.ui.pages.workspace_management.st")
def test_render_approval_requests_table_handles_context_and_permission(mock_st) -> None:
    """Approval requests table should return on context issues and permission errors."""
    from souschef.ui.pages.workspace_management import _render_approval_requests_table

    with (
        patch(
            "souschef.ui.pages.workspace_management._require_context",
            side_effect=[False, True],
        ),
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_approval_requests",
            side_effect=PermissionDeniedError("no access"),
        ),
    ):
        _render_approval_requests_table("ws-a", "owner-user")
        _render_approval_requests_table("ws-a", "owner-user")

    mock_st.error.assert_called_with("no access")


@patch("souschef.ui.pages.workspace_management.st")
def test_render_audit_timeline_handles_context_and_permission(mock_st) -> None:
    """Audit timeline should return on context issues and show permission errors."""
    from souschef.ui.pages.workspace_management import _render_audit_timeline

    mock_st.columns.side_effect = [[_ctx(), _ctx()], [_ctx(), _ctx()]]
    mock_st.text_input.side_effect = ["", ""]
    mock_st.date_input.side_effect = [None, None]

    with (
        patch(
            "souschef.ui.pages.workspace_management._require_context",
            side_effect=[False, True],
        ),
        patch(
            "souschef.ui.pages.workspace_management.list_workspace_audit_events",
            side_effect=PermissionDeniedError("no access"),
        ),
    ):
        _render_audit_timeline("ws-a", "owner-user")
        _render_audit_timeline("ws-a", "owner-user")

    mock_st.error.assert_called_with("no access")
