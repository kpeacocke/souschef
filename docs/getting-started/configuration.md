# Configuration

Learn how to configure SousChef for your environment and customize its behavior.

## Configuration Files

SousChef provides pre-configured setup files for different environments and MCP clients in the `config/` directory:

| File | Purpose |
|------|---------|
| `claude-desktop.json` | Production setup for Claude Desktop |
| `claude-desktop-dev.json` | Development setup pointing to local repository |
| `vscode-copilot.json` | VS Code with GitHub Copilot MCP extension |
| `vscode-copilot-dev.json` | VS Code development setup |

## MCP Server Configuration

The basic MCP server configuration structure:

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

### Configuration Options

#### Command

The `command` field specifies how to launch the MCP server:

=== "PyPI Installation"

    ```json
    {
      "command": "souschef"
    }
    ```

=== "Poetry Development"

    ```json
    {
      "command": "poetry",
      "args": ["run", "souschef"]
    }
    ```

=== "Python Module"

    ```json
    {
      "command": "python3",
      "args": ["-m", "souschef.server"]
    }
    ```

#### Environment Variables

Configure behavior through environment variables:

```json
{
  "env": {
    "LOG_LEVEL": "INFO",
    "SOUSCHEF_CONFIG_PATH": "/path/to/config"
  }
}
```

Available environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `SOUSCHEF_CONFIG_PATH` | - | Custom configuration file path |
| `CHEF_REPO_PATH` | - | Default Chef repository path |

## Model Provider Configuration

SousChef works with any MCP-compatible model provider. Configure your MCP client to use your preferred model.

### Claude (Anthropic)

Claude Desktop configuration is built-in. Simply add the souschef server configuration to `claude_desktop_config.json`.

### OpenAI (GPT-4, GPT-3.5)

Use an MCP client that supports OpenAI models:

```json
{
  "modelProvider": {
    "type": "openai",
    "apiKey": "${OPENAI_API_KEY}",
    "model": "gpt-4"
  },
  "mcpServers": {
    "souschef": {
      "command": "souschef"
    }
  }
}
```

### Local Models (Ollama)

For local model inference:

```json
{
  "modelProvider": {
    "type": "ollama",
    "endpoint": "http://localhost:11434",
    "model": "llama2"
  },
  "mcpServers": {
    "souschef": {
      "command": "souschef"
    }
  }
}
```

### Red Hat AI

Configure for Red Hat AI models:

```json
{
  "modelProvider": {
    "type": "redhat-ai",
    "endpoint": "https://ai.redhat.com/api",
    "apiKey": "${REDHAT_AI_API_KEY}"
  },
  "mcpServers": {
    "souschef": {
      "command": "souschef"
    }
  }
}
```

## Platform-Specific Configuration

### macOS

Configuration file location:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

Example setup:
```bash
# Install SousChef
pip3 install mcp-souschef

# Copy configuration
cp config/claude-desktop.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Restart Claude Desktop
```

### Linux

Configuration file location (varies by desktop environment):
```
~/.config/Claude/claude_desktop_config.json
```

Example setup:
```bash
# Install SousChef
pip3 install --user mcp-souschef

# Ensure pip bin is in PATH
export PATH="$PATH:$(python3 -m site --user-base)/bin"

# Copy configuration
mkdir -p ~/.config/Claude
cp config/claude-desktop.json ~/.config/Claude/claude_desktop_config.json
```

### Windows

Configuration file location:
```
%APPDATA%\Claude\claude_desktop_config.json
```

Example setup (PowerShell):
```powershell
# Install SousChef
pip install mcp-souschef

# Copy configuration
New-Item -Path "$env:APPDATA\Claude" -ItemType Directory -Force
Copy-Item config\claude-desktop.json "$env:APPDATA\Claude\claude_desktop_config.json"
```

## Development Configuration

For development and testing:

### Local Repository Setup

Point to your local development repository:

```json
{
  "mcpServers": {
    "souschef": {
      "command": "poetry",
      "args": ["run", "souschef"],
      "cwd": "/path/to/souschef/repository",
      "env": {
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

### Testing Configuration

For automated testing:

```json
{
  "mcpServers": {
    "souschef": {
      "command": "python3",
      "args": ["-m", "souschef.server"],
      "env": {
        "LOG_LEVEL": "DEBUG",
        "TESTING": "true"
      }
    }
  }
}
```

## Advanced Configuration

### Custom Tool Filtering

Limit which tools are available:

```json
{
  "mcpServers": {
    "souschef": {
      "command": "souschef",
      "env": {
        "SOUSCHEF_TOOLS_INCLUDE": "parse_recipe,generate_playbook_from_recipe",
        "SOUSCHEF_TOOLS_EXCLUDE": "assess_chef_migration_complexity"
      }
    }
  }
}
```

### Performance Tuning

Configure for large-scale migrations:

```json
{
  "mcpServers": {
    "souschef": {
      "command": "souschef",
      "env": {
        "SOUSCHEF_MAX_FILE_SIZE": "10485760",
        "SOUSCHEF_CACHE_ENABLED": "true",
        "SOUSCHEF_PARALLEL_PROCESSING": "true"
      }
    }
  }
}
```

## Troubleshooting Configuration

### Verify Configuration

Check that your configuration is valid:

```bash
# Test MCP server launch
souschef --version

# Check if tools are accessible
souschef list-tools
```

### Common Issues

#### Command Not Found

```bash
# Check if souschef is in PATH
which souschef

# If not, add pip's bin directory to PATH
export PATH="$PATH:$(python3 -m site --user-base)/bin"
```

#### Permission Errors

```bash
# Ensure executable permissions
chmod +x $(which souschef)

# Or install with --user flag
pip3 install --user mcp-souschef
```

#### Configuration Not Loading

1. Verify configuration file location is correct for your platform
2. Check JSON syntax is valid
3. Ensure the MCP client has read permissions
4. Restart the MCP client completely

### Debug Mode

Enable debug logging to troubleshoot issues:

```json
{
  "mcpServers": {
    "souschef": {
      "command": "souschef",
      "env": {
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

Check logs:

=== "macOS"
    ```bash
    tail -f ~/Library/Logs/Claude/mcp*.log
    ```

=== "Linux"
    ```bash
    tail -f ~/.local/share/Claude/logs/mcp*.log
    ```

=== "Windows"
    ```powershell
    Get-Content "$env:APPDATA\Claude\logs\mcp*.log" -Wait
    ```

## Configuration Examples

### Complete Claude Desktop Config

```json
{
  "mcpServers": {
    "souschef": {
      "command": "souschef",
      "args": [],
      "env": {
        "LOG_LEVEL": "INFO",
        "CHEF_REPO_PATH": "/opt/chef/cookbooks"
      }
    }
  }
}
```

### VS Code with GitHub Copilot

```json
{
  "mcp.servers": {
    "souschef": {
      "command": "souschef",
      "args": [],
      "env": {}
    }
  }
}
```

### Multi-Server Setup

Run multiple MCP servers together:

```json
{
  "mcpServers": {
    "souschef": {
      "command": "souschef",
      "env": {
        "LOG_LEVEL": "INFO"
      }
    },
    "other-mcp-server": {
      "command": "other-server",
      "env": {}
    }
  }
}
```

## Next Steps

- [Start using SousChef](quick-start.md) with your configuration
- [Explore MCP tools](../user-guide/mcp-tools.md) available
- [Review CLI usage](../user-guide/cli-usage.md) for automation

For detailed configuration reference and troubleshooting, see [`config/CONFIGURATION.md`](https://github.com/kpeacocke/souschef/blob/main/config/CONFIGURATION.md) in the repository.
