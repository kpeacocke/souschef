"""Migration Configuration and Activity Visualisation Page for SousChef UI."""

import json
import sys
from pathlib import Path
from typing import Any

try:
    import streamlit as st
except ImportError:
    st = None  # type: ignore[assignment]

# Add the parent directory to the path so we can import souschef modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from souschef.assessment import (
    calculate_activity_breakdown,
)
from souschef.migration_config import (
    DeploymentTarget,
    MigrationConfig,
    MigrationStandard,
    ValidationTool,
)


def show_migration_config_page() -> None:
    """Show the migration configuration and visualisation page."""
    st.header("Migration Configuration & Activity Planning")

    st.markdown("""
    Configure your Chef-to-Ansible migration settings and visualise activity
    breakdowns showing manual vs AI-assisted effort.
    """)

    # Configuration section
    _show_configuration_section()

    st.divider()

    # Activity breakdown visualisation
    if "migration_config" in st.session_state:
        _show_activity_visualisation()


def _show_configuration_section() -> None:
    """Show the migration configuration section."""
    st.subheader("Migration Configuration")

    # Check if we already have a config
    if "migration_config" in st.session_state:
        _display_current_config()

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Reconfigure",
                help="Start a new configuration",
                key="reconfigure_migration",
            ):
                del st.session_state.migration_config
                st.rerun()

        with col2:
            if st.button(
                "Export Configuration",
                help="Download configuration as JSON",
                key="export_config",
            ):
                _export_configuration()

    else:
        _show_configuration_form()


def _display_current_config() -> None:
    """Display the current migration configuration."""
    config = st.session_state.migration_config

    st.success("Configuration active")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Deployment Target",
            config.deployment_target.value.replace("-", " ").title(),
        )

    with col2:
        st.metric(
            "Migration Standard",
            config.migration_standard.value.replace("-", " ").title(),
        )

    with col3:
        st.metric(
            "Target Python Version",
            config.target_python_version,
        )

    # Show full configuration in expander
    with st.expander("View Full Configuration"):
        st.json(config.to_dict())


def _show_configuration_form() -> None:
    """Show the interactive configuration form."""
    st.markdown("### Configure Your Migration")

    col1, col2 = st.columns(2)

    with col1:
        deployment_target = st.selectbox(
            "Deployment Target",
            options=[t.value for t in DeploymentTarget],
            format_func=lambda x: x.replace("-", " ").title(),
            help="Select where you will deploy your Ansible playbooks",
            key="cfg_deployment_target",
        )

        migration_standard = st.selectbox(
            "Migration Standard",
            options=[s.value for s in MigrationStandard],
            format_func=lambda x: x.replace("-", " ").title(),
            help="Select the migration approach and standards to follow",
            key="cfg_migration_standard",
        )

        inventory_source = st.text_input(
            "Inventory Source",
            value="hosts.ini",
            help="Path to your Ansible inventory file",
            key="cfg_inventory_source",
        )

    with col2:
        validation_tools = st.multiselect(
            "Validation Tools",
            options=[v.value for v in ValidationTool],
            default=["ansible-lint"],
            format_func=lambda x: x.replace("-", " ").title(),
            help="Select tools to validate your playbooks",
            key="cfg_validation_tools",
        )

        python_version = st.selectbox(
            "Python Version",
            options=["3.8", "3.9", "3.10", "3.11", "3.12"],
            index=2,  # Default to 3.10
            help="Python version for your Ansible environment",
            key="cfg_python_version",
        )

        ansible_version = st.text_input(
            "Ansible Version",
            value="2.15+",
            help="Ansible version or constraint (e.g., '2.15+', '>=2.14')",
            key="cfg_ansible_version",
        )

    if st.button(
        "Save Configuration",
        type="primary",
        help="Save and activate this configuration",
        key="save_config",
    ):
        try:
            # Create MigrationConfig
            config = MigrationConfig(
                deployment_target=DeploymentTarget(deployment_target),
                migration_standard=MigrationStandard(migration_standard),
                inventory_source=inventory_source,
                validation_tools=[ValidationTool(v) for v in validation_tools],
                target_python_version=python_version,
                target_ansible_version=ansible_version,
            )

            # Store in session state
            st.session_state.migration_config = config

            st.success("Configuration saved successfully!")
            st.rerun()

        except Exception as e:
            st.error(f"Failed to save configuration: {e}")


