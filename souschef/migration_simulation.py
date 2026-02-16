"""
Migration simulation with version-aware mocking for Chef→Ansible conversions.

This module provides infrastructure for simulating Chef to Ansible/AWX/AAP migrations
across all supported version combinations, with realistic API mocking for each version.

Supported Version Combinations:
- Chef Origin: 12.19.36, 14.15.6, 15.10.91
- AWX Destination: 20.x, 21.x-22.x, 23.x-24.6.1
- AAP Destination: 2.4+
- Tower Destination: 3.8.x (legacy)
"""

from dataclasses import dataclass, field
from typing import Any, Literal

# Version combination definitions
CHEF_VERSIONS = ["12.19.36", "14.15.6", "15.10.91"]
PLATFORM_VERSIONS = {
    "tower": ["3.8.5"],
    "awx": ["20.1.0", "21.0.0", "22.0.0", "24.6.1"],
    "aap": ["2.4.0"],
}

# Authentication protocol by Chef version
CHEF_AUTH_PROTOCOLS = {
    "12.19.36": ["1.0", "1.3"],  # SHA-1 and SHA-256
    "14.15.6": ["1.3"],  # SHA-256 only (SHA-1 deprecated)
    "15.10.91": ["1.3"],  # SHA-256 only (SHA-1 removed)
}

# Execution model by platform/version
EXECUTION_MODELS = {
    "tower-3.8.5": "custom_virtualenv",  # Legacy: virtualenv
    "awx-20.1.0": "custom_virtualenv",  # Pre-EE: virtualenv
    "awx-21.0.0": "execution_environment",  # EE transition
    "awx-22.0.0": "execution_environment",  # EE standard
    "awx-24.6.1": "execution_environment",  # EE required
    "aap-2.4.0": "execution_environment",  # EE required
}

# Ansible version requirements by platform
ANSIBLE_VERSIONS = {
    "tower-3.8.5": "2.9.0",
    "awx-20.1.0": "2.10.0",
    "awx-21.0.0": "2.11.0",
    "awx-22.0.0": "2.12.0",
    "awx-24.6.1": "2.16.0",
    "aap-2.4.0": "2.15.0",
}

# API endpoint availability by platform/version
AVAILABLE_ENDPOINTS = {
    "tower-3.8.5": [
        "/api/v2/inventories/",
        "/api/v2/job_templates/",
        "/api/v2/projects/",
        "/api/v2/credentials/",
        "/api/v2/groups/",
        "/api/v2/hosts/",
    ],
    "awx-20.1.0": [
        "/api/v2/inventories/",
        "/api/v2/job_templates/",
        "/api/v2/projects/",
        "/api/v2/credentials/",
        "/api/v2/groups/",
        "/api/v2/hosts/",
        "/api/v2/custom_virtualenvs/",
    ],
    "awx-21.0.0": [
        "/api/v2/inventories/",
        "/api/v2/job_templates/",
        "/api/v2/projects/",
        "/api/v2/credentials/",
        "/api/v2/groups/",
        "/api/v2/hosts/",
        "/api/v2/execution_environments/",
        "/api/v2/custom_virtualenvs/",  # Deprecated
    ],
    "awx-22.0.0": [
        "/api/v2/inventories/",
        "/api/v2/job_templates/",
        "/api/v2/projects/",
        "/api/v2/credentials/",
        "/api/v2/groups/",
        "/api/v2/hosts/",
        "/api/v2/execution_environments/",
    ],
    "awx-24.6.1": [
        "/api/v2/inventories/",
        "/api/v2/job_templates/",
        "/api/v2/projects/",
        "/api/v2/credentials/",
        "/api/v2/groups/",
        "/api/v2/hosts/",
        "/api/v2/execution_environments/",
        "/api/v2/mesh_visualizer/",
    ],
    "aap-2.4.0": [
        "/api/v2/inventories/",
        "/api/v2/job_templates/",
        "/api/v2/projects/",
        "/api/v2/credentials/",
        "/api/v2/groups/",
        "/api/v2/hosts/",
        "/api/v2/execution_environments/",
        "/api/v2/instances/",
        "/api/v2/mesh_visualizer/",
        "/api/v2/content_signing/",
    ],
}


