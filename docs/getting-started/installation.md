# Installation

This guide will help you install SousChef and configure it with your preferred MCP client.

## Prerequisites

Before installing SousChef, ensure you have:

- **Python 3.10+** installed on your system
- **pip** or **Poetry** for package management
- An **MCP-compatible client** such as:
    - Claude Desktop
    - VS Code with MCP extension
    - Custom MCP client

## Installation Methods

### Method 1: PyPI Installation (Recommended)

The simplest way to install SousChef:

```bash
pip install mcp-souschef
```

This installs:
- The `mcp-souschef` package
- `souschef` MCP server command
- `souschef-cli` command-line interface

### Method 2: Development Installation

For contributors or those who want the latest development version:

```bash
# Clone the repository
git clone https://github.com/kpeacocke/souschef.git
cd souschef

# Install with Poetry
poetry install

# Verify installation
poetry run souschef --version
poetry run souschef-cli --help
```

## MCP Client Configuration

SousChef provides pre-configured setup files for common MCP clients in the `config/` directory.

### Claude Desktop

=== "macOS"

    ```bash
    # Copy the configuration file
    cp config/claude-desktop.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

    # Restart Claude Desktop
    ```

=== "Linux"

    ```bash
    # Copy the configuration file
    cp config/claude-desktop.json ~/.config/Claude/claude_desktop_config.json

    # Restart Claude Desktop
    ```

=== "Windows"

    ```powershell
    # Copy the configuration file
    copy config\claude-desktop.json %APPDATA%\Claude\claude_desktop_config.json

    # Restart Claude Desktop
    ```

### VS Code with GitHub Copilot

1. Copy the configuration:
   ```bash
   cp config/vscode-copilot.json .vscode/mcp_config.json
   ```

2. Install the MCP extension from the VS Code marketplace

3. Reload VS Code

### Custom MCP Configuration

For other MCP clients or custom setups, use this template:

```json
{
  "mcpServers": {
    "souschef": {
      "command": "souschef",
      "args": [],
      "env": {}
    }
  }
}
```

!!! tip "Development Configuration"
    For development or testing, use `config/claude-desktop-dev.json` which points to the local repository instead of the installed package.

## Verifying Installation

After installation, verify that SousChef is working correctly:

### 1. Check MCP Server

```bash
# Test the MCP server
souschef --version
```

### 2. Check CLI

```bash
# Test the command-line interface
souschef-cli --help
```

### 3. Test with MCP Client

Restart your MCP client and ask:
```
What Chef migration tools are available?
```

The AI should respond with a list of SousChef's 44 MCP tools.

## Troubleshooting

### Command Not Found

If you get "command not found" errors:

```bash
# Ensure pip's bin directory is in your PATH
export PATH="$PATH:$(python3 -m site --user-base)/bin"

# Or use Poetry's virtual environment
poetry shell
```

### MCP Client Not Detecting SousChef

1. Check that the configuration file is in the correct location
2. Verify the `souschef` command is accessible from your terminal
3. Restart your MCP client completely
4. Check the client's logs for error messages

### Python Version Issues

SousChef requires Python 3.10+. Check your version:

```bash
python3 --version
```

If you need to install or upgrade Python, visit [python.org/downloads](https://www.python.org/downloads/).

## Platform-Specific Notes

### macOS

- Python 3.10+ can be installed via Homebrew: `brew install python@3.10`
- Claude Desktop config location: `~/Library/Application Support/Claude/`

### Linux

- Python 3.10+ may need to be compiled from source or installed via third-party repositories
- Config locations vary by distribution and desktop environment

### Windows

- Use PowerShell or Windows Terminal for installation
- Path separators use backslashes (`\`) instead of forward slashes (`/`)
- Config location: `%APPDATA%\Claude\`

## Next Steps

Now that SousChef is installed, you're ready to:

- [Configure SousChef](configuration.md) for your environment
- [Follow the Quick Start guide](quick-start.md) to begin migrating
- [Explore the MCP tools](../user-guide/mcp-tools.md) available

For detailed configuration options and model provider setup, see the [Configuration Reference](configuration.md).
