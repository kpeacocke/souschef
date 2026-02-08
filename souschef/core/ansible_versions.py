"""
Ansible and Python version compatibility data.

Data source: ansible-python-upgrade-matrix-cheatsheet.pdf
Last updated: February 2026

This module contains the authoritative Ansible-Python compatibility matrix
and provides utilities for version checking, upgrade path planning, and
EOL status verification.
"""

from dataclasses import dataclass, field
from datetime import date

# Collection name constants
ANSIBLE_POSIX = "ansible.posix"
ANSIBLE_WINDOWS = "ansible.windows"
ANSIBLE_POSIX_MIN_VERSION = "1.0.0"
ANSIBLE_WINDOWS_MIN_VERSION = "1.0.0"
MANAGED_NODES = "managed_node_python"
CONTROL_NODES = "control_node_python"
POSIX_1_2_0 = "1.2.0"
POSIX_1_3_0 = "1.3.0"
POSIX_1_4_0 = "1.4.0"
POSIX_1_5_0 = "1.5.0"
POSIX_1_5_4 = "1.5.4"
POSIX_1_6_0 = "1.6.0"
POSIX_1_7_0 = "1.7.0"
WINDOWS_1_5_0 = "1.5.0"
WINDOWS_1_9_0 = "1.9.0"
WINDOWS_1_11_0 = "1.11.0"
WINDOWS_1_13_0 = "1.13.0"
WINDOWS_1_14_0 = "1.14.0"
WINDOWS_2_0_0 = "2.0.0"
WINDOWS_2_1_0 = "2.1.0"


@dataclass
class AnsibleVersion:
    """
    Ansible version information from compatibility matrix.

    Attributes:
        version: Ansible version string (e.g., "2.16").
        release_date: Date when this version was released.
        eol_date: End-of-life date, or None if still supported.
        control_node_python: Python versions supported on control node.
        managed_node_python: Python versions supported on managed nodes.
        major_changes: Breaking changes introduced in this version.
        min_collection_versions: Minimum required versions for collections.
        known_issues: Known issues or warnings for this version.

    """

    version: str
    release_date: date
    eol_date: date | None
    control_node_python: list[str]
    managed_node_python: list[str]
    major_changes: list[str] = field(default_factory=list)
    min_collection_versions: dict[str, str] = field(default_factory=dict)
    known_issues: list[str] = field(default_factory=list)


