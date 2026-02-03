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

# Constants
DOWNLOAD_ARTEFACTS_LABEL = "Download Artefacts"


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

    # Check if conversions exist for this analysis
    storage_manager = get_storage_manager()
    blob_storage = get_blob_storage()
    conversions = storage_manager.get_conversions_by_analysis_id(analysis.id)

    st.divider()

    # Show conversion actions based on whether conversions exist
    if conversions:
        _display_conversion_actions(analysis, conversions, blob_storage)
    else:
        _display_convert_button(analysis, blob_storage)

    # Full analysis data
    with st.expander("View Full Analysis Data"):
        try:
            analysis_data = json.loads(analysis.analysis_data)
            st.json(analysis_data)
        except json.JSONDecodeError:
            st.error("Unable to parse analysis data")


def _display_conversion_actions(analysis, conversions, blob_storage) -> None:
    """
    Display download buttons for existing conversions.

    Args:
        analysis: The analysis result.
        conversions: List of conversion results for this analysis.
        blob_storage: Blob storage instance.

    """
    st.markdown("### Conversions")
    st.success(f"✅ {len(conversions)} conversion(s) available for this analysis")

    # Show most recent conversion
    latest_conversion = conversions[0]

    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"**Status:** {latest_conversion.status}")
        st.write(f"**Output Type:** {latest_conversion.output_type}")
        st.write(f"**Files Generated:** {latest_conversion.files_generated}")
        st.write(f"**Date:** {_format_datetime(latest_conversion.created_at)}")

    with col2:
        if latest_conversion.blob_storage_key and st.button(
            DOWNLOAD_ARTEFACTS_LABEL,
            type="primary",
            key=f"download_conversion_{analysis.id}",
        ):
            _download_conversion_artefacts(latest_conversion, blob_storage)

    # Show all conversions in expander if there are multiple
    if len(conversions) > 1:
        with st.expander(f"View All {len(conversions)} Conversions"):
            for idx, conv in enumerate(conversions):
                date_status = _format_datetime(conv.created_at)
                st.write(f"**{idx + 1}. {date_status}** - {conv.status}")
                if conv.blob_storage_key and st.button(
                    "Download",
                    key=f"download_old_conversion_{conv.id}",
                ):
                    _download_conversion_artefacts(conv, blob_storage)


def _display_convert_button(analysis, blob_storage) -> None:
    """
    Display convert button for analyses without conversions.

    Args:
        analysis: The analysis result.
        blob_storage: Blob storage instance.

    """
    st.markdown("### Conversion")
    st.info(
        "No conversions found for this analysis. "
        "Convert the cookbook to Ansible playbooks."
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"**Cookbook:** {analysis.cookbook_name}")
        st.write(f"**Version:** {analysis.cookbook_version}")
        if analysis.cookbook_blob_key:
            st.write("✅ Original cookbook archive available")
        else:
            st.warning("⚠️ Original cookbook archive not found in storage")

    with col2:
        if analysis.cookbook_blob_key:
            if st.button(
                "Convert to Ansible",
                type="primary",
                key=f"convert_analysis_{analysis.id}",
            ):
                _trigger_conversion(analysis, blob_storage)
        else:
            st.button(
                "Convert to Ansible",
                type="primary",
                disabled=True,
                key=f"convert_analysis_{analysis.id}_disabled",
            )
            st.caption("Cannot convert: original cookbook not in storage")


