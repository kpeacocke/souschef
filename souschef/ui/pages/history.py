"""History page for viewing past analyses and conversions."""

import json
import sys
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Add the parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from souschef.storage import get_blob_storage, get_storage_manager

# Constants
DOWNLOAD_ARTEFACTS_LABEL = "Download Artefacts"
MANUAL_HOURS_LABEL = "Manual Hours"
TIME_SAVED_LABEL = "Time Saved"


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
                MANUAL_HOURS_LABEL: f"{analysis.estimated_hours:.1f}",
                "AI Hours": f"{analysis.estimated_hours_with_souschef:.1f}",
                TIME_SAVED_LABEL: f"{time_saved:.1f}h",
                "AI Provider": analysis.ai_provider or "Rule-based",
                "Date": _format_datetime(analysis.created_at),
                "ID": analysis.id,
            }
        )

    df = pd.DataFrame(df_data)
    st.dataframe(df, width="stretch", hide_index=True)

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
        _display_analysis_details(selected, storage_manager)


def _display_analysis_details(analysis, storage_manager) -> None:
    """Display detailed analysis information."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Complexity", analysis.complexity)

    with col2:
        st.metric(MANUAL_HOURS_LABEL, f"{analysis.estimated_hours:.1f}")

    with col3:
        st.metric("AI-Assisted Hours", f"{analysis.estimated_hours_with_souschef:.1f}")

    with col4:
        time_saved = analysis.estimated_hours - analysis.estimated_hours_with_souschef
        st.metric(TIME_SAVED_LABEL, f"{time_saved:.1f}h")

    st.divider()

    # Display activity breakdown if available
    try:
        analysis_data = json.loads(analysis.analysis_data)
        activities = analysis_data.get("activity_breakdown", [])
        if activities:
            _display_analysis_activity_breakdown(activities)
            st.divider()
    except (json.JSONDecodeError, AttributeError):
        # Activity breakdown is a best-effort enhancement; if stored analysis
        # data is missing or malformed, skip this section so the rest of the
        # analysis details can still be displayed.
        pass

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
    blob_storage = get_blob_storage()
    conversions = storage_manager.get_conversions_by_analysis_id(analysis.id)

    st.divider()

    # Show conversion actions based on whether conversions exist
    if conversions:
        _display_conversion_actions(analysis, conversions, blob_storage)
    else:
        _display_convert_button(analysis, blob_storage)

    # Delete button
    st.divider()
    st.markdown("### Danger Zone")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.warning(
            "Deleting this analysis will also delete all associated conversions. "
            "This action cannot be undone."
        )
    with col2:
        if st.button(
            "Delete Analysis",
            type="secondary",
            key=f"delete_analysis_{analysis.id}",
        ):
            if storage_manager.delete_analysis(analysis.id):
                st.success("Analysis deleted successfully!")
                st.rerun()
            else:
                st.error("Failed to delete analysis.")

    # Full analysis data
    with st.expander("View Full Analysis Data"):
        try:
            analysis_data = json.loads(analysis.analysis_data)
            st.json(analysis_data)
        except json.JSONDecodeError:
            st.error("Unable to parse analysis data")


def _display_analysis_activity_breakdown(activities: list) -> None:
    """Display activity breakdown from analysis data."""
    st.subheader("Activity Breakdown Details")

    if not activities:
        return

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Summary")
        for activity in activities:
            name = activity.get("activity_type", "Unknown")
            count = activity.get("count", 0)
            description = activity.get("description", "")
            manual_hours = activity.get("manual_hours", 0)
            ai_hours = activity.get("ai_assisted_hours", 0)
            time_saved = activity.get("time_saved_hours", 0)
            efficiency = activity.get("efficiency_gain_percent", 0)

            st.markdown(
                f"""**{name}** ({count})

*{description}*

Manual: {manual_hours:.1f}h → AI: {ai_hours:.1f}h

