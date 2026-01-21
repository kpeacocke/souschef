# Contributing to SousChef

Thank you for your interest in contributing to SousChef! This guide will help you get started with contributing to our Chef-to-Ansible migration platform.

## Table of Contents

- [Understanding the Architecture](#understanding-the-architecture)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Submitting Changes](#submitting-changes)
- [Community](#community)

## Understanding the Architecture

**New to the codebase?** Start here!

The [**ARCHITECTURE.md**](docs/ARCHITECTURE.md) guide explains:
- **What goes where** - Each module's responsibility and what shouldn't go there
- **Module structure** - Visual guide to the project layout
- **Design patterns** - How components interact
- **Decision tree** - Where to add your feature
- **Common scenarios** - Troubleshooting and code locations

**TL;DR**:
- `parsers/` = Extract Chef data
- `converters/` = Transform to Ansible
- `assessment.py` = Migration planning
- `deployment.py` = AWX/deployment logic
- `core/` = Shared utilities
- `server.py` = MCP tool registration
- `cli.py` = Command-line interface
- `ui/` = Web interface

Read the full [ARCHITECTURE.md](docs/ARCHITECTURE.md) before adding new code!

## Getting Started

### Prerequisites

- **Python 3.14+**: SousChef requires Python 3.14 or newer
- **Poetry**: We use Poetry for dependency management
- **Git**: For version control

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/kpeacocke/souschef.git
   cd souschef
   ```

2. **Install Dependencies**
   ```bash
   # Install Poetry if you don't have it
   curl -sSL https://install.python-poetry.org | python3 -

   # Install project dependencies
   poetry install
   ```

3. **Verify Installation**
   ```bash
   # Run tests to ensure everything works
   poetry run pytest

   # Check linting
   poetry run ruff check .

   # Try the CLI
   poetry run souschef-cli --help
   ```

## Contributing Guidelines

### Types of Contributions

We welcome several types of contributions:

####  **Code Contributions**
- New MCP tools for Chef-to-Ansible conversion
- Bug fixes and performance improvements
- CLI enhancements and new commands
- Enhanced parsing for additional Chef constructs

####  **Documentation**
- API documentation improvements
- Usage examples and tutorials
- Migration best practices guides
- README and setup documentation

####  **Testing**
- Unit tests for new features
- Integration tests with real cookbook fixtures
- Property-based tests for edge case coverage
- Performance benchmarks

#### 🐛 **Bug Reports**
- Detailed bug reports with reproduction steps
- Edge case discoveries
- Performance issue identification

####  **Feature Requests**
- New Chef resource type support
- Ansible module mappings
- CLI command suggestions
- Migration workflow improvements

### Before You Contribute

1. **Search Existing Issues**: Check if your idea or bug is already reported
2. **Read Documentation**: Familiarize yourself with the project structure
3. **Understand the Architecture**: Review the MCP server pattern and tool organization
4. **Review Code Standards**: Follow our development standards (below)

## Code Standards

SousChef maintains high code quality standards:

### **Development Tools**

SousChef uses a modern Python toolchain for quality and consistency:

#### **Ruff** (Linting & Formatting)
- **Purpose**: Primary code quality tool - combines linting + formatting
- **Replaces**: Black, isort, flake8, pycodestyle, and many others
- **Usage**:
  ```bash
  poetry run ruff check .     # Lint code
  poetry run ruff format .    # Format code
  ```
- **Config**: See `[tool.ruff]` in `pyproject.toml`
- **VS Code**: Runs automatically on save via the Ruff extension

#### **mypy** (Static Type Checking)
- **Purpose**: Strict type checking for CI/CD and command line
- **Usage**:
  ```bash
  poetry run mypy souschef    # Type check source code
  ```
- **Config**: See `[tool.mypy]` in `pyproject.toml`
- **CI**: Runs automatically in GitHub Actions

#### **Pylance** (VS Code Language Server)
- **Purpose**: Real-time type checking, intellisense, and code navigation in VS Code
- **How it works**: Provides immediate feedback as you type
- **Config**: See `.vscode/settings.json` for Pylance settings
- **Note**: Complements mypy - Pylance for development speed, mypy for CI strictness

#### **pytest** (Testing Framework)
- **Purpose**: Test runner with coverage reporting
- **Usage**:
  ```bash
  poetry run pytest                                      # Run all tests
  poetry run pytest --cov=souschef --cov-report=html    # With coverage
  ```
- **Config**: See `[tool.pytest.ini_options]` in `pyproject.toml`

### **Zero Warnings Policy**
- All code must be free of errors and warnings from **all tools** (Ruff, mypy, Pylance)
- Do not disable linting warnings without fixing the underlying issue
- Ruff handles formatting automatically - use `poetry run ruff format`
- mypy runs in CI for strict type checking - ensure types are correct locally with Pylance

### **Type Hints**
- All function signatures in `souschef/` must have type hints
- Test files can omit type hints for pytest fixtures and parameterized test parameters
- Use Python's built-in types and `typing` module appropriately

### **Documentation**
- Every function, class, and module must have docstrings
- Follow Google-style docstring format
- Include parameter descriptions and return value documentation

### **File Organization**
- Source code in `souschef/`
- Tests in `tests/` mirroring source structure
- Test fixtures in `tests/fixtures/`
- Follow established patterns for new modules

### **Security**
- Validate all file paths to prevent directory traversal
- Sanitize user inputs, especially Chef cookbook content
- Never commit secrets or credentials
- Review security implications of new features

## Testing Requirements

SousChef maintains comprehensive test coverage with three types of tests:

### 1. **Unit Tests** (`tests/test_server.py`)
- Mock-based tests for individual functions
- Test error handling and edge cases
- Fast execution, isolated from filesystem
- Use `unittest.mock` to patch dependencies

Example:
```python
def test_parse_recipe_success():
    """Test that parse_recipe successfully parses a basic recipe."""
    with patch("souschef.server.Path.read_text") as mock_read:
        mock_read.return_value = "package 'nginx'"
        result = parse_recipe("/path/to/recipe.rb")
        assert "Resource 1:" in result
        assert "nginx" in result
```

### 2. **Integration Tests** (`tests/test_integration.py`)
- Real file operations with test fixtures
- Test with actual Chef cookbook files from `tests/fixtures/`
- Use parameterized tests for multiple scenarios
- Include performance benchmarks

Example:
```python
@pytest.mark.parametrize("recipe_file,expected_resources", [
    ("default.rb", ["package", "service"]),
    ("advanced.rb", ["template", "execute"]),
])
def test_parse_real_recipes(recipe_file, expected_resources):
    """Test parsing real Chef recipe files."""
    fixture_path = FIXTURES_DIR / "sample_cookbook" / "recipes" / recipe_file
    result = parse_recipe(str(fixture_path))

    for resource_type in expected_resources:
        assert resource_type in result
```

### 3. **Property-Based Tests** (`tests/test_property_based.py`)
- Use Hypothesis for fuzz testing
- Generate random inputs to find edge cases
- Ensure functions handle any input gracefully
- Limited to 50 examples per test

Example:
```python
from hypothesis import given, settings
from hypothesis import strategies as st

@given(st.text(min_size=1, max_size=100))
@settings(max_examples=50)
def test_parse_handles_any_input(random_input):
    """Test that parsing functions handle any string input."""
    result = parse_recipe_content(random_input)
    assert isinstance(result, str)  # Should never crash
```

### **Test Coverage Goals**
- **Current**: 91% test coverage (913 tests passing)
- **Goal**: 95%+ coverage for production readiness
- **Requirement**: All new features must include comprehensive tests

### **Running Tests**
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=souschef --cov-report=term-missing

# Run specific test types
poetry run pytest tests/test_server.py          # Unit tests
poetry run pytest tests/test_integration.py    # Integration tests
poetry run pytest tests/test_property_based.py # Property-based tests

# Run performance benchmarks
poetry run pytest --benchmark-only
```

## Managing Dependencies

SousChef uses **Poetry** for dependency management with automated lock file synchronization.

### **Adding Dependencies**

```bash
# Add a production dependency
poetry add package-name

# Add a development dependency
poetry add --group dev package-name

# Add with version constraints
poetry add "package-name>=1.0.0,<2.0.0"

# Update a specific package
poetry update package-name

# Update all dependencies
poetry update
```

### **Keeping poetry.lock in Sync**

The project uses **three layers** of automation to prevent lock file issues:

#### **1. Pre-commit Hooks** (Automatic)
- `poetry-check`: Validates lock file is in sync before every commit
- `poetry-lock`: Auto-regenerates lock when pyproject.toml changes
- **Setup**: `poetry run pre-commit install` (one-time setup)

#### **2. GitHub Actions** (CI Validation)
- `poetry-lock-check.yml`: Validates lock file in all PRs
- Posts helpful comments if out of sync
- Prevents merging with outdated lock files

#### **3. Dependabot** (Automated Updates)
- Weekly dependency updates (Mondays 9am UTC)
- Groups minor/patch updates together
- Auto-creates PRs with updated lock files
- Already configured in `.github/dependabot.yml`

### **Manual Lock File Update**

If you manually edit `pyproject.toml`:

```bash
# Update lock file (Poetry 2.x preserves versions automatically)
poetry lock

# Commit both files together
git add pyproject.toml poetry.lock
git commit -m "chore: update dependencies"
```

### **Troubleshooting**

**Error: "poetry.lock out of sync"**
```bash
# Fix it:
poetry lock

# Verify:
poetry check
```

**Pre-commit hook not running?**
```bash
# Install hooks:
poetry run pre-commit install

# Test manually:
poetry run pre-commit run --all-files
```

**Poetry 2.x Changes:**
- `poetry lock` now preserves versions by default (no `--no-update` flag needed)
- Updates lock file hashes without upgrading versions
- Use `poetry update` when you actually want to upgrade packages

## Submitting Changes

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow code standards
   - Add comprehensive tests
   - Update documentation if needed

3. **Test Your Changes**
   ```bash
   # Lint and format
   poetry run ruff check .
   poetry run ruff format .

   # Type check
   poetry run mypy souschef

   # Run all tests
   poetry run pytest

   # Check coverage
   poetry run pytest --cov=souschef --cov-report=term-missing
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add support for Chef custom resources

   - Add parsing for custom resource properties
   - Include action mapping to Ansible modules
   - Add comprehensive test coverage
   - Update documentation"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

   Then create a pull request on GitHub.

### **Commit Message Format**

We use [Conventional Commits](https://www.conventionalcommits.org/) for automated versioning and changelog generation:

**Format**: `<type>(<scope>): <subject>`

**Types**:
- `feat:` - New features (triggers minor version bump)
- `fix:` - Bug fixes (triggers patch version bump)
- `docs:` - Documentation changes only
- `test:` - Test additions or changes
- `refactor:` - Code refactoring without feature changes
- `perf:` - Performance improvements
- `chore:` - Maintenance tasks, dependency updates
- `ci:` - CI/CD configuration changes
- `style:` - Code style/formatting changes

**Breaking Changes**: Add `BREAKING CHANGE:` in the commit body or use `!` after type (triggers major version bump):

```bash
feat!: change MCP tool parameter names

BREAKING CHANGE: Renamed 'path' parameter to 'file_path' for consistency
```

**Examples**:

```bash
# Feature (bumps 0.1.0 → 0.2.0)
feat: add support for Chef Policyfiles

# Bug fix (bumps 0.1.0 → 0.1.1)
fix: handle empty recipe files without crashing

# Documentation (no version bump)
docs: update installation instructions for PyPI

# Breaking change in pre-1.0.0 (bumps 0.1.0 → 0.2.0)
feat!: redesign MCP tool parameter structure

BREAKING CHANGE: All tools now use standardized parameter names

# Note: Breaking changes only bump major version after reaching 1.0.0
# Before 1.0.0, breaking changes bump the minor version (0.x.y → 0.(x+1).0)
# After 1.0.0, breaking changes bump the major version (1.x.y → 2.0.0)
```

**Why Conventional Commits?**
- Automated semantic versioning
- Auto-generated changelogs
- Clear communication of changes
- Standardized git history

### **PR Checklist**

Before submitting your PR, ensure:

- [ ] No linting errors (`poetry run ruff check .`)
- [ ] Properly formatted (`poetry run ruff format .`)
- [ ] No type errors (`poetry run mypy souschef`)
- [ ] All tests pass (`poetry run pytest`)
- [ ] Coverage maintained/improved (`pytest --cov`)
- [ ] Unit tests added/updated in `test_server.py`
- [ ] Integration tests added/updated in `test_integration.py`
- [ ] Property-based tests added if applicable in `test_property_based.py`
- [ ] Test fixtures updated if new parsing features added
- [ ] Type hints are complete
- [ ] Docstrings are present and clear
- [ ] Error cases are handled
- [ ] Cross-platform compatible

## Release Process

SousChef uses automated releases powered by Release Please and follows the Gitflow branching model.

### **Branching Strategy**

- **`main`**: Production releases only (protected)
- **`develop`**: Integration branch for upcoming releases (protected)
- **`feature/*`**: Feature development branches
- **`bugfix/*`**: Bug fix branches
- **`release/*`**: Release preparation branches (if needed)
- **`hotfix/*`**: Emergency production fixes

### **How Releases Work**

1. **Develop Features**
   - Create feature branches from `develop`
   - Use conventional commits for all changes
   - Submit PRs targeting `develop`

2. **Accumulate on Develop**
   - Multiple features/fixes accumulate on `develop`
   - This is your "staging" branch for batching changes
   - Test everything thoroughly on `develop`

3. **Release When Ready**
   - Create PR: `develop` → `main`
   - Once merged, Release Please automatically:
     - Analyzes conventional commits since last release
     - Creates a Release PR with version bump and CHANGELOG
     - Auto-merges the Release PR when CI passes
     - Publishes the release with Git tag
     - Builds and publishes package to PyPI

### **Automated Release Flow**

```
feature/x ──┐
            ├─→ develop ──→ main ──→ [Release Please] ──→ PyPI
feature/y ──┘                         ↓
                                   Release PR
                                   (auto-merges)
```

**Key Points:**
- **Develop is your control point** - merge here to batch changes
- **Main triggers releases** - every merge to main creates a release
- **Fully automatic** - Release PR auto-merges when CI passes
- **Conventional commits required** - they determine version bumps
- **CHANGELOG auto-generated** - from commit messages

### **Version Bumping Rules**

Based on conventional commit types:

- **Patch (0.0.x)**: `fix:`, `docs:`, `test:`, `chore:`, `refactor:`, `style:`
- **Minor (0.x.0)**: `feat:`, breaking changes in pre-1.0 (`feat!:`, `BREAKING CHANGE`)
- **Major (x.0.0)**: Breaking changes after 1.0.0 only

**Example:**
```bash
# These commits on develop...
git commit -m "feat: add Chef Policyfile support"
git commit -m "fix: handle empty attribute files"
git commit -m "docs: update CLI examples"

# ...will create a minor version bump (0.x.0)
# when merged to main because of the feat: commit
```

### **Manual Release Override**

If you need to release immediately without auto-merge:

1. Merge `develop` → `main`
2. Wait for Release Please to create Release PR
3. Review the Release PR (version, CHANGELOG)
4. Manually merge it if auto-merge fails

### **Hotfix Process**

For emergency production fixes:

```bash
# Create hotfix from main
git checkout main
git checkout -b hotfix/critical-bug-fix

# Make fix and commit
git commit -m "fix: resolve critical security issue"

# PR directly to main
# Release happens automatically
```

### **Pre-Release Validation**

Before merging `develop` → `main`:

```bash
# Ensure everything passes
poetry run ruff check .
poetry run ruff format .
poetry run mypy souschef
poetry run pytest --cov=souschef
poetry run pytest --benchmark-only

# Review accumulated commits
git log main..develop --oneline

# Verify conventional commits
git log main..develop --pretty=format:"%s" | grep -E "^(feat|fix|docs|test|refactor|perf|chore|ci|style)(\(.*\))?:"
```

## Adding New MCP Tools

When adding new MCP tools to SousChef:

### 1. **Tool Implementation**
```python
@mcp.tool()
def your_new_tool(parameter: str) -> str:
    """Brief description of what this tool does.

    Args:
        parameter: Description of the parameter.

    Returns:
        Description of return value.

    Raises:
        ValueError: When parameter is invalid.
    """
    try:
        # Implementation
        return result
    except Exception as e:
        return f"Error: {e}"
```

### 2. **Add to CLI** (if appropriate)
```python
@cli.command()
@click.argument("parameter", type=str)
def your_command(parameter: str) -> None:
    """CLI command description."""
    result = your_new_tool(parameter)
    click.echo(result)
```

### 3. **Comprehensive Testing**
- Unit tests with mocks
- Integration tests with fixtures
- Property-based tests for robustness
- Error case coverage

### 4. **Documentation Updates**
- Add tool to README.md
- Update CLI documentation if applicable
- Include usage examples

## Development Tips

### **Working with Chef Cookbook Fixtures**
- Add realistic Chef content to `tests/fixtures/sample_cookbook/`
- Include edge cases and complex scenarios
- Update fixtures when adding new parsing capabilities

### **Debugging MCP Tools**
```python
# Add logging for development
import logging
logging.basicConfig(level=logging.DEBUG)

# Test tools directly
from souschef.server import your_tool
result = your_tool("/path/to/test/file")
print(result)
```

### **Performance Considerations**
- Large cookbooks can be several MB
- Include benchmarks for parsing functions
- Consider memory usage with large files
- Test with realistic cookbook sizes

### **Cross-Platform Compatibility**
- Use `pathlib.Path` for file operations
- Avoid OS-specific code
- Test on multiple Python versions if possible

## Security Scanning

### **Automatic CodeQL Scanning (GitHub Actions)**

CodeQL security scanning runs automatically - already set up in `.github/workflows/codeql.yml`:
- Runs on push to main/develop/release/hotfix branches
- Runs on all pull requests
- Weekly scheduled scans (Mondays 6am UTC)
- Results appear in Security → Code scanning alerts

**No action needed** - this runs automatically on every PR and push!

### **Local CodeQL Scanning (VS Code Extension)**

The devcontainer automatically installs CodeQL CLI when supported. **Works on x86_64 Linux, Windows, and macOS (Intel/Apple Silicon).**

#### ARM64 Linux Limitation

**CodeQL CLI does not officially support ARM64 Linux.** If you're developing on ARM64 (e.g., Raspberry Pi, AWS Graviton, Oracle Cloud ARM):

- **GitHub Actions still work** - automated scanning continues on every push/PR
- **CI/CD is unaffected** - all security checks run in GitHub's infrastructure
- **Local VS Code extension won't work** - CLI can't run natively on ARM64 Linux

**Alternatives for ARM64 users:**
1. Rely on GitHub Actions for all CodeQL scanning (already configured)
2. Run the devcontainer on x86_64 hardware
3. Use [GitHub Codespaces](https://github.com/features/codespaces) (runs on x86_64)

#### Installation (x86_64 only)

**The CodeQL extension is not pre-installed due to ARM64 compatibility.** x86_64 users can install it manually:

1. **Verify your architecture:**
   ```bash
   uname -m  # Should show x86_64 for compatibility
   ```

2. **Install the extension:**
   - Press `Ctrl+Shift+P` and type "Extensions: Install Extensions"
   - Search for "CodeQL"
   - Install "CodeQL" by GitHub
   - Restart VS Code if prompted

3. **Configure the CLI path:**
   - Open Settings (`Ctrl+,`)
   - Search for "codeql cli"
   - Set **CodeQL: Cli: Executable Path** to: `${userHome}/.codeql/codeql/codeql`
   - Reload VS Code

#### Using CodeQL in VS Code

**Quick Analysis (Easiest):**
1. Open any Python file in `souschef/`
2. Right-click anywhere in the file
3. Select **"CodeQL: Run Queries in Selected Files"**
4. Results appear in the CodeQL view panel

**Full Database Analysis:**
1. Open Command Palette (`Ctrl+Shift+P`)
2. Type "CodeQL: Create Database from Folder"
3. Select the workspace root
4. Once created, run security queries against it

**View Results:**
- Click the CodeQL icon in the sidebar
- See all findings with highlighted code snippets
- Click any result to jump directly to the vulnerable code
- Filter by severity (Error, Warning, Note)

#### What CodeQL Checks

The same security queries as GitHub Actions:
- SQL injection
- Command injection
- Path traversal
- Code injection
- Hardcoded credentials
- Information exposure
- 100+ more security patterns

#### Tips

- **First run takes 2-3 minutes** to build the database
- **Subsequent runs are instant** - database is cached
- **Run before pushing** to catch issues early
- **Explore queries** - right-click results to see query source code

## Resources

### **Learning Resources**
- [Chef Documentation](https://docs.chef.io/)
- [Ansible Documentation](https://docs.ansible.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Python Type Hints Guide](https://docs.python.org/3/library/typing.html)
- [CodeQL for VS Code Guide](https://codeql.github.com/docs/codeql-for-visual-studio-code/)

### **Project-Specific Resources**
- [SousChef README](README.md) - Complete project documentation
- [GitHub Copilot Instructions](.github/copilot-instructions.md) - Development guidelines
- [Security Policy](SECURITY.md) - Security guidelines
- [Code of Conduct](CODE_OF_CONDUCT.md) - Community guidelines

## Getting Help

### **Where to Ask Questions**
- **GitHub Issues**: For bugs, feature requests, and general questions
- **GitHub Discussions**: For broader community discussions
- **Pull Request Comments**: For code-specific questions

### **What Information to Include**
- Python version and operating system
- SousChef version
- Complete error messages
- Minimal reproduction example
- What you expected vs. what happened

## Recognition

Contributors are recognized in:
- GitHub contributors list
- Release notes for significant contributions
- README acknowledgments section (coming soon)

## License

By contributing to SousChef, you agree that your contributions will be licensed under the MIT License.

---

**Happy Contributing!**

We're excited to have you as part of the SousChef community. Every contribution, no matter how small, helps make infrastructure migrations easier for everyone.
