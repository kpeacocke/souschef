"""Jenkins pipeline generation from Chef CI/CD patterns."""

from pathlib import Path
from typing import Any


def generate_jenkinsfile_from_chef_ci(
    cookbook_path: str,
    pipeline_name: str,
    pipeline_type: str = "declarative",
) -> str:
    """
    Generate Jenkinsfile from Chef cookbook CI/CD patterns.

    Analyzes Chef testing tools (kitchen-ci, foodcritic, cookstyle, chefspec)
    and generates equivalent Jenkins pipeline stages.

    Args:
        cookbook_path: Path to Chef cookbook.
        pipeline_name: Name for the Jenkins pipeline.
        pipeline_type: 'declarative' or 'scripted'.

    Returns:
        Jenkinsfile content (Groovy DSL).

    """
    # Analyze Chef CI patterns
    ci_patterns = _analyze_chef_ci_patterns(cookbook_path)

    if pipeline_type == "declarative":
        return _generate_declarative_pipeline(pipeline_name, ci_patterns)
    else:
        return _generate_scripted_pipeline(pipeline_name)


def _analyze_chef_ci_patterns(cookbook_path: str) -> dict[str, Any]:
    """
    Analyze Chef cookbook for CI/CD patterns.

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
            import yaml

            test_suites: list[str] = patterns["test_suites"]
            with kitchen_file.open() as f:
                kitchen_config = yaml.safe_load(f)
                if "suites" in kitchen_config:
                    test_suites.extend(
                        suite["name"] for suite in kitchen_config["suites"]
                    )
        except Exception:
            pass

    return patterns


def _create_lint_stage(ci_patterns: dict[str, Any]) -> str | None:
    """Create lint stage if lint tools are detected."""
    if not ci_patterns.get("lint_tools"):
        return None

    lint_steps = []
    for tool in ci_patterns["lint_tools"]:
        if tool == "cookstyle":
            lint_steps.append("sh 'ansible-lint playbooks/'")
        elif tool == "foodcritic":
            lint_steps.append("sh 'yamllint -c .yamllint .'")
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
    pipeline_name: str, ci_patterns: dict[str, Any]
) -> str:
    """
    Generate Jenkins Declarative Pipeline.

    Args:
        pipeline_name: Pipeline name.
        ci_patterns: Detected CI patterns.

    Returns:
        Jenkinsfile with Declarative Pipeline syntax.

    """
    stages = []

    # Add stages based on detected patterns
    lint_stage = _create_lint_stage(ci_patterns)
    if lint_stage:
        stages.append(lint_stage)

    unit_stage = _create_unit_test_stage(ci_patterns)
    if unit_stage:
        stages.append(unit_stage)

    integration_stage = _create_integration_test_stage(ci_patterns)
    if integration_stage:
        stages.append(integration_stage)

    # Always add deploy stage
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


def _generate_scripted_pipeline(pipeline_name: str) -> str:
    """
    Generate Jenkins Scripted Pipeline.

    Args:
        pipeline_name: Pipeline name.

    Returns:
        Jenkinsfile with Scripted Pipeline syntax.

    """
    return f"""// Jenkinsfile: {pipeline_name}
// Generated from Chef cookbook CI/CD patterns
// Pipeline Type: Scripted

node {{
    try {{
        stage('Checkout') {{
            checkout scm
        }}

        stage('Lint') {{
            sh 'ansible-lint playbooks/'
        }}

        stage('Test') {{
            sh 'molecule test'
        }}

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
