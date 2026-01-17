"""
GitHub Actions workflow generation from Chef CI/CD patterns.

Analyzes Chef testing tools (Test Kitchen, ChefSpec, Cookstyle) and
generates equivalent GitHub Actions workflows with proper job
configuration and caching.
"""

from pathlib import Path
from typing import Any

import yaml

# GitHub Actions constants
ACTION_CHECKOUT = "actions/checkout@v4"
ACTION_SETUP_RUBY = "ruby/setup-ruby@v1"
ACTION_CACHE = "actions/cache@v4"
ACTION_UPLOAD_ARTIFACT = "actions/upload-artifact@v4"

STEP_NAME_CHECKOUT = "Checkout code"
STEP_NAME_SETUP_RUBY = "Setup Ruby"
STEP_NAME_CACHE_GEMS = "Cache gems"
STEP_NAME_INSTALL_DEPS = "Install dependencies"

GEM_BUNDLE_PATH = "vendor/bundle"
GEM_CACHE_KEY = "gems-${{ runner.os }}-${{ hashFiles('**/Gemfile.lock') }}"
GEM_CACHE_RESTORE_KEY = "gems-${{ runner.os }}-"

BUNDLE_INSTALL_CMD = "bundle install --jobs 4 --retry 3"


def generate_github_workflow_from_chef_ci(
    cookbook_path: str,
    workflow_name: str = "Chef Cookbook CI",
    enable_cache: bool = True,
    enable_artifacts: bool = True,
) -> str:
    """
    Generate GitHub Actions workflow from Chef cookbook CI/CD patterns.

    Args:
        cookbook_path: Path to Chef cookbook directory.
        workflow_name: Name for the GitHub Actions workflow.
        enable_cache: Enable caching for Chef dependencies.
        enable_artifacts: Enable artifacts for test results.

    Returns:
        GitHub Actions workflow YAML content.

    """
    cookbook_dir = Path(cookbook_path)
    if not cookbook_dir.exists():
        raise FileNotFoundError(f"Cookbook directory not found: {cookbook_path}")

    # Analyse Chef CI patterns
    patterns = _analyse_chef_ci_patterns(cookbook_dir)

    # Build workflow structure
    workflow = _build_workflow_structure(
        workflow_name, patterns, enable_cache, enable_artifacts
    )

    return yaml.dump(workflow, default_flow_style=False, sort_keys=False)


