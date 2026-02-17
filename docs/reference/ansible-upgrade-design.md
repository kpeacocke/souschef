# Ansible Upgrade Feature - Complete Design Reference

## Overview

This document consolidates the complete architectural design, implementation roadmap, and technical specifications for SousChef's Ansible upgrade assessment and planning capabilities.

**Purpose**: Enable users to assess current Ansible environments for upgrade readiness, generate detailed upgrade plans, check EOL status, and validate collection compatibility.

**Architecture**: Follows SousChef's modular structure with new modules for Ansible version management, complementing existing Chef migration capabilities.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Design](#architecture-design)
3. [Version Compatibility Matrix](#version-compatibility-matrix)
4. [Implementation Roadmap](#implementation-roadmap)
5. [Testing Strategy](#testing-strategy)
6. [API Reference](#api-reference)

---

## Executive Summary

### Feature Scope

SousChef now includes **Ansible upgrade assessment and planning** capabilities based on the official Ansible-Python compatibility matrix. This complements existing Chef→Ansible migration features.

### Key Capabilities

1. **Environment Assessment**: Scan Ansible environments for version compatibility, Python requirements, and upgrade readiness
2. **Upgrade Planning**: Generate detailed upgrade plans with intermediate steps, breaking changes, and effort estimates
3. **EOL Checking**: Identify end-of-life versions requiring urgent security updates
4. **Collection Validation**: Verify collection compatibility with target Ansible versions
5. **Multi-Interface Access**: Available via MCP tools (AI assistants), CLI commands, and Web UI

### User Interfaces

| Interface | Use Case | Example |
|-----------|----------|---------|
| **MCP Tools** | AI-assisted workflows via Claude/GitHub Copilot | "Assess my Ansible environment at /opt/ansible" |
| **CLI Commands** | Scripts, automation, CI/CD pipelines | `souschef ansible assess /opt/ansible` |
| **Web UI** | Interactive exploration and planning | Navigate to "Ansible Upgrades" page |

### Implementation Status

- [x] Feature branch created: `feature/ansible-upgrades`
- [x] Complete architectural design
- [x] Version compatibility matrix mapped
- [ ] Core modules implementation (Phase 1)
- [ ] MCP tools and CLI (Phase 2)
- [ ] Web UI (Phase 3)
- [ ] Documentation and testing (Phase 4)

---

## Architecture Design

### Module Structure

Following SousChef's existing architecture patterns:

```
souschef/
├── ansible_upgrade.py              # NEW: Assessment and planning logic
├── server.py                       # ADD: 5 new MCP tools
├── cli.py                          # ADD: ansible command group
├── core/
│   └── ansible_versions.py         # NEW: Version compatibility data
├── parsers/
│   └── ansible_inventory.py        # NEW: Parse Ansible configs
└── ui/pages/
    └── ansible_upgrade.py          # NEW: Web interface
```

### Module Responsibilities

#### `core/ansible_versions.py`

**What it does**: Version compatibility data from the Ansible-Python upgrade matrix

```python
@dataclass
class AnsibleVersion:
    version: str
    release_date: date
    eol_date: Optional[date]
    control_node_python: List[str]      # Control node requirements
    managed_node_python: List[str]       # Managed node requirements
    major_changes: List[str]             # Breaking changes
    min_collection_versions: dict        # Collection requirements
    known_issues: List[str]

ANSIBLE_VERSIONS: Dict[str, AnsibleVersion] = {...}

def get_python_compatibility(ansible_version: str, node_type: str) -> List[str]
def calculate_upgrade_path(current: str, target: str) -> dict
def get_eol_status(version: str) -> dict
```

**Contains**:
- Version compatibility matrices
- EOL date tracking
- Upgrade path algorithms
- Python version requirements

**Does NOT contain**:
- Environment scanning (belongs in parsers/)
- User interaction (belongs in cli.py, ui/)
- Assessment logic (belongs in ansible_upgrade.py)

#### `parsers/ansible_inventory.py`

**What it does**: Parse Ansible configuration files and detect versions

```python
def parse_ansible_cfg(config_path: str) -> dict
def parse_inventory_file(inventory_path: str) -> dict
def detect_ansible_version(ansible_path: str) -> str
def parse_requirements_yml(requirements_path: str) -> dict
def scan_playbook_for_version_issues(playbook_path: str) -> dict
```

**Contains**:
- ansible.cfg parsing
- Inventory parsing (INI/YAML)
- Version detection from environment
- requirements.yml parsing

**Does NOT contain**:
- Version compatibility logic (belongs in core/)
- Upgrade recommendations (belongs in ansible_upgrade.py)

#### `ansible_upgrade.py`

**What it does**: High-level upgrade assessment and planning

```python
def assess_ansible_environment(environment_path: str) -> dict:
    """Assess current Ansible environment for upgrade readiness."""

def generate_upgrade_plan(current_version: str, target_version: str) -> dict:
    """Generate detailed upgrade plan with steps, risks, timeline."""

def validate_collection_compatibility(collections: List[str], target: str) -> dict:
    """Check collection compatibility with target version."""

def generate_upgrade_testing_plan(environment_path: str) -> str:
    """Generate testing plan for upgrade validation."""

def assess_python_upgrade_impact(current: str, target: str, ansible: str) -> dict:
    """Assess Python upgrade impact on Ansible."""
```

**Contains**:
- Environment assessment logic
- Upgrade plan generation
- Compatibility checking
- Risk assessment
- Testing plan generation

**Does NOT contain**:
- Version data (belongs in core/)
- Parsing (belongs in parsers/)
- User interaction (belongs in cli.py, ui/)

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                          │
├─────────────────────────────────────────────────────────────────┤
│  MCP Server          │     CLI Commands      │     Web UI        │
│  (server.py)         │     (cli.py)          │  (ui/pages/)      │
│  - 5 new tools       │  - ansible assess     │  - 4 tabs         │
│                      │  - ansible plan       │                   │
│                      │  - ansible eol        │                   │
│                      │  - ansible validate   │                   │
├─────────────────────────────────────────────────────────────────┤
│                      DOMAIN LOGIC                                │
├─────────────────────────────────────────────────────────────────┤
│                  ansible_upgrade.py                              │
│  - assess_ansible_environment()                                  │
│  - generate_upgrade_plan()                                       │
│  - validate_collection_compatibility()                           │
├─────────────────────────────────────────────────────────────────┤
│                      PARSERS                                     │
├─────────────────────────────────────────────────────────────────┤
│              parsers/ansible_inventory.py                        │
│  - parse_ansible_cfg()                                           │
│  - detect_ansible_version()                                      │
│  - parse_requirements_yml()                                      │
├─────────────────────────────────────────────────────────────────┤
│                      CORE UTILITIES                              │
├─────────────────────────────────────────────────────────────────┤
│              core/ansible_versions.py                            │
│  - ANSIBLE_VERSIONS (compatibility matrix)                       │
│  - get_python_compatibility()                                    │
│  - calculate_upgrade_path()                                      │
│  - get_eol_status()                                              │
└─────────────────────────────────────────────────────────────────┘
```

### MCP Tools (server.py)

Five new tools registered in [server.py](../../souschef/server.py):

```python
@mcp.tool()
def assess_ansible_upgrade_readiness(environment_path: str) -> str:
    """Assess current Ansible environment for upgrade readiness."""

@mcp.tool()
def plan_ansible_upgrade(environment_path: str, target_version: str) -> str:
    """Generate detailed Ansible upgrade plan."""

@mcp.tool()
def check_ansible_eol_status(version: str) -> str:
    """Check if Ansible version is EOL or approaching EOL."""

@mcp.tool()
def validate_ansible_collection_compatibility(collections_file: str, target_version: str) -> str:
    """Validate collection compatibility with target Ansible version."""

@mcp.tool()
def generate_ansible_upgrade_test_plan(environment_path: str) -> str:
    """Generate testing plan for Ansible upgrade validation."""
```

### CLI Commands (cli.py)

New `ansible` command group in [cli.py](../../souschef/cli.py):

```bash
souschef ansible assess <environment_path> [--format json|text]
souschef ansible plan <environment_path> <target_version> [--output file]
souschef ansible eol <version>
souschef ansible validate-collections <requirements.yml> <target_version>
```

### Web UI (ui/pages/ansible_upgrade.py)

Four-tab interface:

1. **Environment Assessment**: Scan directory, display current version, Python compatibility, EOL status, issues
2. **Upgrade Planning**: Select target version, generate plan, view timeline, download report
3. **EOL Status**: Check version EOL status with visual indicators
4. **Collection Compatibility**: Upload requirements.yml, validate against target version

---

## Version Compatibility Matrix

### Data Source

All version data derived from the official **Ansible-Python Upgrade Matrix Cheatsheet**.

### Complete Version Matrix

| Ansible Version | Release Date | EOL Date | Control Node Python | Managed Node Python | Major Changes |
|-----------------|--------------|----------|---------------------|---------------------|---------------|
| **2.9** | 2019-10-31 | 2022-05-23 | 2.7, 3.5-3.8 | 2.6-2.8 | Last version before collections split |
| **2.10** | 2020-09-22 | 2022-05-23 | 3.6-3.9 | 2.6-3.9 | **MAJOR**: Collections split from core |
| **2.11** | 2021-04-26 | 2022-11-07 | 3.6-3.9 | 2.6-3.9 | Improved collection support |
| **2.12** | 2021-11-08 | 2023-05-31 | 3.8-3.10 | 2.6-3.10 | Python 3.8+ required for control node |
| **2.13** | 2022-05-16 | 2023-11-06 | 3.8-3.10 | 2.7-3.10 | Continued collection evolution |
| **2.14** | 2022-11-07 | 2024-05-20 | 3.9-3.11 | 2.7-3.11 | Python 3.9+ required for control node |
| **2.15** | 2023-05-15 | 2024-11-04 | 3.9-3.11 | 2.7-3.11 | Performance improvements |
| **2.16** | 2023-11-06 | *Supported* | 3.10-3.12 | 2.7-3.12 | Python 3.10+ required, latest stable |
| **2.17** | 2024-05-20 | *Supported* | 3.10-3.12 | 3.7-3.12 | Python 2.7 removed from managed nodes |

### Breaking Changes Timeline

#### 2.9 → 2.10 (MAJOR)

**Impact**: Highest complexity upgrade

- Collections split from ansible-core
- `ansible.builtin` namespace introduced
- Module paths changed (e.g., `yum` → `ansible.builtin.yum`)
- Requires explicit collection installation

**Migration effort**: 3-5 days for typical environments

#### 2.11 → 2.12

- Python 3.8+ required for control node
- `ansible-core` package name introduced
- Python 2.6/2.7 deprecated for managed nodes

#### 2.13 → 2.14

- Python 3.9+ required for control node
- Python 3.11 support added

#### 2.15 → 2.16

- Python 3.10+ required for control node
- Python 3.12 support added

#### 2.16 → 2.17

- Python 2.7 removed from managed nodes
- Python 3.7+ required for managed nodes

### Upgrade Path Algorithm

```python
def calculate_upgrade_path(current: str, target: str) -> dict:
    """Calculate safe upgrade path."""

    version_gap = float(target) - float(current)

    # Determine if intermediate versions needed
    if version_gap > 0.2:  # More than 2 minor versions
        # Calculate intermediates for safety
        intermediate_versions = [...]

    # Special handling for 2.9 → 2.10 (collections split)
    if current == "2.9" and float(target) >= 2.10:
        breaking_changes.append("Collections split - major refactoring required")
        effort_days += 3.0

    # Check Python compatibility
    python_upgrade_needed = current_python not in target_python_versions

    # Assess risk
    risk_level = "High" if len(risk_factors) >= 2 else "Medium" if risk_factors else "Low"

    return {
        "from_version": current,
        "to_version": target,
        "direct_upgrade": len(intermediate_versions) == 0,
        "intermediate_versions": intermediate_versions,
        "breaking_changes": breaking_changes,
        "python_upgrade_needed": python_upgrade_needed,
        "risk_level": risk_level,
        "estimated_effort_days": effort_days
    }
```

### EOL Status Checking

```python
def get_eol_status(version: str) -> dict:
    """Check EOL status against matrix."""

    if eol_date < today:
        return {
            "is_eol": True,
            "days_overdue": (today - eol_date).days,
            "status": "End of Life",
            "security_risk": "HIGH",
            "message": "Reached EOL {days} days ago. Upgrade immediately!"
        }
    elif (eol_date - today).days < 90:
        return {
            "is_eol": False,
            "eol_approaching": True,
            "days_remaining": (eol_date - today).days,
            "status": "EOL Approaching",
            "security_risk": "MEDIUM",
            "message": "Will reach EOL in {days} days. Plan upgrade soon."
        }
    else:
        return {
            "is_eol": False,
            "status": "Supported",
            "security_risk": "LOW"
        }
```

---

## Implementation Roadmap

### Phase 1: Core Data & Parsing (Days 1-3)

#### Day 1: Version Compatibility Data

**Create**: `souschef/core/ansible_versions.py`

**Tasks**:
- [ ] Create `AnsibleVersion` dataclass
- [ ] Populate `ANSIBLE_VERSIONS` dict from version matrix
- [ ] Implement `get_python_compatibility()`
- [ ] Implement `calculate_upgrade_path()`
- [ ] Implement `get_eol_status()`
- [ ] Add docstrings referencing version matrix

**Tests**:
- [ ] Unit tests in `tests/unit/test_ansible_versions.py`
  - Test all version data accuracy
  - Test Python compatibility lookups
  - Test upgrade path calculations
  - Test EOL status checks
- [ ] Validate against source matrix

**Acceptance**: All version data accurate, 100% test coverage, zero linting/type errors

#### Day 2: Inventory & Config Parsing

**Create**: `souschef/parsers/ansible_inventory.py`

**Tasks**:
- [ ] Implement `parse_ansible_cfg()`
- [ ] Implement `parse_inventory_file()` (INI & YAML)
- [ ] Implement `detect_ansible_version()`
- [ ] Implement `parse_requirements_yml()`
- [ ] Implement `scan_playbook_for_version_issues()`

**Tests**:
- [ ] Create fixtures in `tests/integration/fixtures/ansible_environments/`
  - Sample ansible.cfg
  - Sample inventories (INI and YAML)
  - Sample requirements.yml
  - Sample playbooks with version-specific syntax
- [ ] Unit tests in `tests/unit/test_ansible_inventory.py`
- [ ] Integration tests in `tests/integration/test_ansible_inventory_integration.py`

**Acceptance**: Can parse all Ansible config formats, 90%+ coverage, all tests pass

#### Day 3: Assessment Logic

**Create**: `souschef/ansible_upgrade.py`

**Tasks**:
- [ ] Implement `assess_ansible_environment()`
- [ ] Implement `generate_upgrade_plan()`
- [ ] Implement `validate_collection_compatibility()`
- [ ] Implement `generate_upgrade_testing_plan()`
- [ ] Implement `assess_python_upgrade_impact()`
- [ ] Add helper functions for output formatting

**Tests**:
- [ ] Unit tests in `tests/unit/test_ansible_upgrade.py`
  - Mock all file operations
  - Test each assessment function
  - Test edge cases (EOL versions, incompatible Python)
- [ ] Integration tests in `tests/integration/test_ansible_upgrade_integration.py`
  - Full environment assessments
  - End-to-end upgrade plan generation

**Acceptance**: Can assess real environments, generate complete plans, 90%+ coverage

**Phase 1 Checklist**:
- [ ] All core modules implemented
- [ ] All tests passing
- [ ] Zero linting errors (`ruff check`)
- [ ] Zero type errors (`mypy souschef`)
- [ ] Code coverage ≥90%
- [ ] Documentation complete

### Phase 2: MCP Tools & CLI (Days 4-5)

#### Day 4: MCP Tools

**Update**: `souschef/server.py`

**Tasks**:
- [ ] Add `assess_ansible_upgrade_readiness()` tool
- [ ] Add `plan_ansible_upgrade()` tool
- [ ] Add `check_ansible_eol_status()` tool
- [ ] Add `validate_ansible_collection_compatibility()` tool
- [ ] Add `generate_ansible_upgrade_test_plan()` tool
- [ ] Add helper functions for formatting MCP responses

**Tests**:
- [ ] Unit tests in `tests/unit/test_server.py`
  - Test each MCP tool
  - Mock underlying functions
  - Verify JSON output format
- [ ] Manual testing with Claude Desktop or GitHub Copilot
  - Test all tools in conversation
  - Verify error handling
  - Test with various inputs

**Acceptance**: All 5 tools working, proper JSON/Markdown output, tests pass, tested in AI assistant

#### Day 5: CLI Commands

**Update**: `souschef/cli.py`

**Tasks**:
- [ ] Create `ansible` command group
- [ ] Implement `ansible assess` command
- [ ] Implement `ansible plan` command
- [ ] Implement `ansible eol` command
- [ ] Implement `ansible validate-collections` command
- [ ] Add output formatting helpers
- [ ] Add progress indicators for long operations

**Tests**:
- [ ] Unit tests in `tests/unit/test_cli.py`
  - Test each command
  - Test output formatting
  - Test error cases
- [ ] Manual CLI testing
  - Test all commands with various inputs
  - Test help text
  - Test error messages

**Acceptance**: All CLI commands working, help text clear, proper formatting, all tests pass

**Phase 2 Checklist**:
- [ ] MCP tools working in AI assistants
- [ ] CLI commands working in terminal
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Example usage documented

### Phase 3: Web UI (Days 6-8)

#### Day 6: UI Page Structure

**Create**: `souschef/ui/pages/ansible_upgrade.py`
**Update**: `souschef/ui/app.py`

**Tasks**:
- [ ] Create `show_ansible_upgrade_page()` main page
- [ ] Create tab structure (Assessment, Planning, EOL, Collections)
- [ ] Add navigation entry in app.py
- [ ] Implement basic layout and styling
- [ ] Add page header and instructions

**Tests**: Manual UI testing (page loads, navigation works, tabs switch)

**Acceptance**: Page accessible, all tabs render, no UI errors

#### Day 7: UI Feature Implementation

**Update**: `souschef/ui/pages/ansible_upgrade.py`

**Tasks**:
- [ ] Implement `show_environment_assessment()` section
  - File/directory picker
  - Assessment trigger button
  - Results display (metrics, charts)
  - Issue highlighting
- [ ] Implement `show_upgrade_planning()` section
  - Version selectors
  - Plan generation
  - Plan display (formatted, downloadable)
  - Timeline visualisation
- [ ] Implement `show_eol_status()` section
  - Version input
  - Status checker
  - Visual indicators (colours, icons)
- [ ] Implement `show_collection_compatibility()` section
  - File uploader
  - Compatibility table
  - Issue highlighting

**Tests**: Manual UI testing (all inputs, buttons, file types, error states, edge cases)

**Acceptance**: All features working end-to-end, UI responsive, error messages clear

#### Day 8: UI Polish & Visualisations

**Update**: `souschef/ui/pages/ansible_upgrade.py`

**Tasks**:
- [ ] Add version timeline visualisation
- [ ] Add upgrade path diagram
- [ ] Add risk assessment charts
- [ ] Add download/export options (PDF, Markdown)
- [ ] Add help text and tooltips
- [ ] Improve error handling and user feedback
- [ ] Add loading indicators
- [ ] Mobile responsiveness check

**Tests**: Manual UI testing on multiple browsers, test all visualisations, test downloads, test different screen sizes

**Acceptance**: Visualisations clear, export working, UI polished, help text comprehensive, mobile-friendly

**Phase 3 Checklist**:
- [ ] Web UI fully functional
- [ ] All features working end-to-end
- [ ] UI tested on multiple browsers
- [ ] Screenshots taken for documentation
- [ ] User guide updated with UI walkthrough

### Phase 4: Documentation & Polish (Days 9-10)

#### Day 9: Documentation

**Create/Update**:
- `docs/user-guide/ansible-upgrades.md`
- `README.md`
- `CONTRIBUTING.md` (if needed)

**Tasks**:
- [ ] Write comprehensive user guide
- [ ] Add MCP tool examples
- [ ] Add CLI command examples
- [ ] Add UI screenshots
- [ ] Update README with new features
- [ ] Add troubleshooting section
- [ ] Add FAQ section

**Acceptance**: All features documented, examples for all tools, screenshots for UI, README updated

#### Day 10: Final Testing & Release Prep

**Tasks**:
- [ ] Run full test suite: `poetry run pytest --cov=souschef` (verify ≥90% coverage)
- [ ] Run quality checks:
  - `poetry run ruff check .`
  - `poetry run ruff format .`
  - `poetry run mypy souschef`
- [ ] Manual end-to-end testing
  - Test complete workflows
  - Test all interfaces (MCP, CLI, UI)
  - Test error cases
- [ ] Performance testing
  - Test with large environments
  - Identify bottlenecks
  - Optimise if needed
- [ ] Security review
  - Check for path traversal issues
  - Validate input sanitisation
  - Review error messages for info leakage
- [ ] Create demo video/GIF
- [ ] Update CHANGELOG.md
- [ ] Prepare release notes

**Acceptance**: All tests passing, code quality gates passing, no security concerns, performance acceptable, documentation complete, ready for merge

**Phase 4 Checklist**:
- [ ] All quality checks passing
- [ ] Documentation complete
- [ ] Demo materials created
- [ ] Ready for code review
- [ ] Ready for merge to develop

### Phase 5: Advanced Features (Optional - Days 11-14)

#### Collection Catalog Integration
- [ ] Integrate with Ansible Galaxy API
- [ ] Cache collection metadata
- [ ] Provide collection update recommendations

#### Automated Testing Script Generation
- [ ] Generate pytest-ansible tests
- [ ] Generate molecule scenarios
- [ ] Generate basic integration tests

#### Rollback Plan Automation
- [ ] Generate rollback playbooks
- [ ] Create snapshot/backup plans
- [ ] Document rollback procedures

#### CI/CD Integration
- [ ] GitHub Actions workflow template
- [ ] GitLab CI template
- [ ] Jenkins pipeline template

#### AWX/AAP Integration
- [ ] AWX upgrade considerations
- [ ] Execution environment updates
- [ ] Project migration plans

---

## Testing Strategy

### Unit Tests

**Location**: `tests/unit/`

**Files**:
- `test_ansible_versions.py` - Version data and compatibility logic
- `test_ansible_inventory.py` - Parsing logic
- `test_ansible_upgrade.py` - Assessment logic
- `test_server.py` - MCP tools (update existing)
- `test_cli.py` - CLI commands (update existing)

**Approach**:
- Mock all file I/O and external dependencies
- Test all functions in isolation
- Cover edge cases (EOL versions, incompatible Python, missing files)
- Validate version matrix accuracy

**Coverage Target**: ≥90%

### Integration Tests

**Location**: `tests/integration/`

**Files**:
- `test_ansible_inventory_integration.py` - Real file parsing
- `test_ansible_upgrade_integration.py` - Full environment assessments

**Fixtures**: `tests/integration/fixtures/ansible_environments/`
- `minimal/` - Basic ansible.cfg, simple inventory
- `complex/` - Multiple playbooks, collections, requirements.yml
- `eol/` - Environment with EOL Ansible 2.9
- `incompatible/` - Version-specific syntax issues

**Approach**:
- Test with real Ansible config files
- Test end-to-end workflows (assess → plan → validate)
- Test with various Ansible versions (2.9, 2.12, 2.16)
- Benchmark performance with `pytest-benchmark`

### Property-Based Tests

**Location**: `tests/unit/test_property_based.py`

**Approach**:
- Use Hypothesis for fuzz testing
- Generate random version strings
- Test that functions never crash with invalid input
- Validate invariants (e.g., EOL date always before today for EOL versions)

**Example**:
```python
from hypothesis import given, settings
from hypothesis import strategies as st

@given(st.text(min_size=1, max_size=10))
@settings(max_examples=50)
def test_eol_status_handles_invalid_versions(version):
    """Test that get_eol_status handles any input gracefully."""
    result = get_eol_status(version)
    assert isinstance(result, dict)  # Should never crash
```

### Manual Testing Checklists

**MCP Tools**:
- [ ] Test in Claude Desktop
- [ ] Test in GitHub Copilot Chat
- [ ] Test with valid environment paths
- [ ] Test with invalid paths
- [ ] Test with various Ansible versions
- [ ] Verify JSON output is parseable

**CLI Commands**:
- [ ] Test all commands with `--help`
- [ ] Test with valid inputs
- [ ] Test with invalid inputs
- [ ] Test output formatting (text and JSON)
- [ ] Test file output (`--output` flag)
- [ ] Test error messages

**Web UI**:
- [ ] Test on Chrome, Firefox, Safari
- [ ] Test all form inputs
- [ ] Test file uploads
- [ ] Test button clicks and workflows
- [ ] Test error states
- [ ] Test mobile responsiveness
- [ ] Test print/export features

---

## API Reference

### Core Module: `core/ansible_versions.py`

#### `AnsibleVersion`

Dataclass representing an Ansible version with compatibility data.

**Attributes**:
- `version` (str): Version number (e.g., "2.16")
- `release_date` (date): Official release date
- `eol_date` (Optional[date]): End-of-life date (None if still supported)
- `control_node_python` (List[str]): Supported Python versions for control node
- `managed_node_python` (List[str]): Supported Python versions for managed nodes
- `major_changes` (List[str]): Breaking changes in this version
- `min_collection_versions` (dict): Minimum collection versions required
- `known_issues` (List[str]): Known problems with this version

#### `get_python_compatibility(ansible_version: str, node_type: str = "control") -> List[str]`

Get compatible Python versions for an Ansible version.

**Parameters**:
- `ansible_version`: Ansible version string (e.g., "2.16")
- `node_type`: "control" or "managed"

**Returns**: List of compatible Python version strings

**Raises**: `ValueError` if version unknown or node_type invalid

**Example**:
```python
versions = get_python_compatibility("2.16", "control")
# Returns: ["3.10", "3.11", "3.12"]
```

#### `calculate_upgrade_path(current_version: str, target_version: str) -> dict`

Calculate safe upgrade path between versions.

**Parameters**:
- `current_version`: Current Ansible version
- `target_version`: Desired target version

**Returns**: Dictionary with upgrade path details:
```python
{
    "from_version": str,
    "to_version": str,
    "direct_upgrade": bool,
    "intermediate_versions": List[str],
    "breaking_changes": List[str],
    "python_upgrade_needed": bool,
    "current_python": List[str],
    "required_python": List[str],
    "risk_level": str,  # "Low", "Medium", "High"
    "risk_factors": List[str],
    "estimated_effort_days": float,
    "collection_updates_needed": dict
}
```

**Example**:
```python
path = calculate_upgrade_path("2.9", "2.16")
# Returns upgrade path with intermediate versions, breaking changes, effort estimate
```

#### `get_eol_status(version: str) -> dict`

Check EOL status of an Ansible version.

**Parameters**:
- `version`: Ansible version string

**Returns**: Dictionary with EOL status:
```python
{
    "version": str,
    "is_eol": bool,
    "eol_date": Optional[date],
    "days_overdue": Optional[int],  # If EOL
    "days_remaining": Optional[int],  # If not EOL
    "status": str,  # "Supported", "EOL Approaching", "End of Life"
    "message": str,
    "security_risk": str  # "LOW", "MEDIUM", "HIGH"
}
```

**Example**:
```python
status = get_eol_status("2.9")
# Returns: {"is_eol": True, "days_overdue": 1356, "security_risk": "HIGH", ...}
```

### Assessment Module: `ansible_upgrade.py`

#### `assess_ansible_environment(environment_path: str) -> dict`

Assess Ansible environment for upgrade readiness.

**Parameters**:
- `environment_path`: Path to Ansible project directory

**Returns**: Assessment results dictionary:
```python
{
    "current_version": str,
    "python_version": str,
    "python_compatible": bool,
    "eol_status": dict,
    "collections": List[dict],
    "playbooks_scanned": int,
    "compatibility_issues": List[str],
    "recommendations": List[str],
    "version_info": AnsibleVersion
}
```

**Raises**: `FileNotFoundError` if path invalid

**Example**:
```python
result = assess_ansible_environment("/opt/ansible")
if result["eol_status"]["is_eol"]:
    print(f"Upgrade required: {result['recommendations']}")
```

#### `generate_upgrade_plan(current_version: str, target_version: str) -> dict`

Generate detailed upgrade plan.

**Parameters**:
- `current_version`: Current Ansible version
- `target_version`: Target Ansible version

**Returns**: Upgrade plan dictionary:
```python
{
    "upgrade_path": dict,  # From calculate_upgrade_path()
    "pre_upgrade_checklist": List[str],
    "upgrade_steps": List[dict],
    "post_upgrade_validation": List[str],
    "rollback_plan": List[str],
    "estimated_downtime_hours": float,
    "risk_assessment": dict,
    "testing_plan": dict
}
```

**Example**:
```python
plan = generate_upgrade_plan("2.9", "2.16")
print(f"Estimated effort: {plan['upgrade_path']['estimated_effort_days']} days")
print(f"Downtime: {plan['estimated_downtime_hours']} hours")
```

#### `validate_collection_compatibility(collections: List[str], target_ansible_version: str) -> dict`

Validate collection compatibility with target version.

**Parameters**:
- `collections`: List of collection names
- `target_ansible_version`: Target Ansible version

**Returns**: Compatibility report:
```python
{
    "target_version": str,
    "collections_checked": int,
    "compatible": int,
    "incompatible": int,
    "unknown": int,
    "details": List[dict]  # Per-collection results
}
```

**Example**:
```python
result = validate_collection_compatibility(
    ["ansible.posix", "community.general"],
    "2.16"
)
```

---

## Example Usage

### MCP Tools (via AI Assistant)

**Scenario 1: Quick Assessment**

```
User: Assess my Ansible environment at /opt/ansible for upgrades.
