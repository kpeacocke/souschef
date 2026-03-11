"""
Unit tests for the Puppet migration MCP server tools.

Tests cover all Puppet-related MCP tools registered in server.py:
- parse_puppet_manifest
- parse_puppet_module
- convert_puppet_manifest_to_ansible
- convert_puppet_module_to_ansible
- convert_puppet_resource_to_task
- list_puppet_supported_resource_types
"""

from pathlib import Path

import yaml

from souschef.server import (
    convert_puppet_manifest_to_ansible,
    convert_puppet_module_to_ansible,
    convert_puppet_resource_to_task,
    list_puppet_supported_resource_types,
    parse_puppet_manifest,
    parse_puppet_module,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_MANIFEST = """\
package { 'nginx':
  ensure => installed,
}

service { 'nginx':
  ensure => running,
}
"""


# ---------------------------------------------------------------------------
# Tests: parse_puppet_manifest (MCP tool)
# ---------------------------------------------------------------------------


def test_mcp_parse_puppet_manifest_success(tmp_path: Path) -> None:
    """Test that parse_puppet_manifest tool returns analysis results."""
    manifest = tmp_path / "test.pp"
    manifest.write_text(SIMPLE_MANIFEST, encoding="utf-8")

    result = parse_puppet_manifest(str(manifest))

    assert "Puppet Manifest Analysis" in result
    assert "nginx" in result


def test_mcp_parse_puppet_manifest_not_found(tmp_path: Path) -> None:
    """Test that parse_puppet_manifest handles missing files."""
    result = parse_puppet_manifest(str(tmp_path / "missing.pp"))
    assert "Error" in result or "not found" in result.lower()


def test_mcp_parse_puppet_manifest_empty(tmp_path: Path) -> None:
    """Test that parse_puppet_manifest handles empty manifests."""
    manifest = tmp_path / "empty.pp"
    manifest.write_text("", encoding="utf-8")
    result = parse_puppet_manifest(str(manifest))
    assert "Total resources: 0" in result


# ---------------------------------------------------------------------------
# Tests: parse_puppet_module (MCP tool)
# ---------------------------------------------------------------------------


def test_mcp_parse_puppet_module_success(tmp_path: Path) -> None:
    """Test that parse_puppet_module tool processes a directory."""
    (tmp_path / "init.pp").write_text(SIMPLE_MANIFEST, encoding="utf-8")
    result = parse_puppet_module(str(tmp_path))
    assert "Puppet Manifest Analysis" in result


def test_mcp_parse_puppet_module_no_manifests(tmp_path: Path) -> None:
    """Test that parse_puppet_module handles directory with no .pp files."""
    result = parse_puppet_module(str(tmp_path))
    assert "Warning" in result or "No Puppet manifests" in result


def test_mcp_parse_puppet_module_not_found(tmp_path: Path) -> None:
    """Test that parse_puppet_module handles missing directory."""
    result = parse_puppet_module(str(tmp_path / "missing"))
    assert "Error" in result or "not found" in result.lower()


# ---------------------------------------------------------------------------
# Tests: convert_puppet_manifest_to_ansible (MCP tool)
# ---------------------------------------------------------------------------


def test_mcp_convert_puppet_manifest_to_ansible_success(tmp_path: Path) -> None:
    """Test that convert_puppet_manifest_to_ansible returns valid YAML."""
    manifest = tmp_path / "test.pp"
    manifest.write_text(SIMPLE_MANIFEST, encoding="utf-8")

    result = convert_puppet_manifest_to_ansible(str(manifest))

    playbook = yaml.safe_load(result)
    assert isinstance(playbook, list)
    assert playbook[0]["hosts"] == "all"


def test_mcp_convert_puppet_manifest_not_found(tmp_path: Path) -> None:
    """Test that convert_puppet_manifest_to_ansible handles missing files."""
    result = convert_puppet_manifest_to_ansible(str(tmp_path / "missing.pp"))
    assert "Error" in result or "not found" in result.lower()


# ---------------------------------------------------------------------------
# Tests: convert_puppet_module_to_ansible (MCP tool)
# ---------------------------------------------------------------------------


def test_mcp_convert_puppet_module_to_ansible_success(tmp_path: Path) -> None:
    """Test that convert_puppet_module_to_ansible returns valid YAML."""
    (tmp_path / "init.pp").write_text(SIMPLE_MANIFEST, encoding="utf-8")

    result = convert_puppet_module_to_ansible(str(tmp_path))

    playbook = yaml.safe_load(result)
    assert isinstance(playbook, list)


def test_mcp_convert_puppet_module_no_manifests(tmp_path: Path) -> None:
    """Test that convert_puppet_module_to_ansible handles empty directories."""
    result = convert_puppet_module_to_ansible(str(tmp_path))
    assert "Warning" in result or "No Puppet manifests" in result


# ---------------------------------------------------------------------------
# Tests: convert_puppet_resource_to_task (MCP tool)
# ---------------------------------------------------------------------------


def test_mcp_convert_puppet_resource_package() -> None:
    """Test converting a package resource via MCP tool."""
    result = convert_puppet_resource_to_task("package", "nginx", "ensure=installed")
    task = yaml.safe_load(result)
    assert "ansible.builtin.package" in task
    assert task["ansible.builtin.package"]["name"] == "nginx"


def test_mcp_convert_puppet_resource_service() -> None:
    """Test converting a service resource via MCP tool."""
    result = convert_puppet_resource_to_task("service", "nginx", "ensure=running")
    task = yaml.safe_load(result)
    assert "ansible.builtin.service" in task


def test_mcp_convert_puppet_resource_no_attributes() -> None:
    """Test converting a resource with no attributes."""
    result = convert_puppet_resource_to_task("package", "vim")
    task = yaml.safe_load(result)
    assert "ansible.builtin.package" in task


def test_mcp_convert_puppet_resource_multiple_attributes() -> None:
    """Test converting a resource with multiple attributes."""
    result = convert_puppet_resource_to_task(
        "file", "/etc/app", "ensure=directory,owner=root,mode=0755"
    )
    task = yaml.safe_load(result)
    assert "ansible.builtin.file" in task


def test_mcp_convert_puppet_resource_unsupported_type() -> None:
    """Test converting an unsupported resource type."""
    result = convert_puppet_resource_to_task("augeas", "test", "")
    task = yaml.safe_load(result)
    assert "ansible.builtin.debug" in task


def test_mcp_convert_puppet_resource_empty_attribute_value() -> None:
    """Test parsing attribute string with extra spaces."""
    result = convert_puppet_resource_to_task("package", "vim", "  ensure = present  ")
    task = yaml.safe_load(result)
    assert "ansible.builtin.package" in task


def test_mcp_convert_puppet_resource_attribute_without_equals() -> None:
    """Test that attribute pairs without '=' are ignored gracefully."""
    result = convert_puppet_resource_to_task("package", "vim", "notapair")
    task = yaml.safe_load(result)
    assert "ansible.builtin.package" in task


# ---------------------------------------------------------------------------
# Tests: list_puppet_supported_resource_types (MCP tool)
# ---------------------------------------------------------------------------


def test_mcp_list_puppet_supported_resource_types() -> None:
    """Test that the supported types listing is comprehensive."""
    result = list_puppet_supported_resource_types()

    assert "package" in result
    assert "service" in result
    assert "file" in result
    assert "user" in result
    assert "group" in result
    assert "exec" in result
    assert "ansible.builtin.package" in result
    assert "Total:" in result
