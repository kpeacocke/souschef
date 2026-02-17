# Ansible Upgrade Integration Design

## Overview

This document outlines the integration of Ansible upgrade assessment and planning capabilities into SousChef, complementing the existing Chef-to-Ansible migration functionality.

## Key Concepts from Upgrade Matrix

Based on the Ansible-Python upgrade matrix, the tool needs to handle:

1. **Version Compatibility**: Ansible Core versions vs Python versions
2. **EOL Tracking**: End-of-life dates for Ansible and Python versions
3. **Upgrade Paths**: Safe migration paths between versions
4. **Breaking Changes**: Major changes between versions (e.g., 2.9 → 2.10 collections split)
5. **Control Node vs Managed Node**: Different requirements for controller and targets
6. **Collection Dependencies**: Updated collection version requirements

## Architecture Integration

Following the existing SousChef architecture patterns:

```
souschef/
├── ansible_upgrade.py       # NEW: Core upgrade assessment logic
├── server.py                # ADD: New MCP tools for upgrades
├── cli.py                   # ADD: New CLI commands for upgrades
├── ui/
│   └── pages/
│       └── ansible_upgrade.py  # NEW: Web UI for upgrade planning
├── core/
│   └── ansible_versions.py  # NEW: Version compatibility data
└── parsers/
    └── ansible_inventory.py # NEW: Parse existing Ansible environments
```

## Module Responsibilities

### 1. `souschef/core/ansible_versions.py` (NEW)

**Purpose**: Version compatibility data and utilities

```python
"""Ansible and Python version compatibility data."""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

@dataclass
class AnsibleVersion:
    """Ansible version information."""
    version: str
    release_date: date
    eol_date: Optional[date]
    python_versions: List[str]  # Supported Python versions
    control_node_python: List[str]  # Control node requirements
    managed_node_python: List[str]  # Managed node requirements
    major_changes: List[str]  # Breaking changes

@dataclass
class UpgradePath:
    """Represents a safe upgrade path."""
    from_version: str
    to_version: str
    intermediate_versions: List[str]  # If direct upgrade not recommended
    breaking_changes: List[str]
    required_actions: List[str]
    estimated_effort_days: float
    risk_level: str  # "Low", "Medium", "High"

# Version compatibility matrix
ANSIBLE_VERSIONS: Dict[str, AnsibleVersion] = {
    "2.9": AnsibleVersion(...),
    "2.10": AnsibleVersion(...),
    "2.11": AnsibleVersion(...),
    # ... etc
}

def get_python_compatibility(ansible_version: str) -> List[str]:
    """Get compatible Python versions for Ansible version."""

def calculate_upgrade_path(
    current_version: str,
    target_version: str
) -> UpgradePath:
    """Calculate safe upgrade path between versions."""

def get_eol_status(version: str) -> dict:
    """Check if version is EOL or approaching EOL."""
```

**What Goes Here**:
- Version compatibility matrices
- EOL date tracking
- Upgrade path calculation algorithms
- Version comparison utilities

**What Does NOT Go Here**:
- Environment scanning (parsers/)
- Playbook analysis (ansible_upgrade.py)
- User interaction (cli.py, ui/)

### 2. `souschef/parsers/ansible_inventory.py` (NEW)

**Purpose**: Parse existing Ansible environments and inventory

```python
"""Parse Ansible inventory and configuration files."""

def parse_ansible_cfg(config_path: str) -> dict:
    """Parse ansible.cfg file."""

def parse_inventory_file(inventory_path: str) -> dict:
    """Parse Ansible inventory (INI or YAML)."""

def detect_ansible_version(ansible_path: str) -> str:
    """Detect installed Ansible version from environment."""

def parse_requirements_yml(requirements_path: str) -> dict:
    """Parse collections/roles requirements.yml."""

def scan_playbook_for_version_issues(playbook_path: str) -> dict:
    """Scan playbook for version-specific syntax."""
```

