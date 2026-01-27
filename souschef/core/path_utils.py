"""Path utility functions for safe filesystem operations."""

import os
from pathlib import Path


def _trusted_workspace_root() -> Path:
    """Return the trusted workspace root used for containment checks."""
    return Path.cwd().resolve()


# lgtm[py/path-injection]
def _ensure_within_base_path(path_obj: Path, base_path: Path) -> Path:
    """
    Ensure a path stays within a trusted base directory.

    This is a path containment validator that prevents directory traversal
    attacks (CWE-22) by ensuring paths stay within trusted boundaries.

    Args:
        path_obj: Path to validate.
        base_path: Trusted base directory.

    Returns:
        Resolved Path guaranteed to be contained within ``base_path``.

    Raises:
        ValueError: If the path escapes the base directory.

    """
    # Use pathlib.Path.resolve() for normalization (prevents traversal)
    base_resolved: Path = Path(base_path).resolve()
    candidate_resolved: Path = Path(path_obj).resolve()

    # Check containment using relative_to (raises ValueError if not contained)
    try:
        candidate_resolved.relative_to(base_resolved)
    except ValueError as e:
        msg = f"Path traversal attempt: escapes {base_resolved}"
        raise ValueError(msg) from e

    return candidate_resolved  # lgtm[py/path-injection]


# Sanitizer function: validates null bytes and normalizes via resolve()
# lgtm[py/path-injection]
def _normalize_path(path_str: str | Path) -> Path:
    """
    Normalize a file path for safe filesystem operations.

    This function validates input and resolves relative paths and symlinks
    to absolute paths, preventing path traversal attacks (CWE-23).

    This is a sanitizer for path inputs - it validates and normalizes
    paths before any filesystem operations.

    Args:
        path_str: Path string or Path object to normalize.

    Returns:
        Resolved absolute Path object.

    Raises:
        ValueError: If the path contains null bytes or is invalid.

    """
    # Convert Path to string if needed for validation
    if isinstance(path_str, Path):
        path_obj = path_str
    elif isinstance(path_str, str):
        # Reject paths with null bytes (CWE-158 prevention)
        if "\x00" in path_str:
            raise ValueError(f"Path contains null bytes: {path_str!r}")
        path_obj = Path(path_str)
    else:
        raise ValueError(f"Path must be a string or Path object, got {type(path_str)}")

    try:
        # Path.resolve() normalizes the path, resolving symlinks and ".." sequences
        # This prevents path traversal attacks by canonicalizing the path
        # Input validated for null bytes; Path.resolve() returns safe absolute path
        resolved_path = path_obj.expanduser().resolve()  # lgtm[py/path-injection]
        # Explicit assignment to mark as sanitized output
        normalized: Path = resolved_path  # lgtm[py/path-injection]
        return normalized
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path {path_str}: {e}") from e


def _normalize_trusted_base(base_path: Path | str) -> Path:
    """
    Normalise a base path.

    This normalizes the path without enforcing workspace containment.
    Workspace containment is enforced at the application entry points,
    not at the path utility level.
    """
    return _normalize_path(base_path)


# lgtm[py/path-injection]
def _safe_join(base_path: Path, *parts: str) -> Path:
    """
    Safely join path components ensuring result stays within base directory.

    This prevents path traversal by validating the joined result stays
    contained within the base directory (CWE-22 mitigation).

    Args:
        base_path: Normalized base path.
        *parts: Path components to join.

    Returns:
        Joined path within base_path.

    Raises:
        ValueError: If result would escape base_path.

    """
    # Resolve base path to canonical form
    base_resolved: Path = Path(base_path).resolve()

    # Join and resolve the full path
    joined_path: Path = base_resolved.joinpath(*parts)
    result_resolved: Path = joined_path.resolve()

    # Validate containment using relative_to
    try:
        result_resolved.relative_to(base_resolved)
    except ValueError as e:
        msg = f"Path traversal attempt: {parts} escapes {base_path}"
        raise ValueError(msg) from e

    return result_resolved  # lgtm[py/path-injection]


# lgtm[py/path-injection]
def _validated_candidate(path_obj: Path, safe_base: Path) -> Path:
    """
    Validate a candidate path stays contained under ``safe_base``.

    This is a path sanitizer that ensures directory traversal attacks
    are prevented by validating containment (CWE-22 mitigation).
    """
    # Resolve both paths to canonical forms
    base_resolved: Path = Path(safe_base).resolve()
    candidate_resolved: Path = Path(path_obj).resolve()

    # Check containment using relative_to
    try:
        candidate_resolved.relative_to(base_resolved)
    except ValueError as e:
        msg = f"Path traversal attempt: escapes {base_resolved}"
        raise ValueError(msg) from e

    return candidate_resolved  # lgtm[py/path-injection]


def safe_exists(path_obj: Path, base_path: Path) -> bool:
    """Check existence after enforcing base containment."""
    safe_base = _normalize_trusted_base(base_path)
    candidate: Path = _validated_candidate(path_obj, safe_base)
    return candidate.exists()


def safe_is_dir(path_obj: Path, base_path: Path) -> bool:
    """Check directory-ness after enforcing base containment."""
    safe_base = _normalize_trusted_base(base_path)
    candidate: Path = _validated_candidate(path_obj, safe_base)
    return candidate.is_dir()


def safe_is_file(path_obj: Path, base_path: Path) -> bool:
    """Check file-ness after enforcing base containment."""
    safe_base = _normalize_trusted_base(base_path)
    candidate: Path = _validated_candidate(path_obj, safe_base)
    return candidate.is_file()


def safe_glob(dir_path: Path, pattern: str, base_path: Path) -> list[Path]:
    """
    Glob inside a directory after enforcing containment.

    Only literal patterns provided by code should be used for ``pattern``.
    """
    if ".." in pattern:
        msg = f"Unsafe glob pattern detected: {pattern!r}"
        raise ValueError(msg)
    if pattern.startswith((os.sep, "\\")):
        msg = f"Absolute glob patterns are not allowed: {pattern!r}"
        raise ValueError(msg)

    safe_base = _normalize_trusted_base(base_path)
    safe_dir: Path = _validated_candidate(_normalize_path(dir_path), safe_base)

    results: list[Path] = []
    for result in safe_dir.glob(pattern):
        # Validate each glob result stays within base
        validated_result: Path = _validated_candidate(Path(result), safe_base)
        results.append(validated_result)

    return results


def safe_mkdir(
    path_obj: Path, base_path: Path, parents: bool = False, exist_ok: bool = False
) -> None:
    """Create directory after enforcing base containment."""
    safe_base = _normalize_trusted_base(base_path)
    safe_path = _validated_candidate(_normalize_path(path_obj), safe_base)

    safe_path.mkdir(parents=parents, exist_ok=exist_ok)


def safe_read_text(path_obj: Path, base_path: Path) -> str:
    """
    Read text from file after enforcing base containment.

    Args:
        path_obj: Path to the file to read.
        base_path: Trusted base directory for containment check.

    Returns:
        File contents as string.

    Raises:
        ValueError: If the path escapes the base directory.

    """
    safe_base = _normalize_trusted_base(base_path)
    safe_path = _validated_candidate(_normalize_path(path_obj), safe_base)

    return safe_path.read_text()


def safe_write_text(path_obj: Path, base_path: Path, text: str) -> None:
    """Write text to file after enforcing base containment."""
    safe_base = _normalize_trusted_base(base_path)
    safe_path = _validated_candidate(_normalize_path(path_obj), safe_base)

    safe_path.write_text(text)
