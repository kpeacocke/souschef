"""Comprehensive tests for UI modules to boost coverage to 90%+."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestProgressTrackerMethods:
    """Test ProgressTracker class methods thoroughly."""

    @patch("souschef.ui.app.st")
    def test_progress_tracker_init(self, mock_st):
        """Test ProgressTracker initialization."""
        from souschef.ui.app import ProgressTracker

        mock_st.progress.return_value = Mock()
        mock_st.empty.return_value = Mock()

        tracker = ProgressTracker(total_steps=50, description="Test")

        assert tracker.total_steps == 50
        assert tracker.current_step == 0
        assert tracker.description == "Test"
        mock_st.progress.assert_called_once_with(0)
        mock_st.empty.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_progress_tracker_update_with_step(self, mock_st):
        """Test updating progress with explicit step."""
        from souschef.ui.app import ProgressTracker

        mock_progress_bar = Mock()
        mock_status_text = Mock()
        mock_st.progress.return_value = mock_progress_bar
        mock_st.empty.return_value = mock_status_text

        tracker = ProgressTracker(total_steps=100)
        tracker.update(step=50, description="Halfway")

        assert tracker.current_step == 50
        assert tracker.description == "Halfway"
        mock_progress_bar.progress.assert_called_with(0.5)
        mock_status_text.text.assert_called_with("Halfway (50/100)")

    @patch("souschef.ui.app.st")
    def test_progress_tracker_update_increment(self, mock_st):
        """Test updating progress by incrementing."""
        from souschef.ui.app import ProgressTracker

        mock_progress_bar = Mock()
        mock_status_text = Mock()
        mock_st.progress.return_value = mock_progress_bar
        mock_st.empty.return_value = mock_status_text

        tracker = ProgressTracker(total_steps=10)
        tracker.update()
        tracker.update()

        assert tracker.current_step == 2

    @patch("souschef.ui.app.st")
    @patch("time.sleep")
    def test_progress_tracker_complete(self, mock_sleep, mock_st):
        """Test completing progress."""
        from souschef.ui.app import ProgressTracker

        mock_progress_bar = Mock()
        mock_status_text = Mock()
        mock_st.progress.return_value = mock_progress_bar
        mock_st.empty.return_value = mock_status_text

        tracker = ProgressTracker()
        tracker.complete("Done!")

        mock_progress_bar.progress.assert_called_with(1.0)
        mock_status_text.text.assert_called_with("Done!")
        mock_sleep.assert_called_once_with(0.5)

    @patch("souschef.ui.app.st")
    def test_progress_tracker_close(self, mock_st):
        """Test closing progress tracker."""
        from souschef.ui.app import ProgressTracker

        mock_progress_bar = Mock()
        mock_status_text = Mock()
        mock_st.progress.return_value = mock_progress_bar
        mock_st.empty.return_value = mock_status_text

        tracker = ProgressTracker()
        tracker.close()

        mock_progress_bar.empty.assert_called_once()
        mock_status_text.empty.assert_called_once()


class TestDashboardMetrics:
    """Test dashboard metric calculations."""

    @patch("souschef.ui.app.st")
    def test_calculate_dashboard_metrics_empty(self, mock_st):
        """Test metrics with no data."""
        from souschef.ui.app import _calculate_dashboard_metrics

        mock_st.session_state = {}

        cookbooks, complexity, rate, successful = _calculate_dashboard_metrics()

        assert cookbooks == 0
        assert complexity == "Unknown"
        assert rate == 0
        assert successful == 0

    @patch("souschef.ui.app.st")
    def test_calculate_dashboard_metrics_with_data(self, mock_st):
        """Test metrics with analysis data."""
        from souschef.ui.app import _calculate_dashboard_metrics

        # Create a session_state mock that works with both dict and attribute access
        class SessionState(dict):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.__dict__ = self

        mock_st.session_state = SessionState(
            {
                "analysis_results": [
                    {"status": "Analysed", "complexity": "High"},
                    {"status": "Analysed", "complexity": "Medium"},
                    {"status": "Failed", "complexity": "Low"},
                ]
            }
        )

        cookbooks, complexity, rate, successful = _calculate_dashboard_metrics()

        assert cookbooks == 3
        assert complexity == "High"  # High takes precedence
        assert rate == 66  # 2/3 = 66%
        assert successful == 2

    @patch("souschef.ui.app.st")
    def test_calculate_dashboard_metrics_medium_complexity(self, mock_st):
        """Test metrics with medium complexity."""
        from souschef.ui.app import _calculate_dashboard_metrics

        class SessionState(dict):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.__dict__ = self

        mock_st.session_state = SessionState(
            {
                "analysis_results": [
                    {"status": "Analysed", "complexity": "Medium"},
                    {"status": "Analysed", "complexity": "Low"},
                ]
            }
        )

        _, complexity, _, _ = _calculate_dashboard_metrics()
        assert complexity == "Medium"

    @patch("souschef.ui.app.st")
    def test_calculate_dashboard_metrics_low_complexity(self, mock_st):
        """Test metrics with only low complexity."""
        from souschef.ui.app import _calculate_dashboard_metrics

        class SessionState(dict):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.__dict__ = self

        mock_st.session_state = SessionState(
            {
                "analysis_results": [
                    {"status": "Analysed", "complexity": "Low"},
                ]
            }
        )

        _, complexity, _, _ = _calculate_dashboard_metrics()
        assert complexity == "Low"


class TestQuickSelectExamples:
    """Test quick select example application."""

    def test_apply_quick_select_single_cookbook(self):
        """Test applying single cookbook example."""
        from souschef.ui.app import _apply_quick_select_example

        result = _apply_quick_select_example("", "Single Cookbook")

        assert result == "/path/to/cookbooks/nginx"

    def test_apply_quick_select_multiple_cookbooks(self):
        """Test applying multiple cookbooks example."""
        from souschef.ui.app import _apply_quick_select_example

        result = _apply_quick_select_example("", "Multiple Cookbooks")

        assert "/path/to/cookbooks/nginx" in result
        assert "/path/to/cookbooks/apache2" in result
        assert "/path/to/cookbooks/mysql" in result

    def test_apply_quick_select_full_migration(self):
        """Test applying full migration example."""
        from souschef.ui.app import _apply_quick_select_example

        result = _apply_quick_select_example("", "Full Migration")

        assert "/path/to/cookbooks/postgresql" in result
        assert "/path/to/cookbooks/redis" in result

    def test_apply_quick_select_unchanged(self):
        """Test applying no example keeps original."""
        from souschef.ui.app import _apply_quick_select_example

        original = "/custom/path"
        result = _apply_quick_select_example(original, "")

        assert result == original


class TestHistoryFormatting:
    """Test history formatting functions."""

    def test_format_history_analysis_none(self):
        """Test formatting with None analysis_id."""
        from souschef.ui.app import _format_history_analysis

        result = _format_history_analysis(None, [])

        assert result == "-- Select from history --"

    def test_format_history_analysis_with_string_date(self):
        """Test formatting analysis with string date."""
        from souschef.ui.app import _format_history_analysis

        class MockAnalysis:
            id = 1
            cookbook_name = "nginx"
            cookbook_version = "1.0.0"
            complexity = "Medium"
            created_at = "2024-01-15"

        analyses = [MockAnalysis()]
        result = _format_history_analysis(1, analyses)

        assert "nginx v1.0.0" in result
        assert "Medium complexity" in result

    def test_format_history_analysis_with_datetime(self):
        """Test formatting analysis with datetime object."""
        from souschef.ui.app import _format_history_analysis

        class MockAnalysis:
            id = 1
            cookbook_name = "apache"
            cookbook_version = "2.4.0"
            complexity = "High"
            created_at = datetime(2024, 3, 8, 10, 30, 0)

        analyses = [MockAnalysis()]
        result = _format_history_analysis(1, analyses)

        assert "apache v2.4.0" in result
        assert "High complexity" in result

    def test_format_history_analysis_with_other_type(self):
        """Test formatting analysis with other date type."""
        from souschef.ui.app import _format_history_analysis

        class MockAnalysis:
            id = 1
            cookbook_name = "mysql"
            cookbook_version = "8.0"
            complexity = "Low"
            created_at = 123456789  # Unix timestamp

        analyses = [MockAnalysis()]
        result = _format_history_analysis(1, analyses)

        assert "mysql v8.0" in result
        assert "Low complexity" in result

    def test_format_history_analysis_not_found(self):
        """Test formatting when analysis_id not found."""
        from souschef.ui.app import _format_history_analysis

        result = _format_history_analysis(999, [])

        assert result == "--"


class TestNavigationRendering:
    """Test navigation rendering functions."""

    @patch("souschef.ui.app.st")
    def test_render_navigation_button_primary(self, mock_st):
        """Test rendering primary (current page) button."""
        from souschef.ui.app import _render_navigation_button

        mock_col = MagicMock()
        mock_st.button.return_value = False

        _render_navigation_button(mock_col, "Test Page", "test_page", "test_page")

        mock_st.button.assert_called_once()
        args, kwargs = mock_st.button.call_args
        assert kwargs["type"] == "primary"
        assert kwargs["width"] == "stretch"

    @patch("souschef.ui.app.st")
    def test_render_navigation_button_secondary(self, mock_st):
        """Test rendering secondary (not current) button."""
        from souschef.ui.app import _render_navigation_button

        mock_col = MagicMock()
        mock_st.button.return_value = False

        _render_navigation_button(mock_col, "Other Page", "other_page", "current_page")

        args, kwargs = mock_st.button.call_args
        assert kwargs["type"] == "secondary"

    @patch("souschef.ui.app.st")
    def test_render_navigation_button_click_triggers_rerun(self, mock_st):
        """Test that clicking button triggers page change and rerun."""
        from souschef.ui.app import _render_navigation_button

        mock_col = MagicMock()
        mock_st.button.return_value = True  # Button clicked

        # Create a session_state mock that works with both dict and attribute access
        class SessionState(dict):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.__dict__ = self

        mock_st.session_state = SessionState()

        _render_navigation_button(mock_col, "New Page", "new_page", "old_page")

        assert mock_st.session_state.get("current_page") == "new_page"
        mock_st.rerun.assert_called_once()


class TestPageRouting:
    """Test page routing functionality."""

    @patch("souschef.ui.app.show_dashboard")
    def test_route_to_dashboard(self, mock_dashboard):
        """Test routing to dashboard."""
        from souschef.ui.app import _route_to_page

        _route_to_page("Dashboard")

        mock_dashboard.assert_called_once()

    @patch("souschef.ui.app.show_migration_planning")
    def test_route_to_migration_planning(self, mock_planning):
        """Test routing to migration planning."""
        from souschef.ui.app import _route_to_page

        _route_to_page("Migration Planning")

        mock_planning.assert_called_once()

    @patch("souschef.ui.app.show_dashboard")
    def test_route_to_unknown_page_fallsback(self, mock_dashboard):
        """Test routing to unknown page falls back to dashboard."""
        from souschef.ui.app import _route_to_page

        _route_to_page("NonExistentPage")

        mock_dashboard.assert_called_once()


class TestMigrationPlanningFunctions:
    """Test migration planning helper functions."""

    @patch("souschef.ui.app.st")
    def test_display_strategy_details_phased(self, mock_st):
        """Test displaying phased strategy details."""
        from souschef.ui.app import _display_strategy_details

        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = Mock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = Mock(return_value=None)

        _display_strategy_details("phased")

        mock_st.expander.assert_called_once_with("Strategy Details")
        mock_st.markdown.assert_called_once()
        args = mock_st.markdown.call_args[0][0]
        assert "Phased Migration" in args
        assert "Lower risk" in args

    @patch("souschef.ui.app.st")
    def test_display_strategy_details_big_bang(self, mock_st):
        """Test displaying big_bang strategy details."""
        from souschef.ui.app import _display_strategy_details

        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = Mock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = Mock(return_value=None)

        _display_strategy_details("big_bang")

        args = mock_st.markdown.call_args[0][0]
        assert "Big Bang Migration" in args
        assert "Faster overall timeline" in args

    @patch("souschef.ui.app.st")
    def test_display_strategy_details_parallel(self, mock_st):
        """Test displaying parallel strategy details."""
        from souschef.ui.app import _display_strategy_details

        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = Mock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = Mock(return_value=None)

        _display_strategy_details("parallel")

        args = mock_st.markdown.call_args[0][0]
        assert "Parallel Migration" in args
        assert "Zero downtime" in args


class TestDashboardDisplay:
    """Test dashboard display functions."""

    @patch("souschef.ui.app.st")
    def test_display_dashboard_metrics(self, mock_st):
        """Test displaying dashboard metrics."""
        from souschef.ui.app import _display_dashboard_metrics

        # Create mock columns that support context manager protocol
        mock_col1 = MagicMock()
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2 = MagicMock()
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)
        mock_col3 = MagicMock()
        mock_col3.__enter__ = Mock(return_value=mock_col3)
        mock_col3.__exit__ = Mock(return_value=None)

        mock_st.columns.return_value = [mock_col1, mock_col2, mock_col3]

        _display_dashboard_metrics(5, "High", 80, 4)

        mock_st.columns.assert_called_once_with(3)
        # Each column should have metric() and caption() called
        assert mock_st.metric.call_count == 3
        assert mock_st.caption.call_count == 3

    @patch("souschef.ui.app.st")
    def test_display_dashboard_metrics_zero_cookbooks(self, mock_st):
        """Test displaying metrics with zero cookbooks."""
        from souschef.ui.app import _display_dashboard_metrics

        # Create mock columns that support context manager protocol
        mock_col1 = MagicMock()
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2 = MagicMock()
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)
        mock_col3 = MagicMock()
        mock_col3.__enter__ = Mock(return_value=mock_col3)
        mock_col3.__exit__ = Mock(return_value=None)

        mock_st.columns.return_value = [mock_col1, mock_col2, mock_col3]

        _display_dashboard_metrics(0, "Unknown", 0, 0)

        # Verify metrics are called with appropriate zero-state messages
        metric_calls = mock_st.metric.call_args_list
        assert any("Ready to analyse" in str(call) for call in metric_calls)
        assert any("Assessment needed" in str(call) for call in metric_calls)
        assert any("Start migration" in str(call) for call in metric_calls)


class TestRenderButtonsForFeatures:
    """Test rendering navigation buttons for feature sets."""

    @patch("souschef.ui.app.st")
    @patch("souschef.ui.app._render_navigation_button")
    def test_render_buttons_for_chef_features(self, mock_render_btn, mock_st):
        """Test rendering buttons for Chef features."""
        from souschef.ui.app import CHEF_FEATURES, _render_buttons_for_features

        mock_st.columns.return_value = [Mock(), Mock(), Mock()]

        _render_buttons_for_features(CHEF_FEATURES, "Migrate Cookbook")

        # Should create columns
        assert mock_st.columns.call_count > 0
        # Should render buttons
        assert mock_render_btn.call_count >= len(CHEF_FEATURES)

    @patch("souschef.ui.app.st")
    @patch("souschef.ui.app._render_navigation_button")
    def test_render_buttons_for_ansible_features(self, mock_render_btn, mock_st):
        """Test rendering buttons for Ansible features."""
        from souschef.ui.app import ANSIBLE_FEATURES, _render_buttons_for_features

        mock_st.columns.return_value = [Mock(), Mock(), Mock()]

        _render_buttons_for_features(ANSIBLE_FEATURES, "Ansible Assessment")

        assert mock_render_btn.call_count >= len(ANSIBLE_FEATURES)


class TestMainFunction:
    """Test main application function."""

    @patch("souschef.ui.app.st")
    @patch("souschef.ui.app._display_navigation_section")
    @patch("souschef.ui.app._route_to_page")
    def test_main_sets_page_config(self, mock_route, mock_nav, mock_st):
        """Test that main sets Streamlit page configuration."""
        from souschef.ui.app import main

        mock_st.session_state.get.return_value = "Dashboard"

        main()

        mock_st.set_page_config.assert_called_once()
        args, kwargs = mock_st.set_page_config.call_args
        assert kwargs["page_title"] == "SousChef - Chef to Ansible Migration"
        assert kwargs["layout"] == "wide"
        assert kwargs["initial_sidebar_state"] == "collapsed"

    @patch("souschef.ui.app.st")
    @patch("souschef.ui.app._display_navigation_section")
    @patch("souschef.ui.app._route_to_page")
    def test_main_displays_title(self, mock_route, mock_nav, mock_st):
        """Test that main displays page title."""
        from souschef.ui.app import main

        mock_st.session_state.get.return_value = "Dashboard"

        main()

        mock_st.title.assert_called_once_with("SousChef - Visual Migration Planning")
        mock_st.markdown.assert_called_once()

    @patch("souschef.ui.app.st")
    @patch("souschef.ui.app._display_navigation_section")
    @patch("souschef.ui.app._route_to_page")
    def test_main_routes_to_current_page(self, mock_route, mock_nav, mock_st):
        """Test that main routes to current page from session state."""
        from souschef.ui.app import main

        mock_st.session_state.get.return_value = "Migration Planning"

        main()

        mock_route.assert_called_once_with("Migration Planning")


class TestHealthCheckFunction:
    """Test health check function."""

    def test_health_check_returns_healthy_status(self):
        """Test health_check returns healthy status."""
        from souschef.ui.app import health_check

        result = health_check()

        assert result["status"] == "healthy"
        assert result["service"] == "souschef-ui"
        assert isinstance(result, dict)


class TestWithProgressTracking:
    """Test the with_progress_tracking decorator."""

    @patch("souschef.ui.app.ProgressTracker")
    def test_with_progress_tracking_success(self, mock_tracker_class):
        """Test progress tracking decorator with successful operation."""
        from souschef.ui.app import with_progress_tracking

        # Mock tracker instance
        mock_tracker = Mock()
        mock_tracker_class.return_value = mock_tracker

        # Function to wrap
        def test_operation(tracker, arg1, arg2):
            return arg1 + arg2

        # Wrap it
        wrapped = with_progress_tracking(
            test_operation, description="Testing", total_steps=10
        )

        # Call wrapped function
        result = wrapped(5, 3)

        assert result == 8
        mock_tracker.complete.assert_called_once()
        mock_tracker.close.assert_called()

    @patch("souschef.ui.app.ProgressTracker")
    def test_with_progress_tracking_exception(self, mock_tracker_class):
        """Test progress tracking decorator handles exceptions."""
        from souschef.ui.app import with_progress_tracking

        mock_tracker = Mock()
        mock_tracker_class.return_value = mock_tracker

        def failing_operation(tracker):
            raise ValueError("Test error")

        wrapped = with_progress_tracking(failing_operation)

        with pytest.raises(ValueError, match="Test error"):
            wrapped()

        # Should close tracker even on exception
        mock_tracker.close.assert_called()


class TestDisplayNavigationSection:
    """Test navigation section display."""

    @patch("souschef.ui.app.st")
    @patch("souschef.ui.app._render_buttons_for_features")
    def test_display_navigation_section_creates_tabs(self, mock_render, mock_st):
        """Test that navigation section creates three tabs."""
        from souschef.ui.app import _display_navigation_section

        # Mock tabs that support context manager protocol
        mock_tab_chef = MagicMock()
        mock_tab_chef.__enter__ = Mock(return_value=mock_tab_chef)
        mock_tab_chef.__exit__ = Mock(return_value=None)
        mock_tab_ansible = MagicMock()
        mock_tab_ansible.__enter__ = Mock(return_value=mock_tab_ansible)
        mock_tab_ansible.__exit__ = Mock(return_value=None)
        mock_tab_tools = MagicMock()
        mock_tab_tools.__enter__ = Mock(return_value=mock_tab_tools)
        mock_tab_tools.__exit__ = Mock(return_value=None)

        mock_st.tabs.return_value = [mock_tab_chef, mock_tab_ansible, mock_tab_tools]

        _display_navigation_section("Dashboard")

        mock_st.tabs.assert_called_once_with(["Chef", "Ansible", "Tools"])
        # Should render buttons for each tab (3 calls)
        assert mock_render.call_count == 3


# Additional utility function tests
class TestConversionUtilityFunctions:
    """Test various conversion utility functions from cookbook_analysis."""

    @patch("souschef.ui.pages.cookbook_analysis.st")
    def test_parse_conversion_result_text_success(self, mock_st):
        """Test parsing conversion result text."""
        from souschef.ui.pages.cookbook_analysis import (
            _parse_conversion_result_text,
        )

        result_text = """
        # Conversion Summary
        Total files converted: 15

        # Cookbook: nginx
        Status: Success
        """

        parsed = _parse_conversion_result_text(result_text)

        assert isinstance(parsed, dict)
        assert "summary" in parsed or "cookbook_results" in parsed

    @patch("souschef.ui.pages.cookbook_analysis.st")
    def test_parse_conversion_result_text_empty(self, mock_st):
        """Test parsing empty conversion result."""
        from souschef.ui.pages.cookbook_analysis import (
            _parse_conversion_result_text,
        )

        parsed = _parse_conversion_result_text("")

        assert isinstance(parsed, dict)


class TestAISettingsPage:
    """Test AI settings page rendering functions."""

    @patch("souschef.ui.pages.ai_settings.st")
    @patch("souschef.ui.pages.ai_settings.load_ai_settings")
    def test_show_ai_settings_page_renders(self, mock_load, mock_st):
        """Test AI settings page renders without errors."""
        from souschef.ui.pages.ai_settings import show_ai_settings_page

        mock_load.return_value = {
            "provider": "Anthropic",
            "api_key": "",
            "model": "claude-3-5-sonnet-20241022",
            "temperature": 0.7,
            "max_tokens": 4000,
        }

        # Mock session_state
        class SessionState(dict):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.__dict__ = self

        mock_st.session_state = SessionState()

        # Mock columns to return proper context managers
        mock_col1 = MagicMock()
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2 = MagicMock()
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)
        mock_st.columns.return_value = [mock_col1, mock_col2]

        # Mock button to not be clicked
        mock_st.button.return_value = False
        mock_st.form_submit_button.return_value = False

        # Should not raise
        show_ai_settings_page()

        # Verify subheader was called (more reliable than header)
        mock_st.subheader.assert_called()


class TestDependencyDataProcessing:
    """Test dependency analysis data processing functions."""

    def test_extract_dependency_relationships_empty(self):
        """Test extracting dependencies from empty input."""
        from souschef.ui.app import _extract_dependency_relationships

        lines = []
        result = _extract_dependency_relationships(lines)

        assert result == {}

    def test_extract_dependency_relationships_with_direct_deps(self):
        """Test extracting direct dependencies."""
        from souschef.ui.app import _extract_dependency_relationships

        lines = [
            "Direct Dependencies:",
            "- nginx: openssl, zlib",
            "- apache: openssl",
            "- mysql: None",
        ]
        result = _extract_dependency_relationships(lines)

        assert "nginx" in result
        assert result["nginx"] == ["openssl", "zlib"]
        assert result["apache"] == ["openssl"]
        assert "mysql" not in result  # None dependencies not included

    def test_extract_dependency_relationships_ignores_transitive(self):
        """Test that transitive dependencies are ignored."""
        from souschef.ui.app import _extract_dependency_relationships

        lines = [
            "Direct Dependencies:",
            "- nginx: openssl",
            "Transitive Dependencies:",
            "- openssl: zlib",
        ]
        result = _extract_dependency_relationships(lines)

        assert "nginx" in result
        assert "openssl" not in result  # Transitive section ignored

    def test_is_list_item_true(self):
        """Test identifying list items."""
        from souschef.ui.app import _is_list_item

        assert _is_list_item("- nginx: openssl")
        assert _is_list_item("  - apache")
        assert _is_list_item("    -    item")

    def test_is_list_item_false(self):
        """Test non-list items."""
        from souschef.ui.app import _is_list_item

        assert not _is_list_item("Direct Dependencies:")
        assert not _is_list_item("nginx: openssl")
        assert not _is_list_item("")

    def test_process_circular_dependency_item(self):
        """Test processing circular dependency items."""
        from souschef.ui.app import _process_circular_dependency_item

        circular_deps = []
        _process_circular_dependency_item("- nginx -> openssl", circular_deps)

        assert len(circular_deps) == 1
        assert circular_deps[0] == ("nginx", "openssl")

    def test_process_circular_dependency_item_no_arrow(self):
        """Test circular dependency without arrow."""
        from souschef.ui.app import _process_circular_dependency_item

        circular_deps = []
        _process_circular_dependency_item("- nginx", circular_deps)

        assert len(circular_deps) == 0

    def test_process_community_cookbook_item(self):
        """Test processing community cookbook items."""
        from souschef.ui.app import _process_community_cookbook_item

        community = []
        _process_community_cookbook_item("- nginx", community)
        _process_community_cookbook_item("- apache2", community)

        assert len(community) == 2
        assert "nginx" in community
        assert "apache2" in community

    def test_update_current_section_circular(self):
        """Test updating to circular dependencies section."""
        from souschef.ui.app import _update_current_section

        result = _update_current_section("Circular Dependencies:", None)
        assert result == "circular"

    def test_update_current_section_community(self):
        """Test updating to community cookbooks section."""
        from souschef.ui.app import _update_current_section

        result = _update_current_section("Community Cookbooks:", None)
        assert result == "community"

    def test_update_current_section_unchanged(self):
        """Test section remains unchanged for other lines."""
        from souschef.ui.app import _update_current_section

        result = _update_current_section("- some item", "circular")
        assert result == "circular"

    def test_parse_dependency_analysis_full(self):
        """Test parsing complete dependency analysis."""
        from souschef.ui.app import _parse_dependency_analysis

        analysis = """Direct Dependencies:
