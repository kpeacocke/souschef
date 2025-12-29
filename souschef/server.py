"""SousChef MCP Server - Chef to Ansible conversion assistant."""

import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Create a new FastMCP server
mcp = FastMCP("souschef")

# Chef resource to Ansible module mappings
RESOURCE_MAPPINGS = {
    "package": "ansible.builtin.package",
    "apt_package": "ansible.builtin.apt",
    "yum_package": "ansible.builtin.yum",
    "service": "ansible.builtin.service",
    "systemd_unit": "ansible.builtin.systemd",
    "template": "ansible.builtin.template",
    "file": "ansible.builtin.file",
    "directory": "ansible.builtin.file",
    "execute": "ansible.builtin.command",
    "bash": "ansible.builtin.shell",
    "script": "ansible.builtin.script",
    "user": "ansible.builtin.user",
    "group": "ansible.builtin.group",
    "cron": "ansible.builtin.cron",
    "mount": "ansible.builtin.mount",
    "git": "ansible.builtin.git",
}

# Chef action to Ansible state mappings
ACTION_TO_STATE = {
    "create": "present",
    "delete": "absent",
    "remove": "absent",
    "install": "present",
    "upgrade": "latest",
    "purge": "absent",
    "enable": "started",
    "disable": "stopped",
    "start": "started",
    "stop": "stopped",
    "restart": "restarted",
    "reload": "reloaded",
}


@mcp.tool()
def list_directory(path: str) -> list[str] | str:
    """List the contents of a directory.

    Args:
        path: The path to the directory to list.

    Returns:
        A list of filenames in the directory, or an error message.

    """
    try:
        dir_path = Path(path)
        return [item.name for item in dir_path.iterdir()]
    except FileNotFoundError:
        return f"Error: Directory not found at {path}"
    except NotADirectoryError:
        return f"Error: {path} is not a directory"
    except PermissionError:
        return f"Error: Permission denied for {path}"
    except Exception as e:
        return f"An error occurred: {e}"


@mcp.tool()
def read_file(path: str) -> str:
    """Read the contents of a file.

    Args:
        path: The path to the file to read.

    Returns:
        The contents of the file, or an error message.

    """
    try:
        file_path = Path(path)
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: File not found at {path}"
    except IsADirectoryError:
        return f"Error: {path} is a directory, not a file"
    except PermissionError:
        return f"Error: Permission denied for {path}"
    except UnicodeDecodeError:
        return f"Error: Unable to decode {path} as UTF-8 text"
    except Exception as e:
        return f"An error occurred: {e}"


@mcp.tool()
def read_cookbook_metadata(path: str) -> str:
    """Parse Chef cookbook metadata.rb file.

    Args:
        path: Path to the metadata.rb file.

    Returns:
        Formatted string with extracted metadata.

    """
    try:
        file_path = Path(path)
        content = file_path.read_text(encoding="utf-8")

        metadata = _extract_metadata(content)

        if not metadata:
            return f"Warning: No metadata found in {path}"

        return _format_metadata(metadata)

    except FileNotFoundError:
        return f"Error: File not found at {path}"
    except IsADirectoryError:
        return f"Error: {path} is a directory, not a file"
    except PermissionError:
        return f"Error: Permission denied for {path}"
    except UnicodeDecodeError:
        return f"Error: Unable to decode {path} as UTF-8 text"
    except Exception as e:
        return f"An error occurred: {e}"


