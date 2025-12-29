# SousChef 🍳

An AI-powered MCP (Model Context Protocol) server that assists with analyzing and converting Chef cookbooks to Ansible playbooks.

## Features

### Chef Cookbook Analysis
- **Parse Metadata** - Extract cookbook metadata (name, version, dependencies, etc.)
- **Parse Recipes** - Analyze Chef resources, actions, and properties
- **Parse Attributes** - Extract default, override, and normal attributes
- **List Cookbook Structure** - Display the directory structure of Chef cookbooks
- **File Operations** - Read files and list directories

### Coming Soon
- Chef to Ansible resource conversion
- Template conversion (ERB → Jinja2)
- Custom resource/LWRP parsing
- Full playbook generation

## Installation

### Prerequisites
- Python 3.14+
- [uv](https://github.com/astral-sh/uv) for dependency management

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd souschef
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Run tests to verify installation:
   ```bash
   uv run pytest
   ```

## Usage

### As an MCP Server

SousChef is designed to be used as an MCP server with AI assistants that support the Model Context Protocol.

#### Configure with Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "souschef": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/souschef",
        "run",
        "souschef"
      ]
    }
  }
}
```

### Available Tools

#### `list_directory(path: str)`
List the contents of a directory.

**Example:**
```python
list_directory("/path/to/cookbooks")
# Returns: ['nginx', 'apache2', 'mysql']
```

#### `read_file(path: str)`
Read the contents of a file.

**Example:**
```python
read_file("/path/to/cookbook/recipes/default.rb")
# Returns: file contents as string
```

#### `read_cookbook_metadata(path: str)`
Parse Chef cookbook metadata.rb file.

**Example:**
```python
read_cookbook_metadata("/path/to/cookbook/metadata.rb")
# Returns:
# name: nginx
# maintainer: Chef Software, Inc.
# version: 8.0.0
# depends: logrotate, iptables
```

#### `parse_recipe(path: str)`
Parse a Chef recipe file and extract resources.

**Example:**
```python
parse_recipe("/path/to/cookbook/recipes/default.rb")
# Returns:
# Resource 1:
#   Type: package
#   Name: nginx
#   Action: install
```

#### `parse_attributes(path: str)`
Parse a Chef attributes file and extract attribute definitions.

**Example:**
```python
parse_attributes("/path/to/cookbook/attributes/default.rb")
# Returns:
# default[nginx.port] = 80
# default[nginx.ssl_port] = 443
```

#### `list_cookbook_structure(path: str)`
List the structure of a Chef cookbook directory.

**Example:**
```python
list_cookbook_structure("/path/to/cookbook")
# Returns:
# recipes/
#   default.rb
#   install.rb
# attributes/
#   default.rb
# metadata/
#   metadata.rb
```

## Development

### Project Structure

```
souschef/
├── souschef/
│   ├── __init__.py
│   └── server.py          # MCP server implementation
├── tests/
│   ├── __init__.py
│   └── test_server.py     # Comprehensive test suite
├── .devcontainer/         # VS Code dev container config
├── .github/
│   └── copilot-instructions.md  # Copilot development guidelines
├── pyproject.toml         # Project configuration
└── README.md
```

### Development Standards

- **Code Quality**: Zero warnings policy, type hints required, Google-style docstrings
- **Testing**: 100% test coverage goal using pytest
- **Linting**: Code must pass `ruff check` with no violations
- **Formatting**: Code must be formatted with `ruff format`

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for detailed development guidelines.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=souschef --cov-report=term-missing --cov-report=html

# Run linting
uv run ruff check .

# Run formatting
uv run ruff format .
```

### VS Code Tasks

The project includes several VS Code tasks:
- **Run Tests** - Execute test suite
- **Run Tests with Coverage** - Generate coverage reports
- **Lint (Ruff)** - Check code quality
- **Format (Ruff)** - Auto-format code
- **Lint & Test** - Run both linting and tests

## Contributing

Contributions are welcome! Please ensure:
1. All tests pass
2. Code coverage remains at 100%
3. Code passes ruff linting
4. All functions have type hints and docstrings
5. Follow the development standards in `.github/copilot-instructions.md`

## License

TBD

## Roadmap

- [ ] Add server entry point and runner
- [ ] Implement Chef → Ansible resource conversion
- [ ] Support template conversion (ERB → Jinja2)
- [ ] Parse custom Chef resources/LWRPs
- [ ] Generate complete Ansible playbooks
- [ ] Handle Chef guards and notifications
- [ ] Support complex attribute precedence
- [ ] Add conversion validation and testing
