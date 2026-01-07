# SousChef Project - GitHub Copilot Instructions

## Project Overview
SousChef is an AI-powered MCP (Model Context Protocol) server that assists with converting Chef cookbooks to Ansible playbooks.

## Project Architecture

### Module Structure
The project follows a modular architecture organized by functionality:

```
souschef/
├── __init__.py          # Package initialization
├── server.py            # MCP server entry point with tool registrations
├── cli.py               # Command-line interface
├── assessment.py        # Migration assessment and planning
├── deployment.py        # AWX/Tower and deployment strategies
├── core/                # Core utilities
│   ├── constants.py     # Shared constants
│   ├── path_utils.py    # Path normalization utilities
│   ├── ruby_utils.py    # Ruby value normalization
│   └── validation.py    # Validation engine
├── parsers/             # Chef artifact parsers
│   ├── attributes.py    # Attribute file parsing
│   ├── habitat.py       # Habitat plan parsing
│   ├── inspec.py        # InSpec profile parsing
│   ├── metadata.rb      # Cookbook metadata parsing
│   ├── recipe.py        # Recipe parsing
│   ├── resource.py      # Custom resource parsing
│   └── template.py      # ERB template parsing
├── converters/          # Chef to Ansible converters
│   ├── habitat.py       # Habitat to Docker conversion
│   ├── playbook.py      # Recipe to playbook conversion
│   └── resource.py      # Resource to task conversion
└── filesystem/          # Filesystem operations
    └── operations.py    # Directory/file operations
```

### Key Architecture Principles

1. **server.py as Entry Point**: All MCP tools are registered in `server.py`. Internal functions are imported from specialized modules.

2. **Backward Compatibility Exports**: Internal functions used by tests are re-exported from `server.py` with `# noqa: F401` comments to suppress unused import warnings.

3. **Module Responsibilities**:
   - `parsers/`: Parse Chef artifacts (read-only, extract structure)
   - `converters/`: Transform Chef to Ansible (produce output)
   - `core/`: Shared utilities (no business logic dependencies)
   - `assessment.py`: High-level migration planning
   - `deployment.py`: AWX integration and deployment strategies

4. **When to Keep Functions Together vs. Modularize**:
   - Keep tightly coupled MCP tools in `server.py` when they share significant context (e.g., databag/environment functions ~1,180 lines)
   - Extract when reusable across multiple tools or testable in isolation
   - Module size isn't the primary driver - cohesion and coupling are

5. **Mock Patching Rule**: When testing, patch functions where they are **used** (imported), not where they are **defined**. Example:
   ```python
   # Function defined in souschef/parsers/recipe.py
   # Used in souschef/converters/playbook.py
   # Patch: "souschef.converters.playbook._normalize_path"
   ```

## Development Standards

### Code Quality
- **Zero warnings policy**: All code must be free of errors and warnings from **all tools** (Ruff, mypy, Pylance) without disabling them
- **Type hints**: Use Python type hints for all function signatures in source code (`souschef/`). For test files, pytest fixtures (`tmp_path`, `benchmark`) and parameterized test parameters can omit type hints for brevity
- **Docstrings**: Every function, class, and module must have clear docstrings following Google style
- **Linting**: Code must pass `ruff check` with no violations
- **Formatting**: Code must be formatted with `ruff format`
- **Type checking**: Code must pass `mypy` type checking with no errors
- **Import cleanup**: ALWAYS respect `# noqa: F401` markers - these indicate intentional re-exports for backward compatibility with tests. Never remove imports marked with `# noqa: F401` even if they appear unused in the file itself

### Development Tools
SousChef uses a modern Python toolchain:

- **Ruff**: Primary linter and formatter (replaces Black, isort, flake8, etc.)
  - Runs in CI and on save in VS Code
  - Use: `poetry run ruff check .` and `poetry run ruff format .`

- **mypy**: Static type checker for CI/CD and command line
  - Runs in CI for strict type validation
  - Use: `poetry run mypy souschef`
  - Config: `[tool.mypy]` in `pyproject.toml`

- **Pylance**: VS Code language server for real-time feedback
  - Provides immediate type checking as you code
  - Complements mypy - Pylance for dev speed, mypy for CI strictness
  - Config: `.vscode/settings.json`

- **pytest**: Testing framework with coverage reporting
  - Use: `poetry run pytest --cov=souschef`
  - Config: `[tool.pytest.ini_options]` in `pyproject.toml`

### Testing Requirements
- **Current coverage**: 91% (913 tests passing across 13 test files)
- **Coverage goal**: Maintain 90%+ for production readiness, aim for 95%+
- **Test framework**: Use `pytest` for all tests
- **Test structure**: Tests should be organized in `tests/` directory mirroring the source structure
- **Test naming**: Test functions should clearly describe what they test (e.g., `test_list_directory_success`)
- **Error cases**: Always test both success and failure scenarios
- **Mocking**: Use `unittest.mock` for external dependencies

#### Multiple Test Types
The project maintains three types of tests - ensure all are updated when adding features:

1. **Unit Tests** (`tests/test_server.py`)
   - Mock-based tests for individual functions
   - Test error handling and edge cases
   - Fast execution, isolated from filesystem
   - Use `unittest.mock` to patch dependencies

