"""
Visual Migration Planning Interface for SousChef.

A Streamlit-based web interface for Chef to Ansible migration planning,
assessment, and visualization.
"""

import contextlib
import logging
import sys
from pathlib import Path

import streamlit as st

# Configure logging to stdout for Docker visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,  # Override any existing configuration
)

logger = logging.getLogger(__name__)
logger.info("Starting SousChef UI application")

# Add the parent directory to the path so we can import souschef modules
app_path = Path(__file__).parent.parent
if str(app_path) not in sys.path:
    sys.path.insert(0, str(app_path))

# Import page modules
from souschef.ui.pages.ai_settings import show_ai_settings_page  # noqa: E402
from souschef.ui.pages.cookbook_analysis import (  # noqa: E402
    show_cookbook_analysis_page,
)

# Constants for repeated strings
NAV_MIGRATION_PLANNING = "Migration Planning"
NAV_DEPENDENCY_MAPPING = "Dependency Mapping"
NAV_VALIDATION_REPORTS = "Validation Reports"
MIME_TEXT_MARKDOWN = "text/markdown"
MIME_APPLICATION_JSON = "application/json"
SECTION_CIRCULAR_DEPENDENCIES = "Circular Dependencies"
NAV_COOKBOOK_ANALYSIS = "Cookbook Analysis"
NAV_AI_SETTINGS = "AI Settings"
BUTTON_ANALYSE_DEPENDENCIES = "Analyse Dependencies"
SECTION_COMMUNITY_COOKBOOKS = "Community Cookbooks"
SECTION_COMMUNITY_COOKBOOKS_HEADER = "Community Cookbooks:"
INPUT_METHOD_DIRECTORY_PATH = "Directory Path"
SCOPE_BEST_PRACTICES = "Best Practices"
ERROR_MSG_ENTER_PATH = "Please enter a path to validate."


def health_check():
    """Return simple health check endpoint for Docker."""
    return {"status": "healthy", "service": "souschef-ui"}


class ProgressTracker:
    """Track progress for long-running operations."""

    def __init__(self, total_steps=100, description="Processing..."):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()

    def update(self, step=None, description=None):
        """Update progress."""
        if step is not None:
            self.current_step = min(step, self.total_steps)
        else:
            self.current_step = min(self.current_step + 1, self.total_steps)

        if description:
            self.description = description

        progress = min(self.current_step / self.total_steps, 1.0)
        self.progress_bar.progress(progress)
        self.status_text.text(
            f"{self.description} ({self.current_step}/{self.total_steps})"
        )

    def complete(self, message="Completed!"):
        """Mark progress as complete."""
        self.progress_bar.progress(1.0)
        self.status_text.text(message)
        import time

        time.sleep(0.5)  # Brief pause to show completion

    def close(self):
        """Clean up progress indicators."""
        self.progress_bar.empty()
        self.status_text.empty()


def with_progress_tracking(
    operation_func, description="Processing...", total_steps=100
):
    """Add progress tracking to operations."""

    def wrapper(*args, **kwargs):
        tracker = ProgressTracker(total_steps, description)
        try:
            result = operation_func(tracker, *args, **kwargs)
            tracker.complete()
            return result
        except Exception as e:
            tracker.close()
            raise e
        finally:
            tracker.close()

    return wrapper


def _setup_sidebar_navigation():
    """Set up the sidebar navigation with buttons."""
    st.sidebar.title("Navigation")

    # Dashboard button
    if st.sidebar.button(
        "Dashboard",
        help="View migration overview and quick actions",
        width="stretch",
    ):
        st.session_state.current_page = "Dashboard"
        st.rerun()

    # Cookbook Analysis button
    if st.sidebar.button(
        NAV_COOKBOOK_ANALYSIS,
        help="Analyse Chef cookbooks and assess migration complexity",
        width="stretch",
    ):
        st.session_state.current_page = NAV_COOKBOOK_ANALYSIS
        st.rerun()

    # Dependency Mapping button
    if st.sidebar.button(
        NAV_DEPENDENCY_MAPPING,
        help="Visualise cookbook dependencies and migration order",
        width="stretch",
    ):
        st.session_state.current_page = NAV_DEPENDENCY_MAPPING
        st.rerun()

    # Migration Planning button
    if st.sidebar.button(
        NAV_MIGRATION_PLANNING,
        help="Plan your Chef to Ansible migration with detailed timelines",
        width="stretch",
    ):
        st.session_state.current_page = NAV_MIGRATION_PLANNING
        st.rerun()

    # Validation Reports button
    if st.sidebar.button(
        NAV_VALIDATION_REPORTS,
        help="Validate conversions and generate quality assurance reports",
        width="stretch",
    ):
        st.session_state.current_page = NAV_VALIDATION_REPORTS
        st.rerun()

    # AI Settings button
    if st.sidebar.button(
        NAV_AI_SETTINGS,
        help="Configure AI provider settings for intelligent conversions",
        width="stretch",
    ):
        st.session_state.current_page = NAV_AI_SETTINGS
        st.rerun()


