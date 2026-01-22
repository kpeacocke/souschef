"""Cookbook Analysis Page for SousChef UI."""

import contextlib
import io
import json
import os
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

from souschef.assessment import (
    analyse_cookbook_dependencies,
    assess_single_cookbook_with_ai,
)
from souschef.converters.playbook import (
    generate_playbook_from_recipe,
    generate_playbook_from_recipe_with_ai,
)
from souschef.converters.template import convert_cookbook_templates
from souschef.core.constants import METADATA_FILENAME
from souschef.core.metrics import (
    EffortMetrics,
    get_timeline_weeks,
    validate_metrics_consistency,
)
from souschef.parsers.metadata import parse_cookbook_metadata

# AI Settings
ANTHROPIC_PROVIDER = "Anthropic (Claude)"
ANTHROPIC_CLAUDE_DISPLAY = "Anthropic Claude"
OPENAI_PROVIDER = "OpenAI (GPT)"
LOCAL_PROVIDER = "Local Model"
IBM_WATSONX = "IBM Watsonx"
RED_HAT_LIGHTSPEED = "Red Hat Lightspeed"


def _sanitize_filename(filename: str) -> str:
    """
    Sanitise filename to prevent path injection attacks.

    Args:
        filename: The filename to sanitise.

    Returns:
        Sanitised filename safe for file operations.

    """
    import re

    # Remove any path separators and parent directory references
    sanitised = filename.replace("..", "_").replace("/", "_").replace("\\", "_")
    # Remove any null bytes or control characters
    sanitised = re.sub(r"[\x00-\x1f\x7f]", "_", sanitised)
    # Remove leading/trailing whitespace and dots
    sanitised = sanitised.strip(". ")
    # Limit length to prevent issues
    sanitised = sanitised[:255]
    return sanitised if sanitised else "unnamed"


def _get_secure_ai_config_path() -> Path:
    """Return a private, non-world-writable path for AI config storage."""
    config_dir = Path(tempfile.gettempdir()) / ".souschef"
    config_dir.mkdir(mode=0o700, exist_ok=True)
    with contextlib.suppress(OSError):
        config_dir.chmod(0o700)

    if config_dir.is_symlink():
        raise ValueError("AI config directory cannot be a symlink")

    return config_dir / "ai_config.json"


def load_ai_settings() -> dict[str, str | float | int]:
    """Load AI settings from environment variables or configuration file."""
    # First try to load from environment variables
    env_config = _load_ai_settings_from_env()

    # If we have environment config, use it
    if env_config:
        return env_config

    # Fall back to loading from configuration file
    return _load_ai_settings_from_file()


def _load_ai_settings_from_env() -> dict[str, str | float | int]:
    """Load AI settings from environment variables."""
    import os
    from contextlib import suppress

    env_config: dict[str, str | float | int] = {}
    env_mappings = {
        "SOUSCHEF_AI_PROVIDER": "provider",
        "SOUSCHEF_AI_MODEL": "model",
        "SOUSCHEF_AI_API_KEY": "api_key",
        "SOUSCHEF_AI_BASE_URL": "base_url",
        "SOUSCHEF_AI_PROJECT_ID": "project_id",
    }

    # Handle string values
    for env_var, config_key in env_mappings.items():
        env_value = os.environ.get(env_var)
        if env_value:
            env_config[config_key] = env_value

    # Handle numeric values with error suppression
    temp_value = os.environ.get("SOUSCHEF_AI_TEMPERATURE")
    if temp_value:
        with suppress(ValueError):
            env_config["temperature"] = float(temp_value)

    tokens_value = os.environ.get("SOUSCHEF_AI_MAX_TOKENS")
    if tokens_value:
        with suppress(ValueError):
            env_config["max_tokens"] = int(tokens_value)

    return env_config


def _load_ai_settings_from_file() -> dict[str, str | float | int]:
    """Load AI settings from configuration file."""
    try:
        config_file = _get_secure_ai_config_path()
        if config_file.exists():
            with config_file.open() as f:
                file_config = json.load(f)
                return dict(file_config) if isinstance(file_config, dict) else {}
    except (ValueError, OSError):
        return {}
    return {}


def _get_ai_provider(ai_config: dict[str, str | float | int]) -> str:
    """
    Safely get the AI provider from config with proper type handling.

    Args:
        ai_config: The AI configuration dictionary.

    Returns:
        The AI provider string, or empty string if not found.

    """
    provider_raw = ai_config.get("provider", "")
    if isinstance(provider_raw, str):
        return provider_raw
    return str(provider_raw) if provider_raw else ""


def _get_ai_string_value(
    ai_config: dict[str, str | float | int], key: str, default: str = ""
) -> str:
    """
    Safely get a string value from AI config.

    Args:
        ai_config: The AI configuration dictionary.
        key: The key to retrieve.
        default: Default value if key not found.

    Returns:
        The string value or default.

    """
    value = ai_config.get(key, default)
    if isinstance(value, str):
        return value
    return str(value) if value else default


def _get_ai_float_value(
    ai_config: dict[str, str | float | int], key: str, default: float = 0.7
) -> float:
    """
    Safely get a float value from AI config.

    Args:
        ai_config: The AI configuration dictionary.
        key: The key to retrieve.
        default: Default value if key not found or conversion fails.

    Returns:
        The float value or default.

    """
    value = ai_config.get(key)
    if isinstance(value, float):
        return value
    elif isinstance(value, int):
        return float(value)
    elif isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _get_ai_int_value(
    ai_config: dict[str, str | float | int], key: str, default: int = 4000
) -> int:
    """
    Safely get an int value from AI config.

    Args:
        ai_config: The AI configuration dictionary.
        key: The key to retrieve.
        default: Default value if key not found or conversion fails.

    Returns:
        The int value or default.

    """
    value = ai_config.get(key)
    if isinstance(value, int):
        return value
    elif isinstance(value, float):
        return int(value)
    elif isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


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

    # Create temporary directory with secure permissions (owner-only access)
    temp_dir = Path(tempfile.mkdtemp())
    with contextlib.suppress(FileNotFoundError, OSError):
        temp_dir.chmod(0o700)  # Secure permissions: rwx------
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

        # Return the parent directory so it will scan and find the cookbook inside
        return extraction_dir
    else:
        # Single directory that doesn't contain cookbook components
        # It might be a wrapper directory containing multiple cookbooks
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

    if not archive_path.is_file():
        raise ValueError(f"Archive path is not a file: {archive_path}")

    if not tarfile.is_tarfile(str(archive_path)):
        raise ValueError(f"Invalid or corrupted TAR archive: {archive_path.name}")

    try:
        with tarfile.open(  # type: ignore[call-overload]  # NOSONAR
            str(archive_path), mode=mode, filter="data"
        ) as tar_ref:
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
{cookbook_path}  # deepcode ignore PT: used for display only, not file operations
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
- **Source**: {cookbook_path}  # deepcode ignore PT: used for display only

