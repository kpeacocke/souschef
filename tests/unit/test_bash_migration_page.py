"""Tests for the Bash Migration UI page to achieve 100% coverage."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest


class SessionState(dict):
    """Session state helper that supports attribute and dict access."""

    def __getattr__(self, name: str) -> Any:
        if name in self:
            return self[name]
        raise AttributeError(f"No attribute {name}")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def _ctx() -> MagicMock:
    """Create a context manager mock factory."""
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=False)
    return mock


@pytest.fixture(autouse=True)
def mock_streamlit() -> Any:
    """Mock streamlit module so tests run without Streamlit installed."""
    with patch.dict("sys.modules", {"streamlit": MagicMock()}):
        yield


# ---------------------------------------------------------------------------
# show_bash_migration_page
# ---------------------------------------------------------------------------


class TestShowBashMigrationPage:
    """Test the main page entry point."""

    def test_show_page_calls_title(self) -> None:
        """show_bash_migration_page calls st.title."""
        from souschef.ui.pages.bash_migration import show_bash_migration_page

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.tabs.return_value = (_ctx(), _ctx())
            with (
                patch("souschef.ui.pages.bash_migration._render_paste_tab"),
                patch("souschef.ui.pages.bash_migration._render_upload_tab"),
            ):
                show_bash_migration_page()
            mock_st.title.assert_called_once()

    def test_show_page_calls_markdown(self) -> None:
        """show_bash_migration_page calls st.markdown."""
        from souschef.ui.pages.bash_migration import show_bash_migration_page

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.tabs.return_value = (_ctx(), _ctx())
            with (
                patch("souschef.ui.pages.bash_migration._render_paste_tab"),
                patch("souschef.ui.pages.bash_migration._render_upload_tab"),
            ):
                show_bash_migration_page()
            mock_st.markdown.assert_called()


# ---------------------------------------------------------------------------
# _render_paste_tab
# ---------------------------------------------------------------------------


class TestRenderPasteTab:
    """Test the paste-script tab rendering."""

    def test_paste_tab_no_action(self) -> None:
        """With no button clicked nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_paste_tab

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.text_area.return_value = ""
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            mock_st.button.return_value = False
            _render_paste_tab()

    def test_paste_tab_parse_with_content(self) -> None:
        """Clicking Analyse Script with content calls _display_parse_results."""
        from souschef.ui.pages.bash_migration import _render_paste_tab

        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration._display_parse_results"
            ) as mock_display,
        ):
            mock_st.text_area.return_value = "apt-get install nginx\n"
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            # First button (Analyse Script) returns True, rest False
            mock_st.button.side_effect = [True, False, False]
            _render_paste_tab()
            mock_display.assert_called_once()

    def test_paste_tab_convert_with_content(self) -> None:
        """Clicking Convert to Ansible with content calls _display_conversion_results."""
        from souschef.ui.pages.bash_migration import _render_paste_tab

        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration._display_conversion_results"
            ) as mock_convert,
        ):
            mock_st.text_area.return_value = "apt-get install nginx\n"
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            # First button False, second True, third False
            mock_st.button.side_effect = [False, True, False]
            _render_paste_tab()
            mock_convert.assert_called_once()

    def test_paste_tab_parse_without_content_shows_warning(self) -> None:
        """Clicking Analyse Script without content shows a warning."""
        from souschef.ui.pages.bash_migration import _render_paste_tab

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.text_area.return_value = ""
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            mock_st.button.side_effect = [True, False, False]
            _render_paste_tab()
            mock_st.warning.assert_called_once()

    def test_paste_tab_convert_without_content_shows_warning(self) -> None:
        """Clicking Convert to Ansible without content shows a warning."""
        from souschef.ui.pages.bash_migration import _render_paste_tab

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.text_area.return_value = ""
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            mock_st.button.side_effect = [False, True, False]
            _render_paste_tab()
            mock_st.warning.assert_called_once()


# ---------------------------------------------------------------------------
# _render_upload_tab
# ---------------------------------------------------------------------------


