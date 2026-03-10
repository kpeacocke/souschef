"""Second wave of targeted branch tests for app.py."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import networkx as nx
import pytest


class SessionState(dict):
    def __getattr__(self, name: str):
        return self.get(name)

    def __setattr__(self, name: str, value):
        self[name] = value


def _ctx() -> MagicMock:
    m = MagicMock()
    m.__enter__ = Mock(return_value=m)
    m.__exit__ = Mock(return_value=False)
    return m


@pytest.fixture(autouse=True)
def _prevent_auto_main():
    with (
        patch.dict(os.environ, {"STREAMLIT_SERVER_PORT": "8501"}),
        patch.dict("sys.modules", {"streamlit": MagicMock()}),
    ):
        yield


def test_render_history_selectbox_invokes_format_func_path():
    from souschef.ui.app import _render_history_selectbox

    analyses = [
        SimpleNamespace(
            id="a1",
            cookbook_name="nginx",
            cookbook_version="1",
            complexity="Low",
            created_at="2026-01-01",
        )
    ]

    with patch("souschef.ui.app.st") as mock_st:

        def _selectbox(*args, **kwargs):
            fmt = kwargs["format_func"]
            fmt("a1")
            return None

        mock_st.selectbox.side_effect = _selectbox
        _render_history_selectbox(analyses)
        mock_st.selectbox.assert_called_once()


def test_execute_migration_plan_generation_exception_branch():
    from souschef.ui.app import _execute_migration_plan_generation

    tracker = MagicMock()
    with (
        patch("souschef.ui.app.ProgressTracker", return_value=tracker),
        patch("souschef.ui.app.st") as mock_st,
        patch(
            "souschef.assessment.generate_migration_plan",
            side_effect=RuntimeError("boom"),
        ),
    ):
        mock_st.button.return_value = True
        mock_st.session_state = SessionState()
        _execute_migration_plan_generation("/tmp/a", "phased", 8)
        tracker.close.assert_called_once()
        mock_st.error.assert_called_once()


def test_display_migration_action_buttons_report_error_dep_error_and_multi_info():
    from souschef.ui.app import _display_migration_action_buttons

    with patch("souschef.ui.app.st") as mock_st:
        mock_st.session_state = SessionState(
            {
                "strategy": "phased",
                "timeline": 8,
                "migration_plan": "plan",
            }
        )
        mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
        mock_st.spinner.return_value = _ctx()
        mock_st.button.side_effect = [True, True, False]

        with (
            patch(
                "souschef.assessment.generate_migration_report",
                side_effect=RuntimeError("r"),
            ),
            patch(
                "souschef.assessment.analyse_cookbook_dependencies",
                side_effect=RuntimeError("d"),
            ),
        ):
            _display_migration_action_buttons("/tmp/one")
            assert mock_st.error.called

    with patch("souschef.ui.app.st") as mock_st:
        mock_st.session_state = SessionState(
            {"strategy": "phased", "timeline": 8, "migration_plan": "plan"}
        )
        mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
        mock_st.button.side_effect = [False, True, False]
        _display_migration_action_buttons("/tmp/one,/tmp/two")
        mock_st.info.assert_called()


def test_display_migration_action_buttons_success_paths():
    from souschef.ui.app import _display_migration_action_buttons

    with patch("souschef.ui.app.st") as mock_st:
        mock_st.session_state = SessionState(
            {"strategy": "phased", "timeline": 8, "migration_plan": "plan"}
        )
        mock_st.columns.return_value = (_ctx(), _ctx(), _ctx())
        mock_st.spinner.return_value = _ctx()
        mock_st.button.side_effect = [True, True, False]

        with (
            patch(
                "souschef.assessment.generate_migration_report", return_value="report"
            ),
            patch(
                "souschef.assessment.analyse_cookbook_dependencies", return_value="deps"
            ),
        ):
            _display_migration_action_buttons("/tmp/one")

        assert mock_st.session_state.detailed_report == "report"
        assert mock_st.session_state.dep_analysis == "deps"
        assert mock_st.success.called


def test_create_static_matplotlib_graph_circular_and_colour_branches():
    from souschef.ui.app import _create_static_matplotlib_graph

    g = nx.DiGraph()
    g.add_edge("a", "b")
    g.add_edge("b", "a", circular=True)
    g.nodes["a"]["community"] = True
    pos = {"a": (0.0, 0.0), "b": (1.0, 1.0)}

    fake_plt = MagicMock()
    fake_plt.gcf.return_value = object()

    with (
        patch.dict(
            "sys.modules", {"matplotlib": MagicMock(), "matplotlib.pyplot": fake_plt}
        ),
        patch("networkx.draw_networkx_edges"),
        patch("networkx.draw_networkx_nodes"),
        patch("networkx.draw_networkx_labels"),
    ):
        fig = _create_static_matplotlib_graph(g, pos, 2, "spring")
    assert fig is not None


def test_create_static_matplotlib_graph_marks_circular_node_red_branch():
    from souschef.ui.app import _create_static_matplotlib_graph

    g = nx.DiGraph()
    g.add_edge("x", "y", circular=True)
    pos = {"x": (0.0, 0.0), "y": (1.0, 1.0)}

    fake_plt = MagicMock()
    fake_plt.gcf.return_value = object()

    with (
        patch.dict(
            "sys.modules", {"matplotlib": MagicMock(), "matplotlib.pyplot": fake_plt}
        ),
        patch("networkx.draw_networkx_edges"),
        patch("networkx.draw_networkx_nodes"),
        patch("networkx.draw_networkx_labels"),
    ):
        out = _create_static_matplotlib_graph(g, pos, 2, "spring")
    assert out is not None


def test_create_dependency_graph_exception_branch():
    from souschef.ui.app import create_dependency_graph

    with (
        patch(
            "souschef.ui.app._parse_dependency_analysis",
            side_effect=RuntimeError("bad parse"),
        ),
        patch("souschef.ui.app.st") as mock_st,
    ):
        out = create_dependency_graph("x", "interactive")
        assert out is None
        mock_st.error.assert_called_once()


def test_calculate_migration_impact_medium_parallel_2_branch():
    from souschef.ui.app import _calculate_migration_impact

    deps = {f"cb{i}": [f"d{i}"] for i in range(11)}
    out = _calculate_migration_impact(deps, [("a", "b"), ("c", "d")], [])
    assert out["complexity_level"] == "Medium"
    assert out["timeline_impact_weeks"] == 2
    assert out["parallel_streams"] == 2


def test_display_impact_analysis_section_medium_and_low_risk_delta_branches():
    from souschef.ui.app import _display_impact_analysis_section

    with patch("souschef.ui.app.st") as mock_st:
        mock_st.columns.return_value = (_ctx(), _ctx(), _ctx(), _ctx())
        mock_st.expander.return_value = _ctx()
        with (
            patch(
                "souschef.ui.app._parse_dependency_analysis",
                return_value=({"a": ["b"]}, [], []),
            ),
            patch(
                "souschef.ui.app._calculate_migration_impact",
                return_value={
                    "risk_score": 5.0,
                    "timeline_impact_weeks": 1,
                    "complexity_level": "Medium",
                    "parallel_streams": 1,
                    "critical_path": [],
                    "bottlenecks": [],
                    "recommendations": [],
                },
            ),
            patch("souschef.ui.app._display_detailed_impact_analysis"),
        ):
            _display_impact_analysis_section("x")

    with patch("souschef.ui.app.st") as mock_st:
        mock_st.columns.return_value = (_ctx(), _ctx(), _ctx(), _ctx())
        mock_st.expander.return_value = _ctx()
        with (
            patch(
                "souschef.ui.app._parse_dependency_analysis",
                return_value=({"a": ["b"]}, [], []),
            ),
            patch(
                "souschef.ui.app._calculate_migration_impact",
                return_value={
                    "risk_score": 2.0,
                    "timeline_impact_weeks": 0,
                    "complexity_level": "Low",
                    "parallel_streams": 1,
                    "critical_path": [],
                    "bottlenecks": [],
                    "recommendations": [],
                },
            ),
            patch("souschef.ui.app._display_detailed_impact_analysis"),
        ):
            _display_impact_analysis_section("x")


def test_run_validation_engine_empty_results_creates_info_record(tmp_path: Path):
    from souschef.ui.app import _run_validation_engine

    f = tmp_path / "ok.yml"
    f.write_text("---\n- hosts: all\n")

    engine = MagicMock()
    engine.validate_conversion.return_value = []
    with patch("souschef.core.validation.ValidationEngine", return_value=engine):
        out = _run_validation_engine([f])
    assert len(out) == 1
    assert out[0].location == "ok.yml"


def test_parse_validation_metrics_total_checks_value_error_suppressed():
    from souschef.ui.app import _parse_validation_metrics

    errors, _, _, total = _parse_validation_metrics("[ERROR] e\nTotal checks: NaN")
    assert errors == 1
    assert total == 1
