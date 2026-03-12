"""
Unit tests for the PowerShell Migration UI page.

Tests cover:
- show_powershell_migration_page: page render without crashing
- _get_ai_settings: returns expected keys
- _show_script_file_section / _show_directory_section
- Runner helpers (_run_script_analysis, _run_dir_analysis, etc.)
- Display helpers (_display_analysis_result, _display_conversion_result)
- Enterprise artefact generators (EE, inventory, credentials)
- _show_cmdlet_reference
- Missing API key guard on AI conversion
"""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Streamlit mock helper
# ---------------------------------------------------------------------------


def _make_st_mock() -> MagicMock:
    """Build a fully mocked streamlit module."""
    st = MagicMock()
    st.columns.side_effect = lambda n: [MagicMock() for _ in range(n)]
    st.selectbox.return_value = "anthropic"
    st.text_input.return_value = ""
    st.slider.return_value = 0.3
    st.number_input.return_value = 4000
    st.checkbox.return_value = True
    st.radio.return_value = "Script File Path"
    st.button.return_value = False
    st.session_state = {}
    ctx_mgr = MagicMock()
    ctx_mgr.__enter__ = MagicMock(return_value=ctx_mgr)
    ctx_mgr.__exit__ = MagicMock(return_value=False)
    st.expander.return_value = ctx_mgr
    st.spinner.return_value = ctx_mgr
    return st


# ---------------------------------------------------------------------------
# Tests: show_powershell_migration_page
# ---------------------------------------------------------------------------


def test_show_powershell_migration_page_renders(tmp_path: Path) -> None:
    """Test that show_powershell_migration_page renders without error."""
    st = _make_st_mock()
    with patch(
        "souschef.ui.pages.powershell_migration.st", st
    ):
        from souschef.ui.pages.powershell_migration import show_powershell_migration_page

        show_powershell_migration_page()
    st.header.assert_called_once_with("PowerShell Migration")


def test_show_powershell_migration_page_module_mode(tmp_path: Path) -> None:
    """Test that the module directory section renders."""
    st = _make_st_mock()
    st.radio.return_value = "Script Directory Path"
    with patch(
        "souschef.ui.pages.powershell_migration.st", st
    ):
        from souschef.ui.pages.powershell_migration import show_powershell_migration_page

        show_powershell_migration_page()
    st.header.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: _get_ai_settings
# ---------------------------------------------------------------------------


def test_get_ai_settings_returns_expected_keys() -> None:
    """Test that _get_ai_settings returns a dict with required keys."""
    st = _make_st_mock()
    st.selectbox.return_value = "anthropic"
    st.text_input.side_effect = ["sk-test", "claude-3-5-sonnet-20241022", "", ""]
    st.slider.return_value = 0.3
    st.number_input.return_value = 4000

    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import _get_ai_settings

        settings = _get_ai_settings()

    assert "provider" in settings
    assert "api_key" in settings
    assert "model" in settings
    assert "temperature" in settings
    assert "max_tokens" in settings
    assert "project_id" in settings
    assert "base_url" in settings


# ---------------------------------------------------------------------------
# Tests: _show_script_file_section
# ---------------------------------------------------------------------------


def test_show_script_file_section_no_path_no_action() -> None:
    """Test that empty path with button click shows a warning."""
    st = _make_st_mock()
    st.text_input.return_value = ""
    st.button.return_value = True  # simulate click

    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import _show_script_file_section

        _show_script_file_section()

    st.warning.assert_called()


