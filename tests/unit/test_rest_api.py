"""Unit tests for souschef.rest_api."""

from __future__ import annotations

import io
import json
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from souschef.rest_api import (
    SousChefRestApi,
    _coerce_result,
    _decode_json_body,
    handle_rest_request,
    run_api_server,
)


def test_decode_json_body_empty() -> None:
    """Empty request bodies decode to an empty object."""
    assert _decode_json_body(b"") == {}


def test_decode_json_body_rejects_non_object() -> None:
    """Non-object JSON payloads are rejected."""
    try:
        _decode_json_body(b"[]")
    except ValueError as exc:
        assert "JSON object" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for non-object JSON")


def test_coerce_result_parses_json_strings() -> None:
    """JSON strings are converted to structured data."""
    assert _coerce_result('{"status": "ok"}') == {"status": "ok"}


def test_coerce_result_preserves_plain_text() -> None:
    """Plain text results are returned unchanged."""
    assert _coerce_result("plain text") == "plain text"


def test_handle_rest_request_health_route() -> None:
    """Health route returns an OK payload."""
    status, payload = handle_rest_request("GET", "/health")

    assert status == HTTPStatus.OK
    assert payload == {"status": "ok", "service": "souschef-rest-api"}


def test_handle_rest_request_operations_route() -> None:
    """Operations route lists the supported operation names."""
    status, payload = handle_rest_request("GET", "/api/v1/operations")

    assert status == HTTPStatus.OK
    assert "parse_recipe" in payload["operations"]
    assert "import_puppet_catalog_to_ir" in payload["operations"]


def test_handle_rest_request_run_success_with_webhook() -> None:
    """Successful operation runs can also trigger a webhook."""
    request_body = json.dumps(
        {
            "operation": "demo",
            "arguments": {"name": "world"},
            "webhook_url": "https://hooks.example.test/notify",
            "webhook_secret": "secret",
        }
    ).encode("utf-8")

    with (
        patch(
            "souschef.rest_api._supported_operations",
            return_value={"demo": lambda name: json.dumps({"hello": name})},
        ),
        patch(
            "souschef.rest_api.send_webhook_notification",
            return_value={"status": "success", "status_code": 202},
        ) as mock_webhook,
    ):
        status, payload = handle_rest_request("POST", "/api/v1/run", request_body)

    assert status == HTTPStatus.OK
    assert payload["status"] == "success"
    assert payload["result"] == {"hello": "world"}
    assert payload["webhook"] == {"status": "success", "status_code": 202}
    mock_webhook.assert_called_once_with(
        "https://hooks.example.test/notify",
        "operation.completed",
        payload,
        secret="secret",
    )


def test_handle_rest_request_run_requires_operation_name() -> None:
    """Run requests require an operation name."""
    status, payload = handle_rest_request(
        "POST",
        "/api/v1/run",
        b'{"arguments": {}}',
    )

    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "Operation name is required"}


def test_handle_rest_request_run_requires_object_arguments() -> None:
    """Run requests require argument objects."""
    status, payload = handle_rest_request(
        "POST",
        "/api/v1/run",
        b'{"operation": "parse_recipe", "arguments": []}',
    )

    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "Arguments must be a JSON object"}


def test_handle_rest_request_run_unknown_operation() -> None:
    """Unknown operations return not found."""
    status, payload = handle_rest_request(
        "POST",
        "/api/v1/run",
        b'{"operation": "missing", "arguments": {}}',
    )

    assert status == HTTPStatus.NOT_FOUND
    assert payload == {"error": "Unknown operation: missing"}


def test_handle_rest_request_run_invalid_arguments_error_mapping() -> None:
    """Argument errors from operations map to bad request responses."""
    request_body = b'{"operation": "demo", "arguments": {"count": "x"}}'

    def _raise_value_error(**_: object) -> str:
        raise ValueError("count must be an integer")

    with patch(
        "souschef.rest_api._supported_operations",
        return_value={"demo": _raise_value_error},
    ):
        status, payload = handle_rest_request("POST", "/api/v1/run", request_body)

    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "Invalid arguments: count must be an integer"}


def test_handle_rest_request_run_runtime_error_mapping() -> None:
    """Runtime operation failures map to bad gateway responses."""
    request_body = b'{"operation": "demo", "arguments": {}}'

    def _raise_runtime_error(**_: object) -> str:
        raise RuntimeError("upstream service unavailable")

    with patch(
        "souschef.rest_api._supported_operations",
        return_value={"demo": _raise_runtime_error},
    ):
        status, payload = handle_rest_request("POST", "/api/v1/run", request_body)

    assert status == HTTPStatus.BAD_GATEWAY
    assert payload == {"error": "upstream service unavailable"}


