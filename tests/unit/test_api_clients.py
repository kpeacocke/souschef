"""Tests for API clients."""

from unittest.mock import MagicMock, patch

import pytest

from souschef.api_clients import ChefServerClient

# Test fixtures for IP addresses used in mocked node data
# These are intentional test fixtures for unit tests, not production values
TEST_NODE_IP_1 = "10.0.0.1"  # NOSONAR - test fixture
TEST_NODE_IP_2 = "10.0.0.2"  # NOSONAR - test fixture


class TestChefServerClient:
    """Test ChefServerClient with RSA authentication."""

    @pytest.fixture
    def mock_core_client(self):
        """Mock the core ChefServerClient."""
        with patch("souschef.api_clients.CoreChefServerClient") as mock:
            yield mock

    @pytest.fixture
    def chef_client(self, mock_core_client):
        """Create a ChefServerClient instance."""
        mock_instance = MagicMock()
        mock_core_client.return_value = mock_instance

        client = ChefServerClient(
            server_url="https://chef.example.com",
            organization="test-org",
            client_name="test-client",
            client_key="-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
        )
        client._client = mock_instance
        return client

    def test_initialization(self, mock_core_client):
        """Test ChefServerClient initialization."""
        from souschef.core.chef_server import ChefServerConfig

        _ = ChefServerClient(
            server_url="https://chef.example.com/",
            organization="test-org",
            client_name="test-client",
            client_key="-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
            chef_version="15.10.91",
        )

        # Verify the core client was created with correct config
        mock_core_client.assert_called_once()
        call_args = mock_core_client.call_args
        config = call_args[0][0]

        assert isinstance(config, ChefServerConfig)
        assert config.server_url == "https://chef.example.com"
        assert config.organisation == "test-org"
        assert config.client_name == "test-client"
        assert "BEGIN RSA PRIVATE KEY" in config.client_key

    def test_search_nodes_success(self, chef_client):
        """Test successful node search."""
        # Mock the core client's search_nodes method
        chef_client._client.search_nodes.return_value = [
            {"name": "node1", "ip": TEST_NODE_IP_1},
            {"name": "node2", "ip": TEST_NODE_IP_2},
        ]

        result = chef_client.search_nodes("role:webserver")

        chef_client._client.search_nodes.assert_called_once_with("role:webserver")
        assert result["rows"] == [
            {"name": "node1", "ip": TEST_NODE_IP_1},
            {"name": "node2", "ip": TEST_NODE_IP_2},
        ]
        assert result["total"] == 2

    def test_search_nodes_default_query(self, chef_client):
        """Test node search with default wildcard query."""
        chef_client._client.search_nodes.return_value = []

        result = chef_client.search_nodes()

        chef_client._client.search_nodes.assert_called_once_with("*")
        assert result["rows"] == []
        assert result["total"] == 0

    def test_search_nodes_failure(self, chef_client):
        """Test node search failure handling."""
        chef_client._client.search_nodes.side_effect = ConnectionError(
            "Connection refused"
        )

        with pytest.raises(ConnectionError):
            chef_client.search_nodes("*")

    def test_get_node_success(self, chef_client):
        """Test successful node retrieval."""
        chef_client._client.search_nodes.return_value = [
            {
                "name": "web-server-01",
                "ipaddress": TEST_NODE_IP_1,
                "roles": ["webserver"],
            }
        ]

        result = chef_client.get_node("web-server-01")

        chef_client._client.search_nodes.assert_called_once_with("name:web-server-01")
        assert result["name"] == "web-server-01"
        assert result["ipaddress"] == TEST_NODE_IP_1

    def test_get_node_not_found(self, chef_client):
        """Test get_node when node doesn't exist."""
        chef_client._client.search_nodes.return_value = []

        with pytest.raises(ValueError, match="Node .* not found"):
            chef_client.get_node("nonexistent-node")

    def test_get_role_success(self, chef_client):
        """Test successful role retrieval."""
        chef_client._client.list_roles.return_value = [
            {"name": "webserver", "run_list": ["recipe[apache2]"]},
            {"name": "database", "run_list": ["recipe[postgresql]"]},
        ]

        result = chef_client.get_role("webserver")

        chef_client._client.list_roles.assert_called_once()
        assert result["name"] == "webserver"
        assert result["run_list"] == ["recipe[apache2]"]

    def test_get_role_not_found(self, chef_client):
        """Test get_role when role doesn't exist."""
        chef_client._client.list_roles.return_value = [
            {"name": "webserver", "run_list": ["recipe[apache2]"]},
        ]

        with pytest.raises(ValueError, match="Role .* not found"):
            chef_client.get_role("nonexistent-role")

    def test_get_cookbook_success(self, chef_client):
        """Test successful cookbook retrieval."""
        chef_client._client.list_cookbooks.return_value = [
            {"name": "apache2", "version": "8.0.0"},
            {"name": "nginx", "version": "1.0.0"},
        ]

        result = chef_client.get_cookbook("apache2")

        chef_client._client.list_cookbooks.assert_called_once()
        assert result["name"] == "apache2"
        assert result["version"] == "8.0.0"

    def test_get_cookbook_not_found(self, chef_client):
        """Test get_cookbook when cookbook doesn't exist."""
        chef_client._client.list_cookbooks.return_value = [
            {"name": "apache2", "version": "8.0.0"},
        ]

        with pytest.raises(ValueError, match="Cookbook .* not found"):
            chef_client.get_cookbook("nonexistent-cookbook")

    def test_chef_version_stored(self, mock_core_client):
        """Test that chef_version is stored (for API compatibility)."""
        mock_instance = MagicMock()
        mock_core_client.return_value = mock_instance

        client = ChefServerClient(
            server_url="https://chef.example.com",
            organization="test-org",
            client_name="test-client",
            client_key="-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
            chef_version="12.19.36",
        )

        assert client.chef_version == "12.19.36"

    def test_attributes_preserved(self, mock_core_client):
        """Test that ChefServerClient preserves all attributes."""
        mock_instance = MagicMock()
        mock_core_client.return_value = mock_instance

        client = ChefServerClient(
            server_url="https://chef.example.com/",
            organization="test-org",
            client_name="test-client",
            client_key="-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
        )

        assert client.server_url == "https://chef.example.com"
        assert client.organization == "test-org"
        assert client.client_name == "test-client"
        assert "BEGIN RSA PRIVATE KEY" in client.client_key


class TestChefServerClientIntegration:
    """Integration tests with actual RSA authentication."""

    def test_uses_authenticated_client(self, monkeypatch):
        """Test that ChefServerClient uses the authenticated core client."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        # Generate a valid test key
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_pem = pem.decode("utf-8")

        with patch("souschef.api_clients.CoreChefServerClient") as mock_core:
            mock_instance = MagicMock()
            mock_core.return_value = mock_instance
            mock_instance.search_nodes.return_value = []

            client = ChefServerClient(
                server_url="https://chef.example.com",
                organization="test-org",
                client_name="test-client",
                client_key=key_pem,
            )

            # Make a request
            client.search_nodes("*")

            # Verify the authenticated client was used
            mock_instance.search_nodes.assert_called_once_with("*")
