"""Coverage tests for parsers/ansible_inventory.py."""

import configparser
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from souschef.parsers.ansible_inventory import (
    _extract_version_from_output,
    _parse_collections,
    _parse_config_for_paths,
    _parse_group_header,
    _parse_roles,
    _validate_ansible_executable,
    detect_ansible_version,
    parse_ansible_cfg,
    parse_inventory_file,
    parse_inventory_yaml,
    parse_requirements_yml,
    scan_playbook_for_version_issues,
)


def test_parse_ansible_cfg_invalid_format(tmp_path: Path) -> None:
    """Invalid ansible.cfg should raise ValueError."""
    cfg_path = tmp_path / "ansible.cfg"
    cfg_path.write_text("[defaults]\n")

    with (
        patch("configparser.ConfigParser.read", side_effect=configparser.Error("bad")),
        pytest.raises(ValueError, match="Invalid ansible.cfg format"),
    ):
        parse_ansible_cfg(str(cfg_path))


def test_parse_group_header_invalid_pattern() -> None:
    """Invalid group header should return None."""
    inventory: dict[str, Any] = {"groups": {}}
    assert _parse_group_header("[group:]", inventory) is None


def test_parse_inventory_yaml_yaml_error(tmp_path: Path) -> None:
    """Invalid YAML should raise ValueError."""
    inv_path = tmp_path / "inventory.yml"
    inv_path.write_text("- [")

    with (
        patch("yaml.safe_load", side_effect=yaml.YAMLError("bad")),
        pytest.raises(ValueError, match="Invalid inventory YAML"),
    ):
        parse_inventory_yaml(str(inv_path))


def test_parse_inventory_yaml_none_returns_empty(tmp_path: Path) -> None:
    """Empty YAML should return empty dict."""
    inv_path = tmp_path / "inventory.yml"
    inv_path.write_text("")

    with patch("yaml.safe_load", return_value=None):
        result = parse_inventory_yaml(str(inv_path))

    assert result == {}


def test_parse_inventory_yaml_non_dict_raises(tmp_path: Path) -> None:
    """Non-dict YAML should raise ValueError."""
    inv_path = tmp_path / "inventory.yml"
    inv_path.write_text("- item")

    with (
        patch("yaml.safe_load", return_value=["item"]),
        pytest.raises(ValueError, match="expected dict"),
    ):
        parse_inventory_yaml(str(inv_path))


def test_parse_inventory_file_path_not_file(tmp_path: Path) -> None:
    """Inventory path that is a directory should raise ValueError."""
    with pytest.raises(ValueError, match="Inventory path is not a file"):
        parse_inventory_file(str(tmp_path))


def test_parse_inventory_file_unknown_suffix(tmp_path: Path) -> None:
    """Unknown suffix should raise ValueError."""
    inv_path = tmp_path / "inventory.txt"
    inv_path.write_text("host1")

    with pytest.raises(ValueError, match="Unknown inventory file format"):
        parse_inventory_file(str(inv_path))


def test_parse_inventory_file_ini_then_yaml_fail(tmp_path: Path) -> None:
    """INI parse failure should fall back to YAML and error if YAML fails."""
    inv_path = tmp_path / "inventory.ini"
    inv_path.write_text("[bad]")

    with (
        patch(
            "souschef.parsers.ansible_inventory.parse_inventory_ini",
            side_effect=ValueError("bad"),
        ),
        patch(
            "souschef.parsers.ansible_inventory.parse_inventory_yaml",
            side_effect=ValueError("bad yaml"),
        ),
        pytest.raises(ValueError, match="Could not parse"),
    ):
        parse_inventory_file(str(inv_path))


def test_validate_ansible_executable_not_exists(tmp_path: Path) -> None:
    """Missing ansible executable should raise ValueError."""
    with pytest.raises(ValueError, match="does not exist"):
        _validate_ansible_executable(str(tmp_path / "ansible"))


