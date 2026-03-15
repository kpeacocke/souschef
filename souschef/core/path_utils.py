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
    if env_root:
        # env_root is an admin/system-supplied value, not user input; it is safe
        # to expand tilde here before delegating to _normalize_path.
        expanded_root = Path(env_root).expanduser()
        base_path = _normalize_path(expanded_root)
    else:
        base_path = _trusted_workspace_root()

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

    Both paths are normalised with ``_normalize_path`` (pure
    ``normpath``/``cwd`` operations — no filesystem I/O on user-controlled
    data) and then compared with ``relative_to`` (pure string operation).
    This avoids calling ``Path.resolve()`` or ``os.path.realpath()`` on
    user-supplied data, which are filesystem I/O sinks under CodeQL
    ``py/path-injection``.

    Note: symlinks are **not** dereferenced by this function.  A symlink
    whose *name* is within ``base_path`` but whose *target* is outside will
    pass this check.  Callers that need symlink safety should call
    ``_check_symlink_safety`` separately.

    Args:
        path_obj: Path to validate.
        base_path: Trusted base directory.

    Returns:
        Normalised Path guaranteed to be contained within ``base_path``
        (based on ``normpath`` string semantics, not resolved symlinks).

    Raises:
        ValueError: If the path escapes the base directory.

    """
    # _normalize_path uses normpath+cwd — no filesystem I/O on user-controlled
    # data (CodeQL py/path-injection safe).  Both paths become absolute strings
    # that can be compared with pure string operations.
    base_resolved: Path = _normalize_path(base_path)
    candidate_resolved: Path = _normalize_path(path_obj)

    try:
        candidate_resolved.relative_to(base_resolved)
    except ValueError as e:
        msg = f"Path traversal attempt: escapes {base_resolved}"
        raise ValueError(msg) from e

    return candidate_resolved


def _normalize_path(path_str: str | Path) -> Path:
    """
    Normalise a file path to an absolute, canonical form.

    This function validates the input for null bytes, then produces an
    absolute, normalised path using ``Path.cwd()`` (trusted system state)
    combined with ``os.path.normpath`` (pure string normalisation).  This
    is semantically equivalent to ``os.path.abspath()`` but expressed in
    pathlib terms.

    No filesystem I/O is performed on the user-controlled ``path_str``
    argument.  In particular, this function intentionally does **not** call
    ``Path.resolve()`` (which follows symlinks) or ``os.path.abspath()`` to
    avoid CodeQL ``py/path-injection`` (CWE-22/CWE-23).

    Tilde (``~``) expansion is intentionally **not** performed here.
    Callers that need ``~`` expansion for **trusted** inputs (e.g. an
    admin-supplied environment variable) should call
    ``Path(...).expanduser()`` before passing the value to this function.
    User-supplied paths should be handled by ``_resolve_path_under_base``,
    which enforces containment before any filesystem operation.

    Args:
        path_str: Path string or Path object to normalise.

    Returns:
        Absolute, normalised Path object.

    Raises:
        ValueError: If the path contains null bytes, is of an invalid type,
            or if an OS-level error occurs whilst resolving the current
            working directory.

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
        # Produce an absolute, normalised path without calling os.path.abspath()
        # (PTH100) or Path.resolve() (follows symlinks — filesystem I/O on
        # user-controlled data would re-introduce CodeQL py/path-injection).
        #
        # Path.cwd() is trusted system state, NOT derived from user input.
        # The / operator is pure string concatenation (same as os.path.join).
        # os.path.normpath collapses ".", "..", and repeated separators.
        if path_obj.is_absolute():
            normalized = Path(os.path.normpath(str(path_obj)))
        else:
            normalized = Path(os.path.normpath(str(Path.cwd() / path_obj)))
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
    if relative.is_absolute():  # pragma: no cover
        raise ValueError(f"Path traversal attempt: {relative}")

    return relative


