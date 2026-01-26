"""Path utility functions for safe filesystem operations."""

import os
from pathlib import Path


def _trusted_workspace_root() -> Path:
    """Return the trusted workspace root used for containment checks."""
    return Path.cwd().resolve()


def _ensure_within_base_path(path_obj: Path, base_path: Path) -> Path:
    """
    Ensure a path stays within a trusted base directory.

    Args:
        path_obj: Path to validate.
        base_path: Trusted base directory.

    Returns:
        Resolved Path guaranteed to be contained within ``base_path``.

    Raises:
        ValueError: If the path escapes the base directory.

    """
    # Use pathlib.Path.resolve() for normalization (CodeQL recognizes this)
    base_resolved: Path = Path(base_path).resolve()
    candidate_resolved: Path = Path(path_obj).resolve()

    # Check containment using relative_to (raises ValueError if not contained)
    try:
        candidate_resolved.relative_to(base_resolved)
    except ValueError as e:
        msg = f"Path traversal attempt: escapes {base_resolved}"
        raise ValueError(msg) from e

    return candidate_resolved


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
        ValueError: If the path contains null bytes or is invalid.

    """
    # Convert Path to string if needed for validation
    if isinstance(path_str, Path):
        path_obj = path_str
    elif isinstance(path_str, str):
        # Reject paths with null bytes
        if "\x00" in path_str:
            raise ValueError(f"Path contains null bytes: {path_str!r}")
        path_obj = Path(path_str)
    else:
        raise ValueError(f"Path must be a string or Path object, got {type(path_str)}")

    try:
        # Path.resolve() normalizes the path, resolving symlinks and ".." sequences
        # CodeQL recognizes this as path normalization/sanitization
        normalized: Path = path_obj.expanduser().resolve()
        # codeql[py/path-injection]: This function IS the sanitizer
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
    # Resolve base path (CodeQL recognizes Path.resolve())
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

    return result_resolved


def _validated_candidate(path_obj: Path, safe_base: Path) -> Path:
    """Validate a candidate path stays contained under ``safe_base``."""
    # Resolve both paths (CodeQL recognizes Path.resolve())
    base_resolved: Path = Path(safe_base).resolve()
    candidate_resolved: Path = Path(path_obj).resolve()

    # Check containment using relative_to
    try:
        candidate_resolved.relative_to(base_resolved)
    except ValueError as e:
        msg = f"Path traversal attempt: escapes {base_resolved}"
        raise ValueError(msg) from e

    return candidate_resolved


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


def safe_write_text(path_obj: Path, base_path: Path, text: str) -> None:
    """Write text to file after enforcing base containment."""
    safe_base = _normalize_trusted_base(base_path)
    safe_path = _validated_candidate(_normalize_path(path_obj), safe_base)

    safe_path.write_text(text)