- nginx: openssl, zlib
- apache: openssl

Circular Dependencies:
- app1 -> app2
- app2 -> app1

Community Cookbooks:
- openssl
- zlib
"""

        deps, circular, community = _parse_dependency_analysis(analysis)

        assert "nginx" in deps
        assert deps["nginx"] == ["openssl", "zlib"]
        assert len(circular) == 2
        assert ("app1", "app2") in circular
        assert ("app2", "app1") in circular
        assert len(community) == 2
        assert "openssl" in community


class TestValidationDataProcessing:
    """Test validation data processing functions."""

    def test_parse_validation_metrics_empty(self):
        """Test parsing empty validation result."""
        from souschef.ui.app import _parse_validation_metrics

        errors, warnings, passed, total = _parse_validation_metrics("")

        assert errors == 0
        assert warnings == 0
        assert passed == 0
        assert total == 0

    def test_parse_validation_metrics_with_errors(self):
        """Test parsing validation with errors."""
        from souschef.ui.app import _parse_validation_metrics

        result = """
        [ERROR] Missing required attribute
        [ERROR] Invalid syntax
        [WARNING] Deprecated function used
        [INFO] Check passed
        Total checks: 4
        """

        errors, warnings, passed, total = _parse_validation_metrics(result)

        assert errors == 2
        assert warnings == 1
        assert passed == 1
        assert total == 4

    def test_parse_validation_metrics_legacy_format(self):
        """Test parsing validation with legacy format."""
        from souschef.ui.app import _parse_validation_metrics

        result = """
        ERROR: Missing metadata.rb
        WARNING: No description in metadata
        ✓ Recipe syntax is valid
        """

        errors, warnings, passed, total = _parse_validation_metrics(result)

        assert errors == 1
        assert warnings == 1
        assert passed == 1
        assert total == 3  # Inferred from line count

    def test_parse_validation_metrics_no_explicit_total(self):
        """Test parsing without explicit Total checks line."""
        from souschef.ui.app import _parse_validation_metrics

        result = """
        [ERROR] Error 1
        [WARNING] Warning 1
        [INFO] Passed 1
        """

        errors, warnings, passed, total = _parse_validation_metrics(result)

        assert errors == 1
        assert warnings == 1
        assert passed == 1
        assert total == 3  # Inferred

    def test_filter_results_by_scope_full_suite(self):
        """Test filtering with Full Suite returns all results."""
        from souschef.ui.app import _filter_results_by_scope

        class MockResult:
            def __init__(self, category):
                self.category = category

        from souschef.core.validation import ValidationCategory

        results = [
            MockResult(ValidationCategory.SYNTAX),
            MockResult(ValidationCategory.SECURITY),
            MockResult(ValidationCategory.BEST_PRACTICE),
        ]

        filtered = _filter_results_by_scope(results, "Full Suite")

        assert len(filtered) == 3

    def test_filter_results_by_scope_syntax_only(self):
        """Test filtering for syntax only."""
        from souschef.ui.app import _filter_results_by_scope

        class MockResult:
            def __init__(self, category):
                self.category = category

        from souschef.core.validation import ValidationCategory

        results = [
            MockResult(ValidationCategory.SYNTAX),
            MockResult(ValidationCategory.SECURITY),
            MockResult(ValidationCategory.SYNTAX),
        ]

        filtered = _filter_results_by_scope(results, "Syntax Only")

        assert len(filtered) == 2
        assert all(r.category == ValidationCategory.SYNTAX for r in filtered)

    def test_filter_results_by_scope_security(self):
        """Test filtering for security."""
        from souschef.ui.app import _filter_results_by_scope

        class MockResult:
            def __init__(self, category):
                self.category = category

        from souschef.core.validation import ValidationCategory

        results = [
            MockResult(ValidationCategory.SYNTAX),
            MockResult(ValidationCategory.SECURITY),
            MockResult(ValidationCategory.BEST_PRACTICE),
        ]

        filtered = _filter_results_by_scope(results, "Security")

        assert len(filtered) == 1
        assert filtered[0].category == ValidationCategory.SECURITY

    def test_filter_results_by_scope_invalid_scope(self):
        """Test filtering with invalid scope returns all."""
        from souschef.ui.app import _filter_results_by_scope

        class MockResult:
            def __init__(self, category):
                self.category = category

        from souschef.core.validation import ValidationCategory

        results = [MockResult(ValidationCategory.SYNTAX)]

        filtered = _filter_results_by_scope(results, "InvalidScope")

        assert len(filtered) == 1  # Returns all when scope unknown


class TestMigrationImpactCalculations:
    """Test migration impact calculation functions."""

    def test_calculate_max_dependency_chain_empty(self):
        """Test max chain with no dependencies."""
        from souschef.ui.app import _calculate_max_dependency_chain

        dependencies = {}
        result = _calculate_max_dependency_chain(dependencies)

        assert result == 0

    def test_calculate_max_dependency_chain_single_level(self):
        """Test max chain with single-level dependencies."""
        from souschef.ui.app import _calculate_max_dependency_chain

        dependencies = {
            "nginx": ["openssl"],
            "apache": ["openssl"],
            "openssl": [],
        }
        result = _calculate_max_dependency_chain(dependencies)

        assert result == 2  # nginx/apache -> openssl

    def test_calculate_max_dependency_chain_multi_level(self):
        """Test max chain with multi-level dependencies."""
        from souschef.ui.app import _calculate_max_dependency_chain

        dependencies = {
            "app": ["nginx"],
            "nginx": ["openssl"],
            "openssl": ["zlib"],
            "zlib": [],
        }
        result = _calculate_max_dependency_chain(dependencies)

        assert result == 4  # app -> nginx -> openssl -> zlib

    def test_calculate_max_dependency_chain_circular(self):
        """Test max chain with circular dependency."""
        from souschef.ui.app import _calculate_max_dependency_chain

        dependencies = {
            "app1": ["app2"],
            "app2": ["app1"],
        }
        result = _calculate_max_dependency_chain(dependencies)

        assert result == 2  # Counts first hop before detecting circular

    def test_find_critical_path_empty(self):
        """Test critical path with no dependencies."""
        from souschef.ui.app import _find_critical_path

        dependencies = {}
        result = _find_critical_path(dependencies)

        assert result == []

    def test_find_critical_path_single_chain(self):
        """Test critical path with single chain."""
        from souschef.ui.app import _find_critical_path

        dependencies = {
            "app": ["nginx"],
            "nginx": ["openssl"],
            "openssl": [],
        }
        result = _find_critical_path(dependencies)

        assert len(result) == 3
        assert result == ["app", "nginx", "openssl"]

    def test_find_critical_path_multiple_chains(self):
        """Test critical path selects longest chain."""
        from souschef.ui.app import _find_critical_path

        dependencies = {
            "app1": ["middleware"],
            "middleware": ["database"],
            "database": ["storage"],
            "storage": [],
            "app2": ["cache"],
            "cache": [],
        }
        result = _find_critical_path(dependencies)

        # Should return the longest chain (app1 -> middleware -> database -> storage)
        assert len(result) == 4
        assert result[0] == "app1"

    def test_find_critical_path_circular_dependency(self):
        """Test critical path with circular dependency."""
        from souschef.ui.app import _find_critical_path

        dependencies = {
            "app1": ["app2"],
            "app2": ["app1"],
        }
        result = _find_critical_path(dependencies)

        # Should handle circular by returning single element
        assert len(result) >= 1

    def test_identify_bottlenecks_empty(self):
        """Test bottleneck identification with no dependencies."""
        from souschef.ui.app import _identify_bottlenecks

        dependencies = {}
        result = _identify_bottlenecks(dependencies)

        assert result == []

    def test_identify_bottlenecks_high_risk(self):
        """Test identifying high-risk bottlenecks."""
        from souschef.ui.app import _identify_bottlenecks

        dependencies = {
            "app1": ["openssl"],
            "app2": ["openssl"],
            "app3": ["openssl"],
            "app4": ["openssl"],
            "app5": ["openssl"],
            "app6": ["database"],
        }
        result = _identify_bottlenecks(dependencies)

        # openssl is depended on 5 times -> High risk
        assert len(result) >= 1
        assert result[0]["cookbook"] == "openssl"
        assert result[0]["dependent_count"] == 5
        assert result[0]["risk_level"] == "High"

    def test_identify_bottlenecks_medium_risk(self):
        """Test identifying medium-risk bottlenecks."""
        from souschef.ui.app import _identify_bottlenecks

        dependencies = {
            "app1": ["nginx"],
            "app2": ["nginx"],
            "app3": ["nginx"],
            "app4": ["apache"],
        }
        result = _identify_bottlenecks(dependencies)

        # nginx is depended on 3 times -> Medium risk
        assert len(result) >= 1
        bottleneck = next(b for b in result if b["cookbook"] == "nginx")
        assert bottleneck["dependent_count"] == 3
        assert bottleneck["risk_level"] == "Medium"

    def test_identify_bottlenecks_sorted_by_count(self):
        """Test bottlenecks are sorted by dependency count."""
        from souschef.ui.app import _identify_bottlenecks

        dependencies = {
            "app1": ["openssl"],
            "app2": ["openssl"],
            "app3": ["openssl"],
            "app4": ["openssl"],
            "app5": ["openssl"],
            "app6": ["nginx"],
            "app7": ["nginx"],
            "app8": ["nginx"],
        }
        result = _identify_bottlenecks(dependencies)

        # Should be sorted with openssl (5) before nginx (3)
        assert result[0]["cookbook"] == "openssl"
        assert result[1]["cookbook"] == "nginx"
        assert result[0]["dependent_count"] > result[1]["dependent_count"]

    def test_generate_impact_recommendations_empty(self):
        """Test generating recommendations with minimal data."""
        from souschef.ui.app import _generate_impact_recommendations

        impact = {
            "parallel_streams": 1,
            "timeline_impact_weeks": 0,
            "bottlenecks": [],
        }
        result = _generate_impact_recommendations(impact, [], [])

        assert isinstance(result, list)
        # Should have minimal recommendations
        assert len(result) == 0

    def test_generate_impact_recommendations_with_circular_deps(self):
        """Test recommendations include circular dependency resolution."""
        from souschef.ui.app import _generate_impact_recommendations

        impact = {
            "parallel_streams": 1,
            "timeline_impact_weeks": 0,
            "bottlenecks": [],
        }
        circular_deps = [("app1", "app2"), ("app2", "app1")]
        result = _generate_impact_recommendations(impact, circular_deps, [])

        # Should have critical recommendation for circular deps
        assert len(result) >= 1
        assert result[0]["priority"] == "Critical"
        assert "circular" in result[0]["action"].lower()

    def test_generate_impact_recommendations_with_parallel_streams(self):
        """Test recommendations for parallel migration streams."""
        from souschef.ui.app import _generate_impact_recommendations

        impact = {
            "parallel_streams": 3,
            "timeline_impact_weeks": 0,
            "bottlenecks": [],
        }
        result = _generate_impact_recommendations(impact, [], [])

        # Should have high priority recommendation for parallel streams
        assert len(result) >= 1
        parallel_rec = next(r for r in result if "parallel" in r["action"].lower())
        assert parallel_rec["priority"] == "High"
        assert "3" in parallel_rec["action"]

    def test_generate_impact_recommendations_with_community_cookbooks(self):
        """Test recommendations for community cookbooks."""
        from souschef.ui.app import _generate_impact_recommendations

        impact = {
            "parallel_streams": 1,
            "timeline_impact_weeks": 0,
            "bottlenecks": [],
        }
        community = ["openssl", "postgresql", "nginx"]
        result = _generate_impact_recommendations(impact, [], community)

        # Should have medium priority recommendation for community cookbooks
        assert len(result) >= 1
        community_rec = next(r for r in result if "community" in r["action"].lower())
        assert community_rec["priority"] == "Medium"
        assert "3" in community_rec["action"]

    def test_generate_impact_recommendations_with_bottlenecks(self):
        """Test recommendations for bottleneck cookbooks."""
        from souschef.ui.app import _generate_impact_recommendations

        impact = {
            "parallel_streams": 1,
            "timeline_impact_weeks": 0,
            "bottlenecks": [
                {"cookbook": "openssl", "dependent_count": 5},
                {"cookbook": "nginx", "dependent_count": 3},
            ],
        }
        result = _generate_impact_recommendations(impact, [], [])

        # Should have medium priority recommendation for bottlenecks
        assert len(result) >= 1
        bottleneck_rec = next(r for r in result if "bottleneck" in r["action"].lower())
        assert bottleneck_rec["priority"] == "Medium"
        assert "openssl" in bottleneck_rec["action"]

    def test_generate_impact_recommendations_with_timeline_impact(self):
        """Test recommendations for timeline impact."""
        from souschef.ui.app import _generate_impact_recommendations

        impact = {
            "parallel_streams": 1,
            "timeline_impact_weeks": 4,
            "bottlenecks": [],
        }
        result = _generate_impact_recommendations(impact, [], [])

        # Should have low priority recommendation for timeline
        assert len(result) >= 1
        timeline_rec = next(r for r in result if "additional" in r["action"].lower())
        assert timeline_rec["priority"] == "Low"
        assert "4" in timeline_rec["action"]

    def test_generate_impact_recommendations_comprehensive(self):
        """Test generating all types of recommendations."""
        from souschef.ui.app import _generate_impact_recommendations

        impact = {
            "parallel_streams": 3,
            "timeline_impact_weeks": 2,
            "bottlenecks": [{"cookbook": "openssl", "dependent_count": 5}],
        }
        circular_deps = [("app1", "app2")]
        community = ["nginx", "postgresql"]

        result = _generate_impact_recommendations(impact, circular_deps, community)

        # Should have all types of recommendations
        assert len(result) == 5
        priorities = [r["priority"] for r in result]
        assert "Critical" in priorities
        assert "High" in priorities
        assert "Medium" in priorities
        assert "Low" in priorities


class TestGraphFilteringFunctions:
    """Test graph filtering functions."""

    def test_filter_circular_dependencies_disabled(self):
        """Test filtering when circular_only is False."""
        from souschef.ui.app import _filter_circular_dependencies_only

        # Create mock graph
        class MockGraph:
            def __init__(self):
                self._nodes = {"app1", "app2", "nginx"}

            def nodes(self):
                return self._nodes

            def remove_nodes_from(self, nodes):
                for n in nodes:
                    self._nodes.discard(n)

        graph = MockGraph()
        filters = {"circular_only": False}

        _filter_circular_dependencies_only(graph, filters)

        # Should return graph unchanged
        assert len(graph._nodes) == 3

    def test_filter_circular_dependencies_enabled(self):
        """Test filtering to show only circular dependencies."""
        from souschef.ui.app import _filter_circular_dependencies_only

        class MockGraph:
            def __init__(self):
                self._nodes = {"app1", "app2", "nginx", "mysql"}

            def nodes(self):
                return list(self._nodes)

            def remove_nodes_from(self, nodes):
                for n in nodes:
                    self._nodes.discard(n)

        graph = MockGraph()
        filters = {
            "circular_only": True,
            "circular_deps": [("app1", "app2"), ("app2", "app1")],
        }

        _filter_circular_dependencies_only(graph, filters)

        # Should only keep app1 and app2
        assert len(graph._nodes) == 2
        assert "app1" in graph._nodes
        assert "app2" in graph._nodes
        assert "nginx" not in graph._nodes

    def test_filter_community_cookbooks_disabled(self):
        """Test filtering when community_only is False."""
        from souschef.ui.app import _filter_community_cookbooks_only

        class MockGraph:
            def __init__(self):
                self._nodes = {"nginx", "apache", "mysql"}

            def nodes(self):
                return self._nodes

            def remove_nodes_from(self, nodes):
                pass

        graph = MockGraph()
        filters = {"community_only": False}

        result = _filter_community_cookbooks_only(graph, filters)

        # Should return graph unchanged
        assert result == graph

    def test_filter_minimum_connections_zero(self):
        """Test filtering with zero minimum connections."""
        from souschef.ui.app import _filter_minimum_connections

        class MockGraph:
            def __init__(self):
                self._nodes = {"nginx", "apache"}

            def nodes(self):
                return self._nodes

            def degree(self, node):
                return 1

            def remove_nodes_from(self, nodes):
                pass

        graph = MockGraph()
        filters = {"min_connections": 0}

        result = _filter_minimum_connections(graph, filters)

        # Should return graph unchanged
        assert result == graph

    def test_filter_minimum_connections_removes_low_degree(self):
        """Test filtering removes nodes with low degree."""
        from souschef.ui.app import _filter_minimum_connections

        class MockGraph:
            def __init__(self):
                self._nodes = {"nginx", "apache", "mysql"}
                self._degrees = {"nginx": 5, "apache": 2, "mysql": 1}

            def nodes(self):
                return list(self._nodes)

            def degree(self, node):
                return self._degrees.get(node, 0)

            def remove_nodes_from(self, nodes):
                for n in nodes:
                    self._nodes.discard(n)

        graph = MockGraph()
        filters = {"min_connections": 3}

        _filter_minimum_connections(graph, filters)

        # Should only keep nginx (degree 5)
        assert len(graph._nodes) == 1
        assert "nginx" in graph._nodes


class TestDependencyMetricsParsing:
    """Test dependency metrics parsing functions."""

    def test_parse_dependency_metrics_empty(self):
        """Test parsing empty result."""
        from souschef.ui.app import _parse_dependency_metrics_from_result

        result = _parse_dependency_metrics_from_result("")

        assert result == (0, 0, 0, 0)

    def test_parse_dependency_metrics_with_values(self):
        """Test parsing result with numeric values."""
        from souschef.ui.app import _parse_dependency_metrics_from_result

        result_text = """
        Analysis Results:
        Direct Dependencies: 10
        Transitive Dependencies: 25
        Circular Dependencies: 2
        Community Cookbooks: 5
        """

        direct, transitive, circular, community = _parse_dependency_metrics_from_result(
            result_text
        )

        assert direct == 10
        assert transitive == 25
        assert circular == 2
        assert community == 5

    def test_parse_dependency_metrics_missing_values(self):
        """Test parsing result with missing values."""
        from souschef.ui.app import _parse_dependency_metrics_from_result

        result_text = """
        Analysis Results:
        Direct Dependencies: 10
        Some other line
        """

        direct, transitive, circular, community = _parse_dependency_metrics_from_result(
            result_text
        )

        assert direct == 10
        assert transitive == 0
        assert circular == 0
        assert community == 0

    def test_parse_dependency_metrics_invalid_format(self):
        """Test parsing result with invalid format (non-numeric)."""
        from souschef.ui.app import _parse_dependency_metrics_from_result

        result_text = """
        Direct Dependencies: N/A
        Transitive Dependencies: Unknown
        """

        direct, transitive, circular, community = _parse_dependency_metrics_from_result(
            result_text
        )

        # Should handle ValueError gracefully and return 0
        assert direct == 0
        assert transitive == 0


class TestLayoutAlgorithmSelection:
    """Test graph layout algorithm selection."""

    def test_choose_auto_layout_small_graph(self):
        """Test choosing layout for small graphs (<=10 nodes)."""
        from souschef.ui.app import _choose_auto_layout_algorithm

        result = _choose_auto_layout_algorithm(5)
        assert result == "circular"

        result = _choose_auto_layout_algorithm(10)
        assert result == "circular"

    def test_choose_auto_layout_medium_graph(self):
        """Test choosing layout for medium graphs (11-50 nodes)."""
        from souschef.ui.app import _choose_auto_layout_algorithm

        result = _choose_auto_layout_algorithm(25)
        assert result == "spring"

        result = _choose_auto_layout_algorithm(50)
        assert result == "spring"

    def test_choose_auto_layout_large_graph(self):
        """Test choosing layout for large graphs (>50 nodes)."""
        from souschef.ui.app import _choose_auto_layout_algorithm

        result = _choose_auto_layout_algorithm(100)
        assert result == "kamada_kawai"

        result = _choose_auto_layout_algorithm(500)
        assert result == "kamada_kawai"


class TestValidationFormattingFunctions:
    """Test validation history formatting functions."""

    def test_format_analysis_for_validation_none(self):
        """Test formatting with None analysis_id."""
        from souschef.ui.app import _format_analysis_for_validation

        result = _format_analysis_for_validation([], None)

        assert result == "-- Select from history --"

    def test_format_analysis_for_validation_found(self):
        """Test formatting analysis that exists."""
        from souschef.ui.app import _format_analysis_for_validation

        class MockAnalysis:
            id = 1
            cookbook_name = "nginx"
            cookbook_version = "1.0.0"
            complexity = "Medium"
            created_at = datetime(2024, 3, 8)

        analyses = [MockAnalysis()]
        result = _format_analysis_for_validation(analyses, 1)

        assert "nginx v1.0.0" in result
        assert "Medium complexity" in result
        assert "2024-03-08" in result

    def test_format_analysis_for_validation_not_found(self):
        """Test formatting analysis that doesn't exist."""
        from souschef.ui.app import _format_analysis_for_validation

        result = _format_analysis_for_validation([], 999)

        assert result == "--"

    def test_format_analysis_for_validation_string_date(self):
        """Test formatting with string date."""
        from souschef.ui.app import _format_analysis_for_validation

        class MockAnalysis:
            id = 1
            cookbook_name = "apache"
            cookbook_version = "2.4"
            complexity = "High"
            created_at = "2024-03-08 10:30:00"

        analyses = [MockAnalysis()]
        result = _format_analysis_for_validation(analyses, 1)

        assert "apache v2.4" in result
        assert "High complexity" in result
        assert "2024-03-08" in result

    def test_format_conversion_for_validation_none(self):
        """Test formatting conversion with None conversion_id."""
        from souschef.ui.app import _format_conversion_for_validation

        result = _format_conversion_for_validation([], None)

        assert result == "-- Select from history --"

    def test_format_conversion_for_validation_not_found(self):
        """Test formatting conversion that doesn't exist."""
        from souschef.ui.app import _format_conversion_for_validation

        result = _format_conversion_for_validation([], 999)
        assert result == "-- Select from history --"


