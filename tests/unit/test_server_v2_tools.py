"""Tests for server v2 tool handlers and helpers."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from souschef.server import (
    deploy_v2_migration,
    parse_chef_handler,
    query_chef_server,
    rollback_v2_migration,
    validate_v2_playbooks,
)


def test_deploy_v2_migration_returns_ready_status() -> None:
    """Test deploy returns deployment ready payload."""
    result = deploy_v2_migration(
        migration_id="m123",
        ansible_url="https://ansible.example",
        ansible_username="user",
        ansible_password="pass",
    )

    data = json.loads(result)
    assert data["status"] == "deployment_ready"
    assert data["migration_id"] == "m123"


def test_validate_v2_playbooks_returns_entries() -> None:
    """Test playbook validation returns per-playbook results."""
    result = validate_v2_playbooks(
        playbook_paths="a.yml,b.yml",
        target_ansible_version="2.16",
    )

    data = json.loads(result)
    assert data["playbooks_validated"] == 2
    assert data["target_ansible_version"] == "2.16"
    assert len(data["playbooks"]) == 2


def test_rollback_v2_migration_with_ids() -> None:
    """Test rollback returns deleted resources list."""
    result = rollback_v2_migration(
        ansible_url="https://ansible.example",
        ansible_username="user",
        ansible_password="pass",
        inventory_id=1,
        project_id=2,
        job_template_id=3,
    )

    data = json.loads(result)
    assert data["status"] == "rollback_complete"
    assert "job_template:3" in data["deleted_resources"]
    assert "inventory:1" in data["deleted_resources"]
    assert "project:2" in data["deleted_resources"]


def test_query_chef_server_success() -> None:
    """Test Chef Server query returns node list on success."""
    mock_client = MagicMock()
    mock_client.search_nodes.return_value = {
        "total": 1,
        "rows": [{"name": "node1"}],
    }

    with patch("souschef.server.ChefServerClient", return_value=mock_client):
        result = query_chef_server(
            chef_url="https://chef.example",
            organization="default",
            client_name="user",
            client_key="key",
            query="*",
        )

    data = json.loads(result)
    assert data["status"] == "success"
    assert data["total_nodes"] == 1
    assert data["nodes"][0]["name"] == "node1"


def test_query_chef_server_failure() -> None:
    """Test Chef Server query handles errors."""
    with patch("souschef.server.ChefServerClient", side_effect=RuntimeError("boom")):
        result = query_chef_server(
            chef_url="https://chef.example",
            organization="default",
            client_name="user",
            client_key="key",
            query="*",
        )

    data = json.loads(result)
    assert data["status"] == "failed"
    assert "error" in data


def test_parse_chef_handler_success(tmp_path: Path) -> None:
    """Test Chef handler parsing returns structured data."""
    handler_file = tmp_path / "handler.rb"
    handler_file.write_text("class Handler; end")

    with (
        patch(
            "souschef.converters.parse_chef_handler_class",
            return_value={"name": "Handler"},
        ),
        patch(
            "souschef.converters.detect_handler_patterns",
            return_value=["pattern"],
        ),
        patch(
            "souschef.converters.build_handler_routing_table",
            return_value={"route": "value"},
        ),
    ):
        result = parse_chef_handler(str(handler_file))

    data = json.loads(result)
    assert data["status"] == "success"
    assert data["handler_info"]["name"] == "Handler"
    assert data["patterns"] == ["pattern"]


def test_parse_chef_handler_file_not_found(tmp_path: Path) -> None:
    """Test handler parsing returns file not found status."""
    missing_path = tmp_path / "missing.rb"
    result = parse_chef_handler(str(missing_path))

    data = json.loads(result)
    assert data["status"] == "file_not_found"


def test_parse_chef_handler_parse_error(tmp_path: Path) -> None:
    """Test handler parsing returns parse error on exception."""
    handler_file = tmp_path / "handler.rb"
    handler_file.write_text("class Handler; end")

    with patch(
        "souschef.converters.parse_chef_handler_class",
        side_effect=RuntimeError("parse failed"),
    ):
        result = parse_chef_handler(str(handler_file))

    data = json.loads(result)
    assert data["status"] == "parse_error"
    assert "parse failed" in data["error"]
