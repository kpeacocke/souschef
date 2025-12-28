"""SousChef MCP Server - Chef to Ansible conversion assistant."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Create a new FastMCP server
mcp = FastMCP("souschef")


@mcp.tool()
def list_directory(path: str) -> list[str] | str:
    """List the contents of a directory.

    Args:
        path: The path to the directory to list.

    Returns:
        A list of filenames in the directory, or an error message.

    """
    try:
        dir_path = Path(path)
        return [item.name for item in dir_path.iterdir()]
    except FileNotFoundError:
        return f"Error: Directory not found at {path}"
    except NotADirectoryError:
        return f"Error: {path} is not a directory"
    except PermissionError:
        return f"Error: Permission denied for {path}"
    except Exception as e:
        return f"An error occurred: {e}"


@mcp.tool()
def read_file(path: str) -> str:
    """Read the contents of a file.

    Args:
        path: The path to the file to read.

    Returns:
        The contents of the file, or an error message.

    """
    try:
        file_path = Path(path)
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: File not found at {path}"
    except IsADirectoryError:
        return f"Error: {path} is a directory, not a file"
    except PermissionError:
        return f"Error: Permission denied for {path}"
    except UnicodeDecodeError:
        return f"Error: Unable to decode {path} as UTF-8 text"
    except Exception as e:
        return f"An error occurred: {e}"