# FROM PDF: Complete Ansible version compatibility matrix
ANSIBLE_VERSIONS: dict[str, AnsibleVersion] = {
    "2.9": AnsibleVersion(
        version="2.9",
        release_date=date(2019, 10, 31),
        eol_date=date(2022, 5, 23),
        control_node_python=["2.7", "3.5", "3.6", "3.7", "3.8"],
        managed_node_python=["2.6", "2.7", "3.5", "3.6", "3.7", "3.8"],
        major_changes=[
            "Last version before collections split",
            "Many modules now deprecated",
            "No longer receives security updates",
        ],
        min_collection_versions={},
        known_issues=[
            "Security vulnerabilities - upgrade immediately",
            "No Python 3.9+ support",
            "EOL since May 2022",
        ],
    ),
    "2.10": AnsibleVersion(
        version="2.10",
        release_date=date(2020, 9, 22),
        eol_date=date(2022, 5, 23),
        control_node_python=["3.6", "3.7", "3.8", "3.9"],
        managed_node_python=["2.6", "2.7", "3.5", "3.6", "3.7", "3.8", "3.9"],
        major_changes=[
            "Major: collections split from core",
            "ansible.builtin namespace introduced",
            "Requires explicit collection installation",
            "Module paths changed",
        ],
        min_collection_versions={
            ANSIBLE_POSIX: ANSIBLE_POSIX_MIN_VERSION,
            ANSIBLE_WINDOWS: ANSIBLE_WINDOWS_MIN_VERSION,
        },
        known_issues=[
            "Collection installation required for many modules",
            "Import path changes break old playbooks",
            "EOL since May 2022",
        ],
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
            "Performance improvements",
        ],
        min_collection_versions={
            ANSIBLE_POSIX: POSIX_1_2_0,
            ANSIBLE_WINDOWS: WINDOWS_1_5_0,
        },
        known_issues=["EOL since November 2022"],
    ),
    "2.12": AnsibleVersion(
        version="2.12",
        release_date=date(2021, 11, 8),
        eol_date=date(2023, 5, 31),
        control_node_python=["3.8", "3.9", "3.10"],
        managed_node_python=[
            "2.6",
            "2.7",
            "3.5",
            "3.6",
            "3.7",
            "3.8",
            "3.9",
            "3.10",
        ],
        major_changes=[
            "Python 3.8+ required for control node",
            "Python 2.6/2.7 deprecated for managed nodes",
            "New ansible-core package name",
        ],
        min_collection_versions={
            ANSIBLE_POSIX: POSIX_1_3_0,
            ANSIBLE_WINDOWS: WINDOWS_1_9_0,
        },
        known_issues=[
            "Transition to ansible-core package",
            "EOL since May 2023",
        ],
    ),
    "2.13": AnsibleVersion(
        version="2.13",
        release_date=date(2022, 5, 16),
        eol_date=date(2023, 11, 6),
        control_node_python=["3.8", "3.9", "3.10"],
        managed_node_python=["2.7", "3.5", "3.6", "3.7", "3.8", "3.9", "3.10"],
        major_changes=[
            "Continued collection evolution",
            "Module deprecations enforced",
        ],
        min_collection_versions={
            ANSIBLE_POSIX: POSIX_1_4_0,
            ANSIBLE_WINDOWS: WINDOWS_1_11_0,
        },
        known_issues=["EOL since November 2023"],
    ),
    "2.14": AnsibleVersion(
        version="2.14",
        release_date=date(2022, 11, 7),
        eol_date=date(2024, 5, 20),
        control_node_python=["3.9", "3.10", "3.11"],
        managed_node_python=[
            "2.7",
            "3.5",
            "3.6",
            "3.7",
            "3.8",
            "3.9",
            "3.10",
            "3.11",
        ],
        major_changes=[
            "Python 3.9+ required for control node",
            "Python 3.11 support added",
            "Further module deprecations",
        ],
        min_collection_versions={
            ANSIBLE_POSIX: POSIX_1_5_0,
            ANSIBLE_WINDOWS: WINDOWS_1_13_0,
        },
        known_issues=["EOL since May 2024"],
    ),
    "2.15": AnsibleVersion(
        version="2.15",
        release_date=date(2023, 5, 15),
        eol_date=date(2024, 11, 4),
        control_node_python=["3.9", "3.10", "3.11"],
        managed_node_python=[
            "2.7",
            "3.5",
            "3.6",
            "3.7",
            "3.8",
            "3.9",
            "3.10",
            "3.11",
        ],
        major_changes=[
            "Performance improvements",
            "Better collection tooling",
            "Enhanced error reporting",
        ],
        min_collection_versions={
            ANSIBLE_POSIX: POSIX_1_5_4,
            ANSIBLE_WINDOWS: WINDOWS_1_14_0,
        },
        known_issues=["EOL since November 2024"],
    ),
    "2.16": AnsibleVersion(
        version="2.16",
        release_date=date(2023, 11, 6),
        eol_date=date(2025, 5, 19),
        control_node_python=["3.10", "3.11", "3.12"],
        managed_node_python=[
            "2.7",
            "3.6",
            "3.7",
            "3.8",
            "3.9",
            "3.10",
            "3.11",
            "3.12",
        ],
        major_changes=[
            "Python 3.10+ required for control node",
            "Python 3.12 support added",
            "Latest stable release",
        ],
        min_collection_versions={
            ANSIBLE_POSIX: POSIX_1_6_0,
            ANSIBLE_WINDOWS: WINDOWS_2_0_0,
        },
        known_issues=[],
    ),
    "2.17": AnsibleVersion(
        version="2.17",
        release_date=date(2024, 5, 20),
        eol_date=None,
        control_node_python=["3.10", "3.11", "3.12"],
        managed_node_python=["3.7", "3.8", "3.9", "3.10", "3.11", "3.12"],
        major_changes=[
            "Python 2.7 removed from managed nodes",
            "Python 3.7+ required for managed nodes",
            "Continued performance enhancements",
        ],
        min_collection_versions={
            ANSIBLE_POSIX: POSIX_1_7_0,
            ANSIBLE_WINDOWS: WINDOWS_2_1_0,
        },
        known_issues=[],
    ),
}