def test_validate_ansible_executable_not_file(tmp_path: Path) -> None:
    """Directory path should raise ValueError."""
    ansible_dir = tmp_path / "ansible"
    ansible_dir.mkdir()

    with pytest.raises(ValueError, match="is not a file"):
        _validate_ansible_executable(str(ansible_dir))


def test_validate_ansible_executable_wrong_name(tmp_path: Path) -> None:
    """Executable with wrong name should raise ValueError."""
    exec_path = tmp_path / "ansible-playbook"
    exec_path.write_text("#!/bin/sh\n")
    exec_path.chmod(0o755)

    with pytest.raises(ValueError, match="must be named 'ansible'"):
        _validate_ansible_executable(str(exec_path))


def test_validate_ansible_executable_not_executable(tmp_path: Path) -> None:
    """Non-executable file should raise ValueError."""
    exec_path = tmp_path / "ansible"
    exec_path.write_text("#!/bin/sh\n")
    exec_path.chmod(0o644)

    with pytest.raises(ValueError, match="not executable"):
        _validate_ansible_executable(str(exec_path))


def test_extract_version_from_output_core() -> None:
    """Should parse version from core output."""
    output = "ansible [core 2.16.0]"
    assert _extract_version_from_output(output) == "2.16.0"


def test_extract_version_from_output_simple() -> None:
    """Should parse version from simple output."""
    output = "ansible 2.14.0"
    assert _extract_version_from_output(output) == "2.14.0"


def test_extract_version_from_output_invalid() -> None:
    """Invalid output should raise RuntimeError."""
    with pytest.raises(RuntimeError, match="Could not parse"):
        _extract_version_from_output("unexpected")


def test_detect_ansible_version_file_not_found() -> None:
    """FileNotFoundError from subprocess should be wrapped."""
    with (
        patch("subprocess.run", side_effect=FileNotFoundError("missing")),
        pytest.raises(FileNotFoundError, match="not found"),
    ):
        detect_ansible_version()


def test_detect_ansible_version_timeout() -> None:
    """Timeout should raise RuntimeError."""
    with (
        patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["ansible"], timeout=10),
        ),
        pytest.raises(RuntimeError, match="timed out"),
    ):
        detect_ansible_version()


def test_detect_ansible_version_called_process_error() -> None:
    """CalledProcessError should raise RuntimeError with stderr."""
    error = subprocess.CalledProcessError(1, ["ansible"], stderr="bad")
    with (
        patch("subprocess.run", side_effect=error),
        pytest.raises(RuntimeError, match="bad"),
    ):
        detect_ansible_version()


def test_parse_collections_with_string_item() -> None:
    """String collection entries should map to '*' versions."""
    result = _parse_collections({"collections": ["community.general"]})
    assert result == {"community.general": "*"}


def test_parse_roles_with_string_item() -> None:
    """String role entries should map to '*' versions."""
    result = _parse_roles({"roles": ["myrole"]})
    assert result == {"myrole": "*"}


def test_parse_requirements_invalid_name(tmp_path: Path) -> None:
    """Invalid requirements file name should raise ValueError."""
    req_path = tmp_path / "other.yml"
    req_path.write_text("collections: []")

    with pytest.raises(ValueError, match="Invalid requirements file name"):
        parse_requirements_yml(str(req_path))


def test_parse_requirements_missing_file(tmp_path: Path) -> None:
    """Missing requirements file should raise FileNotFoundError."""
    req_path = tmp_path / "requirements.yml"

    with pytest.raises(FileNotFoundError, match="Requirements file not found"):
        parse_requirements_yml(str(req_path))


def test_parse_requirements_not_file(tmp_path: Path) -> None:
    """Directory requirements path should raise ValueError."""
    req_path = tmp_path / "requirements.yml"
    req_path.mkdir()

    with pytest.raises(ValueError, match="Requirements path is not a file"):
        parse_requirements_yml(str(req_path))