def main():
    """Run the main Streamlit application."""
    st.set_page_config(
        page_title="SousChef - Chef to Ansible Migration",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Hide Streamlit's default header elements and sidebar navigation
    st.markdown(
        """
    <style>
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stSidebarNavLink"] {display: none;}
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Set up sidebar navigation
    _setup_sidebar_navigation()

    # Get current page from session state, default to Dashboard
    page = st.session_state.get("current_page", "Dashboard")

    # Main content area
    if page == "Dashboard":
        show_dashboard()
    elif page == NAV_COOKBOOK_ANALYSIS:
        show_cookbook_analysis_page()
    elif page == NAV_AI_SETTINGS:
        show_ai_settings_page()
    elif page == NAV_MIGRATION_PLANNING:
        show_migration_planning()
    elif page == NAV_DEPENDENCY_MAPPING:
        show_dependency_mapping()
    elif page == NAV_VALIDATION_REPORTS:
        show_validation_reports()


def _calculate_dashboard_metrics():
    """Calculate and return dashboard metrics."""
    cookbooks_analysed = 0
    complexity_counts = {"High": 0, "Medium": 0, "Low": 0}
    successful_analyses = 0

    if "analysis_results" in st.session_state and st.session_state.analysis_results:
        results = st.session_state.analysis_results
        cookbooks_analysed = len(results)
        successful_analyses = len([r for r in results if r.get("status") == "Analysed"])

        for r in results:
            comp = r.get("complexity", "Unknown")
            if comp in complexity_counts:
                complexity_counts[comp] += 1

    # Determine overall complexity
    overall_complexity = "Unknown"
    if cookbooks_analysed > 0:
        if complexity_counts["High"] > 0:
            overall_complexity = "High"
        elif complexity_counts["Medium"] > 0:
            overall_complexity = "Medium"
        elif complexity_counts["Low"] > 0:
            overall_complexity = "Low"

    conversion_rate = 0
    if cookbooks_analysed > 0:
        conversion_rate = int((successful_analyses / cookbooks_analysed) * 100)

    return cookbooks_analysed, overall_complexity, conversion_rate, successful_analyses


def _display_dashboard_metrics(
    cookbooks_analysed, overall_complexity, conversion_rate, successful_analyses
):
    """Display the dashboard metrics."""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Cookbooks Analysed",
            str(cookbooks_analysed),
            f"{cookbooks_analysed} processed"
            if cookbooks_analysed > 0
            else "Ready to analyse",
        )
        st.caption("Total cookbooks processed")

    with col2:
        st.metric(
            "Migration Complexity",
            overall_complexity,
            "Based on analysis"
            if overall_complexity != "Unknown"
            else "Assessment needed",
        )
        st.caption("Overall migration effort")

    with col3:
        st.metric(
            "Success Rate",
            f"{conversion_rate}%",
            f"{successful_analyses} successful"
            if cookbooks_analysed > 0
            else "Start migration",
        )
        st.caption("Successful analyses")


def _display_quick_upload_section():
    """Display the quick upload section."""
    st.subheader("Quick Start")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Upload Cookbook Archive",
            type=["zip", "tar.gz", "tgz", "tar"],
            help="Upload a ZIP or TAR archive containing your Chef "
            "cookbooks for quick analysis",
            key="dashboard_upload",
        )

        if uploaded_file:
            # Store the uploaded file in session state for persistence across pages
            st.session_state.uploaded_file_data = uploaded_file.getvalue()
            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.uploaded_file_type = uploaded_file.type

            st.success(f"File {uploaded_file.name} uploaded successfully!")
            st.info(
                "Navigate to Cookbook Analysis to process this file, "
                "or upload another file to replace it."
            )

    with col2:
        st.markdown("**Or choose your workflow:**")

        # Quick actions
        if st.button("Analyse Cookbooks", type="primary", width="stretch"):
            st.session_state.current_page = "Cookbook Analysis"
            st.rerun()

        if st.button("Generate Migration Plan", width="stretch"):
            st.session_state.current_page = NAV_MIGRATION_PLANNING
            st.rerun()

        if st.button(BUTTON_ANALYSE_DEPENDENCIES, width="stretch"):
            st.session_state.current_page = NAV_DEPENDENCY_MAPPING
            st.rerun()


def _display_recent_activity():
    """Display the recent activity section."""
    st.subheader("Recent Activity")
    st.info(
        "No recent migration activity. Start by uploading cookbooks "
        "above or using the Cookbook Analysis page!"
    )

    # Getting started guide
    with st.expander("How to Get Started"):
        st.markdown("""
        **New to SousChef? Here's how to begin:**

        1. **Upload Cookbooks**: Use the uploader above or go to Cookbook Analysis
        2. **Analyse Complexity**: Get detailed migration assessments
        3. **Plan Migration**: Generate timelines and resource requirements
        4. **Convert to Ansible**: Download converted playbooks

        **Supported Formats:**
        - ZIP archives (.zip)
        - TAR archives (.tar, .tar.gz, .tgz)
        - Directory paths (in Cookbook Analysis)

        **Expected Structure:**
        ```
        your-cookbooks/
        ├── nginx/
        │   ├── metadata.rb
        │   ├── recipes/
        │   └── attributes/
        └── apache2/
            └── metadata.rb
        ```
        """)


def show_dashboard():
    """Show the main dashboard with migration overview."""
    st.header("Migration Dashboard")

    # Metrics calculation
    cookbooks_analysed, overall_complexity, conversion_rate, successful_analyses = (
        _calculate_dashboard_metrics()
    )

    # Display metrics
    _display_dashboard_metrics(
        cookbooks_analysed, overall_complexity, conversion_rate, successful_analyses
    )

    st.divider()

    # Quick upload section
    _display_quick_upload_section()

    # Recent activity
    _display_recent_activity()


def show_migration_planning():
    """Show migration planning interface."""
    st.header(NAV_MIGRATION_PLANNING)

    # Import assessment functions
    from souschef.assessment import generate_migration_plan

    # Migration planning wizard
    st.markdown("""
    Plan your Chef-to-Ansible migration with this interactive wizard.
    Get detailed timelines, effort estimates, and risk assessments.
    """)

    # Step 1: Cookbook Selection
    st.subheader("Step 1: Cookbook Selection")

    # Check for previously analyzed cookbooks
    uploaded_plan_context = None
    if (
        "analysis_cookbook_path" in st.session_state
        and st.session_state.analysis_cookbook_path
    ):
        uploaded_plan_context = st.session_state.analysis_cookbook_path
        st.info(f"Using analyzed cookbooks from: {uploaded_plan_context}")

    col1, col2 = st.columns([3, 1])

    with col1:
        # Default to analyzed path if available
        default_paths = uploaded_plan_context if uploaded_plan_context else ""

        cookbook_paths = st.text_area(
            "Cookbook Paths",
            value=default_paths,
            placeholder="/path/to/cookbooks/nginx,/path/to/cookbooks/apache2,/path/to/cookbooks/mysql",
            help="Enter comma-separated paths to your Chef cookbooks. If you uploaded "
            "an archive in the Analysis tab, that path is pre-filled.",
            height=100,
        )

    with col2:
        quick_select = st.selectbox(
            "Quick Examples",
            ["", "Single Cookbook", "Multiple Cookbooks", "Full Migration"],
            help="Load example cookbook configurations",
        )

    # Load example configurations
    if quick_select == "Single Cookbook":
        cookbook_paths = "/path/to/cookbooks/nginx"
    elif quick_select == "Multiple Cookbooks":
        cookbook_paths = (
            "/path/to/cookbooks/nginx,/path/to/cookbooks/apache2,"
            "/path/to/cookbooks/mysql"
        )
    elif quick_select == "Full Migration":
        cookbook_paths = (
            "/path/to/cookbooks/nginx,/path/to/cookbooks/apache2,"
            "/path/to/cookbooks/mysql,/path/to/cookbooks/postgresql,"
            "/path/to/cookbooks/redis"
        )

    # Step 2: Migration Strategy
    st.subheader("Step 2: Migration Strategy")

    col1, col2 = st.columns(2)

    with col1:
        migration_strategy = st.selectbox(
            "Migration Approach",
            ["phased", "big_bang", "parallel"],
            help="Choose your migration strategy",
            format_func=lambda x: {
                "phased": "Phased Migration (Recommended)",
                "big_bang": "Big Bang Migration",
                "parallel": "Parallel Migration",
            }.get(x, str(x)),
        )

    with col2:
        timeline_weeks = st.slider(
            "Timeline (Weeks)",
            min_value=4,
            max_value=24,
            value=12,
            help="Target timeline for migration completion",
        )

    # Strategy descriptions
    strategy_descriptions = {
        "phased": """
        **Phased Migration** - Migrate cookbooks in stages based on complexity
        and dependencies.
        - Lower risk with incremental progress
        - Easier rollback if issues occur
        - Longer timeline but more controlled
        - Recommended for most organizations
        """,
        "big_bang": """
        **Big Bang Migration** - Convert all cookbooks simultaneously and deploy
        at once.
        - Faster overall timeline
        - Higher risk and coordination required
        - Requires comprehensive testing
        - Best for small, well-understood environments
        """,
        "parallel": """
        **Parallel Migration** - Run Chef and Ansible side-by-side during transition.
        - Zero downtime possible
        - Most complex to manage
        - Requires dual maintenance
        - Best for critical production systems
        """,
    }

    with st.expander("Strategy Details"):
        st.markdown(strategy_descriptions.get(migration_strategy, ""))

    # Step 3: Generate Plan
    st.subheader("Step 3: Generate Migration Plan")

    if st.button("Generate Migration Plan", type="primary", width="stretch"):
        if not cookbook_paths.strip():
            st.error("Please enter cookbook paths to generate a migration plan.")
            return

        # Create progress tracker
        progress_tracker = ProgressTracker(
            total_steps=7, description="Generating migration plan..."
        )

        try:
            progress_tracker.update(1, "Scanning cookbook directories...")

            # Generate migration plan
            plan_result = generate_migration_plan(
                cookbook_paths.strip(), migration_strategy, timeline_weeks
            )

            progress_tracker.update(2, "Analyzing cookbook complexity...")
            progress_tracker.update(3, "Assessing migration risks...")
            progress_tracker.update(4, "Calculating resource requirements...")
            progress_tracker.update(5, "Generating timeline estimates...")
            progress_tracker.update(6, "Creating migration phases...")

            # Store results in session state for persistence
            st.session_state.migration_plan = plan_result
            st.session_state.cookbook_paths = cookbook_paths.strip()
            st.session_state.strategy = migration_strategy
            st.session_state.timeline = timeline_weeks

            progress_tracker.complete("Migration plan generated!")
            st.success("Migration plan generated successfully!")
            st.rerun()

        except Exception as e:
            progress_tracker.close()
            st.error(f"Error generating migration plan: {e}")
            return

    # Display results if available
    if "migration_plan" in st.session_state:
        display_migration_plan_results()


def _display_migration_summary_metrics(cookbook_paths, strategy, timeline):
    """Display migration overview summary metrics."""
    st.subheader("Migration Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        cookbook_count = len(cookbook_paths.split(","))
        st.metric("Cookbooks", cookbook_count)

    with col2:
        st.metric("Strategy", strategy.replace("_", " ").title())

    with col3:
        st.metric("Timeline", f"{timeline} weeks")

    with col4:
        st.metric("Status", "Plan Generated")


def _display_migration_plan_details(plan_result):
    """Display the detailed migration plan sections."""
    st.subheader("Migration Plan Details")

    # Split the plan into sections and display
    plan_sections = plan_result.split("\n## ")

    for section in plan_sections:
        if section.strip():
            if not section.startswith("#"):
                section = "## " + section

            # Clean up section headers
            section = section.replace("## Executive Summary", "### Executive Summary")
            section = section.replace("## Migration Phases", "### Migration Phases")
            section = section.replace("## Timeline", "### Timeline")
            section = section.replace("## Team Requirements", "### Team Requirements")

            st.markdown(section)


def _display_migration_action_buttons(cookbook_paths):
    """Display action buttons for next steps."""
    st.subheader("Next Steps")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊 Generate Detailed Report", width="stretch"):
            with st.spinner("Generating detailed migration report..."):
                try:
                    from souschef.assessment import generate_migration_report

                    report = generate_migration_report(
                        "assessment_complete", "executive", "yes"
                    )
                    st.session_state.detailed_report = report
                    st.success("Detailed report generated!")
                except Exception as e:
                    st.error(f"Error generating report: {e}")

    with col2:
        if st.button("🔍 Analyse Dependencies", width="stretch"):
            if len(cookbook_paths.split(",")) == 1:
                # Single cookbook dependency analysis
                cookbook_path = cookbook_paths.split(",")[0].strip()
                with st.spinner(f"Analysing dependencies for {cookbook_path}..."):
                    try:
                        from souschef.assessment import analyse_cookbook_dependencies

                        dep_analysis = analyse_cookbook_dependencies(cookbook_path)
                        st.session_state.dep_analysis = dep_analysis
                        st.success("Dependency analysis complete!")
                    except Exception as e:
                        st.error(f"Error analyzing dependencies: {e}")
            else:
                st.info(
                    "Dependency analysis is optimised for single cookbooks. "
                    "Select one cookbook path for detailed analysis."
                )

    with col3:
        if st.button("📥 Export Plan", width="stretch"):
            # Create downloadable plan
            plan_content = f"""# Chef to Ansible Migration Plan
Generated: {st.session_state.get("timestamp", "Unknown")}

## Configuration
- Cookbook Paths: {cookbook_paths}
- Strategy: {st.session_state.strategy}
- Timeline: {st.session_state.timeline} weeks

## Migration Plan
{st.session_state.migration_plan}
"""

            st.download_button(
                label="Download Migration Plan",
                data=plan_content,
                file_name="migration_plan.md",
                mime=MIME_TEXT_MARKDOWN,
                help="Download the complete migration plan as Markdown",
            )


def _display_additional_reports():
    """Display detailed report and dependency analysis if available."""
    # Display detailed report if generated
    if "detailed_report" in st.session_state:
        with st.expander("📊 Detailed Migration Report"):
            st.markdown(st.session_state.detailed_report)

    # Display dependency analysis if generated
    if "dep_analysis" in st.session_state:
        with st.expander("🔍 Dependency Analysis"):
            st.markdown(st.session_state.dep_analysis)


def display_migration_plan_results():
    """Display the generated migration plan results."""
    plan_result = st.session_state.migration_plan
    cookbook_paths = st.session_state.cookbook_paths
    strategy = st.session_state.strategy
    timeline = st.session_state.timeline

    _display_migration_summary_metrics(cookbook_paths, strategy, timeline)
    _display_migration_plan_details(plan_result)
    _display_migration_action_buttons(cookbook_paths)
    _display_additional_reports()


def show_dependency_mapping():
    """Show dependency mapping visualization."""
    st.header(NAV_DEPENDENCY_MAPPING)

    # Import assessment functions
    from souschef.assessment import analyse_cookbook_dependencies

    st.markdown("""
    Visualise and analyse cookbook dependencies to understand migration order
    and identify potential circular dependencies.
    """)

    # Input method selection
    input_method = st.radio(
        "Choose Input Method",
        ["Upload Archive", INPUT_METHOD_DIRECTORY_PATH],
        horizontal=True,
        help="Select how to provide cookbooks for dependency analysis",
        key="dep_input_method",
    )

    cookbook_path = None
    uploaded_file = None

    if input_method == INPUT_METHOD_DIRECTORY_PATH:
        cookbook_path = st.text_input(
            "Cookbook Directory Path",
            placeholder="/path/to/your/cookbooks",
            help="Enter the path to your cookbooks directory for dependency analysis",
        )
    else:
        uploaded_file = st.file_uploader(
            "Upload Cookbook Archive",
            type=["zip", "tar.gz", "tgz", "tar"],
            help="Upload a ZIP or TAR archive containing your Chef cookbooks",
            key="dep_archive_upload",
        )
        if uploaded_file:
            try:
                with st.spinner("Extracting archive..."):
                    # Import the extract function from cookbook_analysis
                    from souschef.ui.pages.cookbook_analysis import extract_archive

                    cookbook_path = str(extract_archive(uploaded_file))
                st.success("Archive extracted successfully")
            except Exception as e:
                st.error(f"Failed to extract archive: {e}")
                return

    # Analysis options
    col1, col2 = st.columns(2)

    with col1:
        dependency_depth = st.selectbox(
            "Analysis Depth",
            ["direct", "transitive", "full"],
            help="How deep to analyse dependencies",
            format_func=lambda x: {
                "direct": "Direct Dependencies Only",
                "transitive": "Include Transitive Dependencies",
                "full": "Full Dependency Graph",
            }.get(x, str(x)),
        )

    with col2:
        visualization_type = st.selectbox(
            "Visualization",
            ["text", "graph", "interactive"],
            help="How to display dependency information",
            format_func=lambda x: {
                "text": "Text Summary",
                "graph": "Static Graph View",
                "interactive": "Interactive Graph",
            }.get(x, str(x)),
        )

    # Analysis button
    if st.button(BUTTON_ANALYSE_DEPENDENCIES, type="primary", width="stretch"):
        if not cookbook_path or not cookbook_path.strip():
            st.error("Please enter a cookbook directory path.")
            return

        # Create progress tracker
        progress_tracker = ProgressTracker(
            total_steps=5, description="Analysing cookbook dependencies..."
        )

        try:
            progress_tracker.update(1, "Scanning cookbook directory...")

            # Analyse dependencies
            analysis_result = analyse_cookbook_dependencies(
                cookbook_path.strip(), dependency_depth
            )

            progress_tracker.update(2, "Parsing dependency relationships...")
            progress_tracker.update(3, "Detecting circular dependencies...")
            progress_tracker.update(4, "Generating migration recommendations...")

            # Store results
            st.session_state.dep_analysis_result = analysis_result
            st.session_state.dep_cookbook_path = cookbook_path.strip()
            st.session_state.dep_depth = dependency_depth
            st.session_state.dep_viz_type = visualization_type

            progress_tracker.complete("Dependency analysis completed!")
            st.success("Analysis completed successfully!")
            st.rerun()

        except Exception as e:
            progress_tracker.close()
            st.error(f"Error analyzing dependencies: {e}")
            return

    # Display results if available
    if "dep_analysis_result" in st.session_state:
        display_dependency_analysis_results()


def _setup_dependency_mapping_ui():
    """Set up the dependency mapping UI header and description."""
    st.header(NAV_DEPENDENCY_MAPPING)

    st.markdown("""
    Visualise and analyse cookbook dependencies to understand migration order
    and identify potential circular dependencies.
    """)


def _get_dependency_mapping_inputs():
    """Collect user inputs for dependency analysis."""
    # Cookbook path input
    cookbook_path = st.text_input(
        "Cookbook Directory Path",
        placeholder="/path/to/your/cookbooks",
        help="Enter the path to your cookbooks directory for dependency analysis",
    )

    # Analysis options
    col1, col2 = st.columns(2)

    with col1:
        dependency_depth = st.selectbox(
            "Analysis Depth",
            ["direct", "transitive", "full"],
            help="How deep to analyse dependencies",
            format_func=lambda x: {
                "direct": "Direct Dependencies Only",
                "transitive": "Include Transitive Dependencies",
                "full": "Full Dependency Graph",
            }.get(x, str(x)),
        )

    with col2:
        visualization_type = st.selectbox(
            "Visualization",
            ["text", "graph", "interactive"],
            help="How to display dependency information",
            format_func=lambda x: {
                "text": "Text Summary",
                "graph": "Static Graph View",
                "interactive": "Interactive Graph",
            }.get(x, str(x)),
        )

    return cookbook_path, dependency_depth, visualization_type


def _handle_dependency_analysis_execution(
    cookbook_path, dependency_depth, visualization_type
):
    """Handle the dependency analysis execution when button is clicked."""
    # Analysis button
    if st.button(BUTTON_ANALYSE_DEPENDENCIES, type="primary", width="stretch"):
        if not cookbook_path or not cookbook_path.strip():
            st.error("Please enter a cookbook directory path.")
            return

        _perform_dependency_analysis(
            cookbook_path.strip(), dependency_depth, visualization_type
        )


def _perform_dependency_analysis(cookbook_path, dependency_depth, visualization_type):
    """Perform the actual dependency analysis."""
    # Import assessment functions
    from souschef.assessment import analyse_cookbook_dependencies

    # Create progress tracker
    progress_tracker = ProgressTracker(
        total_steps=5, description="Analysing cookbook dependencies..."
    )

    try:
        progress_tracker.update(1, "Scanning cookbook directory...")

        # Analyse dependencies
        analysis_result = analyse_cookbook_dependencies(cookbook_path, dependency_depth)

        progress_tracker.update(2, "Parsing dependency relationships...")
        progress_tracker.update(3, "Detecting circular dependencies...")
        progress_tracker.update(4, "Generating migration recommendations...")

        # Store results
        st.session_state.dep_analysis_result = analysis_result
        st.session_state.dep_cookbook_path = cookbook_path
        st.session_state.dep_depth = dependency_depth
        st.session_state.dep_viz_type = visualization_type

        progress_tracker.complete("Dependency analysis completed!")
        st.success("Analysis completed successfully!")
        st.rerun()

    except Exception as e:
        progress_tracker.close()
        st.error(f"Error analyzing dependencies: {e}")


def _display_dependency_analysis_results_if_available():
    """Display dependency analysis results if they exist in session state."""
    # Display results if available
    if "dep_analysis_result" in st.session_state:
        display_dependency_analysis_results()


def _extract_dependency_relationships(lines):
    """Extract dependency relationships from analysis lines."""
    dependencies = {}
    current_section = None

    for line in lines:
        line = line.strip()
        if "Direct Dependencies:" in line:
            current_section = "direct"
        elif "Transitive Dependencies:" in line:
            current_section = "transitive"
        elif line.startswith("- ") and current_section == "direct":
            # Regular dependencies
            dep_text = line[2:].strip()
            if ":" in dep_text:
                parts = dep_text.split(":", 1)
                cookbook = parts[0].strip()
                deps = parts[1].strip()
                if deps and deps != "None":
                    dep_list = [d.strip() for d in deps.split(",")]
                    dependencies[cookbook] = dep_list

    return dependencies


def _extract_circular_and_community_deps(lines):
    """Extract circular dependencies and community cookbooks."""
    circular_deps: list[tuple[str, str]] = []
    community_cookbooks: list[str] = []
    current_section = None

    for line in lines:
        current_section = _update_current_section(line, current_section)
        if _is_list_item(line) and current_section:
            _process_list_item(
                line, current_section, circular_deps, community_cookbooks
            )

    return circular_deps, community_cookbooks


def _update_current_section(line, current_section):
    """Update the current section based on the line content."""
    line = line.strip()
    if "Circular Dependencies:" in line:
        return "circular"
    elif SECTION_COMMUNITY_COOKBOOKS_HEADER in line:
        return "community"
    return current_section


def _is_list_item(line):
    """Check if the line is a list item."""
    return line.strip().startswith("- ")


def _process_list_item(line, current_section, circular_deps, community_cookbooks):
    """Process a list item based on the current section."""
    if current_section == "circular":
        _process_circular_dependency_item(line, circular_deps)
    elif current_section == "community":
        _process_community_cookbook_item(line, community_cookbooks)


def _process_circular_dependency_item(line, circular_deps):
    """Process a circular dependency list item."""
    dep_text = line[2:].strip()
    if "->" in dep_text:
        parts = dep_text.split("->")
        if len(parts) >= 2:
            circular_deps.append((parts[0].strip(), parts[1].strip()))


def _process_community_cookbook_item(line, community_cookbooks):
    """Process a community cookbook list item."""
    cookbook = line[2:].strip()
    if cookbook:
        community_cookbooks.append(cookbook)


def _parse_dependency_analysis(analysis_result):
    """Parse dependency analysis result into structured data."""
    lines = analysis_result.split("\n")

    dependencies = _extract_dependency_relationships(lines)
    circular_deps, community_cookbooks = _extract_circular_and_community_deps(lines)

    return dependencies, circular_deps, community_cookbooks


def _create_networkx_graph(dependencies, circular_deps, community_cookbooks):
    """Create NetworkX graph from dependency data."""
    import networkx as nx

    graph: nx.DiGraph = nx.DiGraph()

    # Add nodes and edges
    for cookbook, deps in dependencies.items():
        graph.add_node(cookbook, node_type="cookbook")
        for dep in deps:
            graph.add_node(dep, node_type="dependency")
            graph.add_edge(cookbook, dep)

    # Add circular dependency edges with different styling
    for source, target in circular_deps:
        graph.add_edge(source, target, circular=True)

    # Mark community cookbooks
    for cookbook in community_cookbooks:
        if cookbook in graph.nodes:
            graph.nodes[cookbook]["community"] = True

    return graph


def _calculate_graph_positions(graph, layout_algorithm):
    """
    Calculate positions for graph nodes using the specified layout algorithm.

    Args:
        graph: NetworkX graph object
        layout_algorithm: String specifying the layout algorithm to use

    Returns:
        tuple: (positions_dict, algorithm_used)

    """
    # Choose layout algorithm based on graph size and user preference
    num_nodes = len(graph.nodes)
    if layout_algorithm == "auto":
        layout_algorithm = _choose_auto_layout_algorithm(num_nodes)

    # Calculate positions using selected layout algorithm
    pos = _calculate_positions_with_algorithm(graph, layout_algorithm)

    return pos, layout_algorithm


def _choose_auto_layout_algorithm(num_nodes):
    """Choose the best layout algorithm based on graph size."""
    if num_nodes <= 10:
        return "circular"
    elif num_nodes <= 50:
        return "spring"
    else:
        return "kamada_kawai"


def _calculate_positions_with_algorithm(graph, layout_algorithm):
    """Calculate node positions using the specified algorithm."""
    import networkx as nx

    try:
        if layout_algorithm == "spring":
            return nx.spring_layout(graph, k=2, iterations=50, seed=42)
        elif layout_algorithm == "circular":
            return nx.circular_layout(graph)
        elif layout_algorithm == "kamada_kawai":
            return nx.kamada_kawai_layout(graph)
        elif layout_algorithm == "shell":
            return _calculate_shell_layout_positions(graph)
        elif layout_algorithm == "random":
            return nx.random_layout(graph, seed=42)
        elif layout_algorithm == "spectral":
            return nx.spectral_layout(graph)
        elif layout_algorithm == "force_directed":
            return nx.spring_layout(graph, k=3, iterations=100, seed=42, scale=2)
        else:
            return nx.spring_layout(graph, k=2, iterations=50, seed=42)
    except Exception as e:
        # Fallback to spring layout if algorithm fails
        st.warning(
            f"Layout algorithm '{layout_algorithm}' failed, using spring layout: {e}"
        )
        return nx.spring_layout(graph, k=2, iterations=50, seed=42)


def _calculate_shell_layout_positions(graph):
    """Calculate shell layout positions for hierarchical organization."""
    import networkx as nx

    # Identify leaf nodes (no outgoing edges)
    leaf_nodes = [n for n in graph.nodes() if graph.out_degree(n) == 0]
    # Identify root nodes (no incoming edges)
    root_nodes = [n for n in graph.nodes() if graph.in_degree(n) == 0]
    # Middle nodes
    middle_nodes = [
        n for n in graph.nodes() if n not in leaf_nodes and n not in root_nodes
    ]

    shells = []
    if root_nodes:
        shells.append(root_nodes)
    if middle_nodes:
        shells.append(middle_nodes)
    if leaf_nodes:
        shells.append(leaf_nodes)

    if shells:
        return nx.shell_layout(graph, shells)
    else:
        return nx.spring_layout(graph, k=2, iterations=50, seed=42)


def _create_plotly_edge_traces(graph, pos):
    """Create edge traces for Plotly graph."""
    import plotly.graph_objects as go  # type: ignore[import-untyped]

    edge_traces = []

    # Regular edges
    edge_x = []
    edge_y = []
    for edge in graph.edges():
        if not graph.edges[edge].get("circular", False):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    if edge_x:
        edge_traces.append(
            go.Scatter(
                x=edge_x,
                y=edge_y,
                line={"width": 2, "color": "#888"},
                hoverinfo="none",
                mode="lines",
                name="Dependencies",
            )
        )

    # Circular dependency edges (red)
    circ_edge_x = []
    circ_edge_y = []
    for edge in graph.edges():
        if graph.edges[edge].get("circular", False):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            circ_edge_x.extend([x0, x1, None])
            circ_edge_y.extend([y0, y1, None])

    if circ_edge_x:
        edge_traces.append(
            go.Scatter(
                x=circ_edge_x,
                y=circ_edge_y,
                line={"width": 3, "color": "red"},
                hoverinfo="none",
                mode="lines",
                name=SECTION_CIRCULAR_DEPENDENCIES,
            )
        )

    return edge_traces


def _create_plotly_node_trace(graph, pos):
    """Create node trace for Plotly graph."""
    import plotly.graph_objects as go

    node_x = []
    node_y = []
    node_text = []
    node_colors = []
    node_sizes = []

    for node in graph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)

        # Dynamic node sizing based on connectivity
        degree = graph.degree(node)
        node_sizes.append(max(15, min(30, 15 + degree * 2)))

        # Color coding
        if graph.nodes[node].get("community", False):
            node_colors.append("lightgreen")  # Community cookbooks
        elif any(
            graph.edges[edge].get("circular", False)
            for edge in graph.in_edges(node)
            if edge[1] == node
        ):
            node_colors.append("red")  # Involved in circular deps
        elif graph.in_degree(node) > 0:
            node_colors.append("lightblue")  # Has dependencies
        else:
            node_colors.append("lightgray")  # Leaf dependencies

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        hoverinfo="text",
        text=node_text,
        textposition="top center",
        marker={
            "size": node_sizes,
            "color": node_colors,
            "line_width": 2,
            "line_color": "darkgray",
        },
        name="Cookbooks",
    )

    return node_trace


def _create_plotly_figure_layout(num_nodes, layout_algorithm):
    """Create Plotly figure layout."""
    import plotly.graph_objects as go

    layout: go.Layout = go.Layout(
        title=f"Cookbook Dependency Graph ({num_nodes} nodes, "
        f"{layout_algorithm} layout)",
        titlefont_size=16,
        showlegend=True,
        hovermode="closest",
        margin={"b": 20, "l": 5, "r": 5, "t": 40},
        xaxis={
            "showgrid": False,
            "zeroline": False,
            "showticklabels": False,
        },
        yaxis={
            "showgrid": False,
            "zeroline": False,
            "showticklabels": False,
        },
        plot_bgcolor="white",
    )

    return layout


def _create_interactive_plotly_graph(graph, pos, num_nodes, layout_algorithm):
    """Create interactive Plotly graph visualization."""
    import plotly.graph_objects as go

    edge_traces = _create_plotly_edge_traces(graph, pos)
    node_trace = _create_plotly_node_trace(graph, pos)
    layout = _create_plotly_figure_layout(num_nodes, layout_algorithm)

    # Create the figure
    fig = go.Figure(data=edge_traces + [node_trace], layout=layout)

    return fig


def _create_static_matplotlib_graph(graph, pos, num_nodes, layout_algorithm):
    """Create static matplotlib graph visualization."""
    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 8))

    # Draw regular edges
    regular_edges = [
        (u, v) for u, v, d in graph.edges(data=True) if not d.get("circular", False)
    ]
    if regular_edges:
        import networkx as nx

        nx.draw_networkx_edges(
            graph,
            pos,
            edgelist=regular_edges,
            edge_color="gray",
            arrows=True,
            arrowsize=20,
            width=2,
            alpha=0.7,
        )

    # Draw circular dependency edges
    circular_edges = [
        (u, v) for u, v, d in graph.edges(data=True) if d.get("circular", False)
    ]
    if circular_edges:
        import networkx as nx

        nx.draw_networkx_edges(
            graph,
            pos,
            edgelist=circular_edges,
            edge_color="red",
            arrows=True,
            arrowsize=25,
            width=3,
            alpha=0.9,
            style="dashed",
        )

    # Color nodes
    node_colors = []
    for node in graph.nodes():
        if graph.nodes[node].get("community", False):
            node_colors.append("lightgreen")  # Community cookbooks
        elif any(
            graph.edges[edge].get("circular", False)
            for edge in graph.in_edges(node)
            if edge[1] == node
        ):
            node_colors.append("red")  # Involved in circular deps
        elif graph.in_degree(node) > 0:
            node_colors.append("lightblue")  # Has dependencies
        else:
            node_colors.append("lightgray")  # Leaf dependencies

    # Draw nodes with size based on connectivity
    node_sizes = [
        max(300, min(1200, 300 + graph.degree(node) * 100)) for node in graph.nodes()
    ]

    # Draw nodes
    import networkx as nx

    nx.draw_networkx_nodes(
        graph,
        pos,
        node_color=node_colors,
        node_size=node_sizes,
        alpha=0.8,
        linewidths=2,
        edgecolors="darkgray",
    )

    # Draw labels
    nx.draw_networkx_labels(graph, pos, font_size=8, font_weight="bold")

    plt.title(
        f"Cookbook Dependency Graph ({num_nodes} nodes, {layout_algorithm} layout)",
        fontsize=16,
        pad=20,
    )
    plt.axis("off")
    plt.tight_layout()

    return plt.gcf()


def create_dependency_graph(
    analysis_result, viz_type, layout_algorithm="auto", filters=None
):
    """
    Create a dependency graph visualization with optional filtering.

    Args:
        analysis_result: Text analysis result from dependency analysis
        viz_type: Visualization type ("interactive" or "static")
        layout_algorithm: Layout algorithm to use
        filters: Dictionary of filter options

    Returns:
        Plotly figure for interactive graphs, matplotlib figure for static graphs

    """
    try:
        # Parse the analysis result to extract dependencies
        dependencies, circular_deps, community_cookbooks = _parse_dependency_analysis(
            analysis_result
        )

        # Create NetworkX graph
        graph = _create_networkx_graph(dependencies, circular_deps, community_cookbooks)

        # Apply filters if provided
        if filters:
            graph = _apply_graph_filters(graph, filters)

        if len(graph.nodes) == 0:
            return None

        # Calculate positions
        pos, final_layout = _calculate_graph_positions(graph, layout_algorithm)

        if viz_type == "interactive":
            return _create_interactive_plotly_graph(
                graph, pos, len(graph.nodes), final_layout
            )
        else:
            return _create_static_matplotlib_graph(
                graph, pos, len(graph.nodes), final_layout
            )

    except Exception as e:
        st.error(f"Error creating dependency graph: {e}")
        return None


def _apply_graph_filters(graph, filters):
    """Apply filters to the NetworkX graph."""
    filtered_graph = graph.copy()

    # Apply each filter type
    filtered_graph = _filter_circular_dependencies_only(filtered_graph, filters)
    filtered_graph = _filter_community_cookbooks_only(filtered_graph, filters)
    filtered_graph = _filter_minimum_connections(filtered_graph, filters)

    return filtered_graph


def _filter_circular_dependencies_only(graph, filters):
    """Filter graph to show only nodes involved in circular dependencies."""
    if not filters.get("circular_only", False):
        return graph

    # Find nodes involved in circular dependencies
    circular_nodes = set()
    for source, target in filters.get("circular_deps", []):
        circular_nodes.add(source)
        circular_nodes.add(target)

    # Remove nodes not involved in circular dependencies
    nodes_to_remove = [n for n in graph.nodes() if n not in circular_nodes]
    graph.remove_nodes_from(nodes_to_remove)

    return graph


def _filter_community_cookbooks_only(graph, filters):
    """Filter graph to show only community cookbooks and their dependencies."""
    if not filters.get("community_only", False):
        return graph

    community_nodes = set()
    for node in graph.nodes():
        if graph.nodes[node].get("community", False):
            community_nodes.add(node)
            # Also include dependencies of community cookbooks
            for successor in graph.successors(node):
                community_nodes.add(successor)

    # Remove nodes not related to community cookbooks
    nodes_to_remove = [n for n in graph.nodes() if n not in community_nodes]
    graph.remove_nodes_from(nodes_to_remove)

    return graph


def _filter_minimum_connections(graph, filters):
    """Filter graph to show only nodes with minimum connection count."""
    min_connections = filters.get("min_connections", 0)
    if min_connections <= 0:
        return graph

    nodes_to_remove = []
    for node in graph.nodes():
        degree = graph.degree(node)
        if degree < min_connections:
            nodes_to_remove.append(node)
    graph.remove_nodes_from(nodes_to_remove)

    return graph


def _parse_dependency_metrics_from_result(analysis_result):
    """Parse dependency analysis result to extract key metrics."""
    lines = analysis_result.split("\n")

    # Extract key metrics from the analysis
    direct_deps = 0
    transitive_deps = 0
    circular_deps = 0
    community_cookbooks = 0

    for line in lines:
        if "Direct Dependencies:" in line:
            with contextlib.suppress(ValueError):
                direct_deps = int(line.split(":")[1].strip())
        elif "Transitive Dependencies:" in line:
            with contextlib.suppress(ValueError):
                transitive_deps = int(line.split(":")[1].strip())
        elif "Circular Dependencies:" in line:
            with contextlib.suppress(ValueError):
                circular_deps = int(line.split(":")[1].strip())
        elif "Community Cookbooks:" in line:
            with contextlib.suppress(ValueError):
                community_cookbooks = int(line.split(":")[1].strip())

    return direct_deps, transitive_deps, circular_deps, community_cookbooks


def _display_dependency_summary_metrics(
    direct_deps, transitive_deps, circular_deps, community_cookbooks
):
    """Display dependency analysis summary metrics."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Direct Dependencies", direct_deps)

    with col2:
        st.metric("Transitive Dependencies", transitive_deps)

    with col3:
        st.metric(
            SECTION_CIRCULAR_DEPENDENCIES,
            circular_deps,
            delta="⚠️ Check" if circular_deps > 0 else "✅ OK",
        )

    with col4:
        st.metric(SECTION_COMMUNITY_COOKBOOKS, community_cookbooks)


def _calculate_migration_impact(dependencies, circular_deps, community_cookbooks):
    """Calculate migration impact analysis based on dependency structure."""
    from typing import Any

    impact: dict[str, Any] = {
        "risk_score": 0.0,
        "timeline_impact_weeks": 0,
        "complexity_level": "Low",
        "parallel_streams": 1,
        "critical_path": [],
        "bottlenecks": [],
        "recommendations": [],
    }

    # Calculate risk score based on various factors
    risk_factors = {
        "circular_deps": len(circular_deps)
        * 2.0,  # Each circular dep adds significant risk
        "total_deps": len(dependencies) * 0.1,  # More dependencies = higher complexity
        "community_cookbooks": len(community_cookbooks)
        * 0.5,  # Community cookbooks need evaluation
        "max_chain_length": _calculate_max_dependency_chain(dependencies)
        * 0.3,  # Long chains are risky
    }

    impact["risk_score"] = min(10.0, sum(risk_factors.values()))

    # Determine complexity level
    if impact["risk_score"] > 7:
        impact["complexity_level"] = "High"
        impact["timeline_impact_weeks"] = 4
    elif impact["risk_score"] > 4:
        impact["complexity_level"] = "Medium"
        impact["timeline_impact_weeks"] = 2
    else:
        impact["complexity_level"] = "Low"
        impact["timeline_impact_weeks"] = 0

    # Calculate parallel migration streams
    if len(dependencies) > 20:
        impact["parallel_streams"] = 3
    elif len(dependencies) > 10:
        impact["parallel_streams"] = 2
    else:
        impact["parallel_streams"] = 1

    # Identify critical path (longest dependency chain)
    impact["critical_path"] = _find_critical_path(dependencies)

    # Identify bottlenecks (highly depended-upon cookbooks)
    impact["bottlenecks"] = _identify_bottlenecks(dependencies)

    # Generate recommendations
    impact["recommendations"] = _generate_impact_recommendations(
        impact, circular_deps, community_cookbooks
    )

    return impact


def _calculate_max_dependency_chain(dependencies):
    """Calculate the maximum dependency chain length."""
    max_length = 0

    def get_chain_length(cookbook, visited=None):
        if visited is None:
            visited = set()

        if cookbook in visited:
            return 0  # Circular dependency detected

        visited.add(cookbook)
        deps = dependencies.get(cookbook, [])

        if not deps:
            return 1

        max_child_length = 0
        for dep in deps:
            child_length = get_chain_length(dep, visited.copy())
            max_child_length = max(max_child_length, child_length)

        return 1 + max_child_length

    for cookbook in dependencies:
        length = get_chain_length(cookbook)
        max_length = max(max_length, length)

    return max_length


def _find_critical_path(dependencies):
    """Find the critical path (longest dependency chain)."""
    longest_chain: list[str] = []

    def find_longest_chain(cookbook, visited=None):
        if visited is None:
            visited = set()

        if cookbook in visited:
            return []  # Circular dependency

        visited.add(cookbook)
        deps = dependencies.get(cookbook, [])

        if not deps:
            return [cookbook]

        longest_child_chain: list[str] = []
        for dep in deps:
            child_chain = find_longest_chain(dep, visited.copy())
            if len(child_chain) > len(longest_child_chain):
                longest_child_chain = child_chain

        return [cookbook] + longest_child_chain

    for cookbook in dependencies:
        chain = find_longest_chain(cookbook)
        if len(chain) > len(longest_chain):
            longest_chain = chain

    return longest_chain


def _identify_bottlenecks(dependencies: dict[str, list[str]]):
    """Identify bottleneck cookbooks (highly depended upon)."""
    # Count how many times each cookbook is depended upon
    dependency_counts: dict[str, int] = {}

    for deps in dependencies.values():
        for dep in deps:
            dependency_counts[dep] = dependency_counts.get(dep, 0) + 1

    # Find cookbooks with high dependency counts
    bottlenecks = []
    max_count: int = max(dependency_counts.values()) if dependency_counts else 0

    for cookbook, count in dependency_counts.items():
        if count >= 5:
            risk_level = "High"
        elif count >= 3:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        if count >= 3 or (max_count > 1 and count == max_count):
            bottlenecks.append(
                {
                    "cookbook": cookbook,
                    "dependent_count": count,
                    "risk_level": risk_level,
                }
            )

    return sorted(bottlenecks, key=lambda x: x["dependent_count"], reverse=True)


def _generate_impact_recommendations(impact, circular_deps, community_cookbooks):
    """Generate recommendations based on impact analysis."""
    recommendations = []

    if circular_deps:
        recommendations.append(
            {
                "priority": "Critical",
                "action": (
                    f"Resolve {len(circular_deps)} circular dependencies "
                    "before migration"
                ),
                "impact": "Prevents successful migration",
            }
        )

    if impact["parallel_streams"] > 1:
        recommendations.append(
            {
                "priority": "High",
                "action": (
                    f"Plan {impact['parallel_streams']} parallel migration streams"
                ),
                "impact": (
                    f"Reduces timeline by ~{impact['parallel_streams'] * 2} weeks"
                ),
            }
        )

    if community_cookbooks:
        recommendations.append(
            {
                "priority": "Medium",
                "action": (
                    f"Evaluate {len(community_cookbooks)} community cookbooks "
                    "for Ansible Galaxy alternatives"
                ),
                "impact": "Reduces custom development effort",
            }
        )

    if impact["bottlenecks"]:
        bottleneck_names = [b["cookbook"] for b in impact["bottlenecks"][:3]]
        recommendations.append(
            {
                "priority": "Medium",
                "action": (
                    f"Migrate bottleneck cookbooks first: {', '.join(bottleneck_names)}"
                ),
                "impact": "Unblocks dependent cookbook migrations",
            }
        )

    if impact["timeline_impact_weeks"] > 0:
        recommendations.append(
            {
                "priority": "Low",
                "action": (
                    f"Allocate additional {impact['timeline_impact_weeks']} "
                    "weeks for complexity"
                ),
                "impact": "Ensures successful migration completion",
            }
        )

    return recommendations


def _display_detailed_impact_analysis(
    impact_analysis, dependencies, circular_deps, community_cookbooks
):
    """Display detailed impact analysis breakdown."""
    _display_risk_assessment_breakdown(dependencies, circular_deps, community_cookbooks)
    _display_critical_path_analysis(impact_analysis)
    _display_migration_bottlenecks(impact_analysis)
    _display_strategic_recommendations(impact_analysis)


def _display_risk_assessment_breakdown(
    dependencies, circular_deps, community_cookbooks
):
    """Display risk assessment breakdown."""
    st.markdown("### Risk Assessment Breakdown")

    # Risk factors
    risk_factors = {
        "Circular Dependencies": len(circular_deps) * 2.0,
        "Total Dependencies": len(dependencies) * 0.1,
        "Community Cookbooks": len(community_cookbooks) * 0.5,
        "Dependency Chain Length": _calculate_max_dependency_chain(dependencies) * 0.3,
    }

    for factor, score in risk_factors.items():
        if score > 0:
            st.write(f"• **{factor}**: {score:.1f} points")


def _display_critical_path_analysis(impact_analysis):
    """Display critical path analysis."""
    st.markdown("### Critical Path Analysis")
    if impact_analysis["critical_path"]:
        st.write("**Longest dependency chain:**")
        st.code(" → ".join(impact_analysis["critical_path"]), language="text")
    else:
        st.write("No dependency chains identified.")


def _display_migration_bottlenecks(impact_analysis):
    """Display migration bottlenecks."""
    st.markdown("### Migration Bottlenecks")
    if impact_analysis["bottlenecks"]:
        for bottleneck in impact_analysis["bottlenecks"]:
            risk_level = bottleneck["risk_level"]
            if risk_level == "High":
                risk_icon = "🔴"
            elif risk_level == "Medium":
                risk_icon = "🟡"
            else:
                risk_icon = "🟢"
            st.write(
                f"• {risk_icon} **{bottleneck['cookbook']}**: "
                f"{bottleneck['dependent_count']} dependents "
                f"({risk_level} risk)"
            )
    else:
        st.write("✅ No significant bottlenecks identified.")


def _display_strategic_recommendations(impact_analysis):
    """Display strategic recommendations."""
    st.markdown("### Strategic Recommendations")
    for rec in impact_analysis["recommendations"]:
        priority = rec["priority"]
        if priority == "Critical":
            priority_icon = "🔴"
        elif priority == "High":
            priority_icon = "🟡"
        else:
            priority_icon = "🟢"
        st.write(f"• {priority_icon} **{priority}**: {rec['action']}")
        st.write(f"  *Impact*: {rec['impact']}")


def _handle_graph_caching():
    """Handle graph caching controls and cleanup."""
    st.subheader("💾 Graph Cache Management")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        # Toggle caching on/off
        cache_enabled = st.checkbox(
            "Enable Graph Caching",
            value=st.session_state.get("graph_cache_enabled", True),
            help="Cache graph visualizations to improve performance for repeated views",
        )
        st.session_state.graph_cache_enabled = cache_enabled

    with col2:
        # Clear cache button
        if st.button("🗑️ Clear Cache", help="Clear all cached graph data"):
            # Find and remove all graph cache keys
            cache_keys = [key for key in st.session_state if key.startswith("graph_")]
            for key in cache_keys:
                del st.session_state[key]
            st.success(f"✅ Cleared {len(cache_keys)} cached graphs")
            st.rerun()

    with col3:
        # Cache statistics
        cache_keys = [key for key in st.session_state if key.startswith("graph_")]
        cache_count = len(cache_keys)

        if cache_count > 0:
            # Estimate memory usage (rough approximation)
            estimated_memory = cache_count * 50  # Rough estimate: 50KB per cached graph
            st.metric(
                "Cached Graphs",
                f"{cache_count} items",
                f"~{estimated_memory}KB estimated",
            )
        else:
            st.info("📭 No graphs currently cached")

    # Cache status indicator
    if cache_enabled:
        st.success(
            "✅ Graph caching is enabled - visualizations will be "
            "cached for faster loading"
        )
    else:
        st.warning(
            "⚠️ Graph caching is disabled - each visualization will be recalculated"
        )


def _display_dependency_graph_visualization(
    analysis_result,
    viz_type,
    selected_layout,
    show_circular_only,
    show_community_only,
    min_connections,
):
    """Display the dependency graph visualization section with filtering."""
    try:
        # Parse dependencies for filtering
        _, circular_deps, _ = _parse_dependency_analysis(analysis_result)

        # Prepare filters
        filters = {
            "circular_only": show_circular_only,
            "community_only": show_community_only,
            "min_connections": min_connections,
            "circular_deps": circular_deps,
        }

        # Try to get cached graph data
        graph_data = _get_cached_graph_data(
            analysis_result, viz_type, selected_layout, filters
        )

        if graph_data is None:
            # Create dependency graph with filters
            graph_data = create_dependency_graph(
                analysis_result, viz_type, selected_layout, filters
            )
            # Cache the result
            _cache_graph_data(
                analysis_result, viz_type, selected_layout, filters, graph_data
            )

        if graph_data:
            _display_graph_with_export_options(graph_data, viz_type)
        else:
            st.info(
                "No dependency relationships found to visualise after applying filters."
            )

    except Exception as e:
        _handle_graph_visualization_error(e, analysis_result)


def _get_cached_graph_data(analysis_result, viz_type, selected_layout, filters):
    """Get cached graph data if available."""
    cache_key = (
        f"graph_{hash(analysis_result)}_{viz_type}_{selected_layout}_{str(filters)}"
    )

    if cache_key in st.session_state and st.session_state.get(
        "graph_cache_enabled", True
    ):
        graph_data = st.session_state[cache_key]
        st.info("📋 Using cached graph data")
        return graph_data

    return None


def _cache_graph_data(analysis_result, viz_type, selected_layout, filters, graph_data):
    """Cache graph data if caching is enabled."""
    if graph_data is not None and st.session_state.get("graph_cache_enabled", True):
        cache_key = (
            f"graph_{hash(analysis_result)}_{viz_type}_{selected_layout}_{str(filters)}"
        )
        st.session_state[cache_key] = graph_data


def _display_graph_with_export_options(graph_data, viz_type):
    """Display graph and provide export options."""
    if viz_type == "interactive":
        # Interactive Plotly graph
        st.plotly_chart(graph_data, width="stretch")

        # Export options for interactive graph
        st.subheader("Export Graph")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # Export as HTML
            html_content = graph_data.to_html(full_html=False, include_plotlyjs="cdn")
            st.download_button(
                label="🌐 HTML",
                data=html_content,
                file_name="dependency_graph.html",
                mime="text/html",
                help="Download interactive graph as HTML file",
            )

        with col2:
            # Export as JSON
            json_data = graph_data.to_json()
            st.download_button(
                label="📊 JSON",
                data=json_data,
                file_name="dependency_graph.json",
                mime=MIME_APPLICATION_JSON,
                help="Download graph data as JSON",
            )

        with col3:
            # Export as PNG (requires kaleido)
            try:
                import plotly.io as pio  # type: ignore[import-untyped]

                png_data = pio.to_image(graph_data, format="png", scale=2)
                st.download_button(
                    label="🖼️ PNG (High-res)",
                    data=png_data,
                    file_name="dependency_graph.png",
                    mime="image/png",
                    help="Download graph as high-resolution PNG",
                )
            except ImportError:
                st.info("PNG export requires additional dependencies")

        with col4:
            # Export as PDF
            try:
                import plotly.io as pio

                pdf_data = pio.to_image(graph_data, format="pdf")
                st.download_button(
                    label="📄 PDF",
                    data=pdf_data,
                    file_name="dependency_graph.pdf",
                    mime="application/pdf",
                    help="Download graph as PDF document",
                )
            except ImportError:
                st.info("PDF export requires additional dependencies")

    else:
        # Static matplotlib graph
        st.pyplot(graph_data)

        # Export options for static graph
        st.subheader("Export Graph")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # Export as PNG
            import io

            buf = io.BytesIO()
            graph_data.savefig(buf, format="png", dpi=300, bbox_inches="tight")
            buf.seek(0)
            st.download_button(
                label="🖼️ PNG (High-res)",
                data=buf.getvalue(),
                file_name="dependency_graph.png",
                mime="image/png",
                help="Download graph as high-resolution PNG",
            )

        with col2:
            # Export as SVG
            buf_svg = io.BytesIO()
            graph_data.savefig(buf_svg, format="svg", bbox_inches="tight")
            buf_svg.seek(0)
            st.download_button(
                label="📈 SVG",
                data=buf_svg.getvalue(),
                file_name="dependency_graph.svg",
                mime="image/svg+xml",
                help="Download graph as scalable SVG",
            )

        with col3:
            # Export as PDF
            buf_pdf = io.BytesIO()
            graph_data.savefig(buf_pdf, format="pdf", bbox_inches="tight")
            buf_pdf.seek(0)
            st.download_button(
                label="📄 PDF",
                data=buf_pdf.getvalue(),
                file_name="dependency_graph.pdf",
                mime="application/pdf",
                help="Download graph as PDF document",
            )

        with col4:
            # Export as EPS
            buf_eps = io.BytesIO()
            graph_data.savefig(buf_eps, format="eps", bbox_inches="tight")
            buf_eps.seek(0)
            st.download_button(
                label="🔧 EPS",
                data=buf_eps.getvalue(),
                file_name="dependency_graph.eps",
                mime="application/postscript",
                help="Download graph as EPS vector format",
            )


def _handle_graph_visualization_error(error, analysis_result):
    """Handle graph visualization errors with fallback display."""
    st.error("❌ **Graph Visualization Error**")
    with st.expander("Error Details"):
        st.code(str(error), language="text")
        st.markdown("""
        **Possible causes:**
        - Invalid dependency analysis data
        - Graph layout algorithm failed for this data
        - Memory constraints for large graphs

        **Suggestions:**
        - Try a different layout algorithm
        - Reduce the scope of your dependency analysis
        - Check the dependency analysis output for issues
        """)

    # Fallback: show text summary
    st.info("📄 Showing text-based dependency summary instead:")
    st.text_area(
        "Dependency Analysis Text",
        analysis_result,
        height=300,
        help="Raw dependency analysis output",
    )


def _display_dependency_analysis_sections(analysis_result):
    """Display dependency analysis results in expandable sections."""
    # Split analysis into sections
    sections = analysis_result.split("\n## ")

    for section in sections:
        if section.strip():
            if not section.startswith("#"):
                section = "## " + section

            # Add expanders for different sections
            if "Migration Order Recommendations" in section:
                with st.expander("📋 Migration Order Recommendations"):
                    st.markdown(
                        section.replace("## Migration Order Recommendations", "")
                    )
            elif "Dependency Graph" in section:
                with st.expander("🔗 Dependency Graph"):
                    st.markdown(section.replace("## Dependency Graph", ""))
                with st.expander(f"⚠️ {SECTION_CIRCULAR_DEPENDENCIES}"):
                    st.markdown(
                        section.replace(f"## {SECTION_CIRCULAR_DEPENDENCIES}", "")
                    )
                with st.expander(f"🌐 {SECTION_COMMUNITY_COOKBOOKS}"):
                    st.markdown(
                        section.replace(f"## {SECTION_COMMUNITY_COOKBOOKS}", "")
                    )
            elif "Migration Impact Analysis" in section:
                with st.expander("📊 Migration Impact Analysis"):
                    st.markdown(section.replace("## Migration Impact Analysis", ""))
            else:
                st.markdown(section)


def _display_migration_recommendations(circular_deps, community_cookbooks, direct_deps):
    """Display migration recommendations based on analysis results."""
    st.subheader("Migration Recommendations")

    if circular_deps > 0:
        st.error(
            "⚠️ **Critical Issue**: Circular dependencies detected. "
            "Resolve before migration."
        )
        st.markdown("""
        **Resolution Steps:**
        1. Review the circular dependency pairs
        2. Refactor cookbooks to break circular references
        3. Consider combining tightly coupled cookbooks
        4. Update dependency declarations
        """)

    if community_cookbooks > 0:
        st.success(
            f"✅ **Good News**: {community_cookbooks} community cookbooks identified."
        )
        st.markdown("""
        **Recommendations:**
        - Replace with Ansible Galaxy roles where possible
        - Review community cookbook versions and security
        - Consider forking and maintaining custom versions if needed
        """)

    if direct_deps > 10:
        st.warning("⚠️ **Complex Dependencies**: High dependency count detected.")
        st.markdown("""
        **Consider:**
        - Breaking down monolithic cookbooks
        - Implementing proper dependency injection
        - Planning migration in smaller phases
        """)


def _display_dependency_export_options(
    analysis_result,
    cookbook_path,
    depth,
    direct_deps,
    transitive_deps,
    circular_deps,
    community_cookbooks,
):
    """Display export options for dependency analysis."""
    st.subheader("Export Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="📥 Download Full Analysis",
            data=analysis_result,
            file_name="dependency_analysis.md",
            mime=MIME_TEXT_MARKDOWN,
            help="Download complete dependency analysis",
        )

    with col2:
        # Create a simplified JSON export
        analysis_json = {
            "cookbook_path": cookbook_path,
            "analysis_depth": depth,
            "metrics": {
                "direct_dependencies": direct_deps,
                "transitive_dependencies": transitive_deps,
                "circular_dependencies": circular_deps,
                "community_cookbooks": community_cookbooks,
            },
            "full_analysis": analysis_result,
        }

        import json

        st.download_button(
            label="📊 Download JSON Summary",
            data=json.dumps(analysis_json, indent=2),
            file_name="dependency_analysis.json",
            mime=MIME_APPLICATION_JSON,
            help="Download analysis summary as JSON",
        )


def _display_dependency_analysis_summary(analysis_result, cookbook_path, depth):
    """Display dependency analysis summary section."""
    # Summary metrics
    st.subheader("Dependency Analysis Summary")

    # Parse metrics from analysis result
    direct_deps, transitive_deps, circular_deps, community_cookbooks = (
        _parse_dependency_metrics_from_result(analysis_result)
    )

    # Display summary metrics
    _display_dependency_summary_metrics(
        direct_deps, transitive_deps, circular_deps, community_cookbooks
    )

    # Analysis depth indicator
    analysis_msg = f"Analysis performed with **{depth}** depth on: `{cookbook_path}`"
    st.info(analysis_msg)


def _display_graph_visualization_section(analysis_result, viz_type):
    """Display graph visualization section."""
    if viz_type not in ["graph", "interactive"]:
        return

    st.subheader("📊 Dependency Graph Visualization")

    # Parse dependencies for filtering and analysis
    _ = _parse_dependency_analysis(analysis_result)

    # Layout algorithm selector
    layout_options = [
        "auto",
        "spring",
        "circular",
        "kamada_kawai",
        "shell",
        "spectral",
        "force_directed",
        "random",
    ]
    selected_layout = st.selectbox(
        "Layout Algorithm",
        layout_options,
        help="Choose graph layout algorithm. 'auto' selects best "
        "algorithm based on graph size.",
        format_func=lambda x: {
            "auto": "Auto (recommended)",
            "spring": "Spring Layout",
            "circular": "Circular Layout",
            "kamada_kawai": "Kamada-Kawai Layout",
            "shell": "Shell Layout (hierarchical)",
            "spectral": "Spectral Layout",
            "force_directed": "Force Directed",
            "random": "Random Layout",
        }.get(x, str(x)),
    )

    # Graph cache management
    _handle_graph_caching()

    # Graph Filtering Options
    st.subheader("🔍 Graph Filtering & Analysis")

    col1, col2, col3 = st.columns(3)

    with col1:
        show_circular_only = st.checkbox(
            "Show Circular Dependencies Only",
            help=("Filter graph to show only nodes involved in circular dependencies"),
        )

    with col2:
        show_community_only = st.checkbox(
            "Show Community Cookbooks Only",
            help=(
                "Filter graph to show only community cookbooks and their dependencies"
            ),
        )

    with col3:
        min_connections = st.slider(
            "Minimum Connections",
            min_value=0,
            max_value=10,
            value=0,
            help="Show only nodes with at least this many connections",
        )

    _display_dependency_graph_visualization(
        analysis_result,
        viz_type,
        selected_layout,
        show_circular_only,
        show_community_only,
        min_connections,
    )


def _display_impact_analysis_section(analysis_result):
    """Display migration impact analysis section."""
    # Parse dependencies for impact analysis
    dependencies, circular_deps, community_cookbooks = _parse_dependency_analysis(
        analysis_result
    )

    # Impact Analysis Section
    st.subheader("📊 Migration Impact Analysis")

    if not dependencies:
        st.info("No dependencies found for impact analysis.")
        return

    impact_analysis = _calculate_migration_impact(
        dependencies, circular_deps, community_cookbooks
    )

    # Calculate risk score delta
    risk_score = impact_analysis["risk_score"]
    if risk_score > 7:
        risk_delta = "🔴 High"
    elif risk_score > 4:
        risk_delta = "🟡 Medium"
    else:
        risk_delta = "🟢 Low"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Migration Risk Score",
            f"{impact_analysis['risk_score']:.1f}/10",
            delta=risk_delta,
        )

    with col2:
        timeline_weeks = impact_analysis["timeline_impact_weeks"]
        timeline_delta = "↗️" if timeline_weeks > 0 else "→"
        st.metric(
            "Estimated Timeline Impact",
            f"{timeline_weeks} weeks",
            delta=timeline_delta,
        )

    with col3:
        complexity_level = impact_analysis["complexity_level"]
        complexity_delta = "⚠️ High" if complexity_level == "High" else "✅ Low"
        st.metric(
            "Dependency Complexity",
            complexity_level,
            delta=complexity_delta,
        )

    with col4:
        parallel_streams = impact_analysis["parallel_streams"]
        parallel_delta = "🔀 Multiple" if parallel_streams > 1 else "➡️ Single"
        st.metric(
            "Parallel Migration Streams",
            parallel_streams,
            delta=parallel_delta,
        )

    # Detailed impact breakdown
    with st.expander("📈 Detailed Impact Analysis"):
        _display_detailed_impact_analysis(
            impact_analysis, dependencies, circular_deps, community_cookbooks
        )


