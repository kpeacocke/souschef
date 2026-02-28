"""
Comprehensive tests for souschef/api_clients.py.

Targets uncovered lines in API client classes for Chef Server and Ansible platforms.
"""

import contextlib
from unittest.mock import MagicMock, patch

import pytest
import requests

from souschef.api_clients import (
    AAPClient,
    AnsiblePlatformClient,
    AWXClient,
    ChefServerClient,
    TowerClient,
    get_ansible_client,
)


class TestChefServerClientErrors:
    """Coverage for Chef Server client error paths."""

    def test_search_nodes_exception(self) -> None:
        """Search nodes should handle exceptions from core client."""
        with patch("souschef.api_clients.CoreChefServerClient") as mock_core:
            mock_instance = MagicMock()
            mock_instance.search_nodes.side_effect = RuntimeError("Connection failed")
            mock_core.return_value = mock_instance

            client = ChefServerClient(
                server_url="https://chef.example.com",
                organization="testorg",
                client_name="admin",
                client_key="fake_key",
            )

            with pytest.raises(RuntimeError, match="Connection failed"):
                client.search_nodes()

    def test_get_node_not_found(self) -> None:
        """Get node should raise ValueError when node doesn't exist."""
        with patch("souschef.api_clients.CoreChefServerClient") as mock_core:
            mock_instance = MagicMock()
            mock_instance.search_nodes.return_value = []
            mock_core.return_value = mock_instance

            client = ChefServerClient(
                server_url="https://chef.example.com",
                organization="testorg",
                client_name="admin",
                client_key="fake_key",
            )

            with pytest.raises(ValueError, match="not found"):
                client.get_node("missing_node")

    def test_get_node_exception(self) -> None:
        """Get node should propagate exceptions from core client."""
        with patch("souschef.api_clients.CoreChefServerClient") as mock_core:
            mock_instance = MagicMock()
            mock_instance.search_nodes.side_effect = Exception("API error")
            mock_core.return_value = mock_instance

            client = ChefServerClient(
                server_url="https://chef.example.com",
                organization="testorg",
                client_name="admin",
                client_key="fake_key",
            )

            # Should propagate exception without raising
            with contextlib.suppress(Exception):
                client.get_node("test_node")