2. **Integration Tests** (`tests/test_integration.py`)
   - Real file operations with test fixtures
   - Test with actual Chef cookbook files from `tests/fixtures/`
   - Use parameterized tests (`@pytest.mark.parametrize`) for multiple scenarios
   - Include performance benchmarks for parsing functions

3. **Property-Based Tests** (`tests/test_property_based.py`)
   - Use Hypothesis for fuzz testing
   - Generate random inputs to find edge cases
   - Ensure functions handle any input gracefully
   - Limit to 50 examples per test with `@settings(max_examples=50)`

#### Test Fixtures
- **Location**: `tests/fixtures/sample_cookbook/`
- **Contents**: Real Chef cookbook structure (metadata.rb, recipes/, attributes/)
- **Maintenance**: Update fixtures when adding new parsing capabilities
- **Adding fixtures**: Create realistic Chef content that exercises new features

#### Testing Best Practices
- When adding a new tool, add all three test types (unit, integration, property-based)
- Use `@pytest.mark.parametrize` for testing multiple inputs efficiently
- Add benchmarks for performance-sensitive parsing functions
- Update test fixtures when adding support for new Chef constructs
- Ensure integration tests validate actual parsing accuracy, not just coverage

### Cross-Platform Compatibility
- **File paths**: Use `pathlib.Path` instead of string concatenation for file paths
- **Line endings**: Configured via `.gitattributes` (LF for all files)
- **OS-specific code**: Avoid OS-specific code; use `os` and `pathlib` abstractions

### MCP Server Development
- **Framework**: Use `FastMCP` from `mcp.server.fastmcp` for server implementation
- **Tool definitions**: Use the `@mcp.tool()` decorator for defining tools
- **Error handling**: Always handle exceptions gracefully and return meaningful error messages
- **Type safety**: Leverage Python type hints for MCP tool parameters

### Git Practices
- **Clean commits**: Keep commits focused and atomic
- **Clear messages**: Use descriptive commit messages
- **Branch strategy**: Feature branches for new functionality

### Dependencies Management
- **Tool**: Use Poetry for dependency management
- **Lock file**: Always commit `poetry.lock` to version control
- **Dev dependencies**: Keep development dependencies separate in `[tool.poetry.group.dev.dependencies]`

## Code Review Checklist
Before suggesting code, ensure:
1.  No linting errors (`ruff check`)
2.  Properly formatted (`ruff format`)
3.  No type errors (`mypy souschef`)
4.  All tests pass (`pytest`)
5.  Coverage maintained at 90%+ (`pytest --cov`)
6.  Unit tests added/updated in `test_server.py`
7.  Integration tests added/updated in `test_integration.py`
8.  Property-based tests added if applicable in `test_property_based.py`
9.  Test fixtures updated if new parsing features added
10.  Type hints are complete
11.  Docstrings are present and clear
12.  Error cases are handled
13.  Cross-platform compatible

## Preferred Patterns

### Error Handling
```python
try:
    result = operation()
    return result
except SpecificError as e:
    return f"Error: {specific_message}"
except Exception as e:
    return f"An error occurred: {e}"
```

### Function Signatures
```python
def function_name(param: str, optional: int = 0) -> ReturnType:
    """Brief description.

    Args:
        param: Description of param.
        optional: Description of optional param.

    Returns:
        Description of return value.

    """
```

### Test Structure
```python
def test_function_name_scenario():
    """Test that function_name does X when Y."""
    # Arrange
    with patch("module.dependency") as mock:
        mock.return_value = expected_value

        # Act
        result = function_name(arg)

        # Assert
        assert result == expected_result
```

### Parameterized Test Structure
```python
@pytest.mark.parametrize("input_value,expected_output", [
    ("value1", "result1"),
    ("value2", "result2"),
    ("value3", "result3"),
])
def test_function_with_multiple_inputs(input_value, expected_output):
    """Test function with various inputs."""
    result = function_name(input_value)
    assert result == expected_output
```

### Integration Test with Fixtures
```python
def test_parse_real_file():
    """Test parsing a real Chef file."""
    fixture_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"
    result = parse_recipe(str(fixture_path))

    # Validate actual parsing results
    assert "Resource 1:" in result
    assert "Type: package" in result
```

### Property-Based Test Structure
```python
from hypothesis import given, settings
from hypothesis import strategies as st

@given(st.text(min_size=1, max_size=100))
@settings(max_examples=50)
def test_handles_any_input(random_input):
    """Test that function handles any string input."""
    result = function_name(random_input)
    assert isinstance(result, str)  # Should never crash
```

## Anti-Patterns to Avoid
-  Disabling linting warnings without fixing the underlying issue
-  Missing type hints
-  Untested code paths
-  Platform-specific path handling
-  Bare `except:` clauses
-  Missing docstrings
-  Hardcoded file paths

## Documentation Maintenance
- **README updates**: When adding new tools, features, or changing functionality, update README.md to reflect the changes
- **Keep examples current**: Ensure usage examples in README match actual tool signatures and behavior
- **Update roadmap**: Mark completed items and add new planned features to the roadmap section

## When in Doubt
- Prioritize readability over cleverness
- Add tests before fixing bugs
- Document why, not just what
- Ask for clarification rather than assume