@dataclass
class MigrationSimulationConfig:
    """Configuration for a Chef→Ansible migration simulation."""

    chef_version: str
    target_platform: Literal["tower", "awx", "aap"]
    target_version: str
    chef_auth_protocol: str = ""
    execution_environment_id: int = 42
    inventory_id: int = 1
    project_id: int = 1
    fips_mode: bool = False
    content_signing: bool = False
    mock_response_format: Literal["json", "yaml"] = "json"
    extra_vars: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and configure the simulation."""
        # Validate Chef version
        if self.chef_version not in CHEF_VERSIONS:
            raise ValueError(
                f"Invalid Chef version {self.chef_version}. "
                f"Supported: {', '.join(CHEF_VERSIONS)}"
            )

        # Validate target platform/version
        if self.target_platform not in PLATFORM_VERSIONS:
            raise ValueError(
                f"Invalid target platform {self.target_platform}. "
                f"Supported: {', '.join(PLATFORM_VERSIONS.keys())}"
            )

        if self.target_version not in PLATFORM_VERSIONS[self.target_platform]:
            raise ValueError(
                f"Invalid {self.target_platform} version {self.target_version}. "
                f"Supported: {', '.join(PLATFORM_VERSIONS[self.target_platform])}"
            )

        # Set default auth protocol if not specified
        if not self.chef_auth_protocol:
            self.chef_auth_protocol = CHEF_AUTH_PROTOCOLS[self.chef_version][-1]

        # Validate Chef auth protocol
        if self.chef_auth_protocol not in CHEF_AUTH_PROTOCOLS[self.chef_version]:
            raise ValueError(
                f"Invalid auth protocol {self.chef_auth_protocol} "
                f"for Chef {self.chef_version}. "
                f"Supported: {', '.join(CHEF_AUTH_PROTOCOLS[self.chef_version])}"
            )

        # AAP requires content signing
        if self.target_platform == "aap":
            self.content_signing = True

    @property
    def execution_model(self) -> str:
        """Get execution model (virtualenv vs execution_environment) for this config."""
        key = f"{self.target_platform}-{self.target_version}"
        return EXECUTION_MODELS.get(key, "execution_environment")

    @property
    def ansible_version(self) -> str:
        """Get required Ansible version for this config."""
        key = f"{self.target_platform}-{self.target_version}"
        return ANSIBLE_VERSIONS.get(key, "2.15.0")

    @property
    def platform_key(self) -> str:
        """Get platform key for lookups."""
        return f"{self.target_platform}-{self.target_version}"

    @property
    def available_endpoints(self) -> list[str]:
        """Get available API endpoints for this target platform/version."""
        return AVAILABLE_ENDPOINTS.get(self.platform_key, [])

    def get_job_template_structure(self) -> dict[str, Any]:
        """Get the expected job template structure for this version."""
        base = {
            "name": "placeholder",
            "job_type": "run",
            "inventory": self.inventory_id,
            "project": self.project_id,
            "playbook": "placeholder.yml",
            "extra_vars": self.extra_vars,
            "verbosity": 1,
        }

        # Add execution model field based on version
        if self.execution_model == "execution_environment":
            base["execution_environment"] = self.execution_environment_id
        else:
            base["custom_virtualenv"] = "/var/lib/awx/venv/ansible"

        # Add AAP-specific features
        if self.target_platform == "aap":
            base["content_signing"] = self.content_signing

        # Add mesh features for newer versions
        if (
            self.target_platform in ("awx", "aap")
            and int(self.target_version.split(".")[0]) >= 24
        ):
            base["mesh_mode"] = "enabled"

        return base

    def get_mock_response_headers(self) -> dict[str, str]:
        """Get appropriate mock response headers for this target version."""
        headers = {"Content-Type": "application/json"}

        if self.target_platform == "tower":
            headers["Server"] = f"Ansible Tower {self.target_version}"
            headers["X-Ansible-Cost"] = "5"
        elif self.target_platform == "awx":
            headers["Server"] = f"AWX {self.target_version}"
            headers["X-Ansible-Cost"] = "10"
        elif self.target_platform == "aap":
            headers["Server"] = f"Ansible Automation Platform {self.target_version}"
            headers["X-Ansible-Cost"] = "15"

        return headers


def get_all_version_combinations() -> list[dict[str, str]]:
    """
    Get all valid Chef→Platform version combinations.

    Returns:
        List of dicts with chef_version, target_platform, target_version.

    """
    combinations = []
    for chef_ver in CHEF_VERSIONS:
        for platform, versions in PLATFORM_VERSIONS.items():
            for plat_ver in versions:
                combinations.append(
                    {
                        "chef_version": chef_ver,
                        "target_platform": platform,
                        "target_version": plat_ver,
                    }
                )
    return combinations


def create_simulation_config(
    chef_version: str,
    target_platform: str,
    target_version: str,
    **kwargs: Any,
) -> MigrationSimulationConfig:
    """
    Create a migration simulation configuration with sensible defaults.

    Args:
        chef_version: Source Chef version (12.19.36, 14.15.6, 15.10.91).
        target_platform: Target platform (tower, awx, aap).
        target_version: Target platform version.
        **kwargs: Additional configuration options.

    Returns:
        MigrationSimulationConfig instance.

    Raises:
        ValueError: If version combination is invalid.

    """
    return MigrationSimulationConfig(
        chef_version=chef_version,
        target_platform=target_platform,  # type: ignore[arg-type]
        target_version=target_version,
        **kwargs,
    )


def validate_version_combination(
    chef_version: str,
    target_platform: str,
    target_version: str,
) -> dict[str, Any]:
    """
    Validate a version combination and return compatibility info.

    Args:
        chef_version: Source Chef version.
        target_platform: Target platform.
        target_version: Target platform version.

    Returns:
        Dict with validation results and compatibility details.

    Raises:
        ValueError: If version combination is invalid.

    """
    config = MigrationSimulationConfig(
        chef_version=chef_version,
        target_platform=target_platform,  # type: ignore[arg-type]
        target_version=target_version,
    )

    return {
        "valid": True,
        "chef_version": config.chef_version,
        "auth_protocol": config.chef_auth_protocol,
        "target_platform": config.target_platform,
        "target_version": config.target_version,
        "execution_model": config.execution_model,
        "ansible_version": config.ansible_version,
        "available_endpoints": config.available_endpoints,
        "job_template_structure": config.get_job_template_structure(),
        "requires_fips": config.chef_version == "15.10.91",
        "requires_signing": config.target_platform == "aap",
    }
