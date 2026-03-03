"""Comprehensive tests for api_clients module to achieve 100% coverage."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import requests
from requests.auth import HTTPBasicAuth

from souschef.api_clients import (
    AAPClient,
    AnsiblePlatformClient,
    AWXClient,
    ChefServerClient,
    TowerClient,
    get_ansible_client,
)

# Test credentials - not for production use
TEST_SECRET = "test-credential"


class TestChefServerClient:
    """Tests for ChefServerClient wrapper."""

    @patch("souschef.api_clients.CoreChefServerClient")
    def test_init(self, mock_core_client):
        """Test ChefServerClient initialisation."""
        client = ChefServerClient(
            server_url="https://chef.example.com/",
            organization="test_org",
            client_name="admin",
            client_key="-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
        )

        assert client.server_url == "https://chef.example.com"
        assert client.organization == "test_org"
        assert client.client_name == "admin"

    @patch("souschef.api_clients.CoreChefServerClient")
    def test_search_nodes_success(self, mock_core_client):
        """Test successful node search."""
        mock_instance = MagicMock()
        mock_core_client.return_value = mock_instance
        mock_instance.search_nodes.return_value = [
            {"name": "node1", "platform": "ubuntu"},
            {"name": "node2", "platform": "centos"},
        ]

        client = ChefServerClient(
            server_url="https://chef.example.com",
            organization="test_org",
            client_name="admin",
            client_key="key",
        )
        result = client.search_nodes("platform:ubuntu")

        assert result["total"] == 2
        assert len(result["rows"]) == 2
        mock_instance.search_nodes.assert_called_once_with("platform:ubuntu")

    @patch("souschef.api_clients.CoreChefServerClient")
    def test_search_nodes_empty(self, mock_core_client):
        """Test node search with no results."""
        mock_instance = MagicMock()
        mock_core_client.return_value = mock_instance
        mock_instance.search_nodes.return_value = []

        client = ChefServerClient(
            server_url="https://chef.example.com",
            organization="test_org",
            client_name="admin",
            client_key="key",
        )
        result = client.search_nodes("name:nonexistent")

        assert result["total"] == 0
        assert result["rows"] == []

    @patch("souschef.api_clients.CoreChefServerClient")
    def test_search_nodes_error(self, mock_core_client):
        """Test node search error handling."""
        mock_instance = MagicMock()
        mock_core_client.return_value = mock_instance
        mock_instance.search_nodes.side_effect = ValueError("Connection failed")

        client = ChefServerClient(
            server_url="https://chef.example.com",
            organization="test_org",
            client_name="admin",
            client_key="key",
        )

        with pytest.raises(ValueError):
            client.search_nodes("*")

    @patch("souschef.api_clients.CoreChefServerClient")
    def test_get_node_success(self, mock_core_client):
        """Test successful node retrieval."""
        mock_instance = MagicMock()
        mock_core_client.return_value = mock_instance
        mock_instance.search_nodes.return_value = [
            {"name": "node1", "platform": "ubuntu", "recipes": ["recipe1"]}
        ]

        client = ChefServerClient(
            server_url="https://chef.example.com",
            organization="test_org",
            client_name="admin",
            client_key="key",
        )
        result = client.get_node("node1")

        assert result["name"] == "node1"
        assert result["platform"] == "ubuntu"

    @patch("souschef.api_clients.CoreChefServerClient")
    def test_get_node_not_found(self, mock_core_client):
        """Test node not found error."""
        mock_instance = MagicMock()
        mock_core_client.return_value = mock_instance
        mock_instance.search_nodes.return_value = []

        client = ChefServerClient(
            server_url="https://chef.example.com",
            organization="test_org",
            client_name="admin",
            client_key="key",
        )

        with pytest.raises(ValueError, match="not found"):
            client.get_node("nonexistent")

    @patch("souschef.api_clients.CoreChefServerClient")
    def test_get_role_success(self, mock_core_client):
        """Test successful role retrieval."""
        mock_instance = MagicMock()
        mock_core_client.return_value = mock_instance
        mock_instance.list_roles.return_value = [
            {"name": "web", "recipes": ["nginx"]},
            {"name": "db", "recipes": ["postgres"]},
        ]

        client = ChefServerClient(
            server_url="https://chef.example.com",
            organization="test_org",
            client_name="admin",
            client_key="key",
        )
        result = client.get_role("web")

        assert result["name"] == "web"
        assert result["recipes"] == ["nginx"]

    @patch("souschef.api_clients.CoreChefServerClient")
    def test_get_role_not_found(self, mock_core_client):
        """Test role not found error."""
        mock_instance = MagicMock()
        mock_core_client.return_value = mock_instance
        mock_instance.list_roles.return_value = [{"name": "web", "recipes": ["nginx"]}]

        client = ChefServerClient(
            server_url="https://chef.example.com",
            organization="test_org",
            client_name="admin",
            client_key="key",
        )

        with pytest.raises(ValueError, match="not found"):
            client.get_role("nonexistent")

    @patch("souschef.api_clients.CoreChefServerClient")
    def test_get_cookbook_success(self, mock_core_client):
        """Test successful cookbook retrieval."""
        mock_instance = MagicMock()
        mock_core_client.return_value = mock_instance
        mock_instance.list_cookbooks.return_value = [
            {"name": "nginx", "versions": ["1.0.0", "2.0.0"]},
            {"name": "postgres", "versions": ["1.0.0"]},
        ]

        client = ChefServerClient(
            server_url="https://chef.example.com",
            organization="test_org",
            client_name="admin",
            client_key="key",
        )
        result = client.get_cookbook("nginx")

        assert result["name"] == "nginx"
        assert "1.0.0" in result["versions"]

    @patch("souschef.api_clients.CoreChefServerClient")
    def test_get_cookbook_not_found(self, mock_core_client):
        """Test cookbook not found error."""
        mock_instance = MagicMock()
        mock_core_client.return_value = mock_instance
        mock_instance.list_cookbooks.return_value = [
            {"name": "nginx", "versions": ["1.0.0"]}
        ]

        client = ChefServerClient(
            server_url="https://chef.example.com",
            organization="test_org",
            client_name="admin",
            client_key="key",
        )

        with pytest.raises(ValueError, match="not found"):
            client.get_cookbook("nonexistent")


class TestAnsiblePlatformClient:
    """Tests for AnsiblePlatformClient base class."""

    def test_init(self):
        """Test client initialisation."""
        client = TowerClient(
            server_url="https://tower.example.com/",
            username="admin",
            password=TEST_SECRET,
            verify_ssl=False,
        )

        assert client.server_url == "https://tower.example.com"
        assert client.username == "admin"
        assert client.password == TEST_SECRET
        assert client.verify_ssl is False
        assert isinstance(client.session.auth, HTTPBasicAuth)

    def test_abstract_get_api_version_pass(self):
        """Test abstract base method pass-through."""

        class DummyClient(AnsiblePlatformClient):
            def get_api_version(self) -> str:
                return super().get_api_version()

        client = DummyClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        assert client.get_api_version() is None

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_inventory_success(self, mock_post):
        """Test successful inventory creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "name": "test_inv"}
        mock_post.return_value = mock_response

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.create_inventory("test_inv")

        assert result["id"] == 1
        assert result["name"] == "test_inv"
        mock_post.assert_called_once()

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_inventory_error(self, mock_post):
        """Test inventory creation error."""
        mock_post.side_effect = requests.RequestException("Connection failed")

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )

        with pytest.raises(requests.RequestException):
            client.create_inventory("test_inv")

    @patch("souschef.api_clients.requests.Session.post")
    def test_add_host_success(self, mock_post):
        """Test successful host addition."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "name": "host1"}
        mock_post.return_value = mock_response

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.add_host(1, "host1", description="Test host")

        assert result["id"] == 1
        assert result["name"] == "host1"
        mock_post.assert_called_once()

    @patch("souschef.api_clients.requests.Session.post")
    def test_add_host_error(self, mock_post):
        """Test host addition error."""
        mock_post.side_effect = requests.RequestException("Failed to add host")

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )

        with pytest.raises(requests.RequestException):
            client.add_host(1, "host1")

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_group_success(self, mock_post):
        """Test successful group creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "name": "web"}
        mock_post.return_value = mock_response

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.create_group(1, "web")

        assert result["id"] == 1
        assert result["name"] == "web"

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_group_error(self, mock_post):
        """Test group creation error."""
        mock_post.side_effect = requests.RequestException("Failed to create group")

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )

        with pytest.raises(requests.RequestException):
            client.create_group(1, "web")

    @patch("souschef.api_clients.requests.Session.post")
    def test_add_host_to_group_success(self, mock_post):
        """Test adding host to group."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.add_host_to_group(1, 1, 1)

        assert result is True

    @patch("souschef.api_clients.requests.Session.post")
    def test_add_host_to_group_error(self, mock_post):
        """Test add host to group error."""
        mock_post.side_effect = requests.RequestException("Failed")

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )

        with pytest.raises(requests.RequestException):
            client.add_host_to_group(1, 1, 1)

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_project_success(self, mock_post):
        """Test successful project creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "name": "test_proj"}
        mock_post.return_value = mock_response

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.create_project(
            "test_proj", scm_type="git", scm_url="https://github.com/test/repo"
        )

        assert result["id"] == 1

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_project_error(self, mock_post):
        """Test project creation error."""
        mock_post.side_effect = requests.RequestException("Failed")

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )

        with pytest.raises(requests.RequestException):
            client.create_project("test_proj")

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_job_template_success(self, mock_post):
        """Test successful job template creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "name": "test_jt"}
        mock_post.return_value = mock_response

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.create_job_template("test_jt")

        assert result["id"] == 1

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_job_template_error(self, mock_post):
        """Test job template creation error."""
        mock_post.side_effect = requests.RequestException("Failed")

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )

        with pytest.raises(requests.RequestException):
            client.create_job_template("test_jt")

    @patch("souschef.api_clients.requests.Session.delete")
    def test_delete_inventory_success(self, mock_delete):
        """Test successful inventory deletion."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.delete_inventory(1)

        assert result is True

    @patch("souschef.api_clients.requests.Session.delete")
    def test_delete_inventory_error(self, mock_delete):
        """Test inventory deletion error."""
        mock_delete.side_effect = requests.RequestException("Failed")

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.delete_inventory(1)

        assert result is False

    @patch("souschef.api_clients.requests.Session.delete")
    def test_delete_project_success(self, mock_delete):
        """Test successful project deletion."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.delete_project(1)

        assert result is True

    @patch("souschef.api_clients.requests.Session.delete")
    def test_delete_project_error(self, mock_delete):
        """Test project deletion error."""
        mock_delete.side_effect = requests.RequestException("Failed")

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.delete_project(1)

        assert result is False

    @patch("souschef.api_clients.requests.Session.delete")
    def test_delete_job_template_success(self, mock_delete):
        """Test successful job template deletion."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.delete_job_template(1)

        assert result is True

    @patch("souschef.api_clients.requests.Session.delete")
    def test_delete_job_template_error(self, mock_delete):
        """Test job template deletion error."""
        mock_delete.side_effect = requests.RequestException("Failed")

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.delete_job_template(1)

        assert result is False


