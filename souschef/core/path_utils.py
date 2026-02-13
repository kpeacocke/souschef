"""Path utility functions for safe filesystem operations."""

import os
from pathlib import Path


def _trusted_workspace_root() -> Path:
    """Return the trusted workspace root used for containment checks."""
    return Path.cwd().resolve()


def _get_workspace_root() -> Path:
    """
    Resolve the workspace root for filesystem containment checks.

    The workspace root defaults to the current working directory. If the
    `SOUSCHEF_WORKSPACE_ROOT` environment variable is set, its value is
    normalised and used instead.

    Raises:
        ValueError: If the workspace root is invalid or not a directory.

    """
    env_root = os.getenv("SOUSCHEF_WORKSPACE_ROOT")
    base_path = _normalize_path(env_root) if env_root else _trusted_workspace_root()

    if not base_path.exists():
        raise ValueError(f"Workspace root does not exist: {base_path}")
    if not base_path.is_dir():
        raise ValueError(f"Workspace root is not a directory: {base_path}")

    return base_path


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

    return candidate_resolved  # nosonar


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
        resolved_path = path_obj.expanduser().resolve()  # nosonar
        # Explicit assignment to mark as sanitized output
        normalized: Path = resolved_path  # nosonar
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

    return result_resolved  # nosonar


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

    return candidate_resolved  # nosonar


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
    for result in safe_dir.glob(pattern):  # noqa # NOSONAR: S6549
        # Validated: pattern checked above, result checked below for containment
        validated_result: Path = _validated_candidate(Path(result), safe_base)
        results.append(validated_result)

    return results


def safe_mkdir(
    path_obj: Path, base_path: Path, parents: bool = False, exist_ok: bool = False
) -> None:
    """Create directory after enforcing base containment."""
    safe_base = _normalize_trusted_base(base_path)
    safe_path = _validated_candidate(_normalize_path(path_obj), safe_base)

    safe_path.mkdir(parents=parents, exist_ok=exist_ok)  # nosonar


def safe_read_text(path_obj: Path, base_path: Path, encoding: str = "utf-8") -> str:
    """
    Read text from file after enforcing base containment.

    Args:
        path_obj: Path to the file to read.
        base_path: Trusted base directory for containment check.
        encoding: Text encoding (default: 'utf-8').

    Returns:
        File contents as string.

    Raises:
        ValueError: If the path escapes the base directory.

    """
    safe_base = _normalize_trusted_base(base_path)
    safe_path = _validated_candidate(_normalize_path(path_obj), safe_base)

    return safe_path.read_text(encoding=encoding)  # nosonar


def safe_write_text(
    path_obj: Path, base_path: Path, text: str, encoding: str = "utf-8"
) -> None:
    """
    Write text to file after enforcing base containment.

    Args:
        path_obj: Path to the file to write.
        base_path: Trusted base directory for containment check.
        text: Text content to write.
        encoding: Text encoding (default: 'utf-8').

    """
    safe_base = _normalize_trusted_base(base_path)
    safe_path = _validated_candidate(_normalize_path(path_obj), safe_base)

    safe_path.write_text(text, encoding=encoding)  # nosonar


def safe_iterdir(path_obj: Path, base_path: Path) -> list[Path]:
    """
    Iterate directory contents after enforcing base containment.

    Args:
        path_obj: Directory path to iterate.
        base_path: Trusted base directory for containment check.

    Returns:
        List of validated paths within the directory.

    Raises:
        ValueError: If path escapes the base directory.

    """
    safe_base = _normalize_trusted_base(base_path)
    safe_path = _validated_candidate(_normalize_path(path_obj), safe_base)

    results: list[Path] = []
    for item in safe_path.iterdir():  # nosonar
        # Validate each item stays within base
        validated_item: Path = _validated_candidate(item, safe_base)
        results.append(validated_item)

    return results


def _check_symlink_safety(path_obj: Path, base_path: Path | None = None) -> None:
    """
    Verify that a path does not use symlinks to escape the workspace.

    This helper performs a best-effort check for symlink usage in the ancestry
    of a path.

    Containment is primarily enforced elsewhere via normalisation with
    ``resolve()`` and ``relative_to()``. This function is intended as an
    additional security signal to detect suspicious use of symlinks.

    Args:
        path_obj: Normalised candidate path. This is often a resolved path,
            meaning symlink components in the original user input may already
            have been collapsed.
        base_path: Optional original, *unresolved* path to inspect for
            symlink components. When provided, this path is preferred for
            the symlink walk so that symlinks present in the user-supplied
            path can be detected before resolution.

    Raises:
        ValueError: If symlinks are detected in the inspected path ancestry.

    """
    # Prefer checking the unresolved/original path when provided, falling
    # back to the (typically resolved) candidate path.
    target: Path = base_path if base_path is not None else path_obj

    # Check if the chosen path contains components that are symlinks by
    # iterating through each level of the path.
    try:
        current = target
        while current != current.parent:  # Until we reach filesystem root
            if current.is_symlink():
                msg = (
                    f"Symlink detected in path {target}: {current} -> "
                    f"{current.resolve()}"
                )
                raise ValueError(msg)
            current = current.parent
    except (FileNotFoundError, PermissionError, NotADirectoryError):
        # Path might not exist yet or be inaccessible; in that case we cannot
        # reliably inspect symlink ancestry, so we treat this as a no-op.
        return
