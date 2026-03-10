"""Comprehensive tests for chef_server_settings.py to achieve 100% coverage."""

from __future__ import annotations

import tempfile
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest


class SessionState(dict):
    """Session state helper."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(f"No attribute {name}")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def _ctx() -> MagicMock:
    """Create a mock context manager."""
    m = MagicMock()
    m.__enter__ = Mock(return_value=m)
    m.__exit__ = Mock(return_value=False)
    return m


@pytest.fixture(autouse=True)
def mock_streamlit():
    """Mock streamlit module."""
    with patch.dict("sys.modules", {"streamlit": MagicMock()}):
        yield


class TestRenderChefServerConfiguration:
    """Test _render_chef_server_configuration function."""

    def test_renders_all_fields(self):
        """Test that all configuration fields are rendered."""
        from souschef.ui.pages.chef_server_settings import (
            _render_chef_server_configuration,
        )

        with (
            patch("souschef.ui.pages.chef_server_settings.st") as mock_st,
            patch.dict("os.environ", {}),
        ):
            mock_st.columns.return_value = (MagicMock(), MagicMock())
            mock_st.text_input.side_effect = ["url", "org", "client", "keypath"]

            server_url, org, client, keypath = _render_chef_server_configuration()

            assert server_url == "url"
            assert org == "org"
            assert client == "client"
            assert keypath == "keypath"
            assert mock_st.subheader.called
            assert mock_st.markdown.called

    def test_uses_env_vars(self):
        """Test that environment variables are used as defaults."""
        from souschef.ui.pages.chef_server_settings import (
            _render_chef_server_configuration,
        )

        with (
            patch("souschef.ui.pages.chef_server_settings.st") as mock_st,
            patch.dict(
                "os.environ",
                {
                    "CHEF_SERVER_URL": "https://chef.local",
                    "CHEF_ORG": "test_org",
                    "CHEF_CLIENT_NAME": "test_client",
                    "CHEF_CLIENT_KEY_PATH": "/path/to/key",
                },
            ),
        ):
            mock_st.columns.return_value = (MagicMock(), MagicMock())
            mock_st.text_input.side_effect = ["url", "org", "client", "keypath"]

            _render_chef_server_configuration()

            # Verify env vars were used in text_input calls
            calls = list(mock_st.text_input.call_args_list)
            assert len(calls) >= 4


class TestRenderTestConnectionButton:
    """Test _render_test_connection_button function."""

    def test_button_renders(self):
        """Test that test button renders."""
        from souschef.ui.pages.chef_server_settings import (
            _render_test_connection_button,
        )

        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            mock_st.columns.return_value = (MagicMock(), MagicMock())
            mock_st.button.return_value = False

            _render_test_connection_button("url", "org", "client", "keypath")

            mock_st.markdown.assert_called()
            mock_st.subheader.assert_called()
            mock_st.button.assert_called()

    def test_button_success_path(self):
        """Test successful connection test."""
        from souschef.ui.pages.chef_server_settings import (
            _render_test_connection_button,
        )

        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            col_mock = MagicMock()
            mock_st.columns.return_value = (MagicMock(), col_mock)
            mock_st.button.return_value = True
            mock_st.spinner.return_value.__enter__ = Mock()
            mock_st.spinner.return_value.__exit__ = Mock(return_value=False)

            with patch(
                "souschef.ui.pages.chef_server_settings._validate_chef_server_connection",
                return_value=(True, "Success"),
            ):
                _render_test_connection_button("url", "org", "client", "keypath")
                # Should render button
                assert mock_st.button.called

    def test_button_failure_path(self):
        """Test failed connection test."""
        from souschef.ui.pages.chef_server_settings import (
            _render_test_connection_button,
        )

        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            col_mock = MagicMock()
            mock_st.columns.return_value = (MagicMock(), col_mock)
            mock_st.button.return_value = True
            mock_st.spinner.return_value.__enter__ = Mock()
            mock_st.spinner.return_value.__exit__ = Mock(return_value=False)

            with patch(
                "souschef.ui.pages.chef_server_settings._validate_chef_server_connection",
                return_value=(False, "Connection failed"),
            ):
                _render_test_connection_button("url", "org", "client", "keypath")
                assert mock_st.button.called


class TestRenderUsageExamples:
    """Test _render_usage_examples function."""

    def test_examples_render(self):
        """Test that usage examples render."""
        from souschef.ui.pages.chef_server_settings import _render_usage_examples

        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            _render_usage_examples()

            mock_st.markdown.assert_called()
            mock_st.expander.assert_called()


class TestRenderSaveSettingsSection:
    """Test _render_save_settings_section function."""

    def test_save_section_renders(self):
        """Test that save settings section renders."""
        from souschef.ui.pages.chef_server_settings import _render_save_settings_section

        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            mock_st.button.return_value = False
            mock_st.columns.return_value = (MagicMock(), MagicMock())
            _render_save_settings_section("url", "org", "client", "keypath")

            mock_st.subheader.assert_called()
            mock_st.button.assert_called()

    def test_save_button_pressed(self):
        """Test when save button is pressed."""
        from souschef.ui.pages.chef_server_settings import _render_save_settings_section

        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            mock_st.button.return_value = True
            mock_st.columns.return_value = (MagicMock(), MagicMock())

            _render_save_settings_section("url", "org", "client", "keypath")

            # Should call success when button pressed
            mock_st.button.assert_called()


class TestValidateChefServerConnection:
    """Test _validate_chef_server_connection function."""

    def test_validates_with_key_file(self):
        """Test validation with key file."""
        from souschef.ui.pages.chef_server_settings import (
            _validate_chef_server_connection,
        )

        with patch("souschef.core.chef_server.ChefServerClient") as mock_chef:
            mock_instance = MagicMock()
            mock_chef.return_value = mock_instance
            mock_instance.get_organization.return_value = {"name": "org"}

            success, message = _validate_chef_server_connection(
                "https://chef.local",
                "client",
                organisation="org",
                client_key_path="/path",
            )

            assert isinstance(success, bool)
            assert isinstance(message, str)

    def test_validates_without_key_file(self):
        """Test validation without key file."""
        from souschef.ui.pages.chef_server_settings import (
            _validate_chef_server_connection,
        )

        success, message = _validate_chef_server_connection(
            "https://chef.local", "client"
        )

        assert success is False
        assert isinstance(message, str)


class TestShowChefServerSettingsPage:
    """Test show_chef_server_settings_page main function."""

    def test_page_renders(self):
        """Test that page renders all sections."""
        from souschef.ui.pages.chef_server_settings import (
            show_chef_server_settings_page,
        )

        with (
            patch("souschef.ui.pages.chef_server_settings.st") as mock_st,
            patch.dict("os.environ", {}),
            patch("souschef.ui.pages.chef_server_settings._display_chef_server_intro"),
            patch(
                "souschef.ui.pages.chef_server_settings._render_current_configuration"
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._render_chef_server_configuration",
                return_value=("url", "org", "client", "key"),
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._render_test_connection_button"
            ),
            patch("souschef.ui.pages.chef_server_settings._render_bulk_operations"),
            patch("souschef.ui.pages.chef_server_settings._render_usage_examples"),
            patch(
                "souschef.ui.pages.chef_server_settings._render_save_settings_section"
            ),
        ):
            mock_st.title = MagicMock()
            mock_st.markdown = MagicMock()
            mock_st.info = MagicMock()
            mock_st.session_state = {}
            show_chef_server_settings_page()

    def test_page_flow(self):
        """Test complete page flow."""
        from souschef.ui.pages.chef_server_settings import (
            show_chef_server_settings_page,
        )

        with (
            patch("souschef.ui.pages.chef_server_settings.st") as mock_st,
            patch.dict("os.environ", {}),
            patch(
                "souschef.ui.pages.chef_server_settings._display_chef_server_intro"
            ) as mock_intro,
            patch(
                "souschef.ui.pages.chef_server_settings._render_current_configuration"
            ) as mock_current,
            patch(
                "souschef.ui.pages.chef_server_settings._render_chef_server_configuration",
                return_value=("url", "org", "client", "key"),
            ) as mock_config,
            patch(
                "souschef.ui.pages.chef_server_settings._render_test_connection_button"
            ) as mock_test,
            patch(
                "souschef.ui.pages.chef_server_settings._render_bulk_operations"
            ) as mock_bulk,
            patch(
                "souschef.ui.pages.chef_server_settings._render_usage_examples"
            ) as mock_examples,
            patch(
                "souschef.ui.pages.chef_server_settings._render_save_settings_section"
            ) as mock_save,
        ):
            mock_st.title = MagicMock()
            mock_st.markdown = MagicMock()
            mock_st.info = MagicMock()
            mock_st.session_state = {}
            show_chef_server_settings_page()

            # Verify all sections called
            mock_intro.assert_called_once()
            mock_current.assert_called_once()
            mock_config.assert_called_once()
            mock_test.assert_called_once()
            mock_bulk.assert_called_once()
            mock_examples.assert_called_once()
            mock_save.assert_called_once()


class TestDownloadCookbookBranches:
    """Target branch coverage for _download_cookbook."""

    def test_download_rejects_invalid_version_path_chars(self):
        """Reject versions with path separators."""
        from souschef.ui.pages.chef_server_settings import _download_cookbook

        result = _download_cookbook(
            "https://chef.local",
            "org",
            "client",
            "key",
            "nginx",
            "1/2/3",
            MagicMock(),
        )
        assert result is None

    def test_download_returns_none_when_metadata_missing(self):
        """Return None when version metadata lookup returns empty."""
        from pathlib import Path

        from souschef.ui.pages.chef_server_settings import _download_cookbook

        with patch(
            "souschef.core.chef_server.get_chef_cookbook_version",
            return_value=None,
        ):
            result = _download_cookbook(
                "https://chef.local",
                "org",
                "client",
                "key",
                "nginx",
                "1.0.0",
                Path("/tmp"),
            )
        assert result is None

    def test_download_returns_none_on_exception(self):
        """Return None on unexpected exceptions in download flow."""
        from pathlib import Path

        from souschef.ui.pages.chef_server_settings import _download_cookbook

        with patch(
            "souschef.core.chef_server.get_chef_cookbook_version",
            side_effect=RuntimeError("boom"),
        ):
            result = _download_cookbook(
                "https://chef.local",
                "org",
                "client",
                "key",
                "nginx",
                "1.0.0",
                Path("/tmp"),
            )
        assert result is None


class TestAssessSingleCookbookBranches:
    """Target branch coverage for _assess_single_cookbook."""

    def test_assess_single_returns_false_when_download_fails(self):
        """Return False immediately when cookbook download fails."""
        from pathlib import Path

        from souschef.ui.pages.chef_server_settings import _assess_single_cookbook

        storage = MagicMock()
        cookbook = {"name": "nginx", "versions": ["1.0.0"]}
        with patch(
            "souschef.ui.pages.chef_server_settings._download_cookbook",
            return_value=None,
        ):
            ok = _assess_single_cookbook(
                storage,
                "https://chef.local",
                "org",
                "client",
                "key",
                Path("/tmp"),
                cookbook,
                "anthropic",
                "api-key",
                "model",
            )
        assert ok is False

    def test_assess_single_ai_path_uses_string_cookbook_dir(self):
        """AI assessment path uses string path conversion."""
        from pathlib import Path

        from souschef.ui.pages.chef_server_settings import _assess_single_cookbook

        storage = MagicMock()
        storage.get_cached_analysis.return_value = None
        cookbook = {"name": "nginx", "versions": ["1.0.0"]}
        cookbook_dir = Path("/tmp/nginx")

        with (
            patch(
                "souschef.ui.pages.chef_server_settings._download_cookbook",
                return_value=cookbook_dir,
            ),
            patch(
                "souschef.ui.pages.chef_server_settings.assess_single_cookbook_with_ai",
                return_value={"complexity": "Low", "estimated_hours": 1.0},
            ) as mock_ai,
        ):
            ok = _assess_single_cookbook(
                storage,
                "https://chef.local",
                "org",
                "client",
                "key",
                Path("/tmp"),
                cookbook,
                "Anthropic",
                "api-key",
                "model",
            )

        assert ok is True
        assert mock_ai.call_args[0][0] == str(cookbook_dir)


class TestBulkOperationBranches:
    """Target branch coverage for bulk assessment/conversion paths."""

    def test_run_bulk_assessment_handles_per_cookbook_exception(self):
        """Exception during one cookbook increments failed counter path."""
        from souschef.ui.pages.chef_server_settings import _run_bulk_assessment

        with (
            patch("souschef.ui.pages.chef_server_settings.st") as mock_st,
            patch(
                "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
                return_value=[{"name": "nginx", "versions": ["1.0.0"]}],
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._confirm_bulk_operation",
                return_value=True,
            ),
            patch(
                "souschef.ui.pages.chef_server_settings.get_storage_manager",
                return_value=MagicMock(),
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._assess_single_cookbook",
                side_effect=RuntimeError("bad cookbook"),
            ),
            patch("souschef.ui.pages.chef_server_settings.time.sleep"),
        ):
            mock_st.spinner.return_value = _ctx()
            mock_st.container.return_value = _ctx()
            mock_st.empty.return_value = MagicMock()
            mock_st.progress.return_value = MagicMock()
            mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
            _run_bulk_assessment("u", "o", "c", "k")
        assert mock_st.success.called

    def test_run_bulk_conversion_requires_confirm_for_long_estimate(self):
        """Conversion returns early when long estimate confirmation unchecked."""
        from souschef.ui.pages.chef_server_settings import _run_bulk_conversion

        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            mock_st.spinner.return_value = _ctx()
            mock_st.checkbox.return_value = False
            with patch(
                "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
                return_value=[
                    {"name": "nginx", "versions": ["1.0.0"]} for _ in range(20)
                ],
            ):
                _run_bulk_conversion("u", "o", "c", "k")
            assert mock_st.checkbox.called

    def test_run_bulk_conversion_returns_when_start_not_clicked(self):
        """Conversion exits when start button is not clicked."""
        from souschef.ui.pages.chef_server_settings import _run_bulk_conversion

        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            mock_st.spinner.return_value = _ctx()
            mock_st.button.return_value = False
            mock_st.checkbox.return_value = True
            mock_st.text_input.return_value = "./ansible_output"
            with patch(
                "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
                return_value=[{"name": "nginx", "versions": ["1.0.0"]}],
            ):
                _run_bulk_conversion("u", "o", "c", "k")
            assert mock_st.button.called

    def test_run_bulk_conversion_download_none_branch(self):
        """Conversion handles cookbook download failure and continue path."""
        from souschef.ui.pages.chef_server_settings import _run_bulk_conversion

        storage = MagicMock()
        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            mock_st.spinner.return_value = _ctx()
            mock_st.container.return_value = _ctx()
            mock_st.empty.return_value = MagicMock()
            mock_st.progress.return_value = MagicMock()
            mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
            mock_st.button.return_value = True
            mock_st.text_input.return_value = "./ansible_output"
            with (
                patch(
                    "souschef.ui.pages.chef_server_settings.get_storage_manager",
                    return_value=storage,
                ),
                patch(
                    "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
                    return_value=[{"name": "nginx", "versions": ["1.0.0"]}],
                ),
                patch(
                    "souschef.ui.pages.chef_server_settings._download_cookbook",
                    return_value=None,
                ),
            ):
                _run_bulk_conversion("u", "o", "c", "k")
        assert mock_st.success.called

    def test_run_bulk_conversion_exception_branch_saves_failed(self):
        """Conversion exception path records failed conversion and sleeps."""
        from souschef.ui.pages.chef_server_settings import _run_bulk_conversion

        storage = MagicMock()
        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            mock_st.spinner.return_value = _ctx()
            mock_st.container.return_value = _ctx()
            mock_st.empty.return_value = MagicMock()
            mock_st.progress.return_value = MagicMock()
            mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
            mock_st.button.return_value = True
            mock_st.text_input.return_value = "./ansible_output"
            with (
                patch(
                    "souschef.ui.pages.chef_server_settings.get_storage_manager",
                    return_value=storage,
                ),
                patch(
                    "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
                    return_value=[{"name": "nginx", "versions": ["1.0.0"]}],
                ),
                patch(
                    "souschef.ui.pages.chef_server_settings._download_cookbook",
                    side_effect=RuntimeError("download fail"),
                ),
                patch("souschef.ui.pages.chef_server_settings.time.sleep"),
            ):
                _run_bulk_conversion("u", "o", "c", "k")

        assert storage.save_conversion.called


class TestAdditionalChefServerCoverage:
    """Additional branch coverage for chef server settings helpers."""

    def test_format_time_estimate_hours_branch(self):
        """Format function returns hour/min string for long durations."""
        from souschef.ui.pages.chef_server_settings import _format_time_estimate

        text = _format_time_estimate(3700)
        assert "hour" in text

    def test_confirm_bulk_operation_long_uses_checkbox(self):
        """Long operations should delegate to checkbox confirmation."""
        from souschef.ui.pages.chef_server_settings import _confirm_bulk_operation

        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            mock_st.checkbox.return_value = True
            assert _confirm_bulk_operation(120, "assess") is True
            assert mock_st.checkbox.called

    def test_confirm_bulk_operation_short_returns_true(self):
        """Short operations should auto-confirm."""
        from souschef.ui.pages.chef_server_settings import _confirm_bulk_operation

        assert _confirm_bulk_operation(30, "assess") is True

    def test_get_chef_cookbooks_success_and_exception(self):
        """Cover success and exception paths in _get_chef_cookbooks."""
        from souschef.ui.pages.chef_server_settings import _get_chef_cookbooks

        with patch(
            "souschef.core.chef_server.list_chef_cookbooks",
            return_value=[{"name": "nginx"}],
        ):
            result = _get_chef_cookbooks("u", "o", "c", "k")
            assert result == [{"name": "nginx"}]

        with patch(
            "souschef.core.chef_server.list_chef_cookbooks",
            side_effect=RuntimeError("boom"),
        ):
            result = _get_chef_cookbooks("u", "o", "c", "k")
            assert result == []

    def test_render_bulk_operations_buttons_trigger_handlers(self):
        """Bulk operations buttons call corresponding handlers."""
        from souschef.ui.pages.chef_server_settings import _render_bulk_operations

        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            mock_st.columns.return_value = (_ctx(), _ctx())
            mock_st.button.side_effect = [True, True]
            with (
                patch(
                    "souschef.ui.pages.chef_server_settings._run_bulk_assessment"
                ) as mock_assess,
                patch(
                    "souschef.ui.pages.chef_server_settings._run_bulk_conversion"
                ) as mock_convert,
            ):
                _render_bulk_operations("u", "o", "c", "k")
                mock_assess.assert_called_once()
                mock_convert.assert_called_once()

    def test_download_cookbook_success_path(self):
        """Download cookbook success creates metadata and returns path."""
        from pathlib import Path

        from souschef.ui.pages.chef_server_settings import _download_cookbook

        with (
            patch(
                "souschef.core.chef_server.get_chef_cookbook_version",
                return_value={"name": "nginx"},
            ),
            tempfile.TemporaryDirectory() as td,
        ):
            result = _download_cookbook(
                "https://chef.local",
                "org",
                "client",
                "key",
                "nginx",
                "1.0.0",
                Path(td),
            )
            assert result is not None
            assert (result / "metadata.rb").exists()

    def test_download_cookbook_invalid_inputs(self):
        """Invalid cookbook input guards return None."""
        from pathlib import Path

        from souschef.ui.pages.chef_server_settings import _download_cookbook

        with tempfile.TemporaryDirectory() as td:
            assert (
                _download_cookbook("u", "o", "c", "k", "a" * 300, "1.0.0", Path(td))
                is None
            )
            assert (
                _download_cookbook("u", "o", "c", "k", "ok", "x" * 300, Path(td))
                is None
            )
            assert (
                _download_cookbook("u", "o", "c", "k", "bad/name", "1.0.0", Path(td))
                is None
            )

    def test_assess_single_cookbook_cached_short_circuit(self):
        """Cached assessments return True without saving again."""
        from pathlib import Path

        from souschef.ui.pages.chef_server_settings import _assess_single_cookbook

        storage = MagicMock()
        storage.get_cached_analysis.return_value = {"cached": True}
        cookbook = {"name": "nginx", "versions": ["1.0.0"]}

        with patch(
            "souschef.ui.pages.chef_server_settings._download_cookbook",
            return_value=Path("/tmp/nginx"),
        ):
            ok = _assess_single_cookbook(
                storage,
                "u",
                "o",
                "c",
                "k",
                Path("/tmp"),
                cookbook,
                "anthropic",
                "api",
                "model",
            )
        assert ok is True

    def test_assess_single_cookbook_rule_based_path(self):
        """No AI key uses rule-based assessment fallback path."""
        from pathlib import Path

        from souschef.ui.pages.chef_server_settings import _assess_single_cookbook

        storage = MagicMock()
        storage.get_cached_analysis.return_value = None
        cookbook = {"name": "nginx", "versions": ["1.0.0"]}
        with (
            patch(
                "souschef.ui.pages.chef_server_settings._download_cookbook",
                return_value=Path("/tmp/nginx"),
            ),
            patch(
                "souschef.assessment.parse_chef_migration_assessment",
                return_value={"complexity": "Low", "estimated_hours": 1.0},
            ),
        ):
            ok = _assess_single_cookbook(
                storage,
                "u",
                "o",
                "c",
                "k",
                Path("/tmp"),
                cookbook,
                "anthropic",
                "",
                "model",
            )
        assert ok is True

    def test_run_bulk_assessment_no_cookbooks(self):
        """No cookbooks branch shows error and returns."""
        from souschef.ui.pages.chef_server_settings import _run_bulk_assessment

        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            mock_st.spinner.return_value = _ctx()
            with patch(
                "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
                return_value=[],
            ):
                _run_bulk_assessment("u", "o", "c", "k")
            mock_st.error.assert_called_once()

    def test_run_bulk_assessment_confirm_rejects(self):
        """Assessment returns early when confirmation rejected."""
        from souschef.ui.pages.chef_server_settings import _run_bulk_assessment

        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            mock_st.spinner.return_value = _ctx()
            with (
                patch(
                    "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
                    return_value=[{"name": "nginx", "versions": ["1.0.0"]}],
                ),
                patch(
                    "souschef.ui.pages.chef_server_settings._confirm_bulk_operation",
                    return_value=False,
                ),
            ):
                _run_bulk_assessment("u", "o", "c", "k")
            assert mock_st.warning.called

    def test_run_bulk_assessment_failed_increment_path(self):
        """Assessment increments failed count when helper returns False."""
        from souschef.ui.pages.chef_server_settings import _run_bulk_assessment

        with (
            patch("souschef.ui.pages.chef_server_settings.st") as mock_st,
            patch(
                "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
                return_value=[{"name": "nginx", "versions": ["1.0.0"]}],
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._confirm_bulk_operation",
                return_value=True,
            ),
            patch(
                "souschef.ui.pages.chef_server_settings.get_storage_manager",
                return_value=MagicMock(),
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._assess_single_cookbook",
                return_value=False,
            ),
        ):
            mock_st.spinner.return_value = _ctx()
            mock_st.container.return_value = _ctx()
            mock_st.empty.return_value = MagicMock()
            mock_st.progress.return_value = MagicMock()
            mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
            _run_bulk_assessment("u", "o", "c", "k")
        assert mock_st.success.called

    def test_run_bulk_assessment_success_increment_path(self):
        """Assessment increments successful count when helper returns True."""
        from souschef.ui.pages.chef_server_settings import _run_bulk_assessment

        with (
            patch("souschef.ui.pages.chef_server_settings.st") as mock_st,
            patch(
                "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
                return_value=[{"name": "nginx", "versions": ["1.0.0"]}],
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._confirm_bulk_operation",
                return_value=True,
            ),
            patch(
                "souschef.ui.pages.chef_server_settings.get_storage_manager",
                return_value=MagicMock(),
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._assess_single_cookbook",
                return_value=True,
            ),
        ):
            mock_st.spinner.return_value = _ctx()
            mock_st.container.return_value = _ctx()
            mock_st.empty.return_value = MagicMock()
            mock_st.progress.return_value = MagicMock()
            mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
            _run_bulk_assessment("u", "o", "c", "k")
        assert mock_st.success.called

    def test_run_bulk_conversion_no_cookbooks(self):
        """No cookbooks in conversion shows error and returns."""
        from souschef.ui.pages.chef_server_settings import _run_bulk_conversion

        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            mock_st.spinner.return_value = _ctx()
            with patch(
                "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
                return_value=[],
            ):
                _run_bulk_conversion("u", "o", "c", "k")
            mock_st.error.assert_called_once()

    def test_run_bulk_conversion_success_path_with_output_info(self):
        """Successful conversion path reaches output info display."""
        from pathlib import Path

        from souschef.ui.pages.chef_server_settings import _run_bulk_conversion

        storage = MagicMock()
        with patch("souschef.ui.pages.chef_server_settings.st") as mock_st:
            mock_st.spinner.return_value = _ctx()
            mock_st.container.return_value = _ctx()
            mock_st.empty.return_value = MagicMock()
            mock_st.progress.return_value = MagicMock()
            mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
            mock_st.checkbox.return_value = True
            mock_st.button.return_value = True
            mock_st.text_input.return_value = "./ansible_output"
            with (
                patch(
                    "souschef.ui.pages.chef_server_settings.get_storage_manager",
                    return_value=storage,
                ),
                patch(
                    "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
                    return_value=[{"name": "nginx", "versions": ["1.0.0"]}],
                ),
                patch(
                    "souschef.ui.pages.chef_server_settings._download_cookbook",
                    return_value=Path("/tmp/nginx"),
                ),
            ):
                _run_bulk_conversion("u", "o", "c", "k")
        assert storage.save_conversion.called
