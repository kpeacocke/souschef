"""SCM connector abstractions for GitHub and GitLab issue/PR linkage."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

ReferenceType = Literal["issue", "pr"]


class IntegrationCredentialError(ValueError):
    """Raised when provider credential payload is invalid."""


@dataclass(frozen=True)
class ExternalReference:
    """Represents an issue or pull-request style external reference."""

    provider: str
    reference_type: ReferenceType
    reference_id: str
    url: str

    def to_dict(self) -> dict[str, str]:
        """Serialise reference to a plain dictionary payload."""
        return {
            "provider": self.provider,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "url": self.url,
        }


@dataclass(frozen=True)
class GitHubConnector:
    """GitHub issue/PR linker implementation."""

    repo: str
    base_url: str = "https://github.com"
    provider: str = "github"

    def validate_credentials(self, credentials: Mapping[str, str]) -> None:
        """Validate required GitHub credentials and repository context."""
        token = credentials.get("token", "").strip()
        if not token:
            raise IntegrationCredentialError("GitHub credential requires 'token'.")

        if "/" not in self.repo or len(self.repo.split("/")) != 2:
            raise IntegrationCredentialError(
                "GitHub connector requires repo in 'owner/name' format."
            )

    def build_reference(
        self,
        reference_id: str,
        reference_type: ReferenceType,
    ) -> ExternalReference:
        """Build GitHub issue or pull-request URL from reference ID."""
        normalised_id = reference_id.strip()
        if not normalised_id:
            raise ValueError("reference_id must not be empty")

        if reference_type == "issue":
            url = f"{self.base_url}/{self.repo}/issues/{normalised_id}"
        elif reference_type == "pr":
            url = f"{self.base_url}/{self.repo}/pull/{normalised_id}"
        else:
            raise ValueError(f"Unsupported reference type: {reference_type}")

        return ExternalReference(
            provider=self.provider,
            reference_type=reference_type,
            reference_id=normalised_id,
            url=url,
        )


@dataclass(frozen=True)
class GitLabConnector:
    """GitLab issue/MR linker implementation."""

    project_path: str | None = None
    project_id: str | None = None
    base_url: str = "https://gitlab.com"
    provider: str = "gitlab"

    def validate_credentials(self, credentials: Mapping[str, str]) -> None:
        """Validate required GitLab credentials and project context."""
        token = credentials.get("token", "").strip()
        if not token:
            raise IntegrationCredentialError("GitLab credential requires 'token'.")

        if not (self.project_path or self.project_id):
            raise IntegrationCredentialError(
                "GitLab connector requires 'project_path' or 'project_id'."
            )

    def build_reference(
        self,
        reference_id: str,
        reference_type: ReferenceType,
    ) -> ExternalReference:
        """Build GitLab issue or merge-request URL from reference ID."""
        normalised_id = reference_id.strip()
        if not normalised_id:
            raise ValueError("reference_id must not be empty")

        if self.project_path:
            project_segment = self.project_path
        elif self.project_id:
            project_segment = f"projects/{self.project_id}"
        else:
            raise IntegrationCredentialError(
                "GitLab connector requires project context to build URLs."
            )

        if reference_type == "issue":
            url = f"{self.base_url}/{project_segment}/-/issues/{normalised_id}"
        elif reference_type == "pr":
            url = f"{self.base_url}/{project_segment}/-/merge_requests/{normalised_id}"
        else:
            raise ValueError(f"Unsupported reference type: {reference_type}")

        return ExternalReference(
            provider=self.provider,
            reference_type=reference_type,
            reference_id=normalised_id,
            url=url,
        )


def get_connector(
    provider: str,
    config: Mapping[str, str],
) -> GitHubConnector | GitLabConnector:
    """Create a provider connector from generic config payload."""
    provider_name = provider.strip().lower()

    if provider_name == "github":
        connector: GitHubConnector | GitLabConnector = GitHubConnector(
            repo=config.get("repo", "").strip()
        )
    elif provider_name == "gitlab":
        connector = GitLabConnector(
            project_path=config.get("project_path", "").strip() or None,
            project_id=config.get("project_id", "").strip() or None,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    connector.validate_credentials(config)
    return connector
