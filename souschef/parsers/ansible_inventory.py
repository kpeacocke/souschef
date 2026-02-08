"""
Parse Ansible inventory and configuration files.

This module provides utilities for parsing Ansible configurations, inventory
files, requirements, and detecting installed Ansible versions from
environments.
"""

import configparser
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml


def parse_ansible_cfg(config_path: str) -> dict[str, Any]:
    """
    Parse ansible.cfg configuration file.

    Args:
        config_path: Path to ansible.cfg file.

    Returns:
        Dictionary with configuration sections and values.

    Raises:
        FileNotFoundError: If config file does not exist.
        ValueError: If config file is invalid or path is not a file.

    """
    # Validate and resolve path to prevent path traversal
    path = Path(config_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Config path is not a file: {path}")

    config = configparser.ConfigParser()
    try:
        config.read(str(path))
    except configparser.Error as e:
        raise ValueError(f"Invalid ansible.cfg format: {e}") from e

    result: dict[str, dict[str, str]] = {}
    for section in config.sections():
        result[section] = dict(config.items(section))

    return result


def _parse_group_header(
    line: str, inventory: dict[str, Any]
) -> tuple[str, str | None] | None:
    """Parse INI group header and return (group_name, group_type)."""
    if not (line.startswith("[") and line.endswith("]")):
        return None

    group_match = re.match(r"\[([^\]:]+)(?::(\w+))?\]", line)
    if not group_match:
        return None

    group_name = group_match.group(1)
    group_type = group_match.group(2)

    if group_name not in inventory["groups"]:
        inventory["groups"][group_name] = {
            "hosts": [],
            "children": [],
            "vars": {},
        }

    return (group_name, group_type)


def _parse_group_var(line: str, group_name: str, inventory: dict[str, Any]) -> None:
    """Parse group variable assignment."""
    if "=" in line:
        key, value = line.split("=", 1)
        inventory["groups"][group_name]["vars"][key.strip()] = value.strip()


def _parse_child_group(line: str, group_name: str, inventory: dict[str, Any]) -> None:
    """Parse child group reference."""
    inventory["groups"][group_name]["children"].append(line)


def _parse_host_entry(line: str, group_name: str, inventory: dict[str, Any]) -> None:
    """Parse host entry with variables."""
    parts = line.split(None, 1)
    hostname = parts[0]
    host_vars: dict[str, str] = {}

    if len(parts) > 1:
        var_str = parts[1]
        for var in re.findall(r"(\w+)=([^\s]+)", var_str):
            host_vars[var[0]] = var[1]

    inventory["groups"][group_name]["hosts"].append(hostname)

    if hostname not in inventory["hosts"]:
        inventory["hosts"][hostname] = {"vars": {}}

    inventory["hosts"][hostname]["vars"].update(host_vars)


def parse_inventory_ini(inventory_path: str) -> dict[str, Any]:
    """
    Parse INI-format Ansible inventory file.

    Args:
        inventory_path: Path to inventory file.

    Returns:
        Dictionary with groups, hosts, and variables.

    Raises:
        FileNotFoundError: If inventory file does not exist.
        ValueError: If path is not a file.

    """
    # Validate and resolve path to prevent path traversal
    path = Path(inventory_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Inventory file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Inventory path is not a file: {path}")

    inventory: dict[str, Any] = {"groups": {}, "hosts": {}}
    current_group: tuple[str, str | None] | None = None

    with path.open() as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#") or line.startswith(";"):
                continue

            header = _parse_group_header(line, inventory)
            if header:
                current_group = header
                continue

            if current_group:
                group_name, group_type = current_group

                if group_type == "vars":
                    _parse_group_var(line, group_name, inventory)
                elif group_type == "children":
                    _parse_child_group(line, group_name, inventory)
                else:
                    _parse_host_entry(line, group_name, inventory)

    return inventory


def parse_inventory_yaml(inventory_path: str) -> dict[str, Any]:
    """
    Parse YAML-format Ansible inventory file.

    Args:
        inventory_path: Path to inventory YAML file.

    Returns:
        Dictionary with inventory structure.

    Raises:
        FileNotFoundError: If inventory file does not exist.
        ValueError: If YAML is invalid or path is not a file.

    """
    # Validate and resolve path to prevent path traversal
    path = Path(inventory_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Inventory file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Inventory path is not a file: {path}")

    try:
        with path.open() as f:
            inventory = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid inventory YAML: {e}") from e

    if inventory is None:
        return {}

    # Type assertion: yaml.safe_load returns Any, but we expect dict
    if not isinstance(inventory, dict):
        raise ValueError(
            f"Invalid inventory structure: expected dict, "
            f"got {type(inventory).__name__}"
        )

    return inventory


def parse_inventory_file(inventory_path: str) -> dict[str, Any]:
    """
    Parse Ansible inventory file (auto-detect format).

    Supports both INI and YAML formats.

    Args:
        inventory_path: Path to inventory file.

    Returns:
        Dictionary with inventory structure.

    Raises:
        FileNotFoundError: If inventory file does not exist.
        ValueError: If file format cannot be determined or path is not a file.

    """
    # Validate and resolve path to prevent path traversal
    path = Path(inventory_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Inventory file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Inventory path is not a file: {path}")

    suffix = path.suffix.lower()

    # Pass resolved path as string to sub-parsers
    resolved_str = str(path)
    if suffix in [".yml", ".yaml"]:
        return parse_inventory_yaml(resolved_str)
    if suffix in [".ini", ""]:
        try:
            return parse_inventory_ini(resolved_str)
        except (ValueError, configparser.Error):
            try:
                return parse_inventory_yaml(resolved_str)
            except (ValueError, yaml.YAMLError):
                raise ValueError(
                    f"Could not parse {inventory_path} as INI or YAML"
                ) from None

    raise ValueError(f"Unknown inventory file format: {suffix}")


def detect_ansible_version(ansible_path: str | None = None) -> str:
    """
    Detect installed Ansible version from environment.

    Args:
        ansible_path: Path to ansible executable, or None to use PATH.

    Returns:
        Ansible version string (e.g., "2.16.0").

    Raises:
        ValueError: If ansible_path is invalid or not an executable file.
        FileNotFoundError: If ansible executable not found.
        RuntimeError: If version cannot be determined.

    """
    # Validate ansible_path if provided
    if ansible_path:
        ansible_exec = Path(ansible_path).resolve()
        if not ansible_exec.exists():
            raise ValueError(f"Ansible executable does not exist: {ansible_exec}")
        if not ansible_exec.is_file():
            raise ValueError(f"Ansible path is not a file: {ansible_exec}")
        command = [str(ansible_exec), "--version"]
    else:
        command = ["ansible", "--version"]

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, timeout=10
        )
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Ansible executable not found: {ansible_path or 'ansible'}"
        ) from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("Ansible version check timed out") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ansible version check failed: {e.stderr}") from e

    output = result.stdout

    match = re.search(r"ansible \[core ([\d.]+)\]", output)
    if match:
        return match.group(1)

    match = re.search(r"ansible ([\d.]+)", output)
    if match:
        return match.group(1)

    raise RuntimeError(f"Could not parse Ansible version from: {output}")


def _parse_collections(requirements: dict[str, Any]) -> dict[str, str]:
    """Parse collections section from requirements.yml."""
    result: dict[str, str] = {}

    for item in requirements.get("collections", []):
        if isinstance(item, dict):
            name = item.get("name", "")
            version = item.get("version", "*")
            if name:
                result[name] = version
        elif isinstance(item, str):
            result[item] = "*"

    return result


def _parse_roles(requirements: dict[str, Any]) -> dict[str, str]:
    """Parse roles section from requirements.yml."""
    result: dict[str, str] = {}

    for item in requirements.get("roles", []):
        if isinstance(item, dict):
            name = item.get("name", "") or item.get("src", "")
            version = item.get("version", "*")
            if name:
                result[name] = version
        elif isinstance(item, str):
            result[item] = "*"

    return result


def parse_requirements_yml(requirements_path: str) -> dict[str, str]:
    """
    Parse Ansible Galaxy requirements.yml file.

    Args:
        requirements_path: Path to requirements.yml.

    Returns:
        Dictionary mapping collection/role names to version specifiers.

    Raises:
        FileNotFoundError: If requirements file does not exist.
        ValueError: If requirements_path is not a file or YAML is invalid.

    """
    path = Path(requirements_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Requirements file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Requirements path is not a file: {path}")

    try:
        with path.open() as f:
            requirements = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid requirements YAML: {e}") from e

    if not requirements:
        return {}

    if not isinstance(requirements, dict):
        raise ValueError(
            f"Invalid requirements format: expected dict, "
            f"got {type(requirements).__name__}"
        )

    result: dict[str, str] = {}
    result.update(_parse_collections(requirements))
    result.update(_parse_roles(requirements))

    return result


def _validate_playbook_path(playbook_path: str) -> Path:
    """
    Validate and resolve playbook path.

    Args:
        playbook_path: Path to playbook file.

    Returns:
        Resolved Path object.

    Raises:
        FileNotFoundError: If playbook does not exist.
        ValueError: If path is not a file.

    """
    path = Path(playbook_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Playbook not found: {path}")
    if not path.is_file():
        raise ValueError(f"Playbook path is not a file: {path}")
    return path


def scan_playbook_for_version_issues(playbook_path: str) -> dict[str, Any]:
    """
    Scan playbook for version-specific syntax issues.

    Detects deprecated syntax, module usage, and compatibility issues.

    Args:
        playbook_path: Path to playbook YAML file.

    Returns:
        Dictionary with detected issues.

    Raises:
        FileNotFoundError: If playbook does not exist.
        ValueError: If YAML is invalid or path is not a file.

    """
    # Validate and resolve path to prevent path traversal
    path = _validate_playbook_path(playbook_path)

    try:
        with path.open() as f:
            content = f.read()
            playbook = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid playbook YAML: {e}") from e

    issues: dict[str, Any] = {
        "deprecated_modules": [],
        "legacy_syntax": [],
        "collection_usage": set(),
        "warnings": [],
    }

    if not playbook:
        return issues

    deprecated_modules = {
        "ec2",
        "ec2_ami",
        "ec2_instance",
        "gce",
        "azure_rm",
        "docker",
        "docker_container",
        "docker_image",
    }

    module_pattern = re.compile(r"^\s*(\w+(?:\.\w+)*):.*$", re.MULTILINE)
    for match in module_pattern.finditer(content):
        module_name = match.group(1)

        if module_name in deprecated_modules:
            issues["deprecated_modules"].append(module_name)
            issues["warnings"].append(
                f"Module '{module_name}' should use collection namespace"
            )

        if "." in module_name:
            namespace = module_name.split(".")[0]
            issues["collection_usage"].add(namespace)

    if re.search(r"^\s*include:\s", content, re.MULTILINE):
        issues["legacy_syntax"].append("include (use include_tasks/import_tasks)")
        issues["warnings"].append(
            "Legacy 'include:' syntax found. Use include_tasks or import_tasks."
        )

    action_pattern = re.compile(r"action:\s*(\w+)", re.MULTILINE)
    for match in action_pattern.finditer(content):
        action = match.group(1)
        if "." not in action:
            issues["legacy_syntax"].append(f"action: {action} (missing namespace)")

    issues["collection_usage"] = list(issues["collection_usage"])

    return issues


def _find_ansible_cfg() -> str | None:
    """Find ansible.cfg in standard locations."""
    ansible_cfg_locations = [
        Path.cwd() / "ansible.cfg",
        Path.home() / ".ansible.cfg",
        Path("/etc/ansible/ansible.cfg"),
    ]

    for location in ansible_cfg_locations:
        if location.exists():
            return str(location)

    return None


def _parse_config_for_paths(ansible_cfg: str, paths: dict[str, str | None]) -> None:
    """Parse ansible.cfg to find inventory and paths."""
    try:
        config = parse_ansible_cfg(ansible_cfg)
        defaults = config.get("defaults", {})

        if "inventory" in defaults:
            inv_path = Path(defaults["inventory"])
            if inv_path.exists():
                paths["inventory"] = str(inv_path)

        if "roles_path" in defaults:
            paths["roles_path"] = defaults["roles_path"]

        if "collections_paths" in defaults:
            paths["collections_path"] = defaults["collections_paths"]

    except (ValueError, FileNotFoundError):
        return


def get_ansible_config_paths() -> dict[str, str | None]:
    """
    Get standard Ansible configuration file paths.

    Returns:
        Dictionary with configuration file locations.

    """
    paths: dict[str, str | None] = {
        "ansible_cfg": None,
        "inventory": None,
        "roles_path": None,
        "collections_path": None,
    }

    paths["ansible_cfg"] = _find_ansible_cfg()

    if paths["ansible_cfg"]:
        _parse_config_for_paths(paths["ansible_cfg"], paths)

    if not paths["inventory"]:
        default_inventory = Path("/etc/ansible/hosts")
        if default_inventory.exists():
            paths["inventory"] = str(default_inventory)

    return paths