def _analyse_chef_ci_patterns(cookbook_dir: Path) -> dict[str, Any]:
    """
    Analyse Chef cookbook for CI/CD patterns and testing configurations.

    This function examines a Chef cookbook directory to detect various
    testing and linting tools, as well as Test Kitchen configurations
    including suites and platforms.

    Args:
        cookbook_dir: Path to the Chef cookbook directory to analyse.

    Returns:
        Dictionary containing detected patterns with the following keys:
            - has_kitchen (bool): Whether Test Kitchen is configured
              (.kitchen.yml exists)
            - has_chefspec (bool): Whether ChefSpec tests are present
              (spec/**/*_spec.rb files)
            - has_cookstyle (bool): Whether Cookstyle is configured
              (.cookstyle.yml exists)
            - has_foodcritic (bool): Whether Foodcritic (legacy) is
              configured (.foodcritic exists)
            - kitchen_suites (list[str]): Names of Test Kitchen suites
              found in .kitchen.yml
            - kitchen_platforms (list[str]): Names of Test Kitchen
              platforms found in .kitchen.yml

    Note:
        If .kitchen.yml is malformed or cannot be parsed, the function
        continues with empty suite and platform lists rather than
        raising an exception.

    Example:
        >>> patterns = _analyze_chef_ci_patterns(Path("/path/to/cookbook"))
        >>> patterns["has_kitchen"]
        True
        >>> patterns["kitchen_suites"]
        ['default', 'integration']

    """
    patterns: dict[str, Any] = {
        "has_kitchen": False,
        "has_chefspec": False,
        "has_cookstyle": False,
        "has_foodcritic": False,
        "kitchen_suites": [],
        "kitchen_platforms": [],
    }

    # Check for Test Kitchen
    kitchen_yml = cookbook_dir / ".kitchen.yml"
    if kitchen_yml.exists():
        patterns["has_kitchen"] = True
        try:
            with kitchen_yml.open() as f:
                kitchen_config = yaml.safe_load(f)
                if kitchen_config:
                    # Extract suites
                    suites = kitchen_config.get("suites", [])
                    if suites:
                        patterns["kitchen_suites"] = [
                            s.get("name", "default") for s in suites
                        ]
                    # Extract platforms
                    platforms = kitchen_config.get("platforms", [])
                    if platforms:
                        patterns["kitchen_platforms"] = [
                            p.get("name", "unknown") for p in platforms
                        ]
        except (yaml.YAMLError, OSError, KeyError, TypeError, AttributeError):
            # Gracefully handle malformed .kitchen.yml - continue with empty config
            # Catches: YAML syntax errors, file I/O errors, missing config keys,
            # type mismatches in config structure, and missing dict attributes
            pass

    # Check for ChefSpec
    spec_dir = cookbook_dir / "spec"
    if spec_dir.exists() and any(spec_dir.glob("**/*_spec.rb")):
        patterns["has_chefspec"] = True

    # Check for Cookstyle
    cookstyle_yml = cookbook_dir / ".cookstyle.yml"
    if cookstyle_yml.exists():
        patterns["has_cookstyle"] = True

    # Check for Foodcritic (legacy)
    if (cookbook_dir / ".foodcritic").exists():
        patterns["has_foodcritic"] = True

    return patterns


def _build_workflow_structure(
    workflow_name: str,
    patterns: dict[str, Any],
    enable_cache: bool,
    enable_artifacts: bool,
) -> dict[str, Any]:
    """
    Build GitHub Actions workflow structure.

    Args:
        workflow_name: Workflow name.
        patterns: Detected Chef CI patterns.
        enable_cache: Enable caching.
        enable_artifacts: Enable artifacts.

    Returns:
        Workflow dictionary structure.

    """
    workflow: dict[str, Any] = {
        "name": workflow_name,
        "on": {
            "push": {"branches": ["main", "develop"]},
            "pull_request": {"branches": ["main", "develop"]},
        },
        "jobs": {},
    }

    # Add lint job
    if patterns["has_cookstyle"] or patterns["has_foodcritic"]:
        workflow["jobs"]["lint"] = _build_lint_job(patterns, enable_cache)

    # Add unit test job
    if patterns["has_chefspec"]:
        workflow["jobs"]["unit-test"] = _build_unit_test_job(enable_cache)

    # Add integration test jobs
    if patterns["has_kitchen"]:
        workflow["jobs"]["integration-test"] = _build_integration_test_job(
            patterns, enable_cache, enable_artifacts
        )

    return workflow


def _build_lint_job(patterns: dict[str, Any], enable_cache: bool) -> dict[str, Any]:
    """
    Build lint job configuration.

    Args:
        patterns: Detected CI patterns.
        enable_cache: Enable caching.

    Returns:
        Lint job configuration.

    """
    job: dict[str, Any] = {
        "name": "Lint Cookbook",
        "runs-on": "ubuntu-latest",
        "steps": [
            {"name": STEP_NAME_CHECKOUT, "uses": ACTION_CHECKOUT},
            {
                "name": STEP_NAME_SETUP_RUBY,
                "uses": ACTION_SETUP_RUBY,
                "with": {"ruby-version": "3.2"},
            },
        ],
    }

    if enable_cache:
        job["steps"].append(
            {
                "name": STEP_NAME_CACHE_GEMS,
                "uses": ACTION_CACHE,
                "with": {
                    "path": GEM_BUNDLE_PATH,
                    "key": GEM_CACHE_KEY,
                    "restore-keys": GEM_CACHE_RESTORE_KEY,
                },
            }
        )

    job["steps"].extend(
        [
            {
                "name": STEP_NAME_INSTALL_DEPS,
                "run": BUNDLE_INSTALL_CMD,
            },
        ]
    )

    # Add appropriate lint commands
    if patterns["has_cookstyle"]:
        job["steps"].append({"name": "Run Cookstyle", "run": "bundle exec cookstyle"})

    if patterns["has_foodcritic"]:
        job["steps"].append(
            {"name": "Run Foodcritic", "run": "bundle exec foodcritic ."}
        )

    return job


