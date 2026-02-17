"""Security functions for archive extraction and validation in SousChef UI."""

import copy
import inspect
import tarfile
from pathlib import Path
from typing import Any

from souschef.core.path_utils import (
    _ensure_within_base_path,
    _safe_join,
)

# Archive size/complexity limits
ANALYSIS_STATUS_ANALYSED = "Analysed"
ANALYSIS_STATUS_FAILED = "Failed"

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
    ".zip",
    ".rar",
    ".7z",
    ".iso",
    ".dmg",
    ".app",
}


def _extract_zip_securely(archive_path: Path, extraction_dir: Path) -> None:
    """Extract ZIP archive with security checks."""
    import zipfile

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
                safe_path.mkdir(parents=True, exist_ok=True)
            else:
                safe_path.parent.mkdir(parents=True, exist_ok=True)

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
    """
    Extract TAR archive with resource consumption controls (S5042).

    Resource consumption is controlled via:
    - Pre-scanning all members before extraction
    - Validating file sizes, counts, and directory depth
    - Using tarfile.filter='data' (Python 3.12+) to prevent symlink traversal
    - Limiting extraction to validated safe paths

    """
    mode = "r:gz" if gzipped else "r"

    if not archive_path.is_file():
        raise ValueError(f"Archive path is not a file: {archive_path}")

    if not tarfile.is_tarfile(str(archive_path)):
        raise ValueError(f"Invalid or corrupted TAR archive: {archive_path.name}")

    try:
        open_kwargs: dict[str, Any] = {"name": str(archive_path), "mode": mode}

        # Apply safe filter if available (Python 3.12+) to prevent traversal attacks.
        # For older Python versions, resource consumption is controlled via pre-scanning
        # and member validation before extraction.
        if "filter" in inspect.signature(tarfile.open).parameters:
            # Use 'data' filter to prevent extraction of special files and symlinks
            open_kwargs["filter"] = "data"

        # Resource consumption controls (S5042): Pre-scan validates all members for
        # size limits (MAX_ARCHIVE_SIZE, MAX_FILE_SIZE), file count (MAX_FILES),
        # depth (MAX_DEPTH), and blocks malicious files before extraction.
        # Security: Validated via _pre_scan_tar_members + _extract_tar_members
        with tarfile.open(**open_kwargs) as tar_ref:  # NOSONAR
            members = tar_ref.getmembers()
            # Pre-validate all members before allowing extraction
            # This controls resource consumption and prevents
            # zip bombs/decompression bombs
            _pre_scan_tar_members(members)
            # Extract only validated members to pre-validated safe paths
            _extract_tar_members(tar_ref, members, extraction_dir)
    except tarfile.TarError as e:
        raise ValueError(f"Invalid or corrupted TAR archive: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to process TAR archive: {e}") from e


def _pre_scan_tar_members(members):
    """
    Pre-scan TAR members to control resource consumption (S5042).

    Validates all members before extraction to prevent:
    - Compression/decompression bombs (via size limits)
    - Excessive memory consumption (via file count limits)
    - Directory traversal attacks (via depth limits)
    - Malicious file inclusion (via extension and type checks)

    """
    total_size = 0
    for file_count, member in enumerate(members, start=1):
        total_size += member.size
        # Validate member and accumulate size for bounds checking
        _validate_tar_file_security(member, file_count, total_size)


def _extract_tar_members(tar_ref, members, extraction_dir):
    """Extract validated TAR members to the extraction directory."""
    sanitized_members = []
    data_filter = getattr(tarfile, "data_filter", None)

    for member in members:
        safe_path = _get_safe_extraction_path(member.name, extraction_dir)
        safe_relative = safe_path.relative_to(extraction_dir.resolve()).as_posix()
        sanitized_member = copy.copy(member)
        sanitized_member.name = safe_relative

        if data_filter is not None:
            sanitized_member = data_filter(sanitized_member, str(extraction_dir))
            if sanitized_member is None:
                continue

        sanitized_members.append(sanitized_member)

    if sanitized_members:
        tar_ref.extractall(
            path=extraction_dir, members=sanitized_members
        )  # NOSONAR - resource consumption controlled with file size/count limits


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
    """
    Get a safe path for extraction that prevents TarSlip (CWE-22).

    Validates that extracted paths stay within the extraction directory,
    preventing directory traversal and TarSlip attacks.
    """
    # Reject paths with directory traversal attempts or absolute paths
    # These attack vectors prevent TarSlip/Zip-slip attacks
    if (
        ".." in filename
        or filename.startswith("/")
        or "\\" in filename
        or ":" in filename
    ):
        raise ValueError(f"Path traversal or absolute path detected: {filename}")

    # Normalise separators and join using a containment-checked join
    normalized = filename.replace("\\", "/").strip("/")
    # _ensure_within_base_path validates the resolved path is within base
    safe_path = _ensure_within_base_path(
        _safe_join(extraction_dir.resolve(), normalized), extraction_dir.resolve()
    )

    return safe_path