class TestTowerClient:
    """Tests for Ansible Tower client."""

    @patch("souschef.api_clients.requests.Session.get")
    def test_get_api_version_success(self, mock_get):
        """Test successful version retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"version": "3.8.5"}
        mock_get.return_value = mock_response

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.get_api_version()

        assert result == "3.8.5"

    @patch("souschef.api_clients.requests.Session.get")
    def test_get_api_version_error(self, mock_get):
        """Test version retrieval error returns default."""
        mock_get.side_effect = requests.RequestException("Failed")

        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.get_api_version()

        assert result == "3.8.5"


class TestAWXClient:
    """Tests for AWX client."""

    def test_init_with_version(self):
        """Test AWX client initialisation with version."""
        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password=TEST_SECRET,
            version="23.5.0",
        )

        assert client.version == "23.5.0"

    @patch("souschef.api_clients.requests.Session.get")
    def test_get_api_version_success(self, mock_get):
        """Test successful AWX version retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"version": "24.6.1"}
        mock_get.return_value = mock_response

        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password=TEST_SECRET,
            version="24.6.1",
        )
        result = client.get_api_version()

        assert result == "24.6.1"

    @patch("souschef.api_clients.requests.Session.get")
    def test_get_api_version_error(self, mock_get):
        """Test AWX version retrieval error returns default."""
        mock_get.side_effect = requests.RequestException("Failed")

        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password=TEST_SECRET,
            version="24.6.1",
        )
        result = client.get_api_version()

        assert result == "24.6.1"

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_execution_environment_awx_21(self, mock_post):
        """Test EE creation on AWX 21+."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "name": "custom_ee"}
        mock_post.return_value = mock_response

        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password=TEST_SECRET,
            version="23.5.0",
        )
        result = client.create_execution_environment("custom_ee")

        assert result["id"] == 1

    def test_create_execution_environment_awx_20_error(self):
        """Test EE creation fails on AWX 20."""
        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password=TEST_SECRET,
            version="20.0.0",
        )

        with pytest.raises(NotImplementedError):
            client.create_execution_environment("custom_ee")

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_execution_environment_error(self, mock_post):
        """Test EE creation error."""
        mock_post.side_effect = requests.RequestException("Failed")

        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password=TEST_SECRET,
        )

        with pytest.raises(requests.RequestException):
            client.create_execution_environment("custom_ee")


class TestAAPClient:
    """Tests for Ansible Automation Platform client."""

    @patch("souschef.api_clients.requests.Session.get")
    def test_get_api_version_success(self, mock_get):
        """Test successful AAP version retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"version": "2.4.0"}
        mock_get.return_value = mock_response

        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.get_api_version()

        assert result == "2.4.0"

    @patch("souschef.api_clients.requests.Session.get")
    def test_get_api_version_error(self, mock_get):
        """Test AAP version retrieval error returns default."""
        mock_get.side_effect = requests.RequestException("Failed")

        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.get_api_version()

        assert result == "2.4.0"

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_execution_environment_success(self, mock_post):
        """Test successful EE creation on AAP."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "name": "custom_ee"}
        mock_post.return_value = mock_response

        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.create_execution_environment("custom_ee")

        assert result["id"] == 1

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_execution_environment_error(self, mock_post):
        """Test EE creation error on AAP."""
        mock_post.side_effect = requests.RequestException("Failed")

        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password=TEST_SECRET,
        )

        with pytest.raises(requests.RequestException):
            client.create_execution_environment("custom_ee")

    @patch("souschef.api_clients.requests.Session.patch")
    def test_enable_content_signing_success(self, mock_patch):
        """Test enabling content signing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response

        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.enable_content_signing(1, 1)

        assert result is True

    @patch("souschef.api_clients.requests.Session.patch")
    def test_enable_content_signing_error(self, mock_patch):
        """Test content signing error."""
        mock_patch.side_effect = requests.RequestException("Failed")

        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password=TEST_SECRET,
        )
        result = client.enable_content_signing(1, 1)

        assert result is False