def _display_analysis_details_section(
    analysis_result, circular_deps, community_cookbooks, direct_deps
):
    """Display analysis details section."""
    # Display analysis results
    st.subheader("Dependency Analysis Details")

    _display_dependency_analysis_sections(analysis_result)

    # Migration recommendations
    _display_migration_recommendations(circular_deps, community_cookbooks, direct_deps)


def display_dependency_analysis_results():
    """Display dependency analysis results."""
    analysis_result = st.session_state.dep_analysis_result
    cookbook_path = st.session_state.dep_cookbook_path
    depth = st.session_state.dep_depth
    viz_type = st.session_state.get("dep_viz_type", "text")

    # Display summary section
    _display_dependency_analysis_summary(analysis_result, cookbook_path, depth)

    # Display graph visualization section
    _display_graph_visualization_section(analysis_result, viz_type)

    # Display impact analysis section
    _display_impact_analysis_section(analysis_result)

    # Display analysis details section
    dependencies, circular_deps, community_cookbooks = _parse_dependency_analysis(
        analysis_result
    )
    direct_deps = len(dependencies) if dependencies else 0
    _display_analysis_details_section(
        analysis_result, circular_deps, community_cookbooks, direct_deps
    )

    # Export options
    _display_dependency_export_options(
        analysis_result,
        cookbook_path,
        depth,
        direct_deps,
        len(dependencies) if dependencies else 0,  # transitive_deps approximation
        circular_deps,
        community_cookbooks,
    )


