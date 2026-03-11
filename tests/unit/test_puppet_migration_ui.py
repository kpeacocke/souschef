"""
Unit tests for the Puppet Migration UI page.

Tests cover the show_puppet_migration_page and all helper functions
including section renderers, analysis/conversion runners, and display helpers.
"""

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Streamlit mock setup
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_streamlit():
    """Mock Streamlit for all tests in this module."""
    mock_st = MagicMock()
    mock_st.session_state = {}
    # Make spinner a context manager
    mock_st.spinner.return_value.__enter__ = MagicMock(return_value=None)
    mock_st.spinner.return_value.__exit__ = MagicMock(return_value=False)
    # Make expander a context manager
    mock_st.expander.return_value.__enter__ = MagicMock(return_value=None)
    mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)
    # Make columns return the correct number of mock column objects
    mock_st.columns.side_effect = lambda n: [MagicMock() for _ in range(n)]

    with patch("souschef.ui.pages.puppet_migration.st", mock_st):
        yield mock_st


# ---------------------------------------------------------------------------
# Import after mocking
# ---------------------------------------------------------------------------

from souschef.ui.pages.puppet_migration import (  # noqa: E402
    INPUT_METHOD_FILE_PATH,
    INPUT_METHOD_MODULE_PATH,
    _display_analysis_result,
    _display_conversion_result,
    _run_manifest_analysis,
    _run_manifest_conversion,
    _run_module_analysis,
    _run_module_conversion,
    _show_manifest_file_section,
    _show_module_directory_section,
    _show_resource_type_reference,
    show_puppet_migration_page,
)

# ---------------------------------------------------------------------------
# Tests: show_puppet_migration_page
# ---------------------------------------------------------------------------


def test_show_puppet_migration_page_calls_header(mock_streamlit: MagicMock) -> None:
    """Test that the main page renders a header."""
    mock_streamlit.radio.return_value = INPUT_METHOD_FILE_PATH
    show_puppet_migration_page()
    mock_streamlit.header.assert_called_once_with("Puppet Migration")


def test_show_puppet_migration_page_file_method(mock_streamlit: MagicMock) -> None:
    """Test that file input method shows the manifest section."""
    mock_streamlit.radio.return_value = INPUT_METHOD_FILE_PATH
    with patch(
        "souschef.ui.pages.puppet_migration._show_manifest_file_section"
    ) as mock_section:
        show_puppet_migration_page()
        mock_section.assert_called_once()


def test_show_puppet_migration_page_module_method(mock_streamlit: MagicMock) -> None:
    """Test that module input method shows the module section."""
    mock_streamlit.radio.return_value = INPUT_METHOD_MODULE_PATH
    with patch(
        "souschef.ui.pages.puppet_migration._show_module_directory_section"
    ) as mock_section:
        show_puppet_migration_page()
        mock_section.assert_called_once()


def test_show_puppet_migration_page_shows_reference(mock_streamlit: MagicMock) -> None:
    """Test that the resource type reference is shown."""
    mock_streamlit.radio.return_value = INPUT_METHOD_FILE_PATH
    with patch(
        "souschef.ui.pages.puppet_migration._show_resource_type_reference"
    ) as mock_ref:
        show_puppet_migration_page()
        mock_ref.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: _show_manifest_file_section
# ---------------------------------------------------------------------------


def test_show_manifest_file_no_path_no_click(mock_streamlit: MagicMock) -> None:
    """Test that no warning is shown when path is empty and no button clicked."""
    mock_streamlit.text_input.return_value = ""
    mock_streamlit.button.return_value = False
    _show_manifest_file_section()
    mock_streamlit.warning.assert_not_called()


def test_show_manifest_file_no_path_with_analyse_click(mock_streamlit: MagicMock) -> None:
    """Test that warning is shown when analyse clicked with empty path."""
    mock_streamlit.text_input.return_value = ""
    # First button = analyse (secondary), second = convert (primary)
    mock_streamlit.button.side_effect = [True, False]
    _show_manifest_file_section()
    mock_streamlit.warning.assert_called()


def test_show_manifest_file_no_path_with_convert_click(mock_streamlit: MagicMock) -> None:
    """Test that warning is shown when convert clicked with empty path."""
    mock_streamlit.text_input.return_value = ""
    mock_streamlit.button.side_effect = [False, True]
    _show_manifest_file_section()
    mock_streamlit.warning.assert_called()


