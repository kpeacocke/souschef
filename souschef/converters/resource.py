"""Chef resource to Ansible task converter."""

import ast
import json
from collections.abc import Callable
from typing import Any

from souschef.core.constants import ACTION_TO_STATE, RESOURCE_MAPPINGS

# Type alias for parameter builder functions
ParamBuilder = Callable[[str, str, dict[str, Any]], dict[str, Any]]


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


def _get_template_file_params(resource_name: str, action: str) -> dict[str, Any]:
    """Get parameters for template resources."""
    params = {
        "src": resource_name,
        "dest": resource_name.replace(".erb", ""),
    }
    if action == "create":
        params["mode"] = "0644"
    return params


def _get_regular_file_params(resource_name: str, action: str) -> dict[str, Any]:
    """Get parameters for regular file resources."""
    params: dict[str, Any] = {"path": resource_name}
    if action == "create":
        params["state"] = "file"
        params["mode"] = "0644"
    else:
        params["state"] = ACTION_TO_STATE.get(action, action)
    return params


def _get_directory_params(resource_name: str, action: str) -> dict[str, Any]:
    """Get parameters for directory resources."""
    params: dict[str, Any] = {
        "path": resource_name,
        "state": "directory",
    }
    if action == "create":
        params["mode"] = "0755"
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
    if resource_type == "template":
        return _get_template_file_params(resource_name, action)
    elif resource_type == "file":
        return _get_regular_file_params(resource_name, action)
    elif resource_type == "directory":
        return _get_directory_params(resource_name, action)
    return {}


def _get_package_params(
    resource_name: str, action: str, props: dict[str, Any]
) -> dict[str, Any]:
    """Build parameters for package resources."""
    return {"name": resource_name, "state": ACTION_TO_STATE.get(action, action)}


def _get_execute_params(
    resource_name: str, action: str, props: dict[str, Any]
) -> dict[str, Any]:
    """Build parameters for execute/bash resources."""
    return {"cmd": resource_name}


def _get_user_group_params(
    resource_name: str, action: str, props: dict[str, Any]
) -> dict[str, Any]:
    """Build parameters for user/group resources."""
    return {"name": resource_name, "state": ACTION_TO_STATE.get(action, "present")}


def _get_remote_file_params(
    resource_name: str, action: str, props: dict[str, Any]
) -> dict[str, Any]:
    """Build parameters for remote_file resources."""
    params = {"dest": resource_name}
    # Map Chef properties to Ansible parameters
    prop_mappings = {
        "source": "url",
        "mode": "mode",
        "owner": "owner",
        "group": "group",
        "checksum": "checksum",
    }
    for chef_prop, ansible_param in prop_mappings.items():
        if chef_prop in props:
            params[ansible_param] = props[chef_prop]
    return params


def _get_default_params(resource_name: str, action: str) -> dict[str, Any]:
    """Build default parameters for unknown resource types."""
    params = {"name": resource_name}
    if action in ACTION_TO_STATE:
        params["state"] = ACTION_TO_STATE[action]
    return params


# Resource type to parameter builder mappings
RESOURCE_PARAM_BUILDERS: dict[str, ParamBuilder | str] = {
    "package": _get_package_params,
    "service": "service",  # Uses _get_service_params
    "systemd_unit": "service",
    "template": "file",  # Uses _get_file_params
    "file": "file",
    "directory": "file",
    "execute": _get_execute_params,
    "bash": _get_execute_params,
    "user": _get_user_group_params,
    "group": _get_user_group_params,
    "remote_file": _get_remote_file_params,
}


def _convert_chef_resource_to_ansible(
    resource_type: str, resource_name: str, action: str, properties: str
) -> dict[str, Any]:
    """
    Convert Chef resource to Ansible task dictionary using data-driven approach.

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

    # Parse properties
    props = _parse_properties(properties)

    # Build module parameters using appropriate builder
    module_params = _build_module_params(resource_type, resource_name, action, props)

    # Add special task-level flags for execute/bash resources
    if resource_type in ["execute", "bash"]:
        task["changed_when"] = "false"

    task[ansible_module] = module_params
    return task


def _build_module_params(
    resource_type: str, resource_name: str, action: str, props: dict[str, Any]
) -> dict[str, Any]:
    """
    Build Ansible module parameters based on resource type.

    Args:
        resource_type: The Chef resource type.
        resource_name: The resource name.
        action: The Chef action.
        props: Parsed properties dictionary.

    Returns:
        Dictionary of Ansible module parameters.

    """
    # Look up the parameter builder for this resource type
    builder = RESOURCE_PARAM_BUILDERS.get(resource_type)

    if builder is None:
        # Unknown resource type - use default builder
        return _get_default_params(resource_name, action)

    if isinstance(builder, str):
        # Special handler reference (service/file)
        if builder == "service":
            return _get_service_params(resource_name, action)
        elif builder == "file":
            return _get_file_params(resource_name, action, resource_type)
        # This shouldn't happen, but handle gracefully
        return _get_default_params(resource_name, action)

    # Call the parameter builder function
    return builder(resource_name, action, props)


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
