"""Cookbook Analysis Page for SousChef UI."""

import sys
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
import streamlit as st

# Add the parent directory to the path so we can import souschef modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from souschef.assessment import parse_chef_migration_assessment
from souschef.parsers.metadata import parse_cookbook_metadata

# Constants for repeated strings
METADATA_STATUS_YES = "Yes"
METADATA_STATUS_NO = "No"
ANALYSIS_STATUS_ANALYZED = "Analyzed"
ANALYSIS_STATUS_FAILED = "Failed"
METADATA_COLUMN_NAME = "Has Metadata"


def show_cookbook_analysis_page():
    """Show the cookbook analysis page."""
    _setup_cookbook_analysis_ui()
    cookbook_path = _get_cookbook_path_input()

    if cookbook_path:
        _validate_and_list_cookbooks(cookbook_path)

    _display_instructions()


def _setup_cookbook_analysis_ui():
    """Set up the cookbook analysis page header."""
    st.header("Cookbook Analysis")


def _get_cookbook_path_input():
    """Get the cookbook path input from the user."""
    return st.text_input(
        "Cookbook Directory Path",
        placeholder="/path/to/your/cookbooks",
        help="Enter the absolute path to your Chef cookbooks directory",
    )


def _validate_and_list_cookbooks(cookbook_path):
    """Validate the cookbook path and list available cookbooks."""
    safe_dir = _get_safe_cookbook_directory(cookbook_path)
    if safe_dir is None:
        return

    if safe_dir.exists() and safe_dir.is_dir():
        st.success(f"Found directory: {safe_dir}")
        _list_and_display_cookbooks(safe_dir)
    else:
        st.error(f"Directory not found: {safe_dir}")


def _get_safe_cookbook_directory(cookbook_path):
    """
    Resolve the user-provided cookbook path to a safe directory.

    The path is resolved against a base directory and normalized to
    prevent directory traversal outside the allowed root.
    """
    try:
        base_dir = Path.cwd().resolve()
        user_path = Path(cookbook_path.strip())
        if not user_path.is_absolute():
            candidate = (base_dir / user_path).resolve()
        else:
            candidate = user_path.resolve()
    except Exception as exc:
        st.error(f"Invalid path: {exc}")
        return None

    # Ensure the final path is within the allowed base directory.
    try:
        candidate.relative_to(base_dir)
    except ValueError:
        st.error("The specified path is outside the allowed cookbook directory root.")
        return None

    return candidate


def _list_and_display_cookbooks(cookbook_path: Path):
    """List cookbooks in the directory and display them."""
    try:
        cookbooks = [d for d in cookbook_path.iterdir() if d.is_dir()]
        if cookbooks:
            st.subheader("Available Cookbooks")
            cookbook_data = _collect_cookbook_data(cookbooks)
            _display_cookbook_table(cookbook_data)
            _handle_cookbook_selection(str(cookbook_path), cookbook_data)
        else:
            st.warning(
                "No subdirectories found in the specified path. "
                "Are these individual cookbooks?"
            )
    except Exception as e:
        st.error(f"Error reading directory: {e}")


def _collect_cookbook_data(cookbooks):
    """Collect data for all cookbooks."""
    cookbook_data = []
    for cookbook in cookbooks:
        cookbook_info = _analyze_cookbook_metadata(cookbook)
        cookbook_data.append(cookbook_info)
    return cookbook_data


def _analyze_cookbook_metadata(cookbook):
    """Analyze metadata for a single cookbook."""
    metadata_file = cookbook / "metadata.rb"
    if metadata_file.exists():
        return _parse_metadata_with_fallback(cookbook, metadata_file)
    else:
        return _create_no_metadata_entry(cookbook)


def _parse_metadata_with_fallback(cookbook, metadata_file):
    """Parse metadata with error handling."""
    try:
        metadata = parse_cookbook_metadata(str(metadata_file))
        return _extract_cookbook_info(metadata, cookbook, METADATA_STATUS_YES)
    except Exception as e:
        return _create_error_entry(cookbook, str(e))


def _extract_cookbook_info(metadata, cookbook, metadata_status):
    """Extract key information from cookbook metadata."""
    name = metadata.get("name", cookbook.name)
    version = metadata.get("version", "Unknown")
    maintainer = metadata.get("maintainer", "Unknown")
    description = _normalize_description(metadata.get("description", "No description"))
    dependencies = len(metadata.get("depends", []))

    return {
        "Name": name,
        "Version": version,
        "Maintainer": maintainer,
        "Description": _truncate_description(description),
        "Dependencies": dependencies,
        "Path": str(cookbook),
        METADATA_COLUMN_NAME: metadata_status,
    }