def test_show_script_file_section_analyse_clicked(tmp_path: Path) -> None:
    """Test that clicking Analyse triggers script analysis."""
    script = tmp_path / "setup.ps1"
    script.write_text("Install-WindowsFeature -Name IIS", encoding="utf-8")

    st = _make_st_mock()
    # First call = script path; remaining calls (AI settings) return ""
    call_count = [0]

    def _text_input_side(*_: object, **__: object) -> str:
        call_count[0] += 1
        return str(script) if call_count[0] == 1 else ""

    st.text_input.side_effect = _text_input_side
    # Simulate: analyse=True, convert=False, ai=False
    st.button.side_effect = [True, False, False]

    with patch("souschef.ui.pages.powershell_migration.st", st), patch(
        "souschef.ui.pages.powershell_migration.parse_powershell_script",
        return_value="PowerShell Script Analysis: test",
    ) as mock_parse:
        from souschef.ui.pages.powershell_migration import _show_script_file_section

        _show_script_file_section()

    mock_parse.assert_called_once_with(str(script))


def test_show_script_file_section_convert_clicked(tmp_path: Path) -> None:
    """Test that clicking Convert triggers script conversion."""
    script = tmp_path / "setup.ps1"
    script.write_text("Install-WindowsFeature -Name IIS", encoding="utf-8")

    st = _make_st_mock()
    call_count = [0]

    def _text_input_side(*_: object, **__: object) -> str:
        call_count[0] += 1
        return str(script) if call_count[0] == 1 else ""

    st.text_input.side_effect = _text_input_side
    st.button.side_effect = [False, True, False]

    with patch("souschef.ui.pages.powershell_migration.st", st), patch(
        "souschef.ui.pages.powershell_migration.convert_powershell_script_to_ansible",
        return_value="- hosts: windows\n  tasks: []\n",
    ) as mock_conv:
        from souschef.ui.pages.powershell_migration import _show_script_file_section

        _show_script_file_section()

    mock_conv.assert_called_once_with(str(script))


def test_show_script_file_section_ai_clicked_no_key(tmp_path: Path) -> None:
    """Test that AI conversion without API key shows a warning."""
    script = tmp_path / "setup.ps1"
    script.write_text("Install-WindowsFeature -Name IIS", encoding="utf-8")

    st = _make_st_mock()
    # First text_input = script path; all others = "" (including API key)
    call_count = [0]

    def _text_input_side(*_: object, **__: object) -> str:
        call_count[0] += 1
        return str(script) if call_count[0] == 1 else ""

    st.text_input.side_effect = _text_input_side
    st.button.side_effect = [False, False, True]  # AI clicked

    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import _show_script_file_section

        _show_script_file_section()

    st.warning.assert_called()


# ---------------------------------------------------------------------------
# Tests: _show_directory_section
# ---------------------------------------------------------------------------


def test_show_directory_section_no_path_with_click() -> None:
    """Test that empty directory path with click shows warning."""
    st = _make_st_mock()
    st.text_input.return_value = ""
    st.button.return_value = True

    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import _show_directory_section

        _show_directory_section()

    st.warning.assert_called()


def test_show_directory_section_analyse_clicked(tmp_path: Path) -> None:
    """Test that clicking Analyse triggers directory analysis."""
    st = _make_st_mock()
    call_count = [0]

    def _text_input_side(*_: object, **__: object) -> str:
        call_count[0] += 1
        return str(tmp_path) if call_count[0] == 1 else ""

    st.text_input.side_effect = _text_input_side
    st.button.side_effect = [True, False, False]

    with patch("souschef.ui.pages.powershell_migration.st", st), patch(
        "souschef.ui.pages.powershell_migration.parse_powershell_directory",
        return_value="Warning: No scripts found",
    ) as mock_parse:
        from souschef.ui.pages.powershell_migration import _show_directory_section

        _show_directory_section()

    mock_parse.assert_called_once()


