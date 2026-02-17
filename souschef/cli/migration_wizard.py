"""
V2.2: Interactive CLI wizard for migration setup.

Provides user-friendly prompts for configuring Chef to Ansible migrations,
including resource pattern customisation, validation checks, and field-by-field
guidance through the migration configuration process.
"""

# ruff: noqa: T201
import re
import sys
from pathlib import Path
from typing import Any


def setup_wizard() -> dict[str, Any]:
    """
    Run interactive migration setup wizard.

    Guides user through configuration options with validation
    and helpful prompts.

    Returns:
        Complete migration configuration dictionary.

    """
    print("\n╔════════════════════════════════════════════════════════╗")
    print("║  SousChef Migration Wizard - Chef to Ansible          ║")
    print("╚════════════════════════════════════════════════════════╝\n")
    print("This wizard will guide you through setting up a migration.\n")

    config = {}

    # Cookbook path
    config["cookbook_path"] = _prompt_cookbook_path()

    # Output directory
    config["output_dir"] = _prompt_output_directory()

    # Chef version
    config["chef_version"] = _prompt_chef_version()

    # Ansible version target
    config["ansible_version"] = _prompt_ansible_version()

    # Resource patterns
    config["resource_patterns"] = _prompt_resource_patterns()

    # Conversion options
    config["conversion_options"] = _prompt_conversion_options()

    # Validation options
    config["validation_options"] = _prompt_validation_options()

    # Optimization options
    config["optimization_options"] = _prompt_optimization_options()

    # Summary and confirmation
    if _confirm_configuration(config):
        print("\n✓ Configuration saved successfully!")
        return config
    else:
        print("\n✗ Configuration cancelled by user")
        sys.exit(0)


def _prompt_cookbook_path() -> str:
    """Prompt for cookbook path with validation."""
    while True:
        print("\n[1/8] Cookbook Location")
        print("─" * 60)
        path = input("Enter path to Chef cookbook directory: ").strip()

        if not path:
            print("  ✗ Error: Path cannot be empty")
            continue

        cookbook_path = Path(path)
        if not cookbook_path.exists():
            print(f"  ✗ Error: Path does not exist: {path}")
            retry = input("  Would you like to try again? (y/n): ").strip().lower()
            if retry != "y":
                sys.exit(1)
            continue

        if not cookbook_path.is_dir():
            print(f"  ✗ Error: Path is not a directory: {path}")
            continue

        # Check for metadata.rb or recipes directory
        has_metadata = (cookbook_path / "metadata.rb").exists()
        has_recipes = (cookbook_path / "recipes").exists()

        if not has_metadata and not has_recipes:
            print("  ⚠ Warning: No metadata.rb or recipes/ directory found")
            proceed = input("  Continue anyway? (y/n): ").strip().lower()
            if proceed != "y":
                continue

        print(f"  ✓ Cookbook path set: {cookbook_path.absolute()}")
        return str(cookbook_path.absolute())


def _prompt_output_directory() -> str:
    """Prompt for output directory."""
    print("\n[2/8] Output Location")
    print("─" * 60)
    default = "./ansible_output"
    output_dir = input(
        f"Enter output directory for Ansible playbooks [{default}]: "
    ).strip()

    if not output_dir:
        output_dir = default

    output_path = Path(output_dir)
    if output_path.exists() and list(output_path.iterdir()):
        print(f"  ⚠ Warning: Directory is not empty: {output_dir}")
        overwrite = input("  Overwrite existing files? (y/n): ").strip().lower()
        if overwrite != "y":
            sys.exit(1)

    print(f"  ✓ Output directory set: {output_path.absolute()}")
    return str(output_path.absolute())


def _prompt_chef_version() -> str:
    """Prompt for Chef version."""
    print("\n[3/8] Chef Version")
    print("─" * 60)
    print("Supported versions: 12.x, 14.x, 15.x")
    default = "14.15.6"
    version = input(f"Enter Chef version [{default}]: ").strip()

    if not version:
        version = default

    # Basic validation
    if not re.match(r"^\d+\.\d+(\.\d+)?$", version):
        print(f"  ⚠ Warning: Unusual version format: {version}")

    print(f"  ✓ Chef version set: {version}")
    return version