def get_python_compatibility(
    ansible_version: str, node_type: str = "control"
) -> list[str]:
    """
    Get compatible Python versions from compatibility matrix.

    Args:
        ansible_version: Ansible version (e.g., "2.16").
        node_type: Either "control" or "managed".

    Returns:
        List of compatible Python version strings.

    Raises:
        ValueError: If ansible_version is unknown or node_type is invalid.

    """
    if ansible_version not in ANSIBLE_VERSIONS:
        raise ValueError(f"Unknown Ansible version: {ansible_version}")

    version = ANSIBLE_VERSIONS[ansible_version]

    if node_type == "control":
        return version.control_node_python
    if node_type == "managed":
        return version.managed_node_python

    raise ValueError(f"Invalid node_type: {node_type}. Use 'control' or 'managed'")


def _calculate_intermediate_versions(
    current_major: float, target_major: float
) -> list[str]:
    """Calculate intermediate versions for upgrade path."""
    version_gap = target_major - current_major
    intermediate_versions: list[str] = []

    if version_gap > 0.2:
        for version in sorted(ANSIBLE_VERSIONS.keys()):
            version_num = float(version)
            if current_major < version_num < target_major:
                intermediate_versions.append(version)

    return intermediate_versions


def _collect_breaking_changes(
    intermediate_versions: list[str], target_version: str
) -> list[str]:
    """Collect all breaking changes across the upgrade path."""
    breaking_changes: list[str] = []
    versions_to_check = intermediate_versions + [target_version]

    for version in versions_to_check:
        if version in ANSIBLE_VERSIONS:
            breaking_changes.extend(ANSIBLE_VERSIONS[version].major_changes)

    return breaking_changes


def _assess_upgrade_risk(
    current_version: str,
    current: AnsibleVersion,
    version_gap: float,
    python_upgrade_needed: bool,
) -> tuple[str, list[str]]:
    """Assess risk level and factors for upgrade."""
    risk_factors: list[str] = []

    if "2.9" in current_version and version_gap > 0:
        risk_factors.append("Upgrading from 2.9 (collections split required)")
    if version_gap > 0.5:
        risk_factors.append(f"Large version jump ({version_gap} versions)")
    if python_upgrade_needed:
        risk_factors.append("Python upgrade required on control node")
    if current.eol_date and current.eol_date < date.today():
        risk_factors.append("Current version is EOL")

    if len(risk_factors) >= 2:
        risk_level = "High"
    elif risk_factors:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return risk_level, risk_factors


def _estimate_upgrade_effort(
    current_version: str,
    intermediate_versions: list[str],
    python_upgrade_needed: bool,
) -> float:
    """Estimate effort in days for upgrade."""
    effort_days = 1.0

    if "2.9" in current_version:
        effort_days += 3.0
    effort_days += len(intermediate_versions) * 1.5
    if python_upgrade_needed:
        effort_days += 2.0

    return round(effort_days, 1)


def calculate_upgrade_path(
    current_version: str, target_version: str
) -> dict[str, object]:
    """
    Calculate upgrade path based on compatibility matrix.

    Follows best practices from Ansible upgrade documentation:
    - 2.9 to 2.10: major collections split
    - Large version gaps should use intermediate versions
    - Python upgrade may be required
    - Risk assessment based on breaking changes

    Args:
        current_version: Current Ansible version.
        target_version: Desired Ansible version.

    Returns:
        Dictionary with upgrade path details including:
        - from_version: Starting version
        - to_version: Target version
        - direct_upgrade: Whether direct upgrade is safe
        - intermediate_versions: Intermediate versions if needed
        - breaking_changes: List of breaking changes
        - python_upgrade_needed: Whether Python upgrade is required
        - current_python: Compatible Python versions for current
        - required_python: Compatible Python versions for target
        - risk_level: "Low", "Medium", or "High"
        - risk_factors: List of risk factors
        - estimated_effort_days: Estimated effort in days
        - collection_updates_needed: Required collection versions

    Raises:
        ValueError: If either version is unknown.

    """
    if current_version not in ANSIBLE_VERSIONS:
        raise ValueError(f"Unknown current version: {current_version}")
    if target_version not in ANSIBLE_VERSIONS:
        raise ValueError(f"Unknown target version: {target_version}")

    current = ANSIBLE_VERSIONS[current_version]
    target = ANSIBLE_VERSIONS[target_version]

    current_major = float(current_version)
    target_major = float(target_version)
    version_gap = target_major - current_major

    intermediate_versions = _calculate_intermediate_versions(
        current_major, target_major
    )
    breaking_changes = _collect_breaking_changes(intermediate_versions, target_version)

    python_upgrade_needed = not any(
        py in target.control_node_python for py in current.control_node_python
    )

    risk_level, risk_factors = _assess_upgrade_risk(
        current_version, current, version_gap, python_upgrade_needed
    )
    effort_days = _estimate_upgrade_effort(
        current_version, intermediate_versions, python_upgrade_needed
    )

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
        "estimated_effort_days": effort_days,
        "collection_updates_needed": target.min_collection_versions,
    }


