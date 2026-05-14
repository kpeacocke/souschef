"""Unit tests for UI utility modules with low or zero coverage."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest


class SessionState(dict):
    """Session state helper with attribute access."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value


def _ctx() -> MagicMock:
    """Return a generic context manager mock."""
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=ctx)
    ctx.__exit__ = Mock(return_value=None)
    return ctx


def test_analytics_track_stats_and_risk(tmp_path) -> None:
    """Analytics helpers track events, aggregate stats, and derive risk levels."""
    from souschef.ui import analytics

    analytics.ANALYTICS_DIR = tmp_path / "analytics"
    analytics.ANALYTICS_EVENTS_FILE = analytics.ANALYTICS_DIR / "events.jsonl"
    analytics.ANALYTICS_PATTERNS_FILE = analytics.ANALYTICS_DIR / "patterns.json"

    analytics.clear_analytics()
    analytics.track_event(
        event_type="conversion",
        tool="Chef",
        status="success",
        duration_seconds=2.5,
        pattern="service.running",
    )
    analytics.track_event(
        event_type="conversion",
        tool="Chef",
        status="partial_success",
        duration_seconds=4.5,
        pattern="service.running",
    )
    analytics.track_event(
        event_type="conversion",
        tool="Chef",
        status="failure",
        duration_seconds=6.5,
        pattern="file.managed",
    )
    analytics.track_event(event_type="recommendation", tool="Chef", status="success")

    stats = analytics.get_conversion_stats("Chef")
    assert stats["total_conversions"] == 3
    assert stats["successful_conversions"] == 2
    assert stats["failed_conversions"] == 1
    assert stats["success_rate"] == pytest.approx(66.7)
    assert stats["avg_duration"] == pytest.approx(4.5)
    assert stats["common_patterns"][0]["pattern"] == "service.running"

    assert analytics.get_pattern_risk_level("Chef", "service.running") == "high"
    assert analytics.get_pattern_risk_level("Chef", "does.not.exist") == "unknown"


def test_analytics_handles_corrupt_file_and_session_init(tmp_path) -> None:
    """Analytics handling should tolerate corrupt files and initialise session state."""
    from souschef.ui import analytics

    analytics.ANALYTICS_DIR = tmp_path / "analytics"
    analytics.ANALYTICS_EVENTS_FILE = analytics.ANALYTICS_DIR / "events.jsonl"
    analytics.ANALYTICS_PATTERNS_FILE = analytics.ANALYTICS_DIR / "patterns.json"
    analytics.ANALYTICS_DIR.mkdir(parents=True)
    analytics.ANALYTICS_EVENTS_FILE.write_text("{not-json}\n", encoding="utf-8")

    stats = analytics.get_conversion_stats()
    assert stats["total_conversions"] == 0

    mock_st = SimpleNamespace(session_state=SessionState())
    with patch("souschef.ui.analytics.st", mock_st):
        analytics.init_session_tracking()
        assert "analytics_session_id" in mock_st.session_state
        assert mock_st.session_state.conversion_start_time is None


def test_analytics_error_paths_and_risk_levels(tmp_path) -> None:
    """Analytics functions should handle OS errors and risk-level branches."""
    from souschef.ui import analytics

    analytics.ANALYTICS_DIR = tmp_path / "analytics"
    analytics.ANALYTICS_EVENTS_FILE = analytics.ANALYTICS_DIR / "events.jsonl"
    analytics.ANALYTICS_PATTERNS_FILE = analytics.ANALYTICS_DIR / "patterns.json"
    analytics.ANALYTICS_DIR.mkdir(parents=True)

    with patch("souschef.ui.analytics.Path.open", side_effect=OSError("nope")):
        analytics.track_event("conversion", "Chef", "success")
        stats = analytics.get_conversion_stats()
        assert stats["total_conversions"] == 0

    # Force unlink error branch.
    analytics.ANALYTICS_EVENTS_FILE.write_text("{}\n", encoding="utf-8")
    analytics.ANALYTICS_PATTERNS_FILE.write_text("{}\n", encoding="utf-8")
    with patch("souschef.ui.analytics.Path.unlink", side_effect=OSError("blocked")):
        analytics.clear_analytics()

    assert (
        analytics._risk_level_from_failure_rate({"success": 3, "failure": 1})
        == "medium"
    )
    assert (
        analytics._risk_level_from_failure_rate({"success": 9, "failure": 1}) == "low"
    )


