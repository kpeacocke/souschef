"""
Ansible upgrade assessment and planning.

This module provides high-level functions for assessing Ansible environments,
generating upgrade plans, validating collection compatibility, and creating
testing strategies for Ansible upgrades.
"""

import shlex
import subprocess  # nosec B602: All subprocess calls use list args, not shell=True
from datetime import date
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

from souschef.core.ansible_versions import (
    ANSIBLE_VERSIONS,
    calculate_upgrade_path,
    get_eol_status,
    get_latest_version,
    is_python_compatible,
)
from souschef.parsers.ansible_inventory import (
    detect_ansible_version,
    get_ansible_config_paths,
    parse_requirements_yml,
    scan_playbook_for_version_issues,
)


class UpgradePath(TypedDict):
    """
    Structured upgrade path information.

    This mirrors the structure returned by calculate_upgrade_path().
    """

    from_version: str
    to_version: str
    risk_level: str
    estimated_effort_days: float
    direct_upgrade: bool
    intermediate_versions: list[str]
    risk_factors: list[str]
    breaking_changes: list[str]
    python_upgrade_needed: bool
    current_python: list[str]
    required_python: list[str]
    collection_updates_needed: dict[str, str]


class UpgradeStep(TypedDict):
    """Single upgrade step for the plan."""

    step: float
    action: str
    command: str
    duration_minutes: int
    notes: NotRequired[list[str]]


class RollbackPlan(TypedDict):
    """Rollback plan details."""

    steps: list[str]
    estimated_duration_minutes: int


class RiskAssessment(TypedDict):
    """Risk assessment details for the upgrade plan."""

    level: str
    factors: list[str]
    mitigation: list[str]


class UpgradePlan(TypedDict):
    """Structured upgrade plan details."""

    upgrade_path: UpgradePath
    pre_upgrade_checklist: list[str]
    upgrade_steps: list[UpgradeStep]
    testing_plan: dict[str, Any]
    post_upgrade_validation: list[str]
    rollback_plan: RollbackPlan
    estimated_downtime_hours: float
    risk_assessment: RiskAssessment


def _is_path_within(target: Path, base: Path) -> bool:
    """
    Check if target path is within base path (no traversal).

    Args:
        target: Path to check.
        base: Base path that target should be within.

    Returns:
        True if target is within base, False otherwise.

    """
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False


def detect_python_version(environment_path: str | None = None) -> str:
    """
    Detect Python version in use.

    Security: This function validates and resolves paths to prevent path traversal.
    User input should be validated at CLI/MCP layer before calling this function.

    Args:
        environment_path: Path to environment (looks for python/python3 there).

    Returns:
        Python version string (e.g., "3.11.2").

    Raises:
        ValueError: If environment_path is invalid or not a directory.
        RuntimeError: If Python version cannot be determined.

    """
    python_cmd = "python3"

    if environment_path:
        # Resolve path to prevent path traversal attacks
        # lgtm[py/path-injection] - Validated at entry + function level
        env_path = Path(environment_path).resolve()  # nosec B108

        # Validate the path exists and is a directory
        if not env_path.exists():  # NOSONAR
            raise ValueError(f"Environment path does not exist: {env_path}")
        if not env_path.is_dir():
            raise ValueError(f"Environment path is not a directory: {env_path}")

        venv_python = env_path / "bin" / "python3"
        if venv_python.exists():  # NOSONAR
            # Resolve to prevent symlink attacks and validate it's a file
            # lgtm[py/path-injection] - Derived from validated env_path
            resolved_python = venv_python.resolve()  # nosec B108
            if not resolved_python.is_file():
                raise ValueError(f"Python executable is not a file: {resolved_python}")
            # Verify the resolved path is still within expected bounds
            if not _is_path_within(resolved_python, env_path):
                raise ValueError("Python executable path escapes environment directory")
            python_cmd = str(resolved_python)

    try:
        # lgtm[py/command-line-injection] - Validated to be within bounds
        result = subprocess.run(
            [python_cmd, "--version"],  # nosec B603, B607
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        output = result.stdout or result.stderr
        version = output.strip().replace("Python ", "")
        return version
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ) as e:
        raise RuntimeError(f"Could not detect Python version: {e}") from e