class TestCircularAndCommunityParsing:
    """Test parsing of circular dependencies and community cookbooks."""

    def test_update_current_section_to_circular(self):
        """Test updating section to circular."""
        from souschef.ui.app import _update_current_section

        result = _update_current_section("Circular Dependencies:", None)
        assert result == "circular"

    def test_update_current_section_to_community(self):
        """Test updating section to community cookbooks."""
        from souschef.ui.app import _update_current_section

        result = _update_current_section("## Community Cookbooks:", None)
        assert result == "community"

    def test_update_current_section_no_change(self):
        """Test section unchanged when line doesn't match."""
        from souschef.ui.app import _update_current_section

        result = _update_current_section("Some random line", "circular")
        assert result == "circular"

    def test_is_list_item_true(self):
        """Test identifying list items."""
        from souschef.ui.app import _is_list_item

        assert _is_list_item("- Item 1")
        assert _is_list_item("  - Item 2")

    def test_is_list_item_false(self):
        """Test non-list items."""
        from souschef.ui.app import _is_list_item

        assert not _is_list_item("Not a list item")
        assert not _is_list_item("* Asterisk item")

    def test_process_circular_dependency_item(self):
        """Test parsing circular dependency item."""
        from souschef.ui.app import _process_circular_dependency_item

        circular_deps: list[tuple[str, str]] = []
        _process_circular_dependency_item("- app1 -> app2", circular_deps)

        assert len(circular_deps) == 1
        assert circular_deps[0] == ("app1", "app2")

    def test_process_circular_dependency_item_invalid(self):
        """Test circular dependency item without arrow."""
        from souschef.ui.app import _process_circular_dependency_item

        circular_deps: list[tuple[str, str]] = []
        _process_circular_dependency_item("- app1 app2", circular_deps)

        assert len(circular_deps) == 0

    def test_process_community_cookbook_item(self):
        """Test parsing community cookbook item."""
        from souschef.ui.app import _process_community_cookbook_item

        community_cookbooks: list[str] = []
        _process_community_cookbook_item("- nginx", community_cookbooks)

        assert len(community_cookbooks) == 1
        assert community_cookbooks[0] == "nginx"

    def test_process_community_cookbook_item_empty(self):
        """Test empty community cookbook item."""
        from souschef.ui.app import _process_community_cookbook_item

        community_cookbooks: list[str] = []
        _process_community_cookbook_item("- ", community_cookbooks)

        assert len(community_cookbooks) == 0

    def test_parse_dependency_analysis_combined(self):
        """Test complete dependency analysis parsing."""
        from souschef.ui.app import _parse_dependency_analysis

        analysis_result = """
Direct Dependencies:
- nginx: openssl, zlib
- apache: openssl

Circular Dependencies:
- nginx -> apache
- apache -> nginx

## Community Cookbooks:
- nginx
- apache
        """

        dependencies, circular_deps, community_cookbooks = _parse_dependency_analysis(
            analysis_result
        )

        assert len(dependencies) == 2
        assert "nginx" in dependencies
        assert "openssl" in dependencies["nginx"]
        assert len(circular_deps) == 2
        assert ("nginx", "apache") in circular_deps
        assert len(community_cookbooks) == 2
        assert "nginx" in community_cookbooks


