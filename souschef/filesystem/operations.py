"""Filesystem operations for Chef cookbook exploration."""

from mcp.server.fastmcp import FastMCP

from souschef.core.constants import (
    ERROR_FILE_NOT_FOUND,
    ERROR_IS_DIRECTORY,
    ERROR_PERMISSION_DENIED,
)
from souschef.core.path_utils import _normalize_path

# Get MCP instance to register tools
mcp = FastMCP("souschef")


@mcp.tool()
def list_directory(path: str) -> list[str] | str:
    """
    List the contents of a directory.

    Args:
        path: The path to the directory to list.

    Returns:
        A list of filenames in the directory, or an error message.

    """
    try:
        dir_path = _normalize_path(path)
        return [item.name for item in dir_path.iterdir()]
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


@mcp.tool()
def read_file(path: str) -> str:
    """
    Read the contents of a file.

    Args:
        path: The path to the file to read.

    Returns:
        The contents of the file, or an error message.

    """
    try:
        file_path = _normalize_path(path)
        return file_path.read_text(encoding="utf-8")
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
