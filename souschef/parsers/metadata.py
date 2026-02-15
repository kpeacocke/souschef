"""Chef cookbook metadata parser."""

import re

from souschef.core import path_utils
from souschef.core.constants import (
    ERROR_FILE_NOT_FOUND,
    ERROR_IS_DIRECTORY,
    ERROR_PERMISSION_DENIED,
    METADATA_FILENAME,
)

# Make safe functions available as module attributes for testing
safe_exists = path_utils.safe_exists
safe_is_dir = path_utils.safe_is_dir
safe_is_file = path_utils.safe_is_file
safe_read_text = path_utils.safe_read_text


def read_cookbook_metadata(path: str) -> str:
    """
    Parse Chef cookbook metadata.rb file.

    Args:
        path: Path to the metadata.rb file.

    Returns:
        Formatted string with extracted metadata.

    """
    try:
        file_path = path_utils._normalize_path(path)
        workspace_root = path_utils._get_workspace_root()
        safe_path = path_utils._ensure_within_base_path(file_path, workspace_root)
        content = safe_read_text(safe_path, workspace_root, encoding="utf-8")

        metadata = _extract_metadata(content)

        if not metadata:
            return f"Warning: No metadata found in {path}"

        return _format_metadata(metadata)

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


def parse_cookbook_metadata(path: str) -> dict[str, str | list[str]]:
    """
    Parse Chef cookbook metadata.rb file and return as dictionary.

    Args:
        path: Path to the metadata.rb file.

    Returns:
        Dictionary containing extracted metadata fields.

    """
    try:
        file_path = path_utils._normalize_path(path)
        workspace_root = path_utils._get_workspace_root()
        safe_path = path_utils._ensure_within_base_path(file_path, workspace_root)
        content = safe_read_text(safe_path, workspace_root, encoding="utf-8")

        metadata = _extract_metadata(content)
        return metadata

    except ValueError as e:
        return {"error": str(e)}
    except FileNotFoundError:
        return {"error": ERROR_FILE_NOT_FOUND.format(path=path)}
    except IsADirectoryError:
        return {"error": ERROR_IS_DIRECTORY.format(path=path)}
    except PermissionError:
        return {"error": ERROR_PERMISSION_DENIED.format(path=path)}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}


def _scan_cookbook_directory(
    cookbook_path, dir_name: str
) -> tuple[str, list[str]] | None:
    """
    Scan a single cookbook directory for files.

    Args:
        cookbook_path: Path to the cookbook root.
        dir_name: Name of the subdirectory to scan.

    Returns:
        Tuple of (dir_name, files) if directory exists and has files, None otherwise.

    """
    dir_path = path_utils._safe_join(cookbook_path, dir_name)
    workspace_root = path_utils._get_workspace_root()
    if not safe_exists(dir_path, workspace_root) or not safe_is_dir(
        dir_path, workspace_root
    ):
        return None

    # nosonar
    files = [f.name for f in dir_path.iterdir() if safe_is_file(f, workspace_root)]
    return (dir_name, files) if files else None


def _collect_cookbook_structure(cookbook_path) -> dict[str, list[str]]:
    """
    Collect all standard cookbook directories and their files.

    Args:
        cookbook_path: Path to the cookbook root.

    Returns:
        Dictionary mapping directory names to file lists.

    """
    structure = {}
    common_dirs = [
        "recipes",
        "attributes",
        "templates",
        "files",
        "resources",
        "providers",
        "libraries",
        "definitions",
    ]

    for dir_name in common_dirs:
        result = _scan_cookbook_directory(cookbook_path, dir_name)
        if result:
            structure[result[0]] = result[1]

    # Check for metadata.rb
    metadata_path = path_utils._safe_join(cookbook_path, METADATA_FILENAME)
    workspace_root = path_utils._get_workspace_root()
    if safe_exists(metadata_path, workspace_root):
        structure["metadata"] = [METADATA_FILENAME]

    return structure


def list_cookbook_structure(path: str) -> str:
    """
    List the structure of a Chef cookbook directory.

    Args:
        path: Path to the cookbook root directory.

    Returns:
        Formatted string showing the cookbook structure.

    """
    try:
        cookbook_path = path_utils._normalize_path(path)
        workspace_root = path_utils._get_workspace_root()
        safe_path = path_utils._ensure_within_base_path(cookbook_path, workspace_root)

        if not safe_is_dir(safe_path, workspace_root):
            return f"Error: {path} is not a directory"

        structure = _collect_cookbook_structure(safe_path)

        if not structure:
            return f"Warning: No standard cookbook structure found in {path}"

        return _format_cookbook_structure(structure)

    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=path)
    except Exception as e:
        return f"An error occurred: {e}"


def _extract_metadata(content: str) -> dict[str, str | list[str]]:
    """
    Extract metadata fields from cookbook content.

    Args:
        content: Raw content of metadata.rb file.

    Returns:
        Dictionary of extracted metadata fields.

    """
    metadata: dict[str, str | list[str]] = {}
    patterns = {
        "name": r"name\s+['\"]([^'\"]+)['\"]",
        "maintainer": r"maintainer\s+['\"]([^'\"]+)['\"]",
        "version": r"version\s+['\"]([^'\"]+)['\"]",
        "description": r"description\s+['\"]([^'\"]+)['\"]",
        "license": r"license\s+['\"]([^'\"]+)['\"]",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            metadata[key] = match.group(1)

    depends = re.findall(r"depends\s+['\"]([^'\"]+)['\"]", content)
    if depends:
        metadata["depends"] = depends

    supports = re.findall(r"supports\s+['\"]([^'\"]+)['\"]", content)
    if supports:
        metadata["supports"] = supports

    return metadata


def _format_metadata(metadata: dict[str, str | list[str]]) -> str:
    """
    Format metadata dictionary as a readable string.

    Args:
        metadata: Dictionary of metadata fields.

    Returns:
        Formatted string representation.

    """
    result = []
    for key, value in metadata.items():
        if isinstance(value, list):
            result.append(f"{key}: {', '.join(value)}")
        else:
            result.append(f"{key}: {value}")

    return "\n".join(result)


def _format_cookbook_structure(structure: dict[str, list[str]]) -> str:
    """
    Format cookbook structure as a readable string.

    Args:
        structure: Dictionary mapping directory names to file lists.

    Returns:
        Formatted string representation.

    """
    result = []
    for dir_name, files in structure.items():
        result.append(f"{dir_name}/")
        for file_name in sorted(files):
            result.append(f"  {file_name}")
        result.append("")

    return "\n".join(result).rstrip()
