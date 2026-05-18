"""Integrations component for SousChef architecture boundaries."""

from souschef.integrations.scm_connector import (
    ExternalReference,
    GitHubConnector,
    GitLabConnector,
    IntegrationCredentialError,
    ReferenceType,
    get_connector,
)
from souschef.integrations.ticket_sync import (
    TicketCredentialError,
    TicketProvider,
    TicketSyncResult,
    TransientTicketSyncError,
    format_ticket_sync_status,
    sync_ticket_with_retry,
)

__all__ = [
    "ExternalReference",
    "GitHubConnector",
    "GitLabConnector",
    "IntegrationCredentialError",
    "ReferenceType",
    "get_connector",
    "TicketProvider",
    "TicketSyncResult",
    "TicketCredentialError",
    "TransientTicketSyncError",
    "sync_ticket_with_retry",
    "format_ticket_sync_status",
]