def _export_configuration() -> None:
    """Export the current configuration as JSON."""
    config = st.session_state.migration_config
    config_json = json.dumps(config.to_dict(), indent=2)

    st.download_button(
        label="Download Configuration (JSON)",
        data=config_json,
        file_name="migration_config.json",
        mime="application/json",
        help="Download configuration as JSON file",
    )


def _show_activity_visualisation() -> None:
    """Show the activity breakdown visualisation."""
    st.subheader("Migration Activity Breakdown")

    st.markdown("""
    This visualisation shows the estimated effort for different migration
    activities, comparing manual effort vs AI-assisted effort with SousChef.
    """)

    # Input section for activity breakdown
    col1, col2 = st.columns(2)

    with col1:
        cookbook_path = st.text_input(
            "Cookbook Path",
            value=st.session_state.get("analysis_cookbook_path", ""),
            help="Path to cookbook(s) for activity breakdown",
            key="activity_cookbook_path",
        )

    with col2:
        migration_strategy = st.selectbox(
            "Migration Strategy",
            options=["phased", "big_bang", "parallel"],
            format_func=lambda x: x.replace("_", " ").title(),
            help="Select your migration strategy",
            key="activity_migration_strategy",
        )

    if st.button(
        "Generate Activity Breakdown",
        type="primary",
        help="Calculate activity breakdown for the specified cookbook(s)",
        key="generate_breakdown",
    ):
        if not cookbook_path.strip():
            st.error("Please enter a cookbook path.")
            return

        _generate_and_display_breakdown(cookbook_path.strip(), migration_strategy)


def _generate_and_display_breakdown(
    cookbook_path: str, migration_strategy: str
) -> None:
    """Generate and display activity breakdown."""
    try:
        with st.spinner("Calculating activity breakdown..."):
            # Calculate breakdown
            breakdown = calculate_activity_breakdown(
                cookbook_path,
                migration_strategy,
            )

            if "error" in breakdown:
                st.error(f"Failed to generate breakdown: {breakdown['error']}")
                return

            # Store breakdown in session state
            st.session_state.activity_breakdown = breakdown

            # Display breakdown
            _display_activity_breakdown(breakdown)

    except Exception as e:
        st.error(f"Failed to generate activity breakdown: {e}")


def _display_activity_breakdown(breakdown: dict[str, Any]) -> None:
    """Display the activity breakdown with visualisations."""
    st.success("Activity breakdown generated successfully!")

    # Summary metrics
    _display_breakdown_metrics(breakdown)

    col1, col2 = st.columns([1, 2])

    with col1:
        # Activity narrative summary
        _display_activity_summary(breakdown)

    with col2:
        # Activity table
        _display_activity_table(breakdown)

    # Time savings visualisation
    _display_time_savings_chart(breakdown)

    # Export options
    _display_breakdown_export_options(breakdown)


def _display_breakdown_metrics(breakdown: dict[str, Any]) -> None:
    """Display summary metrics from breakdown."""
    summary = breakdown.get("summary", {})

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Manual Hours",
            f"{summary.get('total_manual_hours', 0):.1f}h",
        )

    with col2:
        st.metric(
            "Total AI-Assisted Hours",
            f"{summary.get('total_ai_assisted_hours', 0):.1f}h",
        )

    with col3:
        st.metric(
            "Time Saved",
            f"{summary.get('time_saved_hours', 0):.1f}h",
            delta=f"{summary.get('efficiency_gain_percent', 0):.0f}%",
        )

    with col4:
        timeline_weeks = summary.get("timeline_weeks", 0)
        st.metric(
            "Estimated Timeline",
            f"{timeline_weeks} weeks" if timeline_weeks > 0 else "N/A",
        )


def _display_activity_summary(breakdown: dict[str, Any]) -> None:
    """Display a readable activity breakdown summary alongside numbers."""
    activities = breakdown.get("activities", [])

    if not activities:
        return

    st.subheader("Activity Summary")

    for activity in activities:
        name = activity.get("name", "Unknown")
        count = activity.get("count", 0)
        description = activity.get("description", "")
        manual_hours = activity.get("manual_hours", 0)
        ai_hours = activity.get("ai_assisted_hours", 0)
        time_saved = activity.get("time_saved", 0)
        efficiency = activity.get("efficiency_gain_percent", 0)

        # Format as a compact card-like display
        st.markdown(
            f"""**{name}** ({count} items)

*{description}*

Manual: {manual_hours:.1f}h → AI: {ai_hours:.1f}h

**Saved: {time_saved:.1f}h ({efficiency:.0f}%)**"""
        )
        st.divider()