def test_handle_rest_request_run_rejects_invalid_webhook_url() -> None:
    """Run route rejects invalid webhook URLs before delivery attempts."""
    request_body = json.dumps(
        {
            "operation": "demo",
            "arguments": {},
            "webhook_url": "http://127.0.0.1/internal",
        }
    ).encode("utf-8")

    with (
        patch(
            "souschef.rest_api._supported_operations",
            return_value={"demo": lambda: json.dumps({"ok": True})},
        ),
        patch(
            "souschef.rest_api.validate_user_provided_url",
            side_effect=ValueError("Host is not allowed"),
        ),
    ):
        status, payload = handle_rest_request("POST", "/api/v1/run", request_body)

    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "Invalid webhook URL: Host is not allowed"}


def test_handle_rest_request_webhook_notify_success() -> None:
    """Webhook notify route returns a success payload."""
    request_body = json.dumps(
        {
            "url": "https://hooks.example.test/notify",
            "event": "migration.completed",
            "payload": {"status": "ok"},
            "secret": "shared-secret",
        }
    ).encode("utf-8")

    with patch(
        "souschef.rest_api.send_webhook_notification",
        return_value={"status": "success", "status_code": 200},
    ) as mock_webhook:
        status, payload = handle_rest_request(
            "POST",
            "/api/v1/webhooks/notify",
            request_body,
        )

    assert status == HTTPStatus.OK
    assert payload == {"status": "success", "status_code": 200}
    mock_webhook.assert_called_once_with(
        "https://hooks.example.test/notify",
        "migration.completed",
        {"status": "ok"},
        secret="shared-secret",
    )


def test_handle_rest_request_webhook_notify_failure() -> None:
    """Webhook delivery failures map to bad gateway."""
    request_body = json.dumps(
        {
            "url": "https://hooks.example.test/notify",
            "event": "migration.completed",
            "payload": {"status": "ok"},
        }
    ).encode("utf-8")

    with patch(
        "souschef.rest_api.send_webhook_notification",
        return_value={"status": "error", "error": "boom"},
    ):
        status, payload = handle_rest_request(
            "POST",
            "/api/v1/webhooks/notify",
            request_body,
        )

    assert status == HTTPStatus.BAD_GATEWAY
    assert payload == {"status": "error", "error": "boom"}


def test_handle_rest_request_webhook_notify_rejects_invalid_url() -> None:
    """Webhook notify route validates URL and rejects unsafe values."""
    request_body = json.dumps(
        {
            "url": "http://169.254.169.254/latest/meta-data",
            "event": "migration.completed",
            "payload": {"status": "ok"},
        }
    ).encode("utf-8")

    with patch(
        "souschef.rest_api.validate_user_provided_url",
        side_effect=ValueError("Host is not allowed"),
    ):
        status, payload = handle_rest_request(
            "POST",
            "/api/v1/webhooks/notify",
            request_body,
        )

    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "Invalid webhook URL: Host is not allowed"}


def test_handle_rest_request_invalid_json() -> None:
    """Invalid JSON request bodies are rejected."""
    status, payload = handle_rest_request("POST", "/api/v1/run", b"{")

    assert status == HTTPStatus.BAD_REQUEST
    assert "error" in payload


def test_handle_rest_request_unknown_route() -> None:
    """Unknown routes return not found."""
    status, payload = handle_rest_request("DELETE", "/missing")

    assert status == HTTPStatus.NOT_FOUND
    assert payload == {"error": "Unknown route: DELETE /missing"}


def test_handle_rest_request_webhook_notify_rejects_invalid_url() -> None:
    """Webhook notify route validates URL and rejects unsafe values."""
    request_body = json.dumps(
        {
            "url": "http://169.254.169.254/latest/meta-data",
            "event": "migration.completed",
            "payload": {"status": "ok"},
        }
    ).encode("utf-8")

    with patch(
        "souschef.rest_api.validate_user_provided_url",
        side_effect=ValueError("Host is not allowed"),
    ):
        status, payload = handle_rest_request(
            "POST",
            "/api/v1/webhooks/notify",
            request_body,
        )

    assert status == HTTPStatus.BAD_REQUEST
    assert payload == {"error": "Invalid webhook URL: Host is not allowed"}


def test_wsgi_app_invokes_handler() -> None:
    """The WSGI wrapper serialises the route response."""
    app = SousChefRestApi()
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/api/v1/run",
        "CONTENT_LENGTH": "2",
        "wsgi.input": io.BytesIO(b"{}"),
    }
    start_response = MagicMock()

    with patch(
        "souschef.rest_api.handle_rest_request",
        return_value=(HTTPStatus.OK, {"status": "ok"}),
    ) as mock_handler:
        chunks = app(environ, start_response)

    assert json.loads(chunks[0].decode("utf-8")) == {"status": "ok"}
    mock_handler.assert_called_once_with("POST", "/api/v1/run", b"{}")
    start_response.assert_called_once()


def test_run_api_server_starts_wsgi_server() -> None:
    """run_api_server delegates to the standard-library WSGI server."""
    mock_server = MagicMock()
    mock_server.__enter__.return_value = mock_server
    mock_server.__exit__.return_value = None

    with patch(
        "souschef.rest_api.make_server", return_value=mock_server
    ) as mock_make_server:
        run_api_server(host="0.0.0.0", port=9999)

    mock_make_server.assert_called_once()
    mock_server.serve_forever.assert_called_once()
