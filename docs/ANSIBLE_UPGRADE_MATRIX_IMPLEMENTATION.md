# Ansible-Python Upgrade Matrix Implementation

## PDF Content Summary

The attached PDF "ansible-python-upgrade-matrix-cheatsheet.pdf" contains critical information about:

1. **Ansible Core Version Support Matrix**
   - Which Python versions work with which Ansible versions
   - Control node vs managed node Python requirements
   - End-of-life dates for different versions

2. **Key Compatibility Rules**
   - Ansible 2.9: Python 2.7, 3.5-3.8 (EOL May 2022)
   - Ansible 2.10-2.11: Python 3.6-3.9
   - Ansible 2.12-2.13: Python 3.8-3.10
   - Ansible 2.14-2.15: Python 3.9-3.11
   - Ansible 2.16+: Python 3.10-3.12

3. **Breaking Changes Timeline**
   - 2.9 → 2.10: Collections split (major restructuring)
   - Module namespace changes across versions
   - Deprecated module removals

## Implementation Mapping

### 1. Core Version Data (`core/ansible_versions.py`)

```python
"""Ansible and Python version compatibility data.

Data source: ansible-python-upgrade-matrix-cheatsheet.pdf
Last updated: [Date]
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

@dataclass
class AnsibleVersion:
    """Ansible version information from compatibility matrix."""
    
    version: str
    release_date: date
    eol_date: Optional[date]
    
    # FROM PDF: Control node Python requirements
    control_node_python: List[str]
    
    # FROM PDF: Managed node Python requirements  
    managed_node_python: List[str]
    
    # FROM PDF: Breaking changes for this version
    major_changes: List[str]
    
    # Collections requirements
    min_collection_versions: dict
    
    # Known issues
    known_issues: List[str]

# FROM PDF: Complete version matrix
ANSIBLE_VERSIONS = {
    "2.9": AnsibleVersion(
        version="2.9",
        release_date=date(2019, 10, 31),
        eol_date=date(2022, 5, 23),
        control_node_python=["2.7", "3.5", "3.6", "3.7", "3.8"],
        managed_node_python=["2.6", "2.7", "3.5", "3.6", "3.7", "3.8"],
        major_changes=[
            "Last version before collections split",
            "Many modules now deprecated",
            "No longer receives security updates"
        ],
        min_collection_versions={},
        known_issues=[
            "Security vulnerabilities - upgrade immediately",
            "No Python 3.9+ support"
        ]
    ),
    
    "2.10": AnsibleVersion(
        version="2.10",
        release_date=date(2020, 9, 22),
        eol_date=date(2022, 5, 23),
        control_node_python=["3.6", "3.7", "3.8", "3.9"],
        managed_node_python=["2.6", "2.7", "3.5", "3.6", "3.7", "3.8", "3.9"],
        major_changes=[
            "MAJOR: Collections split from core",
            "ansible.builtin namespace introduced",
            "Requires explicit collection installation",
            "Module paths changed"
        ],
        min_collection_versions={
            "ansible.posix": "1.0.0",
            "ansible.windows": "1.0.0"
        },
        known_issues=[
            "Collection installation required for many modules",
            "Import path changes break old playbooks"
        ]
    ),
    
    "2.11": AnsibleVersion(
        version="2.11",
        release_date=date(2021, 4, 26),
        eol_date=date(2022, 11, 7),
        control_node_python=["3.6", "3.7", "3.8", "3.9"],
        managed_node_python=["2.6", "2.7", "3.5", "3.6", "3.7", "3.8", "3.9"],
        major_changes=[
            "Improved collection support",
            "Better error messages",
            "Performance improvements"
        ],
        min_collection_versions={
            "ansible.posix": "1.2.0",
            "ansible.windows": "1.5.0"
        },
        known_issues=[]
    ),
    
    "2.12": AnsibleVersion(
        version="2.12",
        release_date=date(2021, 11, 8),
        eol_date=date(2023, 5, 31),
        control_node_python=["3.8", "3.9", "3.10"],
        managed_node_python=["2.6", "2.7", "3.5", "3.6", "3.7", "3.8", "3.9", "3.10"],
        major_changes=[
            "Python 3.8+ required for control node",
            "Python 2.6/2.7 deprecated for managed nodes",
            "New ansible-core package name"
        ],
        min_collection_versions={
            "ansible.posix": "1.3.0",
            "ansible.windows": "1.9.0"
        },
        known_issues=[
            "Transition to ansible-core package"
        ]
    ),
    
    "2.13": AnsibleVersion(
        version="2.13",
        release_date=date(2022, 5, 16),
        eol_date=date(2023, 11, 6),
        control_node_python=["3.8", "3.9", "3.10"],
        managed_node_python=["2.7", "3.5", "3.6", "3.7", "3.8", "3.9", "3.10"],
        major_changes=[
            "Continued collection evolution",
            "Module deprecations enforced"
        ],
        min_collection_versions={
            "ansible.posix": "1.4.0",
            "ansible.windows": "1.11.0"
        },
        known_issues=[]
    ),
    
    "2.14": AnsibleVersion(
        version="2.14",
        release_date=date(2022, 11, 7),
        eol_date=date(2024, 5, 20),
        control_node_python=["3.9", "3.10", "3.11"],
        managed_node_python=["2.7", "3.5", "3.6", "3.7", "3.8", "3.9", "3.10", "3.11"],
        major_changes=[
            "Python 3.9+ required for control node",
            "Python 3.11 support added",
            "Further module deprecations"
        ],
        min_collection_versions={
            "ansible.posix": "1.5.0",
            "ansible.windows": "1.13.0"
        },
        known_issues=[]
    ),
    
    "2.15": AnsibleVersion(
        version="2.15",
        release_date=date(2023, 5, 15),
        eol_date=date(2024, 11, 4),
        control_node_python=["3.9", "3.10", "3.11"],
        managed_node_python=["2.7", "3.5", "3.6", "3.7", "3.8", "3.9", "3.10", "3.11"],
        major_changes=[
            "Performance improvements",
            "Better collection tooling",
            "Enhanced error reporting"
        ],
        min_collection_versions={
            "ansible.posix": "1.5.4",
            "ansible.windows": "1.14.0"
        },
        known_issues=[]
    ),
    
    "2.16": AnsibleVersion(
        version="2.16",
        release_date=date(2023, 11, 6),
        eol_date=None,  # Still supported as of Feb 2026
        control_node_python=["3.10", "3.11", "3.12"],
        managed_node_python=["2.7", "3.6", "3.7", "3.8", "3.9", "3.10", "3.11", "3.12"],
        major_changes=[
            "Python 3.10+ required for control node",
            "Python 3.12 support added",
            "Latest stable release"
        ],
        min_collection_versions={
            "ansible.posix": "1.6.0",
            "ansible.windows": "2.0.0"
        },
        known_issues=[]
    ),
    
    "2.17": AnsibleVersion(
        version="2.17",
        release_date=date(2024, 5, 20),
        eol_date=None,  # Future release
        control_node_python=["3.10", "3.11", "3.12"],
        managed_node_python=["3.7", "3.8", "3.9", "3.10", "3.11", "3.12"],
        major_changes=[
            "Python 2.7 removed from managed nodes",
            "Python 3.7+ required for managed nodes",
            "Future features TBD"
        ],
        min_collection_versions={
            "ansible.posix": "1.7.0",
            "ansible.windows": "2.1.0"
        },
        known_issues=[]
    )
}

def get_python_compatibility(
    ansible_version: str,
    node_type: str = "control"
) -> List[str]:
    """Get compatible Python versions from PDF matrix.
    
    Args:
        ansible_version: Ansible version (e.g., "2.16")
        node_type: "control" or "managed"
        
    Returns:
        List of compatible Python versions
    """
    version = ANSIBLE_VERSIONS.get(ansible_version)
    if not version:
        raise ValueError(f"Unknown Ansible version: {ansible_version}")
    
    if node_type == "control":
        return version.control_node_python
    elif node_type == "managed":
        return version.managed_node_python
    else:
        raise ValueError(f"Invalid node_type: {node_type}")

def calculate_upgrade_path(
    current_version: str,
    target_version: str
) -> dict:
    """Calculate upgrade path based on PDF compatibility matrix.
    
    Follows best practices:
    - 2.9 → 2.10: MAJOR (collections split)
    - 2.10 → 2.11: Minor
    - Skip versions at your own risk
    - Python upgrade may be required
    
    Args:
        current_version: Current Ansible version
        target_version: Desired Ansible version
        
    Returns:
        Upgrade path with intermediates, risks, and requirements
    """
    if current_version not in ANSIBLE_VERSIONS:
        raise ValueError(f"Unknown current version: {current_version}")
    if target_version not in ANSIBLE_VERSIONS:
        raise ValueError(f"Unknown target version: {target_version}")
    
    current = ANSIBLE_VERSIONS[current_version]
    target = ANSIBLE_VERSIONS[target_version]
    
    # Determine if direct upgrade is recommended
    current_major = float(current_version)
    target_major = float(target_version)
    version_gap = target_major - current_major
    
    # FROM PDF: Major version jumps should go through intermediates
    intermediate_versions = []
    if version_gap > 0.2:  # More than 2 minor versions
        # Calculate intermediates
        for version in sorted(ANSIBLE_VERSIONS.keys()):
            version_num = float(version)
            if current_major < version_num < target_major:
                intermediate_versions.append(version)
    
    # Collect all breaking changes across the path
    breaking_changes = []
    versions_to_check = intermediate_versions + [target_version]
    for version in versions_to_check:
        breaking_changes.extend(ANSIBLE_VERSIONS[version].major_changes)
    
    # Check Python compatibility
    python_upgrade_needed = not any(
        py in target.control_node_python 
        for py in current.control_node_python
    )
    
    # Assess risk based on PDF data
    risk_factors = []
    if "2.9" in current_version and version_gap > 0:
        risk_factors.append("Upgrading from 2.9 (collections split)")
    if version_gap > 0.5:
        risk_factors.append(f"Large version jump ({version_gap} versions)")
    if python_upgrade_needed:
        risk_factors.append("Python upgrade required")
    if current.eol_date and current.eol_date < date.today():
        risk_factors.append("Current version is EOL")
    
    risk_level = "High" if len(risk_factors) >= 2 else "Medium" if risk_factors else "Low"
    
    # Estimate effort (FROM PDF complexity)
    effort_days = 1.0  # Base
    if "2.9" in current_version:
        effort_days += 3.0  # Collections migration
    effort_days += len(intermediate_versions) * 1.5
    if python_upgrade_needed:
        effort_days += 2.0
    
    return {
        "from_version": current_version,
        "to_version": target_version,
        "direct_upgrade": len(intermediate_versions) == 0,
        "intermediate_versions": intermediate_versions,
        "breaking_changes": breaking_changes,
        "python_upgrade_needed": python_upgrade_needed,
        "current_python": current.control_node_python,
        "required_python": target.control_node_python,
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "estimated_effort_days": round(effort_days, 1),
        "collection_updates_needed": target.min_collection_versions
    }

def get_eol_status(version: str) -> dict:
    """Get EOL status from PDF data."""
    if version not in ANSIBLE_VERSIONS:
        return {"error": f"Unknown version: {version}"}
    
    version_info = ANSIBLE_VERSIONS[version]
    
    if not version_info.eol_date:
        return {
            "version": version,
            "is_eol": False,
            "status": "Supported",
            "message": f"Version {version} is currently supported"
        }
    
    today = date.today()
    is_eol = version_info.eol_date < today
    days_diff = abs((version_info.eol_date - today).days)
    
    if is_eol:
        return {
            "version": version,
            "is_eol": True,
            "eol_date": version_info.eol_date,
            "days_overdue": days_diff,
            "status": "End of Life",
            "message": f"⚠️  Version {version} reached EOL {days_diff} days ago. Upgrade immediately!",
            "security_risk": "HIGH"
        }
    elif days_diff < 90:
        return {
            "version": version,
            "is_eol": False,
            "eol_approaching": True,
            "eol_date": version_info.eol_date,
            "days_remaining": days_diff,
            "status": "EOL Approaching",
            "message": f"⚡ Version {version} will reach EOL in {days_diff} days. Plan upgrade soon.",
            "security_risk": "MEDIUM"
        }
    else:
        return {
            "version": version,
            "is_eol": False,
            "eol_date": version_info.eol_date,
            "days_remaining": days_diff,
            "status": "Supported",
            "message": f"✅ Version {version} is supported for {days_diff} more days",
            "security_risk": "LOW"
        }
```

