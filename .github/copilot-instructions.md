# SousChef Project - GitHub Copilot Instructions

## Project Overview
SousChef is an AI-powered MCP (Model Context Protocol) server that assists with converting Chef cookbooks to Ansible playbooks.

## Specialised Agents
For focused expertise on specific tasks, refer to [**AGENTS.md**](AGENTS.md) which defines specialised agents:
- **Test Coverage Guardian**: Achieve 100% coverage with best-in-class testing
- **Quality Enforcer**: Zero warnings from ruff, mypy, Pylance
- **Architecture Reviewer**: Ensure code follows modular structure
- **TDD Coach**: Guide test-driven development
- **Migration Specialist**: Chef-to-Ansible conversion expertise
- **Documentation Maintainer**: Keep docs accurate and current
- **Performance Optimiser**: Profile and optimise bottlenecks

Invoke agents with: `@AgentName [task description]`

## Project Architecture

### Module Structure
The project follows a **7-layer modular architecture** with strict dependency discipline:

```
souschef/
├── __init__.py          # Package initialization
├── server.py            # MCP server entry point (Layer 7)
├── cli.py               # Command-line interface (Layer 7)
├── ui/                  # Web interface (Layer 7)
├── orchestrators/       # Workflow coordination (Layer 6)
├── assessment.py        # Migration planning (Layer 6)
├── deployment.py        # AWX/Tower deployment (Layer 6)
├── api/                 # REST API endpoints (Layer 5)
├── integrations/        # External integrations (Layer 5)
│   └── github/          # GitHub integration
├── auth/                # Authentication & RBAC (Layer 4)
├── audit/               # Audit logging (Layer 4)
├── benchmarking/        # Performance profiling (Layer 4)
├── parsers/             # Input parsing (Layer 3)
│   ├── attributes.py    # Chef attribute parsing
│   ├── habitat.py       # Habitat plan parsing
│   ├── inspec.py        # InSpec profile parsing
│   ├── metadata.py      # Cookbook metadata parsing
│   ├── recipe.py        # Recipe parsing
│   ├── resource.py      # Custom resource parsing
│   └── template.py      # ERB template parsing
├── converters/          # Transformations (Layer 3)
│   ├── habitat.py       # Habitat to Docker
│   ├── playbook.py      # Recipe to playbook
│   └── resource.py      # Resource to task
├── generators/          # Output generation (Layer 3)
├── storage/             # Data persistence (Layer 2)
├── filesystem/          # File operations (Layer 2)
├── ir/                  # Intermediate representation (Layer 2)
└── core/                # Foundation utilities (Layer 1)
    ├── constants.py     # Shared constants
    ├── errors.py        # Custom exceptions
    ├── path_utils.py    # Path normalization
    ├── ruby_utils.py    # Ruby value parsing
    └── validation.py    # Validation helpers
```

### Key Architecture Principles

1. **server.py as Entry Point**: All MCP tools are registered in `server.py`. Internal functions are imported from specialised modules.

2. **Backward Compatibility Exports**: Internal functions used by tests are re-exported from `server.py` with `# noqa: F401` comments to suppress unused import warnings.

3. **Layered Architecture with Dependency Discipline**:
   - 7 layers: Foundation → Data → Domain → Services → Integration → Orchestration → UI
   - Dependencies ONLY flow downward (never upward)
   - Enforced by SonarCloud to prevent architectural drift
   - See [ARCHITECTURE.md](../docs/ARCHITECTURE.md) for complete details

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

6. **Respecting the Architecture**: Always follow the established module structure. Refer to [**ARCHITECTURE.md**](../docs/ARCHITECTURE.md) for:
   - **Layered architecture** (7 layers with strict downward dependencies)
   - **Decision tree** for where code belongs
   - **Container definitions** and module responsibilities
   - **Dependency matrix** showing allowed imports
   - **SonarCloud enforcement** rules
   - When to create new modules vs. reusing existing ones

   **Critical Architecture Rules**:
   - Dependencies ONLY flow downward (higher layers → lower layers)
   - Lower layers NEVER import from higher layers
   - `core/` has NO internal souschef dependencies
   - Use the decision tree before placing code

   **Before suggesting changes, ask**: "Does this belong in this module? Should it be refactored to another module instead? Does this violate dependency rules?"

