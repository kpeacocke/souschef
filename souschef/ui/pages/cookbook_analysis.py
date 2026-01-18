"""Cookbook Analysis Page for SousChef UI."""

import io
import json
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import streamlit as st

# Add the parent directory to the path so we can import souschef modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from souschef.assessment import parse_chef_migration_assessment
from souschef.converters.playbook import (
    generate_playbook_from_recipe,
    generate_playbook_from_recipe_with_ai,
)
from souschef.core.constants import METADATA_FILENAME
from souschef.parsers.metadata import parse_cookbook_metadata

# AI Settings
ANTHROPIC_PROVIDER = "Anthropic (Claude)"
OPENAI_PROVIDER = "OpenAI (GPT)"
LOCAL_PROVIDER = "Local Model"


def load_ai_settings():
    """Load AI settings from configuration file."""
    try:
        # Use /tmp/.souschef for container compatibility (tmpfs is writable)
        config_file = Path("/tmp/.souschef/ai_config.json")
        if config_file.exists():
            with config_file.open() as f:
                return json.load(f)
    except Exception:
        pass  # Ignore errors when loading config file; return empty dict as fallback
    return {}


# Constants for repeated strings
METADATA_STATUS_YES = "Yes"
METADATA_STATUS_NO = "No"
ANALYSIS_STATUS_ANALYSED = "Analysed"
ANALYSIS_STATUS_FAILED = "Failed"
METADATA_COLUMN_NAME = "Has Metadata"

# Security limits for archive extraction
MAX_ARCHIVE_SIZE = 100 * 1024 * 1024  # 100MB total
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB per file
MAX_FILES = 1000  # Maximum number of files
MAX_DEPTH = 10  # Maximum directory depth
BLOCKED_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".com",
    ".pif",
    ".scr",
    ".vbs",
    ".js",
    ".jar",
    # Note: .sh files are allowed as they are common in Chef cookbooks
}


def extract_archive(uploaded_file) -> tuple[Path, Path]:
    """
    Extract uploaded archive to a temporary directory with security checks.

    Returns:
        tuple: (temp_dir_path, cookbook_root_path)

    Implements multiple security measures to prevent:
    - Zip bombs (size limits, file count limits)
    - Path traversal attacks (../ validation)
    - Resource exhaustion (depth limits, size limits)
    - Malicious files (symlinks, executables blocked)

    """
    # Check initial file size
    file_size = len(uploaded_file.getbuffer())
    if file_size > MAX_ARCHIVE_SIZE:
        raise ValueError(
            f"Archive too large: {file_size} bytes (max: {MAX_ARCHIVE_SIZE})"
        )

    # Create temporary directory (will be cleaned up by caller)
    temp_dir = Path(tempfile.mkdtemp())
    temp_path = temp_dir

    # Save uploaded file
    archive_path = temp_path / uploaded_file.name
    with archive_path.open("wb") as f:
        f.write(uploaded_file.getbuffer())

    # Extract archive with security checks
    extraction_dir = temp_path / "extracted"
    extraction_dir.mkdir()

    _extract_archive_by_type(archive_path, extraction_dir, uploaded_file.name)

    # Find the root directory (should contain cookbooks)
    cookbook_root = _determine_cookbook_root(extraction_dir)

    return temp_dir, cookbook_root


def _extract_archive_by_type(
    archive_path: Path, extraction_dir: Path, filename: str
) -> None:
    """Extract archive based on file extension."""
    if filename.endswith(".zip"):
        _extract_zip_securely(archive_path, extraction_dir)
    elif filename.endswith((".tar.gz", ".tgz")):
        _extract_tar_securely(archive_path, extraction_dir, gzipped=True)
    elif filename.endswith(".tar"):
        _extract_tar_securely(archive_path, extraction_dir, gzipped=False)
    else:
        raise ValueError(f"Unsupported archive format: {filename}")


def _determine_cookbook_root(extraction_dir: Path) -> Path:
    """Determine the root directory containing cookbooks."""
    subdirs = [d for d in extraction_dir.iterdir() if d.is_dir()]

    # Check if this looks like a single cookbook archive (contains typical
    # cookbook dirs)
    cookbook_dirs = {
        "recipes",
        "attributes",
        "templates",
        "files",
        "libraries",
        "definitions",
    }
    extracted_dirs = {d.name for d in subdirs}

    cookbook_root = extraction_dir

    if len(subdirs) > 1 and cookbook_dirs.intersection(extracted_dirs):
        # Case 1: Multiple cookbook directories at root level
        cookbook_root = _handle_multiple_cookbook_dirs(extraction_dir, subdirs)
    elif len(subdirs) == 1:
        # Case 2: Single directory - check if it contains cookbook components
        cookbook_root = _handle_single_cookbook_dir(
            extraction_dir, subdirs[0], cookbook_dirs
        )
    # else: Multiple directories that are not cookbook components - use extraction_dir

    return cookbook_root


