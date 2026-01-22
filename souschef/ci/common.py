"""Common CI/CD analysis utilities for Chef cookbooks."""

from pathlib import Path
from typing import Any

import yaml

from souschef.core.path_utils import _normalize_path


def _normalize_cookbook_base(cookbook_path: str | Path) -> Path:
    """Normalise and resolve a cookbook path to prevent traversal."""
    return (
        _normalize_path(cookbook_path)
        if isinstance(cookbook_path, str)
        else cookbook_path.resolve()
    )


def _initialise_patterns(base_path: Path) -> dict[str, Any]:
    """Build initial pattern flags before deeper inspection."""
    return {
        "has_kitchen": (base_path / ".kitchen.yml").exists(),
        "has_chefspec": (base_path / "spec").exists(),
        "has_inspec": (base_path / "test" / "integration").exists(),
        "has_berksfile": (base_path / "Berksfile").exists(),
        "has_cookstyle": (base_path / ".cookstyle.yml").exists(),
        "has_foodcritic": (base_path / ".foodcritic").exists(),
        "lint_tools": [],
        "kitchen_suites": [],
        "kitchen_platforms": [],
    }


def _detect_lint_tools(base_path: Path) -> list[str]:
    """Detect linting tools configured in the cookbook directory."""
    lint_tools: list[str] = []
    if (base_path / ".foodcritic").exists():
        lint_tools.append("foodcritic")
    if (base_path / ".cookstyle.yml").exists():
        lint_tools.append("cookstyle")
    return lint_tools


def _has_chefspec_tests(base_path: Path) -> bool:
    """Return True when ChefSpec tests are present."""
    spec_dir = base_path / "spec"
    return spec_dir.exists() and any(spec_dir.glob("**/*_spec.rb"))


def _parse_kitchen_configuration(kitchen_file: Path) -> tuple[list[str], list[str]]:
    """Extract Test Kitchen suites and platforms from configuration."""
    kitchen_suites: list[str] = []
    kitchen_platforms: list[str] = []

    try:
        with kitchen_file.open() as file_handle:
            kitchen_config = yaml.safe_load(file_handle)
            if not kitchen_config:
                return kitchen_suites, kitchen_platforms

            suites = kitchen_config.get("suites", [])
            if suites:
                kitchen_suites.extend(suite.get("name", "default") for suite in suites)

            platforms = kitchen_config.get("platforms", [])
            if platforms:
                kitchen_platforms.extend(
                    platform.get("name", "unknown") for platform in platforms
                )
    except (yaml.YAMLError, OSError, KeyError, TypeError, AttributeError):
        # Gracefully handle malformed .kitchen.yml - continue with empty config
        # Catches: YAML syntax errors, file I/O errors, missing config keys,
        # type mismatches in config structure, and missing dict attributes
        return kitchen_suites, kitchen_platforms

    return kitchen_suites, kitchen_platforms


def analyse_chef_ci_patterns(cookbook_path: str | Path) -> dict[str, Any]:
    """
    Analyse Chef cookbook for CI/CD patterns and testing configurations.

    This function examines a Chef cookbook directory to detect various
    testing and linting tools, as well as Test Kitchen configurations
    including suites and platforms.

    Args:
        cookbook_path: Path to the Chef cookbook directory to analyse.

    Returns:
        Dictionary containing detected patterns with the following keys:
            - has_kitchen (bool): Whether Test Kitchen is configured
              (.kitchen.yml exists)
            - has_chefspec (bool): Whether ChefSpec tests are present
              (spec/**/*_spec.rb files)
            - has_inspec (bool): Whether InSpec tests are present
              (test/integration/ exists)
            - has_berksfile (bool): Whether Berksfile exists
            - lint_tools (list[str]): List of detected linting tools
              ('foodcritic', 'cookstyle')
            - kitchen_suites (list[str]): Names of Test Kitchen suites
              found in .kitchen.yml

    Note:
        If .kitchen.yml is malformed or cannot be parsed, the function
        continues with empty suite and platform lists rather than
        raising an exception.

    """
    base_path = _normalize_cookbook_base(cookbook_path)

    patterns: dict[str, Any] = _initialise_patterns(base_path)
    patterns["lint_tools"] = _detect_lint_tools(base_path)
    patterns["has_chefspec"] = _has_chefspec_tests(base_path)

    kitchen_file = base_path / ".kitchen.yml"
    if kitchen_file.exists():
        suites, platforms = _parse_kitchen_configuration(kitchen_file)
        patterns["kitchen_suites"] = suites
        patterns["kitchen_platforms"] = platforms

    # Add backward compatibility alias
    patterns["test_suites"] = patterns["kitchen_suites"]

    return patterns