class TestGetAnsibleClient:
    """Tests for get_ansible_client factory function."""

    def test_get_tower_client(self):
        """Test getting Tower client."""
        client = get_ansible_client(
            server_url="https://tower.example.com",
            platform="tower",
            platform_version="3.8.5",
            username="admin",
            password=TEST_SECRET,
        )

        assert isinstance(client, TowerClient)

    def test_get_awx_client(self):
        """Test getting AWX client."""
        client = get_ansible_client(
            server_url="https://awx.example.com",
            platform="awx",
            platform_version="24.6.1",
            username="admin",
            password=TEST_SECRET,
        )

        assert isinstance(client, AWXClient)
        assert client.version == "24.6.1"

    def test_get_aap_client(self):
        """Test getting AAP client."""
        client = get_ansible_client(
            server_url="https://aap.example.com",
            platform="aap",
            platform_version="2.4.0",
            username="admin",
            password=TEST_SECRET,
        )

        assert isinstance(client, AAPClient)

    def test_get_unknown_platform(self):
        """Test error for unknown platform."""
        with pytest.raises(ValueError, match="Unknown platform"):
            get_ansible_client(
                server_url="https://platform.example.com",
                platform="unknown",
                platform_version="1.0.0",
                username="admin",
                password=TEST_SECRET,
            )


