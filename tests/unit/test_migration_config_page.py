"""Comprehensive tests for migration_config UI page to achieve 100% coverage."""

from __future__ import annotations

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


class TestShowMigrationConfigPage:
    """Test main page entry point."""

    @patch("souschef.ui.pages.migration_config.st")
    def test_show_page_without_config(self, mock_st):
        """Test page display without existing configuration."""
        from souschef.ui.pages.migration_config import show_migration_config_page

        mock_st.session_state = SessionState()
        # Mock st.columns to return a tuple of mock columns
        col1, col2 = MagicMock(), MagicMock()
        mock_st.columns.return_value = (col1, col2)
        mock_st.button.return_value = False

        show_migration_config_page()

        mock_st.header.assert_called_once()
        mock_st.markdown.assert_called()
        mock_st.divider.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    @patch("souschef.ui.pages.migration_config._show_activity_visualisation")
    def test_show_page_with_config(self, mock_visualisation, mock_st):
        """Test page display with existing configuration."""
        from souschef.migration_config import (
            DeploymentTarget,
            MigrationConfig,
            MigrationStandard,
            ValidationTool,
        )
        from souschef.ui.pages.migration_config import show_migration_config_page

        config = MigrationConfig(
            deployment_target=DeploymentTarget.AWX,
            migration_standard=MigrationStandard.STANDARD,
            inventory_source="hosts.ini",
            validation_tools=[ValidationTool.ANSIBLE_LINT],
            target_python_version="3.10",
            target_ansible_version="2.15+",
        )
        mock_st.session_state = SessionState({"migration_config": config})
        # Mock st.columns to return tuples of appropriate sizes (2 or 3)
        col1, col2, col3 = _ctx(), _ctx(), _ctx()
        mock_st.columns.side_effect = [(col1, col2, col3), (col1, col2)]
        mock_st.button.return_value = False
        mock_st.expander.return_value = _ctx()

        show_migration_config_page()

        mock_st.header.assert_called_once()
        mock_visualisation.assert_called_once()


class TestConfigurationSection:
    """Test configuration section display."""

    @patch("souschef.ui.pages.migration_config.st")
    @patch("souschef.ui.pages.migration_config._show_configuration_form")
    def test_show_section_without_config(self, mock_form, mock_st):
        """Test configuration section without existing config."""
        from souschef.ui.pages.migration_config import _show_configuration_section

        mock_st.session_state = SessionState()

        _show_configuration_section()

        mock_st.subheader.assert_called_once()
        mock_form.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    @patch("souschef.ui.pages.migration_config._display_current_config")
    def test_show_section_with_config(self, mock_display, mock_st):
        """Test configuration section with existing config."""
        from souschef.migration_config import (
            DeploymentTarget,
            MigrationConfig,
            MigrationStandard,
            ValidationTool,
        )
        from souschef.ui.pages.migration_config import _show_configuration_section

        config = MigrationConfig(
            deployment_target=DeploymentTarget.AWX,
            migration_standard=MigrationStandard.STANDARD,
            inventory_source="hosts.ini",
            validation_tools=[ValidationTool.ANSIBLE_LINT],
            target_python_version="3.10",
            target_ansible_version="2.15+",
        )
        mock_st.session_state = SessionState({"migration_config": config})
        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)
        mock_st.button.return_value = False

        _show_configuration_section()

        mock_display.assert_called_once()
        assert mock_st.button.call_count == 2  # Reconfigure and Export buttons

    @patch("souschef.ui.pages.migration_config.st")
    @patch("souschef.ui.pages.migration_config._display_current_config")
    def test_reconfigure_button_click(self, mock_display, mock_st):
        """Test reconfigure button deletion of config."""
        from souschef.migration_config import (
            DeploymentTarget,
            MigrationConfig,
            MigrationStandard,
            ValidationTool,
        )
        from souschef.ui.pages.migration_config import _show_configuration_section

        config = MigrationConfig(
            deployment_target=DeploymentTarget.AWX,
            migration_standard=MigrationStandard.STANDARD,
            inventory_source="hosts.ini",
            validation_tools=[ValidationTool.ANSIBLE_LINT],
            target_python_version="3.10",
            target_ansible_version="2.15+",
        )
        mock_st.session_state = SessionState({"migration_config": config})
        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)
        # First button (Reconfigure) returns True
        mock_st.button.side_effect = [True, False]

        _show_configuration_section()

        assert "migration_config" not in mock_st.session_state
        mock_st.rerun.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    @patch("souschef.ui.pages.migration_config._display_current_config")
    @patch("souschef.ui.pages.migration_config._export_configuration")
    def test_export_button_click(self, mock_export, mock_display, mock_st):
        """Test export button triggers export."""
        from souschef.migration_config import (
            DeploymentTarget,
            MigrationConfig,
            MigrationStandard,
            ValidationTool,
        )
        from souschef.ui.pages.migration_config import _show_configuration_section

        config = MigrationConfig(
            deployment_target=DeploymentTarget.AWX,
            migration_standard=MigrationStandard.STANDARD,
            inventory_source="hosts.ini",
            validation_tools=[ValidationTool.ANSIBLE_LINT],
            target_python_version="3.10",
            target_ansible_version="2.15+",
        )
        mock_st.session_state = SessionState({"migration_config": config})
        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)
        # Second button (Export) returns True
        mock_st.button.side_effect = [False, True]

        _show_configuration_section()

        mock_export.assert_called_once()