def test_show_directory_section_convert_clicked(tmp_path: Path) -> None:
    """Test that clicking Convert triggers directory conversion."""
    (tmp_path / "a.ps1").write_text("Install-WindowsFeature -Name IIS", encoding="utf-8")

    st = _make_st_mock()
    call_count = [0]

    def _text_input_side(*_: object, **__: object) -> str:
        call_count[0] += 1
        return str(tmp_path) if call_count[0] == 1 else ""

    st.text_input.side_effect = _text_input_side
    st.button.side_effect = [False, True, False]

    with patch("souschef.ui.pages.powershell_migration.st", st), patch(
        "souschef.ui.pages.powershell_migration.convert_powershell_directory_to_ansible",
        return_value="- hosts: windows\n  tasks: []\n",
    ) as mock_conv:
        from souschef.ui.pages.powershell_migration import _show_directory_section

        _show_directory_section()

    mock_conv.assert_called_once()


def test_show_directory_section_ai_clicked_no_key(tmp_path: Path) -> None:
    """Test that AI directory conversion without API key shows warning."""
    st = _make_st_mock()
    call_count = [0]

    def _text_input_side(*_: object, **__: object) -> str:
        call_count[0] += 1
        return str(tmp_path) if call_count[0] == 1 else ""

    st.text_input.side_effect = _text_input_side
    st.button.side_effect = [False, False, True]

    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import _show_directory_section

        _show_directory_section()

    st.warning.assert_called()


# ---------------------------------------------------------------------------
# Tests: _display_analysis_result
# ---------------------------------------------------------------------------


def test_display_analysis_result_error() -> None:
    """Test that error result is displayed with st.error."""
    st = _make_st_mock()
    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import _display_analysis_result

        _display_analysis_result("Error: Something went wrong", "script")

    st.error.assert_called_once()


def test_display_analysis_result_warning() -> None:
    """Test that warning result is displayed with st.warning."""
    st = _make_st_mock()
    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import _display_analysis_result

        _display_analysis_result("Warning: No scripts found", "directory")

    st.warning.assert_called()


def test_display_analysis_result_success() -> None:
    """Test that successful analysis shows st.success."""
    st = _make_st_mock()
    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import _display_analysis_result

        _display_analysis_result("PowerShell Script Analysis: test", "script")

    st.success.assert_called_once()


def test_display_analysis_result_unsupported_warning() -> None:
    """Test that unsupported constructs trigger an additional warning."""
    st = _make_st_mock()
    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import _display_analysis_result

        _display_analysis_result(
            "PowerShell Script Analysis\nUnsupported Constructs (1):\n  [WMI query]",
            "script",
        )

    warning_msgs = [str(c) for c in st.warning.call_args_list]
    assert any("AI" in msg or "Convert" in msg for msg in warning_msgs)


# ---------------------------------------------------------------------------
# Tests: _display_conversion_result
# ---------------------------------------------------------------------------


def test_display_conversion_result_error() -> None:
    """Test that error playbook shows st.error."""
    st = _make_st_mock()
    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import _display_conversion_result

        _display_conversion_result("Error: conversion failed", "script.ps1")

    st.error.assert_called_once()


def test_display_conversion_result_warning() -> None:
    """Test that warning playbook shows st.warning."""
    st = _make_st_mock()
    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import _display_conversion_result

        _display_conversion_result("Warning: nothing converted", "script.ps1")

    st.warning.assert_called()


def test_display_conversion_result_success() -> None:
    """Test that successful conversion shows st.success."""
    st = _make_st_mock()
    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import _display_conversion_result

        _display_conversion_result(
            "- name: play\n  hosts: windows\n  tasks: []\n", "setup.ps1"
        )

    st.success.assert_called_once()


def test_display_conversion_result_ai_enhanced() -> None:
    """Test that AI-enhanced conversion shows ai_enhanced messaging."""
    st = _make_st_mock()
    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import _display_conversion_result

        _display_conversion_result(
            "- name: play\n  hosts: windows\n  tasks: []\n",
            "setup.ps1",
            ai_enhanced=True,
        )

    success_args = str(st.success.call_args_list)
    assert "AI" in success_args or "ai" in success_args.lower()


