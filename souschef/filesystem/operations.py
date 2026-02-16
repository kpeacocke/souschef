"""Filesystem operations for Chef cookbook exploration."""

import tarfile
from pathlib import Path

from souschef.core.constants import (
    ERROR_FILE_NOT_FOUND,
    ERROR_IS_DIRECTORY,
    ERROR_PERMISSION_DENIED,
)
from souschef.core.path_utils import (
    _check_symlink_safety,
    _ensure_within_base_path,
    _get_workspace_root,
    _normalize_path,
)


def list_directory(path: str) -> list[str] | str:
    """
    List the contents of a directory.

    Args:
        path: The path to the directory to list.

    Returns:
        A list of filenames in the directory, or an error message.

    """
    try:
        # Check for symlinks before normalisation to detect attacks
        _check_symlink_safety(_normalize_path(path), Path(path))

        dir_path = _normalize_path(path)
        workspace_root = _get_workspace_root()
        safe_dir = _ensure_within_base_path(dir_path, workspace_root)

        return [item.name for item in safe_dir.iterdir()]
    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return f"Error: Directory not found at {path}"
    except NotADirectoryError:
        return f"Error: {path} is not a directory"
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=path)
    except Exception as e:
        return f"An error occurred: {e}"


def read_file(path: str) -> str:
    """
    Read the contents of a file.

    Args:
        path: The path to the file to read.

    Returns:
        The contents of the file, or an error message.

    """
    try:
        # Check for symlinks before normalisation to detect attacks
        _check_symlink_safety(_normalize_path(path), Path(path))

        file_path = _normalize_path(path)
        workspace_root = _get_workspace_root()
        safe_file = _ensure_within_base_path(file_path, workspace_root)

        return safe_file.read_text(encoding="utf-8")
    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return ERROR_FILE_NOT_FOUND.format(path=path)
    except IsADirectoryError:
        return ERROR_IS_DIRECTORY.format(path=path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=path)
    except Exception as e:
        return f"An error occurred: {e}"


def create_tar_gz_archive(source_dir: str, output_path: str) -> str:
    """
    Create a tar.gz archive from a directory.

    Args:
        source_dir: Directory to archive.
        output_path: Destination path for the tar.gz archive.

    Returns:
        Path to the created archive.

    """
    # Check for symlinks before normalisation to detect attacks
    _check_symlink_safety(_normalize_path(source_dir), Path(source_dir))

    workspace_root = _get_workspace_root()
    source_path = _ensure_within_base_path(_normalize_path(source_dir), workspace_root)
    if not source_path.is_dir():
        raise ValueError(f"Source directory does not exist: {source_dir}")

    output_file = _ensure_within_base_path(_normalize_path(output_path), workspace_root)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(output_file, "w:gz") as tar:
        for file_path in source_path.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(source_path)
                tar.add(file_path, arcname=arcname)

    return str(output_file)