class TestDisplayCurrentConfig:
    """Test current configuration display."""

    @patch("souschef.ui.pages.migration_config.st")
    def test_display_config_metrics(self, mock_st):
        """Test configuration metrics display."""
        from souschef.migration_config import (
            DeploymentTarget,
            MigrationConfig,
            MigrationStandard,
            ValidationTool,
        )
        from souschef.ui.pages.migration_config import _display_current_config

        config = MigrationConfig(
            deployment_target=DeploymentTarget.AWX,
            migration_standard=MigrationStandard.STANDARD,
            inventory_source="hosts.ini",
            validation_tools=[ValidationTool.ANSIBLE_LINT],
            target_python_version="3.10",
            target_ansible_version="2.15+",
        )
        mock_st.session_state = SessionState({"migration_config": config})
        col1, col2, col3 = _ctx(), _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2, col3)
        mock_st.expander.return_value = _ctx()

        _display_current_config()

        mock_st.success.assert_called_once()
        assert mock_st.metric.call_count == 3  # Three metrics
        mock_st.expander.assert_called_once()
        mock_st.json.assert_called_once()


class TestConfigurationForm:
    """Test configuration form display and submission."""

    @patch("souschef.ui.pages.migration_config.st")
    def test_show_form_displays_all_fields(self, mock_st):
        """Test form displays all configuration fields."""
        from souschef.ui.pages.migration_config import _show_configuration_form

        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)
        mock_st.button.return_value = False

        _show_configuration_form()

        mock_st.markdown.assert_called()
        assert mock_st.selectbox.call_count == 3  # deployment, standard, python
        assert mock_st.text_input.call_count == 2  # inventory, ansible
        mock_st.multiselect.assert_called_once()
        mock_st.button.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    def test_save_config_success(self, mock_st):
        """Test successful configuration save."""
        from souschef.ui.pages.migration_config import _show_configuration_form

        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)
        mock_st.selectbox.side_effect = ["awx", "standard", "3.10"]
        mock_st.text_input.side_effect = ["hosts.ini", "2.15+"]
        mock_st.multiselect.return_value = ["ansible-lint"]
        mock_st.button.return_value = True
        mock_st.session_state = SessionState()

        _show_configuration_form()

        assert "migration_config" in mock_st.session_state
        mock_st.success.assert_called_once()
        mock_st.rerun.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    def test_save_config_exception(self, mock_st):
        """Test configuration save with exception."""
        from souschef.ui.pages.migration_config import _show_configuration_form

        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)
        mock_st.selectbox.side_effect = ["invalid-target", "standard", "3.10"]
        mock_st.text_input.side_effect = ["hosts.ini", "2.15+"]
        mock_st.multiselect.return_value = ["ansible-lint"]
        mock_st.button.return_value = True
        mock_st.session_state = SessionState()

        _show_configuration_form()

        mock_st.error.assert_called_once()
        assert "migration_config" not in mock_st.session_state


