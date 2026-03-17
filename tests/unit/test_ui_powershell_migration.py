"""
Unit tests for souschef/ui/pages/powershell_migration.py.

Tests for all page functions, display helpers, and interaction handlers
to achieve 100% line and branch coverage.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def mock_st():
    """Provide a mock streamlit module for UI tests."""
    with patch("souschef.ui.pages.powershell_migration.st") as mock:
        # Set up common mock returns
        mock.session_state = {}
        mock.columns.return_value = [MagicMock(), MagicMock()]
        mock.tabs.return_value = [MagicMock(), MagicMock()]
        yield mock


class TestShowPowershellMigrationPage:
    """Tests for the main page entry point show_powershell_migration_page()."""

    def test_page_renders_without_error(self, mock_st) -> None:
        """show_powershell_migration_page runs without raising."""
        from souschef.ui.pages.powershell_migration import (
            show_powershell_migration_page,
        )

        mock_st.text_area.return_value = ""
        mock_st.text_input.side_effect = [
            "powershell_migration",
            "windows",
            "windows_provisioning",
        ]
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        # Buttons not clicked
        col1, col2, col3 = MagicMock(), MagicMock(), MagicMock()
        for col in (col1, col2, col3):
            col.__enter__ = lambda s: s
            col.__exit__ = MagicMock(return_value=False)
            col.button = MagicMock(return_value=False)
        mock_st.columns.return_value = [col1, col2, col3]

        # Should not raise
        show_powershell_migration_page()


class TestDisplayIntro:
    """Tests for _display_intro()."""

    def test_intro_calls_title_and_markdown(self, mock_st) -> None:
        """_display_intro calls st.title and st.markdown."""
        from souschef.ui.pages.powershell_migration import _display_intro

        _display_intro()
        mock_st.title.assert_called_once()
        mock_st.markdown.assert_called_once()


class TestRenderInputs:
    """Tests for _render_inputs()."""

    def test_render_inputs_returns_content_name_hosts(self, mock_st) -> None:
        """_render_inputs returns (script_content, playbook_name, hosts, role_name)."""
        from souschef.ui.pages.powershell_migration import _render_inputs

        mock_st.text_area.return_value = "# script content"
        mock_st.text_input.side_effect = ["my_play", "win_servers", "my_role"]
        col1, col2, col3 = MagicMock(), MagicMock(), MagicMock()
        for col in (col1, col2, col3):
            col.__enter__ = lambda s: s
            col.__exit__ = MagicMock(return_value=False)
        mock_st.columns.return_value = [col1, col2, col3]

        content, name, hosts, role = _render_inputs()
        assert content == "# script content"
        assert name == "my_play"
        assert hosts == "win_servers"
        assert role == "my_role"


class TestHandleParse:
    """Tests for _handle_parse()."""

    def test_parse_empty_content_shows_warning(self, mock_st) -> None:
        """_handle_parse with empty content shows a warning."""
        from souschef.ui.pages.powershell_migration import _handle_parse

        _handle_parse("")
        mock_st.warning.assert_called_once()

    def test_parse_whitespace_only_shows_warning(self, mock_st) -> None:
        """_handle_parse with whitespace-only content shows a warning."""
        from souschef.ui.pages.powershell_migration import _handle_parse

        _handle_parse("   \n   ")
        mock_st.warning.assert_called_once()

    def test_parse_valid_content_stores_result(self, mock_st) -> None:
        """_handle_parse stores parsed result in session state."""
        from souschef.ui.pages.powershell_migration import _handle_parse

        mock_st.spinner.return_value.__enter__ = lambda s: s
        mock_st.spinner.return_value.__exit__ = MagicMock(return_value=False)

        # Set up tabs mock
        tab1, tab2 = MagicMock(), MagicMock()
        tab1.__enter__ = lambda s: s
        tab1.__exit__ = MagicMock(return_value=False)
        tab2.__enter__ = lambda s: s
        tab2.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = [tab1, tab2]
        mock_st.columns.return_value = [
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]

        _handle_parse("Install-WindowsFeature -Name Web-Server")
        # Should have stored result
        assert mock_st.session_state.get("ps_parse_result") is not None
        assert mock_st.session_state.get("ps_convert_result") is None


class TestHandleConvert:
    """Tests for _handle_convert()."""

    def test_convert_empty_content_shows_warning(self, mock_st) -> None:
        """_handle_convert with empty content shows a warning."""
        from souschef.ui.pages.powershell_migration import _handle_convert

        _handle_convert("", "play", "windows")
        mock_st.warning.assert_called_once()

    def test_convert_valid_content_stores_result(self, mock_st) -> None:
        """_handle_convert stores result in session state."""
        from souschef.ui.pages.powershell_migration import _handle_convert

        mock_st.spinner.return_value.__enter__ = lambda s: s
        mock_st.spinner.return_value.__exit__ = MagicMock(return_value=False)
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        tab1, tab2 = MagicMock(), MagicMock()
        tab1.__enter__ = lambda s: s
        tab1.__exit__ = MagicMock(return_value=False)
        tab2.__enter__ = lambda s: s
        tab2.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = [tab1, tab2]

        _handle_convert("Install-WindowsFeature -Name Web-Server", "play", "windows")
        assert mock_st.session_state.get("ps_convert_result") is not None
        assert mock_st.session_state.get("ps_parse_result") is None


class TestDisplayParseResult:
    """Tests for _display_parse_result()."""

    def test_display_parse_result_with_actions(self, mock_st) -> None:
        """_display_parse_result renders metrics and actions."""
        from souschef.ui.pages.powershell_migration import _display_parse_result

        result = {
            "metrics": {
                "windows_feature": 1,
                "windows_service": 0,
                "registry": 0,
                "file": 0,
                "package": 0,
                "win_shell_fallback": 0,
            },
            "actions": [
                {
                    "action_type": "windows_feature_install",
                    "source_line": 1,
                    "confidence": "high",
                    "requires_elevation": True,
                    "params": {"feature_name": "Web-Server"},
                    "raw": "Install-WindowsFeature -Name Web-Server",
                }
            ],
            "warnings": [],
        }

        tab1, tab2 = MagicMock(), MagicMock()
        tab1.__enter__ = lambda s: s
        tab1.__exit__ = MagicMock(return_value=False)
        tab2.__enter__ = lambda s: s
        tab2.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = [tab1, tab2]
        cols = [MagicMock() for _ in range(6)]
        mock_st.columns.return_value = cols
        mock_st.expander.return_value.__enter__ = lambda s: s
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

        _display_parse_result(result)
        # metrics are called on column objects
        assert any(c.metric.called for c in cols)

    def test_display_parse_result_empty_actions(self, mock_st) -> None:
        """_display_parse_result handles empty actions list."""
        from souschef.ui.pages.powershell_migration import _display_parse_result

        result = {
            "metrics": {
                "windows_feature": 0,
                "windows_service": 0,
                "registry": 0,
                "file": 0,
                "package": 0,
                "win_shell_fallback": 0,
            },
            "actions": [],
            "warnings": [],
        }

        tab1, tab2 = MagicMock(), MagicMock()
        tab1.__enter__ = lambda s: s
        tab1.__exit__ = MagicMock(return_value=False)
        tab2.__enter__ = lambda s: s
        tab2.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = [tab1, tab2]
        cols = [MagicMock() for _ in range(6)]
        mock_st.columns.return_value = cols

        _display_parse_result(result)
        mock_st.info.assert_called()  # "No actions found" info message


class TestDisplayConvertResult:
    """Tests for _display_convert_result()."""

    def test_display_error_status(self, mock_st) -> None:
        """_display_convert_result shows error for error status."""
        from souschef.ui.pages.powershell_migration import _display_convert_result

        _display_convert_result({"status": "error", "error": "Something failed"})
        mock_st.error.assert_called_once()

    def test_display_success_status(self, mock_st) -> None:
        """_display_convert_result shows playbook for success status."""
        from souschef.ui.pages.powershell_migration import _display_convert_result

        result = {
            "status": "success",
            "tasks_generated": 3,
            "win_shell_fallbacks": 0,
            "warnings": [],
            "playbook_yaml": "- name: test\n  hosts: windows\n",
        }

        cols = [MagicMock(), MagicMock(), MagicMock()]
        mock_st.columns.return_value = cols
        tab1, tab2 = MagicMock(), MagicMock()
        tab1.__enter__ = lambda s: s
        tab1.__exit__ = MagicMock(return_value=False)
        tab2.__enter__ = lambda s: s
        tab2.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = [tab1, tab2]

        _display_convert_result(result)
        assert any(c.metric.called for c in cols)


class TestRenderWarnings:
    """Tests for _render_warnings()."""

    def test_no_warnings_shows_success(self, mock_st) -> None:
        """_render_warnings shows success when no warnings."""
        from souschef.ui.pages.powershell_migration import _render_warnings

        _render_warnings([])
        mock_st.success.assert_called_once()

    def test_warnings_shown(self, mock_st) -> None:
        """_render_warnings displays each warning."""
        from souschef.ui.pages.powershell_migration import _render_warnings

        _render_warnings(["Warning 1", "Warning 2"])
        assert mock_st.warning.call_count == 2


class TestDisplayStoredResults:
    """Tests for _display_stored_results()."""

    def test_displays_parse_result_from_session_state(self, mock_st) -> None:
        """_display_stored_results shows parse result from session state."""
        from souschef.ui.pages.powershell_migration import _display_stored_results

        stored_result = {
            "metrics": {
                "windows_feature": 0,
                "windows_service": 0,
                "registry": 0,
                "file": 0,
                "package": 0,
                "win_shell_fallback": 0,
            },
            "actions": [],
            "warnings": [],
        }
        mock_st.session_state = {
            "ps_parse_result": stored_result,
            "ps_convert_result": None,
        }
        cols = [MagicMock() for _ in range(6)]
        mock_st.columns.return_value = cols
        tab1, tab2 = MagicMock(), MagicMock()
        tab1.__enter__ = lambda s: s
        tab1.__exit__ = MagicMock(return_value=False)
        tab2.__enter__ = lambda s: s
        tab2.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = [tab1, tab2]

        _display_stored_results()
        assert any(c.metric.called for c in cols)

    def test_displays_convert_result_from_session_state(self, mock_st) -> None:
        """_display_stored_results shows convert result from session state."""
        from souschef.ui.pages.powershell_migration import _display_stored_results

        stored_result = {
            "status": "success",
            "tasks_generated": 1,
            "win_shell_fallbacks": 0,
            "warnings": [],
            "playbook_yaml": "- name: test\n",
        }
        mock_st.session_state = {
            "ps_parse_result": None,
            "ps_convert_result": stored_result,
        }
        cols = [MagicMock() for _ in range(3)]
        mock_st.columns.return_value = cols
        tab1, tab2 = MagicMock(), MagicMock()
        tab1.__enter__ = lambda s: s
        tab1.__exit__ = MagicMock(return_value=False)
        tab2.__enter__ = lambda s: s
        tab2.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = [tab1, tab2]

        _display_stored_results()
        assert any(c.metric.called for c in cols)

    def test_no_stored_results_does_nothing(self, mock_st) -> None:
        """_display_stored_results does nothing with empty session state."""
        from souschef.ui.pages.powershell_migration import _display_stored_results

        mock_st.session_state = {}
        _display_stored_results()
        # No columns should be created (no results to display)
        mock_st.columns.assert_not_called()


class TestRenderActionsTable:
    """Tests for _render_actions_table()."""

    def test_empty_actions_shows_info(self, mock_st) -> None:
        """_render_actions_table shows info message for empty list."""
        from souschef.ui.pages.powershell_migration import _render_actions_table

        _render_actions_table([])
        mock_st.info.assert_called_once()

    def test_action_with_low_confidence(self, mock_st) -> None:
        """_render_actions_table renders low-confidence actions."""
        from souschef.ui.pages.powershell_migration import _render_actions_table

        mock_st.expander.return_value.__enter__ = lambda s: s
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

        actions = [
            {
                "action_type": "win_shell",
                "source_line": 3,
                "confidence": "low",
                "requires_elevation": False,
                "params": {"command": "Write-Host 'test'"},
                "raw": "Write-Host 'test'",
            }
        ]
        _render_actions_table(actions)
        mock_st.expander.assert_called_once()

    def test_action_with_elevation(self, mock_st) -> None:
        """_render_actions_table renders elevation-required actions."""
        from souschef.ui.pages.powershell_migration import _render_actions_table

        mock_st.expander.return_value.__enter__ = lambda s: s
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

        actions = [
            {
                "action_type": "windows_feature_install",
                "source_line": 1,
                "confidence": "high",
                "requires_elevation": True,
                "params": {"feature_name": "Web-Server"},
                "raw": "Install-WindowsFeature -Name Web-Server",
            }
        ]
        _render_actions_table(actions)
        # Should include elevation note in the expander label
        call_args = mock_st.expander.call_args.args[0]
        assert "elevation" in call_args


class TestRenderMetricsSummary:
    """Tests for _render_metrics_summary()."""

    def test_metrics_all_columns(self, mock_st) -> None:
        """_render_metrics_summary calls metric for all 6 categories."""
        from souschef.ui.pages.powershell_migration import _render_metrics_summary

        cols = [MagicMock() for _ in range(6)]
        mock_st.columns.return_value = cols

        metrics = {
            "windows_feature": 2,
            "windows_service": 1,
            "registry": 3,
            "file": 4,
            "package": 1,
            "win_shell_fallback": 0,
        }
        _render_metrics_summary(metrics)
        assert mock_st.columns.called
        # Each column should have metric called
        assert all(c.metric.called for c in cols)
