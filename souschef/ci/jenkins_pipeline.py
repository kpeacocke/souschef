"""Jenkins pipeline generation from Chef CI/CD patterns."""

from pathlib import Path
from typing import Any

import yaml


def generate_jenkinsfile_from_chef_ci(
    cookbook_path: str,
    pipeline_name: str,
    pipeline_type: str = "declarative",
    enable_parallel: bool = True,
) -> str:
    """
    Generate Jenkinsfile from Chef cookbook CI/CD patterns.

    Analyzes Chef testing tools (kitchen-ci, foodcritic, cookstyle, chefspec)
    and generates equivalent Jenkins pipeline stages.

    Args:
        cookbook_path: Path to Chef cookbook.
        pipeline_name: Name for the Jenkins pipeline.
        pipeline_type: 'declarative' or 'scripted'.
        enable_parallel: Enable parallel execution of test stages.

    Returns:
        Jenkinsfile content (Groovy DSL).

    """
    # Analyse Chef CI patterns
    ci_patterns = _analyse_chef_ci_patterns(cookbook_path)

    if pipeline_type == "declarative":
        return _generate_declarative_pipeline(
            pipeline_name, ci_patterns, enable_parallel
        )
    else:
        return _generate_scripted_pipeline(pipeline_name, enable_parallel)


def _analyse_chef_ci_patterns(cookbook_path: str) -> dict[str, Any]:
    """
    Analyse Chef cookbook for CI/CD patterns.

    Detects:
    - Test Kitchen configuration (.kitchen.yml)
    - ChefSpec tests (spec/)
    - InSpec tests (test/integration/)
    - Foodcritic/Cookstyle linting
    - Berksfile dependencies

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
            # Gracefully handle malformed .kitchen.yml - continue with empty config
            # Catches: YAML syntax errors, file I/O errors, missing config keys,
            # type mismatches in config structure, and missing dict attributes
            pass

    return patterns


def _create_lint_stage(ci_patterns: dict[str, Any]) -> str | None:
    """Create lint stage if lint tools are detected."""
    if not ci_patterns.get("lint_tools"):
        return None

    lint_steps: list[str] = []
    for tool in ci_patterns["lint_tools"]:
        if tool == "cookstyle":
            lint_steps.append("sh 'ansible-lint playbooks/'")
        elif tool == "foodcritic":
            lint_steps.append("sh 'yamllint -c .yamllint .'")

    if not lint_steps:
        return None

    return _create_stage("Lint", lint_steps)


def _create_unit_test_stage(ci_patterns: dict[str, Any]) -> str | None:
    """Create unit test stage if ChefSpec is detected."""
    if not ci_patterns.get("has_chefspec"):
        return None

    return _create_stage(
        "Unit Tests",
        ["sh 'molecule test --scenario-name default'"],
    )


def _create_integration_test_stage(ci_patterns: dict[str, Any]) -> str | None:
    """Create integration test stage if Test Kitchen or InSpec is detected."""
    if not (ci_patterns.get("has_kitchen") or ci_patterns.get("has_inspec")):
        return None

    test_steps = []
    if ci_patterns.get("test_suites"):
        for suite in ci_patterns["test_suites"]:
            test_steps.append(f"sh 'molecule test --scenario-name {suite}'")
    else:
        test_steps.append("sh 'molecule test'")

    return _create_stage("Integration Tests", test_steps)


def _create_deploy_stage() -> str:
    """Create deploy stage."""
    return _create_stage(
        "Deploy",
        [
            (
                "sh 'ansible-playbook -i inventory/production "
                "playbooks/site.yml --check'"
            ),
            "input message: 'Deploy to production?', ok: 'Deploy'",
            "sh 'ansible-playbook -i inventory/production playbooks/site.yml'",
        ],
    )


def _generate_declarative_pipeline(
    pipeline_name: str, ci_patterns: dict[str, Any], enable_parallel: bool = True
) -> str:
    """
    Generate Jenkins Declarative Pipeline.

    Args:
        pipeline_name: Pipeline name.
        ci_patterns: Detected CI patterns.
        enable_parallel: Enable parallel execution of test stages.

    Returns:
        Jenkinsfile with Declarative Pipeline syntax.

    """
    stages = []

    # Collect test stages for potential parallel execution
    test_stages = []

    lint_stage = _create_lint_stage(ci_patterns)
    if lint_stage:
        test_stages.append(lint_stage)

    unit_stage = _create_unit_test_stage(ci_patterns)
    if unit_stage:
        test_stages.append(unit_stage)

    integration_stage = _create_integration_test_stage(ci_patterns)
    if integration_stage:
        test_stages.append(integration_stage)

    # Add test stages (parallel or sequential based on enable_parallel)
    if enable_parallel and len(test_stages) > 1:
        # Wrap multiple test stages in parallel block
        parallel_content = "\n".join(test_stages)
        parallel_stage = f"""stage('Test') {{
            parallel {{
{_indent_content(parallel_content, 16)}
            }}
        }}"""
        stages.append(parallel_stage)
    else:
        # Execute stages sequentially
        stages.extend(test_stages)

    # Always add deploy stage (never parallelized)
    stages.append(_create_deploy_stage())

    # Build pipeline
    stages_groovy = "\n\n".join(stages)

    return f"""// Jenkinsfile: {pipeline_name}