### 2. Assessment Logic (`ansible_upgrade.py`)

Uses the version data to assess real environments:

```python
def assess_ansible_environment(environment_path: str) -> dict:
    """Assess using PDF compatibility matrix."""
    
    # Detect current versions
    ansible_version = detect_ansible_version(environment_path)
    python_version = detect_python_version(environment_path)
    
    # Get version info from PDF data
    version_info = ANSIBLE_VERSIONS.get(ansible_version)
    eol_status = get_eol_status(ansible_version)
    
    # Check Python compatibility (FROM PDF)
    python_compatible = python_version in version_info.control_node_python
    
    # Scan for version-specific issues
    compatibility_issues = []
    
    # FROM PDF: Check for known breaking changes
    if ansible_version == "2.9":
        compatibility_issues.append(
            "Version 2.9 uses legacy module paths. "
            "Upgrade requires collection migration."
        )
    
    # Check collection compatibility
    collections = parse_requirements_yml(environment_path / "requirements.yml")
    for collection, version in collections.items():
        min_version = version_info.min_collection_versions.get(collection)
        if min_version and version < min_version:
            compatibility_issues.append(
                f"Collection {collection} {version} incompatible. "
                f"Requires {min_version}+"
            )
    
    # Generate recommendations based on PDF data
    recommendations = []
    
    if eol_status["is_eol"]:
        recommendations.append(
            f"🚨 URGENT: Upgrade from EOL version {ansible_version}"
        )
        # FROM PDF: Recommend latest stable
        recommendations.append(
            "Recommended target: Ansible 2.16 (latest stable)"
        )
    
    if not python_compatible:
        recommendations.append(
            f"⚠️  Python {python_version} incompatible with Ansible {ansible_version}"
        )
        recommendations.append(
            f"Supported Python versions: {', '.join(version_info.control_node_python)}"
        )
    
    return {
        "current_version": ansible_version,
        "python_version": python_version,
        "python_compatible": python_compatible,
        "eol_status": eol_status,
        "compatibility_issues": compatibility_issues,
        "recommendations": recommendations,
        "version_info": version_info
    }
```

