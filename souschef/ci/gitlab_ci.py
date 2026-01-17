"""GitLab CI generation from Chef CI/CD patterns."""

from pathlib import Path
from typing import Any

import yaml


def generate_gitlab_ci_from_chef_ci(
    cookbook_path: str,
    project_name: str,
    enable_cache: bool = True,
    enable_artifacts: bool = True,
) -> str:
    """
    Generate .gitlab-ci.yml from Chef cookbook CI/CD patterns.

    Analyzes Chef testing tools and generates equivalent GitLab CI stages.

    Args:
        cookbook_path: Path to Chef cookbook.
        project_name: GitLab project name.
        enable_cache: Enable caching for dependencies.
        enable_artifacts: Enable artifacts for test results.

    Returns:
        GitLab CI YAML content.

    """
    # Analyse Chef CI patterns
    ci_patterns = _analyse_chef_ci_patterns(cookbook_path)

    # Generate CI configuration
    return _generate_gitlab_ci_yaml(
        project_name, ci_patterns, enable_cache, enable_artifacts
    )


def _analyse_chef_ci_patterns(cookbook_path: str) -> dict[str, Any]:
    """
    Analyse Chef cookbook for CI/CD patterns.

    Args:
        cookbook_path: Path to Chef cookbook.

    Returns:
        Dictionary of detected CI patterns.

    """
    base_path = Path(cookbook_path)

    patterns: dict[str, Any] = {
        "has_kitchen": (base_path / ".kitchen.yml").exists(),
        "has_chefspec": (base_path / "spec").exists(),
        "has_inspec": (base_path / "test" / "integration").exists(),
        "has_berksfile": (base_path / "Berksfile").exists(),
        "lint_tools": [],
        "test_suites": [],
    }

    # Detect linting tools
    lint_tools: list[str] = patterns["lint_tools"]
    if (base_path / ".foodcritic").exists():
        lint_tools.append("foodcritic")
    if (base_path / ".cookstyle.yml").exists():
        lint_tools.append("cookstyle")

    # Parse kitchen.yml for test suites
    kitchen_file = base_path / ".kitchen.yml"
    if kitchen_file.exists():
        try:
            test_suites: list[str] = patterns["test_suites"]
            with kitchen_file.open() as f:
                kitchen_config = yaml.safe_load(f)
                if kitchen_config and "suites" in kitchen_config:
                    test_suites.extend(
                        suite["name"] for suite in kitchen_config["suites"]
                    )
        except (yaml.YAMLError, OSError, KeyError, TypeError, AttributeError):
            # Gracefully handle malformed .kitchen.yml - continue with empty
            # test suites. Catches: YAML syntax errors, file I/O errors,
            # missing config keys, type mismatches
            pass

    return patterns


def _build_lint_jobs(ci_patterns: dict[str, Any], enable_artifacts: bool) -> list[str]:
    """Build lint job configurations."""
    jobs = []
    if ci_patterns.get("lint_tools"):
        lint_commands = []
        for tool in ci_patterns["lint_tools"]:
            if tool == "cookstyle":
                lint_commands.append("  - ansible-lint playbooks/")
            elif tool == "foodcritic":
                lint_commands.append("  - yamllint -c .yamllint .")

        if lint_commands:
            jobs.append(
                _create_gitlab_job(
                    "lint:ansible",
                    "lint",
                    lint_commands,
                    allow_failure=False,
                    artifacts=enable_artifacts,
                )
            )
    return jobs


def _build_test_jobs(ci_patterns: dict[str, Any], enable_artifacts: bool) -> list[str]:
    """Build test job configurations."""
    jobs = []

    # Unit test job (ChefSpec → Molecule)
    if ci_patterns.get("has_chefspec"):
        jobs.append(
            _create_gitlab_job(
                "test:unit",
                "test",
                ["  - molecule test --scenario-name default"],
                artifacts=enable_artifacts,
            )
        )

    # Integration test jobs (Kitchen → Molecule)
    if ci_patterns.get("has_kitchen") or ci_patterns.get("has_inspec"):
        if ci_patterns.get("test_suites"):
            for suite in ci_patterns["test_suites"]:
                jobs.append(
                    _create_gitlab_job(
                        f"test:integration:{suite}",
                        "test",
                        [f"  - molecule test --scenario-name {suite}"],
                        artifacts=enable_artifacts,
                    )
                )
        else:
            jobs.append(
                _create_gitlab_job(
                    "test:integration",
                    "test",
                    ["  - molecule test"],
                    artifacts=enable_artifacts,
                )
            )

    return jobs


