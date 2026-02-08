"""Ansible Environment Assessment Page for SousChef UI."""

import json
import sys
from pathlib import Path

import streamlit as st

# Add the parent directory to the path so we can import souschef modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from souschef.ansible_upgrade import assess_ansible_environment


def _display_assessment_intro() -> None:
    """Render the assessment page title and introduction."""
    st.title("🔍 Ansible Environment Assessment")
    st.markdown(
        """
    Assess your current Ansible environment to understand the baseline
    configuration before planning an upgrade.
    """
    )


def _render_assessment_inputs() -> tuple[str, bool]:
    """Render input fields and return the path and button state."""
    col1, col2 = st.columns(2)

    with col1:
        environment_path = st.text_input(
            "Environment Path (optional)",
            value="",
            help="Path to Ansible env/venv. Leave empty to detect current.",
        )

    with col2:
        detect_btn = st.button("🔍 Assess Environment", use_container_width=True)

    return environment_path, detect_btn


def _display_assessment_results(assessment: dict[str, object]) -> None:
    """Display assessment details and export options."""
    st.subheader("📊 Assessment Results")

    col1, col2, col3 = st.columns(3)
    with col1:
        version = assessment.get("current_version", "Unknown")
        st.metric("Ansible Version", str(version))

    with col2:
        python_ver = assessment.get("python_version", "Unknown")
        st.metric("Python Version", str(python_ver))

    with col3:
        eol = assessment.get("eol_date", "Unknown")
        st.metric("EOL Date", str(eol))

    st.divider()

    _display_assessment_collections(assessment)
    _display_assessment_warnings(assessment)
    _display_assessment_details(assessment)
    _display_assessment_export(assessment)


def _display_assessment_collections(assessment: dict[str, object]) -> None:
    """Show installed collection details if present."""
    if "installed_collections" not in assessment:
        return

    collections_obj = assessment["installed_collections"]
    if not isinstance(collections_obj, list):
        return

    collections: list[str] = collections_obj

    st.subheader(f"📦 Installed Collections ({len(collections)} total)")

    col1, col2 = st.columns(2)
    mid = len(collections) // 2

    with col1:
        for collection in collections[:mid]:
            st.text(f"• {collection}")

    with col2:
        for collection in collections[mid:]:
            st.text(f"• {collection}")


def _display_assessment_warnings(assessment: dict[str, object]) -> None:
    """Render any warnings from the assessment."""
    warnings = assessment.get("warnings")
    if not warnings or not isinstance(warnings, list):
        return

    st.warning("**Warnings:**")
    for warning in warnings:
        st.write(f"- {warning}")


def _display_assessment_details(assessment: dict[str, object]) -> None:
    """Show additional assessment details."""
    st.divider()
    st.subheader("📋 Additional Details")

    details_col1, details_col2 = st.columns(2)

    with details_col1:
        if "full_version" in assessment:
            st.write(f"**Full Version:** {assessment['full_version']}")
        if "config_paths" in assessment:
            config_paths = assessment["config_paths"]
            if isinstance(config_paths, list):
                st.write(f"**Config Paths:** {', '.join(str(p) for p in config_paths)}")

    with details_col2:
        if "support_status" in assessment:
            st.write(f"**Support Status:** {assessment['support_status']}")
        if "version_type" in assessment:
            st.write(f"**Version Type:** {assessment['version_type']}")


def _display_assessment_export(assessment: dict[str, object]) -> None:
    """Provide a JSON export for the assessment results."""
    st.divider()
    st.subheader("📥 Export Assessment")

    assessment_json = json.dumps(assessment, indent=2, default=str)
    st.download_button(
        label="Download Assessment as JSON",
        data=assessment_json,
        file_name="ansible_assessment.json",
        mime="application/json",
    )


def _display_assessment_help() -> None:
    """Render the assessment help section."""
    st.divider()
    with st.expander("ℹ️ Assessment Help"):
        st.markdown(
            """
        **What is an assessment?**

        An assessment gathers information about your current Ansible
        environment, including:

        - **Current Ansible Version**: The version of Ansible installed
        - **Python Version**: The Python version Ansible is using
        - **Installed Collections**: All collections and their versions
        - **EOL Status**: Whether your Ansible version is still supported
        - **Configuration**: Ansible configuration paths and settings

        This information is crucial for planning your upgrade strategy
        and identifying potential compatibility issues.

        **Next Steps:**

        After assessing your environment, you can:
        1. Generate an upgrade plan to see the path from your current version
        2. Validate collection compatibility for target Ansible versions
        3. Create a testing strategy for your upgrade
        """
        )


def show_ansible_assessment_page() -> None:
    """
    Display the Ansible Environment Assessment page.

    Shows the current Ansible environment configuration including version,
    Python version, installed collections, and EOL status.
    """
    _display_assessment_intro()
    environment_path, detect_btn = _render_assessment_inputs()

    if detect_btn or st.session_state.get("ansible_assessment_results"):
        st.divider()

        try:
            with st.spinner("Assessing Ansible environment..."):
                path = environment_path if environment_path else "."
                assessment = assess_ansible_environment(path)

            # Store results in session state
            st.session_state.ansible_assessment_results = assessment

            _display_assessment_results(assessment)

        except Exception as e:
            st.error(f"❌ Error assessing environment: {str(e)}")
            st.exception(e)

    _display_assessment_help()