def _handle_multiple_cookbook_dirs(extraction_dir: Path, subdirs: list) -> Path:
    """Handle case where multiple cookbook directories are at root level."""
    synthetic_cookbook_dir = extraction_dir / "cookbook"
    synthetic_cookbook_dir.mkdir(exist_ok=True)

    # Move all extracted directories into the synthetic cookbook
    for subdir in subdirs:
        if subdir.name in {
            "recipes",
            "attributes",
            "templates",
            "files",
            "libraries",
            "definitions",
        }:
            shutil.move(str(subdir), str(synthetic_cookbook_dir / subdir.name))

    # Create a basic metadata.rb file
    metadata_content = """name 'extracted_cookbook'
maintainer 'SousChef'
maintainer_email 'souschef@example.com'
license 'All rights reserved'
description 'Automatically extracted cookbook from archive'
version '1.0.0'
"""
    (synthetic_cookbook_dir / METADATA_FILENAME).write_text(metadata_content)

    return extraction_dir


def _handle_single_cookbook_dir(
    extraction_dir: Path, single_dir: Path, cookbook_dirs: set
) -> Path:
    """Handle case where single directory contains cookbook components."""
    single_dir_contents = {d.name for d in single_dir.iterdir() if d.is_dir()}

    if cookbook_dirs.intersection(single_dir_contents):
        # This single directory contains cookbook components - treat it as a cookbook
        # Check if it already has metadata.rb
        if not (single_dir / METADATA_FILENAME).exists():
            # Create synthetic metadata.rb
            metadata_content = f"""name '{single_dir.name}'
maintainer 'SousChef'
maintainer_email 'souschef@example.com'
license 'All rights reserved'
description 'Automatically extracted cookbook from archive'
version '1.0.0'
"""
            (single_dir / METADATA_FILENAME).write_text(metadata_content)

        return extraction_dir
    else:
        # Single directory that doesn't contain cookbook components
        return single_dir


def _extract_zip_securely(archive_path: Path, extraction_dir: Path) -> None:
    """Extract ZIP archive with security checks."""
    total_size = 0

    with zipfile.ZipFile(archive_path, "r") as zip_ref:
        # Pre-scan for security issues
        for file_count, info in enumerate(zip_ref.filelist, start=1):
            _validate_zip_file_security(info, file_count, total_size)
            total_size += info.file_size

        # Safe extraction with manual path handling
        for info in zip_ref.filelist:
            # Construct safe relative path
            safe_path = _get_safe_extraction_path(info.filename, extraction_dir)

            if info.is_dir():
                # Create directory
                safe_path.mkdir(parents=True, exist_ok=True)
            else:
                # Create parent directories if needed
                safe_path.parent.mkdir(parents=True, exist_ok=True)
                # Extract file content manually
                with zip_ref.open(info) as source, safe_path.open("wb") as target:
                    # Read in chunks to control memory usage
                    while True:
                        chunk = source.read(8192)
                        if not chunk:
                            break
                        target.write(chunk)


def _validate_zip_file_security(info, file_count: int, total_size: int) -> None:
    """Validate a single ZIP file entry for security issues."""
    file_count += 1
    if file_count > MAX_FILES:
        raise ValueError(f"Too many files in archive: {file_count} (max: {MAX_FILES})")

    # Check file size
    if info.file_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {info.filename} ({info.file_size} bytes)")

    total_size += info.file_size
    if total_size > MAX_ARCHIVE_SIZE:
        raise ValueError(f"Total archive size too large: {total_size} bytes")

    # Check for path traversal
    if _has_path_traversal(info.filename):
        raise ValueError(f"Path traversal detected: {info.filename}")

    # Check directory depth
    if _exceeds_depth_limit(info.filename):
        raise ValueError(f"Directory depth too deep: {info.filename}")

    # Check for blocked file extensions
    if _is_blocked_extension(info.filename):
        raise ValueError(f"Blocked file type: {info.filename}")

    # Check for symlinks
    if _is_symlink(info):
        raise ValueError(f"Symlinks not allowed: {info.filename}")