def _generate_gitlab_ci_yaml(
    project_name: str,
    ci_patterns: dict[str, Any],
    enable_cache: bool,
    enable_artifacts: bool,
) -> str:
    """
    Generate GitLab CI YAML configuration.

    Args:
        project_name: Project name.
        ci_patterns: Detected CI patterns.
        enable_cache: Enable caching.
        enable_artifacts: Enable artifacts.

    Returns:
        GitLab CI YAML content.

    """
    stages = ["lint", "test", "deploy"]
    jobs = []

    # Global configuration
    config_lines = [
        f"# .gitlab-ci.yml: {project_name}",
        "# Generated from Chef cookbook CI/CD patterns",
        "",
        "image: python:3.11",
        "",
        "stages:",
    ]
    for stage in stages:
        config_lines.append(f"  - {stage}")
    config_lines.append("")

    # Cache configuration
    if enable_cache:
        config_lines.extend(
            [
                "cache:",
                "  paths:",
                "    - .cache/pip",
                "    - venv/",
                "",
            ]
        )

    # Variables
    config_lines.extend(
        [
            "variables:",
            "  PIP_CACHE_DIR: $CI_PROJECT_DIR/.cache/pip",
            "  ANSIBLE_FORCE_COLOR: 'true'",
            "",
        ]
    )

    # Before script
    config_lines.extend(
        [
            "before_script:",
            "  - python -m venv venv",
            "  - source venv/bin/activate",
            "  - pip install --upgrade pip",
            "  - pip install ansible ansible-lint molecule molecule-docker",
            "",
        ]
    )

    # Build jobs
    jobs.extend(_build_lint_jobs(ci_patterns, enable_artifacts))
    jobs.extend(_build_test_jobs(ci_patterns, enable_artifacts))

    # Deploy job
    jobs.append(
        _create_gitlab_job(
            "deploy:production",
            "deploy",
            [
                (
                    "  - ansible-playbook -i inventory/production "
                    "playbooks/site.yml --check"
                ),
                "  - ansible-playbook -i inventory/production playbooks/site.yml",
            ],
            when="manual",
            only_branches=["main", "master"],
        )
    )

    # Combine configuration and jobs
    config = "\n".join(config_lines) + "\n" + "\n".join(jobs)
    return config


def _create_gitlab_job(
    name: str,
    stage: str,
    script: list[str],
    allow_failure: bool = False,
    artifacts: bool = False,
    when: str | None = None,
    only_branches: list[str] | None = None,
) -> str:
    """
    Create a GitLab CI job.

    Args:
        name: Job name.
        stage: Stage name.
        script: List of script commands.
        allow_failure: Allow job failure.
        artifacts: Enable artifacts.
        when: When to run (manual, on_success, etc).
        only_branches: Only run on specific branches.

    Returns:
        GitLab CI job YAML block.

    """
    job_lines = [f"{name}:", f"  stage: {stage}", "  script:"]
    job_lines.extend(script)

    if allow_failure:
        job_lines.append("  allow_failure: true")

    if artifacts:
        job_lines.extend(
            [
                "  artifacts:",
                "    reports:",
                "      junit: test-results/*.xml",
                "    paths:",
                "      - test-results/",
                "    expire_in: 1 week",
            ]
        )

    if when:
        job_lines.append(f"  when: {when}")

    if only_branches:
        job_lines.append("  only:")
        for branch in only_branches:
            job_lines.append(f"    - {branch}")

    job_lines.append("")
    return "\n".join(job_lines)