def _collect_files_to_validate(input_path: str) -> list[Path]:
    """Collect valid YAML files from input path."""
    validated_path = _normalize_and_validate_input_path(input_path)
    if validated_path is None:
        # Error already reported by _normalize_and_validate_input_path
        return []

    path_obj = validated_path
    files_to_validate = []

    if not path_obj.exists():
        st.error(f"Path does not exist: {path_obj}")
        return []

    if path_obj.is_file():
        if path_obj.suffix in [".yml", ".yaml"] and path_obj.name not in [
            ".kitchen.yml",
            "kitchen.yml",
            "docker-compose.yml",
        ]:
            files_to_validate.append(path_obj)
    elif path_obj.is_dir():
        # Filter out obvious non-playbook files
        excluded_files = {".kitchen.yml", "kitchen.yml", "docker-compose.yml"}

        yml_files = list(path_obj.glob("**/*.yml"))
        yaml_files = list(path_obj.glob("**/*.yaml"))

        raw_files = yml_files + yaml_files
        files_to_validate.extend([f for f in raw_files if f.name not in excluded_files])

    return files_to_validate


def _run_validation_engine(files_to_validate):
    """Run validation engine on a list of files."""
    from souschef.core.validation import (
        ValidationCategory,
        ValidationEngine,
        ValidationLevel,
        ValidationResult,
    )

    engine = ValidationEngine()
    all_results = []

    for file_path in files_to_validate:
        try:
            content = file_path.read_text()
            # We assume 'recipe' (Playbook) conversion type for .yml files found
            file_results = engine.validate_conversion("recipe", content)

            # If no issues found, explicitly add a success record
            if not file_results:
                file_results = [
                    ValidationResult(
                        ValidationLevel.INFO,
                        ValidationCategory.SYNTAX,
                        "File passed all validation checks",
                        location=file_path.name,
                    )
                ]

            # Annotate results with location if missing
            for res in file_results:
                if not res.location:
                    res.location = file_path.name

            all_results.extend(file_results)
        except Exception as file_err:
            st.warning(f"Could not read/validate {file_path.name}: {file_err}")

    return all_results


