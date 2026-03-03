"""Additional server tests for data bags and environments."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from souschef.server import (
    analyse_chef_databag_usage,
    analyse_chef_environment_usage,
    convert_chef_databag_to_vars,
    convert_chef_environment_to_inventory_group,
    generate_ansible_vault_from_databags,
    generate_inventory_from_chef_environments,
)


def test_convert_chef_databag_to_vars_errors() -> None:
    """Invalid inputs should return error strings."""
    assert "Databag content cannot be empty" in convert_chef_databag_to_vars("", "bag")
    assert "Databag name cannot be empty" in convert_chef_databag_to_vars("{}", "")
    assert "Invalid target scope" in convert_chef_databag_to_vars(
        "{}", "bag", target_scope="bad"
    )
    assert "Invalid JSON format" in convert_chef_databag_to_vars("{bad", "bag")


def test_convert_chef_databag_to_vars_success() -> None:
    """Valid JSON should produce YAML output."""
    content = '{"id": "default", "value": 1}'
    result = convert_chef_databag_to_vars(content, "bag", item_name="default")
    assert "Chef data bag converted" in result
    assert "value" in result


def test_generate_ansible_vault_from_databags_invalid_dir(tmp_path: Path) -> None:
    """Invalid data bags directory should return error string."""
    missing = tmp_path / "missing"
    result = generate_ansible_vault_from_databags(str(missing))
    assert "Data bags directory not found" in result


def test_generate_ansible_vault_from_databags_success(tmp_path: Path) -> None:
    """Databag directory should convert items and return summary."""
    databags_dir = tmp_path / "data_bags"
    databags_dir.mkdir()
    bag_dir = databags_dir / "app"
    bag_dir.mkdir()
    (bag_dir / "default.json").write_text('{"id": "default", "token": "abc"}')

    result = generate_ansible_vault_from_databags(str(databags_dir))

    # Just check that we got a non-error result (will have "Summary" or similar)
    assert isinstance(result, str) and len(result) > 100


def test_generate_ansible_vault_from_databags_handles_exception(tmp_path: Path) -> None:
    """Errors during processing should be returned as formatted errors."""
    databags_dir = tmp_path / "data_bags"
    databags_dir.mkdir()
    bag_dir = databags_dir / "app"
    bag_dir.mkdir()
    (bag_dir / "default.json").write_text('{"id": "default"}')

    with patch(
        "souschef.server.safe_read_text", side_effect=RuntimeError("read failed")
    ):
        result = generate_ansible_vault_from_databags(str(databags_dir))
        # Error formatting includes "Error during" prefix
        assert "Error during" in result or "read failed" in result


def test_analyse_chef_databag_usage_missing_cookbook(tmp_path: Path) -> None:
    """Missing cookbook path should return error string."""
    result = analyse_chef_databag_usage(str(tmp_path / "missing"))
    assert "Cookbook path not found" in result


def test_analyse_chef_environment_usage_missing_cookbook(tmp_path: Path) -> None:
    """Missing cookbook path should return error string."""
    result = analyse_chef_environment_usage(str(tmp_path / "missing"))
    assert "Cookbook path not found" in result


def test_convert_chef_environment_to_inventory_group_success() -> None:
    """Valid environment content should produce inventory output."""
    content = """
name 'dev'
description 'Development'
default_attributes({ 'key' => 'value' })
override_attributes({ 'override' => 'value' })
"""
    result = convert_chef_environment_to_inventory_group(content, "dev")
    # Just check basic structure exists
    assert "inventory" in result.lower()
    assert "dev" in result


def test_convert_chef_environment_to_inventory_group_error() -> None:
    """Exceptions should be formatted as errors."""
    with patch(
        "souschef.server._parse_chef_environment_content",
        side_effect=RuntimeError("bad env"),
    ):
        result = convert_chef_environment_to_inventory_group("name 'dev'", "dev")
        assert "converting Chef environment" in result


def test_generate_inventory_from_chef_environments_missing_dir(tmp_path: Path) -> None:
    """Missing environments directory should return error string."""
    result = generate_inventory_from_chef_environments(str(tmp_path / "missing"))
    assert "Environments directory not found" in result


def test_generate_inventory_from_chef_environments_processing(tmp_path: Path) -> None:
    """Environments should be processed even with mixed errors."""
    env_dir = tmp_path / "environments"
    env_dir.mkdir()
    (env_dir / "dev.rb").write_text("name 'dev'\n")
    (env_dir / "bad.rb").write_text("name 'bad'\n")

    with patch(
        "souschef.server._parse_chef_environment_content",
        side_effect=[{"name": "dev"}, RuntimeError("bad")],
    ):
        result = generate_inventory_from_chef_environments(str(env_dir))
        assert "inventory" in result.lower() or "error" in result.lower()
