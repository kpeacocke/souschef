from mcp import McpServer
from mcp.transport.stdio import StdioTransport

# Create a new server
server = McpServer(
    name="souschef",
    version="0.0.1",
    description="A server that helps convert Chef cookbooks to Ansible playbooks.",
)

if __name__ == "__main__":
    # Start the server
    McpServer.run_server(server, StdioTransport())
