"""Chef custom resource parser."""

import json
import re
from typing import Any

from souschef.core.constants import (
    ERROR_FILE_NOT_FOUND,
    ERROR_IS_DIRECTORY,
    ERROR_PERMISSION_DENIED,
)
from souschef.core.path_utils import _normalize_path
from souschef.parsers.template import _strip_ruby_comments


def parse_custom_resource(path: str) -> str:
    """
    Parse a Chef custom resource or LWRP file.

    Args:
        path: Path to the custom resource (.rb) file.

    Returns:
        JSON string with extracted properties, actions, and metadata.

    """
    try:
        file_path = _normalize_path(path)
        content = file_path.read_text(encoding="utf-8")

        # Determine resource type
        resource_type = "custom_resource" if "property" in content else "lwrp"

        # Extract properties/attributes
        properties = _extract_resource_properties(content)

        # Extract actions
        actions_info = _extract_resource_actions(content)

        result = {
            "resource_file": str(file_path),
            "resource_name": file_path.stem,
            "resource_type": resource_type,
            "properties": properties,
            "actions": actions_info["actions"],
            "default_action": actions_info["default_action"],
        }

        return json.dumps(result, indent=2)

    except FileNotFoundError:
        return ERROR_FILE_NOT_FOUND.format(path=path)
    except IsADirectoryError:
        return ERROR_IS_DIRECTORY.format(path=path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=path)
    except UnicodeDecodeError:
        return f"Error: Unable to decode {path} as UTF-8 text"
    except Exception as e:
        return f"An error occurred: {e}"


def _extract_common_property_options(options: str, info: dict[str, Any]) -> None:
    """
    Extract common property options (default, required, name_property).

    Args:
        options: Options string from property/attribute definition.
        info: Dictionary to update with extracted options.

    """
    # Extract name_property / name_attribute
    if "name_property: true" in options or "name_attribute: true" in options:
        info["name_property"] = True

    # Extract default value
    default_match = re.search(r"default:\s*([^,\n]+)", options)
    if default_match:
        info["default"] = default_match.group(1).strip()

    # Extract required
    if "required: true" in options:
        info["required"] = True


def _extract_resource_properties(content: str) -> list[dict[str, Any]]:
    """
    Extract property definitions from custom resource.

    Args:
        content: Raw content of custom resource file.

    Returns:
        List of dictionaries containing property information.

    """
    properties = []
    # Strip comments
    clean_content = _strip_ruby_comments(content)

    # Match modern property syntax: property :name, Type, options
    # Updated to handle multi-line definitions and complex types like [true, false]
    property_pattern = (
        r"property\s+:(\w+),\s*([^,\n\[]+(?:\[[^\]]+\])?),?\s*([^\n]*?)(?:\n|$)"
    )
    for match in re.finditer(property_pattern, clean_content, re.MULTILINE):
        prop_info: dict[str, Any] = {
            "name": match.group(1),
            "type": match.group(2).strip(),
        }
        _extract_common_property_options(match.group(3) or "", prop_info)
        properties.append(prop_info)

    # Match LWRP attribute syntax: attribute :name, kind_of: Type
    attribute_pattern = r"attribute\s+:(\w+)(?:,\s*([^\n]+))?\n?"
    for match in re.finditer(attribute_pattern, content, re.MULTILINE):
        attr_options = match.group(2) or ""
        attr_info: dict[str, Any] = {
            "name": match.group(1),
            "type": "Any",  # Default type
        }

        # Extract type from kind_of
        kind_of_match = re.search(r"kind_of:\s*(\w+)", attr_options)
        if kind_of_match:
            attr_info["type"] = kind_of_match.group(1)

        _extract_common_property_options(attr_options, attr_info)
        properties.append(attr_info)

    return properties


def _extract_resource_actions(content: str) -> dict[str, Any]:
    """
    Extract action definitions from custom resource.

    Args:
        content: Raw content of custom resource file.

    Returns:
        Dictionary with actions list and default action.

    """
    result: dict[str, Any] = {
        "actions": [],
        "default_action": None,
    }

    # Extract modern action blocks: action :name do ... end
    action_pattern = r"action\s+:(\w+)\s+do"
    for match in re.finditer(action_pattern, content):
        action_name = match.group(1)
        if action_name not in result["actions"]:
            result["actions"].append(action_name)

    # Extract LWRP-style actions declaration: actions :create, :drop
    actions_decl = re.search(r"actions\s+([^\n]+)\n?", content)
    if actions_decl:
        action_symbols = re.findall(r":(\w+)", actions_decl.group(1))
        for action in action_symbols:
            if action not in result["actions"]:
                result["actions"].append(action)

    # Extract default action
    default_match = re.search(r"default_action\s+:(\w+)", content)
    if default_match:
        result["default_action"] = default_match.group(1)

    return result