**What Goes Here**:
- Configuration file parsing
- Inventory parsing (INI/YAML)
- Version detection from environment
- Requirements file parsing

**What Does NOT Go Here**:
- Upgrade recommendations (ansible_upgrade.py)
- Version compatibility logic (core/ansible_versions.py)
- User interaction (cli.py, ui/)

### 3. `souschef/ansible_upgrade.py` (NEW)

**Purpose**: High-level upgrade assessment and planning

```python
"""Ansible upgrade assessment and planning."""

def assess_ansible_environment(environment_path: str) -> dict:
    """Assess current Ansible environment for upgrade readiness.

    Returns:
        {
            "current_version": "2.9.27",
            "python_version": "3.8.10",
            "eol_status": {"is_eol": True, "eol_date": "2022-05-23"},
            "collections": [...],
            "playbooks_scanned": 45,
            "compatibility_issues": [...],
            "recommendations": [...]
        }
    """

def generate_upgrade_plan(
    current_version: str,
    target_version: str
) -> dict:
    """Generate detailed upgrade plan.

    Returns:
        {
            "upgrade_path": UpgradePath,
            "pre_upgrade_checklist": [...],
            "upgrade_steps": [...],
            "post_upgrade_validation": [...],
            "rollback_plan": [...],
            "estimated_downtime_hours": 2.5,
            "risk_assessment": {...}
        }
    """

def validate_collection_compatibility(
    collections: List[str],
    target_ansible_version: str
) -> dict:
    """Check if collections are compatible with target version."""

def generate_upgrade_testing_plan(environment_path: str) -> str:
    """Generate testing plan for upgrade validation."""

def assess_python_upgrade_impact(
    current_python: str,
    target_python: str,
    ansible_version: str
) -> dict:
    """Assess impact of Python version upgrade on Ansible."""
```

**What Goes Here**:
- Environment assessment logic
- Upgrade plan generation
- Compatibility checking
- Risk assessment
- Testing plan generation

**What Does NOT Go Here**:
- Version data (core/ansible_versions.py)
- Parsing (parsers/ansible_inventory.py)
- User interaction (cli.py, ui/)
- Deployment automation (deployment.py)

### 4. `souschef/server.py` (Updates)

Add new MCP tools:

```python
@mcp.tool()
def assess_ansible_upgrade_readiness(environment_path: str) -> str:
    """Assess current Ansible environment for upgrade readiness.

    Args:
        environment_path: Path to Ansible environment directory

    Returns:
        JSON string with assessment results
    """
    from souschef.ansible_upgrade import assess_ansible_environment
    result = assess_ansible_environment(environment_path)
    return json.dumps(result, indent=2, default=str)

@mcp.tool()
def plan_ansible_upgrade(
    environment_path: str,
    target_version: str
) -> str:
    """Generate detailed Ansible upgrade plan.

    Args:
        environment_path: Path to Ansible environment
        target_version: Target Ansible version (e.g., "2.16")

    Returns:
        Markdown-formatted upgrade plan
    """
    from souschef.ansible_upgrade import generate_upgrade_plan
    from souschef.parsers.ansible_inventory import detect_ansible_version

    current_version = detect_ansible_version(environment_path)
    plan = generate_upgrade_plan(current_version, target_version)
    return format_upgrade_plan_markdown(plan)

@mcp.tool()
def check_ansible_eol_status(version: str) -> str:
    """Check if Ansible version is EOL or approaching EOL.

    Args:
        version: Ansible version string (e.g., "2.9")

    Returns:
        JSON string with EOL status and recommendations
    """
    from souschef.core.ansible_versions import get_eol_status
    status = get_eol_status(version)
    return json.dumps(status, indent=2, default=str)

@mcp.tool()
def validate_ansible_collection_compatibility(
    collections_file: str,
    target_version: str
) -> str:
    """Validate collection compatibility with target Ansible version.

    Args:
        collections_file: Path to requirements.yml
        target_version: Target Ansible version

    Returns:
        JSON string with compatibility report
    """
    from souschef.ansible_upgrade import validate_collection_compatibility
    from souschef.parsers.ansible_inventory import parse_requirements_yml

    collections = parse_requirements_yml(collections_file)
    result = validate_collection_compatibility(collections, target_version)
    return json.dumps(result, indent=2)

@mcp.tool()
def generate_ansible_upgrade_test_plan(environment_path: str) -> str:
    """Generate testing plan for Ansible upgrade validation.

    Args:
        environment_path: Path to Ansible environment

    Returns:
        Markdown-formatted testing plan
    """
    from souschef.ansible_upgrade import generate_upgrade_testing_plan
    return generate_upgrade_testing_plan(environment_path)
```

