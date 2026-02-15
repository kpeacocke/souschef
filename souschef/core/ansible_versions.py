"""
Ansible and Python version compatibility data.

Data sources:
- ansible.com: https://docs.ansible.com/ansible/latest/reference_appendices/release_and_maintenance.html
- Red Hat AAP Lifecycle: https://access.redhat.com/support/policy/updates/ansible-automation-platform
- Official porting guides: https://docs.ansible.com/ansible/latest/porting_guides/

Last updated: February 8, 2026 (validated with official documentation)

This module contains the authoritative Ansible-Python compatibility matrix
and provides utilities for version checking, upgrade path planning, EOL status
verification, and AAP (Ansible Automation Platform) integration.

Architecture: Hybrid Static + AI-Driven
- Static compatibility matrix provides baseline and offline capability
- AI-driven functions can fetch latest data from Ansible docs dynamically
- Cached results reduce API calls while staying current

Note: Two versioning schemes exist:
1. ansible-core (2.x) - The framework/engine
2. Named Ansible (3.x+) - Community package with collections
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

# Ansible version data file name
_VERSION_DATA_FILENAME = "ansible_versions.json"


def _resolve_version_data_file() -> Path:
    """
    Resolve the path to the Ansible version data file.

    Returns:
        Path to ansible_versions.json.

    Raises:
        FileNotFoundError: If the package data file cannot be found.

    """
    # File is packaged at souschef/data/ansible_versions.json
    # This module is at souschef/core/ansible_versions.py, so go up one level
    module_path = Path(__file__).resolve()
    version_file = module_path.parents[1] / "data" / _VERSION_DATA_FILENAME

    if version_file.is_file():
        return version_file

    raise FileNotFoundError(
        f"Ansible version data file not found at {version_file}. "
        "Please ensure souschef/data/ansible_versions.json exists."
    )


@dataclass
class AnsibleVersion:
    """
    Ansible version information from compatibility matrix.

    Attributes:
        version: ansible-core version string (e.g., "2.16").
        named_version: Named Ansible version (e.g., "9.x") or None for older releases.
        release_date: Date when this version was released.
        eol_date: End-of-life date, or None if still supported.
        control_node_python: Python versions supported on control node.
        managed_node_python: Python versions supported on managed nodes.
        major_changes: Breaking changes introduced in this version.
        min_collection_versions: Minimum required versions for collections.
        known_issues: Known issues or warnings for this version.
        aap_versions: Compatible AAP versions (e.g., ["2.5", "2.6"]).

    """

    version: str
    named_version: str | None
    release_date: date
    eol_date: date | None
    control_node_python: list[str]
    managed_node_python: list[str]
    major_changes: list[str] = field(default_factory=list)
    min_collection_versions: dict[str, str] = field(default_factory=dict)
    known_issues: list[str] = field(default_factory=list)
    aap_versions: list[str] = field(default_factory=list)


def _load_version_data() -> dict[str, AnsibleVersion]:
    """
    Load Ansible version data from external JSON file.

    This replaces the previous hardcoded version matrix, making it easier
    to maintain and update version information without code changes.

    Returns:
        Dictionary mapping version strings to AnsibleVersion objects.

    """
    try:
        version_data_file = _resolve_version_data_file()
        with version_data_file.open() as f:
            data = json.load(f)

        versions: dict[str, AnsibleVersion] = {}
        for version_key, version_data in data["versions"].items():
            release_date_str = version_data["release_date"]
            eol_date_str = version_data.get("eol_date")

            versions[version_key] = AnsibleVersion(
                version=version_key,
                named_version=version_data.get("named_version"),
                release_date=datetime.strptime(release_date_str, "%Y-%m-%d").date(),
                eol_date=(
                    datetime.strptime(eol_date_str, "%Y-%m-%d").date()
                    if eol_date_str
                    else None
                ),
                control_node_python=version_data["control_node_python"],
                managed_node_python=version_data["managed_node_python"],
                major_changes=version_data.get("major_changes", []),
                min_collection_versions=version_data.get("min_collection_versions", {}),
                known_issues=version_data.get("known_issues", []),
                aap_versions=version_data.get("aap_versions", []),
            )

        return versions
    except (FileNotFoundError, KeyError, ValueError) as e:
        # Fallback to empty dict if data file not found
        # In production, you'd want to handle this more gracefully
        raise RuntimeError(f"Failed to load Ansible version data: {e}") from e


# Load version data from external JSON file
# This makes it easier to update version information without code changes
ANSIBLE_VERSIONS: dict[str, AnsibleVersion] = _load_version_data()


def _parse_version(version_str: str) -> tuple[int, ...]:
    """
    Parse a version string into a tuple of integers for comparison.

    This handles semantic versioning (e.g., "2.9", "2.10.0", "2.20").
    Non-numeric suffixes (rc, beta, etc.) are ignored for comparison.

    Args:
        version_str: Version string (e.g., "2.20", "2.10.0rc1").

    Returns:
        Tuple of integers for comparison. Example: "2.10.0rc1" -> (2, 10, 0)

    """
    parts = []
    for part in version_str.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            # Stop at non-numeric part (e.g., "2.10rc1" -> (2, 10))
            break
    return tuple(parts)


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
    current_version: str, target_version: str
) -> list[str]:
    """Calculate intermediate versions for upgrade path."""
    current_key = _parse_version(current_version)
    target_key = _parse_version(target_version)
    if current_key >= target_key:
        return []

    sorted_versions = sorted(ANSIBLE_VERSIONS.keys(), key=_parse_version)
    return [
        version
        for version in sorted_versions
        if current_key < _parse_version(version) < target_key
    ]


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
    target_version: str,
    current: AnsibleVersion,
    intermediate_versions: list[str],
    python_upgrade_needed: bool,
) -> tuple[str, list[str]]:
    """Assess risk level and factors for upgrade."""
    risk_factors: list[str] = []
    is_upgrade = _parse_version(target_version) > _parse_version(current_version)

    if current_version.startswith("2.9") and is_upgrade:
        risk_factors.append("Upgrading from 2.9 (collections split required)")
    if len(intermediate_versions) >= 3:
        risk_factors.append(
            f"Large version jump ({len(intermediate_versions)} intermediate versions)"
        )
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
    current_version: str,
    target_version: str,
    ai_provider: str = "anthropic",
    api_key: str = "",
    use_ai: bool = False,
    use_cache: bool = True,
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
        ai_provider: AI provider to use when use_ai is enabled.
        api_key: API key for AI provider.
        use_ai: Whether to use AI data for compatibility checks.
        use_cache: Whether to use cached AI results.

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

    intermediate_versions = _calculate_intermediate_versions(
        current_version, target_version
    )
    breaking_changes = _collect_breaking_changes(intermediate_versions, target_version)

    ai_data: dict | None = None
    if use_ai and api_key:
        ai_data = fetch_ansible_versions_with_ai(
            ai_provider=ai_provider,
            api_key=api_key,
            use_cache=use_cache,
        )

    current_python = current.control_node_python
    target_python = target.control_node_python
    if ai_data:
        current_python = ai_data.get(current_version, {}).get(
            "control_node_python", current_python
        )
        target_python = ai_data.get(target_version, {}).get(
            "control_node_python", target_python
        )

    python_upgrade_needed = not any(py in target_python for py in current_python)

    risk_level, risk_factors = _assess_upgrade_risk(
        current_version,
        target_version,
        current,
        intermediate_versions,
        python_upgrade_needed,
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
        "current_python": current_python,
        "required_python": target_python,
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
    versions = sorted(ANSIBLE_VERSIONS.keys(), key=_parse_version)
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
    return sorted(supported, key=_parse_version, reverse=True)


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

    control_min = min(version_info.control_node_python, key=_parse_version)
    managed_min = min(version_info.managed_node_python, key=_parse_version)

    return (control_min, managed_min)


def get_ansible_core_version(named_version: str) -> str | None:
    """
    Convert Named Ansible version to ansible-core version.

    Args:
        named_version: Named Ansible version (e.g., "9", "9.x", "13.x").

    Returns:
        ansible-core version string (e.g., "2.16") or None if not found.

    Examples:
        >>> get_ansible_core_version("9.x")
        "2.16"
        >>> get_ansible_core_version("13")
        "2.20"

    """
    # Normalize named version to x.x format
    normalized = named_version.strip().rstrip(".x")

    for version, info in ANSIBLE_VERSIONS.items():
        if info.named_version and info.named_version.rstrip(".x") == normalized:
            return version

    return None


def get_named_ansible_version(core_version: str) -> str | None:
    """
    Convert ansible-core version to Named Ansible version.

    Args:
        core_version: ansible-core version (e.g., "2.16", "2.20").

    Returns:
        Named Ansible version string (e.g., "9.x") or None if predates naming scheme.

    Examples:
        >>> get_named_ansible_version("2.16")
        "9.x"
        >>> get_named_ansible_version("2.9")
        None  # Predates named versioning

    """
    if core_version in ANSIBLE_VERSIONS:
        return ANSIBLE_VERSIONS[core_version].named_version

    return None


def get_aap_compatible_versions(ansible_core_version: str) -> list[str]:
    """
    Get Ansible Automation Platform versions compatible with ansible-core version.

    Args:
        ansible_core_version: ansible-core version (e.g., "2.16").

    Returns:
        List of compatible AAP versions (e.g., ["2.5", "2.6"]) or empty list.

    Examples:
        >>> get_aap_compatible_versions("2.16")
        ["2.5", "2.6"]
        >>> get_aap_compatible_versions("2.15")
        ["2.4"]

    """
    if ansible_core_version in ANSIBLE_VERSIONS:
        return ANSIBLE_VERSIONS[ansible_core_version].aap_versions

    return []


def get_recommended_core_version_for_aap(aap_version: str) -> str | None:
    """
    Get recommended ansible-core version for AAP version.

    Args:
        aap_version: AAP version (e.g., "2.5", "2.6").

    Returns:
        Recommended ansible-core version or None if not found.

    Examples:
        >>> get_recommended_core_version_for_aap("2.6")
        "2.16"  # Default for AAP 2.6
        >>> get_recommended_core_version_for_aap("2.5")
        "2.16"  # Default for AAP 2.5

    """
    # Iterate through versions to find those compatible with the AAP version
    # Return the newest one as the recommendation
    compatible: list[str] = []

    for version, info in ANSIBLE_VERSIONS.items():
        if aap_version in info.aap_versions:
            compatible.append(version)

    if compatible:
        # Use tuple-based comparison for semantic versioning
        # Examples: "2.20" > "2.16", "2.10.0" > "2.9.1"
        return max(compatible, key=_parse_version)

    return None


def format_version_display(
    core_version: str, include_named: bool = True, include_aap: bool = False
) -> str:
    """
    Format version string for display with multiple schemes.

    Args:
        core_version: ansible-core version (e.g., "2.16").
        include_named: Include Named Ansible version if available.
        include_aap: Include AAP compatibility information.

    Returns:
        Formatted version string for display.

    Examples:
        >>> format_version_display("2.16")
        "ansible-core 2.16 (Ansible 9.x)"
        >>> format_version_display("2.16", include_aap=True)
        "ansible-core 2.16 (Ansible 9.x, AAP 2.5/2.6)"
        >>> format_version_display("2.9")
        "ansible-core 2.9"

    """
    parts = [f"ansible-core {core_version}"]

    if include_named:
        named = get_named_ansible_version(core_version)
        if named:
            parts.append(f"Ansible {named}")

    if include_aap:
        aap_versions = get_aap_compatible_versions(core_version)
        if aap_versions:
            aap_str = "/".join(aap_versions)
            parts.append(f"AAP {aap_str}")

    if len(parts) == 1:
        return parts[0]

    return f"{parts[0]} ({', '.join(parts[1:])})"


# =============================================================================
# AI-DRIVEN VERSION COMPATIBILITY (MCP Best Practice)
# =============================================================================
# The following functions provide AI-driven compatibility checking with
# fallback to static data. This follows MCP best practices by leveraging
# AI for dynamic knowledge retrieval rather than hardcoding data.


# Cache configuration
_CACHE_DIR = Path.home() / ".cache" / "souschef"
_CACHE_FILE = _CACHE_DIR / "ansible_versions_ai_cache.json"
_CACHE_DURATION_DAYS = 7  # Refresh weekly


def _get_cache_path() -> Path:
    """Get cache file path, creating directory if needed."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_FILE


