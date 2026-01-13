"""Visual Migration Planning Interface for SousChef.

A Streamlit-based web interface for Chef to Ansible migration planning,
assessment, and visualization.
"""

import streamlit as st
from pathlib import Path
import sys
import os

# Add the parent directory to the path so we can import souschef modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import page modules
from souschef.ui.pages.cookbook_analysis import show_cookbook_analysis_page


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="SousChef - Chef to Ansible Migration",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("SousChef - Visual Migration Planning")
    st.markdown("*AI-powered Chef to Ansible migration planning interface*")

    # Sidebar navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["Dashboard", "Cookbook Analysis", "Migration Planning", "Dependency Mapping", "Validation Reports"]
    )

    # Main content area
    if page == "Dashboard":
        show_dashboard()
    elif page == "Cookbook Analysis":
        show_cookbook_analysis_page()
    elif page == "Migration Planning":
        show_migration_planning()
    elif page == "Dependency Mapping":
        show_dependency_mapping()
    elif page == "Validation Reports":
        show_validation_reports()


def show_dashboard():
    """Show the main dashboard with migration overview."""
    st.header("Migration Dashboard")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Cookbooks Analyzed", "0", "Ready to analyze")
        st.caption("Total cookbooks processed")

    with col2:
        st.metric("Migration Complexity", "Unknown", "Assessment needed")
        st.caption("Overall migration effort")

    with col3:
        st.metric("Conversion Rate", "0%", "Start migration")
        st.caption("Successful conversions")

    st.divider()

    # Quick actions
    st.subheader("Quick Actions")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Analyze Cookbook Directory", type="primary", use_container_width=True):
            st.rerun()  # This will trigger navigation to cookbook analysis

    with col2:
        if st.button("Generate Migration Plan", type="secondary", use_container_width=True):
            st.rerun()  # This will trigger navigation to migration planning

    # Recent activity
    st.subheader("Recent Activity")
    st.info("No recent migration activity. Start by analyzing your cookbooks!")


def show_migration_planning():
    """Show migration planning interface."""
    st.header("Migration Planning")

    st.info("Migration planning interface coming soon!")

    st.markdown("""
    This interface will provide:

    - **Step-by-step migration wizard**
    - **Complexity assessment and effort estimation**
    - **Automated migration plan generation**
    - **Phase-by-phase rollout planning**
    - **Risk assessment and mitigation strategies**
    """)


def show_dependency_mapping():
    """Show dependency mapping visualization."""
    st.header("Dependency Mapping")

    st.info("Interactive dependency visualization coming soon!")

    st.markdown("""
    This interface will provide:

    - **Interactive dependency graphs**
    - **Cookbook relationship visualization**
    - **Circular dependency detection**
    - **Migration order recommendations**
    - **Impact analysis for changes**
    """)


def show_validation_reports():
    """Show validation reports interface."""
    st.header("Validation Reports")

    st.info("Validation reporting interface coming soon!")

    st.markdown("""
    This interface will provide:

    - **Conversion validation results**
    - **Syntax and semantic validation**
    - **Best practice compliance reports**
    - **Security assessment results**
    - **Performance benchmarking reports**
    """)


if __name__ == "__main__":
    main()
