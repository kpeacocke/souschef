"""Unit tests for integration notifications UI page."""

from __future__ import annotations

from unittest.mock import patch


class SessionState(dict):
    """Session state helper with attribute access."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value


@patch("souschef.ui.pages.integration_notifications.st")
def test_notifications_page_saves_valid_config(mock_st) -> None:
    """Page should persist valid provider/webhook configuration."""
    from souschef.ui.pages.integration_notifications import (
        show_integration_notifications_page,
    )

    mock_st.session_state = SessionState()
    mock_st.selectbox.return_value = "Slack"
    mock_st.text_input.side_effect = [
        "https://hooks.slack.com/services/a/b/c",
        "#migrations",
    ]
    mock_st.button.return_value = True

    show_integration_notifications_page()

    assert mock_st.session_state.notification_config["provider"] == "slack"
    mock_st.success.assert_called_once()


@patch("souschef.ui.pages.integration_notifications.st")
def test_notifications_page_shows_error_on_invalid_config(mock_st) -> None:
    """Page should show validation error for invalid webhook config."""
    from souschef.ui.pages.integration_notifications import (
        show_integration_notifications_page,
    )

    mock_st.session_state = SessionState()
    mock_st.selectbox.return_value = "Teams"
    mock_st.text_input.side_effect = [
        "https://hooks.slack.com/services/a/b/c",
        "ops",
    ]
    mock_st.button.return_value = True

    show_integration_notifications_page()

    mock_st.error.assert_called_once()
