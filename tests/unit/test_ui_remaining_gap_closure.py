"""Targeted tests to close remaining UI coverage gaps."""

from __future__ import annotations

import builtins
import importlib
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class _SessionState(dict[str, Any]):
    """Dict-backed session state with attribute access."""

    def __getattr__(self, name: str) -> Any:
        return self.get(name)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def test_filtering_handles_search_dir_creation_error() -> None:
    """Search directory creation failures should be logged and ignored."""
    from souschef.ui import filtering

    fake_dir = MagicMock()
    fake_dir.mkdir.side_effect = OSError("nope")

    with (
        patch("souschef.ui.filtering.SEARCHES_DIR", fake_dir),
        patch.object(filtering.LOGGER, "warning") as warning,
    ):
        filtering._ensure_searches_dir()

    warning.assert_called_once()


def test_filtering_loaders_and_early_returns() -> None:
    """Filtering helpers should handle invalid payload types and blank names."""
    from souschef.ui import filtering

    with patch("souschef.ui.filtering._load_json", return_value="not-a-dict"):
        assert filtering._load_saved_searches() == {}

    with (
        patch("souschef.ui.filtering._load_json", return_value={"bad": {"unknown": 1}}),
        patch.object(filtering.LOGGER, "warning") as warning,
    ):
        assert filtering._load_saved_searches() == {}
    warning.assert_called_once()

    with patch("souschef.ui.filtering._load_json", return_value={"bad": "shape"}):
        assert filtering._load_search_history() == []

    with patch("souschef.ui.filtering._save_searches") as save_searches:
        filtering.save_search("   ", filtering.FilterCriteria())
    save_searches.assert_not_called()

    with patch("souschef.ui.filtering._save_search_history") as save_history:
        filtering.record_search(filtering.FilterCriteria())
    save_history.assert_not_called()


def test_filtering_delete_saved_search_and_dialog_guard() -> None:
    """Filter panel should support deleting a saved search and dialog guard branch."""
    from souschef.ui import filtering

    st_mock = MagicMock()
    st_mock.session_state = _SessionState(
        {"current_filter": filtering.FilterCriteria()}
    )
    st_mock.sidebar.multiselect.side_effect = [[], [], [], []]
    st_mock.sidebar.radio.return_value = "All"
    st_mock.sidebar.text_input.side_effect = ["", ""]
    st_mock.sidebar.selectbox.return_value = "saved-one"
    st_mock.sidebar.button.side_effect = [False, True]

    with (
        patch("souschef.ui.filtering.st", st_mock),
        patch("souschef.ui.filtering.list_saved_searches", return_value=["saved-one"]),
        patch("souschef.ui.filtering.get_search", return_value=None),
        patch("souschef.ui.filtering.delete_search") as delete_search,
    ):
        filtering.show_filter_panel()

    delete_search.assert_called_once_with("saved-one")
    assert st_mock.session_state.load_saved_search == ""
    st_mock.rerun.assert_called()

    st_dialog = MagicMock()
    st_dialog.session_state = _SessionState({})
    with (
        patch("souschef.ui.filtering.st", st_dialog),
        patch("souschef.ui.filtering.st.form") as form,
    ):
        filtering.show_save_search_dialog()
    form.assert_not_called()


def test_command_palette_remaining_branches() -> None:
    """Command palette should handle empty command list and invalid selection."""
    from souschef.ui.command_palette import (
        CommandDefinition,
        register_shortcut,
        render_command_palette,
    )

    with patch("souschef.ui.command_palette.fuzzy_find_commands", return_value=[]):
        assert render_command_palette(MagicMock(), []) is None

    with patch("souschef.ui.command_palette.fuzzy_find_commands", return_value=[]):
        streamlit_module = MagicMock()
        streamlit_module.sidebar = MagicMock()
        streamlit_module.session_state = _SessionState({})
        assert render_command_palette(streamlit_module, []) is None

    with patch("souschef.ui.command_palette.fuzzy_find_commands") as fuzzy:
        cmd = CommandDefinition("c1", "Open Dashboard", "Dashboard", "g d")
        fuzzy.return_value = [cmd]

        streamlit_module = MagicMock()
        streamlit_module.sidebar = MagicMock()
        streamlit_module.session_state = _SessionState({"recent_commands": ["c0"]})
        streamlit_module.sidebar.text_input.return_value = "open"
        streamlit_module.sidebar.selectbox.return_value = "Not a valid label"

        assert render_command_palette(streamlit_module, [cmd]) is None

    with patch("souschef.ui.command_palette.fuzzy_find_commands") as fuzzy:
        cmd = CommandDefinition("c1", "Open Dashboard", "Dashboard", "g d")
        fuzzy.return_value = [cmd]

        streamlit_module = MagicMock()
        streamlit_module.sidebar = MagicMock()
        streamlit_module.session_state = _SessionState({"recent_commands": ["c0"]})
        streamlit_module.sidebar.text_input.return_value = "open"
        streamlit_module.sidebar.selectbox.return_value = "Open Dashboard (g d)"
        streamlit_module.sidebar.button.return_value = False

        assert render_command_palette(streamlit_module, [cmd]) is None
        streamlit_module.sidebar.caption.assert_called()

    try:
        register_shortcut({}, "   ", "c1")
    except ValueError as exc:
        assert "must not be empty" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for empty shortcut")


