"""Tests for workspace management UI page."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch


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