def _extract_tar_securely(
    archive_path: Path, extraction_dir: Path, gzipped: bool
) -> None:
    """Extract TAR archive with security checks."""
    mode = "r:gz" if gzipped else "r"

    try:
        with tarfile.open(str(archive_path), mode=mode) as tar_ref:  # type: ignore[call-overload]
            members = tar_ref.getmembers()
            _pre_scan_tar_members(members)
            _extract_tar_members(tar_ref, members, extraction_dir)
    except tarfile.TarError as e:
        raise ValueError(f"Invalid or corrupted TAR archive: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to process TAR archive: {e}") from e


def _pre_scan_tar_members(members):
    """Pre-scan TAR members for security issues and accumulate totals."""
    total_size = 0
    for file_count, member in enumerate(members, start=1):
        total_size += member.size
        _validate_tar_file_security(member, file_count, total_size)


def _extract_tar_members(tar_ref, members, extraction_dir):
    """Extract validated TAR members to the extraction directory."""
    for member in members:
        safe_path = _get_safe_extraction_path(member.name, extraction_dir)
        if member.isdir():
            safe_path.mkdir(parents=True, exist_ok=True)
        else:
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            _extract_file_content(tar_ref, member, safe_path)


def _extract_file_content(tar_ref, member, safe_path):
    """Extract the content of a single TAR member to a file."""
    source = tar_ref.extractfile(member)
    if source:
        with source, safe_path.open("wb") as target:
            while True:
                chunk = source.read(8192)
                if not chunk:
                    break
                target.write(chunk)


def _validate_tar_file_security(member, file_count: int, total_size: int) -> None:
    """Validate a single TAR file entry for security issues."""
    file_count += 1
    if file_count > MAX_FILES:
        raise ValueError(f"Too many files in archive: {file_count} (max: {MAX_FILES})")

    # Check file size
    if member.size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {member.name} ({member.size} bytes)")

    total_size += member.size
    if total_size > MAX_ARCHIVE_SIZE:
        raise ValueError(f"Total archive size too large: {total_size} bytes")

    # Check for path traversal
    if _has_path_traversal(member.name):
        raise ValueError(f"Path traversal detected: {member.name}")

    # Check directory depth
    if _exceeds_depth_limit(member.name):
        raise ValueError(f"Directory depth too deep: {member.name}")

    # Check for blocked file extensions
    if _is_blocked_extension(member.name):
        raise ValueError(f"Blocked file type: {member.name}")

    # Check for symlinks
    if member.issym() or member.islnk():
        raise ValueError(f"Symlinks not allowed: {member.name}")

    # Check for device files, fifos, etc.
    if not member.isfile() and not member.isdir():
        raise ValueError(f"Unsupported file type: {member.name} (type: {member.type})")


def _has_path_traversal(filename: str) -> bool:
    """Check if filename contains path traversal attempts."""
    return ".." in filename


def _exceeds_depth_limit(filename: str) -> bool:
    """Check if filename exceeds directory depth limit."""
    return filename.count("/") > MAX_DEPTH or filename.count("\\") > MAX_DEPTH


def _is_blocked_extension(filename: str) -> bool:
    """Check if filename has a blocked extension."""
    file_ext = Path(filename).suffix.lower()
    return file_ext in BLOCKED_EXTENSIONS


def _is_symlink(info) -> bool:
    """Check if ZIP file info indicates a symlink."""
    return bool(info.external_attr & 0xA000 == 0xA000)  # Symlink flag


def _get_safe_extraction_path(filename: str, extraction_dir: Path) -> Path:
    """Get a safe path for extraction that prevents directory traversal."""
    # Reject paths with directory traversal attempts or absolute paths
    if (
        ".." in filename
        or filename.startswith("/")
        or "\\" in filename
        or ":" in filename
    ):
        raise ValueError(f"Path traversal or absolute path detected: {filename}")

    # Normalize path separators and remove leading/trailing slashes
    normalized = filename.replace("\\", "/").strip("/")

    # Split into components and filter out dangerous ones
    parts: list[str] = []
    for part in normalized.split("/"):
        if part == "" or part == ".":
            continue
        elif part == "..":
            # Remove parent directory if we have one
            if parts:
                parts.pop()
        else:
            parts.append(part)

    # Join parts back and resolve against extraction_dir
    safe_path = extraction_dir / "/".join(parts)

    # Ensure the final path is still within extraction_dir
    try:
        safe_path.resolve().relative_to(extraction_dir.resolve())
    except ValueError:
        raise ValueError(f"Path traversal detected: {filename}") from None

    return safe_path


