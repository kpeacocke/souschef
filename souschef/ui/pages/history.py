"""History page for viewing past analyses and conversions."""

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Add the parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from souschef.storage import get_blob_storage, get_storage_manager


def show_history_page() -> None:
    """Show the history page with past analyses and conversions."""
    st.header("Analysis and Conversion History")
    st.markdown("""
    View your historical cookbook analyses and conversions. Download previously
    generated assets and review past recommendations.
    """)

    # Get storage manager
    storage_manager = get_storage_manager()
    blob_storage = get_blob_storage()

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Analysis History", "Conversion History", "Statistics"])

    with tab1:
        _show_analysis_history(storage_manager)

    with tab2:
        _show_conversion_history(storage_manager, blob_storage)

    with tab3:
        _show_statistics(storage_manager)


def _show_analysis_history(storage_manager) -> None:
    """Show analysis history tab."""
    st.subheader("Analysis History")

    # Filters
    col1, col2 = st.columns([3, 1])

    with col1:
        cookbook_filter = st.text_input(
            "Filter by cookbook name",
            placeholder="Enter cookbook name...",
            key="history_cookbook_filter",
        )

    with col2:
        limit = st.selectbox(
            "Show results",
            [10, 25, 50, 100],
            index=1,
            key="history_limit",
        )

    # Get analysis history
    if cookbook_filter:
        analyses = storage_manager.get_analysis_history(
            cookbook_name=cookbook_filter, limit=limit
        )
    else:
        analyses = storage_manager.get_analysis_history(limit=limit)

    if not analyses:
        st.info("No analysis history found. Start by analysing a cookbook!")
        return

    # Display as table
    st.write(f"**Total Results:** {len(analyses)}")

    df_data = []
    for analysis in analyses:
        time_saved = analysis.estimated_hours - analysis.estimated_hours_with_souschef
        df_data.append(
            {
                "Cookbook": analysis.cookbook_name,
                "Version": analysis.cookbook_version,
                "Complexity": analysis.complexity,
                "Manual Hours": f"{analysis.estimated_hours:.1f}",
                "AI Hours": f"{analysis.estimated_hours_with_souschef:.1f}",
                "Time Saved": f"{time_saved:.1f}h",
                "AI Provider": analysis.ai_provider or "Rule-based",
                "Date": _format_datetime(analysis.created_at),
                "ID": analysis.id,
            }
        )

    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Expandable details
    st.subheader("Analysis Details")

    selected_id = st.selectbox(
        "Select analysis to view details",
        options=[a.id for a in analyses],
        format_func=lambda x: next(
            f"{a.cookbook_name} - {_format_datetime(a.created_at)}"
            for a in analyses
            if a.id == x
        ),
        key="history_selected_analysis",
    )

    if selected_id:
        selected = next(a for a in analyses if a.id == selected_id)
        _display_analysis_details(selected)