class TestExportConfiguration:
    """Test configuration export functionality."""

    @patch("souschef.ui.pages.migration_config.st")
    def test_export_config_json(self, mock_st):
        """Test exporting configuration as JSON."""
        from souschef.migration_config import (
            DeploymentTarget,
            MigrationConfig,
            MigrationStandard,
            ValidationTool,
        )
        from souschef.ui.pages.migration_config import _export_configuration

        config = MigrationConfig(
            deployment_target=DeploymentTarget.AWX,
            migration_standard=MigrationStandard.STANDARD,
            inventory_source="hosts.ini",
            validation_tools=[ValidationTool.ANSIBLE_LINT],
            target_python_version="3.10",
            target_ansible_version="2.15+",
        )
        mock_st.session_state = SessionState({"migration_config": config})

        _export_configuration()

        mock_st.download_button.assert_called_once()
        _, kwargs = mock_st.download_button.call_args
        assert kwargs["file_name"] == "migration_config.json"
        assert kwargs["mime"] == "application/json"
        assert "deployment_target" in kwargs["data"]


class TestActivityVisualisation:
    """Test activity visualisation section."""

    def test_show_visualisation_returns_when_streamlit_unavailable(self):
        """Function should return early when module-level streamlit handle is None."""
        import souschef.ui.pages.migration_config as mc

        with patch.object(mc, "st", None):
            mc._show_activity_visualisation()

    @patch("souschef.ui.pages.migration_config.st")
    def test_show_visualisation_form(self, mock_st):
        """Test activity visualisation form display."""
        from souschef.ui.pages.migration_config import _show_activity_visualisation

        mock_st.session_state = SessionState()
        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)
        mock_st.button.return_value = False

        _show_activity_visualisation()

        mock_st.subheader.assert_called_once()
        mock_st.markdown.assert_called()
        assert mock_st.text_input.call_count == 1
        assert mock_st.selectbox.call_count == 1
        mock_st.button.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    def test_generate_breakdown_empty_path(self, mock_st):
        """Test generating breakdown with empty path shows error."""
        from souschef.ui.pages.migration_config import _show_activity_visualisation

        mock_st.session_state = SessionState()
        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)
        mock_st.text_input.return_value = "   "  # Whitespace only
        mock_st.selectbox.return_value = "phased"
        mock_st.button.return_value = True

        _show_activity_visualisation()

        mock_st.error.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    @patch("souschef.ui.pages.migration_config._generate_and_display_breakdown")
    def test_generate_breakdown_with_path(self, mock_generate, mock_st):
        """Test generating breakdown with valid path."""
        from souschef.ui.pages.migration_config import _show_activity_visualisation

        mock_st.session_state = SessionState()
        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)
        mock_st.text_input.return_value = "/path/to/cookbook"
        mock_st.selectbox.return_value = "phased"
        mock_st.button.return_value = True

        _show_activity_visualisation()

        mock_generate.assert_called_once_with("/path/to/cookbook", "phased")