def test_parse_requirements_yaml_error(tmp_path: Path) -> None:
    """Invalid requirements YAML should raise ValueError."""
    req_path = tmp_path / "requirements.yml"
    req_path.write_text("invalid")

    with (
        patch("yaml.safe_load", side_effect=yaml.YAMLError("bad")),
        pytest.raises(ValueError, match="Invalid requirements YAML"),
    ):
        parse_requirements_yml(str(req_path))


def test_parse_requirements_empty_returns_dict(tmp_path: Path) -> None:
    """Empty requirements should return empty dict."""
    req_path = tmp_path / "requirements.yml"
    req_path.write_text("")

    with patch("yaml.safe_load", return_value=None):
        assert parse_requirements_yml(str(req_path)) == {}


def test_parse_requirements_non_dict_raises(tmp_path: Path) -> None:
    """Non-dict requirements should raise ValueError."""
    req_path = tmp_path / "requirements.yml"
    req_path.write_text("- item")

    with (
        patch("yaml.safe_load", return_value=["item"]),
        pytest.raises(ValueError, match="expected dict"),
    ):
        parse_requirements_yml(str(req_path))


def test_scan_playbook_invalid_yaml(tmp_path: Path) -> None:
    """Invalid playbook YAML should raise ValueError."""
    playbook = tmp_path / "playbook.yml"
    playbook.write_text("- [")

    with pytest.raises(ValueError, match="Invalid playbook YAML"):
        scan_playbook_for_version_issues(str(playbook))


def test_scan_playbook_empty_returns_issues(tmp_path: Path) -> None:
    """Empty playbook should return empty issues structure."""
    playbook = tmp_path / "playbook.yml"
    playbook.write_text("")

    result = scan_playbook_for_version_issues(str(playbook))
    assert result["deprecated_modules"] == []
    assert result["legacy_syntax"] == []


def test_scan_playbook_detects_issues(tmp_path: Path) -> None:
    """Playbook scan should detect deprecated modules and legacy syntax."""
    playbook = tmp_path / "playbook.yml"
    playbook.write_text(
        """
- hosts: all
  tasks:
    - name: legacy
      ec2:
        name: legacy
    - name: include legacy
      include: old.yml
    - name: action legacy
      action: command
    - name: fqcn copy
      ansible.builtin.copy:
        src: a
        dest: b
"""
    )

    result = scan_playbook_for_version_issues(str(playbook))

    assert "ec2" in result["deprecated_modules"]
    assert any("include" in item for item in result["legacy_syntax"])
    assert any("action:" in item for item in result["legacy_syntax"])
    assert "ansible" in result["collection_usage"]


def test_parse_config_for_paths_populates_paths(tmp_path: Path) -> None:
    """Config parsing should populate inventory, roles, and collections paths."""
    cfg_path = tmp_path / "ansible.cfg"
    inv_path = tmp_path / "inventory.ini"
    roles_path = tmp_path / "roles"
    collections_path = tmp_path / "collections"
    inv_path.write_text("[all]\nhost")
    roles_path.mkdir()
    collections_path.mkdir()

    cfg_path.write_text(
        f"""
[defaults]
inventory = {inv_path}
roles_path = {roles_path}
collections_paths = {collections_path}
"""
    )

    paths: dict[str, str | None] = {
        "inventory": None,
        "roles_path": None,
        "collections_path": None,
    }

    _parse_config_for_paths(str(cfg_path), paths)

    assert paths["inventory"] == str(inv_path.resolve())
    assert paths["roles_path"] == str(roles_path.resolve())
    assert paths["collections_path"] == str(collections_path.resolve())


def test_parse_config_for_paths_handles_errors(tmp_path: Path) -> None:
    """Invalid config should be ignored without raising."""
    cfg_path = tmp_path / "ansible.cfg"
    cfg_path.write_text("invalid")
    paths: dict[str, str | None] = {
        "inventory": None,
        "roles_path": None,
        "collections_path": None,
    }

    with patch(
        "souschef.parsers.ansible_inventory.parse_ansible_cfg",
        side_effect=ValueError("bad"),
    ):
        _parse_config_for_paths(str(cfg_path), paths)

    assert paths["inventory"] is None
