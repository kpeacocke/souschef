"""Unit tests for souschef.webhooks."""

from __future__ import annotations

import hashlib
import hmac
from unittest.mock import MagicMock, patch

from souschef.webhooks import (
    _build_signature,
    build_webhook_headers,
    requests,
    send_webhook_notification,
)


def test_build_signature_uses_hmac_sha256() -> None:
    """Webhook signatures use the expected HMAC SHA-256 format."""
    payload = b'{"status": "ok"}'
    expected = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()

    assert _build_signature("secret", payload) == f"sha256={expected}"


def test_build_webhook_headers_without_secret() -> None:
    """Unsigned webhooks omit the signature header."""
    headers = build_webhook_headers("conversion.completed", b"{}")

    assert headers == {
        "Content-Type": "application/json",
        "X-SousChef-Event": "conversion.completed",
    }


def test_build_webhook_headers_with_secret() -> None:
    """Signed webhooks include the signature header."""
    headers = build_webhook_headers("conversion.completed", b"{}", "secret")

    assert headers["Content-Type"] == "application/json"
    assert headers["X-SousChef-Event"] == "conversion.completed"
    assert headers["X-SousChef-Signature"].startswith("sha256=")


def test_send_webhook_notification_success() -> None:
    """Successful webhook delivery returns metadata about the call."""
    session = MagicMock()
    response = MagicMock(status_code=202)
    session.post.return_value = response

    with patch(
        "souschef.webhooks.validate_user_provided_url",
        return_value="https://hooks.example.test/notify",
    ):
        result = send_webhook_notification(
            "https://hooks.example.test/notify",
            "conversion.completed",
            {"status": "ok"},
            secret="shared-secret",
            timeout=5,
            session=session,
        )

    assert result == {
        "status": "success",
        "event": "conversion.completed",
        "url": "https://hooks.example.test/notify",
        "status_code": 202,
    }
    session.post.assert_called_once()
    _, kwargs = session.post.call_args
    assert kwargs["timeout"] == 5
    assert kwargs["headers"]["X-SousChef-Signature"].startswith("sha256=")


def test_send_webhook_notification_handles_request_error() -> None:
    """Request failures return an error payload."""
    session = MagicMock()
    session.post.side_effect = requests.RequestException("network down")

    with patch(
        "souschef.webhooks.validate_user_provided_url",
        return_value="https://hooks.example.test/notify",
    ):
        result = send_webhook_notification(
            "https://hooks.example.test/notify",
            "conversion.completed",
            {"status": "ok"},
            session=session,
        )

    assert result == {
        "status": "error",
        "event": "conversion.completed",
        "url": "https://hooks.example.test/notify",
        "error": "network down",
    }


def test_send_webhook_notification_uses_default_session() -> None:
    """A requests session is created when one is not supplied."""
    response = MagicMock(status_code=200)
    session = MagicMock()
    session.post.return_value = response

    with (
        patch(
            "souschef.webhooks.validate_user_provided_url",
            return_value="https://hooks.example.test/notify",
        ),
        patch(
            "souschef.webhooks.requests.Session", return_value=session
        ) as mock_session,
    ):
        result = send_webhook_notification(
            "https://hooks.example.test/notify",
            "conversion.completed",
            {"status": "ok"},
        )

    assert result["status"] == "success"
    mock_session.assert_called_once_with()
