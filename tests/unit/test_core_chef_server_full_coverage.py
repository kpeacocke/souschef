"""Tests to raise core Chef Server coverage."""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import souschef.core.chef_server as chef_server


def _generate_rsa_key_pem() -> str:
    """Generate a PEM encoded RSA private key for tests."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


# Test constants
TEST_PASSWORD = "supersecret"  # NOSONAR
TEST_SECRET_PASSWORD = "secret"  # NOSONAR


class TestRedaction:
    """Tests for sensitive data redaction."""

    def test_redacts_pem_key(self) -> None:
        """It redacts PEM-encoded keys."""
        text = "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----"
        assert chef_server.REDACTED_PLACEHOLDER in chef_server._redact_sensitive_data(
            text
        )

    def test_redacts_password_assignment(self) -> None:
        """It redacts password values in assignments."""
        text = f"password={TEST_PASSWORD}"
        redacted = chef_server._redact_sensitive_data(text)
        assert "password=***REDACTED***" in redacted  # NOSONAR

    def test_redacts_token_assignment(self) -> None:
        """It redacts token values in assignments."""
        text = "token:abc123"
        redacted = chef_server._redact_sensitive_data(text)
        assert "token=***REDACTED***" in redacted


class TestLoadClientKey:
    """Tests for client key loading."""

    def test_load_client_key_inline(self) -> None:
        """It returns inline key content."""
        assert chef_server._load_client_key(None, " key ") == "key"

    def test_load_client_key_requires_key(self) -> None:
        """It raises when no key is provided."""
        with pytest.raises(ValueError, match="Client key is required"):
            chef_server._load_client_key(None, None)

    def test_load_client_key_path_missing(self, tmp_path: Path) -> None:
        """It raises when key path does not exist."""
        missing = tmp_path / "missing.pem"
        with pytest.raises(ValueError, match="does not exist"):
            chef_server._load_client_key(str(missing), None)

    def test_load_client_key_path_directory(self, tmp_path: Path) -> None:
        """It raises when key path is a directory."""
        with pytest.raises(ValueError, match="must be a file"):
            chef_server._load_client_key(str(tmp_path), None)

    def test_load_client_key_from_file(self, tmp_path: Path) -> None:
        """It reads key content from a file."""
        key_path = tmp_path / "key.pem"
        key_path.write_text("key\n", encoding="utf-8")
        assert chef_server._load_client_key(str(key_path), None) == "key"


class TestServerUrlNormalisation:
    """Tests for server URL normalisation."""

    def test_requires_organisation(self) -> None:
        """It rejects missing organisation."""
        with pytest.raises(ValueError, match="Organisation is required"):
            chef_server._normalise_server_url("https://chef.example.com", "")

    def test_existing_org_mismatch(self) -> None:
        """It rejects mismatched organisation path."""
        with pytest.raises(ValueError, match="does not match"):
            chef_server._normalise_server_url(
                "https://chef.example.com/organizations/other",
                "default",
            )

    def test_existing_org_matches(self) -> None:
        """It keeps server URL when org matches."""
        url = chef_server._normalise_server_url(
            "https://chef.example.com/organizations/default",
            "default",
        )
        assert url.endswith("/organizations/default")

    def test_appends_org_path(self) -> None:
        """It appends organisation path when missing."""
        url = chef_server._normalise_server_url("https://chef.example.com", "default")
        assert url.endswith("/organizations/default")


class TestSigningHelpers:
    """Tests for signing and auth helper utilities."""

    def test_load_private_key_invalid(self) -> None:
        """It rejects invalid key content."""
        with pytest.raises(ValueError, match="Invalid client key format"):
            chef_server._load_private_key("not a key")

    def test_sign_request_success(self) -> None:
        """It signs a request with an RSA key."""
        key_pem = _generate_rsa_key_pem()
        signature = chef_server._sign_request("canonical", key_pem)
        decoded = base64.b64decode(signature.encode("utf-8"))
        assert decoded

    def test_split_signature_chunks(self) -> None:
        """It splits signature into numbered headers."""
        signature = "a" * (chef_server.AUTH_CHUNK_SIZE * 2 + 1)
        headers = chef_server._split_signature(signature)
        assert "X-Ops-Authorization-1" in headers
        assert "X-Ops-Authorization-3" in headers

    def test_build_auth_headers(self) -> None:
        """It includes auth headers and signature chunks."""
        with patch("souschef.core.chef_server._sign_request") as mock_sign:
            mock_sign.return_value = "abc"
            headers = chef_server._build_auth_headers(
                "GET", "/nodes", b"", "user", "timestamp", "key"
            )
        assert headers["X-Ops-Userid"] == "user"
        assert "X-Ops-Authorization-1" in headers


class TestResponseHandling:
    """Tests for response handling."""

    def test_handle_response_200(self) -> None:
        """It returns success for 200 responses."""
        response = MagicMock(status_code=200)
        success, message = chef_server._handle_chef_server_response(
            response, "https://chef"
        )
        assert success is True
        assert "Successfully" in message

    def test_handle_response_401(self) -> None:
        """It returns authentication errors."""
        response = MagicMock(status_code=401)
        success, message = chef_server._handle_chef_server_response(
            response, "https://chef"
        )
        assert success is False
        assert "Authentication failed" in message

    def test_handle_response_403(self) -> None:
        """It returns authorisation errors."""
        response = MagicMock(status_code=403)
        success, message = chef_server._handle_chef_server_response(
            response, "https://chef"
        )
        assert success is False
        assert "Authorisation" in message

    def test_handle_response_404(self) -> None:
        """It returns not found errors."""
        response = MagicMock(status_code=404)
        success, message = chef_server._handle_chef_server_response(
            response, "https://chef"
        )
        assert success is False
        assert "not found" in message

    def test_handle_response_other(self) -> None:
        """It returns generic errors for other status codes."""
        response = MagicMock(status_code=500)
        success, message = chef_server._handle_chef_server_response(
            response, "https://chef"
        )
        assert success is False
        assert "500" in message


class TestChefServerClient:
    """Tests for the ChefServerClient class."""

    def test_base_url_property(self) -> None:
        """It returns the normalised base URL."""
        config = chef_server.ChefServerConfig(
            server_url="https://chef.example.com",
            organisation="default",
            client_name="user",
            client_key=_generate_rsa_key_pem(),
        )
        client = chef_server.ChefServerClient(config)
        assert client.base_url.endswith("/organizations/default")

    def test_request_raises_when_requests_missing(self) -> None:
        """It fails when requests is unavailable."""
        config = chef_server.ChefServerConfig(
            server_url="https://chef.example.com",
            organisation="default",
            client_name="user",
            client_key=_generate_rsa_key_pem(),
        )
        client = chef_server.ChefServerClient(config)
        with (
            patch("souschef.core.chef_server.requests_module", None),
            pytest.raises(RuntimeError, match="requests library not installed"),
        ):
            client._request("GET", "/nodes")

    def test_search_nodes_filters_rows(self) -> None:
        """It filters non-dict rows from search results."""
        config = chef_server.ChefServerConfig(
            server_url="https://chef.example.com",
            organisation="default",
            client_name="user",
            client_key=_generate_rsa_key_pem(),
        )
        client = chef_server.ChefServerClient(config)
        response = MagicMock()
        response.json.return_value = {
            "rows": [
                {"name": "node1", "run_list": []},
                "invalid",
            ]
        }
        with patch.object(client, "_request", return_value=response):
            nodes = client.search_nodes("*")
        assert len(nodes) == 1
        assert nodes[0]["name"] == "node1"

    def test_list_roles(self) -> None:
        """It lists role summaries."""
        config = chef_server.ChefServerConfig(
            server_url="https://chef.example.com",
            organisation="default",
            client_name="user",
            client_key=_generate_rsa_key_pem(),
        )
        client = chef_server.ChefServerClient(config)
        response = MagicMock()
        response.json.return_value = {"web": {"url": "/roles/web"}, "bad": "x"}
        with patch.object(client, "_request", return_value=response):
            roles = client.list_roles()
        assert roles == [{"name": "web", "url": "/roles/web"}]

    def test_list_cookbooks(self) -> None:
        """It lists cookbook summaries."""
        config = chef_server.ChefServerConfig(
            server_url="https://chef.example.com",
            organisation="default",
            client_name="user",
            client_key=_generate_rsa_key_pem(),
        )
        client = chef_server.ChefServerClient(config)
        response = MagicMock()
        response.json.return_value = {"nginx": {"versions": []}, "bad": "x"}
        with patch.object(client, "_request", return_value=response):
            cookbooks = client.list_cookbooks()
        assert cookbooks == [{"name": "nginx", "versions": []}]

    def test_list_cookbook_versions(self) -> None:
        """It extracts version strings from cookbook versions."""
        config = chef_server.ChefServerConfig(
            server_url="https://chef.example.com",
            organisation="default",
            client_name="user",
            client_key=_generate_rsa_key_pem(),
        )
        client = chef_server.ChefServerClient(config)
        with patch.object(
            client,
            "list_cookbooks",
            return_value=[
                {
                    "name": "nginx",
                    "versions": [{"version": "1.0.0"}, {"version": 2}],
                }
            ],
        ):
            versions = client.list_cookbook_versions("nginx")
        assert versions == ["1.0.0"]

    def test_get_cookbook_version_non_dict(self) -> None:
        """It returns empty dict when response is not JSON object."""
        config = chef_server.ChefServerConfig(
            server_url="https://chef.example.com",
            organisation="default",
            client_name="user",
            client_key=_generate_rsa_key_pem(),
        )
        client = chef_server.ChefServerClient(config)
        response = MagicMock()
        response.json.return_value = "bad"
        with patch.object(client, "_request", return_value=response):
            result = client.get_cookbook_version("nginx", "1.0.0")
        assert result == {}

    def test_download_url_rejects_other_host(self) -> None:
        """It rejects download URLs from other hosts."""
        config = chef_server.ChefServerConfig(
            server_url="https://chef.example.com",
            organisation="default",
            client_name="user",
            client_key=_generate_rsa_key_pem(),
        )
        client = chef_server.ChefServerClient(config)
        with pytest.raises(ValueError, match="does not match"):
            client.download_url("https://evil.example.com/file")

    def test_download_url_with_params(self) -> None:
        """It downloads files with URL parameters."""
        config = chef_server.ChefServerConfig(
            server_url="https://chef.example.com",
            organisation="default",
            client_name="user",
            client_key=_generate_rsa_key_pem(),
        )
        client = chef_server.ChefServerClient(config)
        response = MagicMock()
        response.content = b"data"
        with patch.object(client, "_request", return_value=response) as mock_req:
            data = client.download_url(f"{client.base_url}/file?checksum=abc&other=1")
        assert data == b"data"
        mock_req.assert_called_once()


class TestClientBuilders:
    """Tests for client builder functions."""

    def test_build_client_config_requires_server_url(self) -> None:
        """It rejects missing server URL."""
        with pytest.raises(ValueError, match="Server URL is required"):
            chef_server._build_client_config("", "default", "user", None, "key")

    def test_build_client_config_requires_client_name(self) -> None:
        """It rejects missing client name."""
        with pytest.raises(ValueError, match="Client name is required"):
            chef_server._build_client_config("https://chef", "default", "", None, "key")

    def test_build_client_from_env_uses_env(self, monkeypatch) -> None:
        """It reads config from environment variables."""
        key_pem = _generate_rsa_key_pem()
        monkeypatch.setenv("CHEF_SERVER_URL", "https://chef.example.com")
        monkeypatch.setenv("CHEF_ORG", "default")
        monkeypatch.setenv("CHEF_CLIENT_NAME", "user")
        monkeypatch.setenv("CHEF_CLIENT_KEY", key_pem)

        client = chef_server._build_client_from_env()
        assert isinstance(client, chef_server.ChefServerClient)

    def test_validate_connection_requests_missing(self) -> None:
        """It reports missing requests library."""
        with patch("souschef.core.chef_server.requests_module", None):
            success, message = chef_server._validate_chef_server_connection(
                "https://chef", "user"
            )
        assert success is False
        assert "requests" in message

    def test_validate_connection_value_error_redacts(self) -> None:
        """It redacts sensitive values in errors."""
        with patch("souschef.core.chef_server._build_client_from_env") as mock_build:
            mock_build.side_effect = ValueError(f"password={TEST_SECRET_PASSWORD}")
            success, message = chef_server._validate_chef_server_connection(
                "https://chef", "user"
            )
        assert success is False
        assert chef_server.REDACTED_PLACEHOLDER in message