**Saved: {time_saved:.1f}h ({efficiency:.0f}%)**"""
            )
            st.divider()

    with col2:
        st.markdown("### Details Table")
        table_data = []
        for activity in activities:
            table_data.append(
                {
                    "Activity": activity.get("activity_type", "Unknown"),
                    "Count": activity.get("count", 0),
                    MANUAL_HOURS_LABEL: f"{activity.get('manual_hours', 0):.1f}",
                    "AI Hours": f"{activity.get('ai_assisted_hours', 0):.1f}",
                    TIME_SAVED_LABEL: f"{activity.get('time_saved_hours', 0):.1f}",
                    "Efficiency": f"{activity.get('efficiency_gain_percent', 0):.0f}%",
                }
            )

        df = pd.DataFrame(table_data)
        st.dataframe(df, width="stretch", hide_index=True)


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
            # Download without assuming the format - we'll detect it
            cookbook_path = blob_storage.download(
                analysis.cookbook_blob_key,
                temp_dir / f"{analysis.cookbook_name}_archive",
            )

            if not cookbook_path or not cookbook_path.exists():
                st.error("Failed to download cookbook from storage")
                return

            # Detect the archive format
            archive_format = _detect_archive_format(cookbook_path)
            if not archive_format:
                st.error(
                    "Unable to detect archive format. "
                    "Supported formats: ZIP, TAR, TAR.GZ, TAR.BZ2, TAR.XZ"
                )
                return

            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)

            # Security limits for extraction (prevent zip bombs and resource exhaustion)
            max_file_size = 100 * 1024 * 1024  # 100 MB per file
            max_total_size = 500 * 1024 * 1024  # 500 MB total
            max_files = 10000  # Maximum number of files

            # Extract based on detected format
            if archive_format == "zip":
                _extract_zip_safely(
                    cookbook_path, extract_dir, max_file_size, max_total_size, max_files
                )
            elif archive_format == "tar.gz":
                with tarfile.open(cookbook_path, "r:gz") as tar:
                    safe_members = _filter_safe_tar_members(
                        tar, extract_dir, max_file_size, max_total_size, max_files
                    )
                    tar.extractall(extract_dir, members=safe_members)
            elif archive_format == "tar.bz2":
                with tarfile.open(cookbook_path, "r:bz2") as tar:
                    safe_members = _filter_safe_tar_members(
                        tar, extract_dir, max_file_size, max_total_size, max_files
                    )
                    tar.extractall(extract_dir, members=safe_members)
            elif archive_format == "tar.xz":
                with tarfile.open(cookbook_path, "r:xz") as tar:
                    safe_members = _filter_safe_tar_members(
                        tar, extract_dir, max_file_size, max_total_size, max_files
                    )
                    tar.extractall(extract_dir, members=safe_members)
            elif archive_format == "tar":
                with tarfile.open(cookbook_path, "r") as tar:
                    safe_members = _filter_safe_tar_members(
                        tar, extract_dir, max_file_size, max_total_size, max_files
                    )
                    tar.extractall(extract_dir, members=safe_members)

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


def _filter_safe_tar_members(
    tar, extract_dir: Path, max_file_size: int, max_total_size: int, max_files: int
):
    """
    Filter tar archive members to only include safe ones.

    Args:
        tar: Opened tar archive.
        extract_dir: Directory where files will be extracted.
        max_file_size: Maximum size per file in bytes.
        max_total_size: Maximum total extraction size in bytes.
        max_files: Maximum number of files to extract.

    Returns:
        List of safe tar members to extract.

    """
    safe_members = []
    total_size = 0

    for file_count, member in enumerate(tar.getmembers()):
        validation_result = _validate_tar_member(
            member,
            extract_dir,
            file_count,
            total_size,
            max_file_size,
            max_total_size,
            max_files,
        )

        if validation_result["warning"]:
            st.warning(validation_result["warning"])

        if validation_result["should_stop"]:
            break

        if validation_result["is_safe"]:
            safe_members.append(member)
            total_size = validation_result["new_total_size"]

    return safe_members


def _detect_archive_format(file_path: Path) -> str | None:
    """
    Detect archive format by attempting to open with different methods.

    Args:
        file_path: Path to the archive file.

    Returns:
        Format string: 'zip', 'tar.gz', 'tar.bz2', 'tar.xz', 'tar',
        or None if format cannot be detected.

    """
    # Try ZIP first
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            # Verify it's a valid ZIP by checking if we can list contents
            _ = zf.namelist()
            return "zip"
    except (zipfile.BadZipFile, OSError):
        pass

    # Try gzipped tar (.tar.gz, .tgz)
    try:
        with tarfile.open(file_path, "r:gz") as tf:
            # Verify it's valid by trying to get members
            _ = tf.getmembers()
            return "tar.gz"
    except (tarfile.ReadError, OSError):
        pass

    # Try bzip2 compressed tar (.tar.bz2, .tbz2)
    try:
        with tarfile.open(file_path, "r:bz2") as tf:
            # Verify it's valid by trying to get members
            _ = tf.getmembers()
            return "tar.bz2"
    except (tarfile.ReadError, OSError):
        pass

    # Try xz compressed tar (.tar.xz, .txz)
    try:
        with tarfile.open(file_path, "r:xz") as tf:
            # Verify it's valid by trying to get members
            _ = tf.getmembers()
            return "tar.xz"
    except (tarfile.ReadError, OSError):
        pass

    # Try plain tar
    try:
        with tarfile.open(file_path, "r") as tf:
            # Verify it's valid by trying to get members
            _ = tf.getmembers()
            return "tar"
    except (tarfile.ReadError, OSError):
        pass

    return None


def _extract_zip_safely(
    zip_path: Path,
    extract_dir: Path,
    max_file_size: int,
    max_total_size: int,
    max_files: int,
) -> None:
    """
    Safely extract ZIP archive with security validations.

    Args:
        zip_path: Path to ZIP archive.
        extract_dir: Directory to extract to.
        max_file_size: Maximum size per file in bytes.
        max_total_size: Maximum total extraction size in bytes.
        max_files: Maximum number of files to extract.

    """
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        safe_members = _filter_safe_zip_members(
            zip_ref, max_files, max_file_size, max_total_size
        )
        _extract_zip_members(zip_ref, extract_dir, safe_members)


def _filter_safe_zip_members(
    zip_ref: zipfile.ZipFile, max_files: int, max_file_size: int, max_total_size: int
) -> list[zipfile.ZipInfo]:
    """
    Filter ZIP archive members to only include safe ones.

    Args:
        zip_ref: Open ZipFile reference.
        max_files: Maximum number of files.
        max_file_size: Maximum size per file in bytes.
        max_total_size: Maximum total extraction size in bytes.

    Returns:
        List of safe ZipInfo members to extract.

    """
    safe_members = []
    total_size = 0

    for file_count, info in enumerate(zip_ref.filelist, start=1):
        # Check file count limit
        if file_count > max_files:
            st.warning(f"Too many files in archive (limit: {max_files})")
            break

        # Check individual file size limit
        if info.file_size > max_file_size:
            st.warning(f"Skipping large file: {info.filename}")
            continue

        # Check total size limit
        if total_size + info.file_size > max_total_size:
            st.warning(f"Total extraction size limit reached ({max_total_size} bytes)")
            break

        # Check for path traversal attacks
        if ".." in info.filename or info.filename.startswith("/"):
            st.warning(f"Skipping file with suspicious path: {info.filename}")
            continue

        # File is safe, add to list
        safe_members.append(info)
        total_size += info.file_size

    return safe_members


def _extract_zip_members(
    zip_ref: zipfile.ZipFile, extract_dir: Path, safe_members: list[zipfile.ZipInfo]
) -> None:
    """
    Extract ZIP members safely after validation.

    Args:
        zip_ref: Open ZipFile reference.
        extract_dir: Directory to extract to.
        safe_members: List of validated safe members to extract.

    """
    for info in safe_members:
        try:
            _extract_single_zip_member(zip_ref, info, extract_dir)
        except Exception as e:
            st.warning(f"Failed to extract {info.filename}: {e}")


def _extract_single_zip_member(
    zip_ref: zipfile.ZipFile, info: zipfile.ZipInfo, extract_dir: Path
) -> None:
    """
    Extract a single ZIP member with path validation.

    Args:
        zip_ref: Open ZipFile reference.
        info: ZipInfo for the member.
        extract_dir: Directory to extract to.

    """
    member_path = (extract_dir / info.filename).resolve()

    if not str(member_path).startswith(str(extract_dir.resolve())):
        st.warning(f"Skipping file outside extraction directory: {info.filename}")
        return

    if info.is_dir():
        member_path.mkdir(parents=True, exist_ok=True)
    else:
        member_path.parent.mkdir(parents=True, exist_ok=True)
        with zip_ref.open(info) as source, member_path.open("wb") as target:
            while True:
                chunk = source.read(8192)
                if not chunk:
                    break
                target.write(chunk)


def _validate_tar_member(
    member,
    extract_dir: Path,
    file_count: int,
    total_size: int,
    max_file_size: int,
    max_total_size: int,
    max_files: int,
) -> dict:
    """
    Validate a tar archive member for safe extraction.

    Args:
        member: Tar member to validate.
        extract_dir: Directory where files will be extracted.
        file_count: Current file count.
        total_size: Current total size in bytes.
        max_file_size: Maximum size per file in bytes.
        max_total_size: Maximum total extraction size in bytes.
        max_files: Maximum number of files.

    Returns:
        Dictionary with validation results:
        - is_safe: Whether member should be extracted
        - new_total_size: Updated total size
        - warning: Warning message if any
        - should_stop: Whether to stop processing more members

    """
    # Check file count limit
    if file_count >= max_files:
        return {
            "is_safe": False,
            "new_total_size": total_size,
            "warning": (
                f"Extraction stopped: archive contains more than {max_files} files"
            ),
            "should_stop": True,
        }

    # Check individual file size
    if member.size > max_file_size:
        size_mb = member.size / (1024 * 1024)
        limit_mb = max_file_size / (1024 * 1024)
        return {
            "is_safe": False,
            "new_total_size": total_size,
            "warning": (
                f"Skipping large file {member.name}: "
                f"{size_mb:.1f}MB exceeds {limit_mb:.0f}MB limit"
            ),
            "should_stop": False,
        }

    # Check total extraction size
    new_total_size = total_size + member.size
    if new_total_size > max_total_size:
        limit_mb = max_total_size / (1024 * 1024)
        return {
            "is_safe": False,
            "new_total_size": total_size,
            "warning": f"Extraction stopped: total size exceeds {limit_mb:.0f}MB limit",
            "should_stop": True,
        }

    # Validate path security
    member_path = (extract_dir / member.name).resolve()
    if not str(member_path).startswith(str(extract_dir.resolve())):
        return {
            "is_safe": False,
            "new_total_size": total_size,
            "warning": f"Skipping potentially unsafe path: {member.name}",
            "should_stop": False,
        }

    # Validate symlink security
    if member.issym() or member.islnk():
        link_target = (extract_dir / member.linkname).resolve()
        if not str(link_target).startswith(str(extract_dir.resolve())):
            return {
                "is_safe": False,
                "new_total_size": total_size,
                "warning": f"Skipping unsafe symlink: {member.name}",
                "should_stop": False,
            }

    # Member is safe
    return {
        "is_safe": True,
        "new_total_size": new_total_size,
        "warning": None,
        "should_stop": False,
    }


def _show_conversion_history(storage_manager, blob_storage) -> None:
    """Show conversion history tab."""
    st.subheader("Conversion History")

    cookbook_filter, status_filter, limit = _get_conversion_filters()
    conversions = _get_conversion_history(storage_manager, cookbook_filter, limit)
    conversions = _filter_conversions_by_status(conversions, status_filter)

    if not conversions:
        st.info("No conversion history found. Start by converting a cookbook!")
        return

    _display_conversion_table(conversions)
    _display_conversion_downloads(storage_manager, blob_storage, conversions)


def _get_conversion_filters() -> tuple[str, str, int]:
    """Return filter values for conversion history."""
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

    return cookbook_filter, status_filter, limit


def _get_conversion_history(storage_manager, cookbook_filter: str, limit: int) -> list:
    """Return conversion history with optional cookbook filtering."""
    if cookbook_filter:
        return storage_manager.get_conversion_history(
            cookbook_name=cookbook_filter, limit=limit
        )
    return storage_manager.get_conversion_history(limit=limit)


def _filter_conversions_by_status(conversions: list, status_filter: str) -> list:
    """Filter conversion history by status when requested."""
    if status_filter == "All":
        return conversions
    return [
        conversion for conversion in conversions if conversion.status == status_filter
    ]


def _display_conversion_table(conversions: list) -> None:
    """Display conversion history in a table."""
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
    st.dataframe(df, width="stretch", hide_index=True)


def _display_conversion_downloads(
    storage_manager, blob_storage, conversions: list
) -> None:
    """Display conversion download and deletion actions."""
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

    if not selected_id:
        return

    selected = next(c for c in conversions if c.id == selected_id)
    if not selected.blob_storage_key:
        return

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

    _display_conversion_deletion(storage_manager, selected)


def _display_conversion_deletion(storage_manager, selected) -> None:
    """Display conversion deletion controls."""
    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        st.warning(
            "Deleting this conversion will remove it from history. "
            "This action cannot be undone."
        )
    with col2:
        if st.button(
            "Delete Conversion",
            type="secondary",
            key=f"delete_conversion_{selected.id}",
        ):
            if storage_manager.delete_conversion(selected.id):
                st.success("Conversion deleted successfully!")
                st.rerun()
            else:
                st.error("Failed to delete conversion.")


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
                label="Download Roles Archive",
                data=f.read(),
                file_name=f"{conversion.cookbook_name}_roles.tar.gz",
                mime="application/gzip",
                key=f"download_roles_{conversion.id}",
            )
    else:
        _create_and_display_zip_download(
            roles_path,
            f"{conversion.cookbook_name}_roles.zip",
            "Download Roles Archive",
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
                label="Download Repository Archive",
                data=f.read(),
                file_name=f"{conversion.cookbook_name}_repository.tar.gz",
                mime="application/gzip",
                key=f"download_repo_{conversion.id}",
            )
    else:
        _create_and_display_zip_download(
            repo_path,
            f"{conversion.cookbook_name}_repository.zip",
            "Download Repository Archive",
            f"download_repo_{conversion.id}",
        )


def _create_and_display_zip_download(
    source_path: Path, file_name: str, label: str, key: str
) -> None:
    """Create a ZIP archive from directory and display download button."""
    import io

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