def _get_default_validation_path():
    """Determine the default path for validation from session state."""
    default_path = ""
    if "converted_playbooks_path" in st.session_state:
        default_path = st.session_state.converted_playbooks_path
        st.info(f"Pre-filled path from conversion: {default_path}")
    elif (
        "analysis_cookbook_path" in st.session_state
        and st.session_state.analysis_cookbook_path
    ):
        default_path = st.session_state.analysis_cookbook_path
        st.info(f"Pre-filled path from analysis: {default_path}")
        st.caption(
            "Note: This tool validates Ansible playbooks (.yml). If you're using a raw "
            "Chef cookbook path, please ensure you've performed the conversion first."
        )
    return default_path


def _render_validation_options_ui():
    """Render validation scope and format options."""
    col1, col2 = st.columns(2)

    with col1:
        sub_scope = st.selectbox(
            "Validation Scope",
            [
                "Full Suite",
                "Syntax Only",
                "Logic/Semantic",
                "Security",
                SCOPE_BEST_PRACTICES,
            ],
            help="Filter which validation checks to run",
        )

    with col2:
        sub_format = st.selectbox(
            "Output Format",
            ["text", "json", "html"],
            help="Format for validation reports",
            format_func=lambda x: {
                "text": "Text Report",
                "json": "JSON Data",
                "html": "HTML Report",
            }.get(x, str(x)),
        )
    return sub_scope, sub_format