def _resolve_path_under_base(path_obj: Path | str, base_path: Path | str) -> Path:
    """
    Resolve ``path_obj`` and enforce that it remains under ``base_path``.

    This function performs a two-stage containment check:

    1. **normpath + commonpath (BARRIER 1)** — pure string normalisation (no
       filesystem I/O on user-controlled data) that collapses all ``..`` and
       repeated-separator sequences.  ``os.path.commonpath`` is the CodeQL-
       recognised barrier for ``py/path-injection``.

    2. **realpath + commonpath (BARRIER 2, inline)** — after BARRIER 1
       sanitises the candidate, ``os.path.realpath`` is called in the *same
       inline scope* to follow any symlinks and produce the true filesystem
       path.  A second ``os.path.commonpath`` check then confirms that the
       resolved target also lies within the workspace.  Calling ``realpath``
       *inline* (not in a helper) after the first barrier is CodeQL-safe
       because the guard and the filesystem call share the same function scope.

    Tilde (``~``) expansion is intentionally **not** performed on user-supplied
    paths.  The UI layer (or any trusted caller) must call
    ``Path(...).expanduser()`` on admin/trusted values *before* passing them to
    this function.  ``expanduser()`` on user-controlled data is a CodeQL
    ``py/path-injection`` filesystem sink (reads ``/etc/passwd`` for
    ``~user`` form).
    """
    safe_base = _normalize_trusted_base(base_path)
    # Use normpath-based absolute string — no filesystem I/O on base_path which
    # is trusted.  _normalize_trusted_base already calls _normalize_path.
    base_str = str(safe_base)

    # Normalise the candidate path using pure string operations.
    # Do NOT call expanduser() — that reads /etc/passwd for ~user form.
    if isinstance(path_obj, Path):
        # Path objects: normalise in-place (no string validation needed here;
        # validation was performed before the Path object was created).
        raw_path = path_obj
    else:
        # String inputs: validate characters first (user-controlled data).
        raw_value = str(path_obj)
        if "\x00" in raw_value:
            raise ValueError(f"Path contains null bytes: {raw_value!r}")
        if not re.fullmatch(r"[A-Za-z0-9_./\\~:-]+", raw_value):
            raise ValueError(f"Path contains invalid characters: {raw_value!r}")
        raw_path = Path(raw_value)

    # Produce an absolute, normpath-canonicalised string — no filesystem I/O.
    if raw_path.is_absolute():
        candidate_str = os.path.normpath(str(raw_path))
    else:
        relative = _validate_relative_parts(raw_path.parts)
        candidate_str = os.path.normpath(str(Path(base_str) / relative))

    # BARRIER 1: os.path.commonpath is a pure string operation recognised by
    # CodeQL as a containment barrier for py/path-injection.  After this check
    # passes, candidate_str is safe for downstream use in the same scope.
    try:
        common = os.path.commonpath([candidate_str, base_str])
    except ValueError as e:
        msg = f"Path traversal attempt: escapes {safe_base}"
        raise ValueError(msg) from e

    if common != base_str:
        msg = f"Path traversal attempt: escapes {safe_base}"
        raise ValueError(msg)

    # BARRIER 2 (inline, same scope): Follow symlinks via realpath() — now
    # safe to call because candidate_str was sanitised by BARRIER 1 above —
    # and re-validate containment with a second commonpath check.  Doing this
    # inline (not in a helper) keeps the guard and the filesystem I/O in the
    # same function scope, which is required for CodeQL's barrier model.
    base_resolved = os.path.realpath(base_str)
    resolved_str = os.path.realpath(candidate_str)
    try:
        common2 = os.path.commonpath([resolved_str, base_resolved])
    except ValueError as e:
        msg = f"Path traversal attempt: escapes {safe_base}"
        raise ValueError(msg) from e

    if common2 != base_resolved:
        msg = f"Path traversal attempt: escapes {safe_base}"
        raise ValueError(msg)

    return _ensure_within_base_path(Path(resolved_str), Path(base_resolved))


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
    # Full security validation: raises on symlink escape, char violations, etc.
    validated = _resolve_path_under_base(path_obj, base_path)
    # Inline BARRIER so CodeQL sees normpath+commonpath in the same scope as
    # the I/O call (.exists).  Mirrors the containment checks inside
    # _resolve_path_under_base and applies to the sanitised value.
    base_str = str(_normalize_trusted_base(base_path))
    candidate_str = os.path.normpath(str(validated))
    try:
        common = os.path.commonpath([candidate_str, base_str])
    except ValueError as e:
        msg = f"Path traversal attempt: escapes {base_path}"
        raise ValueError(msg) from e
    if common != base_str:
        msg = f"Path traversal attempt: escapes {base_path}"
        raise ValueError(msg)
    return validated.exists()