7. **Security Awareness**: Be mindful of security anti-patterns documented in [**SECURITY_ANTI_PATTERNS.md**](../docs/SECURITY_ANTI_PATTERNS.md):
   - Never use string interpolation in shell commands (use array form)
   - Validate all inputs against appropriate patterns
   - Avoid shell metacharacters in parameters
   - Reference OWASP/CWE guidelines for secure patterns
   - Test fixtures may contain insecure code intentionally - never copy to production

## Development Standards

**IMPORTANT**: Review [**CONTRIBUTING.md**](../CONTRIBUTING.md) for complete contribution guidelines, PR checklist, and workflow.

### Code Quality
- **Zero warnings policy**: All code must be free of errors and warnings from **all tools** (Ruff, mypy, Pylance) without disabling them
- **Code suppressions require approval**: NEVER add code suppressions (`# noqa`, `# type: ignore`, `# pylint: disable`, `# codeql[...]`, `|| true`, `|| echo`, `continue-on-error`, etc.) without explicitly asking the user first. Always fix the underlying issue rather than masking it. The only exceptions are:
  - Pre-existing `# noqa: F401` markers for backward compatibility exports (respect these, never remove them)
  - User-approved suppressions for legitimate false positives after attempting proper fixes
  - Document the reason for any approved suppression with a comment explaining why it's necessary
- **Type hints**: Use Python type hints for all function signatures in source code (`souschef/`). For test files, pytest fixtures (`tmp_path`, `benchmark`) and parameterized test parameters can omit type hints for brevity
- **Docstrings**: Every function, class, and module must have clear docstrings following Google style
- **Linting**: Code must pass `ruff check` with no violations
- **Formatting**: Code must be formatted with `ruff format`
- **Type checking**: Code must pass `mypy` type checking with no errors
- **Import cleanup**: ALWAYS respect `# noqa: F401` markers - these indicate intentional re-exports for backward compatibility with tests. Never remove imports marked with `# noqa: F401` even if they appear unused in the file itself
- **Australian English**: Use Australian English spelling in all documentation, comments, and docstrings:
  - Use: colour, centre, organise, recognise, optimise, customise, behaviour, honour, etc.
  - Not: color, center, organize, recognize, optimize, customize, behavior, honor, etc.
  - This includes docstrings, comments, and documentation files

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
- **Coverage goal**: Achieve and maintain 100% line and branch coverage
- **Test framework**: Use `pytest` for all tests
- **Test structure**: Tests should be organised in `tests/` directory mirroring the source structure
- **Test naming**: Test functions should clearly describe what they test (e.g., `test_list_directory_success`)
- **Error cases**: Always test both success and failure scenarios
- **Mocking**: Use `unittest.mock` for external dependencies
- **TDD Approach**: Prefer Test-Driven Development (write tests before implementation)
- **Coverage Analysis**: Use `--cov-report=html` and `--cov-report=term-missing` to identify gaps

#### Multiple Test Types
The project maintains three types of tests - ensure all are updated when adding features:

1. **Unit Tests** (`tests/unit/test_server.py`)
   - Mock-based tests for individual functions
   - Test error handling and edge cases
   - Fast execution, isolated from filesystem
   - Use `unittest.mock` to patch dependencies

2. **Integration Tests** (`tests/integration/test_integration.py`)
   - Real file operations with test fixtures
- Test with actual Chef cookbook files from `tests/integration/fixtures/`
   - Use parameterized tests (`@pytest.mark.parametrize`) for multiple scenarios
   - Include performance benchmarks for parsing functions

3. **Property-Based Tests** (`tests/unit/test_property_based.py`)
   - Use Hypothesis for fuzz testing
   - Generate random inputs to find edge cases
   - Ensure functions handle any input gracefully
   - Limit to 50 examples per test with `@settings(max_examples=50)`