def test_workspace_management_import_fallback_and_invite_context_guard() -> None:
    """Workspace management should tolerate missing streamlit import and guard context."""
    import souschef.ui.pages.workspace_management as workspace_management

    original_import = builtins.__import__

    def _fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "streamlit":
            raise ImportError("streamlit unavailable")
        return original_import(name, *args, **kwargs)

    try:
        with patch("builtins.__import__", side_effect=_fake_import):
            reloaded = importlib.reload(workspace_management)
            assert reloaded.st is None
    finally:
        importlib.reload(workspace_management)

    st_mock = MagicMock()
    col1 = MagicMock()
    col2 = MagicMock()
    col1.__enter__.return_value = col1
    col1.__exit__.return_value = False
    col2.__enter__.return_value = col2
    col2.__exit__.return_value = False
    st_mock.columns.return_value = (col1, col2)
    st_mock.text_input.return_value = "alice"
    st_mock.selectbox.return_value = "Owner"
    st_mock.button.return_value = True

    with (
        patch("souschef.ui.pages.workspace_management.st", st_mock),
        patch(
            "souschef.ui.pages.workspace_management._require_context",
            return_value=False,
        ),
        patch("souschef.ui.pages.workspace_management.set_workspace_role") as set_role,
    ):
        workspace_management._render_member_invite_form("", "")

    set_role.assert_not_called()


def test_analytics_medium_complexity_branches() -> None:
    """Analytics helpers should cover medium complexity paths."""
    from souschef.ui.pages.analytics_dashboard import (
        _manual_steps_for_complexity,
        _risk_distribution_for_complexity,
    )

    assert _risk_distribution_for_complexity("medium") == {
        "low": 2,
        "medium": 3,
        "high": 1,
    }
    assert _manual_steps_for_complexity("medium") == 2


def test_recommendations_and_theme_remaining_branches() -> None:
    """Recommendation and theme helper functions should cover fallback branches."""
    from souschef.ui import recommendations
    from souschef.ui.theme import resolve_theme_mode

    groups = recommendations.suggest_migrate_together_groups(
        {
            "a": ["b", "c"],
            "b": ["a", "c"],
            "c": ["a"],
        }
    )
    assert groups

    with patch("souschef.ui.recommendations.st") as st_mock:
        recommendations._render_recommendation_flags([])
    st_mock.subheader.assert_not_called()

    assert resolve_theme_mode("unexpected") == "light"


def test_app_main_routes_on_command_palette_action() -> None:
    """Main app loop should route immediately when command palette returns action."""
    from souschef.ui import app

    class _FakeSt:
        def __init__(self) -> None:
            self.session_state = _SessionState({"current_page": "Dashboard"})

        def set_page_config(self, **_kwargs: Any) -> None:
            return None

        def title(self, _value: str) -> None:
            return None

        def markdown(self, _value: str) -> None:
            return None

        def divider(self) -> None:
            return None

        def rerun(self) -> None:
            raise StopIteration

    fake_st = _FakeSt()

    with (
        patch.object(app, "st", fake_st),
        patch.object(app, "apply_theme_styles"),
        patch.object(app, "show_theme_selector"),
        patch.object(app, "render_accessibility_landmarks"),
        patch.object(app, "_render_ticket_sync_status"),
        patch.object(app, "_run_command_palette", return_value="History"),
        patch.object(app, "_display_navigation_section"),
        patch.object(app, "_route_to_page"),
        pytest.raises(StopIteration),
    ):
        app.main()

    assert fake_st.session_state.current_page == "History"