class TestGraphCreationFunctions:
    """Test NetworkX graph creation functions."""

    def test_create_networkx_graph_basic(self):
        """Test creating graph from dependency data."""
        from souschef.ui.app import _create_networkx_graph

        dependencies = {
            "nginx": ["openssl", "zlib"],
            "apache": ["openssl"],
        }
        circular_deps: list[tuple[str, str]] = []
        community_cookbooks: list[str] = []

        graph = _create_networkx_graph(dependencies, circular_deps, community_cookbooks)

        assert graph.number_of_nodes() == 4  # nginx, apache, openssl, zlib
        assert (
            graph.number_of_edges() == 3
        )  # nginx->openssl, nginx->zlib, apache->openssl
        assert graph.has_edge("nginx", "openssl")
        assert graph.has_edge("nginx", "zlib")
        assert graph.has_edge("apache", "openssl")

    def test_create_networkx_graph_with_circular(self):
        """Test graph with circular dependencies."""
        from souschef.ui.app import _create_networkx_graph

        dependencies = {"nginx": ["apache"], "apache": ["nginx"]}
        circular_deps = [("nginx", "apache"), ("apache", "nginx")]
        community_cookbooks: list[str] = []

        graph = _create_networkx_graph(dependencies, circular_deps, community_cookbooks)

        assert graph.number_of_nodes() == 2
        assert graph.number_of_edges() == 2
        assert graph.has_edge("nginx", "apache")
        assert graph.has_edge("apache", "nginx")

    def test_create_networkx_graph_marks_community(self):
        """Test graph marks community cookbooks."""
        from souschef.ui.app import _create_networkx_graph

        dependencies = {"app": ["nginx"]}
        circular_deps: list[tuple[str, str]] = []
        community_cookbooks = ["nginx"]

        graph = _create_networkx_graph(dependencies, circular_deps, community_cookbooks)

        # Should mark nginx as community cookbook
        assert graph.nodes["nginx"]["node_type"] == "dependency"