def create_results_archive(results: list, cookbook_path: str) -> bytes:
    """Create a ZIP archive containing analysis results."""
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Add JSON summary
        json_data = pd.DataFrame(results).to_json(indent=2)
        zip_file.writestr("analysis_results.json", json_data)

        # Add individual cookbook reports
        for result in results:
            if result["status"] == ANALYSIS_STATUS_ANALYSED:
                report_content = f"""# Cookbook Analysis Report: {result["name"]}

## Metadata
- **Version**: {result["version"]}
- **Maintainer**: {result["maintainer"]}
- **Dependencies**: {result["dependencies"]}
- **Complexity**: {result["complexity"]}
- **Estimated Hours**: {result["estimated_hours"]:.1f}

## Recommendations
{result["recommendations"]}

## Source Path
{result["path"]}
"""
                zip_file.writestr(f"{result['name']}_report.md", report_content)

        # Add summary report
        successful = len(
            [r for r in results if r["status"] == ANALYSIS_STATUS_ANALYSED]
        )
        total_hours = sum(r.get("estimated_hours", 0) for r in results)

        summary_content = f"""# SousChef Cookbook Analysis Summary

## Overview
- **Cookbooks Analysed**: {len(results)}

- **Successfully Analysed**: {successful}

- **Total Estimated Hours**: {total_hours:.1f}
- **Source**: {cookbook_path}

## Results Summary
"""
        for result in results:
            status_icon = "✅" if result["status"] == ANALYSIS_STATUS_ANALYSED else "❌"
            summary_content += f"- {status_icon} {result['name']}: {result['status']}"
            if result["status"] == ANALYSIS_STATUS_ANALYSED:
                summary_content += (
                    f" ({result['estimated_hours']:.1f} hours, "
                    f"{result['complexity']} complexity)"
                )
            summary_content += "\n"

        zip_file.writestr("analysis_summary.md", summary_content)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def show_cookbook_analysis_page():
    """Show the cookbook analysis page."""
    _setup_cookbook_analysis_ui()

    # Initialise session state for analysis results

    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None
        st.session_state.analysis_cookbook_path = None
        st.session_state.total_cookbooks = 0
        st.session_state.temp_dir = None

    # Check if we have analysis results to display
    if st.session_state.analysis_results is not None:
        _display_analysis_results(
            st.session_state.analysis_results,
            st.session_state.total_cookbooks,
        )
        return

    # Check if we have an uploaded file from the dashboard
    if "uploaded_file_data" in st.session_state:
        _handle_dashboard_upload()
        return

    # Input method selection
    input_method = st.radio(
        "Choose Input Method",
        ["Upload Archive", "Directory Path"],
        horizontal=True,
        help="Select how to provide cookbooks for analysis",
    )

    cookbook_path = None
    temp_dir = None
    uploaded_file = None

    if input_method == "Directory Path":
        cookbook_path = _get_cookbook_path_input()
    else:
        uploaded_file = _get_archive_upload_input()
        if uploaded_file:
            try:
                with st.spinner("Extracting archive..."):
                    temp_dir, cookbook_path = extract_archive(uploaded_file)
                    # Store temp_dir in session state to prevent premature cleanup
                    st.session_state.temp_dir = temp_dir
                st.success("Archive extracted successfully to temporary location")
            except Exception as e:
                st.error(f"Failed to extract archive: {e}")
                return

    try:
        if cookbook_path:
            _validate_and_list_cookbooks(cookbook_path)

        _display_instructions()
    finally:
        # Only clean up temp_dir if it wasn't stored in session state
        # (i.e., if we didn't successfully extract an archive)
        if temp_dir and temp_dir.exists() and st.session_state.temp_dir != temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


def _setup_cookbook_analysis_ui():
    """Set up the cookbook analysis page header."""
    st.title("SousChef - Cookbook Analysis")
    st.markdown("""
    Analyse your Chef cookbooks and get detailed migration assessments for
    converting to Ansible playbooks.

    Upload a cookbook archive or specify a directory path to begin analysis.
    """)


def _get_cookbook_path_input():
    """Get the cookbook path input from the user."""
    return st.text_input(
        "Cookbook Directory Path",
        placeholder="cookbooks/ or ../shared/cookbooks/",
        help="Enter a path to your Chef cookbooks directory. "
        "Relative paths (e.g., 'cookbooks/') and absolute paths inside the workspace "
        "(e.g., '/workspaces/souschef/cookbooks/') are allowed.",
    )