def _prompt_ansible_version() -> str:
    """Prompt for target Ansible version."""
    print("\n[4/8] Ansible Version Target")
    print("─" * 60)
    print("Supported versions: 2.9+, 2.10+, 2.11+, 2.12+")
    default = "2.12"
    version = input(f"Enter target Ansible version [{default}]: ").strip()

    if not version:
        version = default

    print(f"  ✓ Ansible version target set: {version}")
    return version


def _prompt_resource_patterns() -> dict[str, bool]:
    """Prompt for resource pattern inclusion."""
    print("\n[5/8] Resource Pattern Configuration")
    print("─" * 60)
    print("Select which Chef resource types to convert:")

    patterns = {
        "package": _yes_no_prompt("  Convert package resources? ", default=True),
        "service": _yes_no_prompt("  Convert service resources? ", default=True),
        "file": _yes_no_prompt("  Convert file resources? ", default=True),
        "template": _yes_no_prompt("  Convert template resources? ", default=True),
        "directory": _yes_no_prompt("  Convert directory resources? ", default=True),
        "execute": _yes_no_prompt("  Convert execute resources? ", default=True),
        "custom": _yes_no_prompt("  Convert custom resources? ", default=True),
    }

    enabled_count = sum(1 for v in patterns.values() if v)
    print(f"\n  ✓ {enabled_count} resource patterns enabled")
    return patterns


def _prompt_conversion_options() -> dict[str, Any]:
    """Prompt for conversion options."""
    print("\n[6/8] Conversion Options")
    print("─" * 60)

    options = {
        "preserve_comments": _yes_no_prompt(
            "  Preserve Chef code comments? ", default=True
        ),
        "add_annotations": _yes_no_prompt(
            "  Add conversion annotations? ", default=True
        ),
        "generate_handlers": _yes_no_prompt("  Generate handler tasks? ", default=True),
        "use_custom_modules": _yes_no_prompt(
            "  Generate custom Ansible modules for complex resources? ",
            default=False,
        ),
        "apply_conversion_rules": _yes_no_prompt(
            "  Apply custom conversion rules? ", default=True
        ),
    }

    print("  ✓ Conversion options configured")
    return options


def _prompt_validation_options() -> dict[str, Any]:
    """Prompt for validation options."""
    print("\n[7/8] Validation Options")
    print("─" * 60)

    options = {
        "syntax_check": _yes_no_prompt(
            "  Perform Ansible syntax validation? ", default=True
        ),
        "lint_check": _yes_no_prompt(
            "  Run ansible-lint on generated playbooks? ", default=False
        ),
        "generate_report": _yes_no_prompt(
            "  Generate conversion quality report? ", default=True
        ),
    }

    print("  ✓ Validation options configured")
    return options


def _prompt_optimization_options() -> dict[str, Any]:
    """Prompt for optimization options."""
    print("\n[8/8] Optimization Options")
    print("─" * 60)

    options = {
        "deduplicate_tasks": _yes_no_prompt("  Remove duplicate tasks? ", default=True),
        "consolidate_loops": _yes_no_prompt(
            "  Consolidate tasks into loops? ", default=True
        ),
        "optimize_handlers": _yes_no_prompt(
            "  Optimize handler notifications? ", default=True
        ),
        "parallel_processing": _yes_no_prompt(
            "  Use parallel processing for large cookbooks? ", default=False
        ),
    }

    print("  ✓ Optimization options configured")
    return options


def _yes_no_prompt(prompt: str, default: bool = True) -> bool:
    """
    Prompt for yes/no answer.

    Args:
        prompt: Question to display.
        default: Default value if user presses enter.

    Returns:
        True for yes, False for no.

    """
    suffix = "(Y/n)" if default else "(y/N)"
    while True:
        response = input(f"{prompt}{suffix}: ").strip().lower()

        if not response:
            return default

        if response in ("y", "yes"):
            return True
        elif response in ("n", "no"):
            return False
        else:
            print("    Please answer 'y' or 'n'")


