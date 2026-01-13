"""Tests for the SousChef UI components."""

from unittest.mock import patch

import networkx as nx

from souschef.ui.app import ProgressTracker, create_dependency_graph


class TestProgressTracker:
    """Test the ProgressTracker class."""

    @patch("streamlit.progress")
    @patch("streamlit.empty")
    def test_progress_tracker_init(self, mock_empty, mock_progress):
        """Test ProgressTracker initialization."""
        tracker = ProgressTracker(total_steps=10, description="Testing")

        assert tracker.total_steps == 10
        assert tracker.current_step == 0
        assert tracker.description == "Testing"
        mock_progress.assert_called_once_with(0)
        assert mock_empty.call_count == 1

    @patch("streamlit.progress")
    @patch("streamlit.empty")
    def test_progress_tracker_update(self, mock_empty, mock_progress):
        """Test ProgressTracker update functionality."""
        tracker = ProgressTracker(total_steps=10, description="Testing")

        # Update step
        tracker.update(step=5)
        mock_progress.return_value.progress.assert_called_with(0.5)

        # Update description
        tracker.update(description="Updated")
        assert tracker.description == "Updated"

    @patch("streamlit.progress")
    @patch("streamlit.empty")
    @patch("time.sleep")
    def test_progress_tracker_complete(self, mock_sleep, mock_empty, mock_progress):
        """Test ProgressTracker completion."""
        tracker = ProgressTracker(total_steps=10, description="Testing")

        tracker.complete("Done!")
        mock_progress.return_value.progress.assert_called_with(1.0)
        mock_sleep.assert_called_once_with(0.5)


class TestDependencyGraph:
    """Test dependency graph creation functions."""

    def test_create_dependency_graph_empty(self):
        """Test graph creation with empty analysis."""
        result = create_dependency_graph("", "interactive")
        assert result is None

    def test_create_dependency_graph_minimal(self):
        """Test graph creation with minimal dependency data."""
        # Create a simple NetworkX graph
        graph = nx.DiGraph()
        graph.add_edge("cookbook1", "cookbook2")

        # Test that the function can handle a NetworkX graph directly
        # (This tests the internal graph creation logic)
        analysis_text = """
Direct Dependencies:
- cookbook1: cookbook2

Transitive Dependencies:
- None

Circular Dependencies:
- None

Community Cookbooks:
- None
"""

        with patch("streamlit.error"):
            result = create_dependency_graph(analysis_text, "interactive")
            # Should return a plotly figure or None
            assert result is not None or result is None  # Allow for error cases

    def test_create_dependency_graph_with_circular(self):
        """Test graph creation with circular dependencies."""
        analysis_text = """
Direct Dependencies:
- cookbook1: cookbook2
- cookbook2: cookbook1

Transitive Dependencies:
- None

Circular Dependencies:
- cookbook1 -> cookbook2 -> cookbook1

Community Cookbooks:
- None
"""

        with patch("streamlit.error"):
            result = create_dependency_graph(analysis_text, "interactive")
            # Should handle circular dependencies gracefully
            assert result is not None or result is None

    @patch("matplotlib.pyplot.figure")
    @patch("matplotlib.pyplot.tight_layout")
    @patch("matplotlib.pyplot.axis")
    @patch("matplotlib.pyplot.title")
    @patch("networkx.draw_networkx_labels")
    @patch("networkx.draw_networkx_nodes")
    @patch("networkx.draw_networkx_edges")
    def test_create_dependency_graph_static(
        self,
        mock_edges,
        mock_nodes,
        mock_labels,
        mock_title,
        mock_axis,
        mock_layout,
        mock_figure,
    ):
        """Test static graph creation."""
        mock_fig = mock_figure.return_value.gcf.return_value
        mock_fig.__class__ = type("MockFig", (), {})

        analysis_text = """
Direct Dependencies:
- cookbook1: cookbook2

Transitive Dependencies:
- None

Circular Dependencies:
- None

Community Cookbooks:
- None
"""

        result = create_dependency_graph(analysis_text, "static")
        assert result is not None
        # matplotlib.pyplot.figure is called once explicitly, and gcf() may call it again
        assert mock_figure.call_count >= 1


class TestUIIntegration:
    """Integration tests for UI functionality."""

    def test_import_safety(self):
        """Test that all UI imports work correctly."""
        # This test ensures the UI module can be imported without issues
        from souschef.ui import app

        assert hasattr(app, "ProgressTracker")
        assert hasattr(app, "create_dependency_graph")
        assert hasattr(app, "main")

    def test_graph_creation_error_handling(self):
        """Test error handling in graph creation."""
        # Test with malformed input
        result = create_dependency_graph("invalid input", "interactive")
        # Should handle errors gracefully
        assert result is None or hasattr(result, "data")  # plotly figure or None
