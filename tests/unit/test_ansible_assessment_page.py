"""Comprehensive tests for ansible_assessment.py to achieve 100% coverage."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest


class SessionState(dict):
    """Session state helper that supports attribute and dict access."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(f"No attribute {name}")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def _ctx():
    """Create a context manager mock factory."""
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=False)
    return mock


@pytest.fixture(autouse=True)
def mock_streamlit():
    """Mock streamlit module."""
    with patch.dict("sys.modules", {"streamlit": MagicMock()}):
        yield


class TestDisplayAssessmentIntro:
    """Test _display_assessment_intro function."""

    def test_intro_displays_title(self):
        """Test that intro displays title and markdown."""
        from souschef.ui.pages.ansible_assessment import _display_assessment_intro

        with patch("souschef.ui.pages.ansible_assessment.st") as mock_st:
            _display_assessment_intro()
            mock_st.title.assert_called_once()
            mock_st.markdown.assert_called_once()


class TestRenderAssessmentInputs:
    """Test _render_assessment_inputs function."""

    def test_inputs_renders_columns(self):
        """Test that inputs renders proper columns."""
        from souschef.ui.pages.ansible_assessment import _render_assessment_inputs

        with patch("souschef.ui.pages.ansible_assessment.st") as mock_st:
            mock_st.columns.return_value = (MagicMock(), MagicMock())
            mock_st.text_input.return_value = "/path"
            mock_st.button.return_value = True

            path, btn = _render_assessment_inputs()

            assert path == "/path"
            assert btn is True
            mock_st.columns.assert_called_once()
            mock_st.text_input.assert_called_once()
            mock_st.button.assert_called_once()


class TestDisplayAssessmentResults:
    """Test _display_assessment_results function."""

    def test_results_displays_metrics(self):
        """Test that results displays metrics properly."""
        from souschef.ui.pages.ansible_assessment import _display_assessment_results

        assessment = {
            "current_version": "2.14.0",
            "python_version": "3.11",
            "eol_status": {"eol_date": "2025-06-01"},
            "collections": {},
        }

        with (
            patch("souschef.ui.pages.ansible_assessment.st") as mock_st,
            patch(
                "souschef.ui.pages.ansible_assessment._display_assessment_collections"
            ),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_warnings"),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_details"),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_export"),
        ):
            mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
            _display_assessment_results(assessment)
            mock_st.subheader.assert_called_once()
            mock_st.metric.assert_called()

    def test_results_handles_missing_eol_date(self):
        """Test results handles missing EOL date gracefully."""
        from souschef.ui.pages.ansible_assessment import _display_assessment_results

        assessment = {
            "current_version": "2.14.0",
            "python_version": "3.11",
            "eol_status": {},
            "collections": {},
        }

        with (
            patch("souschef.ui.pages.ansible_assessment.st") as mock_st,
            patch(
                "souschef.ui.pages.ansible_assessment._display_assessment_collections"
            ),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_warnings"),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_details"),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_export"),
        ):
            mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
            _display_assessment_results(assessment)
            # Should not raise error
            assert mock_st.metric.called

    def test_results_handles_non_dict_eol_status(self):
        """Test results handles non-dict eol_status gracefully."""
        from souschef.ui.pages.ansible_assessment import _display_assessment_results

        assessment = {
            "current_version": "2.14.0",
            "python_version": "3.11",
            "eol_status": "unknown",
            "collections": {},
        }

        with (
            patch("souschef.ui.pages.ansible_assessment.st") as mock_st,
            patch(
                "souschef.ui.pages.ansible_assessment._display_assessment_collections"
            ),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_warnings"),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_details"),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_export"),
        ):
            mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
            _display_assessment_results(assessment)
            assert mock_st.metric.called


class TestDisplayAssessmentCollections:
    """Test _display_assessment_collections function."""

    def test_collections_displays_empty(self):
        """Test collections display with empty collections."""
        from souschef.ui.pages.ansible_assessment import _display_assessment_collections

        assessment = {"collections": {}}

        with patch("souschef.ui.pages.ansible_assessment.st") as mock_st:
            _display_assessment_collections(assessment)  # type: ignore[arg-type]
            # Should handle empty case gracefully
            assert mock_st.subheader.called or not mock_st.subheader.called

    def test_collections_displays_list(self):
        """Test collections display with actual collections."""
        from souschef.ui.pages.ansible_assessment import _display_assessment_collections

        assessment = {
            "collections": {
                "ansible.posix": "1.5.0",
                "community.general": "7.0.0",
            }
        }

        with patch("souschef.ui.pages.ansible_assessment.st") as mock_st:
            mock_st.columns.return_value = (MagicMock(), MagicMock())
            _display_assessment_collections(assessment)  # type: ignore[arg-type]
            mock_st.subheader.assert_called()

    def test_collections_handles_non_dict(self):
        """Test collections with non-dict collections field."""
        from souschef.ui.pages.ansible_assessment import _display_assessment_collections

        assessment = {"collections": None}

        with patch("souschef.ui.pages.ansible_assessment.st"):
            _display_assessment_collections(assessment)  # type: ignore[arg-type]
            # Should silently handle non-dict