def _normalize_description(description):
    """
    Normalize description to string format.

    The metadata parser currently returns a string for the description
    field, but this helper defensively converts any unexpected value to
    a string to keep the UI resilient to future changes.
    """
    if not isinstance(description, str):
        return str(description)
    return description


def _truncate_description(description):
    """Truncate description if too long."""
    if len(description) > 50:
        return description[:50] + "..."
    return description


def _create_error_entry(cookbook, error_message):
    """Create an entry for cookbooks with parsing errors."""
    return {
        "Name": cookbook.name,
        "Version": "Error",
        "Maintainer": "Error",
        "Description": f"Parse error: {error_message[:50]}",
        "Dependencies": 0,
        "Path": str(cookbook),
        METADATA_COLUMN_NAME: METADATA_STATUS_NO,
    }


def _create_no_metadata_entry(cookbook):
    """Create an entry for cookbooks without metadata."""
    return {
        "Name": cookbook.name,
        "Version": "No metadata",
        "Maintainer": "Unknown",
        "Description": "No metadata.rb found",
        "Dependencies": 0,
        "Path": str(cookbook),
        METADATA_COLUMN_NAME: METADATA_STATUS_NO,
    }


def _display_cookbook_table(cookbook_data):
    """Display the cookbook data in a table."""
    df = pd.DataFrame(cookbook_data)
    st.dataframe(df, use_container_width=True)


def _handle_cookbook_selection(cookbook_path, cookbook_data):
    """Handle cookbook selection and analysis trigger."""
    available_cookbooks = [
        str(cb["Name"])
        for cb in cookbook_data
        if cb[METADATA_COLUMN_NAME] == METADATA_STATUS_YES
    ]

    selected_cookbooks = st.multiselect(
        "Select cookbooks to analyze",
        available_cookbooks,
    )

    if selected_cookbooks and st.button("Analyze Selected Cookbooks", type="primary"):
        analyze_selected_cookbooks(cookbook_path, selected_cookbooks)


def _display_instructions():
    """Display usage instructions."""
    with st.expander("How to Use"):
        st.markdown("""
        1. **Enter Cookbook Path**: Provide the absolute path to your cookbooks
           directory
        2. **Review Cookbooks**: The interface will list all cookbooks with metadata
        3. **Select Cookbooks**: Choose which cookbooks to analyze
        4. **Run Analysis**: Click "Analyze Selected Cookbooks" to get detailed insights

        **Expected Structure:**
        ```
        /path/to/cookbooks/
        ├── nginx/
        │   ├── metadata.rb
        │   ├── recipes/
        │   └── attributes/
        ├── apache2/
        │   └── metadata.rb
        └── mysql/
            └── metadata.rb
        ```
        """)


def analyze_selected_cookbooks(cookbook_path: str, selected_cookbooks: list[str]):
    """Analyze the selected cookbooks and display results."""
    st.subheader("Analysis Results")

    progress_bar, status_text = _setup_analysis_progress()
    results = _perform_cookbook_analysis(
        cookbook_path, selected_cookbooks, progress_bar, status_text
    )

    _cleanup_progress_indicators(progress_bar, status_text)
    _display_analysis_results(results, len(selected_cookbooks))