def _detect_ansible_version_info(
    environment_path: str | None, result: dict[str, Any]
) -> None:
    """
    Detect and populate Ansible version information.

    Args:
        environment_path: Path to environment, or None to use system PATH.
        result: Dictionary to populate with version info.

    """
    try:
        # Look for ansible in the environment first
        if environment_path:
            env_path = Path(environment_path)
            ansible_executable = env_path / "bin" / "ansible"
            if ansible_executable.exists():  # NOSONAR
                ansible_version = detect_ansible_version(str(ansible_executable))
            else:
                # Fall back to system PATH ansible
                ansible_version = detect_ansible_version()
        else:
            ansible_version = detect_ansible_version()

        version_parts = ansible_version.split(".")
        if len(version_parts) >= 2:
            major_minor = f"{version_parts[0]}.{version_parts[1]}"
            result["current_version"] = major_minor
            result["current_version_full"] = ansible_version
        else:
            result["current_version"] = ansible_version
            result["current_version_full"] = ansible_version
    except (FileNotFoundError, RuntimeError) as e:
        result["compatibility_issues"].append(f"Could not detect Ansible version: {e}")


def _detect_python_version_info(environment_path: str, result: dict[str, Any]) -> None:
    """Detect Python version and check compatibility."""
    try:
        python_version = detect_python_version(environment_path)
        result["python_version"] = python_version

        if result["current_version"] != "unknown":
            py_parts = python_version.split(".")
            if len(py_parts) >= 2:
                py_major_minor = f"{py_parts[0]}.{py_parts[1]}"
                result["python_compatible"] = is_python_compatible(
                    result["current_version"], py_major_minor, "control"
                )
    except RuntimeError as e:
        result["compatibility_issues"].append(f"Could not detect Python version: {e}")


def _check_eol_status(result: dict[str, Any]) -> None:
    """Check and populate EOL status."""
    if result["current_version"] == "unknown":
        return

    result["eol_status"] = get_eol_status(result["current_version"])

    if result["eol_status"].get("is_eol"):
        result["compatibility_issues"].append(
            f"Ansible {result['current_version']} is EOL - "
            "security updates no longer provided"
        )


def _scan_collections(env_path: Path, result: dict[str, Any]) -> None:
    """Scan for and parse requirements.yml."""
    requirements_paths = [
        env_path / "requirements.yml",
        env_path / "collections" / "requirements.yml",
    ]

    for req_path in requirements_paths:
        if req_path.exists():  # NOSONAR
            try:
                # Verify requirements path is within env_path (no traversal)
                # lgtm[py/path-injection] - Derived from validated env_path
                resolved_req = req_path.resolve()  # nosec B108
                if not _is_path_within(resolved_req, env_path):
                    # Skip if path escapes environment directory
                    continue

                collections = parse_requirements_yml(str(resolved_req))
                result["collections"] = collections
                break
            except (FileNotFoundError, ValueError):
                # Skip requirements files that don't exist or can't be parsed
                continue


def _scan_playbooks(env_path: Path, result: dict[str, Any]) -> None:
    """Scan playbooks for version-specific issues."""
    playbook_paths = list(env_path.glob("**/*.yml")) + list(env_path.glob("**/*.yaml"))
    playbook_issues: list[str] = []

    for playbook_path in playbook_paths[:20]:
        try:
            # Verify playbook path is within env_path (no traversal)
            # lgtm[py/path-injection] - Paths from glob of validated env_path
            resolved_playbook = playbook_path.resolve()  # nosec B108
            if not _is_path_within(resolved_playbook, env_path):
                # Skip files that escape the environment directory
                continue

            issues = scan_playbook_for_version_issues(str(resolved_playbook))
            if issues["warnings"]:
                playbook_issues.extend(issues["warnings"])
            result["playbooks_scanned"] += 1
        except (FileNotFoundError, ValueError):
            continue

    if playbook_issues:
        result["compatibility_issues"].extend(playbook_issues[:10])