### 5. `souschef/cli.py` (Updates)

Add new CLI commands:

```python
@cli.group()
def ansible():
    """Ansible upgrade and management commands."""
    pass

@ansible.command()
@click.argument("environment_path", type=click.Path(exists=True))
@click.option("--format", type=click.Choice(["json", "text"]), default="text")
def assess(environment_path: str, format: str):
    """Assess Ansible environment for upgrade readiness."""
    from souschef.ansible_upgrade import assess_ansible_environment

    result = assess_ansible_environment(environment_path)

    if format == "json":
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        # Pretty print text format
        display_assessment_text(result)

@ansible.command()
@click.argument("environment_path", type=click.Path(exists=True))
@click.argument("target_version")
@click.option("--output", "-o", type=click.Path(), help="Save plan to file")
def plan(environment_path: str, target_version: str, output: str):
    """Generate Ansible upgrade plan."""
    from souschef.ansible_upgrade import generate_upgrade_plan
    from souschef.parsers.ansible_inventory import detect_ansible_version

    current = detect_ansible_version(environment_path)
    plan = generate_upgrade_plan(current, target_version)

    markdown = format_upgrade_plan_markdown(plan)

    if output:
        Path(output).write_text(markdown)
        click.echo(f"Plan saved to {output}")
    else:
        click.echo(markdown)

@ansible.command()
@click.argument("version")
def eol(version: str):
    """Check EOL status of Ansible version."""
    from souschef.core.ansible_versions import get_eol_status

    status = get_eol_status(version)
    display_eol_status(status)

@ansible.command()
@click.argument("collections_file", type=click.Path(exists=True))
@click.argument("target_version")
def validate_collections(collections_file: str, target_version: str):
    """Validate collection compatibility with Ansible version."""
    from souschef.ansible_upgrade import validate_collection_compatibility
    from souschef.parsers.ansible_inventory import parse_requirements_yml

    collections = parse_requirements_yml(collections_file)
    result = validate_collection_compatibility(collections, target_version)
    display_compatibility_results(result)
```

### 6. `souschef/ui/pages/ansible_upgrade.py` (NEW)

Web UI for upgrade planning:

