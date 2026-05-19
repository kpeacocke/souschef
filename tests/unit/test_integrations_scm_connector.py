"""Unit tests for SCM connector provider implementations."""

from __future__ import annotations

from typing import cast

import pytest

from souschef.integrations.scm_connector import (
    GitHubConnector,
    GitLabConnector,
    IntegrationCredentialError,
    get_connector,
)


def test_github_connector_builds_issue_and_pr_links() -> None:
    """GitHub connector should produce valid issue and PR URLs."""
    connector = GitHubConnector(repo="octo/repo")
    connector.validate_credentials({"token": "abc"})

    issue = connector.build_reference("42", "issue")
    pr = connector.build_reference("73", "pr")

    assert issue.url == "https://github.com/octo/repo/issues/42"
    assert pr.url == "https://github.com/octo/repo/pull/73"
    assert issue.to_dict()["reference_id"] == "42"


def test_gitlab_connector_builds_issue_and_pr_links() -> None:
    """GitLab connector should produce valid issue and merge-request URLs."""
    connector = GitLabConnector(project_path="group/project")
    connector.validate_credentials({"token": "abc"})

    issue = connector.build_reference("11", "issue")
    pr = connector.build_reference("8", "pr")

    assert issue.url == "https://gitlab.com/group/project/-/issues/11"
    assert pr.url == "https://gitlab.com/group/project/-/merge_requests/8"


def test_connector_validation_rejects_missing_credentials() -> None:
    """Connector credential validation should fail without required fields."""
    with pytest.raises(IntegrationCredentialError):
        GitHubConnector(repo="octo/repo").validate_credentials({})

    with pytest.raises(IntegrationCredentialError):
        GitLabConnector(project_path="group/project").validate_credentials({})


def test_github_connector_rejects_invalid_repo_and_reference_inputs() -> None:
    """GitHub connector should validate repo format and reference inputs."""
    with pytest.raises(IntegrationCredentialError, match="owner/name"):
        GitHubConnector(repo="octo-only").validate_credentials({"token": "abc"})

    connector = GitHubConnector(repo="octo/repo")
    with pytest.raises(ValueError, match="must not be empty"):
        connector.build_reference("   ", "issue")

    with pytest.raises(ValueError, match="Unsupported reference type"):
        connector.build_reference("1", cast("object", "merge"))


def test_gitlab_connector_rejects_invalid_project_and_reference_inputs() -> None:
    """GitLab connector should validate project context and reference inputs."""
    with pytest.raises(IntegrationCredentialError, match="project_path"):
        GitLabConnector().validate_credentials({"token": "abc"})

    no_context_connector = GitLabConnector()
    with pytest.raises(IntegrationCredentialError, match="project context"):
        no_context_connector.build_reference("5", "issue")

    project_id_connector = GitLabConnector(project_id="123")
    issue = project_id_connector.build_reference("11", "issue")
    assert issue.url == "https://gitlab.com/projects/123/-/issues/11"

    with pytest.raises(ValueError, match="must not be empty"):
        project_id_connector.build_reference(" ", "issue")

    with pytest.raises(ValueError, match="Unsupported reference type"):
        project_id_connector.build_reference("2", cast("object", "merge"))


def test_get_connector_returns_provider_specific_implementation() -> None:
    """Connector factory should return matching provider implementation."""
    github = get_connector("github", {"token": "x", "repo": "octo/repo"})
    gitlab = get_connector(
        "gitlab",
        {"token": "x", "project_path": "group/project"},
    )

    assert github.provider == "github"
    assert gitlab.provider == "gitlab"

    with pytest.raises(ValueError):
        get_connector("unknown", {"token": "x"})