def _load_ai_cache() -> dict | None:
    """
    Load cached AI version data if available and fresh.

    Returns:
        Cached data dict or None if cache is stale/missing.

    """
    try:
        cache_path = _get_cache_path()
        if not cache_path.exists():  # NOSONAR
            return None

        with cache_path.open() as f:
            cache_data = json.load(f)

        # Check if cache is fresh (within _CACHE_DURATION_DAYS)
        cached_time = datetime.fromisoformat(cache_data.get("cached_at", ""))
        age = datetime.now() - cached_time

        if age > timedelta(days=_CACHE_DURATION_DAYS):
            return None  # Cache is stale

        versions: dict | None = cache_data.get("versions", None)
        return versions
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def _save_ai_cache(versions_data: dict) -> None:
    """
    Save AI-fetched version data to cache.

    Args:
        versions_data: Version data to cache.

    """
    try:
        cache_path = _get_cache_path()
        cache_data = {
            "cached_at": datetime.now().isoformat(),
            "versions": versions_data,
        }

        with cache_path.open("w") as f:
            json.dump(cache_data, f, indent=2)
    except (OSError, TypeError):
        pass  # Silent fail - caching is optional


def _get_ai_prompt() -> str:
    """Get prompt for AI version data fetching."""
    return """Please provide the latest Ansible version compatibility \
matrix in JSON format.
Include the following versions: 2.15, 2.16, 2.17, 2.18, 2.19, 2.20, \
and any newer versions.

For each version, provide:
- control_node_python: List of supported Python versions for control nodes
- managed_node_python: List of supported Python versions for managed nodes
- release_date: Release date in YYYY-MM-DD format
- eol_date: End of life date in YYYY-MM-DD format (if known)
- major_changes: List of major changes in this version
- named_version: Named version (e.g., "9.x" for 2.16)
- aap_versions: List of compatible AAP versions

Use the official Ansible documentation as the source. Return ONLY valid \
JSON, no markdown formatting.

Example format:
{
  "2.20": {
    "control_node_python": ["3.12", "3.13", "3.14"],
    "managed_node_python": ["3.9", "3.10", "3.11", "3.12", "3.13", "3.14"],
    "release_date": "2025-11-03",
    "eol_date": "2027-05-31",
    "major_changes": ["Python 3.12+ required for control node"],
    "named_version": "13.x",
    "aap_versions": []
  }
}"""