def test_show_manifest_file_analyse_clicked(mock_streamlit: MagicMock) -> None:
    """Test that analyse click triggers _run_manifest_analysis."""
    mock_streamlit.text_input.return_value = "/path/to/manifest.pp"
    mock_streamlit.button.side_effect = [True, False]

    with patch(
        "souschef.ui.pages.puppet_migration._run_manifest_analysis"
    ) as mock_run:
        _show_manifest_file_section()
        mock_run.assert_called_once_with("/path/to/manifest.pp")


def test_show_manifest_file_convert_clicked(mock_streamlit: MagicMock) -> None:
    """Test that convert click triggers _run_manifest_conversion."""
    mock_streamlit.text_input.return_value = "/path/to/manifest.pp"
    mock_streamlit.button.side_effect = [False, True]

    with patch(
        "souschef.ui.pages.puppet_migration._run_manifest_conversion"
    ) as mock_run:
        _show_manifest_file_section()
        mock_run.assert_called_once_with("/path/to/manifest.pp")


# ---------------------------------------------------------------------------
# Tests: _show_module_directory_section
# ---------------------------------------------------------------------------


def test_show_module_no_path_no_click(mock_streamlit: MagicMock) -> None:
    """Test that no warning when module path empty and no button clicked."""
    mock_streamlit.text_input.return_value = ""
    mock_streamlit.button.return_value = False
    _show_module_directory_section()
    mock_streamlit.warning.assert_not_called()


def test_show_module_no_path_with_click(mock_streamlit: MagicMock) -> None:
    """Test that warning is shown when module analyse clicked with empty path."""
    mock_streamlit.text_input.return_value = ""
    mock_streamlit.button.side_effect = [True, False]
    _show_module_directory_section()
    mock_streamlit.warning.assert_called()


def test_show_module_analyse_clicked(mock_streamlit: MagicMock) -> None:
    """Test that module analyse click triggers _run_module_analysis."""
    mock_streamlit.text_input.return_value = "/path/to/module"
    mock_streamlit.button.side_effect = [True, False]

    with patch(
        "souschef.ui.pages.puppet_migration._run_module_analysis"
    ) as mock_run:
        _show_module_directory_section()
        mock_run.assert_called_once_with("/path/to/module")


def test_show_module_convert_clicked(mock_streamlit: MagicMock) -> None:
    """Test that module convert click triggers _run_module_conversion."""
    mock_streamlit.text_input.return_value = "/path/to/module"
    mock_streamlit.button.side_effect = [False, True]

    with patch(
        "souschef.ui.pages.puppet_migration._run_module_conversion"
    ) as mock_run:
        _show_module_directory_section()
        mock_run.assert_called_once_with("/path/to/module")


# ---------------------------------------------------------------------------
# Tests: _run_manifest_analysis / _run_module_analysis
# ---------------------------------------------------------------------------


def test_run_manifest_analysis_success(mock_streamlit: MagicMock) -> None:
    """Test _run_manifest_analysis calls parse and display."""
    with (
        patch(
            "souschef.ui.pages.puppet_migration.parse_puppet_manifest",
            return_value=(
                "Puppet Manifest Analysis: /some.pp\n"
                "Resources (1):\n  package { 'vim' } [line 1]"
            ),
        ),
        patch(
            "souschef.ui.pages.puppet_migration._display_analysis_result"
        ) as mock_display,
    ):
        _run_manifest_analysis("/some.pp")
        mock_display.assert_called_once()


def test_run_module_analysis_success(mock_streamlit: MagicMock) -> None:
    """Test _run_module_analysis calls parse and display."""
    with patch(
        "souschef.ui.pages.puppet_migration.parse_puppet_module",
        return_value="Puppet Manifest Analysis: /module\nResources: none found",
    ), patch(
        "souschef.ui.pages.puppet_migration._display_analysis_result"
    ) as mock_display:
        _run_module_analysis("/module")
        mock_display.assert_called_once()


