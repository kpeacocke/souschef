# Contributing to SousChef

Thank you for contributing! This guide covers essentials for contributing to Chef-to-Ansible migration and Ansible upgrade planning tools.

## Quick Start

```bash
git clone https://github. com/kpeacocke/souschef.git && cd souschef
poetry install
poetry run pytest --cov=souschef  # All tests should pass
poetry run ruff check .            # No errors
poetry run mypy souschef           # No type errors
```

**Prerequisites:** Python 3.10+, Poetry, Git

## Architecture

**Read [ARCHITECTURE.md](docs/ARCHITECTURE.md) first!** It explains:

- Module responsibilities (parsers/, converters/, core/, etc.)
- Decision tree for where code belongs
- Design patterns and common scenarios

**Quick reference:**

- `parsers/` = Extract Chef/Ansible artifacts (read-only)
- `converters/` = Transform Chef to Ansible
- `assessment.py` = Migration planning
- `deployment.py` = AWX/AAP integration
- `ansible_upgrade.py` = Ansible upgrade planning
- `server.py` = MCP tool registration
- `cli.py` = Command-line interface

## Code Standards

### Zero Warnings Policy

All code must pass **all tools** with zero errors/warnings:

```bash
poetry run ruff check .      # Linting (MUST pass)
poetry run ruff format .     # Formatting
poetry run mypy souschef     # Type checking (MUST pass)
poetry run pytest --cov      # Tests (MUST pass, 90%+ coverage)
```

**Critical:** Never add code suppressions (`# noqa`, `# type: ignore`, etc.) without user approval. Fix the issue, don't mask it.

**Exception:** Pre-existing `# noqa: F401` for backward compatibility exports—respect these.

### Type Hints

- **Source code** (`souschef/`): Type hints required for all functions
- **Test files**: Can omit types for pytest fixtures and parameterized tests
- Use built-in types (dict, list) and `typing` module appropriately

### Docstrings

Google style, required for all functions/classes/modules:

```python
def convert_resource(name: str, action: str) -> dict:
    """Convert Chef resource to Ansible task.
    
    Args:
        name: Resource name.
        action: Resource action (install, create, etc.).
    
    Returns:
        Dictionary with Ansible task definition.
    
    Raises:
        ValueError: If resource type unsupported.
    """
```

### Australian English

Use Australian English spelling in all documentation, comments, and docstrings:

- **Use:** colour, centre, organise, recognise, optimise, behaviour
- **Not:** color, center, organize, recognize, optimize, behavior

## Testing Requirements

### Three Test Types Required

**1. Unit Tests** (`tests/unit/test_server.py`)

Mock-based, fast, isolated:

```python
def test_parse_recipe_success():
    """Test recipe parsing with mocked file."""
    with patch("souschef.server.Path.read_text") as mock:
        mock.return_value = "package 'nginx'"
        result = parse_recipe("/path/to/recipe.rb")
        assert "nginx" in result
```

**2. Integration Tests** (`tests/integration/test_integration.py`)

Real files from `tests/integration/fixtures/`:

```python
def test_parse_real_recipe():
    """Test with actual Chef recipe file."""
    fixture_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / "default.rb"
    result = parse_recipe(str(fixture_path))
    assert "Resource 1:" in result
```

**3. Property-Based Tests** (`tests/unit/test_property_based.py`)

Fuzz testing with Hypothesis:

```python
@given(st.text(min_size=1, max_size=100))
@settings(max_examples=50)
def test_handles_any_input(random_input):
    """Test function handles any string input."""
    result = function_name(random_input)
    assert isinstance(result, str)  # Should never crash
```

### Coverage Goal

- **Current:** 91% (3,500+ passing tests)
- **Requirement:** Maintain 90%+, aim for 95%+
- **For New Code:** All three test types required

## Dependency Management

### Adding Dependencies

```bash
# Production dependency
poetry add package-name

# Development dependency
poetry add --group dev package-name

# With version constraints
poetry add "package-name>=1.0.0,<2.0.0"
```

### Lock File Synchronization

**Three layers of automation prevent lock file issues:**

1. **Pre-commit hooks** (automatic): Validates and regenerates lock on each commit
2. **GitHub Actions** (CI): Validates lock in all PRs
3. **Dependabot** (weekly): Automated dependency updates

**Manual update if needed:**

```bash
poetry lock  # Updates lock file
poetry check # Validates pyproject.toml and poetry.lock match
```

## Submitting Changes

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow code standards, add tests, update docs if needed.

### 3. Pre-Submit Checklist