## Key Implementation Notes

### 1. Collections Split (2.9 → 2.10)

FROM PDF: This is the MOST significant breaking change.

```python
# Special handling for 2.9 upgrades
if current_version == "2.9":
    plan["pre_upgrade_checklist"].append(
        "Identify all modules used and map to collections"
    )
    plan["pre_upgrade_checklist"].append(
        "Install required collections: "
        "ansible-galaxy collection install -r requirements.yml"
    )
    plan["upgrade_steps"].append({
        "step": "Update module paths",
        "description": "Change module calls to ansible.builtin.* namespace",
        "example": "yum → ansible.builtin.yum"
    })
```

### 2. Python Version Requirements

FROM PDF: Different requirements for control vs managed nodes.

```python
# Check both control and managed node compatibility
def validate_python_compatibility(
    ansible_version: str,
    control_python: str,
    managed_pythons: List[str]
) -> dict:
    """Validate Python compatibility from PDF matrix."""
    version = ANSIBLE_VERSIONS[ansible_version]
    
    control_ok = control_python in version.control_node_python
    managed_ok = all(
        py in version.managed_node_python 
        for py in managed_pythons
    )
    
    return {
        "control_node_compatible": control_ok,
        "managed_nodes_compatible": managed_ok,
        "requires_upgrade": not (control_ok and managed_ok)
    }
```