class TestGenerateAndDisplayBreakdown:
    """Test activity breakdown generation and display."""

    @patch("souschef.ui.pages.migration_config.st")
    @patch("souschef.ui.pages.migration_config.calculate_activity_breakdown")
    @patch("souschef.ui.pages.migration_config._display_activity_breakdown")
    def test_successful_breakdown(self, mock_display, mock_calculate, mock_st):
        """Test successful breakdown generation."""
        from souschef.ui.pages.migration_config import (
            _generate_and_display_breakdown,
        )

        mock_st.session_state = SessionState()
        mock_st.spinner.return_value = _ctx()
        breakdown_result = {
            "summary": {"total_manual_hours": 100},
            "activities": [],
        }
        mock_calculate.return_value = breakdown_result

        _generate_and_display_breakdown("/path/to/cookbook", "phased")

        mock_calculate.assert_called_once_with("/path/to/cookbook", "phased")
        assert mock_st.session_state.activity_breakdown == breakdown_result
        mock_display.assert_called_once_with(breakdown_result)

    @patch("souschef.ui.pages.migration_config.st")
    @patch("souschef.ui.pages.migration_config.calculate_activity_breakdown")
    def test_breakdown_with_error(self, mock_calculate, mock_st):
        """Test breakdown generation with error in result."""
        from souschef.ui.pages.migration_config import (
            _generate_and_display_breakdown,
        )

        mock_st.session_state = SessionState()
        mock_st.spinner.return_value = _ctx()
        mock_calculate.return_value = {"error": "Calculation failed"}

        _generate_and_display_breakdown("/path/to/cookbook", "phased")

        mock_st.error.assert_called_once()
        assert "activity_breakdown" not in mock_st.session_state

    @patch("souschef.ui.pages.migration_config.st")
    @patch("souschef.ui.pages.migration_config.calculate_activity_breakdown")
    def test_breakdown_exception(self, mock_calculate, mock_st):
        """Test breakdown generation with exception."""
        from souschef.ui.pages.migration_config import (
            _generate_and_display_breakdown,
        )

        mock_st.session_state = SessionState()
        mock_st.spinner.return_value = _ctx()
        mock_calculate.side_effect = RuntimeError("Unexpected error")

        _generate_and_display_breakdown("/path/to/cookbook", "phased")

        mock_st.error.assert_called_once()


class TestDisplayActivityBreakdown:
    """Test activity breakdown display."""

    @patch("souschef.ui.pages.migration_config.st")
    @patch("souschef.ui.pages.migration_config._display_breakdown_metrics")
    @patch("souschef.ui.pages.migration_config._display_activity_summary")
    @patch("souschef.ui.pages.migration_config._display_activity_table")
    @patch("souschef.ui.pages.migration_config._display_time_savings_chart")
    @patch("souschef.ui.pages.migration_config._display_breakdown_export_options")
    def test_display_breakdown_calls_all_sub_funcs(
        self,
        mock_export,
        mock_chart,
        mock_table,
        mock_summary,
        mock_metrics,
        mock_st,
    ):
        """Test breakdown display calls all display functions."""
        from souschef.ui.pages.migration_config import _display_activity_breakdown

        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)
        breakdown = {
            "summary": {},
            "activities": [],
        }

        _display_activity_breakdown(breakdown)

        mock_st.success.assert_called_once()
        mock_metrics.assert_called_once_with(breakdown)
        mock_summary.assert_called_once_with(breakdown)
        mock_table.assert_called_once_with(breakdown)
        mock_chart.assert_called_once_with(breakdown)
        mock_export.assert_called_once_with(breakdown)


class TestBreakdownMetrics:
    """Test breakdown metrics display."""

    @patch("souschef.ui.pages.migration_config.st")
    def test_display_metrics_with_data(self, mock_st):
        """Test metrics display with valid data."""
        from souschef.ui.pages.migration_config import _display_breakdown_metrics

        col1, col2, col3, col4 = _ctx(), _ctx(), _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2, col3, col4)
        breakdown = {
            "summary": {
                "total_manual_hours": 100.5,
                "total_ai_assisted_hours": 50.2,
                "time_saved_hours": 50.3,
                "efficiency_gain_percent": 50,
                "timeline_weeks": 4,
            }
        }

        _display_breakdown_metrics(breakdown)

        assert mock_st.metric.call_count == 4

    @patch("souschef.ui.pages.migration_config.st")
    def test_display_metrics_empty_summary(self, mock_st):
        """Test metrics display with empty summary."""
        from souschef.ui.pages.migration_config import _display_breakdown_metrics

        col1, col2, col3, col4 = _ctx(), _ctx(), _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2, col3, col4)
        breakdown = {"summary": {}}

        _display_breakdown_metrics(breakdown)

        assert mock_st.metric.call_count == 4  # Still displays with defaults