#### Test Fixtures
- **Location**: `tests/integration/fixtures/sample_cookbook/`
- **Contents**: Real Chef cookbook structure (metadata.rb, recipes/, attributes/)
- **Maintenance**: Update fixtures when adding new parsing capabilities
- **Adding fixtures**: Create realistic Chef content that exercises new features

#### Test Organisation and Discovery
- **Test file naming**: `test_<module_name>.py` mirrors source structure
  - Source: `souschef/parsers/recipe.py` → Test: `tests/unit/test_parsers_recipe.py`
  - Source: `souschef/core/validation.py` → Test: `tests/unit/test_core_validation.py`
- **Test discovery**: pytest automatically discovers `test_*.py` or `*_test.py` files
- **Test function naming**: `test_<function>_<scenario>` clearly describes behaviour
  - Example: `test_parse_recipe_with_invalid_syntax`
  - Example: `test_list_directory_when_path_not_exists`
- **Test class grouping**: Use classes to group related tests (optional)
  ```python
  class TestRecipeParser:
      def test_parse_simple_recipe(self): ...
      def test_parse_complex_recipe(self): ...
  ```

#### Testing Best Practices
- **Test-Driven Development (TDD)**: Write tests before implementation (Red-Green-Refactor)
  1. Write a failing test that describes desired behaviour (RED)
  2. Write minimal code to make the test pass (GREEN)
  3. Refactor code while keeping tests green (REFACTOR)
- When adding a new tool, add all three test types (unit, integration, property-based)
- Use `@pytest.mark.parametrize` for testing multiple inputs efficiently
- Add benchmarks for performance-sensitive parsing functions
- Update test fixtures when adding support for new Chef constructs
- Ensure integration tests validate actual parsing accuracy, not just coverage

#### Advanced Testing Techniques
- **Coverage Gap Analysis**:
  - Run `poetry run pytest --cov=souschef --cov-report=html --cov-report=term-missing`
  - Review `htmlcov/index.html` for visual coverage map
  - Focus on uncovered lines shown in terminal output
  - Identify missing branches (if/else not fully tested)
- **Edge Cases to Test**:
  - None values and null inputs
  - Empty strings, lists, and dictionaries
  - Boundary conditions (min/max values, zero, negative)
  - Error states and exception paths
  - Unicode and special characters
  - Large inputs (performance testing)
- **Testing Private Functions**:
  - Private functions (prefixed with `_`) should be tested indirectly through public API
  - If a private function is complex enough to warrant direct testing, consider:
    - Making it public if it provides reusable utility
    - Moving it to a separate module if it has standalone value
    - Testing through public functions that call it
  - Only test private functions directly if they contain critical logic that's hard to cover via public API
- **Test Markers for Organisation**:
  ```python
  @pytest.mark.slow  # Long-running tests
  @pytest.mark.integration  # Integration tests
  @pytest.mark.unit  # Unit tests
  @pytest.mark.property  # Property-based tests
  ```
  - Run specific markers: `poetry run pytest -m "not slow"`
  - Run fast tests only: `poetry run pytest -m "unit"`
- **Mutation Testing for Quality**:
  - Use `mutmut` to verify tests catch intentional bugs
  - Install: `poetry add --group dev mutmut`
  - Run: `poetry run mutmut run`
  - Tests should fail when code is mutated (high mutation score = good tests)
- **Performance Testing**:
  - Use `@pytest.mark.benchmark` for performance-critical functions
  - Compare performance before/after optimisations
  - Set performance budgets for critical paths

#### When Code is Legitimately Untestable
Some code cannot or should not be extensively tested:
- **Platform-specific code**: OS-level operations that can't be mocked reliably
- **Third-party integrations**: External APIs where mocking is insufficient (use integration tests sparingly)
- **Trivial code**: Simple property getters/setters with no logic
- **Configuration loading**: Basic file I/O without complex logic (test via integration)
- **Main entry points**: `if __name__ == "__main__":` blocks (test CLI separately)

