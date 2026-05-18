"""Integrations component for SousChef architecture boundaries."""

from souschef.integrations.scm_connector import (
    ExternalReference,
    GitHubConnector,
    GitLabConnector,
    IntegrationCredentialError,
    ReferenceType,
    get_connector,
)

__all__ = [
    "ExternalReference",
    "GitHubConnector",
    "GitLabConnector",
    "IntegrationCredentialError",
    "ReferenceType",
    "get_connector",
]
