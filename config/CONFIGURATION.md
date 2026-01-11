# MCP Configuration Examples

This directory contains example MCP server configurations for various MCP clients.

## 📁 Configuration Files

### Production Use (PyPI Installation)

- **`claude-desktop.json`** - Claude Desktop configuration using `uvx mcp-souschef`
- **`vscode-copilot.json`** - VS Code GitHub Copilot configuration using `uvx mcp-souschef`

### Development Use (Local Repository)

- **`claude-desktop-dev.json`** - Claude Desktop with local Poetry development setup
- **`vscode-copilot-dev.json`** - VS Code Copilot with local Poetry development setup

## Quick Setup

### Claude Desktop

**Production (after `pip install mcp-souschef`):**

```bash
# macOS
cp config/claude-desktop.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Linux
cp config/claude-desktop.json ~/.config/Claude/claude_desktop_config.json

# Windows
copy config\claude-desktop.json %APPDATA%\Claude\claude_desktop_config.json
```

**Development:**

```bash
# 1. Copy dev config
cp config/claude-desktop-dev.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# 2. Edit and replace /absolute/path/to/souschef with your actual path
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### VS Code GitHub Copilot

**Prerequisites**: VS Code 1.102+ with GitHub Copilot extension installed.

**Production (after `pip install mcp-souschef`):**

```bash
# macOS/Linux
cp config/vscode-copilot.json ~/.config/Code/User/mcp.json

# Windows
copy config\\vscode-copilot.json %APPDATA%\\Code\\User\\mcp.json

# Reload VS Code window: Cmd+Shift+P > \"Developer: Reload Window\"
# Trust the souschef server when prompted
```

**Development:**

```bash
# 1. Copy dev config
cp config/vscode-copilot-dev.json ~/.config/Code/User/mcp.json

# 2. Edit and replace /absolute/path/to/souschef with your actual path
code ~/.config/Code/User/mcp.json

# 3. Reload VS Code window and trust the server
```

## Model Provider Support

**SousChef is completely model-agnostic!** It works with any MCP-compatible client regardless of what AI model they use.

### Supported Configurations

####  Red Hat AI / IBM Watsonx / Enterprise Models

To use SousChef with Red Hat AI, Watsonx, or custom enterprise models, you need an MCP client that supports your model provider. Example configuration structure:

```json
{
  "mcpServers": {
    "souschef": {
      "command": "uvx",
      "args": ["mcp-souschef"]
    }
  },
  "modelProvider": "red-hat-ai",
  "modelConfig": {
    "endpoint": "https://your-ai-endpoint.example.com",
    "model": "llama-3-70b"
  }
}
```

**Note:** The `modelProvider` and `modelConfig` sections depend on your MCP client implementation. SousChef connects the same way regardless of the model.

####  OpenAI (GPT-4, GPT-3.5)

For OpenAI models, use an MCP client that supports OpenAI:

```json
{
  "mcpServers": {
    "souschef": {
      "command": "uvx",
      "args": ["mcp-souschef"]
    }
  },
  "modelProvider": "openai",
  "modelConfig": {
    "apiKey": "${OPENAI_API_KEY}",
    "model": "gpt-4-turbo"
  }
}
```

####  Local Models (Ollama, llama.cpp)

Run models locally with MCP clients that support local inference:

```json
{
  "mcpServers": {
    "souschef": {
      "command": "uvx",
      "args": ["mcp-souschef"]
    }
  },
  "modelProvider": "ollama",
  "modelConfig": {
    "endpoint": "http://localhost:11434",
    "model": "llama3:70b"
  }
}
```

####  Claude (Anthropic)

The provided example configs use Claude Desktop:

```json
{
  "mcpServers": {
    "souschef": {
      "command": "uvx",
      "args": ["mcp-souschef"]
    }
  }
}
```

####  GitHub Copilot (VS Code)

The provided VS Code configs work with Copilot:

```json
{
  "souschef": {
    "command": "uvx",
    "args": ["mcp-souschef"]
  }
}
```

### Key Principle: Client vs Server

** Important:**
- **MCP Server (SousChef)** = Provides the Chef/Ansible tools
- **MCP Client** = Runs your chosen AI model
- The client configuration determines which model you use
- SousChef configuration is the same for all models

## Configuration Options

### Using uvx (Recommended for Production)

```json
{
  "command": "uvx",
  "args": ["mcp-souschef"]
}
```

**Pros:**
- No global installation needed
- Automatic environment management
- Always uses latest version

### Using pip/pipx

```json
{
  "command": "mcp-souschef"
}
```

**Requirements:**
- Must have `pip install mcp-souschef` or `pipx install mcp-souschef` run first
- Package must be in PATH

### Using Poetry (Development)

```json
{
  "command": "poetry",
  "args": ["--directory", "/path/to/souschef", "run", "souschef"]
}
```

**Best for:**
- Local development
- Testing changes before publishing
- Contributing to the project

## Testing Your Configuration

### Claude Desktop

1. Copy/edit the appropriate config file
2. Restart Claude Desktop completely (quit and relaunch)
3. Look for the MCP connection indicator
4. Try: "What tools does souschef provide?"

### VS Code Copilot

1. Copy/edit the appropriate config file
2. Reload VS Code window (Cmd/Ctrl+Shift+P → "Developer: Reload Window")
3. Open Copilot Chat (Cmd/Ctrl+Shift+I)
4. Type `@souschef` and you should see it as available
5. Try: `@souschef list your available tools`

## 🐛 Troubleshooting

### Server Not Appearing

- **Check config location**: Ensure file is in correct directory
- **Check JSON syntax**: Validate with `python -m json.tool < config.json`
- **Check command availability**: Run command manually (e.g., `uvx mcp-souschef`)
- **Check logs**:
  - Claude Desktop: `~/Library/Logs/Claude/` (macOS)
  - VS Code: Output panel → "MCP" channel

### Command Not Found

**For uvx:**
```bash
# Install uv if missing
pip install uv
```

**For Poetry development:**
```bash
# Verify poetry is installed
poetry --version

# Verify souschef can run
cd /path/to/souschef
poetry run souschef --help
```

### Path Issues (Development)

Ensure you use **absolute paths** in dev configurations:

```bash
# Get absolute path
cd /path/to/souschef
pwd  # Use this output in your config
```

## Additional Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Setup](https://docs.anthropic.com/claude/docs/model-context-protocol)
- [SousChef Main README](../README.md)
- [Contributing Guide](../CONTRIBUTING.md)

## Tips

1. **Use uvx for simplicity** - No need to manage virtual environments
2. **Development setup** - Use Poetry configs when developing/testing
3. **Multiple servers** - You can configure multiple MCP servers in the same file
4. **Environment variables** - Add to `"env": {}` if needed for your setup

## 🤝 Contributing

Found an issue with these configs? Please [open an issue](https://github.com/kpeacocke/souschef/issues) or submit a PR!