def safe_is_dir(path_obj: Path, base_path: Path) -> bool:
    """Check directory-ness after enforcing base containment."""
    validated = _resolve_path_under_base(path_obj, base_path)
    base_str = str(_normalize_trusted_base(base_path))
    candidate_str = os.path.normpath(str(validated))
    try:
        common = os.path.commonpath([candidate_str, base_str])
    except ValueError as e:
        msg = f"Path traversal attempt: escapes {base_path}"
        raise ValueError(msg) from e
    if common != base_str:
        msg = f"Path traversal attempt: escapes {base_path}"
        raise ValueError(msg)
    return validated.is_dir()


def safe_is_file(path_obj: Path, base_path: Path) -> bool:
    """Check file-ness after enforcing base containment."""
    # First, enforce containment using the path utilities' resolver. This
    # ensures the candidate cannot escape the trusted base directory.
    validated = _resolve_path_under_base(path_obj, base_path)

    # Normalise the trusted base using the dedicated helper.
    safe_base = _normalize_trusted_base(base_path)
    base_str = os.path.normpath(str(safe_base))

    # Build a candidate path string that is explicitly rooted under the
    # trusted base and then normalised. This keeps the containment logic
    # in pure string space and matches the CodeQL-recognised pattern for
    # path sanitisation.
    candidate_str = os.path.normpath(str(Path(base_str) / path_obj))
    try:
        common = os.path.commonpath([candidate_str, base_str])
    except ValueError as e:
        msg = f"Path traversal attempt: escapes {base_path}"
        raise ValueError(msg) from e
    if common != base_str:
        msg = f"Path traversal attempt: escapes {base_path}"
        raise ValueError(msg)

    # Only use the fully validated, normalised candidate for filesystem I/O.
    return validated.is_file()


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

    # Resolve and validate the candidate path against the trusted base.
    safe_path = _resolve_path_under_base(path_obj, base_path)
    for result in safe_dir.glob(pattern):
    candidate_str = os.path.normpath(str(safe_path))
        results.append(validated_result)

    return results


def safe_mkdir(
    path_obj: Path, base_path: Path, parents: bool = False, exist_ok: bool = False
) -> None:
    safe_path.mkdir(parents=parents, exist_ok=exist_ok)
    # Enforce containment at the path utilities level.
    _resolve_path_under_base(path_obj, base_path)

    safe_base = _normalize_trusted_base(base_path)
    base_str = os.path.normpath(str(safe_base))

    # Root the candidate under the trusted base and normalise before
    # applying the commonpath containment guard.
    candidate_str = os.path.normpath(str(Path(base_str) / path_obj))
    try:
        common = os.path.commonpath([candidate_str, base_str])
    except ValueError as e:
        msg = f"Path traversal attempt: escapes {base_path}"
        raise ValueError(msg) from e
    if common != base_str:
        msg = f"Path traversal attempt: escapes {base_path}"
        raise ValueError(msg)

    # Resolve and validate the candidate path against the trusted base.
    safe_path = _resolve_path_under_base(path_obj, base_path)
    Path(candidate_str).mkdir(parents=parents, exist_ok=exist_ok)

def safe_read_text(path_obj: Path, base_path: Path, encoding: str = "utf-8") -> str:
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
    safe_path = _resolve_path_under_base(path_obj, base_path)
        common = os.path.commonpath([candidate_str, base_str])
    # Read from the fully validated, normalised path only.
    return Path(candidate_str).read_text(encoding=encoding)
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
    _resolve_path_under_base(path_obj, base_path)
    base_str = str(_normalize_trusted_base(base_path))
    candidate_str = os.path.normpath(str(path_obj))
    try:
        common = os.path.commonpath([candidate_str, base_str])
    except ValueError as e:
        msg = f"Path traversal attempt: escapes {base_path}"
        raise ValueError(msg) from e
    if common != base_str:
        msg = f"Path traversal attempt: escapes {base_path}"
        raise ValueError(msg)
    Path(candidate_str).write_text(text, encoding=encoding)


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
    _resolve_path_under_base(path_obj, safe_base)
    base_str = str(safe_base)
    candidate_str = os.path.normpath(str(path_obj))
    try:
        common = os.path.commonpath([candidate_str, base_str])
    except ValueError as e:
        msg = f"Path traversal attempt: escapes {safe_base}"
        raise ValueError(msg) from e
    if common != base_str:
        msg = f"Path traversal attempt: escapes {safe_base}"
        raise ValueError(msg)

    results: list[Path] = []
    for item in Path(candidate_str).iterdir():
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
