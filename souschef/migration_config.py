"""
Migration configuration and questionnaire system for Chef to Ansible conversions.

This module provides an interactive configuration system for gathering migration
requirements and preferences from users.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

import click


class DeploymentTarget(Enum):
    """Target deployment platform for Ansible."""

    APP = "app"  # Ansible App
    AWX = "awx"  # AWX/Ansible Tower
    AAP = "aap"  # Ansible Automation Platform
    NATIVE = "native"  # Native Ansible (no platform)


class MigrationStandard(Enum):
    """Migration strategy."""

    STANDARD = "standard"  # Full structured migration
    FLAT = "flat"  # Flat playbook approach
    HYBRID = "hybrid"  # Mix of structured and flat


class ValidationTool(Enum):
    """Post-migration validation tools."""

    TOX_ANSIBLE = "tox-ansible"
    MOLECULE = "molecule"
    ANSIBLE_LINT = "ansible-lint"
    CUSTOM = "custom"


@dataclass
class MigrationConfig:
    """Complete migration configuration."""

    deployment_target: DeploymentTarget = DeploymentTarget.AWX
    migration_standard: MigrationStandard = MigrationStandard.STANDARD
    inventory_source: str = "chef-server"  # Chef Server or other
    validate_post_migration: bool = True
    validation_tools: list[ValidationTool] = field(
        default_factory=lambda: [
            ValidationTool.ANSIBLE_LINT,
            ValidationTool.MOLECULE,
        ]
    )
    iterate_until_clean: bool = True
    target_python_version: str = "3.9"
    target_ansible_version: str = "2.13"
    preserve_handlers: bool = True
    preserve_node_attributes: bool = True
    convert_templates_to_jinja2: bool = True
    generate_pre_checks: bool = True
    generate_post_checks: bool = True
    documentation_level: str = "comprehensive"  # minimal|standard|comprehensive
    custom_settings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        data = asdict(self)
        # Convert enums to strings
        data["deployment_target"] = self.deployment_target.value
        data["migration_standard"] = self.migration_standard.value
        data["validation_tools"] = [tool.value for tool in self.validation_tools]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MigrationConfig":
        """Create config from dictionary."""
        # Convert string values back to enums
        if isinstance(data.get("deployment_target"), str):
            data["deployment_target"] = DeploymentTarget(data["deployment_target"])
        if isinstance(data.get("migration_standard"), str):
            data["migration_standard"] = MigrationStandard(data["migration_standard"])
        if isinstance(data.get("validation_tools"), list):
            data["validation_tools"] = [
                ValidationTool(tool) if isinstance(tool, str) else tool
                for tool in data["validation_tools"]
            ]
        return cls(**data)


class MigrationQuestionnaire:
    """Interactive questionnaire for gathering migration requirements."""

    def __init__(self):
        """Initialise the questionnaire."""
        self.config = MigrationConfig()

    def ask_deployment_target(self) -> None:
        """Ask about target deployment platform."""
        click.echo("\n=== Deployment Target ===")
        click.echo("Where will you deploy the Ansible playbooks?")
        click.echo("1. Ansible App (AAP Lite)")
        click.echo("2. AWX (Open-source Tower)")
        click.echo("3. Ansible Automation Platform (AAP)")
        click.echo("4. Native Ansible (no platform)")

        choice = input("Select option (1-4, default=2): ").strip() or "2"

        target_map = {
            "1": DeploymentTarget.APP,
            "2": DeploymentTarget.AWX,
            "3": DeploymentTarget.AAP,
            "4": DeploymentTarget.NATIVE,
        }

        self.config.deployment_target = target_map.get(choice, DeploymentTarget.AWX)

    def ask_migration_strategy(self) -> None:
        """Ask about migration strategy."""
        click.echo("\n=== Migration Strategy ===")
        click.echo("What migration approach would you prefer?")
        click.echo("1. Standard (recommended): Structured with roles and handlers")
        click.echo("2. Flat: Simple single-playbook approach")
        click.echo("3. Hybrid: Mix of structured and flat where appropriate")

        choice = input("Select option (1-3, default=1): ").strip() or "1"

        strategy_map = {
            "1": MigrationStandard.STANDARD,
            "2": MigrationStandard.FLAT,
            "3": MigrationStandard.HYBRID,
        }

        self.config.migration_standard = strategy_map.get(
            choice, MigrationStandard.STANDARD
        )

    def ask_inventory_source(self) -> None:
        """Ask about inventory source."""
        click.echo("\n=== Inventory Source ===")
        click.echo("Where should inventory be sourced from?")
        click.echo("1. Chef Server (existing)")
        click.echo("2. Manual inventory")
        click.echo("3. Cloud provider (AWS/Azure/GCP)")

        choice = input("Select option (1-3, default=1): ").strip() or "1"

        source_map = {
            "1": "chef-server",
            "2": "manual",
            "3": "cloud-provider",
        }

        self.config.inventory_source = source_map.get(choice, "chef-server")

    def ask_validation_strategy(self) -> None:
        """Ask about post-migration validation."""
        click.echo("\n=== Post-Migration Validation ===")
        click.echo("Would you like to validate the migration outcome?")
        validate = input("Validate playbooks? (Y/n, default=Y): ").strip().lower()
        self.config.validate_post_migration = validate != "n"

        if self.config.validate_post_migration:
            click.echo("\nSelect validation tools to use:")
            click.echo("1. ansible-lint (syntax/best practices)")
            click.echo("2. molecule (functional testing)")
            click.echo("3. tox-ansible (compatibility testing)")
            tools_str = (
                input("Enter tool numbers comma-separated (default=1,2): ").strip()
                or "1,2"
            )
            tools_list = []
            for choice in tools_str.split(","):
                choice = choice.strip()
                tool_map = {
                    "1": ValidationTool.ANSIBLE_LINT,
                    "2": ValidationTool.MOLECULE,
                    "3": ValidationTool.TOX_ANSIBLE,
                }
                if choice in tool_map:
                    tools_list.append(tool_map[choice])

            self.config.validation_tools = tools_list or [
                ValidationTool.ANSIBLE_LINT,
                ValidationTool.MOLECULE,
            ]

            click.echo("\nIterate until all validation checks pass?")
            iterate = input("Iterate until clean? (Y/n, default=Y): ").strip().lower()
            self.config.iterate_until_clean = iterate != "n"

    def ask_python_ansible_versions(self) -> None:
        """Ask about target Python and Ansible versions."""
        click.echo("\n=== Target Versions ===")
        python_version = input("Target Python version (default=3.9): ").strip() or "3.9"
        self.config.target_python_version = python_version

        ansible_version = (
            input("Target Ansible version (default=2.13): ").strip() or "2.13"
        )
        self.config.target_ansible_version = ansible_version

    def ask_preservation_options(self) -> None:
        """Ask about what Chef constructs to preserve."""
        click.echo("\n=== Migration Preferences ===")

        handlers = input("Preserve Chef handlers? (Y/n, default=Y): ").strip().lower()
        self.config.preserve_handlers = handlers != "n"

        attributes = (
            input("Preserve node attributes? (Y/n, default=Y): ").strip().lower()
        )
        self.config.preserve_node_attributes = attributes != "n"

        templates = (
            input("Convert ERB templates to Jinja2? (Y/n, default=Y): ").strip().lower()
        )
        self.config.convert_templates_to_jinja2 = templates != "n"

    def ask_checks_and_documentation(self) -> None:
        """Ask about pre/post-checks and documentation."""
        click.echo("\n=== Checks & Documentation ===")

        pre_checks = (
            input("Generate pre-flight checks? (Y/n, default=Y): ").strip().lower()
        )
        self.config.generate_pre_checks = pre_checks != "n"

        post_checks = (
            input("Generate post-execution checks? (Y/n, default=Y): ").strip().lower()
        )
        self.config.generate_post_checks = post_checks != "n"

        click.echo("\nDocumentation detail level:")
        click.echo("1. Minimal (basic comments only)")
        click.echo("2. Standard (moderate documentation)")
        click.echo("3. Comprehensive (extensive documentation)")

        doc_choice = (
            input("Select documentation level (1-3, default=3): ").strip() or "3"
        )

        doc_map = {"1": "minimal", "2": "standard", "3": "comprehensive"}
        self.config.documentation_level = doc_map.get(doc_choice, "comprehensive")

    def run_interactive(self) -> MigrationConfig:
        """Run the full interactive questionnaire."""
        click.echo("\n" + "=" * 60)
        click.echo("SousChef Migration Configuration Questionnaire")
        click.echo("=" * 60)
        click.echo("\nThis questionnaire will help configure your Chef to Ansible")
        click.echo("migration based on your specific requirements.\n")

        self.ask_deployment_target()
        self.ask_migration_strategy()
        self.ask_inventory_source()
        self.ask_validation_strategy()
        self.ask_python_ansible_versions()
        self.ask_preservation_options()
        self.ask_checks_and_documentation()

        click.echo("\n" + "=" * 60)
        click.echo("Configuration Complete!")
        click.echo("=" * 60)
        self._print_summary()

        return self.config

    def _print_summary(self) -> None:
        """Print configuration summary."""
        click.echo("\n=== Configuration Summary ===")
        click.echo(f"Deployment Target: {self.config.deployment_target.value}")
        click.echo(f"Migration Standard: {self.config.migration_standard.value}")
        click.echo(f"Inventory Source: {self.config.inventory_source}")
        click.echo(f"Validate Post-Migration: {self.config.validate_post_migration}")
        if self.config.validate_post_migration:
            tools = ", ".join([t.value for t in self.config.validation_tools])
            click.echo(f"Validation Tools: {tools}")
            click.echo(f"Iterate Until Clean: {self.config.iterate_until_clean}")
        click.echo(f"Target Python: {self.config.target_python_version}")
        click.echo(f"Target Ansible: {self.config.target_ansible_version}")
        click.echo(f"Preserve Handlers: {self.config.preserve_handlers}")
        click.echo(f"Preserve Attributes: {self.config.preserve_node_attributes}")
        click.echo(f"Convert Templates: {self.config.convert_templates_to_jinja2}")
        click.echo(f"Pre-flight Checks: {self.config.generate_pre_checks}")
        click.echo(f"Post-execution Checks: {self.config.generate_post_checks}")
        click.echo(f"Documentation Level: {self.config.documentation_level}")


def get_migration_config_from_user() -> MigrationConfig:
    """Get migration configuration from interactive user input."""
    questionnaire = MigrationQuestionnaire()
    return questionnaire.run_interactive()


def get_migration_config_from_cli_args(args: dict[str, Any]) -> MigrationConfig:
    """Create migration config from CLI arguments."""
    config = MigrationConfig()

    if "deployment_target" in args:
        config.deployment_target = DeploymentTarget(args["deployment_target"])
    if "migration_standard" in args:
        config.migration_standard = MigrationStandard(args["migration_standard"])
    if "inventory_source" in args:
        config.inventory_source = args["inventory_source"]
    if "validate" in args:
        config.validate_post_migration = args["validate"]
    if "validation_tools" in args:
        config.validation_tools = [
            ValidationTool(tool) for tool in args["validation_tools"]
        ]
    if "iterate" in args:
        config.iterate_until_clean = args["iterate"]
    if "python_version" in args:
        config.target_python_version = args["python_version"]
    if "ansible_version" in args:
        config.target_ansible_version = args["ansible_version"]

    return config