class TestLoggingCoverage:
    """Tests to ensure debug logging statements are covered."""

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_inventory_debug_logging(self, mock_post, caplog):
        """Test debug logging in inventory creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 42, "name": "test_inv"}
        mock_post.return_value = mock_response

        with caplog.at_level(logging.DEBUG):
            client = TowerClient(
                server_url="https://tower.example.com",
                username="admin",
                password=TEST_SECRET,
            )
            result = client.create_inventory("test_inv")

        assert result["id"] == 42

    @patch("souschef.api_clients.requests.Session.post")
    def test_add_host_debug_logging(self, mock_post, caplog):
        """Test debug logging in host addition."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "name": "host1"}
        mock_post.return_value = mock_response

        with caplog.at_level(logging.DEBUG):
            client = TowerClient(
                server_url="https://tower.example.com",
                username="admin",
                password=TEST_SECRET,
            )
            result = client.add_host(1, "host1")

        assert result["id"] == 1

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_group_debug_logging(self, mock_post, caplog):
        """Test debug logging in group creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 5, "name": "web"}
        mock_post.return_value = mock_response

        with caplog.at_level(logging.DEBUG):
            client = TowerClient(
                server_url="https://tower.example.com",
                username="admin",
                password=TEST_SECRET,
            )
            result = client.create_group(1, "web")

        assert result["id"] == 5

    @patch("souschef.api_clients.requests.Session.post")
    def test_add_host_to_group_debug_logging(self, mock_post, caplog):
        """Test debug logging in add host to group."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        with caplog.at_level(logging.DEBUG):
            client = TowerClient(
                server_url="https://tower.example.com",
                username="admin",
                password=TEST_SECRET,
            )
            result = client.add_host_to_group(1, 1, 1)

        assert result is True

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_project_debug_logging(self, mock_post, caplog):
        """Test debug logging in project creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 10, "name": "test_proj"}
        mock_post.return_value = mock_response

        with caplog.at_level(logging.DEBUG):
            client = TowerClient(
                server_url="https://tower.example.com",
                username="admin",
                password=TEST_SECRET,
            )
            result = client.create_project("test_proj")

        assert result["id"] == 10

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_job_template_debug_logging(self, mock_post, caplog):
        """Test debug logging in job template creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 15, "name": "test_jt"}
        mock_post.return_value = mock_response

        with caplog.at_level(logging.DEBUG):
            client = TowerClient(
                server_url="https://tower.example.com",
                username="admin",
                password=TEST_SECRET,
            )
            result = client.create_job_template("test_jt")

        assert result["id"] == 15

    @patch("souschef.api_clients.requests.Session.delete")
    def test_delete_inventory_debug_logging(self, mock_delete, caplog):
        """Test debug logging in inventory deletion."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        with caplog.at_level(logging.DEBUG):
            client = TowerClient(
                server_url="https://tower.example.com",
                username="admin",
                password=TEST_SECRET,
            )
            result = client.delete_inventory(1)

        assert result is True

    @patch("souschef.api_clients.requests.Session.delete")
    def test_delete_project_debug_logging(self, mock_delete, caplog):
        """Test debug logging in project deletion."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        with caplog.at_level(logging.DEBUG):
            client = TowerClient(
                server_url="https://tower.example.com",
                username="admin",
                password=TEST_SECRET,
            )
            result = client.delete_project(1)

        assert result is True

    @patch("souschef.api_clients.requests.Session.delete")
    def test_delete_job_template_debug_logging(self, mock_delete, caplog):
        """Test debug logging in job template deletion."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        with caplog.at_level(logging.DEBUG):
            client = TowerClient(
                server_url="https://tower.example.com",
                username="admin",
                password=TEST_SECRET,
            )
            result = client.delete_job_template(1)

        assert result is True

    @patch("souschef.api_clients.requests.Session.post")
    def test_create_execution_environment_debug_logging(self, mock_post, caplog):
        """Test debug logging in EE creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 20, "name": "custom_ee"}
        mock_post.return_value = mock_response

        with caplog.at_level(logging.DEBUG):
            client = AAPClient(
                server_url="https://aap.example.com",
                username="admin",
                password=TEST_SECRET,
            )
            result = client.create_execution_environment("custom_ee")

        assert result["id"] == 20
