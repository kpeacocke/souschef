"""
Integration tests for Chef Server client with mock HTTP responses.

Tests the full Chef Server authentication and API interaction flow using
mocked HTTP responses instead of a real Chef Server instance.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import responses
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from souschef.core.chef_server import (
    ChefServerClient,
    ChefServerConfig,
    _validate_chef_server_connection,
    get_chef_nodes,
    list_chef_roles,
)


@pytest.fixture
def test_key() -> str:
    """Generate a test RSA private key."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return key_pem.decode("utf-8")


@pytest.fixture
def test_config(test_key: str) -> ChefServerConfig:
    """Create a test Chef Server configuration."""
    return ChefServerConfig(
        server_url="https://chef.example.com",
        organisation="testorg",
        client_name="testclient",
        client_key=test_key,
        timeout=10,
    )


@pytest.fixture
def test_key_file(tmp_path: Path, test_key: str) -> Path:
    """Create a temporary key file."""
    key_path = tmp_path / "test-client.pem"
    key_path.write_text(test_key)
    return key_path


class TestChefServerMockIntegration:
    """Integration tests with mocked Chef Server responses."""

    @responses.activate
    def test_connection_success(self, test_config: ChefServerConfig) -> None:
        """Test successful Chef Server connection."""
        # Mock search endpoint response
        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/search/node",
            json={"rows": [], "total": 0, "start": 0},
            status=200,
        )

        client = ChefServerClient(test_config)
        success, message = client.test_connection()

        assert success is True
        assert "Successfully connected" in message
        assert len(responses.calls) == 1
        # Verify authentication headers were sent
        assert "X-Ops-Userid" in responses.calls[0].request.headers
        assert "X-Ops-Sign" in responses.calls[0].request.headers
        assert "X-Ops-Authorization-1" in responses.calls[0].request.headers

    @responses.activate
    def test_connection_auth_failure(self, test_config: ChefServerConfig) -> None:
        """Test Chef Server connection with authentication failure."""
        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/search/node",
            json={"error": "Authentication failed"},
            status=401,
        )

        client = ChefServerClient(test_config)
        success, message = client.test_connection()

        assert success is False
        assert "Authentication failed" in message

    @responses.activate
    def test_connection_timeout(self, test_config: ChefServerConfig) -> None:
        """Test Chef Server connection timeout handling."""
        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/search/node",
            body=Exception("Connection timeout"),
        )

        success, message = _validate_chef_server_connection(
            server_url=test_config.server_url,
            client_name=test_config.client_name,
            organisation=test_config.organisation,
            client_key=test_config.client_key,
        )

        assert success is False
        assert "error" in message.lower() or "connection" in message.lower()

    @responses.activate
    def test_search_nodes(self, test_config: ChefServerConfig) -> None:
        """Test node search with mock response."""
        mock_nodes = {
            "rows": [
                {
                    "name": "web-01",
                    "run_list": ["role[webserver]"],
                    "chef_environment": "production",
                    "platform": "ubuntu",
                    "ipaddress": "10.0.1.10",  # NOSONAR - test fixture
                    "fqdn": "web-01.example.com",
                    "automatic": {"platform": "ubuntu", "platform_version": "22.04"},
                },
                {
                    "name": "db-01",
                    "run_list": ["role[database]"],
                    "chef_environment": "production",
                    "platform": "centos",
                    "ipaddress": "10.0.1.20",  # NOSONAR - test fixture
                    "fqdn": "db-01.example.com",
                    "automatic": {"platform": "centos", "platform_version": "8"},
                },
            ],
            "total": 2,
            "start": 0,
        }

        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/search/node",
            json=mock_nodes,
            status=200,
        )

        client = ChefServerClient(test_config)
        nodes = client.search_nodes("role:webserver")

        assert len(nodes) == 2
        assert nodes[0]["name"] == "web-01"
        assert nodes[0]["platform"] == "ubuntu"
        assert nodes[1]["name"] == "db-01"
        assert nodes[1]["platform"] == "centos"

    @responses.activate
    def test_list_roles(self, test_config: ChefServerConfig) -> None:
        """Test listing Chef roles."""
        mock_roles = {
            "webserver": {"url": "https://chef.example.com/roles/webserver"},
            "database": {"url": "https://chef.example.com/roles/database"},
            "monitoring": {"url": "https://chef.example.com/roles/monitoring"},
        }

        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/roles",
            json=mock_roles,
            status=200,
        )

        client = ChefServerClient(test_config)
        roles = client.list_roles()

        assert len(roles) == 3
        assert {"name": "webserver", "url": mock_roles["webserver"]["url"]} in roles
        assert {"name": "database", "url": mock_roles["database"]["url"]} in roles

    @responses.activate
    def test_list_environments(self, test_config: ChefServerConfig) -> None:
        """Test listing Chef environments."""
        mock_environments = {
            "production": {"url": "https://chef.example.com/environments/production"},
            "staging": {"url": "https://chef.example.com/environments/staging"},
            "_default": {"url": "https://chef.example.com/environments/_default"},
        }

        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/environments",
            json=mock_environments,
            status=200,
        )

        client = ChefServerClient(test_config)
        environments = client.list_environments()

        assert len(environments) == 3
        env_names = [env["name"] for env in environments]
        assert "production" in env_names
        assert "staging" in env_names
        assert "_default" in env_names

    @responses.activate
    def test_list_cookbooks(self, test_config: ChefServerConfig) -> None:
        """Test listing Chef cookbooks with versions."""
        mock_cookbooks = {
            "apache2": {
                "url": "https://chef.example.com/cookbooks/apache2",
                "versions": [
                    {"url": "https://chef.example.com/cookbooks/apache2/8.6.0"}
                ],
            },
            "mysql": {
                "url": "https://chef.example.com/cookbooks/mysql",
                "versions": [
                    {"url": "https://chef.example.com/cookbooks/mysql/10.5.0"}
                ],
            },
        }

        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/cookbooks",
            json=mock_cookbooks,
            status=200,
        )

        client = ChefServerClient(test_config)
        cookbooks = client.list_cookbooks()

        assert len(cookbooks) == 2
        cookbook_names = [cb["name"] for cb in cookbooks]
        assert "apache2" in cookbook_names
        assert "mysql" in cookbook_names

    @responses.activate
    def test_list_policies(self, test_config: ChefServerConfig) -> None:
        """Test listing Chef policies (policyfiles)."""
        mock_policies = {
            "web-policy": {
                "uri": "https://chef.example.com/policies/web-policy",
                "revisions": {
                    "1234abcd": {
                        "url": "https://chef.example.com/policies/web-policy/revisions/1234abcd"
                    }
                },
            },
            "database-policy": {
                "uri": "https://chef.example.com/policies/database-policy",
                "revisions": {
                    "5678efgh": {
                        "url": "https://chef.example.com/policies/database-policy/revisions/5678efgh"
                    }
                },
            },
        }

        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/policies",
            json=mock_policies,
            status=200,
        )

        client = ChefServerClient(test_config)
        policies = client.list_policies()

        assert len(policies) == 2
        policy_names = [p["name"] for p in policies]
        assert "web-policy" in policy_names
        assert "database-policy" in policy_names

    @responses.activate
    def test_get_cookbook_version(self, test_config: ChefServerConfig) -> None:
        """Test retrieving specific cookbook version details."""
        mock_cookbook_version = {
            "cookbook_name": "apache2",
            "version": "8.6.0",
            "recipes": [
                {"name": "default.rb", "path": "recipes/default.rb"},
                {"name": "mod_ssl.rb", "path": "recipes/mod_ssl.rb"},
            ],
            "attributes": [{"name": "default.rb", "path": "attributes/default.rb"}],
        }

        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/cookbooks/apache2/8.6.0",
            json=mock_cookbook_version,
            status=200,
        )

        client = ChefServerClient(test_config)
        cookbook = client.get_cookbook_version("apache2", "8.6.0")

        assert cookbook is not None
        assert cookbook["cookbook_name"] == "apache2"
        assert cookbook["version"] == "8.6.0"
        assert len(cookbook["recipes"]) == 2

    @responses.activate
    def test_helper_functions(
        self, test_config: ChefServerConfig, test_key_file: Path
    ) -> None:
        """Test public helper functions with mock server."""
        # Mock responses for various endpoints
        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/search/node",
            json={"rows": [{"name": "test-node", "platform": "ubuntu"}], "total": 1},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/roles",
            json={"webserver": {"url": "https://chef.example.com/roles/webserver"}},
            status=200,
        )

        # Test get_chef_nodes
        nodes = get_chef_nodes(
            "*:*",
            server_url=test_config.server_url,
            organisation=test_config.organisation,
            client_name=test_config.client_name,
            client_key=test_config.client_key,
        )
        assert len(nodes) == 1
        assert nodes[0]["name"] == "test-node"

        # Test list_chef_roles
        roles = list_chef_roles(
            server_url=test_config.server_url,
            organisation=test_config.organisation,
            client_name=test_config.client_name,
            client_key=test_config.client_key,
        )
        assert len(roles) == 1
        assert roles[0]["name"] == "webserver"