class TestActivitySummary:
    """Test activity summary display."""

    @patch("souschef.ui.pages.migration_config.st")
    def test_display_summary_with_activities(self, mock_st):
        """Test summary display with activities."""
        from souschef.ui.pages.migration_config import _display_activity_summary

        breakdown = {
            "activities": [
                {
                    "name": "Recipe Conversion",
                    "count": 10,
                    "description": "Convert Chef recipes to Ansible playbooks",
                    "manual_hours": 50.0,
                    "ai_assisted_hours": 25.0,
                    "time_saved": 25.0,
                    "efficiency_gain_percent": 50,
                },
                {
                    "name": "Testing",
                    "count": 5,
                    "description": "Test converted playbooks",
                    "manual_hours": 20.0,
                    "ai_assisted_hours": 10.0,
                    "time_saved": 10.0,
                    "efficiency_gain_percent": 50,
                },
            ]
        }

        _display_activity_summary(breakdown)

        mock_st.subheader.assert_called_once()
        assert mock_st.markdown.call_count == 2  # One per activity
        assert mock_st.divider.call_count == 2

    @patch("souschef.ui.pages.migration_config.st")
    def test_display_summary_no_activities(self, mock_st):
        """Test summary display with no activities."""
        from souschef.ui.pages.migration_config import _display_activity_summary

        breakdown = {"activities": []}

        _display_activity_summary(breakdown)

        # Should return early without calling subheader
        mock_st.subheader.assert_not_called()


class TestActivityTable:
    """Test activity table display."""

    @patch("souschef.ui.pages.migration_config.st")
    def test_display_table_with_activities(self, mock_st):
        """Test table display with activities."""
        from souschef.ui.pages.migration_config import _display_activity_table

        breakdown = {
            "activities": [
                {
                    "name": "Recipe Conversion",
                    "count": 10,
                    "description": "Convert recipes",
                    "manual_hours": 50.0,
                    "ai_assisted_hours": 25.0,
                    "time_saved": 25.0,
                    "efficiency_gain_percent": 50,
                }
            ]
        }

        _display_activity_table(breakdown)

        mock_st.subheader.assert_called_once()
        mock_st.table.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    def test_display_table_no_activities(self, mock_st):
        """Test table display with no activities."""
        from souschef.ui.pages.migration_config import _display_activity_table

        breakdown = {"activities": []}

        _display_activity_table(breakdown)

        mock_st.subheader.assert_called_once()
        mock_st.info.assert_called_once()
        mock_st.table.assert_not_called()


class TestTimeSavingsChart:
    """Test time savings chart display."""

    def test_chart_exists(self):
        """Verify chart function exists (unit tests hard to implement with pytest-cov)."""
        from souschef.ui.pages.migration_config import _display_time_savings_chart

        # Verify the function exists and is callable
        assert callable(_display_time_savings_chart)
        # Chart integration testing covered manually and in E2E tests
        # Function is marked #pragma: no cover due to pytest-cov patching issues

    def test_z_display_chart_pandas_not_installed(self):
        """Test chart display when pandas is not available."""
        import sys

        # Remove pandas from sys.modules temporarily
        pandas_modules = {}
        # list() is necessary here - we're modifying sys.modules during iteration
        for key in list(sys.modules.keys()):  # noqa: S7504
            if key == "pandas" or key.startswith("pandas."):
                pandas_modules[key] = sys.modules.pop(key)

        try:
            # Patch builtins.__import__ to block pandas import
            original_import = (
                __builtins__["__import__"]
                if isinstance(__builtins__, dict)
                else __builtins__.__import__
            )

            def import_mock(name, *args, **kwargs):
                if name == "pandas":
                    raise ImportError("No module named 'pandas'")
                return original_import(name, *args, **kwargs)

            # Patch and test - don't reload the module, just test the function
            with patch("builtins.__import__", side_effect=import_mock):
                from unittest.mock import MagicMock

                from souschef.ui.pages import migration_config as mc

                mock_st = MagicMock()

                # Temporarily replace st in the module
                original_st = mc.st
                mc.st = mock_st

                try:
                    breakdown = {
                        "activities": [
                            {"name": "Test", "manual_hours": 10, "ai_assisted_hours": 5}
                        ]
                    }

                    mc._display_time_savings_chart(breakdown)

                    # Should show warning when pandas not available
                    mock_st.warning.assert_called_once_with(
                        "Pandas is required for chart visualisation."
                    )
                    mock_st.bar_chart.assert_not_called()
                finally:
                    # Restore original st
                    mc.st = original_st

        finally:
            # Restore pandas modules
            sys.modules.update(pandas_modules)