```python
"""Streamlit page for Ansible upgrade planning."""

import streamlit as st
from pathlib import Path

def show_ansible_upgrade_page():
    """Display Ansible upgrade planning page."""
    st.title("[SYNC] Ansible Upgrade Planning")

    # Tabs for different workflows
    tab1, tab2, tab3, tab4 = st.tabs([
        "Environment Assessment",
        "Upgrade Planning",
        "EOL Status",
        "Collection Compatibility"
    ])

    with tab1:
        show_environment_assessment()

    with tab2:
        show_upgrade_planning()

    with tab3:
        show_eol_status()

    with tab4:
        show_collection_compatibility()

def show_environment_assessment():
    """Show environment assessment section."""
    st.header("Assess Current Environment")

    environment_path = st.text_input(
        "Ansible Environment Path",
        placeholder="/path/to/ansible/project"
    )

    if st.button("Assess Environment"):
        with st.spinner("Scanning environment..."):
            from souschef.ansible_upgrade import assess_ansible_environment
            result = assess_ansible_environment(environment_path)

            # Display results
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Current Version", result["current_version"])
            with col2:
                st.metric("Python Version", result["python_version"])
            with col3:
                eol = result["eol_status"]
                st.metric(
                    "EOL Status",
                    "WARNING EOL" if eol["is_eol"] else "[YES] Supported",
                    delta="Action Required" if eol["is_eol"] else None
                )

            # Show issues
            if result["compatibility_issues"]:
                st.error("WARNING Compatibility Issues Found")
                for issue in result["compatibility_issues"]:
                    st.warning(issue)

            # Recommendations
            st.subheader("Recommendations")
            for rec in result["recommendations"]:
                st.info(rec)

def show_upgrade_planning():
    """Show upgrade planning section."""
    st.header("Generate Upgrade Plan")

    col1, col2 = st.columns(2)
    with col1:
        environment_path = st.text_input("Environment Path")
        current_version = st.text_input("Current Version (auto-detected)")
    with col2:
        target_version = st.selectbox(
            "Target Version",
            ["2.16", "2.15", "2.14", "2.13", "2.12"]
        )

    if st.button("Generate Plan"):
        # Generate and display plan
        pass

def show_eol_status():
    """Show EOL status checker."""
    st.header("Check Version EOL Status")

    version = st.text_input("Ansible Version", placeholder="2.9")

    if st.button("Check Status"):
        from souschef.core.ansible_versions import get_eol_status
        status = get_eol_status(version)

        # Display status with visual indicators
        if status["is_eol"]:
            st.error(f"WARNING Version {version} reached EOL on {status['eol_date']}")
        elif status.get("eol_approaching"):
            st.warning(f"[URGENT] Version {version} will reach EOL on {status['eol_date']}")
        else:
            st.success(f"[YES] Version {version} is supported until {status['eol_date']}")

def show_collection_compatibility():
    """Show collection compatibility checker."""
    st.header("Validate Collection Compatibility")

    collections_file = st.file_uploader(
        "Upload requirements.yml",
        type=["yml", "yaml"]
    )
    target_version = st.selectbox(
        "Target Ansible Version",
        ["2.16", "2.15", "2.14"]
    )

    if collections_file and st.button("Validate"):
        # Parse and validate
        pass
```

Update `souschef/ui/app.py` to add navigation:

```python
# Add to navigation
NAV_ANSIBLE_UPGRADE = "Ansible Upgrades"

# In main navigation
if page == NAV_ANSIBLE_UPGRADE:
    from souschef.ui.pages.ansible_upgrade import show_ansible_upgrade_page
    show_ansible_upgrade_page()
```

## Data Model

Key data structures:

```python
# Assessment Result
{
    "current_version": "2.9.27",
    "python_version": "3.8.10",
    "eol_status": {
        "is_eol": True,
        "eol_date": "2022-05-23",
        "days_overdue": 1356
    },
    "control_node": {
        "os": "Ubuntu 20.04",
        "python_compatible": True,
        "collections": [...]
    },
    "managed_nodes": {
        "python_versions": ["3.6", "3.8", "3.9"],
        "total_hosts": 45,
        "incompatible_hosts": []
    },
    "compatibility_issues": [
        "Collection ansible.posix requires Ansible >=2.11",
        "Using deprecated module syntax in 3 playbooks"
    ],
    "recommendations": [
        "Upgrade to Ansible 2.16 (latest stable)",
        "Update Python to 3.11 on control node",
        "Review and update 3 playbooks with deprecated syntax"
    ]
}

# Upgrade Plan
{
    "upgrade_path": {
        "from_version": "2.9.27",
        "to_version": "2.16.0",
        "direct_upgrade": False,
        "intermediate_versions": ["2.10", "2.15"],
        "breaking_changes": [
            "2.9 → 2.10: Collections split",
            "2.10 → 2.15: Module namespace changes"
        ],
        "estimated_effort_days": 5.5,
        "risk_level": "Medium"
    },
    "pre_upgrade_checklist": [...],
    "upgrade_steps": [...],
    "testing_plan": {...},
    "rollback_plan": {...}
}
```

