"""Tests for Chef Server listing tools in server module."""

import json
from unittest.mock import patch

from souschef.server import (
    get_chef_cookbooks,
    get_chef_environments,
    get_chef_policies,
    get_chef_roles,
)


def test_get_chef_roles_success() -> None:
    """Roles listing returns success payload."""
    with patch("souschef.server._list_chef_roles", return_value=[{"name": "role"}]):
        result = get_chef_roles(server_url="url", organisation="org")

    data = json.loads(result)
    assert data["status"] == "success"
    assert data["count"] == 1


def test_get_chef_roles_error() -> None:
    """Roles listing handles errors."""
    with patch("souschef.server._list_chef_roles", side_effect=RuntimeError("boom")):
        result = get_chef_roles(server_url="url", organisation="org")

    data = json.loads(result)
    assert data["status"] == "error"
    assert "Error querying Chef Server" in data["message"]


def test_get_chef_environments_success() -> None:
    """Environments listing returns success payload."""
    with patch(
        "souschef.server._list_chef_environments", return_value=[{"name": "env"}]
    ):
        result = get_chef_environments(server_url="url", organisation="org")

    data = json.loads(result)
    assert data["status"] == "success"
    assert data["count"] == 1


def test_get_chef_environments_error() -> None:
    """Environments listing handles errors."""
    with patch(
        "souschef.server._list_chef_environments", side_effect=RuntimeError("boom")
    ):
        result = get_chef_environments(server_url="url", organisation="org")

    data = json.loads(result)
    assert data["status"] == "error"


def test_get_chef_cookbooks_success() -> None:
    """Cookbooks listing returns success payload."""
    with patch("souschef.server._list_chef_cookbooks", return_value=[{"name": "cb"}]):
        result = get_chef_cookbooks(server_url="url", organisation="org")

    data = json.loads(result)
    assert data["status"] == "success"
    assert data["count"] == 1


def test_get_chef_cookbooks_error() -> None:
    """Cookbooks listing handles errors."""
    with patch(
        "souschef.server._list_chef_cookbooks", side_effect=RuntimeError("boom")
    ):
        result = get_chef_cookbooks(server_url="url", organisation="org")

    data = json.loads(result)
    assert data["status"] == "error"


def test_get_chef_policies_success() -> None:
    """Policies listing returns success payload."""
    with patch(
        "souschef.server._list_chef_policies", return_value=[{"name": "policy"}]
    ):
        result = get_chef_policies(server_url="url", organisation="org")

    data = json.loads(result)
    assert data["status"] == "success"
    assert data["count"] == 1


def test_get_chef_policies_error() -> None:
    """Policies listing handles errors."""
    with patch("souschef.server._list_chef_policies", side_effect=RuntimeError("boom")):
        result = get_chef_policies(server_url="url", organisation="org")

    data = json.loads(result)
    assert data["status"] == "error"