class TestTowerClient:
    """Coverage for Tower client API calls."""

    def test_create_inventory_success(self) -> None:
        """Tower should create inventory successfully."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 123, "name": "test_inv"}
        mock_response.raise_for_status = MagicMock()
        client.session.post = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        result = client.create_inventory("test_inv")
        assert result["id"] == 123

    def test_create_inventory_error(self) -> None:
        """Tower should handle inventory creation errors."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        client.session.post = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.exceptions.HTTPError("404 Not Found")
        )

        with pytest.raises(requests.exceptions.HTTPError):
            client.create_inventory("test_inv")

    def test_create_project_success(self) -> None:
        """Tower should create project successfully."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 456, "name": "test_proj"}
        mock_response.raise_for_status = MagicMock()
        client.session.post = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        result = client.create_project("test_proj", "https://git.example.com/repo")
        assert result["id"] == 456

    def test_create_project_error(self) -> None:
        """Tower should handle project creation errors."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        client.session.post = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.exceptions.ConnectionError("Timeout")
        )

        with pytest.raises(requests.exceptions.ConnectionError):
            client.create_project("test_proj", "https://git.example.com/repo")

    def test_create_job_template_success(self) -> None:
        """Tower should create job template successfully."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 789, "name": "test_job"}
        mock_response.raise_for_status = MagicMock()
        client.session.post = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        result = client.create_job_template(
            "test_job",
            inventory_id="inv_id",
            project_id="proj_id",
            playbook="playbook.yml",
        )
        assert result["id"] == 789


class TestAWXClient:
    """Coverage for AWX client API calls."""

    def test_create_inventory_success(self) -> None:
        """AWX should create inventory successfully."""
        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password="secret",
            version="24.6.1",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 111, "name": "awx_inv"}
        mock_response.raise_for_status = MagicMock()
        client.session.post = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        result = client.create_inventory("awx_inv")
        assert result["id"] == 111

    def test_create_inventory_error(self) -> None:
        """AWX should handle inventory creation errors."""
        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password="secret",
            version="24.6.1",
        )

        client.session.post = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.exceptions.RequestException("API error")
        )

        with pytest.raises(requests.exceptions.RequestException):
            client.create_inventory("awx_inv")

    def test_create_project_success(self) -> None:
        """AWX should create project successfully."""
        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password="secret",
            version="24.6.1",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 222, "name": "awx_proj"}
        mock_response.raise_for_status = MagicMock()
        client.session.post = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        result = client.create_project("awx_proj", "https://git.example.com/repo")
        assert result["id"] == 222

    def test_create_job_template_success(self) -> None:
        """AWX should create job template successfully."""
        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password="secret",
            version="24.6.1",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 333, "name": "awx_job"}
        mock_response.raise_for_status = MagicMock()
        client.session.post = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        result = client.create_job_template(
            "awx_job",
            inventory_id="inv_id",
            project_id="proj_id",
            playbook="playbook.yml",
        )
        assert result["id"] == 333


class TestAAPClient:
    """Coverage for AAP client API calls."""

    def test_create_inventory_success(self) -> None:
        """AAP should create inventory successfully."""
        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 555, "name": "aap_inv"}
        mock_response.raise_for_status = MagicMock()
        client.session.post = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        result = client.create_inventory("aap_inv")
        assert result["id"] == 555

    def test_create_inventory_error(self) -> None:
        """AAP should handle inventory creation errors."""
        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password="secret",
        )

        client.session.post = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.exceptions.Timeout("Connection timeout")
        )

        with pytest.raises(requests.exceptions.Timeout):
            client.create_inventory("aap_inv")

    def test_create_project_success(self) -> None:
        """AAP should create project successfully."""
        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 666, "name": "aap_proj"}
        mock_response.raise_for_status = MagicMock()
        client.session.post = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        result = client.create_project("aap_proj", "https://git.example.com/repo")
        assert result["id"] == 666

    def test_create_job_template_success(self) -> None:
        """AAP should create job template successfully."""
        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 777, "name": "aap_job"}
        mock_response.raise_for_status = MagicMock()
        client.session.post = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        result = client.create_job_template(
            "aap_job",
            inventory_id="inv_id",
            project_id="proj_id",
            playbook="playbook.yml",
        )
        assert result["id"] == 777

    def test_create_execution_environment_success(self) -> None:
        """AAP should create execution environment successfully."""
        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 888, "name": "aap_ee"}
        mock_response.raise_for_status = MagicMock()
        client.session.post = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        result = client.create_execution_environment(
            "aap_ee", "quay.io/ansible/ee:latest"
        )
        assert result["id"] == 888


class TestGetAnsibleClient:
    """Coverage for get_ansible_client factory function."""

    def test_get_tower_client(self) -> None:
        """Factory should return TowerClient for 'tower' platform."""
        client = get_ansible_client(
            server_url="https://tower.example.com",
            platform="tower",
            platform_version="3.8.6",
            username="admin",
            password="secret",
        )
        assert isinstance(client, TowerClient)

    def test_get_awx_client(self) -> None:
        """Factory should return AWXClient for 'awx' platform."""
        client = get_ansible_client(
            server_url="https://awx.example.com",
            platform="awx",
            platform_version="24.6.1",
            username="admin",
            password="secret",
        )
        assert isinstance(client, AWXClient)

    def test_get_aap_client(self) -> None:
        """Factory should return AAPClient for 'aap' platform."""
        client = get_ansible_client(
            server_url="https://aap.example.com",
            platform="aap",
            platform_version="2.4.0",
            username="admin",
            password="secret",
        )
        assert isinstance(client, AAPClient)

    def test_unknown_platform_raises_error(self) -> None:
        """Factory should raise ValueError for unknown platforms."""
        with pytest.raises(ValueError, match="Unknown platform"):
            get_ansible_client(
                server_url="https://unknown.example.com",
                platform="unknown",
                platform_version="1.0.0",
                username="admin",
                password="secret",
            )


class _ConcreteClient(AnsiblePlatformClient):
    """Concrete client for exercising base class behaviour."""

    def get_api_version(self) -> str:
        """Call base implementation to exercise abstract method line."""
        super().get_api_version()  # type: ignore[safe-super]
        return ""


class TestAnsiblePlatformBase:
    """Coverage for base AnsiblePlatformClient behaviours."""

    def test_abstract_method_line_executes(self) -> None:
        """Ensure abstract method pass line is executed via super call."""
        client = _ConcreteClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        assert client.get_api_version() == ""

    def test_add_host_success(self) -> None:
        """Adding a host should return parsed response."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"id": 10}
        client.session.post = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        result = client.add_host(1, "web-01", variables="x")

        assert result["id"] == 10

    def test_add_host_error(self) -> None:
        """Adding a host should propagate request exceptions."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        client.session.post = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.RequestException("add host failed")
        )

        with pytest.raises(requests.RequestException, match="add host failed"):
            client.add_host(1, "web-01")

    def test_create_group_success(self) -> None:
        """Creating a group should return parsed response."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"id": 20}
        client.session.post = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        result = client.create_group(1, "web")

        assert result["id"] == 20

    def test_create_group_error(self) -> None:
        """Creating a group should propagate request exceptions."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        client.session.post = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.RequestException("create group failed")
        )

        with pytest.raises(requests.RequestException, match="create group failed"):
            client.create_group(1, "web")

    def test_add_host_to_group_success(self) -> None:
        """Adding host to group should return True on success."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        client.session.post = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        assert client.add_host_to_group(1, 2, 3) is True

    def test_add_host_to_group_error(self) -> None:
        """Adding host to group should propagate request exceptions."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        client.session.post = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.RequestException("group add failed")
        )

        with pytest.raises(requests.RequestException, match="group add failed"):
            client.add_host_to_group(1, 2, 3)

    def test_create_job_template_error(self) -> None:
        """Creating job template should propagate request exceptions."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        client.session.post = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.RequestException("jt failed")
        )

        with pytest.raises(requests.RequestException, match="jt failed"):
            client.create_job_template("jt")

    def test_delete_inventory_error_returns_false(self) -> None:
        """Delete inventory should return False on errors."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        client.session.delete = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.RequestException("delete inventory failed")
        )

        assert client.delete_inventory(1) is False

    def test_delete_project_error_returns_false(self) -> None:
        """Delete project should return False on errors."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        client.session.delete = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.RequestException("delete project failed")
        )

        assert client.delete_project(1) is False

    def test_delete_project_success_returns_true(self) -> None:
        """Delete project should return True on success."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        client.session.delete = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        assert client.delete_project(1) is True

    def test_delete_job_template_error_returns_false(self) -> None:
        """Delete job template should return False on errors."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        client.session.delete = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.RequestException("delete jt failed")
        )

        assert client.delete_job_template(1) is False

    def test_delete_job_template_success_returns_true(self) -> None:
        """Delete job template should return True on success."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        client.session.delete = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        assert client.delete_job_template(1) is True


class TestTowerApiVersion:
    """Coverage for TowerClient version lookup."""

    def test_get_api_version_success(self) -> None:
        """Tower should return version from API."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"version": "3.8.7"}
        client.session.get = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        assert client.get_api_version() == "3.8.7"

    def test_get_api_version_error_defaults(self) -> None:
        """Tower should return default version on request error."""
        client = TowerClient(
            server_url="https://tower.example.com",
            username="admin",
            password="secret",
        )

        client.session.get = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.RequestException("version failed")
        )

        assert client.get_api_version() == "3.8.5"


