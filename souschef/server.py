import os
from zod import z

from mcp import McpServer
from mcp.transport.stdio import StdioTransport

# Create a new server
server = McpServer(
    name="souschef",
    version="0.0.1",
    description="A server that helps convert Chef cookbooks to Ansible playbooks.",
)

@server.tool()
def list_directory(path: str = z.string(description="The path to the directory to list.")):
    """Lists the contents of a directory."""
    try:
        return os.listdir(path)
    except FileNotFoundError:
        return f"Error: Directory not found at {path}"
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    # Start the server
    McpServer.run_server(server, StdioTransport())
