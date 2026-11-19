"""Filesystem operations for Chef cookbook exploration."""

import os
import shutil
import tarfile
from pathlib import Path, PurePosixPath

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
    safe_glob,
    safe_is_dir,
    safe_mkdir,
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
    if not safe_is_dir(source_path, workspace_root):
        raise ValueError(f"Source directory does not exist: {source_dir}")

    output_file = _ensure_within_base_path(_normalize_path(output_path), workspace_root)
    safe_mkdir(output_file.parent, workspace_root, parents=True, exist_ok=True)

    with tarfile.open(  # NOSONAR - S5042: creating archive, not expanding/extracting
        output_file, "w:gz"
    ) as tar:
        for file_path in safe_glob(source_path, "**/*", source_path):
            if file_path.is_file():
                arcname = file_path.relative_to(source_path)
                tar.add(file_path, arcname=arcname)

    return str(output_file)


def _write_archive_member(
    archive: tarfile.TarFile, member: tarfile.TarInfo, member_path: Path
) -> None:
    """Copy a validated regular member with safe initial and final permissions."""
    source_file = archive.extractfile(member)
    if source_file is None:
        raise ValueError(f"Unable to read archive member: {member.name}")

    file_descriptor = os.open(
        member_path,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    safe_mode = member.mode & 0o777 & ~0o022
    with source_file, os.fdopen(file_descriptor, "wb") as output_file:
        if hasattr(os, "fchmod"):
            os.fchmod(output_file.fileno(), 0o600)
        else:
            member_path.chmod(0o600)
        shutil.copyfileobj(source_file, output_file)
        if hasattr(os, "fchmod"):
            os.fchmod(output_file.fileno(), safe_mode)
        else:
            member_path.chmod(safe_mode)


def _validate_archive_member(member: tarfile.TarInfo, target_dir: Path) -> Path:
    """Validate an archive member and return its contained destination path."""
    member_name = PurePosixPath(member.name)
    if (
        member_name.is_absolute()
        or ".." in member_name.parts
        or "\\" in member.name
        or (member_name.parts and member_name.parts[0].endswith(":"))
    ):
        raise ValueError(f"Unsafe archive member path: {member.name}")
    if not (member.isdir() or member.isfile()):
        raise ValueError(f"Unsupported archive member type: {member.name}")

    member_path = _ensure_within_base_path(
        target_dir.joinpath(*member_name.parts), target_dir
    )
    if member_path.is_symlink():
        raise ValueError(f"Archive member would overwrite a symlink: {member.name}")
    return member_path


def extract_tar_gz_archive(archive_path: str, output_dir: str) -> str:
    """
    Extract a tar.gz archive into a directory.

    Args:
        archive_path: Path to the tar.gz archive.
        output_dir: Directory to extract contents into.

    Returns:
        Path to the extracted directory.

    """
    # Check for symlinks before normalisation to detect attacks
    _check_symlink_safety(_normalize_path(archive_path), Path(archive_path))

    workspace_root = _get_workspace_root()
    archive_file = _ensure_within_base_path(
        _normalize_path(archive_path), workspace_root
    )
    target_dir = _ensure_within_base_path(_normalize_path(output_dir), workspace_root)

    if not archive_file.is_file():
        raise ValueError(f"Archive does not exist: {archive_path}")

    safe_mkdir(target_dir, workspace_root, parents=True, exist_ok=True)

    with tarfile.open(archive_file, "r:gz") as tar:  # NOSONAR
        safe_members = [
            (member, _validate_archive_member(member, target_dir))
            for member in tar.getmembers()
        ]

        for member, member_path in safe_members:
            if member.isdir():
                safe_mkdir(member_path, workspace_root, parents=True, exist_ok=True)
                continue

            safe_mkdir(member_path.parent, workspace_root, parents=True, exist_ok=True)
            member_path = _ensure_within_base_path(member_path, target_dir)
            if member_path.is_symlink():
                raise ValueError(
                    f"Archive member would overwrite a symlink: {member.name}"
                )
            _write_archive_member(tar, member, member_path)

    return str(target_dir)