## Implementation Phases

### Phase 1: Core Functionality (Week 1)
- [ ] Create `core/ansible_versions.py` with compatibility data
- [ ] Create `parsers/ansible_inventory.py` with basic parsing
- [ ] Create `ansible_upgrade.py` with assessment logic
- [ ] Add unit tests for all modules
- [ ] Add integration tests with fixtures

### Phase 2: MCP & CLI (Week 2)
- [ ] Add MCP tools to `server.py`
- [ ] Add CLI commands to `cli.py`
- [ ] Test MCP tools with Claude Desktop
- [ ] Test CLI commands
- [ ] Update documentation

### Phase 3: Web UI (Week 3)
- [ ] Create `ui/pages/ansible_upgrade.py`
- [ ] Add navigation to `ui/app.py`
- [ ] Implement all UI sections
- [ ] Add visualizations (version timeline, upgrade paths)
- [ ] User acceptance testing

### Phase 4: Advanced Features (Week 4)
- [ ] Collection catalog integration
- [ ] Automated testing script generation
- [ ] Rollback plan automation
- [ ] Integration with CI/CD pipelines
- [ ] Best practices documentation

## Testing Strategy

1. **Unit Tests**: `tests/unit/test_ansible_upgrade.py`
   - Version compatibility logic
   - Upgrade path calculation
   - EOL date checking

2. **Integration Tests**: `tests/integration/test_ansible_upgrade_integration.py`
   - Full environment scanning
   - Plan generation with real fixtures
   - Collection compatibility checking

3. **Fixtures**: `tests/integration/fixtures/ansible_environments/`
   - Sample ansible.cfg files
   - Sample inventory files
   - Sample requirements.yml files
   - Various version scenarios

## Benefits

1. **Unified Tool**: Single tool for Chef→Ansible migration AND Ansible upgrades
2. **Risk Mitigation**: Assess compatibility before upgrading
3. **Planning**: Detailed upgrade plans with effort estimates
4. **Multiple Interfaces**: MCP, CLI, and Web UI
5. **Extensible**: Easy to add new versions and compatibility data

## Example Usage

### MCP (via Claude Desktop)
```
User: "Assess my Ansible environment at /opt/ansible for upgrades"
Claude: [calls assess_ansible_upgrade_readiness tool]
Returns: Current version, EOL status, compatibility issues, recommendations

User: "Create an upgrade plan to Ansible 2.16"
Claude: [calls plan_ansible_upgrade tool]
Returns: Detailed upgrade plan with steps, risks, and timeline
```

### CLI
```bash
# Assess environment
souschef ansible assess /opt/ansible

# Generate upgrade plan
souschef ansible plan /opt/ansible 2.16 -o upgrade_plan.md

# Check EOL status
souschef ansible eol 2.9

# Validate collections
souschef ansible validate-collections requirements.yml 2.16
```

### Web UI
1. Navigate to "Ansible Upgrades" page
2. Enter environment path
3. Click "Assess Environment"
4. Review results and click "Generate Upgrade Plan"
5. Download plan or export to various formats

## Questions for Discussion

1. **Python Version Tracking**: Should we also track Python's EOL and compatibility separately?
2. **Collection Catalog**: Should we maintain a catalog of popular collections and their version requirements?
3. **Automated Testing**: Should we generate actual test scripts or just test plans?
4. **CI/CD Integration**: Priority for GitHub Actions/GitLab CI/Jenkins integration?
5. **AWX/AAP Integration**: Should upgrade plans include AWX/AAP considerations?

## Next Steps

1. Review this design document
2. Prioritize features (MVP vs nice-to-have)
3. Create feature branch (already done: `feature/ansible-upgrades`)
4. Implement Phase 1 (core functionality)
5. Iterate based on feedback
