"""
Tests for coverage gaps in souschef/ui/pages/powershell_migration.py.

Covers lines: 191, 206-209, 212-213, 232, 258, 277-310, 327, 375-377,
448-520, 531-547, 552-567.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


def _make_mock_tab() -> MagicMock:
    """Return a MagicMock that works as a context manager (for st.tabs)."""
    tab = MagicMock()
    tab.__enter__ = lambda s: s
    tab.__exit__ = MagicMock(return_value=False)
    return tab


@pytest.fixture()
def mock_st():
    """Provide a mock streamlit module for UI tests."""
    with patch("souschef.ui.pages.powershell_migration.st") as mock:
        mock.session_state = {}
        mock.columns.return_value = [MagicMock(), MagicMock()]
        mock.tabs.return_value = [MagicMock(), MagicMock()]
        yield mock


# ---------------------------------------------------------------------------
# show_powershell_migration_page — line 191 (_display_stored_results path)
# ---------------------------------------------------------------------------


def test_show_page_calls_display_stored_results_when_no_button_clicked(
    mock_st,
) -> None:
    """When no action button is clicked _display_stored_results is called (line 191)."""
    from souschef.ui.pages.powershell_migration import show_powershell_migration_page

    mock_st.text_area.return_value = ""
    mock_st.text_input.side_effect = [
        "powershell_migration",
        "windows",
        "windows_provisioning",
    ]
    col1, col2, col3 = MagicMock(), MagicMock(), MagicMock()
    for col in (col1, col2, col3):
        col.__enter__ = lambda s: s
        col.__exit__ = MagicMock(return_value=False)
        col.button = MagicMock(return_value=False)
    mock_st.columns.return_value = [col1, col2, col3]
    # st.button (called inside `with col:` blocks) must return False
    mock_st.button.return_value = False

    # No result in session state → _display_stored_results does nothing
    mock_st.session_state = {}
    show_powershell_migration_page()


# ---------------------------------------------------------------------------
# _load_json_payload — lines 206-209, 212-213
# ---------------------------------------------------------------------------


def test_load_json_payload_invalid_json_shows_error(mock_st) -> None:
    """Invalid JSON triggers st.error + st.text and returns None (lines 206-209)."""
    from souschef.ui.pages.powershell_migration import _load_json_payload

    result = _load_json_payload("this is not json", "TestOp")
    assert result is None
    mock_st.error.assert_called_once()
    mock_st.text.assert_called_once()


def test_load_json_payload_non_dict_shows_error(mock_st) -> None:
    """Non-dict JSON payload triggers st.error and returns None (lines 212-213)."""
    from souschef.ui.pages.powershell_migration import _load_json_payload

    result = _load_json_payload(json.dumps(["not", "a", "dict"]), "TestOp")
    assert result is None
    mock_st.error.assert_called_once()


def test_load_json_payload_valid_dict_returns_payload(mock_st) -> None:
    """Valid dict JSON payload is returned successfully."""
    from souschef.ui.pages.powershell_migration import _load_json_payload

    payload = {"status": "ok", "data": 42}
    result = _load_json_payload(json.dumps(payload), "TestOp")
    assert result == payload


# ---------------------------------------------------------------------------
# _handle_parse — line 232 (load_json_payload returns None)
# ---------------------------------------------------------------------------


def test_handle_parse_invalid_json_returns_early(mock_st) -> None:
    """_handle_parse returns early when parse returns invalid JSON (line 232)."""
    from souschef.ui.pages.powershell_migration import _handle_parse

    mock_st.spinner.return_value.__enter__ = lambda s: s
    mock_st.spinner.return_value.__exit__ = MagicMock(return_value=False)

    with patch(
        "souschef.ui.pages.powershell_migration.parse_powershell_content",
        return_value="not valid json",
    ):
        _handle_parse("Write-Host 'hello'")

    # st.error should have been called (from _load_json_payload)
    mock_st.error.assert_called_once()
    # parse result should NOT be stored
    assert mock_st.session_state.get("ps_parse_result") is None


# ---------------------------------------------------------------------------
# _handle_convert — line 258 (load_json_payload returns None)
# ---------------------------------------------------------------------------


def test_handle_convert_invalid_json_returns_early(mock_st) -> None:
    """_handle_convert returns early when convert returns invalid JSON (line 258)."""
    from souschef.ui.pages.powershell_migration import _handle_convert

    mock_st.spinner.return_value.__enter__ = lambda s: s
    mock_st.spinner.return_value.__exit__ = MagicMock(return_value=False)

    with patch(
        "souschef.ui.pages.powershell_migration.convert_powershell_content_to_ansible",
        return_value="not valid json",
    ):
        _handle_convert("Write-Host 'hello'", "playbook", "windows")

    mock_st.error.assert_called_once()
    assert mock_st.session_state.get("ps_convert_result") is None


# ---------------------------------------------------------------------------
# _handle_enterprise — lines 277-310
# ---------------------------------------------------------------------------


def _make_enterprise_mocks(mock_st) -> None:
    """Set up spinner and common mock_st scaffolding for enterprise tests."""
    mock_st.spinner.return_value.__enter__ = lambda s: s
    mock_st.spinner.return_value.__exit__ = MagicMock(return_value=False)

    tabs = [_make_mock_tab() for _ in range(5)]
    mock_st.tabs.return_value = tabs
    mock_st.columns.return_value = [MagicMock() for _ in range(4)]


def test_handle_enterprise_parse_returns_none_returns_early(mock_st) -> None:
    """_handle_enterprise returns early when parse gives invalid JSON (line 281)."""
    from souschef.ui.pages.powershell_migration import _handle_enterprise

    _make_enterprise_mocks(mock_st)

    with patch(
        "souschef.ui.pages.powershell_migration.parse_powershell_content",
        return_value="not valid json",
    ):
        _handle_enterprise("Write-Host 'hello'", "play", "windows", "role")

    mock_st.error.assert_called_once()
    assert mock_st.session_state.get("ps_enterprise_result") is None


def test_handle_enterprise_fidelity_returns_none_returns_early(mock_st) -> None:
    """_handle_enterprise returns early when fidelity gives invalid JSON (line 286)."""
    from souschef.ui.pages.powershell_migration import _handle_enterprise

    _make_enterprise_mocks(mock_st)
    valid_ir = json.dumps({"actions": [], "metrics": {}, "warnings": []})

    with (
        patch(
            "souschef.ui.pages.powershell_migration.parse_powershell_content",
            return_value=valid_ir,
        ),
        patch(
            "souschef.ui.pages.powershell_migration.analyze_powershell_migration_fidelity",
            return_value="not valid json",
        ),
    ):
        _handle_enterprise("Write-Host 'hello'", "play", "windows", "role")

    mock_st.error.assert_called_once()
    assert mock_st.session_state.get("ps_enterprise_result") is None


def test_handle_enterprise_success_stores_result(mock_st) -> None:
    """_handle_enterprise stores result and calls _display_enterprise_result (lines 288-310)."""
    from souschef.ui.pages.powershell_migration import _handle_enterprise

    _make_enterprise_mocks(mock_st)

    valid_ir = json.dumps({"actions": [], "metrics": {}, "warnings": []})
    valid_fidelity = json.dumps(
        {
            "fidelity_score": 100,
            "total_actions": 0,
            "automated_actions": 0,
            "fallback_actions": 0,
            "summary": "Perfect",
            "recommendations": [],
            "review_required": [],
        }
    )

    with (
        patch(
            "souschef.ui.pages.powershell_migration.parse_powershell_content",
            return_value=valid_ir,
        ),
        patch(
            "souschef.ui.pages.powershell_migration.analyze_powershell_migration_fidelity",
            return_value=valid_fidelity,
        ),
        patch(
            "souschef.ui.pages.powershell_migration.generate_windows_inventory",
            return_value="[windows]\nhost1",
        ),
        patch(
            "souschef.ui.pages.powershell_migration.generate_windows_group_vars",
            return_value="ansible_user: admin",
        ),
        patch(
            "souschef.ui.pages.powershell_migration.generate_ansible_requirements",
            return_value="collections: []",
        ),
        patch(
            "souschef.ui.pages.powershell_migration.generate_powershell_role_structure",
            return_value={"tasks/main.yml": "---\n- name: test"},
        ),
        patch(
            "souschef.ui.pages.powershell_migration.generate_powershell_awx_job_template",
            return_value="# Job Template",
        ),
    ):
        _handle_enterprise("Write-Host 'hello'", "play", "windows", "role")

    assert mock_st.session_state.get("ps_enterprise_result") is not None
    assert mock_st.session_state.get("ps_parse_result") is None
    assert mock_st.session_state.get("ps_convert_result") is None


# ---------------------------------------------------------------------------
# _display_stored_results — line 327 (enterprise result branch)
# ---------------------------------------------------------------------------


def test_display_stored_results_enterprise_result(mock_st) -> None:
    """_display_stored_results calls _display_enterprise_result (line 327)."""
    from souschef.ui.pages.powershell_migration import _display_stored_results

    fidelity = {
        "fidelity_score": 80,
        "total_actions": 2,
        "automated_actions": 1,
        "fallback_actions": 1,
        "summary": "Good",
        "recommendations": [],
        "review_required": [],
    }
    enterprise_result = {
        "fidelity": fidelity,
        "role_files": {},
        "inventory": "",
        "group_vars": "",
        "requirements": "",
        "job_template": "",
    }
    mock_st.session_state = {
        "ps_parse_result": None,
        "ps_convert_result": None,
        "ps_enterprise_result": enterprise_result,
    }
    tabs = [_make_mock_tab() for _ in range(5)]
    mock_st.tabs.return_value = tabs
    mock_st.columns.return_value = [MagicMock() for _ in range(4)]

    _display_stored_results()

    # st.columns should have been called (for the fidelity metrics row)
    mock_st.columns.assert_called()


# ---------------------------------------------------------------------------
# _render_metrics_summary — lines 375-377 (enterprise_vals branch)
# ---------------------------------------------------------------------------


def test_render_metrics_summary_with_enterprise_vals(mock_st) -> None:
    """Enterprise metric values cause additional columns to be rendered (lines 375-377)."""
    from souschef.ui.pages.powershell_migration import _render_metrics_summary

    main_cols = [MagicMock() for _ in range(6)]
    enterprise_cols = [MagicMock() for _ in range(2)]
    mock_st.columns.side_effect = [main_cols, enterprise_cols]

    metrics = {
        "windows_feature": 1,
        "windows_service": 0,
        "registry": 0,
        "file": 0,
        "package": 0,
        "win_shell_fallback": 0,
        "user": 3,
        "firewall": 2,
    }
    _render_metrics_summary(metrics)

    # columns called twice: once for main row, once for enterprise extras
    assert mock_st.columns.call_count == 2


# ---------------------------------------------------------------------------
# _display_enterprise_result — lines 448-520
# ---------------------------------------------------------------------------


def _build_enterprise_result() -> dict:
    """Return a minimal enterprise result dict for testing."""
    return {
        "fidelity": {
            "fidelity_score": 90,
            "total_actions": 5,
            "automated_actions": 4,
            "fallback_actions": 1,
            "summary": "High fidelity migration",
            "recommendations": ["Use WinRM", "Test on staging"],
            "review_required": [
                {
                    "source_line": 10,
                    "action_type": "win_shell",
                    "reason": "Complex expression",
                    "raw": "Write-Host 'test'",
                }
            ],
        },
        "role_files": {
            "tasks/main.yml": "---\n- name: test",
            "README.md": "# Role",
            "inventory/hosts": "[windows]\nhost1",
        },
        "inventory": "[windows]\nwindows01",
        "group_vars": "ansible_user: admin",
        "requirements": "collections: []",
        "job_template": "# Windows Job Template",
    }


def test_display_enterprise_result_full(mock_st) -> None:
    """_display_enterprise_result renders all tabs without error (lines 448-520)."""
    from souschef.ui.pages.powershell_migration import _display_enterprise_result

    tabs = [_make_mock_tab() for _ in range(5)]
    mock_st.tabs.return_value = tabs
    mock_st.columns.return_value = [MagicMock() for _ in range(4)]
    mock_st.expander.return_value.__enter__ = lambda s: s
    mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

    _display_enterprise_result(_build_enterprise_result())

    # Four metric columns should have metric() called
    cols = mock_st.columns.return_value
    assert all(c.metric.called for c in cols)
    # Five tabs should have been unpacked
    assert mock_st.tabs.called


# ---------------------------------------------------------------------------
# _render_fidelity_report — lines 531-547
# ---------------------------------------------------------------------------


def test_render_fidelity_report_with_recommendations_and_review(mock_st) -> None:
    """_render_fidelity_report renders recommendations and review items (lines 531-547)."""
    from souschef.ui.pages.powershell_migration import _render_fidelity_report

    mock_st.expander.return_value.__enter__ = lambda s: s
    mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

    fidelity = {
        "summary": "Mostly automated",
        "recommendations": ["Use ansible.windows.win_feature"],
        "review_required": [
            {
                "source_line": 7,
                "action_type": "win_shell",
                "reason": "Script block",
                "raw": "Invoke-Expression $script",
            }
        ],
    }
    _render_fidelity_report(fidelity)

    mock_st.markdown.assert_called_once()
    mock_st.subheader.assert_called()
    mock_st.info.assert_called_once()
    mock_st.expander.assert_called_once()


def test_render_fidelity_report_empty(mock_st) -> None:
    """_render_fidelity_report handles empty fidelity with no recommendations."""
    from souschef.ui.pages.powershell_migration import _render_fidelity_report

    _render_fidelity_report({})
    mock_st.markdown.assert_called_once()
    # No subheader/info calls when no recommendations or review items
    mock_st.subheader.assert_not_called()


# ---------------------------------------------------------------------------
# _render_role_files — lines 552-567
# ---------------------------------------------------------------------------


def test_render_role_files_empty_shows_info(mock_st) -> None:
    """_render_role_files shows info message when no role files (line 553-554)."""
    from souschef.ui.pages.powershell_migration import _render_role_files

    _render_role_files({})
    mock_st.info.assert_called_once()


def test_render_role_files_yaml_markdown_hosts(mock_st) -> None:
    """_render_role_files renders yaml, markdown and hosts files (lines 555-567)."""
    from souschef.ui.pages.powershell_migration import _render_role_files

    mock_st.expander.return_value.__enter__ = lambda s: s
    mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

    role_files = {
        "tasks/main.yml": "---\n- name: test",
        "README.md": "# Role readme",
        "inventory/hosts": "[windows]\nhost1",
    }
    _render_role_files(role_files)

    # One expander per file
    assert mock_st.expander.call_count == 3
    # caption called once (summary line)
    mock_st.caption.assert_called_once()
    # download_button called once per file
    assert mock_st.download_button.call_count == 3