def _extract_metadata(content: str) -> dict[str, str | list[str]]:
    """Extract metadata fields from cookbook content.

    Args:
        content: Raw content of metadata.rb file.

    Returns:
        Dictionary of extracted metadata fields.

    """
    metadata: dict[str, str | list[str]] = {}
    patterns = {
        "name": r"name\s+['\"]([^'\"]+)['\"]",
        "maintainer": r"maintainer\s+['\"]([^'\"]+)['\"]",
        "version": r"version\s+['\"]([^'\"]+)['\"]",
        "description": r"description\s+['\"]([^'\"]+)['\"]",
        "license": r"license\s+['\"]([^'\"]+)['\"]",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            metadata[key] = match.group(1)

    depends = re.findall(r"depends\s+['\"]([^'\"]+)['\"]", content)
    if depends:
        metadata["depends"] = depends

    supports = re.findall(r"supports\s+['\"]([^'\"]+)['\"]", content)
    if supports:
        metadata["supports"] = supports

    return metadata


def _format_metadata(metadata: dict[str, str | list[str]]) -> str:
    """Format metadata dictionary as a readable string.

    Args:
        metadata: Dictionary of metadata fields.

    Returns:
        Formatted string representation.

    """
    result = []
    for key, value in metadata.items():
        if isinstance(value, list):
            result.append(f"{key}: {', '.join(value)}")
        else:
            result.append(f"{key}: {value}")

    return "\n".join(result)


@mcp.tool()
def parse_recipe(path: str) -> str:
    """Parse a Chef recipe file and extract resources.

    Args:
        path: Path to the recipe (.rb) file.

    Returns:
        Formatted string with extracted Chef resources and their properties.

    """
    try:
        file_path = Path(path)
        content = file_path.read_text(encoding="utf-8")

        resources = _extract_resources(content)

        if not resources:
            return f"Warning: No Chef resources found in {path}"

        return _format_resources(resources)

    except FileNotFoundError:
        return f"Error: File not found at {path}"
    except IsADirectoryError:
        return f"Error: {path} is a directory, not a file"
    except PermissionError:
        return f"Error: Permission denied for {path}"
    except UnicodeDecodeError:
        return f"Error: Unable to decode {path} as UTF-8 text"
    except Exception as e:
        return f"An error occurred: {e}"


def _extract_resources(content: str) -> list[dict[str, str]]:
    """Extract Chef resources from recipe content.

    Args:
        content: Raw content of recipe file.

    Returns:
        List of dictionaries containing resource information.

    """
    resources = []
    # Match Chef resource declarations like: package 'nginx' do ... end
    pattern = r"(\w+)\s+['\"]([^'\"]+)['\"]\s+do(.*?)end"

    for match in re.finditer(pattern, content, re.DOTALL):
        resource_type = match.group(1)
        resource_name = match.group(2)
        resource_body = match.group(3)

        resource = {
            "type": resource_type,
            "name": resource_name,
        }

        # Extract action
        action_match = re.search(r"action\s+:(\w+)", resource_body)
        if action_match:
            resource["action"] = action_match.group(1)

        # Extract common properties
        properties = {}
        for prop_match in re.finditer(r"(\w+)\s+['\"]([^'\"]+)['\"]", resource_body):
            prop_name = prop_match.group(1)
            if prop_name not in ["action"]:
                properties[prop_name] = prop_match.group(2)

        if properties:
            resource["properties"] = str(properties)

        resources.append(resource)

    return resources


def _format_resources(resources: list[dict[str, str]]) -> str:
    """Format resources list as a readable string.

    Args:
        resources: List of resource dictionaries.

    Returns:
        Formatted string representation.

    """
    result = []
    for i, resource in enumerate(resources, 1):
        result.append(f"Resource {i}:")
        result.append(f"  Type: {resource['type']}")
        result.append(f"  Name: {resource['name']}")
        if "action" in resource:
            result.append(f"  Action: {resource['action']}")
        if "properties" in resource:
            result.append(f"  Properties: {resource['properties']}")
        result.append("")

    return "\n".join(result).rstrip()


@mcp.tool()
def parse_attributes(path: str) -> str:
    """Parse a Chef attributes file and extract attribute definitions.

    Args:
        path: Path to the attributes (.rb) file.

    Returns:
        Formatted string with extracted attributes.

    """
    try:
        file_path = Path(path)
        content = file_path.read_text(encoding="utf-8")

        attributes = _extract_attributes(content)

        if not attributes:
            return f"Warning: No attributes found in {path}"

        return _format_attributes(attributes)

    except FileNotFoundError:
        return f"Error: File not found at {path}"
    except IsADirectoryError:
        return f"Error: {path} is a directory, not a file"
    except PermissionError:
        return f"Error: Permission denied for {path}"
    except UnicodeDecodeError:
        return f"Error: Unable to decode {path} as UTF-8 text"
    except Exception as e:
        return f"An error occurred: {e}"


def _extract_attributes(content: str) -> list[dict[str, str]]:
    """Extract Chef attributes from attributes file content.

    Args:
        content: Raw content of attributes file.

    Returns:
        List of dictionaries containing attribute information.

    """
    attributes = []
    # Match attribute declarations like: default['nginx']['port'] = 80
    # Use non-capturing group (?:...) with + to match one or more brackets
    pattern = r"(default|override|normal)((?:\[[^\]]+\])+)\s*=\s*(.+?)(?:\n|$)"

    for match in re.finditer(pattern, content):
        precedence = match.group(1)
        # Extract the bracket part and clean it up
        brackets = match.group(2)
        # Clean up the path - remove quotes and brackets, convert to dot notation
        attr_path = (
            brackets.replace("']['", ".")
            .replace('"]["', ".")
            .replace("['", "")
            .replace("']", "")
            .replace('["', "")
            .replace('"]', "")
        )
        value = match.group(3).strip()

        attributes.append(
            {
                "precedence": precedence,
                "path": attr_path,
                "value": value,
            }
        )

    return attributes


def _format_attributes(attributes: list[dict[str, str]]) -> str:
    """Format attributes list as a readable string.

    Args:
        attributes: List of attribute dictionaries.

    Returns:
        Formatted string representation.

    """
    result = []
    for attr in attributes:
        result.append(f"{attr['precedence']}[{attr['path']}] = {attr['value']}")

    return "\n".join(result)


@mcp.tool()
def list_cookbook_structure(path: str) -> str:
    """List the structure of a Chef cookbook directory.

    Args:
        path: Path to the cookbook root directory.

    Returns:
        Formatted string showing the cookbook structure.

    """
    try:
        cookbook_path = Path(path)

        if not cookbook_path.is_dir():
            return f"Error: {path} is not a directory"

        structure = {}
        common_dirs = [
            "recipes",
            "attributes",
            "templates",
            "files",
            "resources",
            "providers",
            "libraries",
            "definitions",
        ]

        for dir_name in common_dirs:
            dir_path = cookbook_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                files = [f.name for f in dir_path.iterdir() if f.is_file()]
                if files:
                    structure[dir_name] = files

        # Check for metadata.rb
        metadata_path = cookbook_path / "metadata.rb"
        if metadata_path.exists():
            structure["metadata"] = ["metadata.rb"]

        if not structure:
            return f"Warning: No standard cookbook structure found in {path}"

        return _format_cookbook_structure(structure)

    except PermissionError:
        return f"Error: Permission denied for {path}"
    except Exception as e:
        return f"An error occurred: {e}"


def _format_cookbook_structure(structure: dict[str, list[str]]) -> str:
    """Format cookbook structure as a readable string.

    Args:
        structure: Dictionary mapping directory names to file lists.

    Returns:
        Formatted string representation.

    """
    result = []
    for dir_name, files in structure.items():
        result.append(f"{dir_name}/")
        for file_name in sorted(files):
            result.append(f"  {file_name}")
        result.append("")

    return "\n".join(result).rstrip()


@mcp.tool()
def convert_resource_to_task(
    resource_type: str, resource_name: str, action: str = "create", properties: str = ""
) -> str:
    """Convert a Chef resource to an Ansible task.

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
    """Get Ansible service module parameters.

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
    """Get Ansible file module parameters.

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
    """Convert Chef resource to Ansible task dictionary.

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
    else:
        module_params["name"] = resource_name
        if action in ACTION_TO_STATE:
            module_params["state"] = ACTION_TO_STATE[action]

    task[ansible_module] = module_params
    return task


def _format_ansible_task(task: dict[str, Any]) -> str:
    """Format an Ansible task dictionary as YAML.

    Args:
        task: Dictionary representing an Ansible task.

    Returns:
        YAML-formatted string.

    """
    import json

    # Simple YAML formatting (basic implementation)
    result = []
    result.append("- name: " + task["name"])

    for key, value in task.items():
        if key == "name":
            continue

        if isinstance(value, dict):
            result.append(f"  {key}:")
            for param_key, param_value in value.items():
                if isinstance(param_value, str):
                    result.append(f'    {param_key}: "{param_value}"')
                else:
                    result.append(f"    {param_key}: {json.dumps(param_value)}")
        else:
            if isinstance(value, str):
                result.append(f'  {key}: "{value}"')
            else:
                result.append(f"  {key}: {json.dumps(value)}")

    return "\n".join(result)


def main() -> None:
    """Run the SousChef MCP server.

    This is the main entry point for running the server.
    """
    mcp.run()


if __name__ == "__main__":
    main()