def _trigger_conversion(analysis, blob_storage) -> None:
    """
    Trigger conversion for an analysis from history.

    Args:
        analysis: The analysis result to convert.
        blob_storage: Blob storage instance.

    """
    import tempfile
    from pathlib import Path

    try:
        with st.spinner("Downloading cookbook and preparing conversion..."):
            # Download the original cookbook from blob storage
            temp_dir = Path(tempfile.mkdtemp(prefix="souschef_history_convert_"))
            cookbook_path = blob_storage.download(
                analysis.cookbook_blob_key,
                temp_dir / f"{analysis.cookbook_name}.tar.gz",
            )

            if not cookbook_path or not cookbook_path.exists():
                st.error("Failed to download cookbook from storage")
                return

            # Extract the cookbook
            import tarfile

            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)

            with tarfile.open(cookbook_path, "r:gz") as tar:
                tar.extractall(extract_dir)

            # Find the cookbook directory (should be the only directory in extracted/)
            cookbook_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
            if not cookbook_dirs:
                st.error("No cookbook directory found in archive")
                return

            cookbook_dir = cookbook_dirs[0]

        # Store in session state and direct user to cookbook analysis page
        st.session_state.history_convert_path = str(cookbook_dir)
        st.session_state.history_convert_analysis_id = analysis.id
        st.session_state.history_convert_cookbook_name = analysis.cookbook_name

        st.success("✅ Cookbook downloaded and ready for conversion!")
        st.info(
            "Please navigate to the **Cookbook Analysis** page "
            "to complete the conversion."
        )
        st.markdown("""
        The cookbook has been downloaded from storage and is ready for conversion.
        Go to the Cookbook Analysis page where you'll find a "Convert" button to
        generate Ansible playbooks.
        """)

    except Exception as e:
        st.error(f"Failed to prepare conversion: {e}")
        import traceback

        st.error(traceback.format_exc())


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
                    DOWNLOAD_ARTEFACTS_LABEL,
                    type="primary",
                    key=f"download_{selected.id}",
                ):
                    _download_conversion_artefacts(selected, blob_storage)


def _download_conversion_artefacts(conversion, blob_storage) -> None:
    """Download conversion artefacts from blob storage."""
    import tempfile

    try:
        with st.spinner("Preparing downloads..."):
            # Parse conversion data to get blob keys
            roles_blob_key, repo_blob_key = _parse_conversion_blob_keys(conversion)

            # Download and display archives
            temp_dir = Path(tempfile.mkdtemp())
            _display_roles_download(conversion, blob_storage, roles_blob_key, temp_dir)
            _display_repo_download(conversion, blob_storage, repo_blob_key, temp_dir)

            st.success("✅ Archives ready for download!")

    except Exception as e:
        st.error(f"Failed to download artefacts: {e}")


def _parse_conversion_blob_keys(conversion) -> tuple[str, str | None]:
    """Parse conversion data to extract blob storage keys."""
    try:
        conversion_data = json.loads(conversion.conversion_data)
        roles_blob_key = conversion_data.get(
            "roles_blob_key", conversion.blob_storage_key
        )
        repo_blob_key = conversion_data.get("repo_blob_key")
    except (json.JSONDecodeError, AttributeError):
        roles_blob_key = conversion.blob_storage_key
        repo_blob_key = None
    return roles_blob_key, repo_blob_key


def _display_roles_download(
    conversion, blob_storage, roles_blob_key: str, temp_dir: Path
) -> None:
    """Download and display roles archive download button."""
    roles_path = blob_storage.download(roles_blob_key, temp_dir / "roles_archive")

    if not roles_path.exists():
        return

    if roles_path.is_file():
        with roles_path.open("rb") as f:
            st.download_button(
                label="📦 Download Roles Archive",
                data=f.read(),
                file_name=f"{conversion.cookbook_name}_roles.tar.gz",
                mime="application/gzip",
                key=f"download_roles_{conversion.id}",
            )
    else:
        _create_and_display_zip_download(
            roles_path,
            f"{conversion.cookbook_name}_roles.zip",
            "📦 Download Roles Archive",
            f"download_roles_{conversion.id}",
        )


def _display_repo_download(
    conversion, blob_storage, repo_blob_key: str | None, temp_dir: Path
) -> None:
    """Download and display repository archive download button if available."""
    if not repo_blob_key:
        return

    repo_path = blob_storage.download(repo_blob_key, temp_dir / "repo_archive")

    if not repo_path.exists():
        return

    if repo_path.is_file():
        with repo_path.open("rb") as f:
            st.download_button(
                label="🗂️ Download Repository Archive",
                data=f.read(),
                file_name=f"{conversion.cookbook_name}_repository.tar.gz",
                mime="application/gzip",
                key=f"download_repo_{conversion.id}",
            )
    else:
        _create_and_display_zip_download(
            repo_path,
            f"{conversion.cookbook_name}_repository.zip",
            "🗂️ Download Repository Archive",
            f"download_repo_{conversion.id}",
        )


def _create_and_display_zip_download(
    source_path: Path, file_name: str, label: str, key: str
) -> None:
    """Create a ZIP archive from directory and display download button."""
    import io
    import zipfile

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in source_path.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(source_path)
                zipf.write(file_path, arcname)

    zip_buffer.seek(0)
    st.download_button(
        label=label,
        data=zip_buffer.getvalue(),
        file_name=file_name,
        mime="application/zip",
        key=key,
    )


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