def test_analytics_tool_filter_and_count_pattern_branches(tmp_path) -> None:
    """Analytics should cover tool filtering and pattern counting edge branches."""
    from souschef.ui import analytics

    analytics.ANALYTICS_DIR = tmp_path / "analytics"
    analytics.ANALYTICS_EVENTS_FILE = analytics.ANALYTICS_DIR / "events.jsonl"
    analytics.ANALYTICS_PATTERNS_FILE = analytics.ANALYTICS_DIR / "patterns.json"
    analytics.ANALYTICS_DIR.mkdir(parents=True)

    analytics.ANALYTICS_EVENTS_FILE.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event_type": "conversion",
                        "tool": "Chef",
                        "status": "success",
                        "pattern": "pkg.installed",
                    }
                ),
                json.dumps(
                    {
                        "event_type": "conversion",
                        "tool": "Salt",
                        "status": "failure",
                        "pattern": "pkg.installed",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    filtered_stats = analytics.get_conversion_stats("Chef")
    assert filtered_stats["total_conversions"] == 1

    # Missing analytics file branch in _count_pattern_outcomes.
    analytics.ANALYTICS_EVENTS_FILE.unlink()
    assert analytics._count_pattern_outcomes("Chef", "pkg.installed") == {
        "success": 0,
        "failure": 0,
    }

    analytics.ANALYTICS_EVENTS_FILE.write_text("{bad-json}\n", encoding="utf-8")
    assert analytics._count_pattern_outcomes("Chef", "pkg.installed") == {
        "success": 0,
        "failure": 0,
    }

    with patch("souschef.ui.analytics.Path.open", side_effect=OSError("denied")):
        analytics.get_conversion_stats()
        analytics._count_pattern_outcomes("Chef", "pkg.installed")

    # Explicitly cover the patterns file unlink path.
    analytics.ANALYTICS_PATTERNS_FILE.write_text("{}", encoding="utf-8")
    analytics.clear_analytics()


def test_filtering_save_load_apply_and_delete(tmp_path) -> None:
    """Filtering helpers should persist searches and apply all filter criteria."""
    from souschef.ui import filtering

    filtering.SEARCHES_DIR = tmp_path / "searches"
    filtering.SAVED_SEARCHES_FILE = filtering.SEARCHES_DIR / "saved.json"

    criteria = filtering.FilterCriteria(
        tools=["Chef"],
        complexity=["complex"],
        risk_levels=["high"],
        status=["in progress"],
        tags=["db"],
        has_dependencies=True,
        search_text="migration",
    )
    filtering.save_search("complex-chef", criteria)
    assert filtering.list_saved_searches() == ["complex-chef"]
    loaded = filtering.get_search("complex-chef")
    assert loaded is not None
    assert loaded.tools == ["Chef"]

    items = [
        {
            "name": "migration-db",
            "description": "migration item",
            "path": "cookbooks/db",
            "tool": "Chef",
            "complexity": "complex",
            "risk_level": "high",
            "status": "in progress",
            "tags": ["db"],
            "dependencies": ["base"],
        },
        {"name": "other", "tool": "Bash", "dependencies": []},
    ]
    filtered = filtering.apply_filters(items, criteria)
    assert len(filtered) == 1
    assert filtered[0]["name"] == "migration-db"

    filtering.delete_search("complex-chef")
    assert filtering.get_search("complex-chef") is None


def test_filtering_handles_bad_saved_json(tmp_path) -> None:
    """Loading bad saved-search JSON should not raise and should return empty results."""
    from souschef.ui import filtering

    filtering.SEARCHES_DIR = tmp_path / "searches"
    filtering.SAVED_SEARCHES_FILE = filtering.SEARCHES_DIR / "saved.json"
    filtering.SEARCHES_DIR.mkdir(parents=True)
    filtering.SAVED_SEARCHES_FILE.write_text("{bad-json", encoding="utf-8")

    assert filtering.list_saved_searches() == []


def test_filtering_save_searches_oserror(tmp_path) -> None:
    """Saving searches should swallow file write errors."""
    from souschef.ui import filtering

    filtering.SEARCHES_DIR = tmp_path / "searches"
    filtering.SAVED_SEARCHES_FILE = filtering.SEARCHES_DIR / "saved.json"
    filtering.SEARCHES_DIR.mkdir(parents=True)

    with patch("souschef.ui.filtering.Path.open", side_effect=OSError("nope")):
        filtering._save_searches({"x": filtering.FilterCriteria()})


@patch("souschef.ui.filtering.st")
def test_filter_panel_and_dialog_paths(mock_st) -> None:
    """Filter panel and save dialog should return/handle user selections."""
    from souschef.ui import filtering

    mock_st.session_state = SessionState()
    mock_st.sidebar.multiselect.side_effect = [
        ["Chef"],
        ["Complex"],
        ["High"],
        ["In Progress"],
    ]
    mock_st.sidebar.radio.return_value = "With Dependencies"
    mock_st.sidebar.text_input.return_value = "abc"
    mock_st.sidebar.button.return_value = False

    criteria = filtering.show_filter_panel()
    assert criteria.tools == ["Chef"]
    assert criteria.complexity == ["complex"]
    assert criteria.risk_levels == ["high"]
    assert criteria.status == ["in progress"]
    assert criteria.has_dependencies is True
    assert criteria.search_text == "abc"

    # save dialog: save path
    mock_st.session_state = SessionState(
        {
            "save_search_mode": True,
            "filter_tools": ["Chef"],
            "filter_complexity": ["complex"],
            "filter_risk": ["high"],
            "filter_status": ["in progress"],
        }
    )
    mock_st.form.return_value = _ctx()
    mock_st.columns.return_value = [_ctx(), _ctx()]
    mock_st.text_input.return_value = "saved-name"
    mock_st.form_submit_button.side_effect = [True, False]

    with patch("souschef.ui.filtering.save_search") as save_search_mock:
        filtering.show_save_search_dialog()
        save_search_mock.assert_called_once()

    # save dialog: cancel path
    mock_st.session_state = SessionState({"save_search_mode": True})
    mock_st.form_submit_button.side_effect = [False, True]
    filtering.show_save_search_dialog()
    assert mock_st.session_state.save_search_mode is False


@patch("souschef.ui.filtering.st")
def test_filter_panel_saved_search_load_and_save_button(mock_st) -> None:
    """Saved-search load and save-button flows should update state and rerun."""
    from souschef.ui import filtering

    mock_st.session_state = SessionState()
    mock_st.sidebar.multiselect.side_effect = [[], [], [], []]
    mock_st.sidebar.radio.return_value = "No Dependencies"
    mock_st.sidebar.text_input.return_value = ""
    mock_st.sidebar.selectbox.return_value = "saved-one"
    mock_st.sidebar.button.return_value = True

    with (
        patch("souschef.ui.filtering.list_saved_searches", return_value=["saved-one"]),
        patch(
            "souschef.ui.filtering.get_search",
            return_value=filtering.FilterCriteria(tools=["Chef"]),
        ),
    ):
        criteria = filtering.show_filter_panel()

    assert criteria.has_dependencies is False
    assert mock_st.session_state.current_filter.tools == ["Chef"]
    assert mock_st.session_state.save_search_mode is True
    assert mock_st.rerun.call_count >= 2


def test_recommendations_core_logic() -> None:
    """Recommendation generation should combine dependencies, flags, and analytics."""
    from souschef.ui import recommendations as rec

    resources = [
        {
            "id": "r1",
            "type": "recipe",
            "content": "hiera data_bag custom_resource",
            "pattern": "recipe.default",
        },
        {"id": "r2", "type": "resource", "content": "plain"},
    ]
    dep_graph = {"r1": [], "r2": ["r1"]}

    with (
        patch(
            "souschef.ui.recommendations.get_conversion_stats",
            return_value={"success_rate": 80.0},
        ),
        patch(
            "souschef.ui.recommendations.get_pattern_risk_level",
            side_effect=["high", "low"],
        ),
    ):
        out = rec.create_recommendations("Chef", resources, dep_graph)

    assert len(out) == 2
    assert out[0].resource_id == "r1"
    assert out[0].priority <= out[1].priority
    assert out[0].risk_level == "high"
    assert out[0].success_rate == pytest.approx(56.0)
    assert rec.get_risk_flags_for_tool("unknown") == {}
    assert rec.detect_risk_flags("PowerShell", {"content": "HKEY_LOCAL_MACHINE"})


def test_recommendations_priority_reason_and_detection_branches() -> None:
    """Recommendation helper branches should cover priority and reason variants."""
    from souschef.ui import recommendations as rec

    assert rec._compute_priority([], [], "low", []) == 1
    assert rec._compute_priority(["a"], ["b"], "low", []) == 2
    assert rec._compute_priority(["a"], [], "critical", []) == 4
    assert (
        rec._compute_priority(
            ["a"], [], "low", [rec.CHEF_RISK_FLAGS["hiera_hard_lookup"]]
        )
        == 5
    )
    assert rec._compute_priority(["a"], [], "low", []) == 10

    assert rec._build_recommendation_reason(["a"], [], []) == "Ready for migration"
    assert rec._compute_success_rate(77.0, "low") == pytest.approx(77.0)
    assert rec.detect_risk_flags("Puppet", {"content": "lookup('x')"})


@patch("souschef.ui.recommendations.st")
def test_recommendations_display_helpers(mock_st) -> None:
    """Recommendation display helpers should render both empty and populated states."""
    from souschef.ui import recommendations as rec

    rec.show_recommendations_panel([])
    mock_st.info.assert_called()

    risk = rec.RiskFlag(
        flag_id="x",
        severity="medium",
        title="Test",
        explanation="Because",
        mitigation="Do this",
    )
    recommendation = rec.Recommendation(
        resource_id="r1",
        title="resource r1",
        reason="Reason",
        priority=1,
        risk_level="medium",
        flags=[risk],
        depends_on=["a"],
        blocking=["b"],
        success_rate=75.0,
    )
    mock_st.expander.return_value = _ctx()
    rec.show_recommendations_panel([recommendation])
    assert mock_st.expander.called


@patch("souschef.ui.recommendations.st")
def test_recommendations_display_with_cwe_caption(mock_st) -> None:
    """Risk flags with CWE should render caption details."""
    from souschef.ui import recommendations as rec

    recommendation = rec.Recommendation(
        resource_id="r1",
        title="resource r1",
        reason="Reason",
        priority=1,
        risk_level="high",
        flags=[rec.CHEF_RISK_FLAGS["hiera_hard_lookup"]],
        depends_on=[],
        blocking=[],
        success_rate=60.0,
    )
    mock_st.expander.return_value = _ctx()
    rec.show_recommendations_panel([recommendation])
    assert mock_st.caption.called


@patch("souschef.ui.recommendations.st")
def test_dependency_map_render_or_fallback(mock_st) -> None:
    """Dependency map should render with networkx or show fallback warning."""
    from souschef.ui import recommendations as rec

    # Normal render path (networkx is available in dev deps).
    rec.show_dependency_map({"b": ["a"]})
    assert mock_st.info.called


@patch("souschef.ui.recommendations.st")
def test_dependency_map_empty_graph(mock_st) -> None:
    """Empty dependency graphs should show informational message."""
    from souschef.ui import recommendations as rec

    rec.show_dependency_map({})
    mock_st.info.assert_called()


@patch("souschef.ui.recommendations.st")
def test_dependency_map_without_networkx(mock_st) -> None:
    """If networkx import fails, fallback warning should be shown."""
    import builtins

    from souschef.ui import recommendations as rec

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "networkx":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        rec.show_dependency_map({"b": ["a"]})

    mock_st.warning.assert_called_once()


def test_theme_load_save_apply_and_selector(tmp_path) -> None:
    """Theme helpers should persist and apply selected theme modes."""
    from souschef.ui import theme

    theme.THEME_CONFIG_FILE = tmp_path / "theme.json"
    assert theme._load_theme_preference() == "auto"

    theme._save_theme_preference("dark")
    assert theme._load_theme_preference() == "dark"

    theme.THEME_CONFIG_FILE.write_text(
        json.dumps({"theme": "invalid"}), encoding="utf-8"
    )
    assert theme._load_theme_preference() == "auto"

    mock_st = SimpleNamespace(
        session_state=SessionState(), sidebar=MagicMock(), rerun=MagicMock()
    )
    mock_st.sidebar.selectbox.return_value = "Dark"
    with patch("souschef.ui.theme.st", mock_st):
        assert theme.get_active_theme() == "auto"
        theme.set_theme("light")
        assert theme.get_active_theme() == "light"
        assert theme.apply_theme_config({"page_title": "x"})["theme"] == "light"
        theme.show_theme_selector()
        mock_st.rerun.assert_called_once()

    with pytest.raises(ValueError):
        theme.set_theme("invalid")  # type: ignore[arg-type]


def test_theme_additional_branches_and_errors(tmp_path) -> None:
    """Theme module should cover OSError/JSON errors and dark/auto configs."""
    from souschef.ui import theme

    assert theme._get_os_prefers_dark() is False

    theme.THEME_CONFIG_FILE = tmp_path / "theme.json"
    theme.THEME_CONFIG_FILE.write_text("{bad-json", encoding="utf-8")
    assert theme._load_theme_preference() == "auto"

    with patch("souschef.ui.theme.Path.open", side_effect=OSError("nope")):
        theme._save_theme_preference("dark")

    mock_st = SimpleNamespace(
        session_state=SessionState({"souschef_theme": "bad-value"}),
        sidebar=MagicMock(),
        rerun=MagicMock(),
    )
    with patch("souschef.ui.theme.st", mock_st):
        assert theme.get_active_theme() == "auto"
        mock_st.session_state.souschef_theme = "dark"
        assert theme.apply_theme_config({"k": "v"})["theme"] == "dark"
        mock_st.session_state.souschef_theme = "auto"
        assert theme.apply_theme_config({"k": "v"})["theme"] is None