def _render_validation_input_ui(default_path):
    """Render input source selection UI."""
    st.subheader("Input Source")

    input_type = st.radio(
        "Input Type",
        ["Directory", "Single File"],
        horizontal=True,
        help="Validate a directory of files or a single file",
    )

    if input_type == "Directory":
        input_path = st.text_input(
            "Directory Path",
            value=default_path,
            placeholder="/path/to/ansible/playbooks",
            help="Path to directory containing Ansible playbooks to validate",
        )
    else:
        input_path = st.text_input(
            "File Path",
            value=default_path
            if default_path and default_path.endswith((".yml", ".yaml"))
            else "",
            placeholder="/path/to/playbook.yml",
            help="Path to single Ansible playbook file to validate",
        )
    return input_path


def _render_validation_settings_ui():
    """Render strict mode and other validation settings."""
    st.subheader("Validation Options")

    col1, col2, col3 = st.columns(3)

    with col1:
        strict_mode = st.checkbox(
            "Strict Mode", help="Fail on warnings, not just errors"
        )

    with col2:
        include_best_practices = st.checkbox(
            f"Include {SCOPE_BEST_PRACTICES}",
            value=True,
            help="Check for Ansible best practices",
        )

    with col3:
        generate_recommendations = st.checkbox(
            "Generate Recommendations",
            value=True,
            help="Provide improvement suggestions",
        )

    return strict_mode, include_best_practices, generate_recommendations


