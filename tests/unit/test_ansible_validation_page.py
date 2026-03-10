"""Comprehensive tests for ansible_validation UI page to achieve 100% coverage."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock, Mock, patch


class SessionState(dict):
    """Session state helper that supports attribute and dict access."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value

    def __delattr__(self, name: str):
        if name in self:
            del self[name]
        else:
            raise AttributeError(name)


def _ctx() -> MagicMock:
    """Create a context manager mock for Streamlit columns/expanders/etc."""
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=False)
    return mock


class TestDisplayValidationIntro:
    """Test validation page intro display."""

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_intro(self, mock_st):
        """Test that intro title and markdown are displayed."""
        from souschef.ui.pages.ansible_validation import _display_validation_intro

        _display_validation_intro()

        mock_st.title.assert_called_once_with("Ansible Collection Validation")
        mock_st.markdown.assert_called_once()


class TestRenderValidationInputs:
    """Test validation inputs rendering."""

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_render_inputs(self, mock_st):
        """Test input rendering and button state."""
        from souschef.ui.pages.ansible_validation import _render_validation_inputs

        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)
        mock_file = MagicMock()
        mock_st.file_uploader.return_value = mock_file
        mock_st.selectbox.return_value = "2.15"
        mock_st.button.return_value = True

        collections_file, target_version, validate_btn = _render_validation_inputs()

        assert collections_file == mock_file
        assert target_version == "2.15"
        assert validate_btn is True

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_render_inputs_button_false(self, mock_st):
        """Test with button not pressed."""
        from souschef.ui.pages.ansible_validation import _render_validation_inputs

        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)
        mock_st.file_uploader.return_value = None
        mock_st.selectbox.return_value = "2.14"
        mock_st.button.return_value = False

        collections_file, target_version, validate_btn = _render_validation_inputs()

        assert collections_file is None
        assert target_version == "2.14"
        assert validate_btn is False


class TestSaveUploadedFile:
    """Test file saving functionality."""

    def test_save_uploaded_file(self):
        """Test that uploaded file is saved to temporary location."""
        from souschef.ui.pages.ansible_validation import _save_uploaded_file

        mock_file = MagicMock()
        mock_file.getbuffer.return_value.tobytes.return_value = b"test content"

        result_path = _save_uploaded_file(mock_file)

        assert result_path is not None
        assert result_path.endswith("requirements.yml")
        # Verify file was written
        from pathlib import Path

        assert Path(result_path).exists()
        # Cleanup
        import shutil

        shutil.rmtree(str(Path(result_path).parent), ignore_errors=True)

    def test_save_uploaded_file_creates_temp_dir(self):
        """Test that save_uploaded_file creates proper temp structure."""
        from pathlib import Path

        from souschef.ui.pages.ansible_validation import _save_uploaded_file

        mock_file = MagicMock()
        mock_file.getbuffer.return_value.tobytes.return_value = (
            b"collections:\n  - name: test"
        )

        result_path = _save_uploaded_file(mock_file)
        path_obj = Path(result_path)

        assert path_obj.name == "requirements.yml"
        assert path_obj.parent.exists()

        # Cleanup
        import shutil

        shutil.rmtree(str(path_obj.parent), ignore_errors=True)