def _check_python_compatibility(result: dict[str, Any]) -> None:
    """Check for Python compatibility issues."""
    if result["python_compatible"] or result["current_version"] == "unknown":
        return

    version_info = ANSIBLE_VERSIONS.get(result["current_version"])
    if not version_info:
        return

    py_parts = result["python_version"].split(".")
    if len(py_parts) >= 2:
        py_major_minor = f"{py_parts[0]}.{py_parts[1]}"
    else:
        py_major_minor = result["python_version"]
    compatible = ", ".join(version_info.control_node_python)
    result["compatibility_issues"].append(
        f"Python {py_major_minor} is not compatible with "
        f"Ansible {result['current_version']}. "
        f"Compatible versions: {compatible}"
    )


def assess_ansible_environment(environment_path: str) -> dict[str, Any]:
    """
    Assess current Ansible environment for upgrade readiness.

    Security: Path is validated and resolved to prevent traversal attacks.
    User input should be validated at CLI/MCP layer before calling this function.

    Scans the environment, detects versions, checks compatibility,
    and generates recommendations.

    Args:
        environment_path: Path to Ansible environment directory.

    Returns:
        Dictionary containing environment assessment details.

    """
    # lgtm[py/path-injection] - Validated at entry + function level
    env_path = Path(environment_path).resolve()  # nosec B108
    if not env_path.exists():  # NOSONAR
        return {"error": f"Environment path does not exist: {env_path}"}
    if not env_path.is_dir():
        return {"error": f"Environment path is not a directory: {env_path}"}

    result: dict[str, Any] = {
        "current_version": "unknown",
        "python_version": "unknown",
        "python_compatible": False,
        "eol_status": {},
        "config_paths": {},
        "collections": {},
        "playbooks_scanned": 0,
        "compatibility_issues": [],
        "recommendations": [],
    }

    _detect_ansible_version_info(str(env_path), result)
    _detect_python_version_info(str(env_path), result)
    _check_eol_status(result)

    result["config_paths"] = get_ansible_config_paths()

    _scan_collections(env_path, result)
    _scan_playbooks(env_path, result)
    _check_python_compatibility(result)

    _generate_recommendations(result)

    return result


def _generate_recommendations(assessment: dict[str, Any]) -> None:
    """
    Generate recommendations based on assessment.

    Modifies the assessment dictionary in place to add recommendations.

    Args:
        assessment: Assessment dictionary from assess_ansible_environment.

    """
    recommendations: list[str] = []

    if assessment["eol_status"].get("is_eol"):
        latest = get_latest_version()
        recommendations.append(
            "Urgent: upgrade from EOL version "
            f"{assessment['current_version']} to maintain security support"
        )
        recommendations.append(f"Recommended target: Ansible {latest} (latest stable)")
    elif assessment["eol_status"].get("eol_approaching"):
        days = assessment["eol_status"].get("days_remaining", 0)
        recommendations.append(f"Plan upgrade soon - EOL in {days} days")

    if (
        not assessment["python_compatible"]
        and assessment["current_version"] != "unknown"
    ):
        version_info = ANSIBLE_VERSIONS.get(assessment["current_version"])
        if version_info:
            recommendations.append(
                "Upgrade Python to one of: "
                f"{', '.join(version_info.control_node_python)}"
            )

    if "2.9" in assessment["current_version"]:
        recommendations.append(
            "Prepare for collections migration (2.9 to 2.10+ requires updates)"
        )
        recommendations.append(
            "Create requirements.yml with needed collections before upgrading"
        )

    if assessment["compatibility_issues"]:
        unique_issues = len(set(assessment["compatibility_issues"]))
        if unique_issues > 0:
            recommendations.append(
                f"Review and fix {unique_issues} compatibility issue(s) before "
                "upgrading"
            )

    if assessment["current_version"] != "unknown":
        latest = get_latest_version()
        current_float = float(assessment["current_version"])
        latest_float = float(latest)

        if current_float < latest_float:
            recommendations.append(
                f"Consider upgrading to Ansible {latest} for latest features "
                "and security updates"
            )

    assessment["recommendations"] = recommendations