def get_eol_status(version: str) -> dict[str, object]:
    """
    Get EOL status from compatibility matrix.

    Args:
        version: Ansible version to check.

    Returns:
        Dictionary with EOL status information.

    """
    if version not in ANSIBLE_VERSIONS:
        return {"error": f"Unknown version: {version}"}

    version_info = ANSIBLE_VERSIONS[version]

    if not version_info.eol_date:
        return {
            "version": version,
            "is_eol": False,
            "status": "Supported",
            "message": f"Version {version} is currently supported",
            "security_risk": "LOW",
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
            "message": (
                f"Warning: Version {version} reached EOL {days_diff} days ago. "
                "Upgrade immediately."
            ),
            "security_risk": "HIGH",
        }

    if days_diff < 90:
        return {
            "version": version,
            "is_eol": False,
            "eol_approaching": True,
            "eol_date": version_info.eol_date,
            "days_remaining": days_diff,
            "status": "EOL Approaching",
            "message": (
                f"Version {version} will reach EOL in {days_diff} days. "
                "Plan upgrade soon."
            ),
            "security_risk": "MEDIUM",
        }

    return {
        "version": version,
        "is_eol": False,
        "eol_date": version_info.eol_date,
        "days_remaining": days_diff,
        "status": "Supported",
        "message": f"Version {version} is supported for {days_diff} more days",
        "security_risk": "LOW",
    }


def is_python_compatible(
    ansible_version: str, python_version: str, node_type: str = "control"
) -> bool:
    """
    Check if Python version is compatible with Ansible version.

    Args:
        ansible_version: Ansible version (e.g., "2.16").
        python_version: Python version (e.g., "3.11").
        node_type: Either "control" or "managed".

    Returns:
        True if Python version is compatible, False otherwise.

    Raises:
        ValueError: If ansible_version is unknown or node_type is invalid.

    """
    compatible_versions = get_python_compatibility(ansible_version, node_type)
    return python_version in compatible_versions


def get_latest_version() -> str:
    """
    Get the latest supported Ansible version.

    Returns:
        Latest Ansible version string.

    """
    versions = sorted(ANSIBLE_VERSIONS.keys(), key=lambda v: float(v))
    return versions[-1]


def get_supported_versions() -> list[str]:
    """
    Get list of currently supported Ansible versions (not EOL).

    Returns:
        List of supported version strings, sorted newest to oldest.

    """
    today = date.today()
    supported = [
        v
        for v, info in ANSIBLE_VERSIONS.items()
        if not info.eol_date or info.eol_date >= today
    ]
    return sorted(supported, key=lambda v: float(v), reverse=True)


def get_minimum_python_for_ansible(ansible_version: str) -> tuple[str, str]:
    """
    Get minimum Python versions required for Ansible version.

    Args:
        ansible_version: Ansible version to check.

    Returns:
        Tuple of (minimum_control_python, minimum_managed_python).

    Raises:
        ValueError: If ansible_version is unknown.

    """
    if ansible_version not in ANSIBLE_VERSIONS:
        raise ValueError(f"Unknown Ansible version: {ansible_version}")

    version_info = ANSIBLE_VERSIONS[ansible_version]

    control_min = sorted(version_info.control_node_python)[0]
    managed_min = sorted(version_info.managed_node_python)[0]

    return (control_min, managed_min)
