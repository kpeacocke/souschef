"""Additional edge-case tests for souschef.rest_api."""

from __future__ import annotations

import io
import math
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from souschef.rest_api import SousChefRestApi, _vector_similarity, handle_rest_request


def test_migration_analyse_rejects_invalid_list_and_field_types() -> None:
    """Analyse route validates list contents and string fields."""
    status, payload = handle_rest_request(
        "POST",
        "/api/v1/migration/analyse",
        b'{"cookbook_paths": ["ok", ""]}',
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert "list must contain non-empty strings" in payload["error"]

    status, payload = handle_rest_request(
        "POST",
        "/api/v1/migration/analyse",
        b'{"cookbook_paths": "ok", "migration_scope": 1}',
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "migration_scope must be a string"}

    status, payload = handle_rest_request(
        "POST",
        "/api/v1/migration/analyse",
        b'{"cookbook_paths": "ok", "target_platform": 1}',
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "target_platform must be a string"}


def test_migration_plan_rejects_invalid_list_and_strategy_type() -> None:
    """Plan route validates list contents and strategy type."""
    status, payload = handle_rest_request(
        "POST",
        "/api/v1/migration/plan",
        b'{"cookbook_paths": ["ok", ""]}',
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert "list must contain non-empty strings" in payload["error"]

    status, payload = handle_rest_request(
        "POST",
        "/api/v1/migration/plan",
        b'{"cookbook_paths": "ok", "migration_strategy": 9}',
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "migration_strategy must be a string"}


def test_migration_generate_playbook_rejects_non_string_cookbook_path() -> None:
    """Generate-playbook route validates cookbook_path type when provided."""
    status, payload = handle_rest_request(
        "POST",
        "/api/v1/migration/generate-playbook",
        b'{"recipe_path": "/tmp/recipe.rb", "cookbook_path": 123}',
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "cookbook_path must be a string"}


def test_context_query_rejects_non_string_path_and_non_alnum_query() -> None:
    """Context query validates path type and tokenisable query text."""
    status, payload = handle_rest_request(
        "POST",
        "/api/v1/context/query",
        b'{"query": "migration", "cookbook_path": 42}',
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "cookbook_path must be a string"}

    status, payload = handle_rest_request(
        "POST",
        "/api/v1/context/query",
        b'{"query": "!!!", "top_k": 2}',
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "query must contain alphanumeric content"}


def test_context_query_supports_keyword_and_vector_modes() -> None:
    """Context query should support keyword-only and vector-only retrieval."""
    keyword_status, keyword_payload = handle_rest_request(
        "POST",
        "/api/v1/context/query",
        b'{"query": "migration plan", "retrieval_mode": "keyword"}',
    )
    vector_status, vector_payload = handle_rest_request(
        "POST",
        "/api/v1/context/query",
        b'{"query": "migration plan", "retrieval_mode": "vector"}',
    )

    assert keyword_status == HTTPStatus.OK
    assert vector_status == HTTPStatus.OK
    assert keyword_payload["retrieval_mode"] == "keyword"
    assert vector_payload["retrieval_mode"] == "vector"


def test_context_query_stream_propagates_error_and_handles_non_list_matches() -> None:
    """Context stream should pass through errors and normalise non-list matches."""
    status, payload = handle_rest_request(
        "POST",
        "/api/v1/context/query/stream",
        b'{"top_k": 2}',
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "query is required"}

    with patch(
        "souschef.rest_api._route_context_query",
        return_value=(HTTPStatus.OK, {"query": "x", "top_k": 1, "matches": {}}),
    ):
        stream_status, stream_payload = handle_rest_request(
            "POST",
            "/api/v1/context/query/stream",
            b"{}",
        )

    assert stream_status == HTTPStatus.OK
    assert stream_payload["events"][-1]["event"] == "done"


def test_validation_profile_rejects_missing_or_invalid_fields() -> None:
    """Validation profile route requires result content and string profile."""
    status, payload = handle_rest_request(
        "POST",
        "/api/v1/validation/profile",
        b'{"conversion_type": "recipe"}',
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "result_content is required"}

    status, payload = handle_rest_request(
        "POST",
        "/api/v1/validation/profile",
        b'{"conversion_type": "recipe", "result_content": "x", "validation_profile": 7}',
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "validation_profile must be a string"}


def test_validation_profile_maps_upstream_non_ok_and_bad_payloads() -> None:
    """Validation profile route should map upstream and malformed payload failures."""
    with patch(
        "souschef.rest_api._invoke_operation",
        return_value=(HTTPStatus.BAD_GATEWAY, {"error": "upstream"}),
    ):
        status, payload = handle_rest_request(
            "POST",
            "/api/v1/validation/profile",
            b'{"conversion_type": "recipe", "result_content": "x"}',
        )
    assert status == HTTPStatus.BAD_GATEWAY
    assert payload == {"error": "upstream"}

    with patch(
        "souschef.rest_api._invoke_operation",
        return_value=(HTTPStatus.OK, {"result": "bad"}),
    ):
        status, payload = handle_rest_request(
            "POST",
            "/api/v1/validation/profile",
            b'{"conversion_type": "recipe", "result_content": "x"}',
        )
    assert status == HTTPStatus.BAD_GATEWAY
    assert "unexpected payload" in payload["error"]

    with patch(
        "souschef.rest_api._invoke_operation",
        return_value=(HTTPStatus.OK, {"result": {"summary": [], "results": {}}}),
    ):
        status, payload = handle_rest_request(
            "POST",
            "/api/v1/validation/profile",
            b'{"conversion_type": "recipe", "result_content": "x"}',
        )
    assert status == HTTPStatus.BAD_GATEWAY
    assert "invalid result structure" in payload["error"]


def test_validation_profile_stream_propagates_error_and_handles_non_list_results() -> (
    None
):
    """Validation profile stream should pass through errors and normalise non-list results."""
    status, payload = handle_rest_request(
        "POST",
        "/api/v1/validation/profile/stream",
        b'{"conversion_type": "recipe"}',
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "result_content is required"}

    with patch(
        "souschef.rest_api._route_validation_profile",
        return_value=(
            HTTPStatus.OK,
            {
                "profile": "safety",
                "conversion_type": "recipe",
                "results": {},
                "passed": True,
                "result_count": 0,
            },
        ),
    ):
        stream_status, stream_payload = handle_rest_request(
            "POST",
            "/api/v1/validation/profile/stream",
            b"{}",
        )
    assert stream_status == HTTPStatus.OK
    assert stream_payload["events"][-1]["event"] == "done"


def test_wsgi_stream_sanitises_invalid_event_shapes() -> None:
    """WSGI stream renderer should tolerate invalid event payload shapes."""
    app = SousChefRestApi()
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/api/v1/context/query/stream",
        "CONTENT_LENGTH": "2",
        "wsgi.input": io.BytesIO(b"{}"),
    }
    start_response = MagicMock()

    with patch(
        "souschef.rest_api.handle_rest_request",
        return_value=(HTTPStatus.OK, {"events": {"event": "x"}}),
    ):
        chunks = app(environ, start_response)
    assert chunks[0].decode("utf-8") == "\n"

    with patch(
        "souschef.rest_api.handle_rest_request",
        return_value=(
            HTTPStatus.OK,
            {"events": ["bad", {"event": "done", "data": {"ok": True}}]},
        ),
    ):
        chunks = app(environ, start_response)
    assert "event: done" in chunks[0].decode("utf-8")


def test_vector_similarity_returns_zero_for_empty_and_zero_norm_vectors() -> None:
    """Vector similarity should return zero for empty or zero-norm vectors."""
    assert math.isclose(_vector_similarity("", "migration"), 0.0)

    class _ZeroCounter(dict[str, int]):
        def __init__(self, tokens: list[str]) -> None:
            super().__init__(dict.fromkeys(tokens, 0))

    with patch("souschef.rest_api.Counter", _ZeroCounter):
        assert math.isclose(_vector_similarity("migration", "migration"), 0.0)
