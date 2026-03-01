"""Path utility functions for safe filesystem operations."""

import os
import re
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
    base_resolved: Path = Path(base_path).resolve()
    candidate_resolved: Path = Path(path_obj).resolve()

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

    This is a sanitizer for path inputs - it validates and normalizes
    paths before any filesystem operations.

    Args:
        path_str: Path string or Path object to normalize.

    Returns:
        Resolved absolute Path object.

    Raises:
        ValueError: If the path contains null bytes or is invalid.

    """
    if isinstance(path_str, Path):
        path_obj = path_str
    elif isinstance(path_str, str):
        if "\x00" in path_str:
            raise ValueError(f"Path contains null bytes: {path_str!r}")
        path_obj = Path(path_str)
    else:
        raise ValueError(f"Path must be a string or Path object, got {type(path_str)}")

    try:
        resolved_path = path_obj.expanduser().resolve()
        normalized: Path = resolved_path
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


def _validate_relative_parts(parts: tuple[str, ...]) -> Path:
    """
    Validate and normalise relative path components.

    Args:
        parts: Path components provided by callers.

    Returns:
        A relative Path composed from the validated parts.

    Raises:
        ValueError: If any part is absolute or attempts traversal.

    """
    for part in parts:
        part_path = Path(part)
        if part_path.is_absolute():
            raise ValueError(f"Path traversal attempt: {part}")
        if ".." in part_path.parts:
            raise ValueError(f"Path traversal attempt: {part}")

    relative = Path(*parts)
    if relative.is_absolute():
        raise ValueError(f"Path traversal attempt: {relative}")

    return relative


def _resolve_path_under_base(path_obj: Path | str, base_path: Path | str) -> Path:
    """
    Resolve ``path_obj`` and enforce that it remains under ``base_path``.

    This function normalizes both paths, rejects relative traversal, and then
    validates canonical containment before filesystem I/O occurs.
    """
    safe_base = _normalize_trusted_base(base_path)
    base_resolved = os.path.realpath(str(safe_base))

    raw_value = str(path_obj)
    if "\x00" in raw_value:
        raise ValueError(f"Path contains null bytes: {raw_value!r}")
    if not re.fullmatch(r"[A-Za-z0-9_./\\~:-]+", raw_value):
        raise ValueError(f"Path contains invalid characters: {raw_value!r}")

    raw_path = Path(raw_value).expanduser()
    if raw_path.is_absolute():
        candidate_resolved = os.path.realpath(str(raw_path))
    else:
        relative = _validate_relative_parts(raw_path.parts)
        candidate_resolved = os.path.realpath(str(Path(base_resolved) / relative))

    try:
        common = os.path.commonpath([candidate_resolved, base_resolved])
    except ValueError as e:
        msg = f"Path traversal attempt: escapes {safe_base}"
        raise ValueError(msg) from e

    if common != base_resolved:
        msg = f"Path traversal attempt: escapes {safe_base}"
        raise ValueError(msg)

    return _ensure_within_base_path(Path(candidate_resolved), Path(base_resolved))


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
    base_resolved = _normalize_trusted_base(base_path)
    relative_parts = _validate_relative_parts(parts)
    candidate = base_resolved / relative_parts
    return _resolve_path_under_base(candidate, base_resolved)


def _validated_candidate(path_obj: Path | str, safe_base: Path | str) -> Path:
    """
    Validate a candidate path stays contained under ``safe_base``.

    This is a path sanitizer that ensures directory traversal attacks
    are prevented by validating containment (CWE-22 mitigation).
    """
    return _resolve_path_under_base(path_obj, safe_base)


def safe_exists(path_obj: Path, base_path: Path) -> bool:
    """Check existence after enforcing base containment."""
    candidate = _resolve_path_under_base(path_obj, base_path)
    return candidate.exists()


def safe_is_dir(path_obj: Path, base_path: Path) -> bool:
    """Check directory-ness after enforcing base containment."""
    candidate = _resolve_path_under_base(path_obj, base_path)
    return candidate.is_dir()


def safe_is_file(path_obj: Path, base_path: Path) -> bool:
    """Check file-ness after enforcing base containment."""
    candidate = _resolve_path_under_base(path_obj, base_path)
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
    safe_dir = _resolve_path_under_base(dir_path, safe_base)

    results: list[Path] = []
    for result in safe_dir.glob(pattern):
        validated_result: Path = _resolve_path_under_base(result, safe_base)
        results.append(validated_result)

    return results


def safe_mkdir(
    path_obj: Path, base_path: Path, parents: bool = False, exist_ok: bool = False
) -> None:
    """Create directory after enforcing base containment."""
    safe_path = _resolve_path_under_base(path_obj, base_path)
    safe_path.mkdir(parents=parents, exist_ok=exist_ok)


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
    safe_path = _resolve_path_under_base(path_obj, base_path)
    return safe_path.read_text(encoding=encoding)


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
    safe_path = _resolve_path_under_base(path_obj, base_path)
    safe_path.write_text(text, encoding=encoding)


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
    safe_path = _resolve_path_under_base(path_obj, safe_base)

    results: list[Path] = []
    for item in safe_path.iterdir():
        validated_item: Path = _resolve_path_under_base(item, safe_base)
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
    target: Path = base_path if base_path is not None else path_obj

    try:
        current = target
        while current != current.parent:
            if current.is_symlink():
                msg = (
                    f"Symlink detected in path {target}: {current} -> "
                    f"{current.resolve()}"
                )
                raise ValueError(msg)
            current = current.parent
    except (FileNotFoundError, PermissionError, NotADirectoryError):
        return