def _normalize_and_validate_input_path(input_path: str) -> Path | None:
    """
    Normalize and validate a user-provided filesystem path.

    Returns a resolved Path object if valid, otherwise reports an error
    via Streamlit and returns None.
    """
    if not input_path:
        st.error(ERROR_MSG_ENTER_PATH)
        return None

    raw = input_path.strip()
    if not raw:
        st.error(ERROR_MSG_ENTER_PATH)
        return None

    try:
        # Expand user home and resolve to an absolute, normalized path
        path_obj = Path(raw).expanduser().resolve()
    except Exception:
        st.error(f"Invalid path: {raw}")
        return None

    # Optional safety: constrain to the application root directory
    try:
        app_root = Path(app_path).resolve()
        path_obj.relative_to(app_root)
    except Exception:
        st.error("Path must be within the SousChef project directory.")
        return None

    return path_obj


def _handle_validation_execution(input_path, options):
    """Execute the validation process with progress tracking."""
    progress_tracker = ProgressTracker(
        total_steps=6, description="Running validation..."
    )

    try:
        progress_tracker.update(1, "Preparing validation environment...")

        progress_tracker.update(2, "Scanning input files...")

        files_to_validate = _collect_files_to_validate(input_path)

        if not files_to_validate:
            # Error is handled inside _collect_files_to_validate
            # if path doesn't exist or is invalid
            validated_path = _normalize_and_validate_input_path(input_path)
            if validated_path is not None and validated_path.exists():
                st.warning(f"No YAML files found in {validated_path}")
            return

        progress_tracker.update(3, f"Validating {len(files_to_validate)} files...")

        all_results = _run_validation_engine(files_to_validate)

        # Filter results based on scope
        filtered_results = _filter_results_by_scope(all_results, options["scope"])

        # Format the results as text
        validation_result = "\n".join(
            [
                f"[{result.level.value.upper()}] {result.location}: {result.message}"
                for result in filtered_results
            ]
        )

        if not validation_result:
            validation_result = "No issues found matching the selected scope."

        progress_tracker.update(5, "Generating validation report...")

        # Store results
        st.session_state.validation_result = validation_result
        st.session_state.validation_path = input_path.strip()
        st.session_state.validation_type = options["scope"]
        st.session_state.validation_options = options

        progress_tracker.complete("Validation completed!")
        st.success(f"Validation completed! Scanned {len(files_to_validate)} files.")
        st.rerun()

    except Exception as e:
        progress_tracker.close()
        st.error(f"Error during validation: {e}")