// Generated from Chef cookbook CI/CD patterns
// Pipeline Type: Declarative

pipeline {{
    agent any

    options {{
        timestamps()
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }}

    environment {{
        ANSIBLE_FORCE_COLOR = 'true'
        ANSIBLE_HOST_KEY_CHECKING = 'false'
    }}

    stages {{
{_indent_content(stages_groovy, 8)}
    }}

    post {{
        always {{
            cleanWs()
        }}
        success {{
            echo 'Pipeline succeeded!'
        }}
        failure {{
            echo 'Pipeline failed!'
        }}
    }}
}}
"""


def _generate_scripted_pipeline(
    pipeline_name: str, enable_parallel: bool = True
) -> str:
    """
    Generate Jenkins Scripted Pipeline.

    Args:
        pipeline_name: Pipeline name.
        enable_parallel: Enable parallel execution of test stages.

    Returns:
        Jenkinsfile with Scripted Pipeline syntax.

    """
    if enable_parallel:
        test_block = """        parallel(
            lint: {{
                stage('Lint') {{
                    sh 'ansible-lint playbooks/'
                }}
            }},
            test: {{
                stage('Test') {{
                    sh 'molecule test'
                }}
            }}
        )"""
    else:
        test_block = """        stage('Lint') {{
            sh 'ansible-lint playbooks/'
        }}

        stage('Test') {{
            sh 'molecule test'
        }}"""

    return f"""// Jenkinsfile: {pipeline_name}
// Generated from Chef cookbook CI/CD patterns
// Pipeline Type: Scripted

node {{
    try {{
        stage('Checkout') {{
            checkout scm
        }}

{test_block}

        stage('Deploy') {{
            input message: 'Deploy to production?', ok: 'Deploy'
            sh 'ansible-playbook -i inventory/production playbooks/site.yml'
        }}
    }} catch (Exception e) {{
        currentBuild.result = 'FAILURE'
        throw e
    }} finally {{
        cleanWs()
    }}
}}
"""


def _create_stage(name: str, steps: list[str]) -> str:
    """
    Create a Jenkins Declarative Pipeline stage.

    Args:
        name: Stage name.
        steps: List of steps (shell commands or Jenkins DSL).

    Returns:
        Groovy stage block.

    """
    steps_formatted = "\n".join(f"                {step}" for step in steps)
    return f"""stage('{name}') {{
            steps {{
{steps_formatted}
            }}
        }}"""


def _indent_content(content: str, spaces: int) -> str:
    """
    Indent multi-line content.

    Args:
        content: Content to indent.
        spaces: Number of spaces to indent.

    Returns:
        Indented content.

    """
    indent = " " * spaces
    return "\n".join(
        indent + line if line.strip() else line for line in content.split("\n")
    )
