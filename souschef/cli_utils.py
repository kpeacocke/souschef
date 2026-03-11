"""
Shared CLI utility functions for SousChef command-line tools.

Provides path resolution and file writing utilities shared between
the main CLI and the V2 command modules.
"""

from pathlib import Path

import click

from souschef.core.path_utils import (
    _ensure_within_base_path,
    _get_workspace_root,
    _normalize_path,
)


def _resolve_output_path(output: str | None, default_path: Path) -> Path:
    """
    Normalise and validate output paths for generated files.

    Args:
        output: User-specified output path or None.
        default_path: Default path if output not specified.

    Returns:
        Validated and resolved Path.

    Raises:
        click.Abort: If path validation fails.

    """
    try:
        workspace_root = _get_workspace_root()
        if output:
            resolved_path = _ensure_within_base_path(
                _normalize_path(output), workspace_root
            )
        else:
            resolved_path = _ensure_within_base_path(
                default_path.resolve(), workspace_root
            )
    except ValueError as exc:  # noqa: TRY003
        click.echo(f"Invalid output path: {exc}", err=True)
        raise click.Abort() from exc

    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    return resolved_path


def _safe_write_file(content: str, output: str | None, default_path: Path) -> Path:
    """
    Safely write content to a validated file path.

    Args:
        content: Content to write to file.
        output: Optional user-specified output path.
        default_path: Default path if output not specified.

    Returns:
        The path where content was written.

    Raises:
        click.Abort: If path validation or write fails.

    """
    validated_path = _resolve_output_path(output, default_path)
    try:
        # Separate validation from write to satisfy SonarQube path construction rules
        with validated_path.open("w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        click.echo(f"Error writing file: {e}", err=True)
        raise click.Abort() from e
    return validated_path
