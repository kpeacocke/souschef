"""Tests for CI/CD pipeline generation tools in server module."""

from unittest.mock import patch

from souschef.server import (
    generate_github_workflow_from_chef,
    generate_gitlab_ci_from_chef,
    generate_jenkinsfile_from_chef,
)


def test_generate_jenkinsfile_success() -> None:
    """Jenkinsfile generation returns content on success."""
    with (
        patch(
            "souschef.server._normalise_workspace_path",
            return_value="/tmp/cookbook",
        ),
        patch(
            "souschef.ci.jenkins_pipeline.generate_jenkinsfile_from_chef_ci",
            return_value="jenkins",
        ) as mock_gen,
    ):
        result = generate_jenkinsfile_from_chef(
            cookbook_path="/tmp/cookbook",
            pipeline_type="declarative",
            enable_parallel="no",
        )

    assert result == "jenkins"
    assert mock_gen.called


def test_generate_jenkinsfile_file_not_found() -> None:
    """Jenkinsfile generation handles FileNotFoundError."""
    with (
        patch(
            "souschef.server._normalise_workspace_path",
            return_value="/tmp/cookbook",
        ),
        patch(
            "souschef.ci.jenkins_pipeline.generate_jenkinsfile_from_chef_ci",
            side_effect=FileNotFoundError("missing"),
        ),
    ):
        result = generate_jenkinsfile_from_chef("/tmp/cookbook")

    assert "Could not find file" in result


def test_generate_gitlab_ci_success() -> None:
    """GitLab CI generation returns content on success."""
    with (
        patch(
            "souschef.server._normalise_workspace_path",
            return_value="/tmp/cookbook",
        ),
        patch(
            "souschef.ci.gitlab_ci.generate_gitlab_ci_from_chef_ci",
            return_value="gitlab",
        ) as mock_gen,
    ):
        result = generate_gitlab_ci_from_chef(
            cookbook_path="/tmp/cookbook",
            enable_cache="yes",
            enable_artifacts="no",
        )

    assert result == "gitlab"
    assert mock_gen.called


def test_generate_gitlab_ci_file_not_found() -> None:
    """GitLab CI generation handles FileNotFoundError."""
    with (
        patch(
            "souschef.server._normalise_workspace_path",
            return_value="/tmp/cookbook",
        ),
        patch(
            "souschef.ci.gitlab_ci.generate_gitlab_ci_from_chef_ci",
            side_effect=FileNotFoundError("missing"),
        ),
    ):
        result = generate_gitlab_ci_from_chef("/tmp/cookbook")

    assert "Could not find file" in result


def test_generate_github_workflow_success() -> None:
    """GitHub workflow generation returns content on success."""
    with (
        patch(
            "souschef.server._normalize_path",
            return_value="/tmp/cookbook",
        ),
        patch(
            "souschef.ci.github_actions.generate_github_workflow_from_chef_ci",
            return_value="workflow",
        ) as mock_gen,
    ):
        result = generate_github_workflow_from_chef(
            cookbook_path="/tmp/cookbook",
            enable_cache="no",
            enable_artifacts="yes",
        )

    assert result == "workflow"
    assert mock_gen.called


def test_generate_github_workflow_file_not_found() -> None:
    """GitHub workflow generation handles FileNotFoundError."""
    with (
        patch(
            "souschef.server._normalize_path",
            return_value="/tmp/cookbook",
        ),
        patch(
            "souschef.ci.github_actions.generate_github_workflow_from_chef_ci",
            side_effect=FileNotFoundError("missing"),
        ),
    ):
        result = generate_github_workflow_from_chef("/tmp/cookbook")

    assert "Could not find file" in result
