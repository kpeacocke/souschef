"""Utility functions for path handling and file operations in SousChef UI."""

import contextlib
import os
import re
import tempfile
from pathlib import Path


def _sanitize_filename(filename: str) -> str:
    """
    Sanitise filename to prevent path injection attacks.

    Args:
        filename: The filename to sanitise.

    Returns:
        Sanitised filename safe for file operations.

    """
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

    config_file = config_dir / "ai_config.json"
    # Ensure config file has secure permissions if it exists
    if config_file.exists():  # NOSONAR
        with contextlib.suppress(OSError):
            config_file.chmod(0o600)
    return config_file


def _is_within_base(base: Path, candidate: Path) -> bool:
    """Check whether candidate is contained within base after resolution."""
    base_real = Path(os.path.realpath(str(base)))
    candidate_real = Path(os.path.realpath(str(candidate)))
    try:
        candidate_real.relative_to(base_real)
        return True
    except ValueError:
        return False