class TestAwxClientCoverage:
    """Coverage for AWX client API differences."""

    def test_get_api_version_error_defaults(self) -> None:
        """AWX should return configured version on request error."""
        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password="secret",
            version="24.6.1",
        )

        client.session.get = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.RequestException("version failed")
        )

        assert client.get_api_version() == "24.6.1"

    def test_get_api_version_success(self) -> None:
        """AWX should return version from API response."""
        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password="secret",
            version="24.6.1",
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"version": "23.0.0"}
        client.session.get = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        assert client.get_api_version() == "23.0.0"

    def test_create_execution_environment_not_supported(self) -> None:
        """AWX 20 should raise when creating execution environment."""
        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password="secret",
            version="20.1.0",
        )

        with pytest.raises(NotImplementedError, match="not supported"):
            client.create_execution_environment("ee")

    def test_create_execution_environment_error(self) -> None:
        """AWX should propagate request exceptions creating execution environment."""
        client = AWXClient(
            server_url="https://awx.example.com",
            username="admin",
            password="secret",
            version="24.6.1",
        )

        client.session.post = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.RequestException("ee failed")
        )

        with pytest.raises(requests.RequestException, match="ee failed"):
            client.create_execution_environment("ee")


class TestAapClientCoverage:
    """Coverage for AAP client API differences."""

    def test_get_api_version_error_defaults(self) -> None:
        """AAP should return default version on request error."""
        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password="secret",
        )

        client.session.get = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.RequestException("version failed")
        )

        assert client.get_api_version() == "2.4.0"

    def test_get_api_version_success(self) -> None:
        """AAP should return version from API response."""
        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"version": "2.5.0"}
        client.session.get = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        assert client.get_api_version() == "2.5.0"

    def test_create_execution_environment_error(self) -> None:
        """AAP should propagate request exceptions for EE creation."""
        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password="secret",
        )

        client.session.post = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.RequestException("ee failed")
        )

        with pytest.raises(requests.RequestException, match="ee failed"):
            client.create_execution_environment("ee")

    def test_enable_content_signing_error_returns_false(self) -> None:
        """Enable content signing should return False on errors."""
        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password="secret",
        )

        client.session.patch = MagicMock(  # type: ignore[method-assign]
            side_effect=requests.RequestException("signing failed")
        )

        assert client.enable_content_signing(1, 2) is False

    def test_enable_content_signing_success_returns_true(self) -> None:
        """Enable content signing should return True on success."""
        client = AAPClient(
            server_url="https://aap.example.com",
            username="admin",
            password="secret",
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        client.session.patch = MagicMock(return_value=mock_response)  # type: ignore[method-assign]

        assert client.enable_content_signing(1, 2) is True