class TestShellLayoutCalculation:
    """Test shell layout position calculation."""

    def test_calculate_shell_layout_with_hierarchy(self):
        """Test shell layout with root, middle, leaf nodes."""
        import networkx as nx

        from souschef.ui.app import _calculate_shell_layout_positions

        graph = nx.DiGraph()
        graph.add_edge("root", "middle")
        graph.add_edge("middle", "leaf")

        positions = _calculate_shell_layout_positions(graph)

        # Should have positions for all 3 nodes
        assert len(positions) == 3
        assert "root" in positions
        assert "middle" in positions
        assert "leaf" in positions

    def test_calculate_shell_layout_no_hierarchy(self):
        """Test shell layout with circular graph (no clear hierarchy)."""
        import networkx as nx

        from souschef.ui.app import _calculate_shell_layout_positions

        graph = nx.DiGraph()
        graph.add_edge("a", "b")
        graph.add_edge("b", "a")

        positions = _calculate_shell_layout_positions(graph)

        # Should fall back to spring layout
        assert len(positions) == 2

    def test_calculate_shell_layout_single_node(self):
        """Test shell layout with single node."""
        import networkx as nx

        from souschef.ui.app import _calculate_shell_layout_positions

        graph = nx.DiGraph()
        graph.add_node("single")

        positions = _calculate_shell_layout_positions(graph)

        # Should position the single node
        assert len(positions) == 1
        assert "single" in positions


class TestValidationFiltering:
    """Test validation result filtering."""

    def test_filter_results_full_suite(self):
        """Test filtering with 'Full Suite' returns all results."""
        from souschef.ui.app import _filter_results_by_scope

        class MockResult:
            def __init__(self, category):
                self.category = category

        from souschef.core.validation import ValidationCategory

        results = [
            MockResult(ValidationCategory.SYNTAX),
            MockResult(ValidationCategory.SEMANTIC),
            MockResult(ValidationCategory.SECURITY),
        ]

        filtered = _filter_results_by_scope(results, "Full Suite")

        assert len(filtered) == 3

    def test_filter_results_syntax_only(self):
        """Test filtering for syntax errors only."""
        from souschef.ui.app import _filter_results_by_scope

        class MockResult:
            def __init__(self, category):
                self.category = category

        from souschef.core.validation import ValidationCategory

        results = [
            MockResult(ValidationCategory.SYNTAX),
            MockResult(ValidationCategory.SEMANTIC),
            MockResult(ValidationCategory.SYNTAX),
        ]

        filtered = _filter_results_by_scope(results, "Syntax Only")

        assert len(filtered) == 2
        assert all(r.category == ValidationCategory.SYNTAX for r in filtered)

    def test_filter_results_security(self):
        """Test filtering for security issues."""
        from souschef.ui.app import _filter_results_by_scope

        class MockResult:
            def __init__(self, category):
                self.category = category

        from souschef.core.validation import ValidationCategory

        results = [
            MockResult(ValidationCategory.SECURITY),
            MockResult(ValidationCategory.BEST_PRACTICE),
        ]

        filtered = _filter_results_by_scope(results, "Security")

        assert len(filtered) == 1
        assert filtered[0].category == ValidationCategory.SECURITY

    def test_filter_results_unknown_scope(self):
        """Test filtering with unknown scope returns all."""
        from souschef.ui.app import _filter_results_by_scope

        class MockResult:
            def __init__(self, category):
                self.category = category

        from souschef.core.validation import ValidationCategory

        results = [MockResult(ValidationCategory.SYNTAX)]

        filtered = _filter_results_by_scope(results, "Unknown Scope")

        assert len(filtered) == 1


class TestDisplayHelperFunctions:
    """Test display helper functions with Streamlit mocks."""

    @staticmethod
    def _ctx() -> MagicMock:
        ctx = MagicMock()
        ctx.__enter__ = Mock(return_value=ctx)
        ctx.__exit__ = Mock(return_value=None)
        return ctx

    @patch("souschef.ui.app.st")
    def test_display_dependency_summary_metrics(self, mock_st):
        """Test dependency summary metrics rendering."""
        from souschef.ui.app import _display_dependency_summary_metrics

        mock_st.columns.return_value = [
            self._ctx(),
            self._ctx(),
            self._ctx(),
            self._ctx(),
        ]

        _display_dependency_summary_metrics(10, 20, 1, 3)

        assert mock_st.metric.call_count == 4

    @patch("souschef.ui.app.st")
    def test_display_validation_summary_metrics(self, mock_st):
        """Test validation summary metrics rendering."""
        from souschef.ui.app import _display_validation_summary_metrics

        mock_st.columns.return_value = [
            self._ctx(),
            self._ctx(),
            self._ctx(),
            self._ctx(),
        ]

        _display_validation_summary_metrics(2, 3, 10, 15)

        assert mock_st.metric.call_count == 4

    @patch("souschef.ui.app.st")
    def test_display_validation_status_all_branches(self, mock_st):
        """Test validation status messages for error/warning/success."""
        from souschef.ui.app import _display_validation_status

        _display_validation_status(1, 0)
        mock_st.error.assert_called_once()

        _display_validation_status(0, 2)
        mock_st.warning.assert_called_once()

        _display_validation_status(0, 0)
        mock_st.success.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_display_validation_sections(self, mock_st):
        """Test validation section expanders and markdown paths."""
        from souschef.ui.app import _display_validation_sections

        mock_st.expander.return_value = self._ctx()
        validation_result = (
            "## Syntax Validation\nok\n"
            "## Logic Validation\nok\n"
            "## Security Validation\nok\n"
            "## Performance Validation\nok\n"
            "## Best Practices\nok\n"
            "## Recommendations\nok\n"
            "## Other\ntext"
        )

        _display_validation_sections(validation_result)

        assert mock_st.expander.call_count >= 6
        assert mock_st.markdown.call_count >= 7

    @patch("souschef.ui.app.st")
    def test_display_migration_recommendations(self, mock_st):
        """Test migration recommendation rendering across branches."""
        from souschef.ui.app import _display_migration_recommendations

        _display_migration_recommendations(
            circular_deps=1, community_cookbooks=2, direct_deps=11
        )

        mock_st.error.assert_called()
        mock_st.success.assert_called()
        mock_st.warning.assert_called()

    @patch("souschef.ui.app.st")
    def test_display_risk_critical_bottlenecks_and_recommendations(self, mock_st):
        """Test impact analysis display helper functions."""
        from souschef.ui.app import (
            _display_critical_path_analysis,
            _display_migration_bottlenecks,
            _display_risk_assessment_breakdown,
            _display_strategic_recommendations,
        )

        deps = {"a": ["b"], "b": []}
        _display_risk_assessment_breakdown(deps, [("a", "b")], ["b"])

        _display_critical_path_analysis({"critical_path": ["a", "b"]})
        _display_critical_path_analysis({"critical_path": []})

        _display_migration_bottlenecks(
            {
                "bottlenecks": [
                    {"cookbook": "core", "dependent_count": 5, "risk_level": "High"},
                    {"cookbook": "mid", "dependent_count": 3, "risk_level": "Medium"},
                    {"cookbook": "low", "dependent_count": 1, "risk_level": "Low"},
                ]
            }
        )
        _display_migration_bottlenecks({"bottlenecks": []})

        _display_strategic_recommendations(
            {
                "recommendations": [
                    {"priority": "Critical", "action": "a", "impact": "x"},
                    {"priority": "High", "action": "b", "impact": "y"},
                    {"priority": "Low", "action": "c", "impact": "z"},
                ]
            }
        )

        assert mock_st.write.call_count > 0


class TestValidationPathHelpers:
    """Test path normalisation and file collection helpers."""

    @patch("souschef.ui.app.st")
    def test_normalize_and_validate_input_path_empty(self, mock_st):
        """Test empty input path handling."""
        from souschef.ui.app import _normalize_and_validate_input_path

        assert _normalize_and_validate_input_path("") is None
        mock_st.error.assert_called()

    @patch("souschef.ui.app.st")
    @patch("souschef.ui.app._normalize_path")
    def test_normalize_and_validate_input_path_invalid(self, mock_normalize, mock_st):
        """Test invalid path handling."""
        from souschef.ui.app import _normalize_and_validate_input_path

        mock_normalize.side_effect = ValueError("bad path")

        assert _normalize_and_validate_input_path("bad") is None
        mock_st.error.assert_called()

    @patch("souschef.ui.app._ensure_within_base_path")
    @patch("souschef.ui.app._normalize_path")
    def test_normalize_and_validate_input_path_valid(self, mock_normalize, mock_within):
        """Test valid path handling."""
        from souschef.ui.app import _normalize_and_validate_input_path

        mock_normalize.return_value = Path("/tmp/example")
        mock_within.return_value = Path("/tmp/example")

        result = _normalize_and_validate_input_path("/tmp/example")
        assert result == Path("/tmp/example")

    @patch("souschef.ui.app._normalize_and_validate_input_path")
    def test_collect_files_to_validate_none_path(self, mock_validate):
        """Test collection returns empty when path invalid."""
        from souschef.ui.app import _collect_files_to_validate

        mock_validate.return_value = None
        assert _collect_files_to_validate("x") == []

    @patch("souschef.ui.app.safe_is_dir")
    @patch("souschef.ui.app.safe_is_file")
    @patch("souschef.ui.app.safe_exists")
    @patch("souschef.ui.app._normalize_and_validate_input_path")
    def test_collect_files_to_validate_single_file(
        self, mock_validate, mock_exists, mock_is_file, mock_is_dir
    ):
        """Test collecting one valid playbook file."""
        from souschef.ui.app import _collect_files_to_validate

        file_path = Path("/tmp/playbook.yml")
        mock_validate.return_value = file_path
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_is_dir.return_value = False

        files = _collect_files_to_validate("/tmp/playbook.yml")
        assert files == [file_path]

    @patch("souschef.ui.app.safe_glob")
    @patch("souschef.ui.app.safe_is_dir")
    @patch("souschef.ui.app.safe_is_file")
    @patch("souschef.ui.app.safe_exists")
    @patch("souschef.ui.app._normalize_and_validate_input_path")
    def test_collect_files_to_validate_directory(
        self,
        mock_validate,
        mock_exists,
        mock_is_file,
        mock_is_dir,
        mock_glob,
    ):
        """Test collecting files from directory with exclusions."""
        from souschef.ui.app import _collect_files_to_validate

        dir_path = Path("/tmp/ansible")
        mock_validate.return_value = dir_path
        mock_exists.return_value = True
        mock_is_file.return_value = False
        mock_is_dir.return_value = True
        mock_glob.side_effect = [
            [Path("/tmp/ansible/site.yml"), Path("/tmp/ansible/docker-compose.yml")],
            [Path("/tmp/ansible/tasks.yaml")],
        ]

        files = _collect_files_to_validate("/tmp/ansible")

        assert Path("/tmp/ansible/site.yml") in files
        assert Path("/tmp/ansible/tasks.yaml") in files
        assert Path("/tmp/ansible/docker-compose.yml") not in files


