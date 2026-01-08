"""Chef resource to Ansible task converter."""

import ast
import json
from typing import Any

from souschef.core.constants import ACTION_TO_STATE, RESOURCE_MAPPINGS


def _parse_properties(properties_str: str) -> dict[str, Any]:
    """
    Parse properties string into a dictionary.

    Args:
        properties_str: String representation of properties dict.

    Returns:
        Dictionary of properties.

    """
    if not properties_str:
        return {}
    try:
        # Try ast.literal_eval first for safety
        result = ast.literal_eval(properties_str)
        if isinstance(result, dict):
            return result
        return {}
    except (ValueError, SyntaxError):
        # Fallback to eval if needed, but this is less safe
        try:
            result = eval(properties_str)  # noqa: S307
            if isinstance(result, dict):
                return result
            return {}
        except Exception:
            return {}


def convert_resource_to_task(
    resource_type: str, resource_name: str, action: str = "create", properties: str = ""
) -> str:
    """
    Convert a Chef resource to an Ansible task.

    Args:
        resource_type: The Chef resource type (e.g., 'package', 'service').
        resource_name: The name of the resource.
        action: The Chef action (e.g., 'install', 'start', 'create').
            Defaults to 'create'.
        properties: Additional resource properties as a string representation.

    Returns:
        YAML representation of the equivalent Ansible task.

    """
    try:
        task = _convert_chef_resource_to_ansible(
            resource_type, resource_name, action, properties
        )
        return _format_ansible_task(task)
    except Exception as e:
        return f"An error occurred during conversion: {e}"


def _get_service_params(resource_name: str, action: str) -> dict[str, Any]:
    """
    Get Ansible service module parameters.

    Args:
        resource_name: Service name.
        action: Chef action.

    Returns:
        Dictionary of Ansible service parameters.

    """
    params: dict[str, Any] = {"name": resource_name}
    if action in ["enable", "start"]:
        params["enabled"] = True
        params["state"] = "started"
    elif action in ["disable", "stop"]:
        params["enabled"] = False
        params["state"] = "stopped"
    else:
        params["state"] = ACTION_TO_STATE.get(action, action)
    return params


def _get_file_params(
    resource_name: str, action: str, resource_type: str
) -> dict[str, Any]:
    """
    Get Ansible file module parameters.

    Args:
        resource_name: File/directory path.
        action: Chef action.
        resource_type: Type of file resource (file/directory/template).

    Returns:
        Dictionary of Ansible file parameters.

    """
    params: dict[str, Any] = {}

    if resource_type == "template":
        params["src"] = resource_name
        params["dest"] = resource_name.replace(".erb", "")
        if action == "create":
            params["mode"] = "0644"
    elif resource_type == "file":
        params["path"] = resource_name
        if action == "create":
            params["state"] = "file"
            params["mode"] = "0644"
        else:
            params["state"] = ACTION_TO_STATE.get(action, action)
    elif resource_type == "directory":
        params["path"] = resource_name
        params["state"] = "directory"
        if action == "create":
            params["mode"] = "0755"

    return params


def _convert_chef_resource_to_ansible(
    resource_type: str, resource_name: str, action: str, properties: str
) -> dict[str, Any]:
    """
    Convert Chef resource to Ansible task dictionary.

    Args:
        resource_type: The Chef resource type.
        resource_name: The name of the resource.
        action: The Chef action.
        properties: Additional properties string.

    Returns:
        Dictionary representing an Ansible task.

    """
    # Get Ansible module name
    ansible_module = RESOURCE_MAPPINGS.get(resource_type, f"# Unknown: {resource_type}")

    # Start building the task
    task: dict[str, Any] = {
        "name": f"{action.capitalize()} {resource_type} {resource_name}",
    }

    # Build module parameters based on resource type
    module_params: dict[str, Any] = {}

    # Parse properties if provided
    props = _parse_properties(properties)

    if resource_type == "package":
        module_params["name"] = resource_name
        module_params["state"] = ACTION_TO_STATE.get(action, action)
    elif resource_type in ["service", "systemd_unit"]:
        module_params = _get_service_params(resource_name, action)
    elif resource_type in ["template", "file", "directory"]:
        module_params = _get_file_params(resource_name, action, resource_type)
    elif resource_type in ["execute", "bash"]:
        module_params["cmd"] = resource_name
        task["changed_when"] = "false"
    elif resource_type in ["user", "group"]:
        module_params["name"] = resource_name
        module_params["state"] = ACTION_TO_STATE.get(action, "present")
    elif resource_type == "remote_file":
        module_params["dest"] = resource_name
        if "source" in props:
            module_params["url"] = props["source"]
        if "mode" in props:
            module_params["mode"] = props["mode"]
        if "owner" in props:
            module_params["owner"] = props["owner"]
        if "group" in props:
            module_params["group"] = props["group"]
        if "checksum" in props:
            module_params["checksum"] = props["checksum"]
    else:
        module_params["name"] = resource_name
        if action in ACTION_TO_STATE:
            module_params["state"] = ACTION_TO_STATE[action]

    task[ansible_module] = module_params
    return task


def _format_yaml_value(value: Any) -> str:
    """Format a value for YAML output."""
    if isinstance(value, str):
        return f'"{value}"'
    return json.dumps(value)


def _format_dict_value(key: str, value: dict[str, Any]) -> list[str]:
    """Format a dictionary value for YAML output."""
    lines = [f"  {key}:"]
    for param_key, param_value in value.items():
        lines.append(f"    {param_key}: {_format_yaml_value(param_value)}")
    return lines


def _format_ansible_task(task: dict[str, Any]) -> str:
    """
    Format an Ansible task dictionary as YAML.

    Args:
        task: Dictionary representing an Ansible task.

    Returns:
        YAML-formatted string.

    """
    result = ["- name: " + task["name"]]

    for key, value in task.items():
        if key == "name":
            continue
        if isinstance(value, dict):
            result.extend(_format_dict_value(key, value))
        else:
            result.append(f"  {key}: {_format_yaml_value(value)}")

    return "\n".join(result)