def generate_upgrade_plan(current_version: str, target_version: str) -> UpgradePlan:
    """
    Generate detailed Ansible upgrade plan.

    Args:
        current_version: Current Ansible version (e.g., "2.9").
        target_version: Target Ansible version (e.g., "2.16").

    Returns:
        Dictionary containing upgrade plan details.

    """
    path = cast(UpgradePath, calculate_upgrade_path(current_version, target_version))

    plan: UpgradePlan = {
        "upgrade_path": path,
        "pre_upgrade_checklist": [],
        "upgrade_steps": [],
        "testing_plan": {},
        "post_upgrade_validation": [],
        "rollback_plan": {
            "steps": [],
            "estimated_duration_minutes": 0,
        },
        "estimated_downtime_hours": 0.0,
        "risk_assessment": {
            "level": "",
            "factors": [],
            "mitigation": [],
        },
    }

    plan["pre_upgrade_checklist"] = [
        "Backup current Ansible installation and configurations",
        "Document current Ansible and Python versions",
        "Review all playbooks for deprecated syntax",
        "Create test environment matching production",
        "Notify team of planned upgrade window",
    ]

    if "2.9" in current_version:
        plan["pre_upgrade_checklist"].extend(
            [
                "Identify all modules used and map to collections",
                "Create requirements.yml with needed collections",
                "Test collections installation in dev environment",
                "Update playbooks to use ansible.builtin.* namespace",
            ]
        )

    if path["python_upgrade_needed"]:
        # Type cast: we know required_python is list[str] from calculate_upgrade_path
        required_python = path["required_python"]
        assert isinstance(required_python, list)
        plan["pre_upgrade_checklist"].extend(
            [
                f"Upgrade Python to one of: {', '.join(required_python)}",
                "Test Python upgrade in isolated environment",
                "Verify all Python dependencies still work",
            ]
        )

    if path["direct_upgrade"]:
        plan["upgrade_steps"] = [
            {
                "step": 1,
                "action": (f"Upgrade Ansible {current_version} to {target_version}"),
                "command": f"pip install ansible-core=={target_version}",
                "duration_minutes": 15,
            }
        ]
    else:
        step_num = 1
        # Type cast: we know intermediate_versions is list[str]
        # from calculate_upgrade_path
        intermediate_versions = path["intermediate_versions"]
        assert isinstance(intermediate_versions, list)
        versions = [current_version] + intermediate_versions + [target_version]

        for i in range(len(versions) - 1):
            from_ver = versions[i]
            to_ver = versions[i + 1]

            plan["upgrade_steps"].append(
                {
                    "step": step_num,
                    "action": f"Upgrade Ansible {from_ver} to {to_ver}",
                    "command": f"pip install ansible-core=={to_ver}",
                    "duration_minutes": 15,
                    "notes": _get_upgrade_notes(from_ver, to_ver),
                }
            )
            step_num += 1

    if "2.9" in current_version:
        plan["upgrade_steps"].insert(
            1,
            {
                "step": 1.5,
                "action": "Install required collections",
                "command": "ansible-galaxy collection install -r requirements.yml",
                "duration_minutes": 10,
            },
        )

    plan["post_upgrade_validation"] = [
        "Verify Ansible version: ansible --version",
        "Run ansible-playbook --syntax-check on all playbooks",
        "Execute test playbooks in dev environment",
        "Validate connectivity to all managed nodes",
        "Check collection versions: ansible-galaxy collection list",
        "Run smoke tests on critical playbooks",
    ]

    plan["testing_plan"] = _generate_testing_plan()

    plan["rollback_plan"] = {
        "steps": [
            f"Uninstall Ansible {target_version}",
            f"Reinstall Ansible {current_version}",
            "Restore configuration backups",
            "Verify rollback: ansible --version",
            "Test critical playbooks",
        ],
        "estimated_duration_minutes": 30,
    }

    total_minutes = sum(
        step.get("duration_minutes", 15) for step in plan["upgrade_steps"]
    )
    plan["estimated_downtime_hours"] = round(total_minutes / 60, 1)

    plan["risk_assessment"] = {
        "level": path["risk_level"],
        "factors": path["risk_factors"],
        "mitigation": _generate_risk_mitigation(path),
    }

    return plan


def _get_upgrade_notes(from_version: str, to_version: str) -> list[str]:
    """
    Get upgrade notes for version transition.

    Args:
        from_version: Source version.
        to_version: Target version.

    Returns:
        List of notes for this upgrade.

    """
    notes: list[str] = []

    if from_version == "2.9" and to_version == "2.10":
        notes.append("Collections split - major breaking change")
        notes.append("Update module paths to use collections")

    if ("2.9" in from_version or "2.10" in from_version) and float(to_version) >= 2.12:
        notes.append("Python 3.8+ required for control node")

    return notes


