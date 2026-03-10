"""Targeted branch coverage tests for remaining app.py gaps."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest


class SessionState(dict):
    """Simple session-state-like mapping."""

    def __getattr__(self, name: str):
        return self.get(name)

    def __setattr__(self, name: str, value):
        self[name] = value


def _ctx() -> MagicMock:
    """Context manager mock."""
    m = MagicMock()
    m.__enter__ = Mock(return_value=m)
    m.__exit__ = Mock(return_value=False)
    return m


@pytest.fixture(autouse=True)
def _prevent_auto_main():
    """Prevent app.py import-time main() execution and mock streamlit module."""
    with (
        patch.dict(os.environ, {"STREAMLIT_SERVER_PORT": "8501"}),
        patch.dict("sys.modules", {"streamlit": MagicMock()}),
    ):
        yield


def test_format_history_analysis_non_datetime_created_at():
    from souschef.ui.app import _format_history_analysis

    a = SimpleNamespace(
        id="x",
        cookbook_name="cb",
        cookbook_version="1.0",
        complexity="Low",
        created_at=1234567890,
    )
    out = _format_history_analysis("x", [a])
    assert "cb" in out


def test_display_dependency_mapping_header():
    from souschef.ui.app import _display_dependency_mapping_header

    with patch("souschef.ui.app.st") as mock_st:
        _display_dependency_mapping_header()
        mock_st.header.assert_called_once()
        mock_st.markdown.assert_called_once()


def test_display_dependency_mapping_history_with_analyses_and_formatter_paths():
    from souschef.ui.app import _display_dependency_mapping_history

    analysis = SimpleNamespace(
        id="a1",
        cookbook_name="nginx",
        cookbook_version="1.0",
        complexity="Medium",
        created_at="2026-01-01T00:00:00",
        cookbook_path="/tmp/nginx",
    )
    storage = MagicMock()
    storage.get_analysis_history.return_value = [analysis]

    with patch("souschef.ui.app.st") as mock_st:
        mock_st.session_state = SessionState()
        mock_st.columns.return_value = (_ctx(), _ctx())
        captured = {}

        def _selectbox(*args, **kwargs):
            captured["fmt"] = kwargs.get("format_func")
            return None

        mock_st.selectbox.side_effect = _selectbox
        mock_st.button.return_value = False

        with patch(
            "souschef.orchestration.orchestrate_get_storage_manager",
            return_value=storage,
        ):
            _display_dependency_mapping_history()

        fmt = captured["fmt"]
        assert fmt(None) == "-- Select from history --"
        assert "nginx" in fmt("a1")
        assert fmt("missing") == "--"


def test_get_cookbook_path_from_input_method_returns_none_for_upload_without_file():
    from souschef.ui.app import _get_cookbook_path_from_input_method

    with patch("souschef.ui.app.st") as mock_st:
        mock_st.file_uploader.return_value = None
        assert _get_cookbook_path_from_input_method("Upload Archive") is None


def test_setup_dependency_mapping_ui_and_inputs():
    from souschef.ui.app import (
        _get_dependency_mapping_inputs,
        _setup_dependency_mapping_ui,
    )

    with patch("souschef.ui.app.st") as mock_st:
        mock_st.columns.return_value = (_ctx(), _ctx())
        mock_st.text_input.return_value = "/tmp/cookbooks"
        mock_st.selectbox.side_effect = ["direct", "text"]

        _setup_dependency_mapping_ui()
        path, depth, viz = _get_dependency_mapping_inputs()

        assert path == "/tmp/cookbooks"
        assert depth == "direct"
        assert viz == "text"


def test_handle_dependency_analysis_execution_error_and_success_paths():
    from souschef.ui.app import _handle_dependency_analysis_execution

    with patch("souschef.ui.app.st") as mock_st:
        mock_st.button.return_value = True
        _handle_dependency_analysis_execution("", "direct", "text")
        mock_st.error.assert_called()

    with patch("souschef.ui.app.st") as mock_st:
        mock_st.button.return_value = True
        with patch("souschef.ui.app._perform_dependency_analysis") as mock_perf:
            _handle_dependency_analysis_execution(" /tmp/path ", "direct", "text")
            mock_perf.assert_called_once()


def test_perform_dependency_analysis_success_and_exception():
    from souschef.ui.app import _perform_dependency_analysis

    tracker = MagicMock()
    with (
        patch("souschef.ui.app.ProgressTracker", return_value=tracker),
        patch("souschef.ui.app.st") as mock_st,
        patch(
            "souschef.assessment.analyse_cookbook_dependencies",
            return_value="analysis",
        ),
    ):
        mock_st.session_state = SessionState()
        _perform_dependency_analysis("/tmp/path", "direct", "text")
        assert mock_st.session_state.dep_analysis_result == "analysis"
        mock_st.success.assert_called_once()

    tracker2 = MagicMock()
    with (
        patch("souschef.ui.app.ProgressTracker", return_value=tracker2),
        patch("souschef.ui.app.st") as mock_st,
        patch(
            "souschef.assessment.analyse_cookbook_dependencies",
            side_effect=RuntimeError("boom"),
        ),
    ):
        mock_st.session_state = SessionState()
        _perform_dependency_analysis("/tmp/path", "direct", "text")
        tracker2.close.assert_called_once()
        mock_st.error.assert_called_once()


def test_display_dependency_analysis_results_if_available():
    from souschef.ui.app import _display_dependency_analysis_results_if_available

    with patch("souschef.ui.app.st") as mock_st:
        mock_st.session_state = SessionState({"dep_analysis_result": "x"})
        with patch("souschef.ui.app.display_dependency_analysis_results") as mock_disp:
            _display_dependency_analysis_results_if_available()
            mock_disp.assert_called_once()


def test_layout_algorithm_branches_and_shell_fallback():
    import networkx as nx

    from souschef.ui.app import (
        _calculate_positions_with_algorithm,
        _calculate_shell_layout_positions,
    )

    g = nx.DiGraph()
    g.add_edge("a", "b")

    with patch(
        "souschef.ui.app._calculate_shell_layout_positions", return_value={"a": (0, 0)}
    ):
        _calculate_positions_with_algorithm(g, "shell")
    with patch("networkx.random_layout", return_value={"a": (0, 0)}):
        _calculate_positions_with_algorithm(g, "random")
    with patch("networkx.spectral_layout", return_value={"a": (0, 0)}):
        _calculate_positions_with_algorithm(g, "spectral")
    with patch("networkx.spring_layout", return_value={"a": (0, 0)}):
        _calculate_positions_with_algorithm(g, "force_directed")

    empty = nx.DiGraph()
    with patch("networkx.spring_layout", return_value={}) as mock_spring:
        _calculate_shell_layout_positions(empty)
        mock_spring.assert_called_once()


def test_create_interactive_plotly_graph_and_create_dependency_graph_branches():
    import networkx as nx

    from souschef.ui.app import (
        _create_interactive_plotly_graph,
        create_dependency_graph,
    )

    g = nx.DiGraph()
    g.add_edge("a", "b")
    pos = {"a": (0.0, 0.0), "b": (1.0, 1.0)}

    _create_interactive_plotly_graph(g, pos, 2, "spring")

    with (
        patch(
            "souschef.ui.app._parse_dependency_analysis",
            return_value=({"a": ["b"]}, [], []),
        ),
        patch("souschef.ui.app._create_networkx_graph", return_value=g),
        patch("souschef.ui.app._apply_graph_filters", return_value=g) as mock_filter,
        patch(
            "souschef.ui.app._calculate_graph_positions",
            return_value=(pos, "spring"),
        ),
        patch(
            "souschef.ui.app._create_interactive_plotly_graph",
            return_value=object(),
        ),
    ):
        out = create_dependency_graph("x", "interactive", filters={"x": 1})
        assert out is not None
        mock_filter.assert_called_once()

    with (
        patch(
            "souschef.ui.app._parse_dependency_analysis",
            return_value=({"a": ["b"]}, [], []),
        ),
        patch("souschef.ui.app._create_networkx_graph", return_value=g),
        patch(
            "souschef.ui.app._calculate_graph_positions",
            return_value=(pos, "spring"),
        ),
        patch(
            "souschef.ui.app._create_static_matplotlib_graph",
            return_value=object(),
        ),
    ):
        out = create_dependency_graph("x", "graph")
        assert out is not None


def test_display_graph_export_importerror_branches():
    from souschef.ui.app import _display_graph_with_export_options

    fig = MagicMock()
    fig.to_html.return_value = "<html></html>"
    fig.to_json.return_value = "{}"

    with patch("souschef.ui.app.st") as mock_st:
        mock_st.columns.return_value = (_ctx(), _ctx(), _ctx(), _ctx())
        with patch.dict("sys.modules", {"plotly.io": None}):
            _display_graph_with_export_options(fig, "interactive")
            assert mock_st.info.called


def test_collect_files_to_validate_path_missing_and_run_validation_engine_branches(
    tmp_path: Path,
):
    from souschef.ui.app import _collect_files_to_validate, _run_validation_engine

    with (
        patch("souschef.ui.app.st") as mock_st,
        patch(
            "souschef.ui.app._normalize_and_validate_input_path", return_value=tmp_path
        ),
        patch("souschef.ui.app.safe_exists", return_value=False),
    ):
        assert _collect_files_to_validate("/nope") == []
        mock_st.error.assert_called_once()

    good = tmp_path / "playbook.yml"
    good.write_text("---\n- hosts: all\n")

    with patch("souschef.ui.app.st") as mock_st:
        fake_result = SimpleNamespace(
            level=SimpleNamespace(value="info"),
            category=SimpleNamespace(),
            message="ok",
            location="",
        )
        engine = MagicMock()
        engine.validate_conversion.return_value = [fake_result]
        with patch("souschef.core.validation.ValidationEngine", return_value=engine):
            res = _run_validation_engine([good])
            assert len(res) == 1
            assert res[0].location == "playbook.yml"

    with patch("souschef.ui.app.st") as mock_st:
        bad = tmp_path / "bad.yml"
        bad.write_text("x")
        with patch.object(Path, "read_text", side_effect=RuntimeError("read fail")):
            _run_validation_engine([bad])
            mock_st.warning.assert_called_once()


def test_normalize_input_empty_stripped_and_validation_execution_empty_results(
    tmp_path: Path,
):
    from souschef.ui.app import (
        _handle_validation_execution,
        _normalize_and_validate_input_path,
    )

    with patch("souschef.ui.app.st") as mock_st:
        assert _normalize_and_validate_input_path("   ") is None
        mock_st.error.assert_called_once()

    tracker = MagicMock()
    with (
        patch("souschef.ui.app.ProgressTracker", return_value=tracker),
        patch("souschef.ui.app.st") as mock_st,
        patch("souschef.ui.app._collect_files_to_validate", return_value=[]),
        patch(
            "souschef.ui.app._normalize_and_validate_input_path",
            return_value=tmp_path,
        ),
        patch("souschef.ui.app.safe_exists", return_value=True),
    ):
        mock_st.session_state = SessionState()
        _handle_validation_execution("/tmp/path", {"scope": "Full Suite"})
        mock_st.warning.assert_called()

    tracker2 = MagicMock()
    with (
        patch("souschef.ui.app.ProgressTracker", return_value=tracker2),
        patch("souschef.ui.app.st") as mock_st,
    ):
        mock_st.session_state = SessionState()
        res = SimpleNamespace(
            level=SimpleNamespace(value="info"),
            location="x",
            message="m",
            category=SimpleNamespace(),
        )
        with (
            patch(
                "souschef.ui.app._collect_files_to_validate",
                return_value=[tmp_path / "a.yml"],
            ),
            patch("souschef.ui.app._run_validation_engine", return_value=[res]),
            patch("souschef.ui.app._filter_results_by_scope", return_value=[]),
        ):
            _handle_validation_execution("/tmp/path", {"scope": "Security"})
            result = mock_st.session_state.validation_result
            assert result is not None
            assert "No issues found matching" in result  # type: ignore[operator]


def test_format_conversion_for_validation_and_parse_metrics_and_statuses():
    from souschef.ui.app import (
        _display_validation_export_options,
        _format_conversion_for_validation,
        _parse_validation_metrics,
    )

    conv = SimpleNamespace(
        id="c1",
        cookbook_name="cb",
        output_type="playbook",
        status="ok",
        created_at="2026-01-01",
    )
    out = _format_conversion_for_validation([conv], "c1")
    assert "cb" in out

    # parse total checks with malformed number to cover suppress block
    _parse_validation_metrics("[ERROR] x\nTotal checks: not-a-number")

    with patch("souschef.ui.app.st") as mock_st:
        mock_st.columns.return_value = (_ctx(), _ctx())
        _display_validation_export_options("r", "/p", "Security", {}, 0, 1, 0, 1)
        _display_validation_export_options("r", "/p", "Security", {}, 0, 0, 1, 1)
        assert mock_st.download_button.called


def test_display_validation_results_and_impact_medium_low_and_detailed_calls():
    from souschef.ui.app import (
        _display_detailed_impact_analysis,
        display_validation_results,
    )

    with (
        patch("souschef.ui.app._display_risk_assessment_breakdown") as a,
        patch("souschef.ui.app._display_critical_path_analysis") as b,
        patch("souschef.ui.app._display_migration_bottlenecks") as c,
        patch("souschef.ui.app._display_strategic_recommendations") as d,
    ):
        _display_detailed_impact_analysis({}, {}, [], [])
        a.assert_called_once()
        b.assert_called_once()
        c.assert_called_once()
        d.assert_called_once()

    with (
        patch("souschef.ui.app.st") as mock_st,
        patch("souschef.ui.app._display_validation_summary_metrics"),
        patch("souschef.ui.app._display_validation_status"),
        patch("souschef.ui.app._display_validation_sections"),
        patch("souschef.ui.app._display_validation_action_items"),
        patch("souschef.ui.app._display_validation_export_options"),
    ):
        mock_st.session_state = SessionState(
            {
                "validation_result": "[INFO] a: ok",
                "validation_path": "/tmp/p",
                "validation_type": "Full Suite",
                "validation_options": {},
            }
        )
        display_validation_results()
        mock_st.subheader.assert_called()


def test_app_sys_path_insertion_when_not_present():
    """Test that app.py adds parent directory to sys.path when not already present."""
    import importlib
    import sys
    from pathlib import Path

    # Get the app module path
    app_module_path = Path(__file__).parent.parent.parent / "souschef" / "ui" / "app.py"
    expected_path = str(app_module_path.parent.parent)

    # Store original sys.path and the cached module (if any)
    original_path = sys.path.copy()
    original_module = sys.modules.pop("souschef.ui.app", None)

    try:
        # Ensure expected_path is NOT in sys.path so the insertion branch executes
        sys.path = [p for p in sys.path if p != expected_path]

        # Mock environment to prevent main() execution during the reimport
        with (
            patch.dict(os.environ, {"STREAMLIT_SERVER_PORT": "8501"}),
            patch.dict("sys.modules", {"streamlit": MagicMock()}),
        ):
            # Import the module fresh - re-executes the top-level sys.path.insert code
            importlib.import_module("souschef.ui.app")

        # Verify the path was inserted by app.py's top-level code
        assert expected_path in sys.path

    finally:
        # Restore original sys.path
        sys.path = original_path
        # Restore or remove the module cache entry
        if original_module is not None:
            sys.modules["souschef.ui.app"] = original_module
        else:
            sys.modules.pop("souschef.ui.app", None)
