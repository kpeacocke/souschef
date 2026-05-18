"""API facade for SCM integration connectors and artifact linkage."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from souschef.audit import log_event
from souschef.integrations.scm_connector import (
    ExternalReference,
    ReferenceType,
    get_connector,
)
from souschef.storage import get_storage_manager


def _resolve_storage(storage_manager=None):
    """Resolve storage manager instance for API operations."""
    return storage_manager if storage_manager is not None else get_storage_manager()


def validate_provider_credentials(
    provider: str,
    credentials: Mapping[str, str],
) -> bool:
    """Validate provider credential payload using connector rules."""
    get_connector(provider=provider, config=credentials)
    return True


def build_external_reference(
    provider: str,
    credentials: Mapping[str, str],
    reference_type: ReferenceType,
    reference_id: str,
) -> ExternalReference:
    """Build provider-specific issue/PR reference payload."""
    connector = get_connector(provider=provider, config=credentials)
    return connector.build_reference(
        reference_id=reference_id,
        reference_type=reference_type,
    )


def link_conversion_artifact_reference(
    workspace_id: str,
    actor_user_id: str,
    cookbook_name: str,
    output_type: str,
    status: str,
    files_generated: int,
    conversion_data: dict[str, Any],
    provider: str,
    credentials: Mapping[str, str],
    reference_type: ReferenceType,
    reference_id: str,
    analysis_id: int | None = None,
    storage_manager=None,
) -> tuple[int | None, ExternalReference]:
    """Create conversion record linked to an external issue/PR reference."""
    from souschef.api.workspace_api import create_conversion_record

    storage = _resolve_storage(storage_manager)
    reference = build_external_reference(
        provider=provider,
        credentials=credentials,
        reference_type=reference_type,
        reference_id=reference_id,
    )

    linked_payload = dict(conversion_data)
    references = list(linked_payload.get("external_references", []))
    references.append(reference.to_dict())
    linked_payload["external_references"] = references

    conversion_id = create_conversion_record(
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        cookbook_name=cookbook_name,
        output_type=output_type,
        status=status,
        files_generated=files_generated,
        conversion_data=linked_payload,
        analysis_id=analysis_id,
        storage_manager=storage,
    )

    log_event(
        storage_manager=storage,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        event_type="integration",
        action="artifact_reference_linked",
        details={
            "conversion_id": conversion_id,
            "provider": provider,
            "reference_type": reference.reference_type,
            "reference_id": reference.reference_id,
            "reference_url": reference.url,
        },
    )

    return conversion_id, reference