class TestDisplayValidationMetrics:
    """Test validation metrics display."""

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_metrics_with_all_categories(self, mock_st):
        """Test displaying metrics with all collection categories."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_metrics,
        )

        col1, col2, col3, col4 = _ctx(), _ctx(), _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2, col3, col4)

        validation = {
            "compatible": [{"collection": "test.collection", "version": "1.0"}],
            "incompatible": [{"collection": "bad.collection", "version": "2.0"}],
            "updates_needed": [{"collection": "old.collection", "version": "1.5"}],
            "warnings": ["Warning 1"],
        }

        result = _display_validation_metrics(validation)

        assert len(result["compatible"]) == 1
        assert len(result["incompatible"]) == 1
        assert len(result["updates_needed"]) == 1
        assert len(result["warnings"]) == 1
        assert mock_st.metric.call_count == 4

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_metrics_with_empty_categories(self, mock_st):
        """Test displaying metrics with empty categories."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_metrics,
        )

        col1, col2, col3, col4 = _ctx(), _ctx(), _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2, col3, col4)

        validation = {
            "compatible": [],
            "incompatible": [],
            "updates_needed": [],
            "warnings": [],
        }

        result = _display_validation_metrics(validation)

        assert result["compatible"] == []
        assert result["incompatible"] == []
        assert result["updates_needed"] == []
        assert result["warnings"] == []

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_metrics_with_non_list_values(self, mock_st):
        """Test handling of non-list values in validation dict."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_metrics,
        )

        col1, col2, col3, col4 = _ctx(), _ctx(), _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2, col3, col4)

        validation = {
            "compatible": "not a list",
            "incompatible": 123,
            "updates_needed": {"not": "list"},
            "warnings": None,
        }

        result = _display_validation_metrics(validation)

        assert result["compatible"] == []
        assert result["incompatible"] == []
        assert result["updates_needed"] == []
        assert result["warnings"] == []


class TestDisplayValidationSummary:
    """Test validation summary tab."""

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_summary_with_collections(self, mock_st):
        """Test summary display with collections."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_summary,
        )

        compatible = [{"collection": "test.one", "version": "1.0"}]
        incompatible = [{"collection": "test.bad", "version": "2.0"}]
        updates_needed = [{"collection": "test.old", "version": "1.5"}]
        warnings = ["Warning 1", "Warning 2"]

        _display_validation_summary(compatible, incompatible, updates_needed, warnings)

        mock_st.subheader.assert_called_once_with("Summary")
        assert mock_st.progress.called
        assert mock_st.write.called

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_summary_no_collections(self, mock_st):
        """Test summary display with no collections."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_summary,
        )

        compatible: list[dict[str, str]] = []
        incompatible: list[dict[str, str]] = []
        updates_needed: list[dict[str, str]] = []
        warnings: list[str] = []

        _display_validation_summary(compatible, incompatible, updates_needed, warnings)

        mock_st.subheader.assert_called_once_with("Summary")
        # Should show total 0
        assert mock_st.write.called


class TestDisplayValidationCompatibleTab:
    """Test compatible collections tab."""

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_compatible_with_items(self, mock_st):
        """Test displaying compatible collections."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_compatible_tab,
        )

        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)

        compatible = [
            {"collection": "test.one", "version": "1.0"},
            {"collection": "test.two", "version": "2.0"},
            {"collection": "test.three", "version": "3.0"},
        ]

        _display_validation_compatible_tab(compatible)

        mock_st.subheader.assert_called_once_with("Compatible Collections")
        assert mock_st.write.call_count >= 3

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_compatible_empty(self, mock_st):
        """Test displaying when no compatible collections."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_compatible_tab,
        )

        compatible: list[dict[str, str]] = []

        _display_validation_compatible_tab(compatible)

        mock_st.info.assert_called_once_with("No fully compatible collections")


class TestDisplayValidationRequiresTab:
    """Test updates needed tab."""

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_requires_with_items(self, mock_st):
        """Test displaying collections that require updates."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_requires_tab,
        )

        mock_st.expander.return_value = _ctx()

        updates_needed = [
            {
                "collection": "test.old",
                "current": "1.0",
                "required": "2.0",
            }
        ]

        _display_validation_requires_tab(updates_needed)

        mock_st.subheader.assert_called_once_with("Collections Requiring Update")
        mock_st.expander.assert_called_once()

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_requires_empty(self, mock_st):
        """Test displaying when no updates needed."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_requires_tab,
        )

        updates_needed: list[dict[str, str]] = []

        _display_validation_requires_tab(updates_needed)

        mock_st.info.assert_called_once_with("No collections require mandatory updates")


class TestDisplayValidationWarningsTab:
    """Test warnings tab."""

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_warnings_with_items(self, mock_st):
        """Test displaying warnings."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_warnings_tab,
        )

        warnings = ["Warning 1", "Warning 2"]

        _display_validation_warnings_tab(warnings)

        mock_st.subheader.assert_called_once_with("Validation Warnings")
        assert mock_st.warning.call_count == 2

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_warnings_empty(self, mock_st):
        """Test displaying when no warnings."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_warnings_tab,
        )

        warnings: list[str] = []

        _display_validation_warnings_tab(warnings)

        mock_st.info.assert_called_once_with("No warnings")


class TestDisplayValidationIncompatibleTab:
    """Test incompatible collections tab."""

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_incompatible_with_items(self, mock_st):
        """Test displaying incompatible collections."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_incompatible_tab,
        )

        incompatible = [
            {"collection": "test.bad", "version": "1.0"},
            {"collection": "test.worse", "version": "2.0"},
        ]

        _display_validation_incompatible_tab(incompatible)

        assert mock_st.error.call_count >= 3  # Header + 2 items
        mock_st.markdown.assert_called_once()

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_incompatible_empty(self, mock_st):
        """Test displaying when no incompatible collections."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_incompatible_tab,
        )

        incompatible: list[dict[str, str]] = []

        _display_validation_incompatible_tab(incompatible)

        mock_st.success.assert_called_once_with("No incompatible collections detected!")


class TestDisplayValidationTabs:
    """Test validation tabs structure."""

    @patch("souschef.ui.pages.ansible_validation.st")
    @patch("souschef.ui.pages.ansible_validation._display_validation_summary")
    @patch("souschef.ui.pages.ansible_validation._display_validation_compatible_tab")
    @patch("souschef.ui.pages.ansible_validation._display_validation_incompatible_tab")
    @patch("souschef.ui.pages.ansible_validation._display_validation_requires_tab")
    @patch("souschef.ui.pages.ansible_validation._display_validation_warnings_tab")
    def test_display_tabs(
        self,
        mock_warnings,
        mock_requires,
        mock_incompatible,
        mock_compatible,
        mock_summary,
        mock_st,
    ):
        """Test that all tabs are created and populated."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_tabs,
        )

        tab_mocks = [_ctx(), _ctx(), _ctx(), _ctx(), _ctx()]
        mock_st.tabs.return_value = tab_mocks

        validation = cast(
            dict[str, Any],
            {
                "compatible": [],
                "incompatible": [],
                "updates_needed": [],
                "warnings": [],
            },
        )

        _display_validation_tabs(
            validation,
            cast(list[dict[str, str]], []),
            cast(list[dict[str, str]], []),
            cast(list[dict[str, str]], []),
            cast(list[str], []),
        )

        mock_st.tabs.assert_called_once()
        mock_summary.assert_called_once()
        mock_compatible.assert_called_once()
        mock_incompatible.assert_called_once()
        mock_requires.assert_called_once()
        mock_warnings.assert_called_once()