def _confirm_configuration(config: dict[str, Any]) -> bool:
    """
    Display configuration summary and ask for confirmation.

    Args:
        config: Configuration dictionary.

    Returns:
        True if user confirms, False otherwise.

    """
    print("\n╔════════════════════════════════════════════════════════╗")
    print("║  Configuration Summary                                 ║")
    print("╚════════════════════════════════════════════════════════╝\n")

    print(f"Cookbook Path:      {config['cookbook_path']}")
    print(f"Output Directory:   {config['output_dir']}")
    print(f"Chef Version:       {config['chef_version']}")
    print(f"Ansible Version:    {config['ansible_version']}")

    print("\nResource Patterns:")
    enabled_patterns = [k for k, v in config["resource_patterns"].items() if v]
    for pattern in enabled_patterns:
        print(f"  • {pattern}")

    print("\nConversion Options:")
    for key, value in config["conversion_options"].items():
        status = "✓" if value else "✗"
        print(f"  {status} {key.replace('_', ' ').title()}")

    print("\nValidation Options:")
    for key, value in config["validation_options"].items():
        status = "✓" if value else "✗"
        print(f"  {status} {key.replace('_', ' ').title()}")

    print("\nOptimization Options:")
    for key, value in config["optimization_options"].items():
        status = "✓" if value else "✗"
        print(f"  {status} {key.replace('_', ' ').title()}")

    print()
    return _yes_no_prompt("Proceed with this configuration?", default=True)


def validate_inputs(config: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate configuration inputs.

    Args:
        config: Configuration dictionary.

    Returns:
        Tuple of (is_valid, list of error messages).

    """
    errors = []

    # Validate cookbook path
    if "cookbook_path" not in config:
        errors.append("Missing cookbook_path")
    elif not Path(config["cookbook_path"]).exists():
        errors.append(f"Cookbook path does not exist: {config['cookbook_path']}")

    # Validate output directory
    if "output_dir" not in config:
        errors.append("Missing output_dir")

    # Validate versions
    if "chef_version" not in config:
        errors.append("Missing chef_version")
    elif not re.match(r"^\d+\.\d+(\.\d+)?$", config.get("chef_version", "")):
        errors.append(f"Invalid Chef version: {config.get('chef_version')}")

    if "ansible_version" not in config:
        errors.append("Missing ansible_version")

    # Validate at least one resource pattern enabled
    if "resource_patterns" in config and not any(config["resource_patterns"].values()):
        errors.append("At least one resource pattern must be enabled")

    return len(errors) == 0, errors


def generate_migration_config(config: dict[str, Any]) -> str:
    """
    Generate migration configuration file content.

    Args:
        config: Configuration dictionary from wizard.

    Returns:
        YAML configuration file content.

    """
    yaml_content = f"""# SousChef Migration Configuration
# Generated by migration wizard

cookbook:
  path: '{config["cookbook_path"]}'
  chef_version: '{config["chef_version"]}'

output:
  directory: '{config["output_dir"]}'
  ansible_version: '{config["ansible_version"]}'

resource_patterns:
"""

    for pattern, enabled in config["resource_patterns"].items():
        yaml_content += f"  {pattern}: {str(enabled).lower()}\n"

    yaml_content += "\nconversion:\n"
    for option, value in config["conversion_options"].items():
        yaml_content += f"  {option}: {str(value).lower()}\n"

    yaml_content += "\nvalidation:\n"
    for option, value in config["validation_options"].items():
        yaml_content += f"  {option}: {str(value).lower()}\n"

    yaml_content += "\noptimization:\n"
    for option, value in config["optimization_options"].items():
        yaml_content += f"  {option}: {str(value).lower()}\n"

    return yaml_content
