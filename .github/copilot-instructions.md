# SousChef Project - GitHub Copilot Instructions

## Project Overview
SousChef is an AI-powered MCP (Model Context Protocol) server that assists with converting Chef cookbooks to Ansible playbooks.

## Development Standards

### Code Quality
- **Zero warnings policy**: All code must be free of errors and warnings without disabling them
- **Type hints**: Use Python type hints for all function signatures
- **Docstrings**: Every function, class, and module must have clear docstrings following Google style
- **Linting**: Code must pass `ruff` linting checks with no violations
- **Formatting**: Code must be formatted with `ruff format`

### Testing Requirements
- **100% coverage goal**: Aim for as close to 100% test coverage as possible
- **Test framework**: Use `pytest` for all tests
- **Test structure**: Tests should be organized in `tests/` directory mirroring the source structure
- **Test naming**: Test functions should clearly describe what they test (e.g., `test_list_directory_success`)
- **Error cases**: Always test both success and failure scenarios
- **Mocking**: Use `unittest.mock` for external dependencies

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
- **Tool**: Use `uv` for dependency management
- **Lock file**: Always commit `uv.lock` to version control
- **Dev dependencies**: Keep development dependencies separate in `[dependency-groups]`

## Code Review Checklist
Before suggesting code, ensure:
1. ✅ No linting errors (`ruff check`)
2. ✅ Properly formatted (`ruff format`)
3. ✅ All tests pass (`pytest`)
4. ✅ Coverage maintained/improved (`pytest --cov`)
5. ✅ Type hints are complete
6. ✅ Docstrings are present and clear
7. ✅ Error cases are handled
8. ✅ Cross-platform compatible

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

## Anti-Patterns to Avoid
- ❌ Disabling linting warnings without fixing the underlying issue
- ❌ Missing type hints
- ❌ Untested code paths
- ❌ Platform-specific path handling
- ❌ Bare `except:` clauses
- ❌ Missing docstrings
- ❌ Hardcoded file paths

## When in Doubt
- Prioritize readability over cleverness
- Add tests before fixing bugs
- Document why, not just what
- Ask for clarification rather than assume