Run these checks **before committing**:

```bash
# Lint and format
poetry run ruff check .
poetry run ruff format .

# Type check
poetry run mypy souschef

# Run tests
poetry run pytest --cov=souschef

# Check git status
git status  # Should be clean after commit
```

These checks are **mandatory quality gates**. Do not skip.

### 4. Commit with Conventional Commits

Format: `<type>(<scope>): <subject>`

**Types:**
- `feat:` = New feature (minor version bump)
- `fix:` = Bug fix (patch version bump)
- `docs:` = Documentation only
- `test:` = Test changes
- `refactor:` = Code refactoring
- `perf:` = Performance improvements
- `chore:` = Maintenance
- `ci:` = CI/CD changes

**Breaking changes:** Add `!` or `BREAKING CHANGE:` in body:

```bash
git commit -m "feat!: change MCP tool parameter names

BREAKING CHANGE: Renamed 'path' parameter to 'file_path' for consistency."
```

### 5. Create Pull Request

**PR Checklist:**

- [ ] No linting errors (`ruff check`)
- [ ] Properly formatted (`ruff format`)
- [ ] No type errors (`mypy souschef`)
- [ ] All tests pass (`pytest`)
- [ ] Coverage maintained/improved (90%+)
- [ ] Unit, integration, and property-based tests added
- [ ] Type hints complete
- [ ] Docstrings present and clear
- [ ] Error cases handled
- [ ] Cross-platform compatible (use `pathlib.Path`)
- [ ] Architecture respected (code in correct module)
- [ ] Australian English spelling

## Adding New MCP Tools

### Implementation Steps

**1. Create the tool function:**

```python
@mcp.tool()
def your_new_tool(parameter: str) -> str:
    """Brief description.
    
    Args:
        parameter: Description.
    
    Returns:
        Description of return value.
    
    Raises:
        ValueError: When parameter invalid.
    """
    try:
        # Implementation
        return result
    except Exception as e:
        return f"Error: {e}"
```

**2. Add to CLI** (if appropriate):

```python
@cli.command()
@click.argument("parameter", type=str)
def your_command(parameter: str) -> None:
    """CLI command description."""
    result = your_new_tool(parameter)
    click.echo(result)
```

**3. Add comprehensive tests:**

- Unit tests with mocks
- Integration tests with fixtures
- Property-based tests
- Error case coverage

**4. Update documentation:**

- Add to README.md capabilities
- Update docs/user-guide/mcp-tools.md
- Include usage examples

## Development Tips

### Working with Fixtures

- Store realistic Chef content in `tests/integration/fixtures/sample_cookbook/`
- Include edge cases
- Update when adding new parsing capabilities

### Performance Testing

```python
def test_parse_large_recipe(benchmark):
    """Benchmark parsing performance."""
    result = benchmark(parse_recipe, large_recipe_pathstr())
    assert len(result) > 0
```

### Cross-Platform

- Use `pathlib.Path` for all file operations
- Avoid OS-specific code
- Test on multiple Python versions if possible

## Resources

- [SousChef README](README.md) - Project overview
- [Architecture Guide](docs/ARCHITECTURE.md) - Code organization
- [Security Policy](SECURITY.md) - Security guidelines
- [Code of Conduct](CODE_OF_CONDUCT.md) - Community guidelines

### External Resources

- [Chef Documentation](https://docs.chef.io/)
- [Ansible Documentation](https://docs.ansible.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

## Getting Help

### Where to Ask

- **GitHub Issues**: Bugs, feature requests, questions
- **GitHub Discussions**: Broader discussions
- **PR Comments**: Code-specific questions

### What to Include

- Python version and OS
- SousChef version
- Complete error messages
- Minimal reproduction example
- Expected vs actual behaviour

## Recognition

Contributors are recognized in:

- GitHub contributors list
- Release notes for significant contributions
- README acknowledgments

## Release Process (Maintainers)

SousChef uses automated releases via Release Please:

- **Conventional commits** determine version bumps automatically
- **Releases triggered** when PRs merge to `main`
- **Contributors:** Target `develop` branch with PRs

**Version bumps:**
- `fix:` or `docs:` → patch (5.1.4 → 5.1.5)
- `feat:` → minor (5.1.4 → 5.2.0)
- `feat!:` or `BREAKING CHANGE:` → major (5.1.4 → 6.0.0, after 1.0.0)

## License

By contributing, you agree your contributions will be licensed under the MIT License.

---

**Thank you for contributing!** Every contribution helps make Chef-to-Ansible migrations easier for everyone.
