"""Integration-style tests for provider-mocked SCM connector workflows."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from souschef.api.integration_api import link_conversion_artifact_reference


@patch("souschef.api.integration_api.log_event")
@patch("souschef.api.workspace_api.log_event")
def test_github_linkage_flow_with_mocked_provider(
    workspace_log_event,
    integration_log_event,
) -> None:
    """GitHub linkage flow should append PR reference and persist conversion."""
    storage_manager = MagicMock()
    storage_manager.get_workspace_role.return_value = "owner"
    storage_manager.save_conversion.return_value = 301

    conversion_id, reference = link_conversion_artifact_reference(
        workspace_id="ws-1",
        actor_user_id="owner",
        cookbook_name="redis",
        output_type="role",
        status="success",
        files_generated=3,
        conversion_data={"result": "ok"},
        provider="github",
        credentials={"token": "token", "repo": "org/repo"},
        reference_type="pr",
        reference_id="451",
        storage_manager=storage_manager,
    )

    assert conversion_id == 301
    assert reference.url == "https://github.com/org/repo/pull/451"
    persisted = storage_manager.save_conversion.call_args.kwargs["conversion_data"]
    assert persisted["external_references"][0]["provider"] == "github"
    assert workspace_log_event.called
    assert integration_log_event.called


@patch("souschef.api.integration_api.log_event")
@patch("souschef.api.workspace_api.log_event")
def test_gitlab_linkage_flow_with_mocked_provider(
    workspace_log_event,
    integration_log_event,
) -> None:
    """GitLab linkage flow should append issue reference and persist conversion."""
    storage_manager = MagicMock()
    storage_manager.get_workspace_role.return_value = "owner"
    storage_manager.save_conversion.return_value = 402

    conversion_id, reference = link_conversion_artifact_reference(
        workspace_id="ws-2",
        actor_user_id="owner",
        cookbook_name="nginx",
        output_type="collection",
        status="success",
        files_generated=7,
        conversion_data={"result": "ok"},
        provider="gitlab",
        credentials={"token": "token", "project_path": "group/project"},
        reference_type="issue",
        reference_id="12",
        storage_manager=storage_manager,
    )

    assert conversion_id == 402
    assert reference.url == "https://gitlab.com/group/project/-/issues/12"
    persisted = storage_manager.save_conversion.call_args.kwargs["conversion_data"]
    assert persisted["external_references"][0]["provider"] == "gitlab"
    assert workspace_log_event.called
    assert integration_log_event.called