def _display_activity_table(breakdown: dict[str, Any]) -> None:
    """Display activity breakdown as a table."""
    st.subheader("Activity Details")

    activities = breakdown.get("activities", [])

    if not activities:
        st.info("No activities found in breakdown.")
        return

    # Prepare data for display
    table_data = []
    for activity in activities:
        table_data.append(
            {
                "Activity": activity.get("name", "Unknown"),
                "Count": activity.get("count", 0),
                "Description": activity.get("description", ""),
                "Manual Hours": f"{activity.get('manual_hours', 0):.1f}",
                "AI-Assisted Hours": f"{activity.get('ai_assisted_hours', 0):.1f}",
                "Time Saved": f"{activity.get('time_saved', 0):.1f}",
                "Efficiency Gain": f"{activity.get('efficiency_gain_percent', 0):.0f}%",
            }
        )

    st.table(table_data)


def _display_time_savings_chart(breakdown: dict[str, Any]) -> None:
    """Display time savings as a bar chart."""
    try:
        import pandas as pd

        st.subheader("Time Savings Visualisation")

        activities = breakdown.get("activities", [])

        if not activities:
            return

        # Prepare data for chart
        chart_data = []
        for activity in activities:
            chart_data.append(
                {
                    "Activity": activity.get("name", "Unknown"),
                    "Manual Hours": activity.get("manual_hours", 0),
                    "AI-Assisted Hours": activity.get("ai_assisted_hours", 0),
                }
            )

        df = pd.DataFrame(chart_data)

        # Create stacked bar chart
        st.bar_chart(
            df.set_index("Activity"),
            height=400,
        )

    except ImportError:
        st.warning("Pandas is required for chart visualisation.")


def _display_breakdown_export_options(breakdown: dict[str, Any]) -> None:
    """Display export options for activity breakdown."""
    st.subheader("Export Activity Breakdown")

    col1, col2 = st.columns(2)

    with col1:
        # Export as JSON
        breakdown_json = json.dumps(breakdown, indent=2)
        st.download_button(
            label="Download as JSON",
            data=breakdown_json,
            file_name="activity_breakdown.json",
            mime="application/json",
            help="Download activity breakdown as JSON file",
        )

    with col2:
        # Export as Markdown report
        markdown_report = _generate_markdown_report(breakdown)
        st.download_button(
            label="Download as Markdown",
            data=markdown_report,
            file_name="activity_breakdown.md",
            mime="text/markdown",
            help="Download activity breakdown as Markdown report",
        )


def _generate_markdown_report(breakdown: dict[str, Any]) -> str:
    """Generate a Markdown report from activity breakdown."""
    summary = breakdown.get("summary", {})
    activities = breakdown.get("activities", [])

    report = f"""# Migration Activity Breakdown Report

## Summary

- **Total Manual Hours**: {summary.get("total_manual_hours", 0):.1f}h
- **Total AI-Assisted Hours**: {summary.get("total_ai_assisted_hours", 0):.1f}h
- **Time Saved**: {summary.get("time_saved_hours", 0):.1f}h
- **Efficiency Gain**: {summary.get("efficiency_gain_percent", 0):.0f}%
- **Estimated Timeline**: {summary.get("timeline_weeks", 0)} weeks

## Activity Details

"""

    for activity in activities:
        report += f"""### {activity.get("name", "Unknown")}

- **Count**: {activity.get("count", 0)}
- **Description**: {activity.get("description", "")}
- **Manual Hours**: {activity.get("manual_hours", 0):.1f}h
- **AI-Assisted Hours**: {activity.get("ai_assisted_hours", 0):.1f}h
- **Time Saved**: {activity.get("time_saved", 0):.1f}h
- **Efficiency Gain**: {activity.get("efficiency_gain_percent", 0):.0f}%

"""

    report += """---
*Generated by SousChef Migration Configuration Tool*
"""

    return report