def test_display_conversion_result_warns_on_stub_tasks() -> None:
    """Test that WARNING stubs trigger a manual-review warning."""
    st = _make_st_mock()
    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import _display_conversion_result

        _display_conversion_result(
            "- name: WARNING: Unknown-Cmdlet requires manual conversion\n  hosts: windows",
            "setup.ps1",
        )

    warning_calls = str(st.warning.call_args_list)
    assert "WARNING" in warning_calls or "manual" in warning_calls.lower()


# ---------------------------------------------------------------------------
# Tests: Enterprise artefact section
# ---------------------------------------------------------------------------


def test_show_enterprise_artefacts_section_renders() -> None:
    """Test that the enterprise artefacts section renders."""
    st = _make_st_mock()
    st.button.return_value = False

    with patch("souschef.ui.pages.powershell_migration.st", st):
        from souschef.ui.pages.powershell_migration import (
            _show_enterprise_artefacts_section,
        )

        _show_enterprise_artefacts_section()

    st.subheader.assert_called()


def test_show_ee_generator_button_clicked() -> None:
    """Test EE generator renders output when button clicked."""
    st = _make_st_mock()
    st.text_input.side_effect = ["windows-ee", "", "", ""]
    st.button.return_value = True

    with patch("souschef.ui.pages.powershell_migration.st", st), patch(
        "souschef.ui.pages.powershell_migration.generate_windows_ee_definition",
        return_value="# EE definition\nversion: 3\n",
    ) as mock_gen:
        from souschef.ui.pages.powershell_migration import _show_ee_generator

        _show_ee_generator()

    mock_gen.assert_called_once()
    st.code.assert_called()


def test_show_inventory_generator_button_clicked() -> None:
    """Test inventory generator renders output when button clicked."""
    st = _make_st_mock()
    st.text_input.side_effect = ["win-server-01,win-server-02", "windows"]
    st.selectbox.return_value = "ntlm"
    st.button.return_value = True

    with patch("souschef.ui.pages.powershell_migration.st", st), patch(
        "souschef.ui.pages.powershell_migration.generate_windows_inventory_template",
        return_value="windows:\n  hosts:\n    win-server-01: {}\n",
    ) as mock_gen:
        from souschef.ui.pages.powershell_migration import _show_inventory_generator

        _show_inventory_generator()

    mock_gen.assert_called_once()
    st.code.assert_called()


def test_show_credential_generator_button_clicked() -> None:
    """Test credential generator renders output when button clicked."""
    st = _make_st_mock()
    st.selectbox.return_value = "ntlm"
    st.number_input.return_value = 5985
    st.checkbox.return_value = True
    st.button.return_value = True

    with patch("souschef.ui.pages.powershell_migration.st", st), patch(
        "souschef.ui.pages.powershell_migration.generate_aap_windows_credential_vars",
        return_value="ansible_connection: winrm\n",
    ) as mock_gen:
        from souschef.ui.pages.powershell_migration import _show_credential_generator

        _show_credential_generator()

    mock_gen.assert_called_once()
    st.code.assert_called()


# ---------------------------------------------------------------------------
# Tests: _show_cmdlet_reference
# ---------------------------------------------------------------------------


def test_show_cmdlet_reference_renders() -> None:
    """Test that the cmdlet reference table renders."""
    st = _make_st_mock()
    ctx_mgr = MagicMock()
    ctx_mgr.__enter__ = MagicMock(return_value=ctx_mgr)
    ctx_mgr.__exit__ = MagicMock(return_value=False)
    st.expander.return_value = ctx_mgr

    with patch("souschef.ui.pages.powershell_migration.st", st), patch(
        "souschef.ui.pages.powershell_migration.get_powershell_ansible_module_map",
        return_value={"install-windowsfeature": "ansible.windows.win_feature"},
    ):
        from souschef.ui.pages.powershell_migration import _show_cmdlet_reference

        _show_cmdlet_reference()

    st.expander.assert_called()
