"""Common CI/CD analysis utilities for Chef cookbooks."""

from pathlib import Path
from typing import Any

import yaml

from souschef.core.path_utils import _normalize_path


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
    # Normalize path to prevent path traversal attacks
    if isinstance(cookbook_path, str):
        base_path = _normalize_path(cookbook_path)
    else:
        base_path = cookbook_path.resolve()

    patterns: dict[str, Any] = {
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

    # Detect linting tools
    lint_tools: list[str] = patterns["lint_tools"]
    if (base_path / ".foodcritic").exists():
        lint_tools.append("foodcritic")
    if (base_path / ".cookstyle.yml").exists():
        lint_tools.append("cookstyle")

    # Check for ChefSpec
    spec_dir = base_path / "spec"
    patterns["has_chefspec"] = spec_dir.exists() and any(spec_dir.glob("**/*_spec.rb"))

    # Parse kitchen.yml for test suites and platforms
    kitchen_file = base_path / ".kitchen.yml"
    if kitchen_file.exists():
        try:
            kitchen_suites: list[str] = patterns["kitchen_suites"]
            kitchen_platforms: list[str] = patterns["kitchen_platforms"]
            with kitchen_file.open() as f:
                kitchen_config = yaml.safe_load(f)
                if kitchen_config:
                    # Extract suites
                    suites = kitchen_config.get("suites", [])
                    if suites:
                        kitchen_suites.extend(s.get("name", "default") for s in suites)
                    # Extract platforms
                    platforms = kitchen_config.get("platforms", [])
                    if platforms:
                        kitchen_platforms.extend(
                            p.get("name", "unknown") for p in platforms
                        )
        except (yaml.YAMLError, OSError, KeyError, TypeError, AttributeError):
            # Gracefully handle malformed .kitchen.yml - continue with empty config
            # Catches: YAML syntax errors, file I/O errors, missing config keys,
            # type mismatches in config structure, and missing dict attributes
            pass

    # Add backward compatibility alias
    patterns["test_suites"] = patterns["kitchen_suites"]

    return patterns