def _get_archive_upload_input():
    """Get archive upload input from the user."""
    uploaded_file = st.file_uploader(
        "Upload Cookbook Archive",
        type=["zip", "tar.gz", "tgz", "tar"],
        help="Upload a ZIP or TAR archive containing your Chef cookbooks",
    )
    return uploaded_file


def _validate_and_list_cookbooks(cookbook_path):
    """Validate the cookbook path and list available cookbooks."""
    safe_dir = _get_safe_cookbook_directory(cookbook_path)
    if safe_dir is None:
        return

    if safe_dir.exists() and safe_dir.is_dir():
        _list_and_display_cookbooks(safe_dir)
    else:
        st.error(f"Directory not found: {safe_dir}")


def _get_safe_cookbook_directory(cookbook_path):
    """
    Resolve the user-provided cookbook path to a safe directory.

    The path is validated and normalized to prevent directory traversal
    outside the allowed root before any path operations.
    """
    try:
        base_dir = Path.cwd().resolve()
        temp_dir = Path(tempfile.gettempdir()).resolve()

        path_str = str(cookbook_path).strip()

        # Reject obviously malicious patterns
        if "\x00" in path_str or ":\\" in path_str or "\\" in path_str:
            st.error(
                "❌ Invalid path: Path contains null bytes or backslashes, "
                "which are not allowed."
            )
            return None

        # Reject paths with directory traversal attempts
        if ".." in path_str:
            st.error(
                "❌ Invalid path: Path contains '..' which is not allowed "
                "for security reasons."
            )
            return None

        user_path = Path(path_str)

        # Resolve the path safely
        if user_path.is_absolute():
            resolved_path = user_path.resolve()
        else:
            resolved_path = (base_dir / user_path).resolve()

        # Check if the resolved path is within allowed directories
        try:
            resolved_path.relative_to(base_dir)
            return resolved_path
        except ValueError:
            pass

        try:
            resolved_path.relative_to(temp_dir)
            return resolved_path
        except ValueError:
            st.error(
                "❌ Invalid path: The resolved path is outside the allowed "
                "directories (workspace or temporary directory). Paths cannot go above "
                "the workspace root for security reasons."
            )
            return None

    except Exception as exc:
        st.error(f"❌ Invalid path: {exc}. Please enter a valid relative path.")
        return None


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
        cookbook_info = _analyse_cookbook_metadata(cookbook)
        cookbook_data.append(cookbook_info)
    return cookbook_data


def _analyse_cookbook_metadata(cookbook):
    """Analyse metadata for a single cookbook."""
    metadata_file = cookbook / METADATA_FILENAME
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


def _normalize_description(description: Any) -> str:
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


def _handle_cookbook_selection(cookbook_path: str, cookbook_data: list):
    """Handle selection of cookbooks for analysis."""
    st.subheader("Select Cookbooks to Analyse")

    # Create a multiselect widget for cookbook selection
    cookbook_names = [cookbook["Name"] for cookbook in cookbook_data]
    selected_cookbooks = st.multiselect(
        "Choose cookbooks to analyse:",
        options=cookbook_names,
        default=[],  # No default selection
        help="Select one or more cookbooks to analyse for migration to Ansible",
    )

    # Show selection summary
    if selected_cookbooks:
        st.info(f"Selected {len(selected_cookbooks)} cookbook(s) for analysis")

        # Analyse button
        if st.button("Analyse Selected Cookbooks", type="primary"):
            analyse_selected_cookbooks(cookbook_path, selected_cookbooks)
    else:
        st.info("Please select at least one cookbook to analyse")