def _generate_testing_plan() -> dict[str, Any]:
    """
    Generate testing plan for upgrade.

    Returns:
        Testing plan dictionary.

    """
    return {
        "phases": [
            {
                "phase": "Unit Testing",
                "steps": [
                    "Syntax check all playbooks",
                    "Validate inventory files",
                    "Check variable definitions",
                ],
            },
            {
                "phase": "Integration Testing",
                "steps": [
                    "Run playbooks in test environment",
                    "Verify idempotency",
                    "Test error handling",
                ],
            },
            {
                "phase": "Performance Testing",
                "steps": [
                    "Compare execution times",
                    "Monitor resource usage",
                    "Test with production-like load",
                ],
            },
        ],
        "success_criteria": [
            "All playbooks pass syntax check",
            "Test runs complete without errors",
            "Idempotency verified",
            "Performance within 10 percent of baseline",
        ],
    }


def _generate_risk_mitigation(upgrade_path: UpgradePath) -> list[str]:
    """
    Generate risk mitigation strategies.

    Args:
        upgrade_path: Upgrade path from calculate_upgrade_path.

    Returns:
        List of mitigation strategies.

    """
    mitigation = [
        "Create full backups before upgrade",
        "Test upgrade in non-production environment first",
        "Implement staged rollout (dev to staging to production)",
        "Maintain rollback capability throughout process",
        "Document all changes and issues encountered",
    ]

    if upgrade_path["risk_level"] == "High":
        mitigation.extend(
            [
                "Schedule extended maintenance window",
                "Have senior team members available during upgrade",
                "Prepare communication plan for stakeholders",
            ]
        )

    if "2.9" in upgrade_path["from_version"]:
        mitigation.append("Allocate extra time for collections migration testing")

    return mitigation


def _add_collection_entry(
    result: dict[str, Any],
    collection: str,
    version: str,
    required: str | None = None,
    update_needed: bool = False,
    warning: str | None = None,
) -> None:
    """
    Append a collection entry and optional warning to the result.

    Args:
        result: Compatibility result dictionary to update.
        collection: Collection name.
        version: Current collection version.
        required: Required minimum version, if applicable.
        update_needed: Whether this collection requires an update.
        warning: Optional warning message to append.

    """
    if update_needed and required:
        result["updates_needed"].append(
            {
                "collection": collection,
                "current": version,
                "required": required,
            }
        )
    else:
        result["compatible"].append({"collection": collection, "version": version})

    if warning:
        result["warnings"].append(warning)


def _normalise_collection_version(version: str | None) -> str | None:
    """
    Normalise collection version strings.

    Args:
        version: Raw version string from requirements.yml.

    Returns:
        Normalised version string, or None for wildcard/empty values.

    """
    if not version or version == "*":
        return None
    return version


def _handle_version_specifier(
    result: dict[str, Any],
    collection: str,
    version: str,
    required: str,
) -> None:
    """
    Handle non-standard version specifiers.

    Args:
        result: Compatibility result dictionary to update.
        collection: Collection name.
        version: Version specifier string.
        required: Required minimum version.

    """
    try:
        specifier = SpecifierSet(version)
        required_obj = Version(required)

        if required_obj in specifier:
            _add_collection_entry(result, collection, version)
        else:
            warning = (
                f"Collection {collection} has specifier {version}. "
                f"Cannot determine compatibility with {required}"
            )
            _add_collection_entry(result, collection, version, warning=warning)
    except Exception:
        warning = f"Collection {collection} has unparseable version: {version}"
        _add_collection_entry(result, collection, version, warning=warning)