**Approach for near-untestable code**:
1. Isolate untestable code in thin wrapper functions
2. Test business logic separately with mocks
3. Document why code is untested (comment + pragma)
4. Use integration tests to verify end-to-end behaviour
5. Ask user for approval before adding `# pragma: no cover`

#### Coverage Report Interpretation
- **Line coverage**: Percentage of code lines executed during tests
- **Branch coverage**: Percentage of conditional branches tested (both if/else paths)
- **Target**: 100% line and branch coverage
- **Interpreting HTML reports** (`htmlcov/index.html`):
  - Green lines: Covered by tests
  - Red lines: Not executed by any test
  - Yellow lines: Partially covered (some branches untested)
  - Click filenames to see line-by-line coverage
- **Terminal missing report**: Shows uncovered line numbers directly
- **Focus areas**: Functions with 0% coverage, edge cases, error handling

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

## Quality Assurance Checklist
**CRITICAL**: Before committing or submitting ANY code changes, you MUST complete this comprehensive checklist.

### Mandatory Pre-Submission Checks
These checks MUST pass without errors:

1.  ✅ **Ruff Linting** (exit code 0 required):
    ```bash
    poetry run ruff check .
    poetry run ruff check . --fix  # Auto-fix where possible
    ```
    - Zero violations allowed
    - Fix all errors manually if auto-fix insufficient

2.  ✅ **Code Formatting** (properly formatted):
    ```bash
    poetry run ruff format .
    ```
    - All code must follow consistent style

3.  ✅ **Type Checking** (zero errors required):
    ```bash
    poetry run mypy souschef
    ```
    - No type errors in source code
    - Standard library stub warnings can be ignored
    - Pylance should show no warnings in VS Code

4.  ✅ **Test Suite** (all tests pass):
    ```bash
    poetry run pytest --cov=souschef --cov-report=term-missing --cov-report=html
    ```
    - Exit code 0 required (all tests pass)
    - Coverage maintained or improved (target: 100%)
    - Review uncovered lines in terminal output
    - Check `htmlcov/index.html` for visual coverage gaps

5.  ✅ **Git Status** (clean state):
    ```bash
    git status
    ```
    - No uncommitted changes (unless intentional)
    - No temporary or generated files
    - `.gitignore` properly configured

### Code Quality Checklist
Before submitting code changes, verify:

**Testing:**
- [ ] Unit tests added/updated in `tests/unit/`
- [ ] Integration tests added/updated in `tests/integration/`
- [ ] Property-based tests added if applicable in `tests/unit/test_property_based.py`
- [ ] Test fixtures updated for new Chef constructs
- [ ] All three test types present for new features
- [ ] Edge cases tested (None, empty, boundaries, errors)
- [ ] Error paths and exceptions covered
- [ ] Test names clearly describe scenarios
- [ ] Tests follow Arrange-Act-Assert pattern

**Code Standards:**
- [ ] Type hints complete for all function signatures
- [ ] Docstrings present and clear (Google style)
- [ ] Australian English in all documentation/comments
- [ ] Cross-platform compatible (`pathlib.Path` for paths)
- [ ] No hardcoded file paths
- [ ] Error handling comprehensive (no bare `except:`)
- [ ] No code suppressions without user approval
- [ ] Existing `# noqa: F401` markers respected

**Architecture:**
- [ ] Code placed in correct module using [decision tree](../docs/ARCHITECTURE.md)
- [ ] Module responsibilities respected (see layer definitions)
- [ ] Dependency rules followed (downward only, no upward imports)
- [ ] SonarCloud enforcement rules not violated
- [ ] No tight coupling between modules
- [ ] Functions extracted when reusable
- [ ] Mock patching done where functions are used
- [ ] Security anti-patterns avoided (see [SECURITY_ANTI_PATTERNS.md](../docs/SECURITY_ANTI_PATTERNS.md))