class TestChefServerMockErrorHandling:
    """Test error handling with mock responses."""

    @responses.activate
    def test_404_not_found(self, test_config: ChefServerConfig) -> None:
        """Test handling of 404 Not Found responses."""
        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/search/node",
            json={"error": "Not Found"},
            status=404,
        )

        client = ChefServerClient(test_config)
        success, message = client.test_connection()

        assert success is False
        assert "not found" in message.lower()

    @responses.activate
    def test_403_forbidden(self, test_config: ChefServerConfig) -> None:
        """Test handling of 403 Forbidden responses."""
        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/search/node",
            json={"error": "Forbidden"},
            status=403,
        )

        client = ChefServerClient(test_config)
        success, message = client.test_connection()

        assert success is False
        assert "authorisation" in message.lower() or "access denied" in message.lower()

    @responses.activate
    def test_500_server_error(self, test_config: ChefServerConfig) -> None:
        """Test handling of 500 Internal Server Error responses."""
        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/search/node",
            json={"error": "Internal Server Error"},
            status=500,
        )

        client = ChefServerClient(test_config)
        success, message = client.test_connection()

        assert success is False
        assert "500" in message or "failed" in message.lower()

    @responses.activate
    def test_malformed_json_response(self, test_config: ChefServerConfig) -> None:
        """Test handling of malformed JSON responses."""
        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/roles",
            body="Not valid JSON",
            status=200,
            content_type="text/plain",
        )

        client = ChefServerClient(test_config)
        with pytest.raises(json.JSONDecodeError):
            client.list_roles()

    @responses.activate
    def test_empty_response_handling(self, test_config: ChefServerConfig) -> None:
        """Test handling of empty or missing data in responses."""
        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/search/node",
            json={"rows": [], "total": 0},
            status=200,
        )

        client = ChefServerClient(test_config)
        nodes = client.search_nodes("*:*")

        assert nodes == []
        assert isinstance(nodes, list)