def _handle_dashboard_upload():
    """Handle file uploaded from the dashboard."""
    # Create a file-like object from the stored data
    file_data = st.session_state.uploaded_file_data
    file_name = st.session_state.uploaded_file_name

    # Create a file-like object that mimics the UploadedFile interface
    class MockUploadedFile:
        def __init__(self, data, name, mime_type):
            self.data = data
            self.name = name
            self.type = mime_type

        def getbuffer(self):
            return self.data

        def getvalue(self):
            return self.data

    mock_file = MockUploadedFile(
        file_data, file_name, st.session_state.uploaded_file_type
    )

    # Display upload info
    st.info(f"📁 Using file uploaded from Dashboard: {file_name}")

    # Add option to clear and upload a different file
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button(
            "Use Different File", help="Clear this file and upload a different one"
        ):
            # Clear the uploaded file from session state
            del st.session_state.uploaded_file_data
            del st.session_state.uploaded_file_name
            del st.session_state.uploaded_file_type
            st.rerun()

    with col2:
        if st.button("Back to Dashboard", help="Return to dashboard"):
            st.session_state.current_page = "Dashboard"
            st.rerun()

    # Process the file
    try:
        with st.spinner("Extracting archive..."):
            temp_dir, cookbook_path = extract_archive(mock_file)
            # Store temp_dir in session state to prevent premature cleanup
            st.session_state.temp_dir = temp_dir
        st.success("Archive extracted successfully!")

        # Validate and list cookbooks
        if cookbook_path:
            _validate_and_list_cookbooks(cookbook_path)

    except Exception as e:
        st.error(f"Failed to process uploaded file: {e}")
        # Clear the uploaded file on error
        if "uploaded_file_data" in st.session_state:
            del st.session_state.uploaded_file_data
            del st.session_state.uploaded_file_name
            del st.session_state.uploaded_file_type


def _display_instructions():
    """Display usage instructions."""
    with st.expander("How to Use"):
        st.markdown("""
        ## Input Methods

        ### Directory Path
        1. **Enter Cookbook Path**: Provide a **relative path** to your cookbooks
           (absolute paths not allowed)
        2. **Review Cookbooks**: The interface will list all cookbooks with metadata
        3. **Select Cookbooks**: Choose which cookbooks to analyse
        4. **Run Analysis**: Click "Analyse Selected Cookbooks" to get detailed insights

        **Path Examples:**
        - `cookbooks/` - subdirectory in current workspace
        - `../shared/cookbooks/` - parent directory
        - `./my-cookbooks/` - explicit current directory

        ### Archive Upload
        1. **Upload Archive**: Upload a ZIP or TAR archive containing your cookbooks
        2. **Automatic Extraction**: The system will extract and analyse the archive

        3. **Review Cookbooks**: Interface will list all cookbooks found in archive
        4. **Select Cookbooks**: Choose which cookbooks to analyse
        5. **Run Analysis**: Click "Analyse Selected Cookbooks" to get insights


        ## Expected Structure
        ```
        cookbooks/ or archive.zip/
        ├── nginx/
        │   ├── metadata.rb
        │   ├── recipes/
        │   └── attributes/
        ├── apache2/
        │   └── metadata.rb
        └── mysql/
            └── metadata.rb
        ```

        ## Supported Archive Formats
        - ZIP (.zip)
        - TAR (.tar)
        - GZIP-compressed TAR (.tar.gz, .tgz)
        """)


def analyse_selected_cookbooks(cookbook_path: str, selected_cookbooks: list[str]):
    """Analyse the selected cookbooks and store results in session state."""
    st.subheader("Analysis Results")

    progress_bar, status_text = _setup_analysis_progress()
    results = _perform_cookbook_analysis(
        cookbook_path, selected_cookbooks, progress_bar, status_text
    )

    _cleanup_progress_indicators(progress_bar, status_text)

    # Store results in session state
    st.session_state.analysis_results = results
    st.session_state.analysis_cookbook_path = cookbook_path
    st.session_state.total_cookbooks = len(selected_cookbooks)

    # Trigger rerun to display results
    st.rerun()


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
            analysis_result = _analyse_single_cookbook(cookbook_name, cookbook_dir)
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


def _analyse_single_cookbook(cookbook_name, cookbook_dir):
    """Analyse a single cookbook."""
    try:
        assessment = parse_chef_migration_assessment(str(cookbook_dir))
        metadata = parse_cookbook_metadata(str(cookbook_dir / METADATA_FILENAME))

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
        "status": ANALYSIS_STATUS_ANALYSED,
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
    """Display the complete analysis results."""
    # Add a back button to return to analysis selection
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("⬅️ Analyse More Cookbooks", help="Return to cookbook selection"):
            # Clear session state to go back to selection
            st.session_state.analysis_results = None
            st.session_state.analysis_cookbook_path = None
            st.session_state.total_cookbooks = 0
            # Clean up temporary directory when going back
            if st.session_state.temp_dir and st.session_state.temp_dir.exists():
                shutil.rmtree(st.session_state.temp_dir, ignore_errors=True)
                st.session_state.temp_dir = None
            st.rerun()

    with col2:
        st.subheader("Analysis Results")

    _display_analysis_summary(results, total_cookbooks)
    _display_results_table(results)
    _display_detailed_analysis(results)
    _display_download_option(results)