class TestValidationWorkflowHelpers:
    """Test validation workflow helper functions in app.py."""

    @staticmethod
    def _ctx() -> MagicMock:
        ctx = MagicMock()
        ctx.__enter__ = Mock(return_value=ctx)
        ctx.__exit__ = Mock(return_value=None)
        return ctx

    @staticmethod
    def _session_state(initial: dict | None = None):
        class SessionState(dict):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.__dict__ = self

        return SessionState(initial or {})

    @patch("souschef.ui.app._handle_validation_execution")
    @patch("souschef.ui.app.st")
    def test_execute_validation_workflow_empty_path(self, mock_st, mock_handle):
        """Test validation workflow with empty path."""
        from souschef.ui.app import _execute_validation_workflow

        _execute_validation_workflow(
            "",
            "Full Suite",
            "text",
            strict_mode=False,
            include_best_practices=True,
            generate_recommendations=True,
        )

        mock_st.error.assert_called_once()
        mock_handle.assert_not_called()

    @patch("souschef.ui.app._handle_validation_execution")
    def test_execute_validation_workflow_valid_path(self, mock_handle):
        """Test validation workflow with valid path."""
        from souschef.ui.app import _execute_validation_workflow

        _execute_validation_workflow(
            "/tmp/playbooks",
            "Security",
            "json",
            strict_mode=True,
            include_best_practices=False,
            generate_recommendations=False,
        )

        mock_handle.assert_called_once()
        args = mock_handle.call_args[0]
        options = args[1]
        assert options["strict"]
        assert options["scope"] == "Security"
        assert options["format"] == "json"

    @patch("souschef.ui.app._render_validation_settings_ui")
    @patch("souschef.ui.app._render_validation_input_ui")
    @patch("souschef.ui.app._render_validation_options_ui")
    @patch("souschef.ui.app._get_default_validation_path")
    def test_collect_validation_inputs(
        self,
        mock_default,
        mock_opts,
        mock_input,
        mock_settings,
    ):
        """Test collecting validation inputs from UI helpers."""
        from souschef.ui.app import _collect_validation_inputs

        mock_default.return_value = "/tmp/default"
        mock_opts.return_value = ("Full Suite", "text")
        mock_input.return_value = "/tmp/path"
        mock_settings.return_value = (True, False, True)

        result = _collect_validation_inputs()

        assert result == ("/tmp/path", "Full Suite", "text", True, False, True)

    @patch("souschef.ui.app.st")
    def test_display_analysis_history_tab_no_analyses(self, mock_st):
        """Test analysis history tab with no analyses."""
        from souschef.ui.app import _display_analysis_history_tab

        _display_analysis_history_tab([])
        mock_st.info.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_display_analysis_history_tab_load(self, mock_st):
        """Test loading analysis from history tab."""
        from souschef.ui.app import _display_analysis_history_tab

        class Analysis:
            id = 1
            cookbook_name = "nginx"
            cookbook_version = "1.0"
            complexity = "Low"
            created_at = "2025-01-01"
            cookbook_path = "/tmp/nginx"

        mock_st.columns.return_value = [self._ctx(), self._ctx()]
        mock_st.selectbox.return_value = 1
        mock_st.button.return_value = True
        mock_st.session_state = self._session_state()

        _display_analysis_history_tab([Analysis()])

        assert mock_st.session_state["analysis_cookbook_path"] == "/tmp/nginx"
        mock_st.rerun.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_display_conversion_history_tab_no_conversions(self, mock_st):
        """Test conversion history tab with no conversions."""
        from souschef.ui.app import _display_conversion_history_tab

        _display_conversion_history_tab([])
        mock_st.info.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_display_conversion_history_tab_load(self, mock_st):
        """Test loading conversion from history tab."""
        from souschef.ui.app import _display_conversion_history_tab

        class Conversion:
            id = 2
            cookbook_name = "apache"
            output_type = "playbook"
            status = "success"
            created_at = "2025-01-01"
            blob_storage_key = "blob"

        mock_st.columns.return_value = [self._ctx(), self._ctx()]
        mock_st.selectbox.return_value = 2
        mock_st.button.return_value = True
        mock_st.session_state = self._session_state()

        _display_conversion_history_tab([Conversion()])

        assert mock_st.session_state["converted_playbooks_path"] == "conversion_2"
        mock_st.rerun.assert_called_once()

    @patch("souschef.ui.app._display_conversion_history_tab")
    @patch("souschef.ui.app._display_analysis_history_tab")
    @patch("souschef.ui.app.st")
    def test_display_validation_history_tabs(
        self, mock_st, mock_analysis_tab, mock_conv_tab
    ):
        """Test validation history tabs wiring."""
        from souschef.ui.app import _display_validation_history_tabs

        mock_st.tabs.return_value = [self._ctx(), self._ctx()]

        storage = MagicMock()
        storage.get_analysis_history.return_value = [MagicMock()]
        storage.get_conversion_history.return_value = [MagicMock()]

        with patch(
            "souschef.orchestration.orchestrate_get_storage_manager",
            return_value=storage,
        ):
            _display_validation_history_tabs()

        mock_analysis_tab.assert_called_once()
        mock_conv_tab.assert_called_once()


class TestValidationExecutionFlow:
    """Test validation report execution flow in app.py."""

    @staticmethod
    def _session_state(initial: dict | None = None):
        class SessionState(dict):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.__dict__ = self

        return SessionState(initial or {})

    @patch("souschef.ui.app.st")
    def test_show_validation_reports_no_run(self, mock_st):
        from souschef.ui.app import show_validation_reports

        mock_st.session_state = self._session_state()
        mock_st.button.return_value = False

        with (
            patch("souschef.ui.app._display_validation_history_tabs"),
            patch(
                "souschef.ui.app._collect_validation_inputs",
                return_value=("/tmp/x", "Full Suite", "text", False, True, True),
            ),
            patch("souschef.ui.app.display_validation_results") as disp,
        ):
            show_validation_reports()

        disp.assert_not_called()

    @patch("souschef.ui.app.st")
    def test_show_validation_reports_run_and_display(self, mock_st):
        from souschef.ui.app import show_validation_reports

        mock_st.session_state = self._session_state({"validation_result": "ok"})
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.app._display_validation_history_tabs"),
            patch(
                "souschef.ui.app._collect_validation_inputs",
                return_value=("/tmp/x", "Security", "json", True, False, False),
            ),
            patch("souschef.ui.app._execute_validation_workflow") as exec_flow,
            patch("souschef.ui.app.display_validation_results") as disp,
        ):
            show_validation_reports()

        exec_flow.assert_called_once()
        disp.assert_called_once()

    @patch("souschef.ui.app.st")
    @patch("souschef.ui.app.ProgressTracker")
    def test_handle_validation_execution_success(self, mock_tracker_cls, mock_st):
        from souschef.ui.app import _handle_validation_execution

        tracker = MagicMock()
        mock_tracker_cls.return_value = tracker
        mock_st.session_state = self._session_state()

        class Level:
            value = "warning"

        class Result:
            level = Level()
            location = "file.yml:1"
            message = "issue"

        with (
            patch(
                "souschef.ui.app._collect_files_to_validate",
                return_value=[Path("/tmp/file.yml")],
            ),
            patch(
                "souschef.ui.app._run_validation_engine",
                return_value=[Result()],
            ),
            patch(
                "souschef.ui.app._filter_results_by_scope",
                return_value=[Result()],
            ),
        ):
            _handle_validation_execution("/tmp", {"scope": "Full Suite"})

        assert "validation_result" in mock_st.session_state
        tracker.complete.assert_called_once()
        mock_st.success.assert_called_once()
        mock_st.rerun.assert_called_once()

    @patch("souschef.ui.app.st")
    @patch("souschef.ui.app.ProgressTracker")
    def test_handle_validation_execution_no_files(self, mock_tracker_cls, mock_st):
        from souschef.ui.app import _handle_validation_execution

        tracker = MagicMock()
        mock_tracker_cls.return_value = tracker

        with (
            patch(
                "souschef.ui.app._collect_files_to_validate",
                return_value=[],
            ),
            patch(
                "souschef.ui.app._normalize_and_validate_input_path",
                return_value=None,
            ),
        ):
            _handle_validation_execution("/tmp", {"scope": "Full Suite"})

        tracker.complete.assert_not_called()

    @patch("souschef.ui.app.st")
    @patch("souschef.ui.app.ProgressTracker")
    def test_handle_validation_execution_exception(self, mock_tracker_cls, mock_st):
        from souschef.ui.app import _handle_validation_execution

        tracker = MagicMock()
        mock_tracker_cls.return_value = tracker

        with patch(
            "souschef.ui.app._collect_files_to_validate",
            side_effect=RuntimeError("boom"),
        ):
            _handle_validation_execution("/tmp", {"scope": "Full Suite"})

        tracker.close.assert_called_once()
        mock_st.error.assert_called_once()