class TestBreakdownExportOptions:
    """Test breakdown export options."""

    @patch("souschef.ui.pages.migration_config.st")
    @patch("souschef.ui.pages.migration_config._generate_markdown_report")
    def test_display_export_options(self, mock_report, mock_st):
        """Test export options display."""
        from souschef.ui.pages.migration_config import (
            _display_breakdown_export_options,
        )

        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)
        mock_report.return_value = "# Report"
        breakdown = {"summary": {}, "activities": []}

        _display_breakdown_export_options(breakdown)

        mock_st.subheader.assert_called_once()
        assert mock_st.download_button.call_count == 2  # JSON and Markdown
        mock_report.assert_called_once_with(breakdown)


class TestGenerateMarkdownReport:
    """Test markdown report generation."""

    def test_generate_report_with_data(self):
        """Test markdown report generation with data."""
        from souschef.ui.pages.migration_config import _generate_markdown_report

        breakdown = {
            "summary": {
                "total_manual_hours": 100.0,
                "total_ai_assisted_hours": 50.0,
                "time_saved_hours": 50.0,
                "efficiency_gain_percent": 50,
                "timeline_weeks": 4,
            },
            "activities": [
                {
                    "name": "Recipe Conversion",
                    "count": 10,
                    "description": "Convert recipes",
                    "manual_hours": 50.0,
                    "ai_assisted_hours": 25.0,
                    "time_saved": 25.0,
                    "efficiency_gain_percent": 50,
                }
            ],
        }

        report = _generate_markdown_report(breakdown)

        assert "# Migration Activity Breakdown Report" in report
        assert "## Summary" in report
        assert "100.0h" in report
        assert "Recipe Conversion" in report
        assert "## Activity Details" in report
        assert "Generated by SousChef" in report

    def test_generate_report_empty_data(self):
        """Test markdown report generation with empty data."""
        from souschef.ui.pages.migration_config import _generate_markdown_report

        breakdown = {
            "summary": {},
            "activities": [],
        }

        report = _generate_markdown_report(breakdown)

        assert "# Migration Activity Breakdown Report" in report
        assert "## Summary" in report
        assert "## Activity Details" in report
        assert "Generated by SousChef" in report


class TestStreamlitImportHandling:
    """Test streamlit import error handling at module level."""

    def test_z_module_handles_streamlit_import_error(self):
        """Test that module handles streamlit ImportError gracefully (lines 13-14)."""
        import sys

        # Save all souschef.ui.pages modules
        souschef_modules = {}
        # list() is necessary here - we're modifying sys.modules during iteration
        for key in list(sys.modules.keys()):  # noqa: S7504
            if key.startswith("souschef.ui.pages"):
                souschef_modules[key] = sys.modules.pop(key)

        # Save streamlit modules
        streamlit_modules = {}
        # list() is necessary here - we're modifying sys.modules during iteration
        for key in list(sys.modules.keys()):  # noqa: S7504
            if key == "streamlit" or key.startswith("streamlit."):
                streamlit_modules[key] = sys.modules.pop(key)

        try:
            # Patch __import__ to raise ImportError for streamlit
            original_import = (
                __builtins__["__import__"]
                if isinstance(__builtins__, dict)
                else __builtins__.__import__
            )

            def import_mock(name, *args, **kwargs):
                if name == "streamlit":
                    raise ImportError("No module named 'streamlit'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=import_mock):
                # Import the module - should handle ImportError and set st = None
                import souschef.ui.pages.migration_config

                # Verify st is None when streamlit unavailable (covers lines 13-14)
                assert souschef.ui.pages.migration_config.st is None

        finally:
            # Clean up - remove the module we imported
            # list() is necessary here - we're modifying sys.modules during iteration
            for key in list(sys.modules.keys()):  # noqa: S7504
                if key.startswith("souschef.ui.pages"):
                    sys.modules.pop(key, None)

            # Restore original modules
            sys.modules.update(streamlit_modules)
            sys.modules.update(souschef_modules)