def _assess_collection_version(
    result: dict[str, Any],
    collection: str,
    version: str | None,
    required: str,
) -> None:
    """
    Compare collection version against required minimum version.

    Args:
        result: Compatibility result dictionary to update.
        collection: Collection name.
        version: Current version string (may be None for wildcard).
        required: Required minimum version.

    """
    normalised = _normalise_collection_version(version)
    if normalised is None:
        _add_collection_entry(result, collection, version or "*")
        return

    try:
        version_obj = Version(normalised)
        required_obj = Version(required)

        if version_obj >= required_obj:
            _add_collection_entry(result, collection, normalised)
        else:
            warning = (
                f"Collection {collection} {normalised} incompatible. "
                f"Requires {required}+"
            )
            _add_collection_entry(
                result,
                collection,
                normalised,
                required=required,
                update_needed=True,
                warning=warning,
            )
    except InvalidVersion:
        _handle_version_specifier(result, collection, normalised, required)


def validate_collection_compatibility(
    collections: dict[str, str], target_ansible_version: str
) -> dict[str, Any]:
    """
    Validate collection compatibility with target Ansible version.

    Args:
        collections: Dictionary of collection names to versions.
        target_ansible_version: Target Ansible version.

    Returns:
        Dictionary with compatibility results.

    """
    if target_ansible_version not in ANSIBLE_VERSIONS:
        return {"error": f"Unknown Ansible version: {target_ansible_version}"}

    target_info = ANSIBLE_VERSIONS[target_ansible_version]
    min_versions = target_info.min_collection_versions

    result: dict[str, Any] = {
        "compatible": [],
        "incompatible": [],
        "updates_needed": [],
        "warnings": [],
    }

    for collection, version in collections.items():
        if collection in min_versions:
            _assess_collection_version(
                result, collection, version, min_versions[collection]
            )
            continue

        _add_collection_entry(result, collection, version)

    return result


def generate_upgrade_testing_plan(environment_path: str) -> str:
    """
    Generate comprehensive testing plan for Ansible upgrade.

    Security: Path is validated, resolved, and escaped to prevent injection.
    User input should be validated at CLI/MCP layer before calling this function.

    Args:
        environment_path: Path to Ansible environment.

    Returns:
        Markdown-formatted testing plan.

    """
    # Validate and resolve path to prevent injection
    # lgtm[py/path-injection] - Input validated at CLI/MCP layer, resolved and escaped
    resolved_path = Path(environment_path).resolve()  # nosec B108
    escaped_path = shlex.quote(str(resolved_path))

    plan = f"""# Ansible Upgrade Testing Plan

Generated: {date.today().isoformat()}
Environment: {escaped_path}

## 1. Pre-Upgrade Testing

### 1.1 Baseline Establishment
- [ ] Run all playbooks and record results
- [ ] Document current execution times
- [ ] Capture current output/logs
- [ ] Record resource usage (CPU, memory, network)

### 1.2 Inventory Validation
- [ ] Verify all hosts are reachable
- [ ] Validate group structure
- [ ] Check variable precedence
- [ ] Test dynamic inventory scripts

## 2. Post-Upgrade Testing

### 2.1 Syntax Validation
```bash
# Check all playbooks
find . -name "*.yml" -o -name "*.yaml" | \\
    xargs -I {{}} ansible-playbook --syntax-check {{}}
```

### 2.2 Dry Run Testing
```bash
# Run playbooks in check mode
ansible-playbook playbook.yml --check --diff
```

### 2.3 Integration Testing
- [ ] Run playbooks in test environment
- [ ] Verify idempotency (run twice, second should have no changes)
- [ ] Test with various inventory configurations
- [ ] Validate handler execution
- [ ] Test error conditions and recovery

### 2.4 Performance Testing
- [ ] Compare execution times with baseline
- [ ] Monitor resource usage
- [ ] Test with production-like load
- [ ] Identify any performance regressions

## 3. Regression Testing

### 3.1 Module Testing
- [ ] Verify all modules work as expected
- [ ] Test deprecated module replacements
- [ ] Validate collection module paths

### 3.2 Feature Testing
- [ ] Test conditional execution (when/unless)
- [ ] Verify loops and iterations
- [ ] Test variable interpolation
- [ ] Validate facts gathering
- [ ] Test privilege escalation (become)

## 4. Acceptance Criteria

- All syntax checks pass
- All playbooks execute successfully
- Idempotency verified (no changes on second run)
- Performance within 10 percent of baseline
- No new errors or warnings
- All managed nodes respond correctly

## 5. Sign-Off

- [ ] Testing completed by: ________________
- [ ] Date: ________________
- [ ] Approved for production: ________________
"""

    return plan