class TestChefServerMockAuthHeaders:
    """Test authentication header generation with mock server."""

    @responses.activate
    def test_auth_headers_present(self, test_config: ChefServerConfig) -> None:
        """Verify all required auth headers are sent."""
        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/search/node",
            json={"rows": [], "total": 0},
            status=200,
        )

        client = ChefServerClient(test_config)
        client.test_connection()

        # Check that authentication headers were sent
        request_headers = responses.calls[0].request.headers

        assert "X-Ops-Userid" in request_headers
        assert request_headers["X-Ops-Userid"] == "testclient"

        assert "X-Ops-Sign" in request_headers
        assert "algorithm=sha1" in request_headers["X-Ops-Sign"]
        assert "version=1.0" in request_headers["X-Ops-Sign"]

        assert "X-Ops-Timestamp" in request_headers
        assert "X-Ops-Content-Hash" in request_headers

        # Check for signature chunks
        assert "X-Ops-Authorization-1" in request_headers
        # Signature should be split into chunks
        chunk_num = 1
        while f"X-Ops-Authorization-{chunk_num}" in request_headers:
            chunk = request_headers[f"X-Ops-Authorization-{chunk_num}"]
            assert len(chunk) <= 60  # Each chunk should be ≤60 chars
            chunk_num += 1

        assert chunk_num > 1  # Should have at least 1 signature chunk

    @responses.activate
    def test_query_params_in_signature(self, test_config: ChefServerConfig) -> None:
        """Verify query parameters are included in signature."""
        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/search/node",
            json={"rows": [], "total": 0},
            status=200,
            match=[responses.matchers.query_param_matcher({"q": "role:webserver"})],
        )

        client = ChefServerClient(test_config)
        client.search_nodes("role:webserver")

        # Verify request was made with correct query params
        assert len(responses.calls) == 1
        assert "q=role%3Awebserver" in responses.calls[0].request.url


class TestChefServerMockSecretsRedaction:
    """Test that secrets are redacted in error messages."""

    @responses.activate
    def test_error_redacts_keys(self, test_key: str) -> None:
        """Ensure error messages don't leak key material."""
        responses.add(
            responses.GET,
            "https://chef.example.com/organizations/testorg/search/node",
            json={"error": "Invalid signature"},
            status=401,
        )

        success, message = _validate_chef_server_connection(
            server_url="https://chef.example.com",
            client_name="testclient",
            organisation="testorg",
            client_key=test_key,
        )

        assert success is False
        # Ensure the actual key is not in the error message
        assert "-----BEGIN" not in message
        assert "-----END" not in message
        assert test_key not in message
        # But the error should still be informative
        assert "Authentication failed" in message or "credentials" in message.lower()