def _setup_analysis_progress():
    """Set up progress tracking for analysis."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    return progress_bar, status_text


def _perform_cookbook_analysis(
    cookbook_path, selected_cookbooks, progress_bar, status_text
):
    """Perform analysis on selected cookbooks."""
    results = []
    total = len(selected_cookbooks)

    for i, cookbook_name in enumerate(selected_cookbooks):
        _update_progress(status_text, cookbook_name, i + 1, total)
        progress_bar.progress((i + 1) / total)

        cookbook_dir = _find_cookbook_directory(cookbook_path, cookbook_name)
        if cookbook_dir:
            analysis_result = _analyze_single_cookbook(cookbook_name, cookbook_dir)
            results.append(analysis_result)

    return results


def _update_progress(status_text, cookbook_name, current, total):
    """Update progress display."""
    status_text.text(f"Analyzing {cookbook_name}... ({current}/{total})")


def _find_cookbook_directory(cookbook_path, cookbook_name):
    """Find the directory for a specific cookbook."""
    for d in Path(cookbook_path).iterdir():
        if d.is_dir() and d.name == cookbook_name:
            return d
    return None


def _analyze_single_cookbook(cookbook_name, cookbook_dir):
    """Analyze a single cookbook."""
    try:
        assessment = parse_chef_migration_assessment(str(cookbook_dir))
        metadata = parse_cookbook_metadata(str(cookbook_dir / "metadata.rb"))

        return _create_successful_analysis(
            cookbook_name, cookbook_dir, assessment, metadata
        )
    except Exception as e:
        return _create_failed_analysis(cookbook_name, cookbook_dir, str(e))


def _create_successful_analysis(cookbook_name, cookbook_dir, assessment, metadata):
    """Create analysis result for successful analysis."""
    return {
        "name": cookbook_name,
        "path": str(cookbook_dir),
        "version": metadata.get("version", "Unknown"),
        "maintainer": metadata.get("maintainer", "Unknown"),
        "description": metadata.get("description", "No description"),
        "dependencies": len(metadata.get("depends", [])),
        "complexity": assessment.get("complexity", "Unknown"),
        "estimated_hours": assessment.get("estimated_hours", 0),
        "recommendations": assessment.get("recommendations", ""),
        "status": ANALYSIS_STATUS_ANALYZED,
    }


def _create_failed_analysis(cookbook_name, cookbook_dir, error_message):
    """Create analysis result for failed analysis."""
    return {
        "name": cookbook_name,
        "path": str(cookbook_dir),
        "version": "Error",
        "maintainer": "Error",
        "description": f"Analysis failed: {error_message}",
        "dependencies": 0,
        "complexity": "Error",
        "estimated_hours": 0,
        "recommendations": f"Error: {error_message}",
        "status": ANALYSIS_STATUS_FAILED,
    }


def _cleanup_progress_indicators(progress_bar, status_text):
    """Clean up progress indicators."""
    progress_bar.empty()
    status_text.empty()


def _display_analysis_results(results, total_cookbooks):
    """Display the analysis results."""
    if results:
        _display_analysis_summary(results, total_cookbooks)
        _display_results_table(results)
        _display_detailed_analysis(results)
        _display_download_option(results)


def _display_analysis_summary(results, total_cookbooks):
    """Display summary metrics for the analysis."""
    col1, col2, col3 = st.columns(3)

    with col1:
        successful = len(
            [r for r in results if r["status"] == ANALYSIS_STATUS_ANALYZED]
        )
        st.metric("Successfully Analyzed", f"{successful}/{total_cookbooks}")

    with col2:
        total_hours = sum(r.get("estimated_hours", 0) for r in results)
        st.metric("Total Estimated Hours", f"{total_hours:.1f}")

    with col3:
        complexities = [r.get("complexity", "Unknown") for r in results]
        high_complexity = complexities.count("High")
        st.metric("High Complexity Cookbooks", high_complexity)


def _display_results_table(results):
    """Display results in a table format."""
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)


def _display_detailed_analysis(results):
    """Display detailed analysis for each cookbook."""
    st.subheader("Detailed Analysis")

    for result in results:
        if result["status"] == ANALYSIS_STATUS_ANALYZED:
            _display_single_cookbook_details(result)


def _display_single_cookbook_details(result):
    """Display detailed analysis for a single cookbook."""
    with st.expander(f"{result['name']} - {result['complexity']} Complexity"):
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Version:** {result['version']}")
            st.write(f"**Maintainer:** {result['maintainer']}")
            st.write(f"**Dependencies:** {result['dependencies']}")

        with col2:
            st.write(f"**Estimated Hours:** {result['estimated_hours']:.1f}")
            st.write(f"**Complexity:** {result['complexity']}")

        st.write(f"**Recommendations:** {result['recommendations']}")


def _display_download_option(results):
    """Display download option for analysis results."""
    successful = len([r for r in results if r["status"] == ANALYSIS_STATUS_ANALYZED])
    if successful > 0:
        st.download_button(
            label="Download Analysis Report",
            data=pd.DataFrame(results).to_json(indent=2),
            file_name="cookbook_analysis.json",
            mime="application/json",
            help="Download the analysis results as JSON",
        )


if __name__ == "__main__":
    show_cookbook_analysis_page()