def _call_ai_provider(
    ai_provider: str, api_key: str, model: str, prompt: str
) -> str | None:
    """Call AI provider and return response text."""
    try:
        if ai_provider.lower() == "anthropic":
            import anthropic

            anthropic_client = anthropic.Anthropic(api_key=api_key)
            anthropic_response = anthropic_client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            # Extract text from first content block
            if anthropic_response.content and len(anthropic_response.content) > 0:
                first_block = anthropic_response.content[0]
                # Use getattr for type safety
                text_content: str | None = getattr(first_block, "text", None)
                if text_content:
                    return text_content
            return None

        if ai_provider.lower() == "openai":
            import openai

            openai_client = openai.OpenAI(api_key=api_key)
            openai_response = openai_client.chat.completions.create(
                model=model or "gpt-4",
                messages=[{"role": "user", "content": prompt}],
            )
            return openai_response.choices[0].message.content or ""

        if ai_provider.lower() == "watson":
            # Watson implementation would go here
            return None

        return None
    except (ImportError, AttributeError, KeyError):
        return None


def _parse_ai_response(ai_response: str) -> dict | None:
    """Parse and validate AI response JSON."""
    try:
        # Remove markdown code fences if present
        ai_response = ai_response.strip()
        if ai_response.startswith("```json"):
            ai_response = ai_response[7:]
        if ai_response.startswith("```"):
            ai_response = ai_response[3:]
        if ai_response.endswith("```"):
            ai_response = ai_response[:-3]

        versions_data = json.loads(ai_response.strip())

        # Validate structure
        if not isinstance(versions_data, dict):
            return None

        # Basic validation - ensure keys are version strings
        for version_key in versions_data:
            if not re.match(r"^\d+\.\d+", version_key):
                return None

        return versions_data
    except (json.JSONDecodeError, KeyError):
        return None


