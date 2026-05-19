"""Integration tests for the REST API request handlers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from souschef.rest_api import handle_rest_request

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_COOKBOOK = FIXTURES_DIR / "sample_cookbook"


def _request_bytes(payload: dict[str, object]) -> bytes:
    """Encode a dictionary payload as UTF-8 JSON bytes."""
    return json.dumps(payload).encode("utf-8")


@pytest.fixture
def workspace_root(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set workspace root for path containment checks."""
    root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(root))
    return root


def test_migration_analyse_endpoint_with_real_fixture(workspace_root: Path) -> None:
    """Analyse endpoint works end-to-end against fixture cookbook path."""
    del workspace_root

    status, payload = handle_rest_request(
        "POST",
        "/api/v1/migration/analyse",
        _request_bytes(
            {
                "cookbook_paths": [str(SAMPLE_COOKBOOK)],
                "migration_scope": "full",
                "target_platform": "ansible_awx",
            }
        ),
    )

    assert status.value == 200
    assert payload["status"] == "success"
    assert payload["operation"] == "assess_chef_migration_complexity"
    assert isinstance(payload["result"], str)


def test_migration_plan_endpoint_with_real_fixture(workspace_root: Path) -> None:
    """Migration planning endpoint returns a plan for fixture cookbook path."""
    del workspace_root

    status, payload = handle_rest_request(
        "POST",
        "/api/v1/migration/plan",
        _request_bytes(
            {
                "cookbook_paths": [str(SAMPLE_COOKBOOK)],
                "migration_strategy": "phased",
                "timeline_weeks": 6,
            }
        ),
    )

    assert status.value == 200
    assert payload["status"] == "success"
    assert payload["operation"] == "generate_migration_plan"
    assert isinstance(payload["result"], str)


def test_generate_playbook_endpoint_with_real_fixture(workspace_root: Path) -> None:
    """Generate-playbook endpoint converts a real fixture recipe."""
    del workspace_root

    status, payload = handle_rest_request(
        "POST",
        "/api/v1/migration/generate-playbook",
        _request_bytes(
            {
                "recipe_path": str(SAMPLE_COOKBOOK / "recipes" / "default.rb"),
                "cookbook_path": str(SAMPLE_COOKBOOK),
            }
        ),
    )

    assert status.value == 200
    assert payload["status"] == "success"
    assert payload["operation"] == "generate_playbook_from_recipe"
    assert isinstance(payload["result"], str)


def test_validation_profile_endpoint_with_real_payload() -> None:
    """Validation profile endpoint returns structured response without mocks."""
    status, payload = handle_rest_request(
        "POST",
        "/api/v1/validation/profile",
        _request_bytes(
            {
                "conversion_type": "recipe",
                "result_content": "- hosts: all\\n  tasks: []",
                "validation_profile": "moderate",
            }
        ),
    )

    assert status.value == 200
    assert payload["status"] == "success"
    assert payload["operation"] == "validate_conversion_with_profile"
    assert payload["profile"] == "moderate"
    assert isinstance(payload["results"], list)


def test_context_query_endpoint_with_real_cookbook_signals(
    workspace_root: Path,
) -> None:
    """Context query endpoint returns cookbook-derived context signals."""
    del workspace_root

    status, payload = handle_rest_request(
        "POST",
        "/api/v1/context/query",
        _request_bytes(
            {
                "query": "cookbook recipes structure",
                "top_k": 5,
                "cookbook_path": str(SAMPLE_COOKBOOK),
            }
        ),
    )

    assert status.value == 200
    assert payload["status"] == "success"
    assert payload["operation"] == "context_query"
    assert payload["cookbook_path"] == str(SAMPLE_COOKBOOK)
    assert any(match["kind"] == "cookbook_signal" for match in payload["matches"])


def test_context_query_stream_endpoint_with_real_fixture(workspace_root: Path) -> None:
    """Context query stream endpoint emits event envelopes."""
    del workspace_root

    status, payload = handle_rest_request(
        "POST",
        "/api/v1/context/query/stream",
        _request_bytes(
            {
                "query": "migration plan",
                "top_k": 3,
                "cookbook_path": str(SAMPLE_COOKBOOK),
                "retrieval_mode": "hybrid",
            }
        ),
    )

    assert status.value == 200
    assert payload["status"] == "success"
    assert payload["operation"] == "context_query_stream"
    assert payload["events"][0]["event"] == "start"
    assert payload["events"][-1]["event"] == "done"


def test_validation_profile_stream_endpoint_with_real_payload() -> None:
    """Validation profile stream endpoint emits result events."""
    status, payload = handle_rest_request(
        "POST",
        "/api/v1/validation/profile/stream",
        _request_bytes(
            {
                "conversion_type": "recipe",
                "result_content": "- hosts: all\n  tasks: []",
                "validation_profile": "safety",
            }
        ),
    )

    assert status.value == 200
    assert payload["status"] == "success"
    assert payload["operation"] == "validate_conversion_with_profile_stream"
    assert payload["events"][0]["event"] == "start"
    assert payload["events"][-1]["event"] == "done"
