# Server API

MCP server implementation and internal functions for the SousChef tool.

## Overview

The `souschef.server` module provides the MCP (Model Context Protocol) server implementation that exposes Chef-to-Ansible conversion tools to AI assistants like Claude Desktop and GitHub Copilot.

!!! info "MCP Framework"
    SousChef uses [FastMCP](https://github.com/jlowin/fastmcp) to implement the Model Context Protocol server. Tools are registered using the `@mcp.tool()` decorator.

---

## Server Entry Point

::: souschef.server
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3
      members:
        - main

---

## Core Parsing Tools

### Recipe Parsing

::: souschef.server.parse_recipe
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### Template Parsing

::: souschef.server.parse_template
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### Resource Parsing

::: souschef.server.parse_custom_resource
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### Attribute Parsing

::: souschef.server.parse_attributes
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### Metadata Parsing

::: souschef.server.parse_metadata
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

---

## Conversion Tools

### Recipe to Playbook Conversion

::: souschef.server.convert_recipe_to_playbook
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### Full Cookbook Conversion

::: souschef.server.convert_full_cookbook
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

---

## Structural Analysis

### Cookbook Structure

::: souschef.server.analyze_cookbook_structure
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### Migration Assessment

::: souschef.server.assess_chef_migration_complexity
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### Dependency Analysis

::: souschef.server.analyze_cookbook_dependencies
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### Migration Planning

::: souschef.server.generate_migration_plan
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

---

## InSpec Tools

### InSpec Profile Parsing

::: souschef.server.parse_inspec_profile
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### InSpec to Ansible Test Conversion

::: souschef.server.convert_inspec_to_ansible_tests
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### InSpec Report Generation

::: souschef.server.generate_inspec_summary
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

---

## Habitat Tools

### Habitat Plan Parsing

::: souschef.server.parse_habitat_plan
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### Habitat to Docker Conversion

::: souschef.server.convert_habitat_to_docker
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### Docker Compose Generation

::: souschef.server.generate_docker_compose
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

---

## Data Management Tools

### Data Bag Operations

::: souschef.server.read_data_bag
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

::: souschef.server.list_data_bags
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

::: souschef.server.list_data_bag_items
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

::: souschef.server.convert_data_bag_to_ansible_vars
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### Environment Operations

::: souschef.server.read_environment
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

::: souschef.server.list_environments
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

::: souschef.server.convert_environment_to_ansible_inventory
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

---

## Filesystem Operations

### Directory Operations

::: souschef.server.list_directory
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### File Reading

::: souschef.server.cat_file
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

---

## Deployment Tools

### AWX Configuration

::: souschef.server.generate_awx_job_templates
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### Deployment Strategies

::: souschef.server.generate_deployment_strategy
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

---

## Performance Tools

### Resource Profiling

::: souschef.server.profile_recipe_parsing
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

::: souschef.server.profile_cookbook_conversion
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

---

## Validation Tools

### Playbook Validation

::: souschef.server.validate_playbook
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

### Conversion Validation

::: souschef.server.validate_conversion
    options:
      show_root_heading: true
      show_source: false
      heading_level: 4

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