**Documentation:**
- [ ] README updated if features changed
- [ ] Usage examples accurate and current
- [ ] API documentation reflects changes
- [ ] Comments explain "why", not "what"

### Quick Quality Check Command
Run all checks in sequence:
```bash
poetry run ruff check . && poetry run ruff format . && poetry run mypy souschef && poetry run pytest --cov=souschef --cov-report=term-missing
```

### When Checks Fail
- **Never suppress errors** without attempting to fix them first
- **Never commit failing code** - all checks must pass
- **Ask for help** if stuck - use specialised agents:
  - Coverage improvements → @TestCoverageGuardian
  - Quality issues → @QualityEnforcer
  - Architecture questions → @ArchitectureReviewer
  - TDD guidance → @TDDCoach
  - See [AGENTS.md](AGENTS.md) for full agent list

**IMPORTANT**: These checks are mandatory quality gates. Do not skip them or commit code that fails any check.

## Best Practices and Patterns

### Security Considerations

**CRITICAL**: Review [SECURITY_ANTI_PATTERNS.md](../docs/SECURITY_ANTI_PATTERNS.md) to avoid common security issues:

```python
# ❌ NEVER: String interpolation in shell commands (Command Injection - CWE-78)
execute "dangerous" do
  command "docker pull #{user_input}"  # Vulnerable to injection!
end

# ✅ ALWAYS: Use array form to prevent injection
execute "safe" do
  command ["docker", "pull", user_input]  # Arguments passed safely
end

# ✅ Validate inputs against expected patterns
import re
if not re.match(r'^[a-z0-9][a-z0-9._-]*(/[a-z0-9._-]+)*$', image_name):
    raise ValueError(f"Invalid image name: {image_name}")
```

**Security Checklist**:
- [ ] No string interpolation in shell commands
- [ ] All user inputs validated
- [ ] No shell metacharacters (`;|&$()<>`) in parameters
- [ ] Proper escaping/sanitization applied
- [ ] Follows OWASP guidelines (document CWE/CAPEC references)

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
-  **Adding suppressions without user approval** - Never add `# noqa`, `# type: ignore`, `# pylint: disable`, `# codeql[...]`, `|| true`, `|| echo`, `continue-on-error: true`, `--skip-editable`, or similar bypasses without explicitly asking the user first
-  **Masking problems instead of fixing them** - Always attempt to fix the underlying issue rather than suppressing warnings or errors
-  **Disabling linting warnings** - Don't disable warnings without user approval and documented justification
-  **Accepting test/check failures** - Don't use `|| true`, `|| echo`, or similar patterns to ignore failures without user consent
-  Missing type hints
-  Untested code paths
-  Platform-specific path handling
-  Bare `except:` clauses
-  Missing docstrings
-  Hardcoded file paths
-  **Using emojis in UI elements** - The user strongly dislikes emojis in navigation buttons, tooltips, and interface elements. Use plain text instead.

## Documentation Maintenance
- **README updates**: When adding new tools, features, or changing functionality, update README.md to reflect the changes
- **Keep examples current**: Ensure usage examples in README match actual tool signatures and behavior
- **Update roadmap**: Mark completed items and add new planned features to the roadmap section

## Contributing Guidelines

For comprehensive contribution guidelines, see [**CONTRIBUTING.md**](../CONTRIBUTING.md):
- Pull request workflow
- PR checklist
- Adding new MCP tools
- Dependency management
- Commit message conventions
- Branch strategy

## When in Doubt
- **Architecture**: Use the [decision tree](../docs/ARCHITECTURE.md)
- **Dependencies**: Check the [dependency matrix](../docs/ARCHITECTURE.md)
- **Security**: Review [SECURITY_ANTI_PATTERNS.md](../docs/SECURITY_ANTI_PATTERNS.md)
- **Contributing**: Follow [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Agents**: Consult [AGENTS.md](AGENTS.md) for specialised help
- Prioritise readability over cleverness
- Add tests before fixing bugs
- Document why, not just what
- Ask for clarification rather than assume