## Results Summary
"""
        for result in results:
            status_icon = (
                "PASS" if result["status"] == ANALYSIS_STATUS_ANALYSED else "FAIL"
            )
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


def show_cookbook_analysis_page() -> None:
    """Show the cookbook analysis page."""
    # Initialise session state for analysis results
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None
        st.session_state.analysis_cookbook_path = None
        st.session_state.total_cookbooks = 0
        st.session_state.temp_dir = None

    # Add unique key to track if this is a new page load
    if "analysis_page_key" not in st.session_state:
        st.session_state.analysis_page_key = 0

    _setup_cookbook_analysis_ui()

    # Check if we have analysis results to display
    if st.session_state.analysis_results is not None:
        _display_results_view()
        return

    # Check if we have an uploaded file from the dashboard
    if "uploaded_file_data" in st.session_state:
        _handle_dashboard_upload()
        return

    _show_analysis_input()


def _show_analysis_input() -> None:
    """Show analysis input interface."""
    # Input method selection
    input_method = st.radio(
        "Choose Input Method",
        ["Upload Archive", "Directory Path"],
        horizontal=True,
        help="Select how to provide cookbooks for analysis",
    )

    cookbook_path: str | Path | None = None
    temp_dir = None
    uploaded_file = None

    if input_method == "Directory Path":
        cookbook_path = _get_cookbook_path_input()
    else:
        uploaded_file = _get_archive_upload_input()
        if uploaded_file:
            try:
                with st.spinner("Extracting archive..."):
                    # Clear any previous analysis results
                    st.session_state.analysis_results = None
                    st.session_state.holistic_assessment = None

                    temp_dir, cookbook_path = extract_archive(uploaded_file)
                    # Store temp_dir in session state to prevent premature cleanup
                    st.session_state.temp_dir = temp_dir
                st.success("Archive extracted successfully to temporary location")
            except Exception as e:
                st.error(f"Failed to extract archive: {e}")
                return

    try:
        if cookbook_path:
            _validate_and_list_cookbooks(str(cookbook_path))

        _display_instructions()
    finally:
        # Only clean up temp_dir if it wasn't stored in session state
        # (i.e., if we didn't successfully extract an archive)
        if temp_dir and temp_dir.exists() and st.session_state.temp_dir != temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


def _display_results_view() -> None:
    """Display the results view with new analysis button."""
    # Add a "New Analysis" button at the top of results page
    col1, col2 = st.columns([6, 1])
    with col1:
        st.write("")  # Spacer
    with col2:
        if st.button(
            "New Analysis",
            help="Start a new analysis",
            key=f"new_analysis_{st.session_state.analysis_page_key}",
        ):
            st.session_state.analysis_results = None
            st.session_state.holistic_assessment = None
            st.session_state.analysis_cookbook_path = None
            st.session_state.total_cookbooks = None
            st.session_state.analysis_info_messages = None
            st.session_state.analysis_page_key += 1
            st.rerun()

    _display_analysis_results(
        st.session_state.analysis_results,
        st.session_state.total_cookbooks,
    )


def _setup_cookbook_analysis_ui() -> None:
    """Set up the cookbook analysis page header."""
    st.title("SousChef - Cookbook Analysis")
    st.markdown("""
    Analyse your Chef cookbooks and get detailed migration assessments for
    converting to Ansible playbooks.

    Upload a cookbook archive or specify a directory path to begin analysis.
    """)

    # Add back to dashboard button
    col1, _ = st.columns([1, 4])
    with col1:
        if st.button(
            "← Back to Dashboard",
            help="Return to main dashboard",
            key="back_to_dashboard_from_analysis",
        ):
            # Clear all analysis state
            st.session_state.analysis_results = None
            st.session_state.holistic_assessment = None
            st.session_state.analysis_cookbook_path = None
            st.session_state.total_cookbooks = None
            st.session_state.current_page = "Dashboard"
            st.rerun()


def _get_cookbook_path_input() -> str:
    """Get the cookbook path input from the user."""
    return st.text_input(
        "Cookbook Directory Path",
        placeholder="cookbooks/ or ../shared/cookbooks/",
        help="Enter a path to your Chef cookbooks directory. "
        "Relative paths (e.g., 'cookbooks/') and absolute paths inside the workspace "
        "(e.g., '/workspaces/souschef/cookbooks/') are allowed.",
    )


def _get_archive_upload_input() -> Any:
    """Get archive upload input from the user."""
    uploaded_file = st.file_uploader(
        "Upload Cookbook Archive",
        type=["zip", "tar.gz", "tgz", "tar"],
        help="Upload a ZIP or TAR archive containing your Chef cookbooks",
    )
    return uploaded_file


def _validate_and_list_cookbooks(cookbook_path: str) -> None:
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
                "Invalid path: Path contains null bytes or backslashes, "
                "which are not allowed."
            )
            return None

        # Reject paths with directory traversal attempts
        if ".." in path_str:
            st.error(
                "Invalid path: Path contains '..' which is not allowed "
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
                "Invalid path: The resolved path is outside the allowed "
                "directories (workspace or temporary directory). Paths cannot go above "
                "the workspace root for security reasons."
            )
            return None

    except Exception as exc:
        st.error(f"Invalid path: {exc}. Please enter a valid relative path.")
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
    st.dataframe(df, width="stretch")


def _handle_cookbook_selection(cookbook_path: str, cookbook_data: list):
    """Handle the cookbook selection interface with individual and holistic options."""
    st.subheader("Cookbook Selection & Analysis")

    # Show validation warnings if any cookbooks have issues
    _show_cookbook_validation_warnings(cookbook_data)

    # Holistic analysis/conversion buttons
    st.markdown("### Holistic Analysis & Conversion")
    st.markdown(
        "Analyse and convert **ALL cookbooks** in the archive holistically, "
        "considering dependencies between cookbooks."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "🔍 Analyse ALL Cookbooks",
            type="primary",
            help="Analyse all cookbooks together considering inter-cookbook "
            "dependencies",
            key="holistic_analysis",
        ):
            _analyze_all_cookbooks_holistically(cookbook_path, cookbook_data)

    with col2:
        if st.button(
            "🔄 Convert ALL Cookbooks",
            type="secondary",
            help="Convert all cookbooks to Ansible roles considering dependencies",
            key="holistic_conversion",
        ):
            _convert_all_cookbooks_holistically(cookbook_path)

    st.divider()

    # Individual cookbook selection
    st.markdown("### Individual Cookbook Selection")
    st.markdown("Select specific cookbooks to analyse individually.")

    # Get list of cookbook names for multiselect
    cookbook_names = [cb["Name"] for cb in cookbook_data]

    selected_cookbooks = st.multiselect(
        "Select cookbooks to analyse:",
        options=cookbook_names,
        default=[],
        help="Choose which cookbooks to analyse individually",
    )

    if selected_cookbooks:
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button(
                f"📊 Analyse Selected ({len(selected_cookbooks)})",
                help=f"Analyse {len(selected_cookbooks)} selected cookbooks",
                key="analyze_selected",
            ):
                analyse_selected_cookbooks(cookbook_path, selected_cookbooks)

        with col2:
            if st.button(
                f"🔗 Analyse as Project ({len(selected_cookbooks)})",
                help=f"Analyse {len(selected_cookbooks)} cookbooks as a project "
                f"with dependency analysis",
                key="analyze_project",
            ):
                analyse_project_cookbooks(cookbook_path, selected_cookbooks)

        with col3:
            if st.button(
                f"📋 Select All ({len(cookbook_names)})",
                help=f"Select all {len(cookbook_names)} cookbooks",
                key="select_all",
            ):
                # This will trigger a rerun with all cookbooks selected
                st.session_state.selected_cookbooks = cookbook_names
                st.rerun()


def _show_cookbook_validation_warnings(cookbook_data: list):
    """Show validation warnings for cookbooks that might not be analyzable."""
    problematic_cookbooks = []

    for cookbook in cookbook_data:
        if cookbook.get(METADATA_COLUMN_NAME) == METADATA_STATUS_NO:
            problematic_cookbooks.append(cookbook["Name"])

    if problematic_cookbooks:
        st.warning("Some cookbooks may not be analyzable:")
        st.markdown("**Cookbooks without valid metadata.rb:**")
        for name in problematic_cookbooks:
            st.write(f"• {name}")

        with st.expander("Why this matters"):
            st.markdown("""
            Cookbooks need a valid `metadata.rb` file for proper analysis. Without it:
            - Version and maintainer information cannot be determined
            - Dependencies cannot be identified
            - Analysis may fail or produce incomplete results

            **To fix:** Ensure each cookbook has a `metadata.rb` file with
 proper Ruby syntax.
            """)

    # Check for cookbooks without recipes
    cookbooks_without_recipes = []
    for cookbook in cookbook_data:
        cookbook_dir = Path(cookbook["Path"])
        recipes_dir = cookbook_dir / "recipes"
        if not recipes_dir.exists() or not list(recipes_dir.glob("*.rb")):
            cookbooks_without_recipes.append(cookbook["Name"])

    if cookbooks_without_recipes:
        st.warning("Some cookbooks may not have recipes:")
        st.markdown("**Cookbooks without recipe files:**")
        for name in cookbooks_without_recipes:
            st.write(f"• {name}")

        with st.expander("Why this matters"):
            st.markdown("""
            Cookbooks need recipe files (`.rb` files in the `recipes/` directory)
            to be converted to Ansible.
            Without recipes, the cookbook cannot be analyzed or converted.

            **To fix:** Ensure each cookbook has at least one `.rb` file in its
            `recipes/` directory.
            """)


def _analyze_all_cookbooks_holistically(
    cookbook_path: str, cookbook_data: list
) -> None:
    """Analyse all cookbooks holistically."""
    st.subheader("Holistic Cookbook Analysis")

    progress_bar, status_text = _setup_analysis_progress()

    try:
        status_text.text("Performing holistic analysis of all cookbooks...")

        # Check if AI-enhanced analysis is available
        ai_config = load_ai_settings()
        provider_name = _get_ai_provider(ai_config)
        use_ai = (
            provider_name
            and provider_name != LOCAL_PROVIDER
            and ai_config.get("api_key")
        )

        if use_ai:
            results = _analyze_with_ai(cookbook_data, provider_name, progress_bar)
            assessment_result = {
                "cookbook_assessments": results,
                "recommendations": "AI-enhanced per-cookbook recommendations above",
            }
            st.session_state.analysis_info_messages = [
                f"Using AI-enhanced analysis with {provider_name} "
                f"({_get_ai_string_value(ai_config, 'model', 'claude-3-5-sonnet-20241022')})",  # noqa: E501
                f"Detected {len(cookbook_data)} cookbook(s)",
            ]
        else:
            results, assessment_result = _analyze_rule_based(cookbook_data)

        st.session_state.holistic_assessment = assessment_result
        st.session_state.analysis_results = results
        st.session_state.analysis_cookbook_path = cookbook_path
        st.session_state.total_cookbooks = len(results)

        progress_bar.progress(1.0)
        st.rerun()

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Holistic analysis failed: {e}")
    finally:
        progress_bar.empty()
        status_text.empty()


def _analyze_with_ai(
    cookbook_data: list,
    provider_name: str,
    progress_bar,
) -> list:
    """
    Analyze cookbooks using AI-enhanced analysis.

    Args:
        cookbook_data: List of cookbook data.
        provider_name: Name of the AI provider.
        progress_bar: Streamlit progress bar.

    Returns:
        List of analysis results.

    """
    from souschef.assessment import assess_single_cookbook_with_ai

    ai_config = load_ai_settings()
    provider_mapping = {
        ANTHROPIC_CLAUDE_DISPLAY: "anthropic",
        ANTHROPIC_PROVIDER: "anthropic",
        "OpenAI": "openai",
        OPENAI_PROVIDER: "openai",
        IBM_WATSONX: "watson",
        RED_HAT_LIGHTSPEED: "lightspeed",
    }
    provider = provider_mapping.get(
        provider_name,
        provider_name.lower().replace(" ", "_"),
    )

    model = _get_ai_string_value(ai_config, "model", "claude-3-5-sonnet-20241022")
    api_key = _get_ai_string_value(ai_config, "api_key", "")
    temperature = _get_ai_float_value(ai_config, "temperature", 0.7)
    max_tokens = _get_ai_int_value(ai_config, "max_tokens", 4000)
    project_id = _get_ai_string_value(ai_config, "project_id", "")
    base_url = _get_ai_string_value(ai_config, "base_url", "")

    st.info(f"Using AI-enhanced analysis with {provider_name} ({model})")

    # Count total recipes across all cookbooks
    total_recipes = sum(
        len(list((Path(cb["Path"]) / "recipes").glob("*.rb")))
        if (Path(cb["Path"]) / "recipes").exists()
        else 0
        for cb in cookbook_data
    )

    st.info(f"Detected {len(cookbook_data)} cookbook(s) with {total_recipes} recipe(s)")

    results = []
    for i, cb_data in enumerate(cookbook_data):
        # Count recipes in this cookbook
        recipes_dir = Path(cb_data["Path"]) / "recipes"
        recipe_count = (
            len(list(recipes_dir.glob("*.rb"))) if recipes_dir.exists() else 0
        )

        st.info(
            f"Analyzing {cb_data['Name']} ({recipe_count} recipes)... "
            f"({i + 1}/{len(cookbook_data)})"
        )
        progress_bar.progress((i + 1) / len(cookbook_data))

        assessment = assess_single_cookbook_with_ai(
            cb_data["Path"],
            ai_provider=provider,
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            project_id=project_id,
            base_url=base_url,
        )

        result = _build_cookbook_result(cb_data, assessment, ANALYSIS_STATUS_ANALYSED)
        results.append(result)

    return results


def _analyze_rule_based(
    cookbook_data: list,
) -> tuple[list, dict]:
    """
    Analyze cookbooks using rule-based analysis.

    Args:
        cookbook_data: List of cookbook data.

    Returns:
        Tuple of (results list, assessment_result dict).

    """
    from souschef.assessment import parse_chef_migration_assessment

    cookbook_paths_list = [cb["Path"] for cb in cookbook_data]
    cookbook_paths_str = ",".join(cookbook_paths_list)

    assessment_result = parse_chef_migration_assessment(cookbook_paths_str)

    if "error" in assessment_result:
        st.error(f"Holistic analysis failed: {assessment_result['error']}")
        return [], {}

    results = _process_cookbook_assessments(assessment_result, cookbook_data)
    return results, assessment_result


def _process_cookbook_assessments(assessment_result: dict, cookbook_data: list) -> list:
    """
    Process cookbook assessments and build results.

    Args:
        assessment_result: Assessment result dictionary.
        cookbook_data: List of cookbook data.

    Returns:
        List of result dictionaries.

    """
    results: list[dict] = []
    if "cookbook_assessments" not in assessment_result:
        return results

    top_recommendations = assessment_result.get("recommendations", "")

    for cookbook_assessment in assessment_result["cookbook_assessments"]:
        result = _build_assessment_result(
            cookbook_assessment, cookbook_data, top_recommendations
        )
        results.append(result)

    return results


def _build_assessment_result(
    cookbook_assessment: dict, cookbook_data: list, top_recommendations: str
) -> dict:
    """
    Build result dictionary from cookbook assessment.

    Args:
        cookbook_assessment: Single cookbook assessment.
        cookbook_data: List of cookbook data.
        top_recommendations: Top-level recommendations.

    Returns:
        Result dictionary.

    """
    cookbook_path = cookbook_assessment.get("cookbook_path", "")
    cookbook_info = _find_cookbook_info(cookbook_data, cookbook_path)

    recommendations = _build_recommendations(cookbook_assessment, top_recommendations)

    estimated_days = cookbook_assessment.get("estimated_effort_days", 0)
    effort_metrics = EffortMetrics(estimated_days)

    return {
        "name": (
            cookbook_info["Name"]
            if cookbook_info
            else cookbook_assessment["cookbook_name"]
        ),
        "path": cookbook_info["Path"] if cookbook_info else cookbook_path,
        "version": cookbook_info["Version"] if cookbook_info else "Unknown",
        "maintainer": cookbook_info["Maintainer"] if cookbook_info else "Unknown",
        "description": (
            cookbook_info["Description"] if cookbook_info else "Analysed holistically"
        ),
        "dependencies": int(cookbook_assessment.get("dependencies", 0) or 0),
        "complexity": cookbook_assessment.get("migration_priority", "Unknown").title(),
        "estimated_hours": effort_metrics.estimated_hours,
        "recommendations": recommendations,
        "status": ANALYSIS_STATUS_ANALYSED,
    }


def _find_cookbook_info(cookbook_data: list, cookbook_path: str) -> dict | None:
    """
    Find cookbook info matching the given path.

    Args:
        cookbook_data: List of cookbook data.
        cookbook_path: Path to match.

    Returns:
        Matching cookbook info or None.

    """
    return next(
        (cd for cd in cookbook_data if cd["Path"] == cookbook_path),
        None,
    )


def _build_cookbook_result(cb_data: dict, assessment: dict, status: str) -> dict:
    """
    Build a cookbook result from assessment data.

    Args:
        cb_data: Cookbook data.
        assessment: Assessment dictionary.
        status: Status of analysis.

    Returns:
        Result dictionary.

    """
    if "error" not in assessment:
        return {
            "name": cb_data["Name"],
            "path": cb_data["Path"],
            "version": cb_data["Version"],
            "maintainer": cb_data["Maintainer"],
            "description": cb_data["Description"],
            "dependencies": cb_data["Dependencies"],
            "complexity": assessment.get("complexity", "Unknown"),
            "estimated_hours": assessment.get("estimated_hours", 0),
            "recommendations": assessment.get(
                "recommendations", "No recommendations available"
            ),
            "status": status,
        }
    return {
        "name": cb_data["Name"],
        "path": cb_data["Path"],
        "version": cb_data["Version"],
        "maintainer": cb_data["Maintainer"],
        "description": cb_data["Description"],
        "dependencies": cb_data["Dependencies"],
        "complexity": "Error",
        "estimated_hours": 0,
        "recommendations": f"Analysis failed: {assessment['error']}",
        "status": ANALYSIS_STATUS_FAILED,
    }


def _build_recommendations(cookbook_assessment: dict, top_recommendations: str) -> str:
    """
    Build recommendations from cookbook assessment.

    Args:
        cookbook_assessment: Assessment data for a cookbook.
        top_recommendations: Top-level recommendations.

    Returns:
        Formatted recommendations string.

    """
    recommendations: list[str] = []
    if cookbook_assessment.get("challenges"):
        for challenge in cookbook_assessment["challenges"]:
            recommendations.append(f"• {challenge}")
        return "\n".join(recommendations)

    return (
        top_recommendations
        if top_recommendations
        else f"Complexity: {str(cookbook_assessment.get('complexity_score', 0))}/100"
    )


def _convert_all_cookbooks_holistically(cookbook_path: str):
    """Convert all cookbooks to Ansible roles."""
    st.subheader("Holistic Cookbook Conversion")

    progress_bar, status_text = _setup_analysis_progress()

    try:
        status_text.text("Converting all cookbooks holistically...")

        # Create temporary output directory with secure permissions
        import tempfile
        from pathlib import Path

        output_dir = Path(tempfile.mkdtemp(prefix="souschef_holistic_conversion_"))
        with contextlib.suppress(FileNotFoundError, OSError):
            output_dir.chmod(0o700)  # Secure permissions: rwx------

        # Get assessment data if available
        assessment_data = ""
        if (
            "holistic_assessment" in st.session_state
            and st.session_state.holistic_assessment
        ):
            assessment_data = json.dumps(st.session_state.holistic_assessment)

        # Call the new holistic conversion function
        from souschef.server import convert_all_cookbooks_comprehensive

        conversion_result = convert_all_cookbooks_comprehensive(
            cookbooks_path=cookbook_path,
            output_path=str(output_dir),
            assessment_data=assessment_data,
            include_templates=True,
            include_attributes=True,
            include_recipes=True,
        )

        if conversion_result.startswith("Error"):
            st.error(f"Holistic conversion failed: {conversion_result}")
            return

        # Store conversion result for display
        st.session_state.holistic_conversion_result = {
            "result": conversion_result,
            "output_path": str(output_dir),
        }

        progress_bar.progress(1.0)
        status_text.text("Holistic conversion completed!")
        st.success("Holistically converted all cookbooks to Ansible roles!")

        # Display conversion results
        _display_holistic_conversion_results(
            st.session_state.holistic_conversion_result
        )

        # Trigger rerun to display results
        st.rerun()

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"Holistic conversion failed: {e}")
    finally:
        progress_bar.empty()
        status_text.empty()


def _parse_conversion_result_text(result_text: str) -> dict:
    """Parse the conversion result text to extract structured data."""
    structured: dict[str, Any] = {
        "summary": {},
        "cookbook_results": [],
        "warnings": [],
        "errors": [],
    }

    lines = result_text.split("\n")
    current_section = None

    for line in lines:
        line = line.strip()

        # Parse summary section
        if "## Overview:" in line:
            current_section = "summary"
        elif current_section == "summary" and "- " in line:
            _parse_summary_line(line, structured)

        # Parse successfully converted cookbooks
        elif "## Successfully Converted Cookbooks:" in line:
            current_section = "converted"
        elif current_section == "converted" and line.startswith("- **"):
            _parse_converted_cookbook(line, structured)

        # Parse failed conversions
        elif "## Failed Conversions:" in line:
            current_section = "failed"
        elif current_section == "failed" and line.startswith("- ❌ **"):
            _parse_failed_cookbook(line, structured)

    # Extract warnings from the result text
    _extract_warnings_from_text(result_text, structured)

    return structured


def _parse_summary_line(line: str, structured: dict):
    """Parse a single summary line."""
    if "Total cookbooks found:" in line:
        try:
            count = int(line.split(":")[-1].strip())
            structured["summary"]["total_cookbooks"] = count
        except ValueError:
            pass
    elif "Successfully converted:" in line:
        try:
            count = int(line.split(":")[-1].strip())
            structured["summary"]["cookbooks_converted"] = count
        except ValueError:
            pass
    elif "Total files converted:" in line:
        try:
            count = int(line.split(":")[-1].strip())
            structured["summary"]["total_converted_files"] = count
        except ValueError:
            pass


def _parse_converted_cookbook(line: str, structured: dict):
    """Parse a successfully converted cookbook line."""
    try:
        parts = line.split("**")
        if len(parts) >= 3:
            cookbook_name = parts[1]
            role_name = parts[3].strip("`→ ")
            structured["cookbook_results"].append(
                {
                    "cookbook_name": cookbook_name,
                    "role_name": role_name,
                    "status": "success",
                    "tasks_count": 0,  # Will be updated if more details available
                    "templates_count": 0,
                    "variables_count": 0,
                    "files_count": 0,
                }
            )
    except (IndexError, ValueError):
        pass


def _parse_failed_cookbook(line: str, structured: dict):
    """Parse a failed conversion cookbook line."""
    try:
        parts = line.split("**")
        if len(parts) >= 3:
            cookbook_name = parts[1]
            error = parts[3].strip(": ")
            structured["cookbook_results"].append(
                {
                    "cookbook_name": cookbook_name,
                    "status": "failed",
                    "error": error,
                }
            )
    except (IndexError, ValueError):
        pass


def _extract_warnings_from_text(result_text: str, structured: dict):
    """Extract warnings from the conversion result text."""
    # Extract warnings from the result text (look for common warning patterns)
    if "No recipes directory found" in result_text:
        structured["warnings"].append(
            "Some cookbooks are missing recipes directories and cannot be "
            "converted to Ansible tasks"
        )
    if "No recipe files" in result_text.lower():
        structured["warnings"].append("Some cookbooks have empty recipes directories")

    # If no cookbooks were successfully converted but some were found,
    # add a general warning
    total_found = structured["summary"].get("total_cookbooks", 0)
    converted = structured["summary"].get("cookbooks_converted", 0)
    if total_found > 0 and converted == 0:
        structured["warnings"].append(
            "No cookbooks were successfully converted. Check that cookbooks "
            "contain recipes directories with .rb files."
        )


def _display_holistic_conversion_results(conversion_result: dict):
    """Display the results of holistic cookbook conversion."""
    st.subheader("Holistic Conversion Results")

    # Parse the conversion result string to extract structured data
    result_text = conversion_result.get("result", "")
    structured_result = _parse_conversion_result_text(result_text)

    _display_conversion_summary(structured_result)
    _display_conversion_warnings_errors(structured_result)
    _display_conversion_details(structured_result)
    _display_conversion_report(result_text)
    _display_conversion_download_options(conversion_result)


def _display_conversion_summary(structured_result: dict):
    """Display the conversion summary metrics."""
    if "summary" in structured_result:
        summary = structured_result["summary"]
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Cookbooks Converted", summary.get("cookbooks_converted", 0))

        with col2:
            st.metric("Roles Created", summary.get("roles_created", 0))

        with col3:
            st.metric("Tasks Generated", summary.get("tasks_generated", 0))

        with col4:
            st.metric("Templates Converted", summary.get("templates_converted", 0))


def _display_conversion_warnings_errors(structured_result: dict):
    """Display conversion warnings and errors."""
    if "warnings" in structured_result and structured_result["warnings"]:
        st.warning("⚠️ Conversion Warnings")
        for warning in structured_result["warnings"]:
            st.write(f"• {warning}")

    if "errors" in structured_result and structured_result["errors"]:
        st.error("❌ Conversion Errors")
        for error in structured_result["errors"]:
            st.write(f"• {error}")


def _display_conversion_details(structured_result: dict):
    """Display detailed conversion results."""
    if "cookbook_results" in structured_result:
        st.subheader("Conversion Details")

        for cookbook_result in structured_result["cookbook_results"]:
            with st.expander(
                f"📁 {cookbook_result.get('cookbook_name', 'Unknown')}", expanded=False
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Tasks", cookbook_result.get("tasks_count", 0))
                    st.metric("Templates", cookbook_result.get("templates_count", 0))

                with col2:
                    st.metric("Variables", cookbook_result.get("variables_count", 0))
                    st.metric("Files", cookbook_result.get("files_count", 0))

                if cookbook_result.get("status") == "success":
                    st.success("✅ Conversion successful")
                else:
                    error_msg = cookbook_result.get("error", "Unknown error")
                    st.error(f"❌ Conversion failed: {error_msg}")


def _display_conversion_report(result_text: str):
    """Display the raw conversion report."""
    with st.expander("Full Conversion Report"):
        st.code(result_text, language="markdown")


def _display_conversion_download_options(conversion_result: dict):
    """Display download options for converted roles."""
    if "output_path" in conversion_result:
        st.subheader("Download Converted Roles")

        # Validate output_path before use
        output_path = conversion_result["output_path"]
        try:
            from souschef.core.path_utils import _normalize_path

            # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected
            safe_output_path = _normalize_path(str(output_path))
        except ValueError:
            st.error("Invalid output path")
            return

        if safe_output_path.exists():
            # Create ZIP archive of all converted roles
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected
                for root, _dirs, files in os.walk(str(safe_output_path)):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(safe_output_path)
                        zip_file.write(str(file_path), str(arcname))

            zip_buffer.seek(0)

            st.download_button(
                label="📦 Download All Ansible Roles",
                data=zip_buffer.getvalue(),
                file_name="ansible_roles_holistic.zip",
                mime="application/zip",
                help="Download ZIP archive containing all converted Ansible roles",
                key="download_holistic_roles",
            )

            st.info(f"📂 Roles saved to: {output_path}")
        else:
            st.warning("Output directory not found for download")


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
    st.info(f"Using file uploaded from Dashboard: {file_name}")

    # Add option to clear and upload a different file
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button(
            "Use Different File",
            help="Clear this file and upload a different one",
            key="use_different_file",
        ):
            # Clear the uploaded file from session state
            del st.session_state.uploaded_file_data
            del st.session_state.uploaded_file_name
            del st.session_state.uploaded_file_type
            st.rerun()

    with col2:
        if st.button(
            "Back to Dashboard", help="Return to dashboard", key="back_to_dashboard"
        ):
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
            _validate_and_list_cookbooks(str(cookbook_path))

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
    # Check if AI is configured
    ai_config = load_ai_settings()
    ai_available = (
        ai_config.get("provider")
        and ai_config.get("provider") != LOCAL_PROVIDER
        and ai_config.get("api_key")
    )

    ai_indicator = " [AI-ENHANCED]" if ai_available else " [RULE-BASED]"
    status_text.text(f"Analyzing {cookbook_name}{ai_indicator}... ({current}/{total})")


def _find_cookbook_directory(cookbook_path, cookbook_name):
    """Find the directory for a specific cookbook by checking metadata."""
    for d in Path(cookbook_path).iterdir():
        if d.is_dir():
            # Check if this directory contains a cookbook with the matching name
            metadata_file = d / METADATA_FILENAME
            if metadata_file.exists():
                try:
                    metadata = parse_cookbook_metadata(str(metadata_file))
                    if metadata.get("name") == cookbook_name:
                        return d
                except Exception:
                    # If metadata parsing fails, skip this directory
                    continue
    return None


def _analyse_single_cookbook(cookbook_name, cookbook_dir):
    """Analyse a single cookbook."""
    try:
        metadata = _load_cookbook_metadata(cookbook_name, cookbook_dir)
        if "error" in metadata:
            return metadata  # Return error result

        ai_config = load_ai_settings()
        use_ai = _should_use_ai(ai_config)

        if use_ai:
            assessment = _run_ai_analysis(cookbook_dir, ai_config)
        else:
            assessment = _run_rule_based_analysis(cookbook_dir)

        if isinstance(assessment, dict) and "error" in assessment:
            return _create_failed_analysis(
                cookbook_name, cookbook_dir, assessment["error"]
            )

        return _create_successful_analysis(
            cookbook_name, cookbook_dir, assessment, metadata
        )
    except Exception as e:
        import traceback

        error_details = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        return _create_failed_analysis(cookbook_name, cookbook_dir, error_details)


def _load_cookbook_metadata(cookbook_name: str, cookbook_dir: Path) -> dict[str, Any]:
    """
    Load and parse cookbook metadata.

    Args:
        cookbook_name: Name of the cookbook.
        cookbook_dir: Directory containing the cookbook.

    Returns:
        Metadata dictionary or error result.

    """
    metadata_file = cookbook_dir / METADATA_FILENAME
    if not metadata_file.exists():
        return _create_failed_analysis(  # type: ignore[no-any-return]
            cookbook_name,
            cookbook_dir,
            f"No {METADATA_FILENAME} found in {cookbook_dir}",
        )

    try:
        return parse_cookbook_metadata(str(metadata_file))
    except Exception as e:
        return _create_failed_analysis(  # type: ignore[no-any-return]
            cookbook_name, cookbook_dir, f"Failed to parse metadata: {e}"
        )


def _should_use_ai(ai_config: dict) -> bool:
    """
    Check if AI-enhanced analysis should be used.

    Args:
        ai_config: AI configuration dictionary.

    Returns:
        True if AI analysis should be used.

    """
    return bool(
        ai_config.get("provider")
        and ai_config.get("provider") != LOCAL_PROVIDER
        and ai_config.get("api_key")
    )


def _run_ai_analysis(cookbook_dir: Path, ai_config: dict) -> dict:
    """
    Run AI-enhanced cookbook analysis.

    Args:
        cookbook_dir: Directory containing the cookbook.
        ai_config: AI configuration dictionary.

    Returns:
        Assessment dictionary.

    """
    ai_provider = _determine_ai_provider(ai_config)

    return assess_single_cookbook_with_ai(
        str(cookbook_dir),
        ai_provider=ai_provider or "anthropic",
        api_key=str(ai_config.get("api_key", "")),
        model=str(ai_config.get("model", "claude-3-5-sonnet-20241022")),
        temperature=float(ai_config.get("temperature", 0.7)),
        max_tokens=int(ai_config.get("max_tokens", 4000)),
        project_id=str(ai_config.get("project_id", "")),
        base_url=str(ai_config.get("base_url", "")),
    )


def _determine_ai_provider(ai_config: dict) -> str:
    """
    Determine AI provider name from config.

    Args:
        ai_config: AI configuration dictionary.

    Returns:
        Provider string.

    """
    provider_mapping = {
        ANTHROPIC_CLAUDE_DISPLAY: "anthropic",
        ANTHROPIC_PROVIDER: "anthropic",
        "OpenAI": "openai",
        OPENAI_PROVIDER: "openai",
        IBM_WATSONX: "watson",
        RED_HAT_LIGHTSPEED: "lightspeed",
    }
    provider_name_raw = ai_config.get("provider", "")
    provider_name = str(provider_name_raw) if provider_name_raw else ""
    return provider_mapping.get(
        provider_name,
        provider_name.lower().replace(" ", "_") if provider_name else "anthropic",
    )


def _run_rule_based_analysis(cookbook_dir: Path) -> dict:
    """
    Run rule-based cookbook analysis.

    Args:
        cookbook_dir: Directory containing the cookbook.

    Returns:
        Assessment dictionary.

    """
    from souschef.assessment import parse_chef_migration_assessment

    assessment = parse_chef_migration_assessment(str(cookbook_dir))

    # Extract single cookbook assessment if multi-cookbook structure returned
    if "cookbook_assessments" in assessment and assessment["cookbook_assessments"]:
        cookbook_assessment = assessment["cookbook_assessments"][0]
        return {
            "complexity": assessment.get("complexity", "Unknown"),
            "estimated_hours": assessment.get("estimated_hours", 0),
            "recommendations": _format_recommendations_from_assessment(
                cookbook_assessment, assessment
            ),
        }

    return assessment


def _create_successful_analysis(
    cookbook_name: str, cookbook_dir: Path, assessment: dict, metadata: dict
) -> dict:
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


def _format_recommendations_from_assessment(
    cookbook_assessment: dict, overall_assessment: dict
) -> str:
    """Format recommendations from the detailed assessment structure."""
    recommendations: list[str] = []

    # Add cookbook-specific details
    _add_complexity_score(recommendations, cookbook_assessment)
    _add_effort_estimate(recommendations, cookbook_assessment)
    _add_migration_priority(recommendations, cookbook_assessment)
    _add_key_findings(recommendations, cookbook_assessment)
    _add_overall_recommendations(recommendations, overall_assessment)

    return "\n".join(recommendations) if recommendations else "Analysis completed"


def _add_complexity_score(recommendations: list[str], assessment: dict) -> None:
    """Add complexity score to recommendations."""
    if "complexity_score" in assessment:
        recommendations.append(
            f"Complexity Score: {assessment['complexity_score']}/100"
        )


def _add_effort_estimate(recommendations: list[str], assessment: dict) -> None:
    """Add effort estimate to recommendations."""
    if "estimated_effort_days" not in assessment:
        return

    estimated_days = assessment["estimated_effort_days"]
    effort_metrics = EffortMetrics(estimated_days)
    complexity = assessment.get("complexity", "Medium")
    is_valid, _ = validate_metrics_consistency(
        days=effort_metrics.estimated_days,
        weeks=effort_metrics.estimated_weeks_range,
        hours=effort_metrics.estimated_hours,
        complexity=complexity,
    )
    if is_valid:
        recommendations.append(
            f"Estimated Effort: {effort_metrics.estimated_days_formatted}"
        )
    else:
        recommendations.append(f"Estimated Effort: {estimated_days} days")


def _add_migration_priority(recommendations: list[str], assessment: dict) -> None:
    """Add migration priority to recommendations."""
    if "migration_priority" in assessment:
        recommendations.append(
            f"Migration Priority: {assessment['migration_priority']}"
        )


def _add_key_findings(recommendations: list[str], assessment: dict) -> None:
    """Add key findings to recommendations."""
    if not assessment.get("key_findings"):
        return

    recommendations.append("\nKey Findings:")
    for finding in assessment["key_findings"]:
        recommendations.append(f"  - {finding}")


def _add_overall_recommendations(
    recommendations: list[str], overall_assessment: dict
) -> None:
    """Add overall recommendations to recommendations."""
    rec_data = overall_assessment.get("recommendations")
    if not rec_data:
        return

    recommendations.append("\nRecommendations:")
    if isinstance(rec_data, list):
        for rec in rec_data:
            if isinstance(rec, dict) and "recommendation" in rec:
                recommendations.append(f"  - {rec['recommendation']}")
            elif isinstance(rec, str):
                recommendations.append(f"  - {rec}")
    elif isinstance(rec_data, str):
        recommendations.append(f"  - {rec_data}")


def _get_error_context(cookbook_dir: Path) -> str:
    """Get context information about why analysis might have failed."""
    context_parts = []

    # Check basic structure
    validation = _validate_cookbook_structure(cookbook_dir)

    missing_items = [check for check, valid in validation.items() if not valid]
    if missing_items:
        context_parts.append(f"Missing: {', '.join(missing_items)}")

    # Check if metadata parsing failed
    metadata_file = cookbook_dir / METADATA_FILENAME
    if metadata_file.exists():
        try:
            parse_cookbook_metadata(str(metadata_file))
            context_parts.append("metadata.rb exists and parses successfully")
        except Exception as e:
            context_parts.append(f"metadata.rb parsing error: {str(e)[:100]}")

    # Check AI configuration if using AI
    ai_config = load_ai_settings()
    use_ai = (
        ai_config.get("provider")
        and ai_config.get("provider") != LOCAL_PROVIDER
        and ai_config.get("api_key")
    )

    if use_ai:
        context_parts.append(
            f"Using AI analysis with {ai_config.get('provider', 'Unknown')}"
        )
        if not ai_config.get("api_key"):
            context_parts.append("AI configured but no API key provided")
    else:
        context_parts.append("Using rule-based analysis (AI not configured)")

    return (
        "; ".join(context_parts) if context_parts else "No additional context available"
    )


def _create_failed_analysis(cookbook_name, cookbook_dir, error_message):
    """Create analysis result for failed analysis."""
    # Add context to the error message
    context_info = _get_error_context(cookbook_dir)
    full_error = f"{error_message}\n\nContext: {context_info}"

    return {
        "name": cookbook_name,
        "path": str(cookbook_dir),
        "version": "Error",
        "maintainer": "Error",
        "description": (
            f"Analysis failed: {error_message[:100]}"
            f"{'...' if len(error_message) > 100 else ''}"
        ),
        "dependencies": 0,
        "complexity": "Error",
        "estimated_hours": 0,
        "recommendations": full_error,
        "status": ANALYSIS_STATUS_FAILED,
    }


def _cleanup_progress_indicators(progress_bar, status_text):
    """Clean up progress indicators."""
    progress_bar.empty()
    status_text.empty()


def analyse_project_cookbooks(cookbook_path: str, selected_cookbooks: list[str]):
    """Analyse cookbooks as a project with dependency analysis."""
    st.subheader("Project-Level Analysis Results")

    progress_bar, status_text = _setup_analysis_progress()
    results = _perform_cookbook_analysis(
        cookbook_path, selected_cookbooks, progress_bar, status_text
    )

    # Perform project-level dependency analysis
    status_text.text("Analyzing project dependencies...")
    project_analysis = _analyse_project_dependencies(
        cookbook_path, selected_cookbooks, results
    )

    _cleanup_progress_indicators(progress_bar, status_text)

    # Store results in session state
    st.session_state.analysis_results = results
    st.session_state.analysis_cookbook_path = cookbook_path
    st.session_state.total_cookbooks = len(selected_cookbooks)
    st.session_state.project_analysis = project_analysis

    # Trigger rerun to display results
    st.rerun()


def _analyse_project_dependencies(
    cookbook_path: str, selected_cookbooks: list[str], individual_results: list
) -> dict:
    """Analyze dependencies across all cookbooks in the project."""
    project_analysis = {
        "dependency_graph": {},
        "migration_order": [],
        "circular_dependencies": [],
        "project_complexity": "Low",
        "project_effort_days": 0,
        "migration_strategy": "phased",
        "risks": [],
        "recommendations": [],
    }

    try:
        # Build dependency graph
        dependency_graph = _build_dependency_graph(cookbook_path, selected_cookbooks)
        project_analysis["dependency_graph"] = dependency_graph

        # Determine migration order using topological sort
        migration_order = _calculate_migration_order(
            dependency_graph, individual_results
        )
        project_analysis["migration_order"] = migration_order

        # Identify circular dependencies
        circular_deps = _find_circular_dependencies(dependency_graph)
        project_analysis["circular_dependencies"] = circular_deps

        # Calculate project-level metrics
        project_metrics = _calculate_project_metrics(
            individual_results, dependency_graph
        )
        project_analysis.update(project_metrics)

        # Generate project recommendations
        recommendations = _generate_project_recommendations(
            project_analysis, individual_results
        )
        project_analysis["recommendations"] = recommendations

    except Exception as e:
        st.warning(f"Project dependency analysis failed: {e}")
        # Continue with basic analysis

    return project_analysis


def _build_dependency_graph(cookbook_path: str, selected_cookbooks: list[str]) -> dict:
    """Build a dependency graph for all cookbooks in the project."""
    dependency_graph = {}

    for cookbook_name in selected_cookbooks:
        cookbook_dir = _find_cookbook_directory(cookbook_path, cookbook_name)
        if cookbook_dir:
            try:
                # Use the existing dependency analysis function
                dep_analysis = analyse_cookbook_dependencies(str(cookbook_dir))
                # Parse the markdown response to extract dependencies
                dependencies = _extract_dependencies_from_markdown(dep_analysis)
                dependency_graph[cookbook_name] = dependencies
            except Exception:
                # If dependency analysis fails, assume no dependencies
                dependency_graph[cookbook_name] = []

    return dependency_graph


def _extract_dependencies_from_markdown(markdown_text: str) -> list[str]:
    """Extract dependencies from markdown output of analyse_cookbook_dependencies."""
    dependencies = []

    # Look for the dependency graph section
    lines = markdown_text.split("\n")
    in_graph_section = False

    for line in lines:
        if "## Dependency Graph:" in line:
            in_graph_section = True
        elif in_graph_section and line.startswith("##"):
            break
        elif in_graph_section and "├──" in line:
            # Extract dependency name
            dep_line = line.strip()
            if "├──" in dep_line:
                dep_name = dep_line.split("├──")[-1].strip()
                if dep_name and dep_name != "External dependencies:":
                    dependencies.append(dep_name)

    return dependencies


def _calculate_migration_order(
    dependency_graph: dict, individual_results: list
) -> list[dict]:
    """Calculate optimal migration order using topological sort."""
    order = _perform_topological_sort(dependency_graph)

    # If topological sort failed due to cycles, fall back to complexity-based ordering
    if len(order) != len(dependency_graph):
        order = _fallback_migration_order(individual_results)

    # Convert to detailed order with metadata
    return _build_detailed_migration_order(order, dependency_graph, individual_results)


def _perform_topological_sort(dependency_graph: dict) -> list[str]:
    """Perform topological sort on dependency graph."""
    visited = set()
    temp_visited = set()
    order = []

    def visit(cookbook_name: str) -> bool:
        if cookbook_name in temp_visited:
            return False  # Circular dependency detected
        if cookbook_name in visited:
            return True

        temp_visited.add(cookbook_name)

        # Visit all dependencies first
        for dep in dependency_graph.get(cookbook_name, []):
            if dep in dependency_graph and not visit(dep):
                return False

        temp_visited.remove(cookbook_name)
        visited.add(cookbook_name)
        order.append(cookbook_name)
        return True

    # Visit all cookbooks
    for cookbook_name in dependency_graph:
        if cookbook_name not in visited and not visit(cookbook_name):
            break  # Circular dependency detected

    return order


def _build_detailed_migration_order(
    order: list[str], dependency_graph: dict, individual_results: list
) -> list[dict]:
    """Build detailed migration order with metadata."""
    detailed_order = []
    for i, cookbook_name in enumerate(reversed(order), 1):
        cookbook_result = next(
            (r for r in individual_results if r["name"] == cookbook_name), None
        )
        if cookbook_result:
            detailed_order.append(
                {
                    "phase": i,
                    "cookbook": cookbook_name,
                    "complexity": cookbook_result.get("complexity", "Unknown"),
                    "effort_days": cookbook_result.get("estimated_hours", 0) / 8,
                    "dependencies": dependency_graph.get(cookbook_name, []),
                    "reason": _get_migration_reason(cookbook_name, dependency_graph, i),
                }
            )

    return detailed_order


def _fallback_migration_order(individual_results: list) -> list[str]:
    """Fallback migration order based on complexity (low to high)."""
    # Sort by complexity score (ascending) and then by dependencies (fewer first)
    sorted_results = sorted(
        individual_results,
        key=lambda x: (
            {"Low": 0, "Medium": 1, "High": 2}.get(x.get("complexity", "Medium"), 1),
            x.get("dependencies", 0),
        ),
    )
    return [r["name"] for r in sorted_results]


def _get_migration_reason(
    cookbook_name: str, dependency_graph: dict, phase: int
) -> str:
    """Get the reason for migrating a cookbook at this phase."""
    dependencies = dependency_graph.get(cookbook_name, [])

    if not dependencies:
        return "No dependencies - can be migrated early"
    elif phase == 1:
        return "Foundation cookbook with minimal dependencies"
    else:
        dep_names = ", ".join(dependencies[:3])  # Show first 3 dependencies
        if len(dependencies) > 3:
            dep_names += f" and {len(dependencies) - 3} more"
        return f"Depends on: {dep_names}"


def _detect_cycle_dependency(
    dependency_graph: dict, start: str, current: str, path: list[str]
) -> list[str] | None:
    """Detect a cycle in the dependency graph starting from current node."""
    if current in path:
        # Found a cycle
        cycle_start = path.index(current)
        return path[cycle_start:] + [current]

    path.append(current)

    for dep in dependency_graph.get(current, []):
        if dep in dependency_graph:  # Only check cookbooks in our project
            cycle = _detect_cycle_dependency(dependency_graph, start, dep, path)
            if cycle:
                return cycle

    path.pop()
    return None


def _find_circular_dependencies(dependency_graph: dict) -> list[dict]:
    """Find circular dependencies in the dependency graph."""
    circular_deps = []
    visited = set()

    for cookbook in dependency_graph:
        if cookbook not in visited:
            cycle = _detect_cycle_dependency(dependency_graph, cookbook, cookbook, [])
            if cycle:
                circular_deps.append(
                    {
                        "cookbooks": cycle,
                        "type": "circular_dependency",
                        "severity": "high",
                    }
                )
                # Mark all cycle members as visited to avoid duplicate detection
                visited.update(cycle)

    return circular_deps


def _calculate_project_metrics(
    individual_results: list, dependency_graph: dict
) -> dict:
    """Calculate project-level complexity and effort metrics."""
    total_effort = sum(
        r.get("estimated_hours", 0) / 8 for r in individual_results
    )  # Convert hours to days
    avg_complexity = (
        sum(
            {"Low": 30, "Medium": 50, "High": 80}.get(r.get("complexity", "Medium"), 50)
            for r in individual_results
        )
        / len(individual_results)
        if individual_results
        else 50
    )

    # Determine project complexity
    if avg_complexity > 70:
        project_complexity = "High"
    elif avg_complexity > 40:
        project_complexity = "Medium"
    else:
        project_complexity = "Low"

    # Determine migration strategy based on dependencies and complexity
    total_dependencies = sum(len(deps) for deps in dependency_graph.values())
    has_circular_deps = any(
        len(dependency_graph.get(cb, [])) > 0 for cb in dependency_graph
    )

    if project_complexity == "High" or total_dependencies > len(individual_results) * 2:
        migration_strategy = "phased"
    elif has_circular_deps:
        migration_strategy = "parallel"
    else:
        migration_strategy = "big_bang"

    # Calculate parallel tracks if needed
    parallel_tracks = 1
    if migration_strategy == "parallel":
        parallel_tracks = min(3, max(2, len(individual_results) // 5))

    # Calculate calendar timeline based on strategy
    # This applies strategy multipliers (phased +10%, big_bang -10%, parallel +5%)
    timeline_weeks = get_timeline_weeks(total_effort, strategy=migration_strategy)

    return {
        "project_complexity": project_complexity,
        "project_effort_days": round(total_effort, 1),
        "project_timeline_weeks": timeline_weeks,
        "migration_strategy": migration_strategy,
        "parallel_tracks": parallel_tracks,
        "total_dependencies": total_dependencies,
        "dependency_density": round(total_dependencies / len(individual_results), 2)
        if individual_results
        else 0,
    }


def _generate_project_recommendations(
    project_analysis: dict, individual_results: list
) -> list[str]:
    """Generate project-level recommendations."""
    recommendations = []

    strategy = project_analysis.get("migration_strategy", "phased")
    complexity = project_analysis.get("project_complexity", "Medium")
    effort_days = project_analysis.get("project_effort_days", 0)
    circular_deps = project_analysis.get("circular_dependencies", [])

    # Strategy recommendations
    if strategy == "phased":
        recommendations.append(
            "• Use phased migration approach due to project complexity and dependencies"
        )
        recommendations.append(
            "• Start with foundation cookbooks (minimal dependencies) in Phase 1"
        )
        recommendations.append("• Migrate dependent cookbooks in subsequent phases")
    elif strategy == "parallel":
        tracks = project_analysis.get("parallel_tracks", 2)
        recommendations.append(
            f"• Use parallel migration with {tracks} tracks to handle complexity"
        )
        recommendations.append("• Assign dedicated teams to each migration track")
    else:
        recommendations.append("• Big-bang migration suitable for this project scope")

    # Complexity-based recommendations
    if complexity == "High":
        recommendations.append(
            "• Allocate senior Ansible engineers for complex cookbook conversions"
        )
        recommendations.append("• Plan for extensive testing and validation phases")
    elif complexity == "Medium":
        recommendations.append(
            "• Standard engineering team with Ansible experience sufficient"
        )
        recommendations.append("• Include peer reviews for quality assurance")

    # Effort-based recommendations
    if effort_days > 30:
        recommendations.append("• Consider extending timeline to reduce team pressure")
        recommendations.append(
            "• Break migration into 2-week sprints with deliverables"
        )
    else:
        recommendations.append("• Timeline suitable for focused migration effort")

    # Dependency recommendations
    dependency_density = project_analysis.get("dependency_density", 0)
    if dependency_density > 2:
        recommendations.append(
            "• High dependency density - prioritize dependency resolution"
        )
        recommendations.append("• Create shared Ansible roles for common dependencies")

    # Circular dependency warnings
    if circular_deps:
        recommendations.append(
            f"• {len(circular_deps)} circular dependency groups detected"
        )
        recommendations.append(
            "• Resolve circular dependencies before migration begins"
        )
        recommendations.append("• Consider refactoring interdependent cookbooks")

    # Team and resource recommendations
    total_cookbooks = len(individual_results)
    if total_cookbooks > 10:
        recommendations.append(
            "• Large project scope - consider dedicated migration team"
        )
    else:
        recommendations.append("• Project size manageable with existing team capacity")

    return recommendations


def _display_analysis_results(results, total_cookbooks):
    """Display the complete analysis results."""
    # Display stored analysis info messages if available
    if "analysis_info_messages" in st.session_state:
        for message in st.session_state.analysis_info_messages:
            st.info(message)
        st.success(
            f"✓ Analysis completed! Analysed {len(results)} cookbook(s) with "
            f"detailed AI insights."
        )

    # Add a back button to return to analysis selection
    col1, _ = st.columns([1, 4])
    with col1:
        if st.button(
            "Analyse More Cookbooks",
            help="Return to cookbook selection",
            key="analyse_more",
        ):
            # Clear session state to go back to selection
            st.session_state.analysis_results = None
            st.session_state.analysis_cookbook_path = None
            st.session_state.total_cookbooks = 0
            st.session_state.project_analysis = None
            # Clean up temporary directory when going back
            if st.session_state.temp_dir and st.session_state.temp_dir.exists():
                shutil.rmtree(st.session_state.temp_dir, ignore_errors=True)
                st.session_state.temp_dir = None
            st.rerun()

    st.subheader("Analysis Results")

    _display_analysis_summary(results, total_cookbooks)

    # Display project-level analysis if available
    if "project_analysis" in st.session_state and st.session_state.project_analysis:
        _display_project_analysis(st.session_state.project_analysis)

    _display_results_table(results)
    _display_detailed_analysis(results)
    _display_download_option(results)


def _display_project_analysis(project_analysis: dict):
    """Display project-level analysis results."""
    st.subheader("Project-Level Analysis")

    # Project metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Project Complexity", project_analysis.get("project_complexity", "Unknown")
        )

    with col2:
        effort_days = project_analysis.get("project_effort_days", 0)
        timeline_weeks = project_analysis.get("project_timeline_weeks", 2)
        effort_hours = effort_days * 8
        st.metric(
            "Total Effort",
            f"{effort_hours:.0f} hours ({timeline_weeks} weeks calendar time)",
        )

    with col3:
        strategy = (
            project_analysis.get("migration_strategy", "phased")
            .replace("_", " ")
            .title()
        )
        st.metric("Migration Strategy", strategy)

    with col4:
        dependencies = project_analysis.get("total_dependencies", 0)
        st.metric("Total Dependencies", dependencies)

    # Migration order
    if project_analysis.get("migration_order"):
        st.subheader("Recommended Migration Order")

        migration_df = pd.DataFrame(project_analysis["migration_order"])
        migration_df = migration_df.rename(
            columns={
                "phase": "Phase",
                "cookbook": "Cookbook",
                "complexity": "Complexity",
                "effort_days": "Effort (Days)",
                "dependencies": "Dependencies",
                "reason": "Migration Reason",
            }
        )

        st.dataframe(migration_df, width="stretch")

    # Dependency graph visualization
    if project_analysis.get("dependency_graph"):
        with st.expander("Dependency Graph"):
            _display_dependency_graph(project_analysis["dependency_graph"])

    # Circular dependencies warning
    if project_analysis.get("circular_dependencies"):
        st.warning("Circular Dependencies Detected")
        for circ in project_analysis["circular_dependencies"]:
            cookbooks = " → ".join(circ["cookbooks"])
            st.write(f"**Cycle:** {cookbooks}")

    # Effort explanation
    with st.expander("Effort vs Timeline"):
        effort_days = project_analysis.get("project_effort_days", 0)
        effort_hours = effort_days * 8
        timeline_weeks = project_analysis.get("project_timeline_weeks", 2)
        strategy = (
            project_analysis.get("migration_strategy", "phased")
            .replace("_", " ")
            .title()
        )
        explanation = (
            f"**Effort**: {effort_hours:.0f} hours ({effort_days:.1f} person-days) "
            f"of actual work\n\n"
            f"**Calendar Timeline**: {timeline_weeks} weeks\n\n"
            f"**Strategy**: {strategy}\n\n"
            f"The difference between effort and timeline accounts for:\n"
            f"• Phased approach adds ~10% overhead for testing between phases\n"
            f"• Parallel execution allows some tasks to overlap\n"
            f"• Dependency constraints may extend the critical path\n"
            f"• Team coordination and integration time"
        )
        st.write(explanation)

    # Project recommendations
    if project_analysis.get("recommendations"):
        with st.expander("Project Recommendations"):
            for rec in project_analysis["recommendations"]:
                st.write(rec)


def _display_dependency_graph(dependency_graph: dict):
    """Display a visual representation of the dependency graph."""
    st.write("**Cookbook Dependencies:**")

    for cookbook, deps in dependency_graph.items():
        if deps:
            deps_str = ", ".join(deps)
            st.write(f"• **{cookbook}** depends on: {deps_str}")
        else:
            st.write(f"• **{cookbook}** (no dependencies)")

    # Show dependency statistics
    total_deps = sum(len(deps) for deps in dependency_graph.values())
    cookbooks_with_deps = sum(1 for deps in dependency_graph.values() if deps)
    isolated_cookbooks = len(dependency_graph) - cookbooks_with_deps

    st.write(f"""
    **Dependency Statistics:**
    - Total dependencies: {total_deps}
    - Cookbooks with dependencies: {cookbooks_with_deps}
    - Independent cookbooks: {isolated_cookbooks}
    - Average dependencies per cookbook: {total_deps / len(dependency_graph):.1f}
    """)


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
        key="convert_to_ansible_playbooks",
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
            st.info(f"Using AI-enhanced conversion with {provider} ({model})")
        else:
            st.info(
                "Using deterministic conversion. Configure AI settings "
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

    successful_results = [r for r in results if r["status"] == ANALYSIS_STATUS_ANALYSED]
    failed_results = [r for r in results if r["status"] == ANALYSIS_STATUS_FAILED]

    if successful_results:
        st.markdown("### Successfully Analysed Cookbooks")
        for result in successful_results:
            _display_single_cookbook_details(result)

    if failed_results:
        st.markdown("### Failed Analysis Cookbooks")
        for result in failed_results:
            _display_failed_cookbook_details(result)


def _validate_cookbook_structure(cookbook_dir: Path) -> dict:
    """Validate the basic structure of a cookbook for analysis."""
    validation = {}

    # Check if directory exists
    validation["Cookbook directory exists"] = (
        cookbook_dir.exists() and cookbook_dir.is_dir()
    )

    if not validation["Cookbook directory exists"]:
        return validation

    # Check metadata.rb
    metadata_file = cookbook_dir / METADATA_FILENAME
    validation["metadata.rb exists"] = metadata_file.exists()

    # Check recipes directory
    recipes_dir = cookbook_dir / "recipes"
    validation["recipes/ directory exists"] = (
        recipes_dir.exists() and recipes_dir.is_dir()
    )

    if validation["recipes/ directory exists"]:
        recipe_files = list(recipes_dir.glob("*.rb"))
        validation["Has recipe files"] = len(recipe_files) > 0
        validation["Has default.rb recipe"] = (recipes_dir / "default.rb").exists()
    else:
        validation["Has recipe files"] = False
        validation["Has default.rb recipe"] = False

    # Check for common cookbook directories
    common_dirs = ["attributes", "templates", "files", "libraries", "definitions"]
    for dir_name in common_dirs:
        dir_path = cookbook_dir / dir_name
        validation[f"{dir_name}/ directory exists"] = (
            dir_path.exists() and dir_path.is_dir()
        )

    return validation


def _display_single_cookbook_details(result):
    """Display detailed information for a successfully analysed cookbook."""
    with st.expander(f"{result['name']} - Analysis Complete", expanded=True):
        # Basic information
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Version", result.get("version", "Unknown"))
        with col2:
            st.metric("Maintainer", result.get("maintainer", "Unknown"))
        with col3:
            st.metric("Dependencies", result.get("dependencies", 0))

        # Complexity and effort
        col1, col2 = st.columns(2)
        with col1:
            complexity = result.get("complexity", "Unknown")
            if complexity == "High":
                st.metric("Complexity", complexity, delta="High")
            elif complexity == "Medium":
                st.metric("Complexity", complexity, delta="Medium")
            else:
                st.metric("Complexity", complexity, delta="Low")
        with col2:
            hours = result.get("estimated_hours", 0)
            st.metric("Estimated Hours", f"{hours:.1f}")

        # Path
        st.write(f"**Cookbook Path:** {result['path']}")

        # Recommendations
        if result.get("recommendations"):
            st.markdown("**Analysis Recommendations:**")
            st.info(result["recommendations"])


def _display_failed_cookbook_details(result):
    """Display detailed failure information for a cookbook."""
    with st.expander(f"{result['name']} - Analysis Failed", expanded=True):
        st.error(f"**Analysis Error:** {result['recommendations']}")

        # Show cookbook path
        st.write(f"**Cookbook Path:** {result['path']}")

        # Try to show some basic validation info
        cookbook_dir = Path(result["path"])
        validation_info = _validate_cookbook_structure(cookbook_dir)

        if validation_info:
            st.markdown("**Cookbook Structure Validation:**")
            for check, status in validation_info.items():
                icon = "✓" if status else "✗"
                st.write(f"{icon} {check}")

        # Suggest fixes
        st.markdown("**Suggested Fixes:**")
        st.markdown("""
        - Check if `metadata.rb` exists and is valid Ruby syntax
        - Ensure `recipes/` directory exists with at least one `.rb` file
        - Verify cookbook dependencies are properly declared
        - Check for syntax errors in recipe files
        - Ensure the cookbook follows standard Chef structure
        """)

        # Show raw error details in a collapsible section
        with st.expander("Technical Error Details"):
            st.code(result["recommendations"], language="text")


def _convert_and_download_playbooks(results):
    """Convert analysed cookbooks to Ansible playbooks and provide download."""
    successful_results = [r for r in results if r["status"] == ANALYSIS_STATUS_ANALYSED]

    if not successful_results:
        st.warning("No successfully analysed cookbooks to convert.")
        return

    # Get project recommendations from session state
    project_recommendations = None
    if "project_analysis" in st.session_state and st.session_state.project_analysis:
        project_recommendations = st.session_state.project_analysis

    with st.spinner("Converting cookbooks to Ansible playbooks..."):
        playbooks = []
        templates = []

        for result in successful_results:
            # _convert_single_cookbook now returns tuple of (playbooks, templates)
            cookbook_playbooks, cookbook_templates = _convert_single_cookbook(
                result, project_recommendations
            )
            if cookbook_playbooks:
                playbooks.extend(cookbook_playbooks)
            if cookbook_templates:
                templates.extend(cookbook_templates)

        st.info(
            f"Total: {len(playbooks)} playbook(s) and {len(templates)} "
            f"template(s) ready for download"
        )

    if playbooks:
        # Save converted playbooks to temporary directory for validation
        try:
            output_dir = Path(tempfile.mkdtemp(prefix="souschef_converted_"))
            with contextlib.suppress(FileNotFoundError, OSError):
                output_dir.chmod(0o700)  # Secure permissions: rwx------
            for _i, playbook in enumerate(playbooks):
                # Sanitize filename - include recipe name to avoid conflicts
                recipe_name = playbook["recipe_file"].replace(".rb", "")
                cookbook_name = _sanitize_filename(playbook["cookbook_name"])
                recipe_name = _sanitize_filename(recipe_name)
                filename = f"{cookbook_name}_{recipe_name}.yml"
                (output_dir / filename).write_text(playbook["playbook_content"])

            # Store path in session state for validation page
            st.session_state.converted_playbooks_path = str(output_dir)
            st.success("Playbooks converted and staged for validation.")
        except Exception as e:
            st.warning(f"Could not stage playbooks for validation: {e}")

    _handle_playbook_download(playbooks, templates)


def _convert_single_cookbook(
    result: dict, project_recommendations: dict | None = None
) -> tuple[list, list]:
    """
    Convert entire cookbook (all recipes) to Ansible playbooks.

    Args:
        result: Cookbook analysis result.
        project_recommendations: Optional project recommendations.

    Returns:
        Tuple of (playbooks list, templates list).

    """
    cookbook_dir = Path(result["path"])
    recipes_dir = cookbook_dir / "recipes"

    if not recipes_dir.exists():
        st.warning(f"No recipes directory found in {result['name']}")
        return [], []

    recipe_files = list(recipes_dir.glob("*.rb"))
    if not recipe_files:
        st.warning(f"No recipe files found in {result['name']}")
        return [], []

    # Convert recipes
    converted_playbooks = _convert_recipes(
        result["name"], recipe_files, project_recommendations
    )

    # Convert templates
    converted_templates = _convert_templates(result["name"], cookbook_dir)

    return converted_playbooks, converted_templates


def _convert_recipes(
    cookbook_name: str, recipe_files: list, project_recommendations: dict | None
) -> list:
    """
    Convert all recipes in a cookbook.

    Args:
        cookbook_name: Name of the cookbook.
        recipe_files: List of recipe file paths.
        project_recommendations: Optional project recommendations.

    Returns:
        List of converted playbooks.

    """
    ai_config = load_ai_settings()
    provider_name = _get_ai_provider(ai_config)
    use_ai = (
        provider_name and provider_name != LOCAL_PROVIDER and ai_config.get("api_key")
    )

    provider_mapping = {
        ANTHROPIC_CLAUDE_DISPLAY: "anthropic",
        ANTHROPIC_PROVIDER: "anthropic",
        "OpenAI": "openai",
        OPENAI_PROVIDER: "openai",
        IBM_WATSONX: "watson",
        RED_HAT_LIGHTSPEED: "lightspeed",
    }
    ai_provider = provider_mapping.get(
        provider_name,
        provider_name.lower().replace(" ", "_") if provider_name else "anthropic",
    )

    converted_playbooks = []
    api_key = _get_ai_string_value(ai_config, "api_key", "")
    model = _get_ai_string_value(ai_config, "model", "claude-3-5-sonnet-20241022")
    temperature = _get_ai_float_value(ai_config, "temperature", 0.7)
    max_tokens = _get_ai_int_value(ai_config, "max_tokens", 4000)
    project_id = _get_ai_string_value(ai_config, "project_id", "")
    base_url = _get_ai_string_value(ai_config, "base_url", "")

    for recipe_file in recipe_files:
        try:
            if use_ai:
                playbook_content = generate_playbook_from_recipe_with_ai(
                    str(recipe_file),
                    ai_provider=ai_provider,
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    project_id=project_id,
                    base_url=base_url,
                    project_recommendations=project_recommendations,
                )
            else:
                playbook_content = generate_playbook_from_recipe(str(recipe_file))

            if not playbook_content.startswith("Error"):
                converted_playbooks.append(
                    {
                        "cookbook_name": cookbook_name,
                        "playbook_content": playbook_content,
                        "recipe_file": recipe_file.name,
                        "conversion_method": "AI-enhanced"
                        if use_ai
                        else "Deterministic",
                    }
                )
            else:
                st.warning(f"Failed to convert {recipe_file.name}: {playbook_content}")
        except Exception as e:
            st.warning(f"Failed to convert {recipe_file.name}: {e}")

    return converted_playbooks


def _convert_templates(cookbook_name: str, cookbook_dir: Path) -> list:
    """
    Convert all templates in a cookbook.

    Args:
        cookbook_name: Name of the cookbook.
        cookbook_dir: Path to cookbook directory.

    Returns:
        List of converted templates.

    """
    converted_templates = []
    template_results = convert_cookbook_templates(str(cookbook_dir))

    if template_results.get("success"):
        for template_result in template_results.get("results", []):
            if template_result["success"]:
                converted_templates.append(
                    {
                        "cookbook_name": cookbook_name,
                        "template_content": template_result["jinja2_content"],
                        "template_file": Path(template_result["jinja2_file"]).name,
                        "original_file": Path(template_result["original_file"]).name,
                        "variables": template_result["variables"],
                    }
                )
        if converted_templates:
            st.info(
                f"Converted {len(converted_templates)} template(s) from {cookbook_name}"
            )
    elif not template_results.get("message"):
        st.warning(
            f"Template conversion failed for {cookbook_name}: "
            f"{template_results.get('error', 'Unknown error')}"
        )

    return converted_templates


def _find_recipe_file(cookbook_dir: Path, cookbook_name: str) -> Path | None:
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


def _handle_playbook_download(playbooks: list, templates: list | None = None) -> None:
    """Handle the download of generated playbooks."""
    if not playbooks:
        st.error("No playbooks were successfully generated.")
        return

    templates = templates or []
    playbook_archive = _create_playbook_archive(playbooks, templates)

    # Display success and statistics
    unique_cookbooks = len({p["cookbook_name"] for p in playbooks})
    template_count = len(templates)
    st.success(
        f"Successfully converted {unique_cookbooks} cookbook(s) with "
        f"{len(playbooks)} recipe(s) and {template_count} template(s) to Ansible!"
    )

    # Show summary
    _display_playbook_summary(len(playbooks), template_count)

    # Provide download button
    _display_download_button(len(playbooks), template_count, playbook_archive)

    # Show previews
    _display_playbook_previews(playbooks)
    _display_template_previews(templates)


def _display_playbook_summary(playbook_count: int, template_count: int) -> None:
    """Display summary of archive contents."""
    if template_count > 0:
        st.info(
            f"Archive includes:\n"
            f"- {playbook_count} playbook files (.yml)\n"
            f"- {template_count} template files (.j2)\n"
            f"- README.md with conversion details"
        )
    else:
        st.info(
            f"Archive includes:\n"
            f"- {playbook_count} playbook files (.yml)\n"
            f"- README.md with conversion details\n"
            f"- Note: No templates were found in the converted cookbooks"
        )


def _display_download_button(
    playbook_count: int, template_count: int, archive_data: bytes
) -> None:
    """Display the download button for the archive."""
    download_label = f"Download Ansible Playbooks ({playbook_count} playbooks"
    if template_count > 0:
        download_label += f", {template_count} templates"
    download_label += ")"

    st.download_button(
        label=download_label,
        data=archive_data,
        file_name="ansible_playbooks.zip",
        mime="application/zip",
        help=f"Download ZIP archive containing {playbook_count} playbooks "
        f"and {template_count} templates",
    )


def _display_playbook_previews(playbooks: list) -> None:
    """Display preview of generated playbooks."""
    with st.expander("Preview Generated Playbooks", expanded=True):
        for playbook in playbooks:
            conversion_badge = (
                "AI-Enhanced"
                if playbook.get("conversion_method") == "AI-enhanced"
                else "Deterministic"
            )
            st.subheader(
                f"{playbook['cookbook_name']} ({conversion_badge}) - "
                f"from {playbook['recipe_file']}"
            )
            content = playbook["playbook_content"]
            preview = content[:1000] + "..." if len(content) > 1000 else content
            st.code(preview, language="yaml")
            st.divider()


def _display_template_previews(templates: list) -> None:
    """Display preview of converted templates."""
    if not templates:
        return

    with st.expander(
        f"Preview Converted Templates ({len(templates)} templates)", expanded=True
    ):
        for template in templates:
            st.subheader(
                f"{template['cookbook_name']}/templates/{template['template_file']}"
            )
            st.caption(f"Converted from: {template['original_file']}")

            # Show extracted variables
            if template.get("variables"):
                with st.container():
                    st.write("**Variables used in template:**")
                    st.code(", ".join(template["variables"]), language="text")

            # Show template content preview
            content = template["template_content"]
            preview = content[:500] + "..." if len(content) > 500 else content
            st.code(preview, language="jinja2")
            st.divider()


def _create_playbook_archive(playbooks, templates=None):
    """Create a ZIP archive containing all generated Ansible playbooks and templates."""
    zip_buffer = io.BytesIO()
    templates = templates or []

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Organize playbooks by cookbook in subdirectories
        for playbook in playbooks:
            # Create cookbook directory structure with sanitised names
            cookbook_name = _sanitize_filename(playbook["cookbook_name"])
            recipe_name = _sanitize_filename(playbook["recipe_file"].replace(".rb", ""))
            playbook_filename = f"{cookbook_name}/{recipe_name}.yml"
            zip_file.writestr(playbook_filename, playbook["playbook_content"])

        # Add converted templates
        for template in templates:
            cookbook_name = _sanitize_filename(template["cookbook_name"])
            template_filename = _sanitize_filename(template["template_file"])
            archive_path = f"{cookbook_name}/templates/{template_filename}"
            zip_file.writestr(archive_path, template["template_content"])

        # Count unique cookbooks
        unique_cookbooks = len({p["cookbook_name"] for p in playbooks})
        template_count = len(templates)

        # Add a summary README
        readme_content = f"""# Ansible Playbooks Generated by SousChef