def fetch_ansible_versions_with_ai(
    ai_provider: str = "anthropic",
    api_key: str = "",
    model: str = "claude-3-5-sonnet-20241022",
    use_cache: bool = True,
) -> dict[str, dict] | None:
    """
    [EXPERIMENTAL] Fetch latest Ansible version compatibility data using AI.

    ⚠️  WARNING: This is an experimental feature not fully integrated into
    the upgrade workflow. The static version matrix loaded from JSON is the
    current production implementation.

    This function queries AI to fetch the latest version information from
    Ansible documentation, falling back to cached data if AI is unavailable.

    Status:
        - ✓ Optional integration into calculate_upgrade_path() when enabled
        - ✗ Not used by default in assessment workflows
        - ✗ Incomplete integration tests
        - ✓ Caching implemented
        - ✓ Multiple provider support (Anthropic, OpenAI)

    Args:
        ai_provider: AI provider to use (anthropic, openai, watson).
        api_key: API key for the AI provider.
        model: AI model to use.
        use_cache: Whether to use cached data if available.

    Returns:
        Dictionary mapping version strings to compatibility data, or None if
        AI and cache are unavailable.

    Example:
        >>> # Manual invocation required - not automatic
        >>> data = fetch_ansible_versions_with_ai(
        ...     ai_provider="anthropic",
        ...     api_key="sk-..."
        ... )
        >>> if data:
        ...     print(data["2.20"]["control_node_python"])
        ["3.12", "3.13", "3.14"]

    """
    # Try cache first if enabled
    if use_cache:
        cached = _load_ai_cache()
        if cached:
            return cached

    # Validate inputs
    if not api_key:
        return None

    supported_providers = ["anthropic", "openai", "watson"]
    if ai_provider not in supported_providers:
        return None

    # Get prompt and call AI
    prompt = _get_ai_prompt()
    ai_response = _call_ai_provider(ai_provider, api_key, model, prompt)

    if not ai_response:
        return None

    # Parse and validate response
    versions_data = _parse_ai_response(ai_response)

    if versions_data:
        # Cache the successful result
        _save_ai_cache(versions_data)

    return versions_data


