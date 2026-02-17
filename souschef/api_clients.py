"""
API Clients for Chef Server and Ansible Platforms (Tower/AWX/AAP).

Handles authentication, requests, and response handling for each platform.
Supports all version-specific API differences.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, cast

import requests
from requests.auth import HTTPBasicAuth

from souschef.core.chef_server import ChefServerClient as CoreChefServerClient
from souschef.core.chef_server import ChefServerConfig

logger = logging.getLogger(__name__)


class ChefServerClient:
    """
    Client for Chef Server API.

    This is a wrapper around the core ChefServerClient that uses RSA-signed
    authentication. It provides a simpler interface for the migration orchestrator.
    """

    def __init__(
        self,
        server_url: str,
        organization: str,
        client_name: str,
        client_key: str,
        chef_version: str = "15.10.91",
    ):
        """
        Initialize Chef Server client.

        Args:
            server_url: Chef Server URL.
            organization: Chef organization.
            client_name: Client name for authentication.
            client_key: Client private key for authentication.
            chef_version: Chef version for API compatibility.

        """
        self.server_url = server_url.rstrip("/")
        self.organization = organization
        self.client_name = client_name
        self.client_key = client_key
        self.chef_version = chef_version

        # Initialize the core authenticated client
        config = ChefServerConfig(
            server_url=self.server_url,
            organisation=organization,
            client_name=client_name,
            client_key=client_key,
        )
        self._client = CoreChefServerClient(config)

    def search_nodes(self, query: str = "*") -> dict[str, Any]:
        """
        Search for nodes in Chef Server.

        Args:
            query: Search query (default: all nodes).

        Returns:
            Search results with node information.

        """
        try:
            nodes = self._client.search_nodes(query)
            logger.debug(f"Retrieved {len(nodes)} nodes")
            # Wrap in Chef Server API format
            return {"rows": nodes, "total": len(nodes)}
        except Exception as e:
            logger.error(f"Failed to search nodes: {e}")
            raise

    def get_node(self, node_name: str) -> dict[str, Any]:
        """
        Get node details from Chef Server.

        Args:
            node_name: Name of the node.

        Returns:
            Node details including attributes, recipes, roles.

        """
        try:
            # Use search to get node details (core client doesn't have get_node yet)
            results = self._client.search_nodes(f"name:{node_name}")
            if not results:
                raise ValueError(f"Node {node_name} not found")
            return results[0]
        except Exception as e:
            logger.error(f"Failed to get node {node_name}: {e}")
            raise

    def get_role(self, role_name: str) -> dict[str, Any]:
        """
        Get role definition from Chef Server.

        Args:
            role_name: Name of the role.

        Returns:
            Role definition including recipes and attributes.

        """
        try:
            roles = self._client.list_roles()
            for role in roles:
                if role.get("name") == role_name:
                    return role
            raise ValueError(f"Role {role_name} not found")
        except Exception as e:
            logger.error(f"Failed to get role {role_name}: {e}")
            raise

    def get_cookbook(self, cookbook_name: str) -> dict[str, Any]:
        """
        Get cookbook details from Chef Server.

        Args:
            cookbook_name: Name of the cookbook.

        Returns:
            Cookbook metadata and versions.

        """
        try:
            cookbooks = self._client.list_cookbooks()
            for cookbook in cookbooks:
                if cookbook.get("name") == cookbook_name:
                    return cookbook
            raise ValueError(f"Cookbook {cookbook_name} not found")
        except Exception as e:
            logger.error(f"Failed to get cookbook {cookbook_name}: {e}")
            raise


class AnsiblePlatformClient(ABC):
    """Abstract base for Ansible Platform clients."""

    def __init__(
        self,
        server_url: str,
        username: str,
        password: str,
        verify_ssl: bool = True,
    ):
        """
        Initialize Ansible Platform client.

        Args:
            server_url: Platform URL.
            username: Username for authentication.
            password: Password for authentication.
            verify_ssl: Verify SSL certificates.

        """
        self.server_url = server_url.rstrip("/")
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)
        self.session.verify = verify_ssl

    @abstractmethod
    def get_api_version(self) -> str:
        """Get platform version."""
        pass

    def create_inventory(self, name: str) -> dict[str, Any]:
        """Create inventory."""
        url = f"{self.server_url}/api/v2/inventories/"
        data = {"name": name, "kind": "ssh"}

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            result = cast(dict[str, Any], response.json())
            logger.debug(f"Created inventory: {result['id']}")
            return result
        except requests.RequestException as e:
            logger.error(f"Failed to create inventory: {e}")
            raise

    def add_host(
        self, inventory_id: int, hostname: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Add host to inventory."""
        url = f"{self.server_url}/api/v2/inventories/{inventory_id}/hosts/"
        data = {"name": hostname, **kwargs}

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            result = cast(dict[str, Any], response.json())
            logger.debug(f"Added host {hostname}: {result['id']}")
            return result
        except requests.RequestException as e:
            logger.error(f"Failed to add host {hostname}: {e}")
            raise

    def create_group(
        self, inventory_id: int, name: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Create a group within an inventory."""
        url = f"{self.server_url}/api/v2/inventories/{inventory_id}/groups/"
        data = {"name": name, **kwargs}

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            result = cast(dict[str, Any], response.json())
            logger.debug(
                f"Created group {name} in inventory {inventory_id}: {result['id']}"
            )
            return result
        except requests.RequestException as e:
            logger.error(f"Failed to create group {name}: {e}")
            raise

    def add_host_to_group(self, inventory_id: int, group_id: int, host_id: int) -> bool:
        """Add a host to a group."""
        url = f"{self.server_url}/api/v2/groups/{group_id}/hosts/"
        data = {"id": host_id}

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            logger.debug(f"Added host {host_id} to group {group_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to add host to group: {e}")
            raise

    def create_project(
        self, name: str, scm_type: str = "git", **kwargs: Any
    ) -> dict[str, Any]:
        """Create project."""
        url = f"{self.server_url}/api/v2/projects/"
        data = {"name": name, "scm_type": scm_type, **kwargs}

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            result = cast(dict[str, Any], response.json())
            logger.debug(f"Created project: {result['id']}")
            return result
        except requests.RequestException as e:
            logger.error(f"Failed to create project: {e}")
            raise

    def create_job_template(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """Create job template."""
        url = f"{self.server_url}/api/v2/job_templates/"
        data = {"name": name, **kwargs}

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            result = cast(dict[str, Any], response.json())
            logger.debug(f"Created job template: {result['id']}")
            return result
        except requests.RequestException as e:
            logger.error(f"Failed to create job template: {e}")
            raise

    def delete_inventory(self, inventory_id: int) -> bool:
        """Delete inventory."""
        url = f"{self.server_url}/api/v2/inventories/{inventory_id}/"

        try:
            response = self.session.delete(url)
            response.raise_for_status()
            logger.debug(f"Deleted inventory {inventory_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to delete inventory: {e}")
            return False

    def delete_project(self, project_id: int) -> bool:
        """Delete project."""
        url = f"{self.server_url}/api/v2/projects/{project_id}/"

        try:
            response = self.session.delete(url)
            response.raise_for_status()
            logger.debug(f"Deleted project {project_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to delete project: {e}")
            return False

    def delete_job_template(self, jt_id: int) -> bool:
        """Delete job template."""
        url = f"{self.server_url}/api/v2/job_templates/{jt_id}/"

        try:
            response = self.session.delete(url)
            response.raise_for_status()
            logger.debug(f"Deleted job template {jt_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to delete job template: {e}")
            return False


class TowerClient(AnsiblePlatformClient):
    """Client for Ansible Tower 3.8.x."""

    def get_api_version(self) -> str:
        """Get Tower version."""
        url = f"{self.server_url}/api/v2/config/"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = cast(dict[str, Any], response.json())
            return cast(str, data.get("version", "3.8.5"))
        except requests.RequestException:
            return "3.8.5"


class AWXClient(AnsiblePlatformClient):
    """Client for AWX 20.x-24.6.1."""

    def __init__(
        self,
        server_url: str,
        username: str,
        password: str,
        version: str = "24.6.1",
        verify_ssl: bool = True,
    ):
        """Initialize AWX client."""
        super().__init__(server_url, username, password, verify_ssl)
        self.version = version

    def get_api_version(self) -> str:
        """Get AWX version."""
        url = f"{self.server_url}/api/v2/config/"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = cast(dict[str, Any], response.json())
            return cast(str, data.get("version", self.version))
        except requests.RequestException:
            return self.version

    def create_execution_environment(
        self, name: str, image: str = "quay.io/ansible/creator-ee:0.5.0", **kwargs: Any
    ) -> dict[str, Any]:
        """Create execution environment (AWX 21+)."""
        if "20" in self.version:
            raise NotImplementedError(
                f"Execution environments not supported in AWX {self.version}"
            )

        url = f"{self.server_url}/api/v2/execution_environments/"
        data = {"name": name, "image": image, **kwargs}

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            logger.debug(f"Created EE: {cast(dict[str, Any], response.json())['id']}")
            return cast(dict[str, Any], response.json())
        except requests.RequestException as e:
            logger.error(f"Failed to create EE: {e}")
            raise


class AAPClient(AnsiblePlatformClient):
    """Client for Ansible Automation Platform 2.4+."""

    def get_api_version(self) -> str:
        """Get AAP version."""
        url = f"{self.server_url}/api/v2/config/"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = cast(dict[str, Any], response.json())
            return cast(str, data.get("version", "2.4.0"))
        except requests.RequestException:
            return "2.4.0"

    def create_execution_environment(
        self, name: str, image: str = "quay.io/ansible/creator-ee:0.5.0", **kwargs: Any
    ) -> dict[str, Any]:
        """Create execution environment (required in AAP)."""
        url = f"{self.server_url}/api/v2/execution_environments/"
        data = {"name": name, "image": image, **kwargs}

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            logger.debug(f"Created EE: {cast(dict[str, Any], response.json())['id']}")
            return cast(dict[str, Any], response.json())
        except requests.RequestException as e:
            logger.error(f"Failed to create EE: {e}")
            raise

    def enable_content_signing(self, job_template_id: int, signing_key_id: int) -> bool:
        """Enable content signing on job template (AAP 2.4)."""
        url = f"{self.server_url}/api/v2/job_templates/{job_template_id}/"
        data = {"content_signing": True, "signing_key": signing_key_id}

        try:
            response = self.session.patch(url, json=data)
            response.raise_for_status()
            logger.debug(f"Enabled content signing on JT {job_template_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to enable content signing: {e}")
            return False


def get_ansible_client(
    server_url: str,
    platform: str,
    platform_version: str,
    username: str,
    password: str,
) -> AnsiblePlatformClient:
    """
    Get appropriate Ansible client for the specified platform.

    Args:
        server_url: URL of Ansible platform.
        platform: Platform type (tower, awx, aap).
        platform_version: Platform version string.
        username: Username for authentication.
        password: Password for authentication.

    Returns:
        Appropriate client instance for the platform.

    Raises:
        ValueError: If platform is not supported.

    """
    if platform == "tower":
        return TowerClient(server_url, username, password)
    elif platform == "awx":
        return AWXClient(server_url, username, password, version=platform_version)
    elif platform == "aap":
        return AAPClient(server_url, username, password)
    else:
        raise ValueError(f"Unknown platform: {platform}")