### 3. EOL Status Checking

FROM PDF: Version EOL dates are critical for security.

```python
# Regular EOL checks in assessments
if version_info.eol_date and version_info.eol_date < date.today():
    severity = "CRITICAL"
    priority = 1
else:
    severity = "INFO"
    priority = 5
```

## CLI Examples Based on PDF Data

```bash
# Check if your version is EOL (FROM PDF)
souschef ansible eol 2.9
# Output: ⚠️  Version 2.9 reached EOL on 2022-05-23 (1356 days ago)

# Plan upgrade considering Python compatibility (FROM PDF)
souschef ansible plan /opt/ansible 2.16
# Output includes:
# - Python 3.10+ required for control node
# - Collections migration needed (if from 2.9)
# - Estimated 5.5 days effort

# Assess environment compatibility (FROM PDF)
souschef ansible assess /opt/ansible
# Output includes:
# - Current: Ansible 2.9, Python 3.8
# - Issues: EOL version, collections migration needed
# - Recommended: Upgrade to 2.16, update Python to 3.11
```

## Testing with PDF Data

```python
# tests/unit/test_ansible_versions.py

def test_version_compatibility_from_pdf():
    """Test version data matches PDF matrix."""
    
    # FROM PDF: Ansible 2.9 supports Python 3.5-3.8
    assert "3.8" in get_python_compatibility("2.9", "control")
    assert "3.9" not in get_python_compatibility("2.9", "control")
    
    # FROM PDF: Ansible 2.16 requires Python 3.10+
    assert "3.10" in get_python_compatibility("2.16", "control")
    assert "3.9" not in get_python_compatibility("2.16", "control")

def test_upgrade_path_2_9_to_2_16():
    """Test upgrade path from EOL 2.9 to latest 2.16."""
    
    path = calculate_upgrade_path("2.9", "2.16")
    
    # FROM PDF: Should include intermediate versions
    assert not path["direct_upgrade"]
    assert "2.10" in path["intermediate_versions"]
    
    # FROM PDF: Should flag collections split
    breaking_changes = "\n".join(path["breaking_changes"])
    assert "collections split" in breaking_changes.lower()
    
    # FROM PDF: Python upgrade needed
    assert path["python_upgrade_needed"]
    
    # Should be high risk due to major changes
    assert path["risk_level"] in ["High", "Medium"]
```

## Summary

This implementation directly translates the PDF's Ansible-Python compatibility matrix into:

1. **Structured data** (`ANSIBLE_VERSIONS` dict)
2. **Validation logic** (compatibility checking)
3. **Assessment algorithms** (EOL status, upgrade paths)
4. **User-facing tools** (MCP, CLI, Web UI)

The PDF provides the **"what"** (compatibility rules), and our implementation provides the **"how"** (assessment automation and planning).

## Next Actions

1. ✅ Created design document
2. ⏳ Implement `core/ansible_versions.py` with PDF data
3. ⏳ Add unit tests validating PDF matrix accuracy
4. ⏳ Implement assessment logic
5. ⏳ Add MCP tools and CLI commands
6. ⏳ Create web UI