class TestRenderUploadTab:
    """Test the file-upload tab rendering."""

    def test_upload_tab_no_file(self) -> None:
        """With no uploaded file, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_upload_tab

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.file_uploader.return_value = None
            _render_upload_tab()

    def test_upload_tab_file_uploaded_shows_code(self) -> None:
        """Uploaded file shows code block."""
        from souschef.ui.pages.bash_migration import _render_upload_tab

        mock_file = MagicMock()
        mock_file.read.return_value = b"apt-get install nginx\n"
        mock_file.name = "deploy.sh"

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.file_uploader.return_value = mock_file
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            mock_st.button.return_value = False
            _render_upload_tab()
            mock_st.code.assert_called_once()

    def test_upload_tab_parse_uploaded_file(self) -> None:
        """Clicking Analyse Uploaded Script calls _display_parse_results."""
        from souschef.ui.pages.bash_migration import _render_upload_tab

        mock_file = MagicMock()
        mock_file.read.return_value = b"apt-get install nginx\n"
        mock_file.name = "deploy.sh"

        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration._display_parse_results"
            ) as mock_display,
        ):
            mock_st.file_uploader.return_value = mock_file
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            mock_st.button.side_effect = [True, False, False]
            _render_upload_tab()
            mock_display.assert_called_once()

    def test_upload_tab_convert_uploaded_file(self) -> None:
        """Clicking Convert Uploaded Script calls _display_conversion_results."""
        from souschef.ui.pages.bash_migration import _render_upload_tab

        mock_file = MagicMock()
        mock_file.read.return_value = b"apt-get install nginx\n"
        mock_file.name = "deploy.sh"

        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration._display_conversion_results"
            ) as mock_convert,
        ):
            mock_st.file_uploader.return_value = mock_file
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            mock_st.button.side_effect = [False, True, False]
            _render_upload_tab()
            mock_convert.assert_called_once()


# ---------------------------------------------------------------------------
# _display_parse_results
# ---------------------------------------------------------------------------


class TestDisplayParseResults:
    """Test the parse results rendering."""

    def test_display_parse_results_calls_subheader(self) -> None:
        """_display_parse_results calls st.subheader."""
        from souschef.ui.pages.bash_migration import _display_parse_results

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            _display_parse_results("apt-get install nginx\n")
            mock_st.subheader.assert_called()

    def test_display_parse_results_with_packages(self) -> None:
        """_display_parse_results renders packages section."""
        from souschef.ui.pages.bash_migration import _display_parse_results

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            mock_st.expander.return_value = _ctx()
            _display_parse_results("apt-get install -y nginx\n")
            # Should have called subheader at least for "Analysis Results"
            mock_st.subheader.assert_called()

    def test_display_parse_results_with_services(self) -> None:
        """_display_parse_results renders services section."""
        from souschef.ui.pages.bash_migration import _display_parse_results

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            mock_st.expander.return_value = _ctx()
            _display_parse_results("systemctl start nginx\n")
            mock_st.subheader.assert_called()

    def test_display_parse_results_with_downloads(self) -> None:
        """_display_parse_results renders downloads section."""
        from souschef.ui.pages.bash_migration import _display_parse_results

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            mock_st.expander.return_value = _ctx()
            _display_parse_results("curl -o /tmp/f.tgz https://example.com/f.tgz\n")
            mock_st.subheader.assert_called()

    def test_display_parse_results_with_file_writes(self) -> None:
        """_display_parse_results renders file writes section."""
        from souschef.ui.pages.bash_migration import _display_parse_results

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            mock_st.expander.return_value = _ctx()
            _display_parse_results("cat <<EOF > /etc/nginx.conf\nfoo\nEOF\n")
            mock_st.subheader.assert_called()

    def test_display_parse_results_with_idempotency_risks(self) -> None:
        """_display_parse_results renders idempotency risks."""
        from souschef.ui.pages.bash_migration import _display_parse_results

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            _display_parse_results("apt-get install nginx\n")
            # warning called for idempotency risk
            mock_st.warning.assert_called()

    def test_display_parse_results_with_shell_fallbacks(self) -> None:
        """_display_parse_results renders shell fallbacks section."""
        from souschef.ui.pages.bash_migration import _display_parse_results

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            mock_st.expander.return_value = _ctx()
            _display_parse_results("custom-unknown-cmd --flag\n")
            mock_st.info.assert_called()


# ---------------------------------------------------------------------------
# _render_summary_metrics
# ---------------------------------------------------------------------------


class TestRenderSummaryMetrics:
    """Test the summary metrics display."""

    def test_renders_four_metrics(self) -> None:
        """Renders metrics for packages, services, file_writes, downloads."""
        from souschef.ui.pages.bash_migration import _render_summary_metrics

        ir = {
            "packages": [{}],
            "services": [{}],
            "file_writes": [{}],
            "downloads": [{}],
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
            _render_summary_metrics(ir)
            assert mock_st.columns.called


# ---------------------------------------------------------------------------
# _render_packages
# ---------------------------------------------------------------------------


class TestRenderPackages:
    """Test the packages rendering helper."""

    def test_no_packages_renders_nothing(self) -> None:
        """With no packages, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_packages

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_packages({"packages": []})
            mock_st.subheader.assert_not_called()

    def test_packages_renders_expander(self) -> None:
        """With packages, expander is rendered."""
        from souschef.ui.pages.bash_migration import _render_packages

        ir = {
            "packages": [
                {
                    "line": 1,
                    "manager": "apt",
                    "packages": ["nginx"],
                    "raw": "apt-get install nginx",
                    "ansible_module": "ansible.builtin.apt",
                    "confidence": 0.9,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_packages(ir)
            mock_st.subheader.assert_called_once()


# ---------------------------------------------------------------------------
# _render_services
# ---------------------------------------------------------------------------


class TestRenderServices:
    """Test the services rendering helper."""

    def test_no_services_renders_nothing(self) -> None:
        """With no services, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_services

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_services({"services": []})
            mock_st.subheader.assert_not_called()

    def test_services_renders_expander(self) -> None:
        """With services, expander is rendered."""
        from souschef.ui.pages.bash_migration import _render_services

        ir = {
            "services": [
                {
                    "line": 2,
                    "manager": "systemctl",
                    "action": "start",
                    "name": "nginx",
                    "raw": "systemctl start nginx",
                    "confidence": 0.95,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_services(ir)
            mock_st.subheader.assert_called_once()


# ---------------------------------------------------------------------------
# _render_file_writes
# ---------------------------------------------------------------------------


class TestRenderFileWrites:
    """Test the file writes rendering helper."""

    def test_no_file_writes_renders_nothing(self) -> None:
        """With no file writes, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_file_writes

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_file_writes({"file_writes": []})
            mock_st.subheader.assert_not_called()

    def test_file_writes_renders_expander(self) -> None:
        """With file writes, expander is rendered."""
        from souschef.ui.pages.bash_migration import _render_file_writes

        ir = {
            "file_writes": [
                {
                    "line": 3,
                    "destination": "/etc/app.conf",
                    "raw": "cat <<EOF > /etc/app.conf",
                    "confidence": 0.75,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_file_writes(ir)
            mock_st.subheader.assert_called_once()


# ---------------------------------------------------------------------------
# _render_downloads
# ---------------------------------------------------------------------------


class TestRenderDownloads:
    """Test the downloads rendering helper."""

    def test_no_downloads_renders_nothing(self) -> None:
        """With no downloads, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_downloads

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_downloads({"downloads": []})
            mock_st.subheader.assert_not_called()

    def test_downloads_renders_expander(self) -> None:
        """With downloads, expander is rendered."""
        from souschef.ui.pages.bash_migration import _render_downloads

        ir = {
            "downloads": [
                {
                    "line": 4,
                    "tool": "curl",
                    "url": "https://example.com/f.tgz",
                    "raw": "curl -o /tmp/f.tgz https://example.com/f.tgz",
                    "confidence": 0.7,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_downloads(ir)
            mock_st.subheader.assert_called_once()

    def test_downloads_without_url_shows_fallback_text(self) -> None:
        """Downloads without URL show fallback text in expander."""
        from souschef.ui.pages.bash_migration import _render_downloads

        ir = {
            "downloads": [
                {
                    "line": 5,
                    "tool": "curl",
                    "url": "",
                    "raw": "curl --some-flag",
                    "confidence": 0.5,
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_downloads(ir)
            mock_st.subheader.assert_called_once()


# ---------------------------------------------------------------------------
# _render_idempotency_risks
# ---------------------------------------------------------------------------


class TestRenderIdempotencyRisks:
    """Test the idempotency risks rendering helper."""

    def test_no_risks_renders_nothing(self) -> None:
        """With no risks, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_idempotency_risks

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_idempotency_risks({"idempotency_risks": []})
            mock_st.subheader.assert_not_called()

    def test_risks_renders_warnings(self) -> None:
        """With risks, warning is called."""
        from souschef.ui.pages.bash_migration import _render_idempotency_risks

        ir = {
            "idempotency_risks": [
                {
                    "line": 1,
                    "type": "raw_download",
                    "suggestion": "Use checksum",
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_idempotency_risks(ir)
            mock_st.warning.assert_called_once()


# ---------------------------------------------------------------------------
# _render_shell_fallbacks
# ---------------------------------------------------------------------------


class TestRenderShellFallbacks:
    """Test the shell fallbacks rendering helper."""

    def test_no_fallbacks_renders_nothing(self) -> None:
        """With no fallbacks, nothing is rendered."""
        from souschef.ui.pages.bash_migration import _render_shell_fallbacks

        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            _render_shell_fallbacks({"shell_fallbacks": []})
            mock_st.subheader.assert_not_called()

    def test_fallbacks_renders_info(self) -> None:
        """With fallbacks, info message and expander are rendered."""
        from souschef.ui.pages.bash_migration import _render_shell_fallbacks

        ir = {
            "shell_fallbacks": [
                {
                    "line": 6,
                    "raw": "custom-cmd --flag",
                    "warning": "No mapping found",
                }
            ]
        }
        with patch("souschef.ui.pages.bash_migration.st") as mock_st:
            mock_st.expander.return_value = _ctx()
            _render_shell_fallbacks(ir)
            mock_st.info.assert_called_once()


# ---------------------------------------------------------------------------
# _display_conversion_results
# ---------------------------------------------------------------------------


class TestDisplayConversionResults:
    """Test the conversion results display."""

    def test_successful_conversion_shows_code(self) -> None:
        """Successful conversion shows playbook code."""
        import json as _json

        from souschef.ui.pages.bash_migration import _display_conversion_results

        mock_response = _json.dumps(
            {
                "status": "success",
                "playbook_yaml": "---\n- name: test\n",
                "warnings": [],
                "idempotency_report": {"total_risks": 0, "non_idempotent_tasks": 0, "suggestions": []},
                "tasks": [],
                "script_path": "test.sh",
            }
        )

        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration.convert_bash_content_to_ansible",
                return_value=mock_response,
            ),
        ):
            mock_st.columns.return_value = (_ctx(), _ctx())
            _display_conversion_results("apt-get install nginx\n")
            mock_st.code.assert_called_once()

    def test_conversion_error_shows_error(self) -> None:
        """Conversion error shows st.error."""
        import json as _json

        from souschef.ui.pages.bash_migration import _display_conversion_results

        mock_response = _json.dumps(
            {"status": "error", "error": "File not found"}
        )

        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration.convert_bash_content_to_ansible",
                return_value=mock_response,
            ),
        ):
            _display_conversion_results("irrelevant")
            mock_st.error.assert_called_once()

    def test_conversion_with_warnings_shows_warnings(self) -> None:
        """Conversion with warnings renders warning section."""
        import json as _json

        from souschef.ui.pages.bash_migration import _display_conversion_results

        mock_response = _json.dumps(
            {
                "status": "success",
                "playbook_yaml": "---\n",
                "warnings": ["Line 1: some warning"],
                "idempotency_report": {"total_risks": 0, "non_idempotent_tasks": 0, "suggestions": []},
                "tasks": [],
                "script_path": "test.sh",
            }
        )

        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration.convert_bash_content_to_ansible",
                return_value=mock_response,
            ),
        ):
            _display_conversion_results("custom-cmd\n")
            # Should have called warning for the warnings list
            mock_st.warning.assert_called()

    def test_conversion_with_risks_shows_report(self) -> None:
        """Conversion with idempotency risks renders report section."""
        import json as _json

        from souschef.ui.pages.bash_migration import _display_conversion_results

        mock_response = _json.dumps(
            {
                "status": "success",
                "playbook_yaml": "---\n",
                "warnings": [],
                "idempotency_report": {
                    "total_risks": 2,
                    "non_idempotent_tasks": 1,
                    "risks": [],
                    "suggestions": ["Use checksum"],
                },
                "tasks": [],
                "script_path": "test.sh",
            }
        )

        with (
            patch("souschef.ui.pages.bash_migration.st") as mock_st,
            patch(
                "souschef.ui.pages.bash_migration.convert_bash_content_to_ansible",
                return_value=mock_response,
            ),
        ):
            mock_st.columns.return_value = (_ctx(), _ctx())
            _display_conversion_results("curl url\n")
            mock_st.subheader.assert_called()