def get_python_compatibility_with_ai(
    ansible_version: str,
    node_type: str = "control",
    ai_provider: str = "anthropic",
    api_key: str = "",
    use_cache: bool = True,
) -> list[str]:
    """
    [EXPERIMENTAL] Get Python compatibility using AI with static fallback.

    ⚠️  WARNING: Experimental AI feature. Always falls back to static data
    from ANSIBLE_VERSIONS if AI unavailable.

    This function tries to fetch the latest compatibility data from AI,
    falling back to the static ANSIBLE_VERSIONS matrix if AI is unavailable.

    Args:
        ansible_version: Ansible version (e.g., "2.16").
        node_type: Either "control" or "managed".
        ai_provider: AI provider to use.
        api_key: API key for the AI provider.
        use_cache: Whether to use cached AI results.

    Returns:
        List of compatible Python version strings.

    Raises:
        ValueError: If ansible_version is unknown or node_type is invalid.

    Example:
        >>> # Tries AI first, falls back to static data
        >>> versions = get_python_compatibility_with_ai("2.20", api_key="...")
        >>> print(versions)
        ["3.12", "3.13", "3.14"]

    """
    # Try AI-enhanced lookup
    if api_key:
        ai_data = fetch_ansible_versions_with_ai(
            ai_provider=ai_provider, api_key=api_key, use_cache=use_cache
        )
        if ai_data and ansible_version in ai_data:
            version_data = ai_data[ansible_version]
            if node_type == "control":
                control_python: list[str] = version_data.get("control_node_python", [])
                return control_python
            if node_type == "managed":
                managed_python: list[str] = version_data.get("managed_node_python", [])
                return managed_python

    # Fallback to static data
    return get_python_compatibility(ansible_version, node_type)


def get_latest_version_with_ai(
    api_key: str = "",
    use_cache: bool = True,
) -> str:
    """
    [EXPERIMENTAL] Get the latest Ansible version using AI with static fallback.

    ⚠️  WARNING: Experimental AI feature. Falls back to static data if unavailable.

    Args:
        api_key: API key for the AI provider.
        use_cache: Whether to use cached AI results.

    Returns:
        Latest Ansible version string.

    Example:
        >>> # Tries AI first, falls back to static ANSIBLE_VERSIONS
        >>> latest = get_latest_version_with_ai(api_key="...")
        >>> print(latest)
        "2.20"

    """
    # Try AI-enhanced lookup
    if api_key:
        ai_data = fetch_ansible_versions_with_ai(api_key=api_key, use_cache=use_cache)
        if ai_data:
            versions = sorted(ai_data.keys(), key=_parse_version)
            if versions:
                return versions[-1]

    # Fallback to static data
    return get_latest_version()