class TestDisplayValidationExport:
    """Test validation export functionality."""

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_export(self, mock_st):
        """Test export button display."""
        from souschef.ui.pages.ansible_validation import (
            _display_validation_export,
        )

        validation = cast(
            dict[str, Any],
            {
                "compatible": [],
                "incompatible": [],
                "updates_needed": [],
                "warnings": [],
            },
        )

        _display_validation_export(validation, "2.15")

        mock_st.divider.assert_called_once()
        mock_st.subheader.assert_called_once_with("Export Validation Report")
        mock_st.download_button.assert_called_once()

        # Verify download button parameters
        call_args = mock_st.download_button.call_args
        assert "Download Validation Report as JSON" in call_args[1]["label"]
        assert "ansible_collection_validation_2.15.json" in call_args[1]["file_name"]


class TestDisplayValidationHelp:
    """Test validation help section."""

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_help(self, mock_st):
        """Test help section display."""
        from souschef.ui.pages.ansible_validation import _display_validation_help

        mock_st.expander.return_value = _ctx()

        _display_validation_help()

        mock_st.divider.assert_called_once()
        mock_st.expander.assert_called_once_with("Validation Help")
        mock_st.markdown.assert_called_once()


class TestShowAnsibleValidationPage:
    """Test main validation page entry point."""

    @patch("souschef.ui.pages.ansible_validation.st")
    @patch("souschef.ui.pages.ansible_validation._display_validation_intro")
    @patch("souschef.ui.pages.ansible_validation._render_validation_inputs")
    @patch("souschef.ui.pages.ansible_validation._display_validation_help")
    def test_show_page_without_validation(
        self, mock_help, mock_inputs, mock_intro, mock_st
    ):
        """Test page display when button not pressed."""
        from souschef.ui.pages.ansible_validation import show_ansible_validation_page

        mock_st.session_state = SessionState()
        mock_inputs.return_value = (None, "2.15", False)

        show_ansible_validation_page()

        mock_intro.assert_called_once()
        mock_inputs.assert_called_once()
        mock_help.assert_called_once()

    @patch("souschef.ui.pages.ansible_validation.st")
    @patch("souschef.ui.pages.ansible_validation._display_validation_intro")
    @patch("souschef.ui.pages.ansible_validation._render_validation_inputs")
    @patch("souschef.ui.pages.ansible_validation._display_validation_help")
    def test_show_page_no_file(self, mock_help, mock_inputs, mock_intro, mock_st):
        """Test page when button pressed but no file uploaded."""
        from souschef.ui.pages.ansible_validation import show_ansible_validation_page

        mock_st.session_state = SessionState()
        mock_inputs.return_value = (None, "2.15", True)

        show_ansible_validation_page()

        mock_st.error.assert_called_once_with("Please upload a requirements file")

    @patch("souschef.ui.pages.ansible_validation.st")
    @patch("souschef.ui.pages.ansible_validation._display_validation_intro")
    @patch("souschef.ui.pages.ansible_validation._render_validation_inputs")
    @patch("souschef.ui.pages.ansible_validation._save_uploaded_file")
    @patch("souschef.ui.pages.ansible_validation.parse_requirements_yml")
    @patch("souschef.ui.pages.ansible_validation.validate_collection_compatibility")
    @patch("souschef.ui.pages.ansible_validation._display_validation_metrics")
    @patch("souschef.ui.pages.ansible_validation._display_validation_tabs")
    @patch("souschef.ui.pages.ansible_validation._display_validation_export")
    @patch("souschef.ui.pages.ansible_validation._display_validation_help")
    def test_show_page_with_validation(
        self,
        mock_help,
        mock_export,
        mock_tabs,
        mock_metrics,
        mock_validate_compat,
        mock_parse,
        mock_save_file,
        mock_inputs,
        mock_intro,
        mock_st,
    ):
        """Test page when validation is performed successfully."""
        from souschef.ui.pages.ansible_validation import show_ansible_validation_page

        mock_st.session_state = SessionState()
        mock_file = MagicMock()
        mock_inputs.return_value = (mock_file, "2.15", True)

        mock_save_file.return_value = "/tmp/tmpdir/requirements.yml"
        mock_parse.return_value = [{"collection": "test.collection", "version": "1.0"}]
        mock_validate_compat.return_value = {
            "compatible": [{"collection": "test.collection", "version": "1.0"}],
            "incompatible": [],
            "updates_needed": [],
            "warnings": [],
        }
        mock_metrics.return_value = {
            "compatible": [{"collection": "test.collection", "version": "1.0"}],
            "incompatible": [],
            "updates_needed": [],
            "warnings": [],
        }
        mock_st.spinner.return_value = _ctx()

        show_ansible_validation_page()

        mock_parse.assert_called_once()
        mock_validate_compat.assert_called_once()
        mock_tabs.assert_called_once()
        mock_export.assert_called_once()

    @patch("souschef.ui.pages.ansible_validation.st")
    @patch("souschef.ui.pages.ansible_validation._display_validation_intro")
    @patch("souschef.ui.pages.ansible_validation._render_validation_inputs")
    @patch("souschef.ui.pages.ansible_validation._save_uploaded_file")
    @patch("souschef.ui.pages.ansible_validation.parse_requirements_yml")
    @patch("souschef.ui.pages.ansible_validation._display_validation_help")
    def test_show_page_parsing_error(
        self,
        mock_help,
        mock_parse,
        mock_save_file,
        mock_inputs,
        mock_intro,
        mock_st,
    ):
        """Test page when parsing raises an exception."""
        from souschef.ui.pages.ansible_validation import show_ansible_validation_page

        mock_st.session_state = SessionState()
        mock_file = MagicMock()
        mock_inputs.return_value = (mock_file, "2.15", True)

        mock_save_file.return_value = "/tmp/tmpdir/requirements.yml"
        mock_parse.side_effect = ValueError("Invalid format")
        mock_st.spinner.return_value = _ctx()

        show_ansible_validation_page()

        mock_st.error.assert_called_once()
        mock_st.exception.assert_called_once()

    @patch("souschef.ui.pages.ansible_validation.st")
    @patch("souschef.ui.pages.ansible_validation._display_validation_intro")
    @patch("souschef.ui.pages.ansible_validation._render_validation_inputs")
    @patch("souschef.ui.pages.ansible_validation._save_uploaded_file")
    @patch("souschef.ui.pages.ansible_validation.parse_requirements_yml")
    @patch("souschef.ui.pages.ansible_validation.validate_collection_compatibility")
    @patch("souschef.ui.pages.ansible_validation._display_validation_metrics")
    @patch("souschef.ui.pages.ansible_validation._display_validation_tabs")
    @patch("souschef.ui.pages.ansible_validation._display_validation_export")
    @patch("souschef.ui.pages.ansible_validation._display_validation_help")
    def test_show_page_validation_error(
        self,
        mock_help,
        mock_export,
        mock_tabs,
        mock_metrics,
        mock_validate_compat,
        mock_parse,
        mock_save_file,
        mock_inputs,
        mock_intro,
        mock_st,
    ):
        """Test page when validation raises an exception."""
        from souschef.ui.pages.ansible_validation import show_ansible_validation_page

        mock_st.session_state = SessionState()
        mock_file = MagicMock()
        mock_inputs.return_value = (mock_file, "2.15", True)

        mock_save_file.return_value = "/tmp/tmpdir/requirements.yml"
        mock_parse.return_value = [{"collection": "test.collection", "version": "1.0"}]
        mock_validate_compat.side_effect = RuntimeError("Validation error")
        mock_st.spinner.return_value = _ctx()

        show_ansible_validation_page()

        mock_st.error.assert_called_once()
        mock_st.exception.assert_called_once()

    @patch("souschef.ui.pages.ansible_validation.st")
    @patch("souschef.ui.pages.ansible_validation._display_validation_intro")
    @patch("souschef.ui.pages.ansible_validation._render_validation_inputs")
    @patch("souschef.ui.pages.ansible_validation._save_uploaded_file")
    @patch("souschef.ui.pages.ansible_validation.parse_requirements_yml")
    @patch("souschef.ui.pages.ansible_validation.validate_collection_compatibility")
    @patch("souschef.ui.pages.ansible_validation._display_validation_metrics")
    @patch("souschef.ui.pages.ansible_validation._display_validation_tabs")
    @patch("souschef.ui.pages.ansible_validation._display_validation_export")
    @patch("souschef.ui.pages.ansible_validation._display_validation_help")
    def test_show_page_cleanup_error(
        self,
        mock_help,
        mock_export,
        mock_tabs,
        mock_metrics,
        mock_validate_compat,
        mock_parse,
        mock_save_file,
        mock_inputs,
        mock_intro,
        mock_st,
    ):
        """Test page when cleanup raises an exception (should be silently ignored)."""
        from souschef.ui.pages.ansible_validation import show_ansible_validation_page

        mock_st.session_state = SessionState()
        mock_file = MagicMock()
        mock_inputs.return_value = (mock_file, "2.15", True)

        mock_save_file.return_value = "/tmp/tmpdir/requirements.yml"
        mock_parse.return_value = [{"collection": "test.collection", "version": "1.0"}]
        mock_validate_compat.return_value = {
            "compatible": [],
            "incompatible": [],
            "updates_needed": [],
            "warnings": [],
        }
        mock_metrics.return_value = {
            "compatible": [],
            "incompatible": [],
            "updates_needed": [],
            "warnings": [],
        }
        mock_st.spinner.return_value = _ctx()

        # Mock shutil.rmtree to raise an exception
        with patch("souschef.ui.pages.ansible_validation.shutil.rmtree") as mock_rmtree:
            mock_rmtree.side_effect = Exception("Cleanup failed")

            show_ansible_validation_page()

        # Should not raise, and validation should still complete
        mock_tabs.assert_called_once()
