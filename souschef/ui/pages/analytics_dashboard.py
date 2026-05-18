"""Analytics dashboard for risk, time, and cost insights."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

import streamlit as st

from souschef.api import (
    EstimationInput,
    RiskScoringInput,
    estimate_time_cost,
    score_risk,
    serialise_explainability,
)


def _complexity_to_score(complexity: str) -> float:
    """Map complexity label to a numeric score."""
    mapping = {"low": 30.0, "medium": 55.0, "high": 82.0}
    return mapping.get(complexity.lower(), 50.0)


def _risk_distribution_for_complexity(complexity: str) -> dict[str, int]:
    """Create a baseline risk distribution from complexity level."""
    level = complexity.lower()
    if level == "high":
        return {"low": 1, "medium": 2, "high": 3}
    if level == "medium":
        return {"low": 2, "medium": 3, "high": 1}
    return {"low": 4, "medium": 1, "high": 0}


def _manual_steps_for_complexity(complexity: str) -> int:
    """Estimate baseline manual steps from complexity."""
    level = complexity.lower()
    if level == "high":
        return 4
    if level == "medium":
        return 2
    return 1


def _build_dashboard_rows(
    analysis_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build item-level dashboard rows from analysis results."""
    rows: list[dict[str, Any]] = []

    for result in analysis_results:
        item_name = str(result.get("name", "Unknown"))
        complexity = str(result.get("complexity", "Medium"))
        dependencies = int(result.get("dependencies", 0) or 0)
        status = str(result.get("status", "Unknown"))
        maintainer = str(result.get("maintainer", "unknown"))

        risk_input = RiskScoringInput(
            item_id=item_name,
            app=item_name,
            team=maintainer,
            environment="production",
            complexity_score=_complexity_to_score(complexity),
            dependency_count=dependencies,
            custom_resource_count=max(0, dependencies // 2),
            security_hotspots=0,
            test_coverage_percent=80.0,
            manual_steps=_manual_steps_for_complexity(complexity),
        )
        risk_result = score_risk(risk_input)

        estimate_input = EstimationInput(
            project_id=item_name,
            total_items=max(dependencies + 1, 1),
            average_complexity=_complexity_to_score(complexity),
            average_manual_steps=float(_manual_steps_for_complexity(complexity)),
            risk_distribution=_risk_distribution_for_complexity(complexity),
        )
        estimate_result = estimate_time_cost(estimate_input)

        rows.append(
            {
                "Item": item_name,
                "Complexity": complexity,
                "Status": status,
                "Dependencies": dependencies,
                "Risk Level": risk_result.risk_level,
                "Risk Score": risk_result.total_score,
                "Effort Hours": estimate_result.effort_hours,
                "Duration Weeks": estimate_result.estimated_duration_weeks,
                "Cost Amount": estimate_result.cost_amount,
                "Confidence Low Hours": estimate_result.confidence_low_hours,
                "Confidence High Hours": estimate_result.confidence_high_hours,
                "Confidence Low Cost": estimate_result.confidence_low_cost,
                "Confidence High Cost": estimate_result.confidence_high_cost,
                "Risk Explainability": serialise_explainability(risk_result),
            }
        )

    return rows


def _filter_dashboard_rows(
    rows: list[dict[str, Any]],
    complexity_filter: list[str],
    risk_filter: list[str],
    status_filter: list[str],
    search_query: str,
) -> list[dict[str, Any]]:
    """Filter dashboard rows by selected criteria."""
    filtered = rows

    if complexity_filter:
        allowed = {value.lower() for value in complexity_filter}
        filtered = [
            row for row in filtered if str(row["Complexity"]).lower() in allowed
        ]

    if risk_filter:
        allowed = {value.lower() for value in risk_filter}
        filtered = [
            row for row in filtered if str(row["Risk Level"]).lower() in allowed
        ]

    if status_filter:
        allowed = {value.lower() for value in status_filter}
        filtered = [row for row in filtered if str(row["Status"]).lower() in allowed]

    if search_query.strip():
        query = search_query.strip().lower()
        filtered = [row for row in filtered if query in str(row["Item"]).lower()]

    return filtered


def _exportable_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return flat rows suitable for CSV and JSON export."""
    return [
        {
            "item": row["Item"],
            "complexity": row["Complexity"],
            "status": row["Status"],
            "dependencies": row["Dependencies"],
            "risk_level": row["Risk Level"],
            "risk_score": row["Risk Score"],
            "effort_hours": row["Effort Hours"],
            "duration_weeks": row["Duration Weeks"],
            "cost_amount": row["Cost Amount"],
            "confidence_low_hours": row["Confidence Low Hours"],
            "confidence_high_hours": row["Confidence High Hours"],
            "confidence_low_cost": row["Confidence Low Cost"],
            "confidence_high_cost": row["Confidence High Cost"],
        }
        for row in rows
    ]


def _rows_to_csv(rows: list[dict[str, Any]]) -> str:
    """Serialise rows to CSV text."""
    output = io.StringIO()
    fieldnames = [
        "item",
        "complexity",
        "status",
        "dependencies",
        "risk_level",
        "risk_score",
        "effort_hours",
        "duration_weeks",
        "cost_amount",
        "confidence_low_hours",
        "confidence_high_hours",
        "confidence_low_cost",
        "confidence_high_cost",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def show_analytics_dashboard_page() -> None:
    """Render analytics dashboard with widgets, drill-down, and exports."""
    st.header("Analytics Dashboard")
    st.markdown("Risk, time, and cost insights with drill-down and export support.")

    raw_results = st.session_state.get("analysis_results") or []
    if not raw_results:
        st.info("Run cookbook analysis first to populate dashboard analytics.")
        return

    rows = _build_dashboard_rows(raw_results)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        complexity_filter = st.multiselect(
            "Complexity",
            options=sorted({str(row["Complexity"]) for row in rows}),
        )
    with col2:
        risk_filter = st.multiselect(
            "Risk Level",
            options=sorted({str(row["Risk Level"]).title() for row in rows}),
        )
    with col3:
        status_filter = st.multiselect(
            "Status",
            options=sorted({str(row["Status"]) for row in rows}),
        )
    with col4:
        search_query = st.text_input("Search Item", value="")

    filtered_rows = _filter_dashboard_rows(
        rows=rows,
        complexity_filter=complexity_filter,
        risk_filter=risk_filter,
        status_filter=status_filter,
        search_query=search_query,
    )

    st.subheader("Summary Widgets")
    widget_1, widget_2, widget_3 = st.columns(3)
    with widget_1:
        high_risk_count = len(
            [row for row in filtered_rows if str(row["Risk Level"]).lower() == "high"]
        )
        st.metric("High-Risk Items", high_risk_count)
    with widget_2:
        total_effort = sum(float(row["Effort Hours"]) for row in filtered_rows)
        st.metric("Total Effort (Hours)", f"{total_effort:.2f}")
    with widget_3:
        total_cost = sum(float(row["Cost Amount"]) for row in filtered_rows)
        st.metric("Total Cost", f"${total_cost:,.2f}")

    st.subheader("Filtered Items")
    st.dataframe(_exportable_rows(filtered_rows), width="stretch")

    st.subheader("Export Filtered View")
    export_rows = _exportable_rows(filtered_rows)
    export_json = json.dumps(export_rows, indent=2)
    export_csv = _rows_to_csv(export_rows)

    export_col_1, export_col_2 = st.columns(2)
    with export_col_1:
        st.download_button(
            "Export JSON",
            data=export_json,
            file_name="analytics_dashboard.json",
            mime="application/json",
            width="stretch",
        )
    with export_col_2:
        st.download_button(
            "Export CSV",
            data=export_csv,
            file_name="analytics_dashboard.csv",
            mime="text/csv",
            width="stretch",
        )

    if filtered_rows:
        st.subheader("Item Drill-Down")
        selected_item = st.selectbox(
            "Select item",
            options=[str(row["Item"]) for row in filtered_rows],
        )
        selected_row = next(
            row for row in filtered_rows if str(row["Item"]) == selected_item
        )

        detail_col_1, detail_col_2, detail_col_3 = st.columns(3)
        with detail_col_1:
            st.metric("Risk Score", f"{selected_row['Risk Score']:.2f}")
        with detail_col_2:
            st.metric("Effort Hours", f"{selected_row['Effort Hours']:.2f}")
        with detail_col_3:
            st.metric("Cost", f"${selected_row['Cost Amount']:,.2f}")

        st.caption(
            "Confidence range (hours): "
            f"{selected_row['Confidence Low Hours']:.2f} - "
            f"{selected_row['Confidence High Hours']:.2f}"
        )
        st.caption(
            "Confidence range (cost): "
            f"${selected_row['Confidence Low Cost']:,.2f} - "
            f"${selected_row['Confidence High Cost']:,.2f}"
        )

        st.markdown("**Risk explainability**")
        st.json(selected_row["Risk Explainability"])
