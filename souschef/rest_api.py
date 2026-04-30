"""Lightweight REST API and webhook surface for SousChef."""

from __future__ import annotations

import json
import logging
from http import HTTPStatus
from typing import Any
from wsgiref.simple_server import make_server

from souschef.core.url_validation import validate_user_provided_url
from souschef.server import (
    convert_puppet_manifest_to_ansible,
    import_puppet_catalog_to_ir,
    list_puppet_server_nodes,
    parse_recipe,
    validate_conversion,
)
from souschef.webhooks import send_webhook_notification

JsonObject = dict[str, Any]
RouteResponse = tuple[HTTPStatus, JsonObject]
LOGGER = logging.getLogger(__name__)


def _supported_operations() -> dict[str, Any]:
    """Return the REST-exposed operation map."""
    return {
        "parse_recipe": parse_recipe,
        "validate_conversion": validate_conversion,
        "convert_puppet_manifest_to_ansible": convert_puppet_manifest_to_ansible,
        "list_puppet_server_nodes": list_puppet_server_nodes,
        "import_puppet_catalog_to_ir": import_puppet_catalog_to_ir,
    }


def _decode_json_body(body: bytes) -> JsonObject:
    """Decode a JSON body into a dictionary."""
    if not body:
        return {}

    decoded = json.loads(body.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("Request body must decode to a JSON object")
    return decoded


def _coerce_result(result: Any) -> Any:
    """Coerce server return values into structured JSON when possible."""
    if not isinstance(result, str):
        return result

    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return result


def _route_health() -> RouteResponse:
    """Return a basic health-check response."""
    return HTTPStatus.OK, {"status": "ok", "service": "souschef-rest-api"}


def _route_operations() -> RouteResponse:
    """Return supported REST operations."""
    return HTTPStatus.OK, {"operations": sorted(_supported_operations())}


def _route_run(request: JsonObject) -> RouteResponse:
    """Run a named SousChef operation via JSON request."""
    operation = request.get("operation", "")
    arguments = request.get("arguments", {})

    if not isinstance(operation, str) or not operation:
        return HTTPStatus.BAD_REQUEST, {"error": "Operation name is required"}
    if not isinstance(arguments, dict):
        return HTTPStatus.BAD_REQUEST, {"error": "Arguments must be a JSON object"}

    operations = _supported_operations()
    if operation not in operations:
        return HTTPStatus.NOT_FOUND, {"error": f"Unknown operation: {operation}"}

    try:
        result = operations[operation](**arguments)
    except TypeError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": f"Invalid arguments: {exc}"}
    except RuntimeError as exc:
        return HTTPStatus.BAD_GATEWAY, {"error": str(exc)}
    except ValueError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": f"Invalid arguments: {exc}"}
    response: JsonObject = {
        "status": "success",
        "operation": operation,
        "result": _coerce_result(result),
    }

    webhook_url = request.get("webhook_url", "")
    webhook_secret = request.get("webhook_secret", "")
    if isinstance(webhook_url, str) and webhook_url:
        try:
            webhook_url = validate_user_provided_url(webhook_url)
        except ValueError as exc:
            return HTTPStatus.BAD_REQUEST, {"error": f"Invalid webhook URL: {exc}"}
        webhook_result = send_webhook_notification(
            webhook_url,
            "operation.completed",
            response,
            secret=webhook_secret if isinstance(webhook_secret, str) else "",
        )
        response["webhook"] = webhook_result

    return HTTPStatus.OK, response


def _route_webhook_notify(request: JsonObject) -> RouteResponse:
    """Deliver a webhook notification from the REST surface."""
    url = request.get("url", "")
    event = request.get("event", "")
    payload = request.get("payload", {})
    secret = request.get("secret", "")

    if not isinstance(url, str) or not url:
        return HTTPStatus.BAD_REQUEST, {"error": "Webhook URL is required"}
    if not isinstance(event, str) or not event:
        return HTTPStatus.BAD_REQUEST, {"error": "Webhook event is required"}
    if not isinstance(payload, dict):
        return HTTPStatus.BAD_REQUEST, {
            "error": "Webhook payload must be a JSON object"
        }

    try:
        safe_url = validate_user_provided_url(url, strip_path=False)
    except ValueError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": f"Invalid webhook URL: {exc}"}

    result = send_webhook_notification(
        safe_url,
        event,
        payload,
        secret=secret if isinstance(secret, str) else "",
    )
    status = HTTPStatus.OK if result["status"] == "success" else HTTPStatus.BAD_GATEWAY
    return status, result


def handle_rest_request(method: str, path: str, body: bytes = b"") -> RouteResponse:
    """Handle a REST request in a testable, framework-free manner."""
    try:
        request = _decode_json_body(body)
    except ValueError as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}

    if method == "GET" and path == "/health":
        return _route_health()
    if method == "GET" and path == "/api/v1/operations":
        return _route_operations()
    if method == "POST" and path == "/api/v1/run":
        return _route_run(request)
    if method == "POST" and path == "/api/v1/webhooks/notify":
        return _route_webhook_notify(request)
    return HTTPStatus.NOT_FOUND, {"error": f"Unknown route: {method} {path}"}


class SousChefRestApi:
    """WSGI wrapper around the lightweight REST handlers."""

    def __call__(self, environ: dict[str, Any], start_response: Any) -> list[bytes]:
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")
        body_length = int(environ.get("CONTENT_LENGTH") or 0)
        body = environ["wsgi.input"].read(body_length) if body_length else b""
        status, payload = handle_rest_request(method, path, body)
        response_bytes = json.dumps(payload, indent=2).encode("utf-8")
        headers = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_bytes))),
        ]
        start_response(f"{status.value} {status.phrase}", headers)
        return [response_bytes]


def run_api_server(host: str = "127.0.0.1", port: int = 8081) -> None:
    """Run the SousChef REST API using the standard library server."""
    app = SousChefRestApi()
    with make_server(host, port, app) as httpd:
        LOGGER.info("SousChef REST API listening on http://%s:%s", host, port)
        httpd.serve_forever()
