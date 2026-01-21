# SousChef Architecture Guide

This document explains the structure of SousChef, where code belongs, and the reasoning behind architectural decisions.

## Quick Navigation

- [Overall Structure](#overall-structure)
- [Module Responsibilities](#module-responsibilities)
- [Where Code Goes](#where-code-goes)
- [Design Patterns](#design-patterns)
- [Adding New Features](#adding-new-features)
- [Common Scenarios](#common-scenarios)

## Overall Structure

```
souschef/
├── __init__.py              # Package initialization
├── server.py                # MCP server entry point & tool registration
├── cli.py                   # Command-line interface
├── assessment.py            # Migration assessment and planning
├── deployment.py            # AWX/AAP integration & deployment strategies
│
├── core/                    # Shared utilities (no business logic)
│   ├── __init__.py
│   ├── constants.py         # Shared constants and configuration
│   ├── errors.py            # Error handling utilities
│   ├── metrics.py           # Effort/timeline metrics calculations
│   ├── path_utils.py        # Path normalization and safety checks
│   ├── ruby_utils.py        # Ruby value parsing and normalization
│   └── validation.py        # General validation utilities
│
├── parsers/                 # Chef artifact parsing (read-only)
│   ├── __init__.py
│   ├── attributes.py        # Parse Chef attributes files
│   ├── habitat.py           # Parse Habitat plan files
│   ├── inspec.py            # Parse InSpec profiles
│   ├── metadata.py          # Parse cookbook metadata.rb
│   ├── recipe.py            # Parse Chef recipes
│   ├── resource.py          # Parse custom resource definitions
│   └── template.py          # Parse ERB templates
│
├── converters/              # Chef to Ansible conversion
│   ├── __init__.py
│   ├── habitat.py           # Habitat → Docker conversion
│   ├── playbook.py          # Recipe → Ansible playbook
│   └── resource.py          # Resource → Ansible task
│
├── ui/                      # Streamlit web interface
│   ├── app.py               # Main dashboard and routing
│   ├── pages/               # Streamlit pages
│   │   ├── ai_settings.py
│   │   ├── cookbook_analysis.py
│   │   └── validation_reports.py
│   └── health_check.py      # Health check endpoint
│
└── filesystem/              # Filesystem operations
    └── operations.py        # Directory/file operations with validation
```

### Top-Level Files

| File | Purpose | When to Edit |
|------|---------|--------------|
| `server.py` | MCP tool registration & entry point | Adding new MCP tools, tool parameter changes |
| `cli.py` | Command-line commands | Adding CLI subcommands, CLI-specific options |
| `assessment.py` | Migration assessment logic | Adding assessment methods, complexity rules |
| `deployment.py` | AWX integration & deployment patterns | Deployment strategies, platform-specific logic |

## Module Responsibilities

### `core/` - Shared Utilities

**Purpose**: No business logic. Only utilities that multiple modules need.

**What Goes Here**:
- Constants and configuration values
- Data validation functions
- Error handling and formatting
- Path utilities with security checks
- Ruby/Chef value parsing
- Metrics calculations

**What Does NOT Go Here**:
- Migration planning logic → `assessment.py`
- Recipe parsing → `parsers/recipe.py`
- Playbook generation → `converters/playbook.py`

**Example**:
```python
# ✅ Belongs in core/
# - Shared constants
# - Path normalization
# - Error formatting
HOURS_PER_WORKDAY = 8  # core/metrics.py
METADATA_FILENAME = "metadata.rb"  # core/constants.py

# ❌ Does NOT belong in core/
# - "assess complexity of this cookbook" logic
# - "convert this recipe to playbook" logic
```

### `parsers/` - Chef Artifact Parsing

**Purpose**: Extract structure from Chef files (read-only, no transformation).

**Principles**:
- Only **read** and **parse** Chef artifacts
- Extract raw data structures without modification
- No domain-specific interpretation
- No conversion to Ansible

**What Goes Here**:
- Recipe resource extraction
- Attribute file parsing
- Metadata parsing
- Template structure analysis
- Custom resource definition parsing

**What Does NOT Go Here**:
- Complexity scoring → `assessment.py`
- Ansible conversion → `converters/`
- Migration planning → `assessment.py`

**Example**:
```python
# ✅ Belongs in parsers/recipe.py
def parse_recipe(recipe_path: str) -> dict:
    """Extract resources from a Chef recipe (parse only)."""
    resources = []
    # Read file, extract resources
    return {"resources": resources}

# ❌ Does NOT belong in parsers/
def assess_recipe_complexity(recipe_path):
    """This is assessment logic, not parsing."""
    # Belongs in assessment.py
```

### `converters/` - Chef to Ansible Transformation

**Purpose**: Convert parsed Chef structures to Ansible format.

**Principles**:
- Takes output from `parsers/` as input
- Produces Ansible-compatible output
- No further parsing of input
- Focused on one transformation type

**Organization**:
- `playbook.py` - Recipe → Playbook conversion
- `resource.py` - Resource → Ansible task conversion
- `habitat.py` - Habitat → Docker conversion

**What Goes Here**:
- Chef resource to Ansible module mapping
- Recipe to playbook generation
- Template conversion (ERB → Jinja2)
- Habitat to Docker/Compose conversion

**What Does NOT Go Here**:
- Parsing Chef files → `parsers/`
- Assessment logic → `assessment.py`
- File I/O → `filesystem/`

**Example**:
```python
# ✅ Belongs in converters/resource.py
def convert_resource_to_task(resource_dict):
    """Convert a parsed Chef resource to Ansible task."""
    return {
        "name": resource_dict["type"],
        "ansible.builtin.debug": {"msg": "..."}
    }

# ❌ Does NOT belong in converters/
def parse_recipe_for_resources():
    """This is parsing, not conversion."""
    # Belongs in parsers/recipe.py
```

### `assessment.py` - Migration Assessment

**Purpose**: High-level migration planning and assessment logic.

**Responsibilities**:
- Analyze cookbook complexity
- Generate migration recommendations
- Create migration roadmaps
- Estimate effort and timeline
- Assess deployment strategies
- Analyze cookbook dependencies

**What Goes Here**:
- Complexity scoring algorithms
- Effort estimation
- Recommendation generation
- Migration planning logic
- Dependency analysis

**What Does NOT Go Here**:
- Parsing Chef files → `parsers/`
- Converting to Ansible → `converters/`
- File operations → `filesystem/`

**Example**:
```python
# ✅ Belongs in assessment.py
def assess_single_cookbook(cookbook_path):
    """Assess complexity and generate recommendations."""
    metrics = count_artifacts(cookbook_path)
    complexity = calculate_complexity(metrics)
    return {
        "complexity": complexity,
        "estimated_effort_days": estimate_effort(complexity)
    }

# Uses parsers to get raw data
# Uses converters to show playbook output
# Does not do the parsing or converting itself
```

### `deployment.py` - AWX/AAP & Deployment

**Purpose**: Deployment strategies, AWX integration, platform-specific logic.

**Responsibilities**:
- AWX/AAP project and credential generation
- Deployment strategy selection (blue-green, canary, rolling)
- Platform-specific configurations
- Deployment risk assessment
- Resource requirement estimation

**What Goes Here**:
- AWX project generation
- Deployment strategy logic
- Platform detection and adaptation
- Resource estimation for deployments

**What Does NOT Go Here**:
- General migration assessment → `assessment.py`
- Recipe parsing → `parsers/`
- Playbook generation → `converters/`

### `server.py` - MCP Tool Registration

**Purpose**: Single entry point for all MCP tools.

**Key Principles**:

1. **Register All Tools Here**
   - Every MCP tool gets `@mcp.tool()` decorator in `server.py`
   - Imports the actual implementation from specialized modules

2. **Keep Tightly-Coupled Tools Together**
   - If multiple tools share significant context, keep in `server.py`
   - Example: databag and environment functions (1,180 lines) share credential handling

3. **Extract When Reusable or Isolatable**
   - If a tool is standalone or reusable, move to appropriate module
   - Example: `assess_single_cookbook` → `assessment.py`

4. **Backward Compatibility Exports**
   - Re-export internal functions for test imports
   - Mark with `# noqa: F401` (intentional unused imports)
   - Don't remove these imports!

**Example**:
```python
# In server.py
@mcp.tool()
def assess_chef_migration_complexity(cookbook_paths: str) -> str:
    """MCP tool wrapper."""
    return _assess_chef_migration_complexity(cookbook_paths)

# Actual implementation in assessment.py
def _assess_chef_migration_complexity(cookbook_paths: str) -> str:
    """Internal implementation."""
    # Logic here
```

### `filesystem/` - Filesystem Operations

**Purpose**: Safe file operations with validation.

**Principles**:
- All file operations go through `filesystem.operations`
- Validates paths to prevent directory traversal
- Handles archive extraction safely
- Consistent error handling

**What Goes Here**:
- Directory/file operations
- Archive extraction and creation
- Path validation
- File permission checks

**What Does NOT Go Here**:
- Path utilities → `core/path_utils.py`
- Application logic → other modules

### `cli.py` - Command-Line Interface

**Purpose**: CLI commands for direct tool invocation.

**Principles**:
- Wraps functions from other modules
- Handles CLI-specific formatting
- Click-based command definitions
- Output formatting for terminals

**Example**:
```python
# ✅ Belongs in cli.py
@cli.command()
@click.argument("cookbook_path", type=str)
def assess_cookbook(cookbook_path):
    """CLI command."""
    from souschef.assessment import assess_single_cookbook
    result = assess_single_cookbook(cookbook_path)
    click.echo(result)
```

### `ui/` - Streamlit Web Interface

**Purpose**: Web-based interface for interactive workflows.

**Organization**:
- `app.py` - Main dashboard and routing
- `pages/` - Individual page components
- `health_check.py` - Health check endpoint

**Principles**:
- Calls functions from core modules
- Handles UI-specific formatting
- Session state management
- Page routing

## Where Code Goes

### Decision Tree

```
I'm adding a new feature. Where does it go?

1. Is it about parsing Chef files?
   YES → parsers/
   NO → go to 2

2. Is it about converting to Ansible?
   YES → converters/
   NO → go to 3

3. Is it about migration assessment/planning?
   YES → assessment.py
   NO → go to 4

4. Is it about deployments/AWX integration?
   YES → deployment.py
   NO → go to 5

5. Is it a shared utility (not business logic)?
   YES → core/
   NO → go to 6

6. Is it a CLI command?
   YES → cli.py
   NO → go to 7

7. Is it a web UI component?
   YES → ui/
   NO → go to 8

8. Is it file operations?
   YES → filesystem/
   NO → go to 9

9. Is it an MCP tool or server config?
   YES → server.py
   NO → Needs new module (discuss first)
```

### Examples

**"I need to parse Chef Berkshelf files"**
1. Create `parsers/berkshelf.py`
2. Implement `parse_berkshelf(file_path) -> dict`
3. Add tests in `tests/test_server.py` (unit) and `tests/test_integration.py`
4. Export from `server.py` if it's an MCP tool

**"I need to score complexity differently"**
1. Update complexity function in `assessment.py`
2. Or create `core/complexity_calculator.py` if it's reusable
3. Update tests in `tests/test_server.py`
4. Update documentation

**"I need to support a new deployment strategy"**
1. Add to `deployment.py`
2. Implement strategy logic
3. Add tests in `tests/test_integration.py`
4. Register MCP tool in `server.py` if user-facing

**"I need a new CLI command"**
1. Add command in `cli.py`
2. Call existing function from appropriate module
3. Add tests in `tests/test_server.py`

## Design Patterns

### Pattern 1: Layered Approach

```
┌─────────────────────────────────┐
│  MCP Server / CLI / Web UI      │  server.py, cli.py, ui/
│  (User Interface)                │
├─────────────────────────────────┤
│  Assessment / Deployment Logic   │  assessment.py, deployment.py
│  (Domain Logic)                  │
├─────────────────────────────────┤
│  Converters                      │  converters/
│  (Transformation)                │
├─────────────────────────────────┤
│  Parsers                         │  parsers/
│  (Data Extraction)               │
├─────────────────────────────────┤
│  Utilities                       │  core/, filesystem/
│  (Shared Infrastructure)         │
└─────────────────────────────────┘
```

**Flow**: UI calls → Domain Logic → Transformers → Parsers → Utilities

### Pattern 2: Separation of Concerns

| Concern | Module(s) | Responsibility |
|---------|-----------|-----------------|
| **Parsing** | `parsers/` | Read and extract |
| **Converting** | `converters/` | Transform format |
| **Assessment** | `assessment.py` | Analyze and plan |
| **Deployment** | `deployment.py` | Execute and monitor |
| **CLI** | `cli.py` | Command handling |
| **Web UI** | `ui/` | Web presentation |
| **Utilities** | `core/`, `filesystem/` | Shared services |

### Pattern 3: Mock Patching

When testing, **patch where functions are used**, not where they're defined.

**Example**:
```python
# Function defined in: souschef/parsers/recipe.py
def parse_recipe(path: str) -> dict:
    ...

# Function used in: souschef/assessment.py
def assess_cookbook(path: str) -> dict:
    recipe_data = parse_recipe(path)  # Uses it here
    ...

# Test in: tests/test_server.py
def test_assess_cookbook():
    with patch("souschef.assessment.parse_recipe") as mock:
        # Patch where it's USED, not where it's defined
        mock.return_value = {"resources": []}
        result = assess_cookbook("/path/to/cookbook")
        assert result["complexity"] == "Low"
```

### Pattern 4: Backward Compatibility

Re-export internal functions from `server.py` for test imports:

```python
# In souschef/assessment.py
def _assess_complexity(path: str) -> str:
    """Internal function."""

# In souschef/server.py
from souschef.assessment import _assess_complexity  # noqa: F401

# In tests/test_server.py
from souschef.server import _assess_complexity
```

**Why?**
- Tests import from single entry point (`server.py`)
- Internal refactoring doesn't break test imports
- `# noqa: F401` suppresses "unused import" warning

## Adding New Features

### Checklist

- [ ] Determined correct module (use decision tree above)
- [ ] Created/updated file in appropriate location
- [ ] Added type hints to all functions
- [ ] Added docstrings (Google style)
- [ ] Wrote unit tests in `tests/test_server.py`
- [ ] Wrote integration tests in `tests/test_integration.py`
- [ ] Added property-based tests if applicable
- [ ] Ran `poetry run ruff check .` and `poetry run ruff format .`
- [ ] Ran `poetry run mypy souschef`
- [ ] Ran `poetry run pytest --cov=souschef`
- [ ] Updated documentation if needed
- [ ] Updated CONTRIBUTING.md if adding new tool type

### Example: Adding Chef Berkshelf Support

**Step 1**: Create the parser
```python
# souschef/parsers/berkshelf.py
def parse_berkshelf(file_path: str) -> dict:
    """Parse Berkshelf file and extract cookbook sources.

    Args:
        file_path: Path to Berkshelf file

    Returns:
        Dictionary with cookbook sources and versions
    """
```

**Step 2**: Create tests
```python
# tests/test_server.py (unit)
def test_parse_berkshelf_success():
    """Test parsing valid Berkshelf file."""
    with patch("souschef.parsers.berkshelf.Path.read_text") as mock:
        mock.return_value = "cookbook 'nginx', '~> 5.0'"
        result = parse_berkshelf("/path/to/Berksfile")
        assert "nginx" in result["sources"]

# tests/test_integration.py (integration)
def test_parse_real_berkshelf_file():
    """Test with actual Berkshelf file."""
    fixture_path = FIXTURES_DIR / "Berksfile"
    result = parse_berkshelf(str(fixture_path))
    assert isinstance(result, dict)
```

**Step 3**: Register MCP tool
```python
# souschef/server.py
@mcp.tool()
def parse_berkshelf_file(file_path: str) -> str:
    """Parse Berkshelf file and list dependencies."""
    from souschef.parsers.berkshelf import parse_berkshelf
    result = parse_berkshelf(file_path)
    return json.dumps(result, indent=2)
```

**Step 4**: Document
- Update README.md with new capability
- Add example to user guide
- Update CONTRIBUTING.md if it's a new parser type

## Common Scenarios

### Scenario 1: "Complexity scoring gives wrong results"

**Where to look**:
1. `assessment.py` - Scoring algorithms
2. `core/metrics.py` - Metric calculations
3. `parsers/` - Data extraction (might be missing something)

**What to check**:
- Unit tests in `tests/test_server.py`
- Integration tests in `tests/test_integration.py`
- Complexity thresholds in `core/constants.py`

### Scenario 2: "Recipe parsing misses a resource type"

**Where to look**:
1. `parsers/recipe.py` - Resource extraction logic
2. `core/constants.py` - Resource type mappings

**What to check**:
- Unit tests for the resource type
- Integration tests with real cookbooks
- Regex patterns for resource detection

### Scenario 3: "Generated playbook is incorrect"

**Where to look**:
1. `converters/playbook.py` - Playbook generation
2. `parsers/recipe.py` - Input data (might be wrong)
3. `converters/resource.py` - Resource conversion

**What to check**:
- Unit tests for each resource type conversion
- Integration tests with various cookbook patterns

### Scenario 4: "CLI command doesn't work"

**Where to look**:
1. `cli.py` - Command definition
2. Underlying module (`assessment.py`, `parsers/`, etc.)
3. `core/` - Utilities and error handling

**What to check**:
- CLI tests in `tests/test_server.py`
- Error handling in underlying module
- Argument validation

### Scenario 5: "Web UI shows wrong data"

**Where to look**:
1. `ui/pages/*.py` - UI component
2. `ui/app.py` - Data flow/state management
3. Underlying module that provides data

**What to check**:
- Session state management
- Data transformation for display
- Underlying data source

## Guidelines for New Modules

If you think you need a **new module**, follow this checklist:

- [ ] Not a "grab-bag" (has clear, cohesive purpose)
- [ ] At least 3-5 related functions
- [ ] Reusable by multiple other modules OR
- [ ] Distinct responsibility that warrants isolation
- [ ] Has associated tests
- [ ] Documented in this architecture guide

**Example Good New Module**: `core/complexity_calculator.py`
- Clear purpose (calculate complexity)
- 3+ functions (score resources, analyze patterns, recommend strategies)
- Reusable by multiple modules
- Testable in isolation

**Example Not-Ready-Yet**: Single utility function
- Too small for its own module
- Should go in appropriate existing module or `core/utils.py`

## Related Documentation

- **CONTRIBUTING.md** - Development workflow and standards
- **Code Standards** - Linting, type hints, docstrings
- **Testing Guide** - Test structure and patterns
- **GitHub Copilot Instructions** - IDE setup and configuration

---

**Questions?** Check CONTRIBUTING.md or open a GitHub discussion!
