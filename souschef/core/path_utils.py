"""Path utility functions for safe filesystem operations."""

import os
from pathlib import Path


def _normalize_path(path_str: str | Path) -> Path:
    """
    Normalize a file path for safe filesystem operations.

    This function validates input and resolves relative paths and symlinks
    to absolute paths, preventing path traversal attacks (CWE-23).

    Args:
        path_str: Path string or Path object to normalize.

    Returns:
        Resolved absolute Path object.

    Raises:
        ValueError: If the path contains null bytes, traversal attempts, or is invalid.

    """
    # Convert Path to string if needed
    if isinstance(path_str, Path):
        path_str = str(path_str)
    elif not isinstance(path_str, str):
        raise ValueError(f"Path must be a string or Path object, got {type(path_str)}")

    # Reject paths with null bytes
    if "\x00" in path_str:
        raise ValueError(f"Path contains null bytes: {path_str!r}")

    # Reject paths with obvious directory traversal attempts
    if ".." in path_str:
        raise ValueError(f"Path contains directory traversal: {path_str!r}")

    try:
        # Use os.path.realpath which CodeQL recognizes as a sanitizer
        normalized = os.path.realpath(path_str)  # noqa: PTH111
        return Path(normalized)
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path {path_str}: {e}") from e


def _safe_join(base_path: Path, *parts: str) -> Path:
    """
    Safely join path components ensuring result stays within base directory.

    Args:
        base_path: Normalized base path.
        *parts: Path components to join.

    Returns:
        Joined path within base_path.

    Raises:
        ValueError: If result would escape base_path.

    """
    # Use os.path.realpath for normalization that CodeQL recognizes
    base_str = os.path.realpath(str(base_path))  # noqa: PTH111

    # Join paths using os.path.join
    joined_str = os.path.join(base_str, *parts)  # noqa: PTH118

    # Normalize the joined path
    result_str = os.path.realpath(joined_str)  # noqa: PTH111

    # Validate result stays under base_path
    base_prefix = base_str + os.sep
    if result_str != base_str and not result_str.startswith(base_prefix):
        msg = f"Path traversal attempt: {parts} escapes {base_path}"
        raise ValueError(msg)

    return Path(result_str)
