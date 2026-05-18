"""Unit tests for API integration facade and artifact linkage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from souschef.api.integration_api import (
    build_external_reference,
    link_conversion_artifact_reference,
    validate_provider_credentials,
)


def test_validate_provider_credentials_accepts_valid_payload() -> None:
    """Credential validation should succeed for valid provider payload."""
    assert validate_provider_credentials(
        "github",
        {"token": "abc", "repo": "octo/repo"},
    )


def test_build_external_reference_creates_provider_url() -> None:
    """Reference builder should resolve provider URL for issue references."""
    reference = build_external_reference(
        provider="github",
        credentials={"token": "abc", "repo": "octo/repo"},
        reference_type="issue",
        reference_id="99",
    )

    assert reference.provider == "github"
    assert reference.url.endswith("/issues/99")


@patch("souschef.api.integration_api.log_event")
@patch("souschef.api.workspace_api.log_event")
def test_link_conversion_artifact_reference_enriches_payload_and_logs(
    workspace_log_event,
    integration_log_event,
) -> None:
    """Artifact linker should append external references and emit integration audit."""
    storage_manager = MagicMock()
    storage_manager.get_workspace_role.return_value = "owner"
    storage_manager.save_conversion.return_value = 55

    conversion_id, reference = link_conversion_artifact_reference(
        workspace_id="ws-1",
        actor_user_id="owner",
        cookbook_name="nginx",
        output_type="role",
        status="success",
        files_generated=4,
        conversion_data={"summary": "ok"},
        provider="github",
        credentials={"token": "abc", "repo": "octo/repo"},
        reference_type="pr",
        reference_id="17",
        analysis_id=22,
        storage_manager=storage_manager,
    )

    assert conversion_id == 55
    assert reference.url.endswith("/pull/17")
    saved_payload = storage_manager.save_conversion.call_args.kwargs["conversion_data"]
    assert len(saved_payload["external_references"]) == 1
    assert saved_payload["external_references"][0]["reference_id"] == "17"
    assert workspace_log_event.called
    assert integration_log_event.called