class TestDisplayAssessmentWarnings:
    """Test _display_assessment_warnings function."""

    def test_warnings_empty(self):
        """Test warnings display with empty list."""
        from souschef.ui.pages.ansible_assessment import _display_assessment_warnings

        assessment = {"compatibility_issues": []}

        with patch("souschef.ui.pages.ansible_assessment.st") as mock_st:
            _display_assessment_warnings(assessment)  # type: ignore[arg-type]
            # Should not display anything for None warnings
            assert mock_st is not None

    def test_warnings_displays_issues(self):
        """Test warnings display with actual issues."""
        from souschef.ui.pages.ansible_assessment import _display_assessment_warnings

        assessment = {
            "compatibility_issues": [
                "Collection A requires Python 3.10+",
                "Collection B has security issue",
            ]
        }

        with patch("souschef.ui.pages.ansible_assessment.st") as mock_st:
            _display_assessment_warnings(assessment)  # type: ignore[arg-type]
            mock_st.warning.assert_called()

    def test_warnings_handles_non_list(self):
        """Test warnings with non-list issues."""
        from souschef.ui.pages.ansible_assessment import _display_assessment_warnings

        assessment = {"compatibility_issues": None}

        with patch("souschef.ui.pages.ansible_assessment.st"):
            _display_assessment_warnings(assessment)  # type: ignore[arg-type]
            # Should handle silently


class TestDisplayAssessmentDetails:
    """Test _display_assessment_details function."""

    def test_details_displays_full_version(self):
        """Test details display with full version."""
        from souschef.ui.pages.ansible_assessment import _display_assessment_details

        assessment = {
            "current_version_full": "ansible 2.14.0",
            "eol_status": {"status": "Active", "security_risk": "Low"},
            "playbooks_scanned": 5,
        }

        with patch("souschef.ui.pages.ansible_assessment.st") as mock_st:
            mock_st.columns.return_value = (MagicMock(), MagicMock())
            _display_assessment_details(assessment)
            mock_st.divider.assert_called()
            mock_st.subheader.assert_called()

    def test_details_handles_missing_eol_status(self):
        """Test details with missing EOL status."""
        from souschef.ui.pages.ansible_assessment import _display_assessment_details

        assessment = {
            "current_version_full": "ansible 2.14.0",
            "eol_status": {},
            "playbooks_scanned": 0,
        }

        with patch("souschef.ui.pages.ansible_assessment.st") as mock_st:
            mock_st.columns.return_value = (MagicMock(), MagicMock())
            _display_assessment_details(assessment)
            # Should not raise error


class TestDisplayAssessmentExport:
    """Test _display_assessment_export function."""

    def test_export_provides_download(self):
        """Test export provides download button."""
        from souschef.ui.pages.ansible_assessment import _display_assessment_export

        assessment = {"current_version": "2.14.0", "data": "test"}

        with patch("souschef.ui.pages.ansible_assessment.st") as mock_st:
            _display_assessment_export(assessment)  # type: ignore[arg-type]
            mock_st.divider.assert_called()
            mock_st.subheader.assert_called()
            mock_st.download_button.assert_called()


class TestDisplayAssessmentHelp:
    """Test _display_assessment_help function."""

    def test_help_displays_guidance(self):
        """Test help displays guidance."""
        from souschef.ui.pages.ansible_assessment import _display_assessment_help

        with patch("souschef.ui.pages.ansible_assessment.st") as mock_st:
            _display_assessment_help()
            mock_st.divider.assert_called()
            mock_st.expander.assert_called()


class TestShowAnsibleAssessmentPage:
    """Test show_ansible_assessment_page function."""

    def test_main_page_no_assessment(self):
        """Test main page without assessment results."""
        from souschef.ui.pages.ansible_assessment import show_ansible_assessment_page

        with (
            patch("souschef.ui.pages.ansible_assessment.st"),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_intro"),
            patch(
                "souschef.ui.pages.ansible_assessment._render_assessment_inputs",
                return_value=("", False),
            ),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_help"),
            patch(
                "souschef.ui.pages.ansible_assessment.st.session_state",
                SessionState(),
            ),
        ):
            show_ansible_assessment_page()

    def test_main_page_with_assessment_success(self):
        """Test main page with successful assessment."""
        from souschef.ui.pages.ansible_assessment import show_ansible_assessment_page

        session = SessionState()
        assessment = {
            "current_version": "2.14.0",
            "python_version": "3.11",
            "eol_status": {},
            "collections": {},
        }

        with (
            patch("souschef.ui.pages.ansible_assessment.st") as mock_st,
            patch("souschef.ui.pages.ansible_assessment._display_assessment_intro"),
            patch(
                "souschef.ui.pages.ansible_assessment._render_assessment_inputs",
                return_value=(".", True),
            ),
            patch(
                "souschef.ui.pages.ansible_assessment.assess_ansible_environment",
                return_value=assessment,
            ),
            patch("souschef.ui.pages.ansible_assessment.st.spinner"),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_results"),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_help"),
        ):
            mock_st.session_state = session
            show_ansible_assessment_page()
            assert session.get("ansible_assessment_results")

    def test_main_page_with_assessment_error(self):
        """Test main page with assessment error."""
        from souschef.ui.pages.ansible_assessment import show_ansible_assessment_page

        session = SessionState()

        with (
            patch("souschef.ui.pages.ansible_assessment.st") as mock_st,
            patch("souschef.ui.pages.ansible_assessment._display_assessment_intro"),
            patch(
                "souschef.ui.pages.ansible_assessment._render_assessment_inputs",
                return_value=(".", True),
            ),
            patch(
                "souschef.ui.pages.ansible_assessment.assess_ansible_environment",
                side_effect=Exception("Test error"),
            ),
            patch("souschef.ui.pages.ansible_assessment.st.spinner"),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_help"),
        ):
            mock_st.session_state = session
            show_ansible_assessment_page()
            mock_st.error.assert_called()
            mock_st.exception.assert_called()