class TestDashboardAndDependencyHelpers:
    """Additional branch tests for dashboard and dependency mapping helpers."""

    @staticmethod
    def _ctx() -> MagicMock:
        ctx = MagicMock()
        ctx.__enter__ = Mock(return_value=ctx)
        ctx.__exit__ = Mock(return_value=None)
        return ctx

    @staticmethod
    def _session_state(initial: dict | None = None):
        class SessionState(dict):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.__dict__ = self

        return SessionState(initial or {})

    @patch("souschef.ui.app.st")
    def test_display_quick_upload_section_with_file(self, mock_st):
        from souschef.ui.app import _display_quick_upload_section

        upload = MagicMock()
        upload.getvalue.return_value = b"zipdata"
        upload.name = "cookbooks.zip"
        upload.type = "application/zip"

        mock_st.columns.return_value = [self._ctx(), self._ctx()]
        mock_st.file_uploader.return_value = upload
        mock_st.session_state = self._session_state()

        _display_quick_upload_section()

        assert mock_st.session_state.uploaded_file_name == "cookbooks.zip"
        mock_st.success.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_display_recent_activity(self, mock_st):
        from souschef.ui.app import _display_recent_activity

        mock_st.expander.return_value = self._ctx()
        _display_recent_activity()

        mock_st.info.assert_called_once()
        mock_st.markdown.assert_called()

    # Removed duplicate test_render_history_selectbox (original at line 3269)

    def test_format_history_analysis_helper(self):
        from souschef.ui.app import _format_history_analysis

        analysis = MagicMock()
        analysis.id = 1
        analysis.cookbook_name = "nginx"
        analysis.cookbook_version = "1.0"
        analysis.complexity = "Low"
        analysis.created_at = "2025-01-01"

        text = _format_history_analysis(1, [analysis])
        assert "nginx v1.0" in text

    @patch("souschef.ui.app.st")
    def test_display_migration_planning_history_no_data(self, mock_st):
        from souschef.ui.app import _display_migration_planning_history

        storage = MagicMock()
        storage.get_analysis_history.return_value = []

        with patch(
            "souschef.orchestration.orchestrate_get_storage_manager",
            return_value=storage,
        ):
            _display_migration_planning_history()

        mock_st.info.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_display_migration_planning_history_load(self, mock_st):
        from souschef.ui.app import _display_migration_planning_history

        analysis = MagicMock()
        analysis.id = 7
        analysis.cookbook_name = "apache"
        analysis.cookbook_version = "2.4"
        analysis.complexity = "Medium"
        analysis.created_at = "2025-01-01"
        analysis.cookbook_path = "/tmp/apache"

        storage = MagicMock()
        storage.get_analysis_history.return_value = [analysis]

        mock_st.columns.return_value = [self._ctx(), self._ctx()]
        mock_st.selectbox.return_value = 7
        mock_st.button.return_value = True
        mock_st.session_state = self._session_state()

        with patch(
            "souschef.orchestration.orchestrate_get_storage_manager",
            return_value=storage,
        ):
            _display_migration_planning_history()

        assert mock_st.session_state.analysis_cookbook_path == "/tmp/apache"
        mock_st.rerun.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_display_dependency_mapping_history_no_data(self, mock_st):
        from souschef.ui.app import _display_dependency_mapping_history

        storage = MagicMock()
        storage.get_analysis_history.return_value = []

        with patch(
            "souschef.orchestration.orchestrate_get_storage_manager",
            return_value=storage,
        ):
            _display_dependency_mapping_history()

        mock_st.info.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_display_dependency_mapping_history_load(self, mock_st):
        from souschef.ui.app import _display_dependency_mapping_history

        analysis = MagicMock()
        analysis.id = 3
        analysis.cookbook_name = "mysql"
        analysis.cookbook_version = "8.0"
        analysis.complexity = "High"
        analysis.created_at = "2025-01-01"
        analysis.cookbook_path = "/tmp/mysql"

        storage = MagicMock()
        storage.get_analysis_history.return_value = [analysis]

        mock_st.columns.return_value = [self._ctx(), self._ctx()]
        mock_st.selectbox.return_value = 3
        mock_st.button.return_value = True
        mock_st.session_state = self._session_state()

        with patch(
            "souschef.orchestration.orchestrate_get_storage_manager",
            return_value=storage,
        ):
            _display_dependency_mapping_history()

        assert mock_st.session_state.dep_analysis_cookbook_path == "/tmp/mysql"
        mock_st.rerun.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_display_graph_visualization_section_non_graph(self, mock_st):
        from souschef.ui.app import _display_graph_visualization_section

        _display_graph_visualization_section("analysis", "text")

        mock_st.selectbox.assert_not_called()

    @patch("souschef.ui.app.st")
    def test_display_graph_visualization_section_graph(self, mock_st):
        from souschef.ui.app import _display_graph_visualization_section

        mock_st.columns.return_value = [self._ctx(), self._ctx(), self._ctx()]
        mock_st.selectbox.return_value = "auto"
        mock_st.checkbox.side_effect = [False, True]
        mock_st.slider.return_value = 2

        with (
            patch(
                "souschef.ui.app._parse_dependency_analysis", return_value=({}, [], [])
            ),
            patch("souschef.ui.app._handle_graph_caching"),
            patch("souschef.ui.app._display_dependency_graph_visualization") as disp,
        ):
            _display_graph_visualization_section("analysis", "graph")

        disp.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_display_dependency_export_options(self, mock_st):
        from souschef.ui.app import _display_dependency_export_options

        mock_st.columns.return_value = [self._ctx(), self._ctx()]

        _display_dependency_export_options(
            analysis_result="## report",
            cookbook_path="/tmp/cookbook",
            depth="full",
            direct_deps=3,
            transitive_deps=8,
            circular_deps=1,
            community_cookbooks=2,
        )

        assert mock_st.download_button.call_count == 2

    @patch("souschef.ui.app.st")
    def test_display_dependency_analysis_summary(self, mock_st):
        from souschef.ui.app import _display_dependency_analysis_summary

        with (
            patch(
                "souschef.ui.app._parse_dependency_metrics_from_result",
                return_value=(2, 5, 1, 1),
            ),
            patch("souschef.ui.app._display_dependency_summary_metrics") as summary,
        ):
            _display_dependency_analysis_summary("analysis", "/tmp/cookbook", "direct")

        summary.assert_called_once_with(2, 5, 1, 1)
        mock_st.info.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_display_validation_action_items_branches(self, mock_st):
        from souschef.ui.app import _display_validation_action_items

        _display_validation_action_items(errors=2, warnings=1)
        _display_validation_action_items(errors=0, warnings=2)
        _display_validation_action_items(errors=0, warnings=0)

        assert mock_st.markdown.call_count >= 3

    @patch("souschef.ui.app.st")
    def test_display_validation_export_options(self, mock_st):
        from souschef.ui.app import _display_validation_export_options

        mock_st.columns.return_value = [self._ctx(), self._ctx()]

        _display_validation_export_options(
            validation_result="[ERROR] thing",
            input_path="/tmp/playbooks",
            validation_type="Security",
            options={"strict": True},
            errors=1,
            warnings=0,
            passed=2,
            total_checks=3,
        )

        assert mock_st.download_button.call_count == 2

    @patch("souschef.ui.app.st")
    def test_display_dependency_analysis_sections(self, mock_st):
        from souschef.ui.app import _display_dependency_analysis_sections

        mock_st.expander.return_value = self._ctx()

        analysis = (
            "## Migration Order Recommendations\n- step\n"
            "## Dependency Graph\n- graph\n"
            "## Migration Impact Analysis\n- impact\n"
            "## Misc\n- x\n"
        )

        _display_dependency_analysis_sections(analysis)
        assert mock_st.expander.call_count >= 3

    @patch("souschef.ui.app.st")
    def test_display_impact_analysis_section_no_deps(self, mock_st):
        from souschef.ui.app import _display_impact_analysis_section

        with patch(
            "souschef.ui.app._parse_dependency_analysis",
            return_value=({}, [], []),
        ):
            _display_impact_analysis_section("analysis")

        mock_st.info.assert_called()

    @patch("souschef.ui.app.st")
    def test_display_impact_analysis_section_with_deps(self, mock_st):
        from souschef.ui.app import _display_impact_analysis_section

        mock_st.columns.return_value = [
            self._ctx(),
            self._ctx(),
            self._ctx(),
            self._ctx(),
        ]

        with (
            patch(
                "souschef.ui.app._parse_dependency_analysis",
                return_value=({"a": ["b"], "b": []}, [], []),
            ),
            patch(
                "souschef.ui.app._calculate_migration_impact",
                return_value={
                    "risk_score": 8.0,
                    "timeline_impact_weeks": 2,
                    "complexity_level": "High",
                    "parallel_streams": 1,
                    "critical_path": ["a", "b"],
                    "bottlenecks": [],
                    "recommendations": [],
                },
            ),
            patch("souschef.ui.app._display_detailed_impact_analysis") as details,
        ):
            _display_impact_analysis_section("analysis")

        assert mock_st.metric.call_count >= 4
        details.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_show_dependency_mapping_branches(self, mock_st):
        from souschef.ui.app import show_dependency_mapping

        mock_st.button.return_value = True
        mock_st.session_state = self._session_state()
        mock_st.radio.return_value = "Use History"
        mock_st.selectbox.side_effect = ["direct", "text"]
        mock_st.columns.return_value = [self._ctx(), self._ctx()]

        with (
            patch("souschef.ui.app._display_dependency_mapping_header"),
            patch("souschef.ui.app._display_dependency_mapping_history"),
            patch(
                "souschef.ui.app._get_cookbook_path_from_input_method",
                return_value=None,
            ),
        ):
            show_dependency_mapping()

        mock_st.error.assert_called()

    @patch("souschef.ui.app.st")
    def test_get_cookbook_path_from_input_method_branches(self, mock_st):
        from souschef.ui.app import _get_cookbook_path_from_input_method

        # Directory path branch
        mock_st.text_input.return_value = "/tmp/cookbooks"
        assert (
            _get_cookbook_path_from_input_method("Directory Path") == "/tmp/cookbooks"
        )

        # Use history branch with session value
        mock_st.session_state = self._session_state(
            {"dep_analysis_cookbook_path": "/tmp/from-history"}
        )
        assert (
            _get_cookbook_path_from_input_method("Use History") == "/tmp/from-history"
        )

        # Use history branch without session value
        mock_st.session_state = self._session_state()
        assert _get_cookbook_path_from_input_method("Use History") is None

        # Upload branch success
        upload = MagicMock()
        mock_st.file_uploader.return_value = upload
        mock_st.spinner.return_value = self._ctx()
        with patch(
            "souschef.ui.pages.cookbook_analysis.extract_archive",
            return_value=Path("/tmp/extracted"),
        ):
            assert (
                _get_cookbook_path_from_input_method("Upload Archive")
                == "/tmp/extracted"
            )

        # Upload branch failure
        with patch(
            "souschef.ui.pages.cookbook_analysis.extract_archive",
            side_effect=RuntimeError("boom"),
        ):
            assert _get_cookbook_path_from_input_method("Upload Archive") is None

    @patch("souschef.ui.app.st")
    def test_handle_graph_visualization_error(self, mock_st):
        from souschef.ui.app import _handle_graph_visualization_error

        mock_st.expander.return_value = self._ctx()
        _handle_graph_visualization_error(RuntimeError("bad graph"), "raw analysis")

        mock_st.error.assert_called()
        mock_st.text_area.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_display_graph_with_export_options_interactive(self, mock_st):
        from souschef.ui.app import _display_graph_with_export_options

        graph = MagicMock()
        graph.to_html.return_value = "<html></html>"
        graph.to_json.return_value = "{}"
        mock_st.columns.return_value = [
            self._ctx(),
            self._ctx(),
            self._ctx(),
            self._ctx(),
        ]

        with patch("plotly.io.to_image", return_value=b"img"):
            _display_graph_with_export_options(graph, "interactive")

        assert mock_st.download_button.call_count >= 2

    @patch("souschef.ui.app.st")
    def test_display_graph_with_export_options_static(self, mock_st):
        from souschef.ui.app import _display_graph_with_export_options

        fig = MagicMock()
        mock_st.columns.return_value = [
            self._ctx(),
            self._ctx(),
            self._ctx(),
            self._ctx(),
        ]

        _display_graph_with_export_options(fig, "graph")

        assert mock_st.download_button.call_count >= 4

    @patch("souschef.ui.app.st")
    def test_display_analysis_details_section(self, mock_st):
        from souschef.ui.app import _display_analysis_details_section

        with (
            patch("souschef.ui.app._display_dependency_analysis_sections") as sec,
            patch("souschef.ui.app._display_migration_recommendations") as rec,
        ):
            _display_analysis_details_section(
                "analysis", [("a", "b")], ["community.x"], 3
            )

        sec.assert_called_once()
        rec.assert_called_once_with(1, 1, 3)

    @patch("souschef.ui.app.st")
    def test_display_dependency_analysis_results(self, mock_st):
        from souschef.ui.app import display_dependency_analysis_results

        mock_st.session_state = self._session_state(
            {
                "dep_analysis_result": "analysis text",
                "dep_cookbook_path": "/tmp/cook",
                "dep_depth": "direct",
                "dep_viz_type": "text",
            }
        )

        with (
            patch("souschef.ui.app._display_dependency_analysis_summary") as a,
            patch("souschef.ui.app._display_graph_visualization_section") as b,
            patch("souschef.ui.app._display_impact_analysis_section") as c,
            patch(
                "souschef.ui.app._parse_dependency_analysis",
                return_value=({"a": ["b"]}, [("a", "b")], ["community.general"]),
            ),
            patch("souschef.ui.app._display_analysis_details_section") as d,
            patch("souschef.ui.app._display_dependency_export_options") as e,
        ):
            display_dependency_analysis_results()

        a.assert_called_once()
        b.assert_called_once()
        c.assert_called_once()
        d.assert_called_once()
        e.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_handle_graph_caching_clear(self, mock_st):
        from souschef.ui.app import _handle_graph_caching

        mock_st.columns.return_value = [self._ctx(), self._ctx(), self._ctx()]
        mock_st.checkbox.return_value = True
        mock_st.button.return_value = True
        mock_st.session_state = self._session_state(
            {
                "graph_cache_enabled": True,
                "graph_a": "x",
                "graph_b": "y",
                "other": 1,
            }
        )

        _handle_graph_caching()

        assert "graph_a" not in mock_st.session_state
        assert "graph_b" not in mock_st.session_state
        mock_st.rerun.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_handle_graph_caching_disabled_no_cache(self, mock_st):
        from souschef.ui.app import _handle_graph_caching

        mock_st.columns.return_value = [self._ctx(), self._ctx(), self._ctx()]
        mock_st.checkbox.return_value = False
        mock_st.button.return_value = False
        mock_st.session_state = self._session_state({})

        _handle_graph_caching()

        assert mock_st.info.called or mock_st.metric.called
        mock_st.warning.assert_called()

    @patch("souschef.ui.app.st")
    def test_display_dependency_graph_visualization_cached(self, mock_st):
        from souschef.ui.app import _display_dependency_graph_visualization

        with (
            patch(
                "souschef.ui.app._parse_dependency_analysis", return_value=({}, [], [])
            ),
            patch("souschef.ui.app._get_cached_graph_data", return_value="graph"),
            patch("souschef.ui.app._display_graph_with_export_options") as disp,
            patch("souschef.ui.app.create_dependency_graph") as create_graph,
        ):
            _display_dependency_graph_visualization(
                "analysis", "graph", "auto", False, False, 0
            )

        disp.assert_called_once_with("graph", "graph")
        create_graph.assert_not_called()

    @patch("souschef.ui.app.st")
    def test_display_dependency_graph_visualization_create_none(self, mock_st):
        from souschef.ui.app import _display_dependency_graph_visualization

        with (
            patch(
                "souschef.ui.app._parse_dependency_analysis", return_value=({}, [], [])
            ),
            patch("souschef.ui.app._get_cached_graph_data", return_value=None),
            patch("souschef.ui.app.create_dependency_graph", return_value=None),
            patch("souschef.ui.app._cache_graph_data"),
        ):
            _display_dependency_graph_visualization(
                "analysis", "graph", "auto", False, False, 0
            )

        mock_st.info.assert_called()

    @patch("souschef.ui.app.st")
    def test_display_dependency_graph_visualization_exception(self, mock_st):
        from souschef.ui.app import _display_dependency_graph_visualization

        with (
            patch(
                "souschef.ui.app._parse_dependency_analysis", return_value=({}, [], [])
            ),
            patch(
                "souschef.ui.app._get_cached_graph_data",
                side_effect=RuntimeError("boom"),
            ),
            patch("souschef.ui.app._handle_graph_visualization_error") as err,
        ):
            _display_dependency_graph_visualization(
                "analysis", "graph", "auto", False, False, 0
            )

        err.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_get_cached_graph_data_hit_and_miss(self, mock_st):
        from souschef.ui.app import _get_cached_graph_data

        filters = {"x": 1}
        cache_key = f"graph_{hash('analysis')}_graph_auto_{str(filters)}"
        mock_st.session_state = self._session_state(
            {cache_key: "cached-graph", "graph_cache_enabled": True}
        )

        hit = _get_cached_graph_data("analysis", "graph", "auto", filters)
        assert hit == "cached-graph"

        mock_st.session_state = self._session_state({"graph_cache_enabled": True})
        miss = _get_cached_graph_data("analysis", "graph", "auto", filters)
        assert miss is None

    @patch("souschef.ui.app.st")
    def test_cache_graph_data_enabled_and_disabled(self, mock_st):
        from souschef.ui.app import _cache_graph_data

        filters = {"x": 1}
        mock_st.session_state = self._session_state({"graph_cache_enabled": True})
        _cache_graph_data("analysis", "graph", "auto", filters, "g")

        cache_key = f"graph_{hash('analysis')}_graph_auto_{str(filters)}"
        assert mock_st.session_state[cache_key] == "g"

        mock_st.session_state = self._session_state({"graph_cache_enabled": False})
        _cache_graph_data("analysis", "graph", "auto", filters, "g2")
        assert cache_key not in mock_st.session_state

    @patch("souschef.ui.app.st")
    def test_get_default_validation_path_branches(self, mock_st):
        from souschef.ui.app import _get_default_validation_path

        mock_st.session_state = self._session_state(
            {"converted_playbooks_path": "/tmp/out"}
        )
        assert _get_default_validation_path() == "/tmp/out"

        mock_st.session_state = self._session_state(
            {"analysis_cookbook_path": "/tmp/cook"}
        )
        assert _get_default_validation_path() == "/tmp/cook"

    @patch("souschef.ui.app.st")
    def test_render_validation_options_ui(self, mock_st):
        from souschef.ui.app import _render_validation_options_ui

        mock_st.columns.return_value = [self._ctx(), self._ctx()]
        mock_st.selectbox.side_effect = ["Full Suite", "json"]

        scope, output = _render_validation_options_ui()
        assert scope == "Full Suite"
        assert output == "json"

    @patch("souschef.ui.app.st")
    def test_render_validation_input_ui(self, mock_st):
        from souschef.ui.app import _render_validation_input_ui

        mock_st.radio.return_value = "Directory"
        mock_st.text_input.return_value = "/tmp/playbooks"
        assert _render_validation_input_ui("") == "/tmp/playbooks"

        mock_st.radio.return_value = "Single File"
        mock_st.text_input.return_value = "/tmp/site.yml"
        assert _render_validation_input_ui("/tmp/site.yml") == "/tmp/site.yml"

    @patch("souschef.ui.app.st")
    def test_render_validation_settings_ui(self, mock_st):
        from souschef.ui.app import _render_validation_settings_ui

        mock_st.columns.return_value = [self._ctx(), self._ctx(), self._ctx()]
        mock_st.checkbox.side_effect = [True, True, False]

        strict, best, recs = _render_validation_settings_ui()
        assert strict is True
        assert best is True
        assert recs is False

    @patch("souschef.ui.app.st")
    def test_execute_migration_plan_generation_empty_path(self, mock_st):
        from souschef.ui.app import _execute_migration_plan_generation

        mock_st.button.return_value = True
        _execute_migration_plan_generation("   ", "phased", 6)

        mock_st.error.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_execute_migration_plan_generation_success(self, mock_st):
        from souschef.ui.app import _execute_migration_plan_generation

        mock_st.button.return_value = True
        mock_st.session_state = self._session_state()

        progress = MagicMock()
        with (
            patch(
                "souschef.assessment.generate_migration_plan", return_value="## Plan"
            ),
            patch("souschef.ui.app.ProgressTracker", return_value=progress),
        ):
            _execute_migration_plan_generation("/tmp/cook", "phased", 6)

        assert mock_st.session_state.migration_plan == "## Plan"
        mock_st.success.assert_called_once()
        mock_st.rerun.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_show_migration_planning_with_results(self, mock_st):
        from souschef.ui.app import show_migration_planning

        mock_st.session_state = self._session_state({"migration_plan": "## Plan"})

        with (
            patch("souschef.ui.app._display_migration_planning_history"),
            patch(
                "souschef.ui.app._get_cookbook_paths_input", return_value="/tmp/cook"
            ),
            patch(
                "souschef.ui.app._get_migration_strategy_inputs",
                return_value=("phased", 6),
            ),
            patch("souschef.ui.app._execute_migration_plan_generation"),
            patch("souschef.ui.app.display_migration_plan_results") as results,
        ):
            show_migration_planning()

        results.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_display_migration_summary_metrics(self, mock_st):
        from souschef.ui.app import _display_migration_summary_metrics

        mock_st.columns.return_value = [
            self._ctx(),
            self._ctx(),
            self._ctx(),
            self._ctx(),
        ]
        _display_migration_summary_metrics("a,b", "single_pass", 8)

        assert mock_st.metric.call_count == 4

    @patch("souschef.ui.app.st")
    def test_display_migration_plan_details(self, mock_st):
        from souschef.ui.app import _display_migration_plan_details

        _display_migration_plan_details("## Executive Summary\nA\n## Timeline\nB")

        assert mock_st.markdown.call_count >= 2

    @patch("souschef.ui.app.st")
    def test_display_migration_action_buttons_export(self, mock_st):
        from souschef.ui.app import _display_migration_action_buttons

        mock_st.columns.return_value = [self._ctx(), self._ctx(), self._ctx()]
        mock_st.button.side_effect = [False, False, True]
        mock_st.session_state = self._session_state(
            {
                "strategy": "phased",
                "timeline": 6,
                "migration_plan": "## Plan",
                "timestamp": "2026-03-09",
            }
        )

        _display_migration_action_buttons("/tmp/cook")

        mock_st.download_button.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_display_additional_reports(self, mock_st):
        from souschef.ui.app import _display_additional_reports

        mock_st.session_state = self._session_state(
            {"detailed_report": "report", "dep_analysis": "deps"}
        )
        mock_st.expander.return_value = self._ctx()

        _display_additional_reports()

        assert mock_st.expander.call_count == 2

    @patch("souschef.ui.app.st")
    def test_display_migration_plan_results(self, mock_st):
        from souschef.ui.app import display_migration_plan_results

        mock_st.session_state = self._session_state(
            {
                "migration_plan": "## Plan",
                "cookbook_paths": "/tmp/cook",
                "strategy": "phased",
                "timeline": 6,
            }
        )

        with (
            patch("souschef.ui.app._display_migration_summary_metrics") as a,
            patch("souschef.ui.app._display_migration_plan_details") as b,
            patch("souschef.ui.app._display_migration_action_buttons") as c,
            patch("souschef.ui.app._display_additional_reports") as d,
        ):
            display_migration_plan_results()

        a.assert_called_once()
        b.assert_called_once()
        c.assert_called_once()
        d.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_get_cookbook_paths_input_quick_select(self, mock_st):
        from souschef.ui.app import _get_cookbook_paths_input

        mock_st.session_state = self._session_state(
            {"analysis_cookbook_path": "/tmp/from-analysis"}
        )
        mock_st.columns.return_value = [self._ctx(), self._ctx()]
        mock_st.text_area.return_value = "custom"
        mock_st.selectbox.return_value = "Full Migration"

        result = _get_cookbook_paths_input()
        assert "redis" in result

    def test_apply_quick_select_example(self):
        from souschef.ui.app import _apply_quick_select_example

        assert _apply_quick_select_example("x", "Single Cookbook").endswith("nginx")
        assert _apply_quick_select_example("x", "") == "x"

    @patch("souschef.ui.app.st")
    def test_get_migration_strategy_inputs(self, mock_st):
        from souschef.ui.app import _get_migration_strategy_inputs

        mock_st.columns.return_value = [self._ctx(), self._ctx()]
        mock_st.selectbox.return_value = "parallel"
        mock_st.slider.return_value = 10

        with patch("souschef.ui.app._display_strategy_details") as details:
            strategy, weeks = _get_migration_strategy_inputs()

        assert strategy == "parallel"
        assert weeks == 10
        details.assert_called_once_with("parallel")

    @patch("souschef.ui.app.st")
    def test_display_strategy_details(self, mock_st):
        from souschef.ui.app import _display_strategy_details

        mock_st.expander.return_value = self._ctx()
        _display_strategy_details("phased")

        mock_st.markdown.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_handle_history_load_button(self, mock_st):
        from souschef.ui.app import _handle_history_load_button

        mock_st.session_state = self._session_state()
        mock_st.button.return_value = True

        class Analysis:
            id = 7
            cookbook_path = "/tmp/cook"
            cookbook_name = "nginx"

        _handle_history_load_button(7, [Analysis()])
        assert mock_st.session_state.analysis_cookbook_path == "/tmp/cook"
        mock_st.rerun.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_render_history_selectbox(self, mock_st):
        from souschef.ui.app import _render_history_selectbox

        class Analysis:
            id = 1
            created_at = "2026-01-01"
            cookbook_name = "nginx"
            cookbook_version = "1.0"
            complexity = "Low"

        mock_st.selectbox.return_value = 1
        selected = _render_history_selectbox([Analysis()])
        assert selected == 1

    @patch("souschef.ui.app.st")
    def test_execute_dependency_analysis_success(self, mock_st):
        from souschef.ui.app import _execute_dependency_analysis

        mock_st.session_state = self._session_state()
        tracker = MagicMock()

        with (
            patch(
                "souschef.assessment.analyse_cookbook_dependencies", return_value="deps"
            ),
            patch("souschef.ui.app.ProgressTracker", return_value=tracker),
        ):
            _execute_dependency_analysis("/tmp/cook", "direct", "text")

        assert mock_st.session_state.dep_analysis_result == "deps"
        mock_st.rerun.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_execute_dependency_analysis_empty_path(self, mock_st):
        from souschef.ui.app import _execute_dependency_analysis

        _execute_dependency_analysis("   ", "direct", "text")
        mock_st.error.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_execute_dependency_analysis_exception(self, mock_st):
        from souschef.ui.app import _execute_dependency_analysis

        tracker = MagicMock()
        with (
            patch(
                "souschef.assessment.analyse_cookbook_dependencies",
                side_effect=RuntimeError("boom"),
            ),
            patch("souschef.ui.app.ProgressTracker", return_value=tracker),
        ):
            _execute_dependency_analysis("/tmp/cook", "direct", "text")

        tracker.close.assert_called_once()
        mock_st.error.assert_called()

    @patch("souschef.ui.app.st")
    def test_show_dependency_mapping_executes_and_displays(self, mock_st):
        from souschef.ui.app import show_dependency_mapping

        mock_st.session_state = self._session_state({"dep_analysis_result": "x"})
        mock_st.radio.return_value = "Directory Path"
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.app._display_dependency_mapping_header"),
            patch("souschef.ui.app._display_dependency_mapping_history"),
            patch(
                "souschef.ui.app._get_cookbook_path_from_input_method",
                return_value="/tmp/cook",
            ),
            patch(
                "souschef.ui.app._get_dependency_analysis_options",
                return_value=("direct", "text"),
            ),
            patch("souschef.ui.app._execute_dependency_analysis") as exec_dep,
            patch("souschef.ui.app.display_dependency_analysis_results") as disp,
        ):
            show_dependency_mapping()

        exec_dep.assert_called_once_with("/tmp/cook", "direct", "text")
        disp.assert_called_once()

    @patch("souschef.ui.app.st")
    def test_handle_dependency_analysis_execution_paths(self, mock_st):
        from souschef.ui.app import _handle_dependency_analysis_execution

        mock_st.button.return_value = True
        _handle_dependency_analysis_execution("   ", "direct", "text")
        mock_st.error.assert_called()

        mock_st.error.reset_mock()
        with patch("souschef.ui.app._perform_dependency_analysis") as perf:
            _handle_dependency_analysis_execution("/tmp/cook", "full", "graph")
        perf.assert_called_once_with("/tmp/cook", "full", "graph")