def _display_download_option(results):
    """Display download options for analysis results."""
    st.subheader("Download Options")

    successful_results = [r for r in results if r["status"] == ANALYSIS_STATUS_ANALYSED]

    if not successful_results:
        st.info("No successfully analysed cookbooks available for download.")

        return

    col1, _col2 = st.columns(2)

    with col1:
        # Download analysis report
        analysis_data = _create_analysis_report(results)
        st.download_button(
            label="Download Analysis Report",
            data=analysis_data,
            file_name="cookbook_analysis_report.json",
            mime="application/json",
            help="Download detailed analysis results as JSON",
        )

    # Convert to Ansible Playbooks button - moved outside columns for better reliability
    if st.button(
        "Convert to Ansible Playbooks",
        type="primary",
        help="Convert analysed cookbooks to Ansible playbooks and download as ZIP",
    ):
        # Check AI configuration status
        ai_config = load_ai_settings()
        ai_available = (
            ai_config.get("provider")
            and ai_config.get("provider") != LOCAL_PROVIDER
            and ai_config.get("api_key")
        )

        if ai_available:
            provider = ai_config.get("provider", "Unknown")
            model = ai_config.get("model", "Unknown")
            st.info(f"🤖 Using AI-enhanced conversion with {provider} ({model})")
        else:
            st.info(
                "⚙️ Using deterministic conversion. Configure AI settings "
                "for enhanced results."
            )

        _convert_and_download_playbooks(results)


def _display_analysis_summary(results, total_cookbooks):
    """Display summary metrics for the analysis."""
    col1, col2, col3 = st.columns(3)

    with col1:
        successful = len(
            [r for r in results if r["status"] == ANALYSIS_STATUS_ANALYSED]
        )
        st.metric("Successfully Analysed", f"{successful}/{total_cookbooks}")

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
    st.dataframe(df, width="stretch")


def _display_detailed_analysis(results):
    """Display detailed analysis for each cookbook."""
    st.subheader("Detailed Analysis")

    for result in results:
        if result["status"] == ANALYSIS_STATUS_ANALYSED:
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


def _convert_and_download_playbooks(results):
    """Convert analysed cookbooks to Ansible playbooks and provide download."""
    successful_results = [r for r in results if r["status"] == ANALYSIS_STATUS_ANALYSED]

    if not successful_results:
        st.warning("No successfully analysed cookbooks to convert.")
        return

    with st.spinner("Converting cookbooks to Ansible playbooks..."):
        playbooks = []

        for result in successful_results:
            playbook_data = _convert_single_cookbook(result)
            if playbook_data:
                playbooks.append(playbook_data)

    if playbooks:
        # Save converted playbooks to temporary directory for validation
        try:
            output_dir = Path(tempfile.mkdtemp(prefix="souschef_converted_"))
            for playbook in playbooks:
                # Sanitize filename
                filename = f"{playbook['cookbook_name']}.yml"
                (output_dir / filename).write_text(playbook["playbook_content"])

            # Store path in session state for validation page
            st.session_state.converted_playbooks_path = str(output_dir)
            st.success("Playbooks converted and staged for validation.")
        except Exception as e:
            st.warning(f"Could not stage playbooks for validation: {e}")

    _handle_playbook_download(playbooks)


def _convert_single_cookbook(result):
    """Convert a single cookbook to Ansible playbook."""
    cookbook_dir = Path(result["path"])
    recipe_file = _find_recipe_file(cookbook_dir, result["name"])

    if not recipe_file:
        return None

    try:
        # Check if AI-enhanced conversion is available and enabled
        ai_config = load_ai_settings()
        use_ai = (
            ai_config.get("provider")
            and ai_config.get("provider") != LOCAL_PROVIDER
            and ai_config.get("api_key")
        )

        if use_ai:
            # Use AI-enhanced conversion
            # Map provider display names to API provider strings
            provider_mapping = {
                "Anthropic Claude": "anthropic",
                "Anthropic (Claude)": "anthropic",
                "OpenAI": "openai",
                "OpenAI (GPT)": "openai",
                "IBM Watsonx": "watson",
                "Red Hat Lightspeed": "lightspeed",
            }
            provider_name = ai_config.get("provider", "")
            ai_provider = provider_mapping.get(
                provider_name, provider_name.lower().replace(" ", "_")
            )

            playbook_content = generate_playbook_from_recipe_with_ai(
                str(recipe_file),
                ai_provider=ai_provider,
                api_key=ai_config.get("api_key", ""),
                model=ai_config.get("model", "claude-3-5-sonnet-20241022"),
                temperature=ai_config.get("temperature", 0.7),
                max_tokens=ai_config.get("max_tokens", 4000),
                project_id=ai_config.get("project_id", ""),
                base_url=ai_config.get("base_url", ""),
            )
        else:
            # Use deterministic conversion
            playbook_content = generate_playbook_from_recipe(str(recipe_file))

        if not playbook_content.startswith("Error"):
            return {
                "cookbook_name": result["name"],
                "playbook_content": playbook_content,
                "recipe_file": recipe_file.name,
                "conversion_method": "AI-enhanced" if use_ai else "Deterministic",
            }
        else:
            st.warning(f"Failed to convert {result['name']}: {playbook_content}")
            return None
    except Exception as e:
        st.warning(f"Failed to convert {result['name']}: {e}")
        return None