This archive contains {len(playbooks)} Ansible playbooks and {template_count} """
        readme_content += f"templates from {unique_cookbooks} cookbook(s) "
        readme_content += "converted from Chef."

        readme_content += """

## Contents:
"""

        # Group by cookbook for README
        from collections import defaultdict

        by_cookbook = defaultdict(list)
        for playbook in playbooks:
            by_cookbook[playbook["cookbook_name"]].append(playbook)

        # Group templates by cookbook
        by_cookbook_templates = defaultdict(list)
        for template in templates:
            by_cookbook_templates[template["cookbook_name"]].append(template)

        for cookbook_name, cookbook_playbooks in sorted(by_cookbook.items()):
            cookbook_templates = by_cookbook_templates.get(cookbook_name, [])
            # Sanitise cookbook name for display in README
            safe_cookbook_name = _sanitize_filename(cookbook_name)
            readme_content += (
                f"\n### {safe_cookbook_name}/ "
                f"({len(cookbook_playbooks)} recipes, "
                f"{len(cookbook_templates)} templates)\n"
            )
            for playbook in cookbook_playbooks:
                conversion_method = playbook.get("conversion_method", "Deterministic")
                recipe_name = playbook["recipe_file"].replace(".rb", "")
                safe_recipe_name = _sanitize_filename(recipe_name)
                readme_content += (
                    f"  - {safe_recipe_name}.yml "
                    f"(from {playbook['recipe_file']}, "
                    f"{conversion_method})\n"
                )
            if cookbook_templates:
                readme_content += "  - templates/\n"
                for template in cookbook_templates:
                    safe_template_name = _sanitize_filename(template["template_file"])
                    readme_content += (
                        f"    - {safe_template_name} "
                        f"(from {template['original_file']})\n"
                    )

        readme_content += """

## Usage:
Run these playbooks with Ansible:
  ansible-playbook <cookbook_name>/<recipe_name>.yml

## Notes:
- These playbooks were automatically generated from Chef recipes
- Templates have been converted from ERB to Jinja2 format
- Each cookbook's recipes and templates are organized in separate directories
- Review and test before deploying to production
- Review and test the playbooks before using in production
- Some manual adjustments may be required for complex recipes or templates
- Verify that template variables are correctly mapped from Chef to Ansible
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
