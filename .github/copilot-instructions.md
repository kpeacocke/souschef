# SousChef Project - GitHub Copilot Instructions

## Project Overview
SousChef is an AI-powered MCP (Model Context Protocol) server that assists with converting Chef cookbooks to Ansible playbooks.

## Development Standards

### Code Quality
- **Zero warnings policy**: All code must be free of errors and warnings without disabling them
- **Type hints**: Use Python type hints for all function signatures in source code (`souschef/`). For test files, pytest fixtures (`tmp_path`, `benchmark`) and parameterized test parameters can omit type hints for brevity
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
1. ✅ No linting errors (`ruff check`)
2. ✅ Properly formatted (`ruff format`)
3. ✅ All tests pass (`pytest`)
4. ✅ Coverage maintained/improved (`pytest --cov`)
5. ✅ Unit tests added/updated in `test_server.py`
6. ✅ Integration tests added/updated in `test_integration.py`
7. ✅ Property-based tests added if applicable in `test_property_based.py`
8. ✅ Test fixtures updated if new parsing features added
9. ✅ Type hints are complete
10. ✅ Docstrings are present and clear
11. ✅ Error cases are handled
12. ✅ Cross-platform compatible

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
- ❌ Disabling linting warnings without fixing the underlying issue
- ❌ Missing type hints
- ❌ Untested code paths
- ❌ Platform-specific path handling
- ❌ Bare `except:` clauses
- ❌ Missing docstrings
- ❌ Hardcoded file paths

## Documentation Maintenance
- **README updates**: When adding new tools, features, or changing functionality, update README.md to reflect the changes
- **Keep examples current**: Ensure usage examples in README match actual tool signatures and behavior
- **Update roadmap**: Mark completed items and add new planned features to the roadmap section

## When in Doubt
- Prioritize readability over cleverness
- Add tests before fixing bugs
- Document why, not just what
- Ask for clarification rather than assume