def _find_recipe_file(cookbook_dir, cookbook_name):
    """Find the appropriate recipe file for a cookbook."""
    recipes_dir = cookbook_dir / "recipes"
    if not recipes_dir.exists():
        st.warning(f"No recipes directory found in {cookbook_name}")
        return None

    recipe_files = list(recipes_dir.glob("*.rb"))
    if not recipe_files:
        st.warning(f"No recipe files found in {cookbook_name}")
        return None

    # Use the default.rb recipe if available, otherwise first recipe
    default_recipe = recipes_dir / "default.rb"
    return default_recipe if default_recipe.exists() else recipe_files[0]


def _handle_playbook_download(playbooks):
    """Handle the download of generated playbooks."""
    if not playbooks:
        st.error("No playbooks were successfully generated.")
        return

    # Create ZIP archive with all playbooks
    playbook_archive = _create_playbook_archive(playbooks)

    st.success(
        f"Successfully converted {len(playbooks)} cookbooks to Ansible playbooks!"
    )

    # Provide download button
    st.download_button(
        label="Download Ansible Playbooks",
        data=playbook_archive,
        file_name="ansible_playbooks.zip",
        mime="application/zip",
        help="Download ZIP archive containing all generated Ansible playbooks",
    )

    # Show preview of generated playbooks
    with st.expander("Preview Generated Playbooks"):
        for playbook in playbooks:
            conversion_badge = (
                "🤖 AI-Enhanced"
                if playbook.get("conversion_method") == "AI-enhanced"
                else "⚙️ Deterministic"
            )
            st.subheader(
                f"{playbook['cookbook_name']} ({conversion_badge}) - "
                f"from {playbook['recipe_file']}"
            )
            st.code(
                playbook["playbook_content"][:1000] + "..."
                if len(playbook["playbook_content"]) > 1000
                else playbook["playbook_content"],
                language="yaml",
            )
            st.divider()


def _create_playbook_archive(playbooks):
    """Create a ZIP archive containing all generated Ansible playbooks."""
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Add individual playbook files
        for playbook in playbooks:
            playbook_filename = f"{playbook['cookbook_name']}.yml"
            zip_file.writestr(playbook_filename, playbook["playbook_content"])

        # Add a summary README
        readme_content = f"""# Ansible Playbooks Generated by SousChef

This archive contains {len(playbooks)} Ansible playbooks converted from Chef cookbooks.

## Contents:
"""

        for playbook in playbooks:
            conversion_method = playbook.get("conversion_method", "Deterministic")
            readme_content += (
                f"- {playbook['cookbook_name']}.yml "
                f"(converted from {playbook['recipe_file']}, "
                f"method: {conversion_method})\n"
            )

        readme_content += """

## Usage:
Run these playbooks with Ansible:
  ansible-playbook <playbook_name>.yml

## Notes:
- These playbooks were automatically generated from Chef recipes
- Review and test the playbooks before using in production
- Some manual adjustments may be required for complex recipes
"""

        zip_file.writestr("README.md", readme_content)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def _create_analysis_report(results):
    """Create a JSON report of the analysis results."""
    report = {
        "analysis_summary": {
            "total_cookbooks": len(results),
            "successful_analyses": len(
                [r for r in results if r["status"] == ANALYSIS_STATUS_ANALYSED]
            ),
            "total_estimated_hours": sum(r.get("estimated_hours", 0) for r in results),
            "high_complexity_count": len(
                [r for r in results if r.get("complexity") == "High"]
            ),
        },
        "cookbook_details": results,
        "generated_at": str(pd.Timestamp.now()),
    }

    return json.dumps(report, indent=2)


if __name__ == "__main__":
    show_cookbook_analysis_page()