def _display_analysis_details(analysis) -> None:
    """Display detailed analysis information."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Complexity", analysis.complexity)

    with col2:
        st.metric("Manual Hours", f"{analysis.estimated_hours:.1f}")

    with col3:
        st.metric("AI-Assisted Hours", f"{analysis.estimated_hours_with_souschef:.1f}")

    with col4:
        time_saved = analysis.estimated_hours - analysis.estimated_hours_with_souschef
        st.metric("Time Saved", f"{time_saved:.1f}h")

    # Recommendations
    st.markdown("### Recommendations")
    st.text_area(
        "Analysis Recommendations",
        value=analysis.recommendations,
        height=200,
        disabled=True,
        key=f"recommendations_{analysis.id}",
    )

    # Full analysis data
    with st.expander("View Full Analysis Data"):
        try:
            analysis_data = json.loads(analysis.analysis_data)
            st.json(analysis_data)
        except json.JSONDecodeError:
            st.error("Unable to parse analysis data")


def _show_conversion_history(storage_manager, blob_storage) -> None:
    """Show conversion history tab."""
    st.subheader("Conversion History")

    # Filters
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        cookbook_filter = st.text_input(
            "Filter by cookbook name",
            placeholder="Enter cookbook name...",
            key="conversion_cookbook_filter",
        )

    with col2:
        status_filter = st.selectbox(
            "Filter by status",
            ["All", "success", "partial", "failed"],
            key="conversion_status_filter",
        )

    with col3:
        limit = st.selectbox(
            "Show results",
            [10, 25, 50, 100],
            index=1,
            key="conversion_limit",
        )

    # Get conversion history
    if cookbook_filter:
        conversions = storage_manager.get_conversion_history(
            cookbook_name=cookbook_filter, limit=limit
        )
    else:
        conversions = storage_manager.get_conversion_history(limit=limit)

    # Filter by status
    if status_filter != "All":
        conversions = [c for c in conversions if c.status == status_filter]

    if not conversions:
        st.info("No conversion history found. Start by converting a cookbook!")
        return

    # Display as table
    st.write(f"**Total Results:** {len(conversions)}")

    df_data = []
    for conversion in conversions:
        df_data.append(
            {
                "Status": conversion.status,
                "Cookbook": conversion.cookbook_name,
                "Output Type": conversion.output_type,
                "Files Generated": conversion.files_generated,
                "Has Artefacts": "Yes" if conversion.blob_storage_key else "No",
                "Date": _format_datetime(conversion.created_at),
                "ID": conversion.id,
            }
        )

    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Download artifacts
    st.subheader("Download Artefacts")

    selected_id = st.selectbox(
        "Select conversion to download",
        options=[c.id for c in conversions if c.blob_storage_key],
        format_func=lambda x: next(
            f"{c.cookbook_name} - {_format_datetime(c.created_at)}"
            for c in conversions
            if c.id == x
        ),
        key="history_selected_conversion",
    )

    if selected_id:
        selected = next(c for c in conversions if c.id == selected_id)
        if selected.blob_storage_key:
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(f"**Cookbook:** {selected.cookbook_name}")
                st.write(f"**Output Type:** {selected.output_type}")
                st.write(f"**Files Generated:** {selected.files_generated}")

            with col2:
                if st.button(
                    "Download Artefacts",
                    type="primary",
                    key=f"download_{selected.id}",
                ):
                    _download_conversion_artefacts(selected, blob_storage)


def _download_conversion_artefacts(conversion, blob_storage) -> None:
    """Download conversion artefacts from blob storage."""
    import tempfile

    try:
        with st.spinner("Downloading artefacts..."):
            # Download to temporary location
            temp_dir = Path(tempfile.mkdtemp())
            download_path = blob_storage.download(
                conversion.blob_storage_key, temp_dir / "artefacts"
            )

            # Create download button
            if download_path.exists():
                if download_path.is_dir():
                    # Create ZIP for download
                    import io
                    import zipfile

                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                        for file_path in download_path.rglob("*"):
                            if file_path.is_file():
                                arcname = file_path.relative_to(download_path)
                                zipf.write(file_path, arcname)

                    zip_buffer.seek(0)
                    st.download_button(
                        label="Download ZIP",
                        data=zip_buffer.getvalue(),
                        file_name=f"{conversion.cookbook_name}_artefacts.zip",
                        mime="application/zip",
                        key=f"download_btn_{conversion.id}",
                    )
                else:
                    # Single file download
                    with download_path.open("rb") as f:
                        st.download_button(
                            label="Download File",
                            data=f.read(),
                            file_name=download_path.name,
                            key=f"download_btn_{conversion.id}",
                        )

                st.success("Artefacts ready for download!")

    except Exception as e:
        st.error(f"Failed to download artefacts: {e}")


def _show_statistics(storage_manager) -> None:
    """Show statistics tab."""
    st.subheader("Overall Statistics")

    stats = storage_manager.get_statistics()

    # Main metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Analyses", stats["total_analyses"])
        st.metric("Unique Cookbooks", stats["unique_cookbooks_analysed"])

    with col2:
        st.metric("Total Conversions", stats["total_conversions"])
        st.metric("Successful Conversions", stats["successful_conversions"])

    with col3:
        success_rate = (
            (stats["successful_conversions"] / stats["total_conversions"] * 100)
            if stats["total_conversions"] > 0
            else 0
        )
        st.metric("Success Rate", f"{success_rate:.1f}%")
        st.metric("Files Generated", stats["total_files_generated"])

    st.divider()

    # Effort savings
    st.subheader("Effort Savings Analysis")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Avg Manual Hours", f"{stats['avg_manual_hours']:.1f}")

    with col2:
        st.metric("Avg AI-Assisted Hours", f"{stats['avg_ai_hours']:.1f}")

    with col3:
        time_saved = stats["avg_manual_hours"] - stats["avg_ai_hours"]
        st.metric("Avg Time Saved", f"{time_saved:.1f}h")

    # Calculate total time saved
    if stats["total_analyses"] > 0:
        total_manual = stats["avg_manual_hours"] * stats["total_analyses"]
        total_ai = stats["avg_ai_hours"] * stats["total_analyses"]
        total_saved = total_manual - total_ai

        st.info(
            f"**Total Time Saved Across All Analyses:** {total_saved:.1f} hours "
            f"({total_saved / 8:.1f} work days)"
        )


def _format_datetime(dt_str: str) -> str:
    """
    Format datetime string for display.

    Args:
        dt_str: DateTime string from database.

    Returns:
        Formatted datetime string.

    """
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return dt_str
