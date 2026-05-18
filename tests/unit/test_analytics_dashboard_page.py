"""Unit tests for analytics dashboard page."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch


class SessionState(dict):
    """Session state helper with attribute access."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value


def _ctx() -> MagicMock:
    """Return context manager mock."""
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=ctx)
    ctx.__exit__ = Mock(return_value=None)
    return ctx


def test_filter_dashboard_rows_applies_all_filters() -> None:
    """Filtering should honour complexity, risk, status, and text query."""
    from souschef.ui.pages.analytics_dashboard import _filter_dashboard_rows

    rows = [
        {
            "Item": "nginx",
            "Complexity": "High",
            "Risk Level": "high",
            "Status": "Analysed",
        },
        {
            "Item": "redis",
            "Complexity": "Low",
            "Risk Level": "low",
            "Status": "Analysed",
        },
    ]

    filtered = _filter_dashboard_rows(
        rows,
        complexity_filter=["High"],
        risk_filter=["High"],
        status_filter=["Analysed"],
        search_query="ngi",
    )

    assert len(filtered) == 1
    assert filtered[0]["Item"] == "nginx"


def test_rows_to_csv_includes_header_and_item() -> None:
    """CSV export should include expected columns and values."""
    from souschef.ui.pages.analytics_dashboard import _rows_to_csv

    csv_output = _rows_to_csv(
        [
            {
                "item": "nginx",
                "complexity": "High",
                "status": "Analysed",
                "dependencies": 2,
                "risk_level": "high",
                "risk_score": 71.2,
                "effort_hours": 18.5,
                "duration_weeks": 1.0,
                "cost_amount": 3330.0,
                "confidence_low_hours": 16.0,
                "confidence_high_hours": 22.0,
                "confidence_low_cost": 2880.0,
                "confidence_high_cost": 3960.0,
            }
        ]
    )

    assert "item,complexity,status" in csv_output
    assert "nginx" in csv_output


@patch("souschef.ui.pages.analytics_dashboard.st")
def test_show_analytics_dashboard_page_empty_state(mock_st) -> None:
    """Page should show info message when no analysis data exists."""
    from souschef.ui.pages.analytics_dashboard import show_analytics_dashboard_page

    mock_st.session_state = SessionState()

    show_analytics_dashboard_page()

    mock_st.info.assert_called_once()


@patch("souschef.ui.pages.analytics_dashboard.st")
def test_show_analytics_dashboard_page_key_interactions(mock_st) -> None:
    """Page should render widgets, drill-down, and exports with filtered data."""
    from souschef.ui.pages.analytics_dashboard import show_analytics_dashboard_page

    mock_st.session_state = SessionState(
        {
            "analysis_results": [
                {
                    "name": "nginx",
                    "complexity": "High",
                    "dependencies": 3,
                    "status": "Analysed",
                    "maintainer": "platform",
                },
                {
                    "name": "redis",
                    "complexity": "Low",
                    "dependencies": 1,
                    "status": "Analysed",
                    "maintainer": "platform",
                },
            ]
        }
    )

    mock_st.columns.side_effect = [
        [_ctx(), _ctx(), _ctx(), _ctx()],
        [_ctx(), _ctx(), _ctx()],
        [_ctx(), _ctx()],
        [_ctx(), _ctx(), _ctx()],
    ]
    mock_st.multiselect.side_effect = [[], [], []]
    mock_st.text_input.return_value = ""
    mock_st.selectbox.return_value = "nginx"

    show_analytics_dashboard_page()

    assert mock_st.metric.call_count >= 6
    mock_st.dataframe.assert_called_once()
    assert mock_st.download_button.call_count == 2
    mock_st.json.assert_called_once()
