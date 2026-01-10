# Server API

MCP server implementation and internal functions for the SousChef tool.

## Overview

The `souschef.server` module provides the MCP (Model Context Protocol) server implementation that exposes Chef-to-Ansible conversion tools to AI assistants like Claude Desktop and GitHub Copilot.

!!! info "MCP Framework"
    SousChef uses [FastMCP](https://github.com/jlowin/fastmcp) to implement the Model Context Protocol server. Tools are registered using the `@mcp.tool()` decorator.

---

## MCP Tools

See the [MCP Tools Reference](../user-guide/mcp-tools.md) for complete documentation of all 38 available MCP tools with usage examples.

---

## Usage Examples

### Basic Server Startup

```python
from souschef.server import mcp

# MCP server starts automatically when module is imported
# or can be run directly:
if __name__ == "__main__":
    mcp.run()
```

### Tool Registration Pattern

```python
from mcp import FastMCP

mcp = FastMCP("SousChef")

@mcp.tool()
def my_chef_tool(cookbook_path: str) -> str:
    """Parse a Chef cookbook.

    Args:
        cookbook_path: Path to the cookbook directory

    Returns:
        Analysis results as formatted text
    """
    # Implementation
    return results
```

### Calling Tools from Python

```python
from souschef.server import parse_recipe, convert_recipe_to_playbook

# Parse a recipe
analysis = parse_recipe("/path/to/recipe.rb")
print(analysis)

# Convert to playbook
playbook = convert_recipe_to_playbook("/path/to/recipe.rb")
print(playbook)
```

---

## Error Handling

All MCP tools follow consistent error handling:

```python
try:
    result = parse_recipe(recipe_path)
    return result
except FileNotFoundError:
    return f"Error: Recipe file not found: {recipe_path}"
except Exception as e:
    return f"An error occurred: {e}"
```

!!! warning "Error Messages"
    MCP tools return error messages as strings rather than raising exceptions. This ensures AI assistants receive actionable feedback.

---

## Type Safety

All tools use Python type hints for parameters and return values:

```python
def parse_recipe(recipe_path: str, format: str = "text") -> str:
    """Type-safe function signature."""
    pass
```

Benefits:
- IDE autocomplete and IntelliSense
- Static type checking with mypy
- Better documentation
- Reduced runtime errors

---

## Testing

See the test suite for examples of testing MCP tools:

- **Unit tests**: [tests/test_server.py](../../tests/test_server.py)
- **Integration tests**: [tests/test_integration.py](../../tests/test_integration.py)
- **MCP protocol tests**: [tests/test_mcp.py](../../tests/test_mcp.py)

---

## See Also

- **[CLI API](cli.md)** - Command-line interface implementation
- **[Parsers API](parsers.md)** - Chef artifact parsers
- **[Converters API](converters.md)** - Chef-to-Ansible converters
- **[MCP Tools Reference](../user-guide/mcp-tools.md)** - User-facing tool documentation
- **[FastMCP Documentation](https://github.com/jlowin/fastmcp)** - MCP framework