def show_validation_reports():
    """Show validation reports and conversion validation."""
    st.header(NAV_VALIDATION_REPORTS)

    st.markdown("""
    Validate Chef to Ansible conversions and generate comprehensive
    validation reports for migration quality assurance.
    """)

    # Check for previously analyzed path to pre-fill
    default_path = _get_default_validation_path()

    # UI Components
    validation_scope, output_format = _render_validation_options_ui()
    input_path = _render_validation_input_ui(default_path)
    strict_mode, include_best_practices, generate_recommendations = (
        _render_validation_settings_ui()
    )

    # Validation button
    if st.button("Run Validation", type="primary", width="stretch"):
        if not input_path or not input_path.strip():
            st.error("Please enter a path to validate.")
            return

        options = {
            "strict": strict_mode,
            "best_practices": include_best_practices,
            "recommendations": generate_recommendations,
            "scope": validation_scope,
            "format": output_format,
        }

        _handle_validation_execution(input_path, options)

    # Display results if available
    if "validation_result" in st.session_state:
        display_validation_results()


def _filter_results_by_scope(results, scope):
    """Filter validation results based on selected scope."""
    from souschef.core.validation import ValidationCategory

    if scope == "Full Suite":
        return results

    scope_map = {
        "Syntax Only": ValidationCategory.SYNTAX,
        "Logic/Semantic": ValidationCategory.SEMANTIC,
        "Security": ValidationCategory.SECURITY,
        SCOPE_BEST_PRACTICES: ValidationCategory.BEST_PRACTICE,
    }

    target_category = scope_map.get(scope)
    if not target_category:
        return results

    return [r for r in results if r.category == target_category]


def _parse_validation_metrics(validation_result):
    """Parse validation result to extract key metrics."""
    lines = validation_result.split("\n")

    errors = 0
    warnings = 0
    passed = 0
    total_checks = 0

    for line in lines:
        line_upper = line.upper()
        # Match both old format "ERROR:" and new format "[ERROR]"
        if "ERROR:" in line_upper or "[ERROR]" in line_upper:
            errors += 1
        elif "WARNING:" in line_upper or "[WARNING]" in line_upper:
            warnings += 1
        # Match explicit passed check or INFO level (which we use for success now)
        elif (
            "PASSED:" in line_upper
            or "PASSED" in line_upper
            or "✓" in line
            or "[INFO]" in line_upper
        ):
            passed += 1
        if "Total checks:" in line.lower():
            with contextlib.suppress(ValueError):
                total_checks = int(line.split(":")[1].strip())

    # If we found errors/warnings but no explicit "checks" count (legacy log parsing),
    # infer total checks from line items
    if total_checks == 0 and (errors > 0 or warnings > 0 or passed > 0):
        total_checks = errors + warnings + passed

    return errors, warnings, passed, total_checks


def _display_validation_summary_metrics(errors, warnings, passed, total_checks):
    """Display validation summary metrics."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Checks", total_checks)

    with col2:
        st.metric("Passed", passed, delta="✅" if passed > 0 else "")

    with col3:
        st.metric("Warnings", warnings, delta="⚠️" if warnings > 0 else "")

    with col4:
        st.metric("Errors", errors, delta="❌" if errors > 0 else "")


def _display_validation_status(errors, warnings):
    """Display overall validation status."""
    if errors > 0:
        st.error("❌ **Validation Failed**: Critical issues found that need attention.")
    elif warnings > 0:
        st.warning(
            "⚠️ **Validation Passed with Warnings**: Review warnings before proceeding."
        )
    else:
        st.success("✅ **Validation Passed**: All checks successful!")


def _display_validation_sections(validation_result):
    """Display validation results in expandable sections."""
    # Split results into sections
    sections = validation_result.split("\n## ")

    for section in sections:
        if section.strip():
            if not section.startswith("#"):
                section = "## " + section

            # Add expanders for different sections
            if "Syntax Validation" in section:
                with st.expander("🔍 Syntax Validation"):
                    st.markdown(section.replace("## Syntax Validation", ""))
            elif "Logic Validation" in section:
                with st.expander("🧠 Logic Validation"):
                    st.markdown(section.replace("## Logic Validation", ""))
            elif "Security Validation" in section:
                with st.expander("🔒 Security Validation"):
                    st.markdown(section.replace("## Security Validation", ""))
            elif "Performance Validation" in section:
                with st.expander("⚡ Performance Validation"):
                    st.markdown(section.replace("## Performance Validation", ""))
            elif SCOPE_BEST_PRACTICES in section:
                with st.expander(f"📋 {SCOPE_BEST_PRACTICES}"):
                    st.markdown(section.replace(f"## {SCOPE_BEST_PRACTICES}", ""))
            elif "Recommendations" in section:
                with st.expander("💡 Recommendations"):
                    st.markdown(section.replace("## Recommendations", ""))
            else:
                st.markdown(section)


def _display_validation_action_items(errors, warnings):
    """Display action items based on validation results."""
    if errors > 0 or warnings > 0:
        st.subheader("Action Items")

        if errors > 0:
            st.error("**Critical Issues to Fix:**")
            st.markdown("""
            - Review error messages above
            - Fix syntax and logic errors
            - Re-run validation after fixes
            - Consider impact on migration timeline
            """)

        if warnings > 0:
            st.warning("**Warnings to Review:**")
            st.markdown("""
            - Address security warnings
            - Review performance suggestions
            - Consider best practice recommendations
            - Document any intentional deviations
            """)


def _display_validation_export_options(
    validation_result,
    input_path,
    validation_type,
    options,
    errors,
    warnings,
    passed,
    total_checks,
):
    """Display export options for validation results."""
    st.subheader("Export Report")

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="📥 Download Full Report",
            data=validation_result,
            file_name="validation_report.md",
            mime=MIME_TEXT_MARKDOWN,
            help="Download complete validation report",
        )

    with col2:
        # Create JSON summary
        if errors > 0:
            status = "failed"
        elif warnings > 0:
            status = "warning"
        else:
            status = "passed"
        report_json = {
            "input_path": input_path,
            "validation_type": validation_type,
            "options": options,
            "metrics": {
                "total_checks": total_checks,
                "passed": passed,
                "warnings": warnings,
                "errors": errors,
            },
            "status": status,
            "full_report": validation_result,
        }

        import json

        st.download_button(
            label="📊 Download JSON Summary",
            data=json.dumps(report_json, indent=2),
            file_name="validation_report.json",
            mime=MIME_APPLICATION_JSON,
            help="Download validation summary as JSON",
        )


def display_validation_results():
    """Display validation results."""
    validation_result = st.session_state.validation_result
    input_path = st.session_state.validation_path
    validation_type = st.session_state.validation_type
    options = st.session_state.validation_options

    # Summary metrics
    st.subheader("Validation Summary")

    # Parse validation result for metrics
    errors, warnings, passed, total_checks = _parse_validation_metrics(
        validation_result
    )

    # Display summary metrics
    _display_validation_summary_metrics(errors, warnings, passed, total_checks)

    # Overall status
    _display_validation_status(errors, warnings)

    # Validation details
    validation_msg = f"Validation type: **{validation_type}** | Path: `{input_path}`"
    st.info(validation_msg)

    # Display validation results
    st.subheader("Validation Details")

    _display_validation_sections(validation_result)

    # Action items
    _display_validation_action_items(errors, warnings)

    # Export options
    _display_validation_export_options(
        validation_result,
        input_path,
        validation_type,
        options,
        errors,
        warnings,
        passed,
        total_checks,
    )


if __name__ == "__main__":
    main()
