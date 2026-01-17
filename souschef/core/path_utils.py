"""Path utility functions for safe filesystem operations."""

from pathlib import Path


def _normalize_path(path_str: str) -> Path:
    """
    Normalize a file path for safe filesystem operations.

    This function validates input and resolves relative paths and symlinks
    to absolute paths, preventing path traversal attacks (CWE-23).

    Args:
        path_str: Path string to normalize.

    Returns:
        Resolved absolute Path object.

    Raises:
        ValueError: If the path contains null bytes, traversal attempts, or is invalid.

    """
    if not isinstance(path_str, str):
        raise ValueError(f"Path must be a string, got {type(path_str)}")

    # Reject paths with null bytes
    if "\x00" in path_str:
        raise ValueError(f"Path contains null bytes: {path_str!r}")

    # Reject paths with obvious directory traversal attempts
    if ".." in path_str:
        raise ValueError(f"Path contains directory traversal: {path_str!r}")

    try:
        # Resolve to absolute path, removing ., and resolving symlinks
        return Path(path_str).resolve()
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
    result = base_path.joinpath(*parts).resolve()
    try:
        result.relative_to(base_path)
        return result
    except ValueError as e:
        raise ValueError(f"Path traversal attempt: {parts} escapes {base_path}") from e
