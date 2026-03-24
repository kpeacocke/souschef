"""Webhook delivery helpers for SousChef automation workflows."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import requests

from souschef.core.url_validation import validate_user_provided_url

DEFAULT_WEBHOOK_TIMEOUT_SECONDS = 10


def _build_signature(secret: str, payload: bytes) -> str:
    """Build an HMAC SHA-256 signature for webhook payloads."""
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256)
    return f"sha256={digest.hexdigest()}"


def build_webhook_headers(
    event: str,
    payload: bytes,
    secret: str = "",
) -> dict[str, str]:
    """Build standard webhook headers for outbound delivery."""
    headers = {
        "Content-Type": "application/json",
        "X-SousChef-Event": event,
    }
    if secret:
        headers["X-SousChef-Signature"] = _build_signature(secret, payload)
    return headers


def send_webhook_notification(
    url: str,
    event: str,
    payload: dict[str, Any],
    *,
    secret: str = "",
    timeout: int = DEFAULT_WEBHOOK_TIMEOUT_SECONDS,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Send a JSON webhook notification to a validated endpoint."""
    validated_url = validate_user_provided_url(url, strip_path=False)
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    headers = build_webhook_headers(event, payload_bytes, secret)
    client = session or requests.Session()

    try:
        response = client.post(
            validated_url,
            data=payload_bytes,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return {
            "status": "error",
            "event": event,
            "url": validated_url,
            "error": str(exc),
        }

    return {
        "status": "success",
        "event": event,
        "url": validated_url,
        "status_code": response.status_code,
    }
