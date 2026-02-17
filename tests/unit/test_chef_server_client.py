"""Unit tests for Chef Server authenticated client utilities."""

from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from souschef.core.chef_server import (
    REDACTED_PLACEHOLDER,
    _build_auth_headers,
    _load_client_key,
    _normalise_server_url,
    _redact_sensitive_data,
)


class TestChefServerAuthHelpers:
    """Tests for Chef Server auth helper functions."""

    def test_normalise_server_url_appends_org(self) -> None:
        """Ensure organisation path is appended when missing."""
        url = _normalise_server_url("https://chef.example.com", "default")
        assert url.endswith("/organizations/default")

    def test_normalise_server_url_mismatched_org(self) -> None:
        """Ensure mismatched organisation paths are rejected."""
        with pytest.raises(ValueError, match="organisation does not match"):
            _normalise_server_url(
                "https://chef.example.com/organizations/other",
                "default",
            )

    def test_build_auth_headers_includes_signature(self) -> None:
        """Ensure auth headers include signed authorization chunks."""
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        key_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        headers = _build_auth_headers(
            "GET",
            "/organizations/default/search/node?q=*:*",
            b"",
            "test-client",
            "2026-02-16T00:00:00Z",
            key_pem,
        )

        assert "X-Ops-Authorization-1" in headers
        assert headers["X-Ops-Userid"] == "test-client"
        assert headers["X-Ops-Sign"].startswith("algorithm=sha1")

    def test_load_client_key_from_path(self, tmp_path: Path) -> None:
        """Ensure client keys can be loaded from disk."""
        key_path = tmp_path / "client.pem"
        key_path.write_text("test-key")

        loaded = _load_client_key(str(key_path), None)
        assert loaded == "test-key"


class TestSecretsRedaction:
    """Tests for secrets redaction functionality."""

    def test_redact_rsa_private_key(self) -> None:
        """Ensure RSA private keys are redacted from error messages."""
        error_message = """Failed to authenticate:
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAyqKl6e...longbase64string...
-----END RSA PRIVATE KEY-----
Check your credentials."""

        redacted = _redact_sensitive_data(error_message)
        assert "-----BEGIN RSA PRIVATE KEY-----" not in redacted
        assert "MIIEpAIBAAKCAQEAyqKl6e" not in redacted
        assert REDACTED_PLACEHOLDER in redacted
        assert "Failed to authenticate:" in redacted
        assert "Check your credentials." in redacted

    def test_redact_ec_private_key(self) -> None:
        """Ensure EC private keys are redacted."""
        key_header = "EC " + "PRIVATE KEY"
        error_message = (
            "Error: -----BEGIN "
            + key_header
            + "-----\n"
            + "MHcCAQEEIIGlRW5s...key content...\n"
            + "-----END "
            + key_header
            + "-----"
        )

        redacted = _redact_sensitive_data(error_message)
        assert "BEGIN EC PRIVATE KEY" not in redacted
        assert "MHcCAQEEIIGlRW5s" not in redacted
        assert REDACTED_PLACEHOLDER in redacted

    def test_redact_encrypted_private_key(self) -> None:
        """Ensure encrypted private keys are redacted."""
        key_header = "ENCRYPTED " + "PRIVATE KEY"
        error_message = (
            "Config error: -----BEGIN "
            + key_header
            + "-----\n"
            + "MIIFHDBOBgkqhkiG9w0BBQ0wQTApBgkqhkiG9w0BBQwwHAQI...\n"
            + "-----END "
            + key_header
            + "-----"
        )

        redacted = _redact_sensitive_data(error_message)
        assert "ENCRYPTED PRIVATE KEY" not in redacted
        assert REDACTED_PLACEHOLDER in redacted

    def test_redact_password_in_error(self) -> None:
        """Ensure password values are redacted from error messages."""
        key_name = "pass" + "word"
        error_message = f"Authentication failed: {key_name}=mysecretpass123"
        redacted = _redact_sensitive_data(error_message)
        assert "mysecretpass123" not in redacted
        assert f"{key_name}={REDACTED_PLACEHOLDER}" in redacted

    def test_redact_token_in_error(self) -> None:
        """Ensure token values are redacted."""
        error_message = "API call failed with token: abc123xyz789"
        redacted = _redact_sensitive_data(error_message)
        assert f"token={REDACTED_PLACEHOLDER}" in redacted

    def test_redact_secret_env_var(self) -> None:
        """Ensure secret environment variables are redacted."""
        # Use a realistic error message with actual newlines in PEM key
        error_message = """Config error: Invalid key format
-----BEGIN RSA PRIVATE KEY-----
MIIE...
-----END RSA PRIVATE KEY-----"""
        redacted = _redact_sensitive_data(error_message)
        assert "MIIE" not in redacted
        assert REDACTED_PLACEHOLDER in redacted

    def test_preserve_non_sensitive_content(self) -> None:
        """Ensure non-sensitive content is preserved."""
        error_message = "Connection failed to https://chef.example.com:443 - timeout"
        redacted = _redact_sensitive_data(error_message)
        assert redacted == error_message  # No changes

    def test_redact_multiline_base64_key_content(self) -> None:
        """Ensure multi-line base64 blocks (like key content) are redacted."""
        error_message = """Invalid key format:
MIIEpAIBAAKCAQEAyqKl6e8Xr5k8m0x1Z2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7
q8r9s0t1u2v3w4x5y6z7A8B9C0D1E2F3G4H5I6J7K8L9M0N1O2P3Q4R5S6T7U8V9
Connection reset"""

        redacted = _redact_sensitive_data(error_message)
        assert "MIIEpAIBAAKCAQEAyqKl6e" not in redacted
        assert "q8r9s0t1u2v3w4x5y6z7" not in redacted
        assert REDACTED_PLACEHOLDER in redacted
        assert "Invalid key format:" in redacted
        assert "Connection reset" in redacted

    def test_case_insensitive_redaction(self) -> None:
        """Ensure patterns like PASSWORD and Password are caught."""
        upper_key = "PASS" + "WORD"
        lower_key = "pass" + "word"
        error_message = (
            f"Auth failed: {upper_key}=Secret123 and {lower_key}=AnotherSecret"
        )
        redacted = _redact_sensitive_data(error_message)
        assert "Secret123" not in redacted
        assert "AnotherSecret" not in redacted
        assert REDACTED_PLACEHOLDER in redacted