def test_run_manifest_conversion_success(mock_streamlit: MagicMock) -> None:
    """Test _run_manifest_conversion calls convert and display."""
    with patch(
        "souschef.ui.pages.puppet_migration.convert_puppet_manifest_to_ansible",
        return_value="- name: play\n  hosts: all\n  tasks: []\n",
    ), patch(
        "souschef.ui.pages.puppet_migration._display_conversion_result"
    ) as mock_display:
        _run_manifest_conversion("/some.pp")
        mock_display.assert_called_once()


def test_run_module_conversion_success(mock_streamlit: MagicMock) -> None:
    """Test _run_module_conversion calls convert and display."""
    with patch(
        "souschef.ui.pages.puppet_migration.convert_puppet_module_to_ansible",
        return_value="- name: play\n  hosts: all\n  tasks: []\n",
    ), patch(
        "souschef.ui.pages.puppet_migration._display_conversion_result"
    ) as mock_display:
        _run_module_conversion("/module")
        mock_display.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: _display_analysis_result
# ---------------------------------------------------------------------------


def test_display_analysis_result_error(mock_streamlit: MagicMock) -> None:
    """Test that error results show an error message."""
    _display_analysis_result("Error: file not found", "manifest")
    mock_streamlit.error.assert_called_once()


def test_display_analysis_result_warning(mock_streamlit: MagicMock) -> None:
    """Test that warning results show a warning message."""
    _display_analysis_result("Warning: no manifests found", "module")
    mock_streamlit.warning.assert_called()


def test_display_analysis_result_success(mock_streamlit: MagicMock) -> None:
    """Test that successful analysis shows success and text area."""
    _display_analysis_result(
        "Puppet Manifest Analysis: test.pp\nResources: none found", "manifest"
    )
    mock_streamlit.success.assert_called_once()
    mock_streamlit.text_area.assert_called_once()
    mock_streamlit.download_button.assert_called_once()


def test_display_analysis_result_with_unsupported_warning(mock_streamlit: MagicMock) -> None:
    """Test that unsupported constructs trigger a warning."""
    result = "Puppet Manifest Analysis: test.pp\nUnsupported Constructs (3) - require manual review:"
    _display_analysis_result(result, "manifest")
    # Should show the unsupported warning
    warning_calls = mock_streamlit.warning.call_args_list
    assert len(warning_calls) >= 1


def test_display_analysis_result_generic_error(mock_streamlit: MagicMock) -> None:
    """Test that 'An error occurred' prefix triggers error display."""
    _display_analysis_result("An error occurred: something failed", "manifest")
    mock_streamlit.error.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: _display_conversion_result
# ---------------------------------------------------------------------------


def test_display_conversion_result_error(mock_streamlit: MagicMock) -> None:
    """Test that error conversion results show an error message."""
    _display_conversion_result("Error: file not found", "/path")
    mock_streamlit.error.assert_called_once()


def test_display_conversion_result_warning(mock_streamlit: MagicMock) -> None:
    """Test that warning conversion results show a warning message."""
    _display_conversion_result("Warning: no manifests found", "/path")
    mock_streamlit.warning.assert_called()


def test_display_conversion_result_success(mock_streamlit: MagicMock) -> None:
    """Test that successful conversion shows success and code display."""
    _display_conversion_result(
        "- name: play\n  hosts: all\n  tasks: []\n", "/path/to.pp"
    )
    mock_streamlit.success.assert_called_once()
    mock_streamlit.code.assert_called_once()
    mock_streamlit.download_button.assert_called_once()


def test_display_conversion_result_with_warning_task(mock_streamlit: MagicMock) -> None:
    """Test that playbooks with WARNING tasks show a warning."""
    playbook = "- name: play\n  tasks:\n  - name: WARNING: Hiera lookup\n"
    _display_conversion_result(playbook, "/path/to.pp")
    mock_streamlit.warning.assert_called()


def test_display_conversion_result_generic_error(mock_streamlit: MagicMock) -> None:
    """Test that 'An error occurred' prefix triggers error display."""
    _display_conversion_result("An error occurred: boom", "/path")
    mock_streamlit.error.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: _show_resource_type_reference
# ---------------------------------------------------------------------------


def test_show_resource_type_reference(mock_streamlit: MagicMock) -> None:
    """Test that resource type reference renders an expander."""
    _show_resource_type_reference()
    mock_streamlit.expander.assert_called_once()