def _build_unit_test_job(enable_cache: bool) -> dict[str, Any]:
    """
    Build unit test job configuration.

    Args:
        enable_cache: Enable caching.

    Returns:
        Unit test job configuration.

    """
    job: dict[str, Any] = {
        "name": "Unit Tests (ChefSpec)",
        "runs-on": "ubuntu-latest",
        "steps": [
            {"name": STEP_NAME_CHECKOUT, "uses": ACTION_CHECKOUT},
            {
                "name": STEP_NAME_SETUP_RUBY,
                "uses": ACTION_SETUP_RUBY,
                "with": {"ruby-version": "3.2"},
            },
        ],
    }

    if enable_cache:
        job["steps"].append(
            {
                "name": STEP_NAME_CACHE_GEMS,
                "uses": ACTION_CACHE,
                "with": {
                    "path": GEM_BUNDLE_PATH,
                    "key": GEM_CACHE_KEY,
                    "restore-keys": GEM_CACHE_RESTORE_KEY,
                },
            }
        )

    job["steps"].extend(
        [
            {
                "name": STEP_NAME_INSTALL_DEPS,
                "run": BUNDLE_INSTALL_CMD,
            },
            {"name": "Run ChefSpec tests", "run": "bundle exec rspec"},
        ]
    )

    return job


def _build_integration_test_job(
    patterns: dict[str, Any], enable_cache: bool, enable_artifacts: bool
) -> dict[str, Any]:
    """
    Build integration test job configuration.

    Args:
        patterns: Detected CI patterns.
        enable_cache: Enable caching.
        enable_artifacts: Enable artifacts.

    Returns:
        Integration test job configuration.

    """
    job: dict[str, Any] = {
        "name": "Integration Tests (Test Kitchen)",
        "runs-on": "ubuntu-latest",
        "strategy": {"matrix": {"suite": patterns["kitchen_suites"] or ["default"]}},
        "steps": [
            {"name": STEP_NAME_CHECKOUT, "uses": ACTION_CHECKOUT},
            {
                "name": STEP_NAME_SETUP_RUBY,
                "uses": ACTION_SETUP_RUBY,
                "with": {"ruby-version": "3.2"},
            },
        ],
    }

    if enable_cache:
        job["steps"].append(
            {
                "name": STEP_NAME_CACHE_GEMS,
                "uses": ACTION_CACHE,
                "with": {
                    "path": GEM_BUNDLE_PATH,
                    "key": GEM_CACHE_KEY,
                    "restore-keys": GEM_CACHE_RESTORE_KEY,
                },
            }
        )

    job["steps"].extend(
        [
            {
                "name": STEP_NAME_INSTALL_DEPS,
                "run": BUNDLE_INSTALL_CMD,
            },
            {
                "name": "Run Test Kitchen",
                "run": "bundle exec kitchen test ${{ matrix.suite }}",
            },
        ]
    )

    if enable_artifacts:
        job["steps"].append(
            {
                "name": "Upload test results",
                "uses": ACTION_UPLOAD_ARTIFACT,
                "if": "always()",
                "with": {
                    "name": "kitchen-logs-${{ matrix.suite }}",
                    "path": ".kitchen/logs/",
                },
            }
        )

    return job
