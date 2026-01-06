"""Chef attributes file parser."""

import re
from typing import Any

from souschef.core.constants import (
    ERROR_FILE_NOT_FOUND,
    ERROR_IS_DIRECTORY,
    ERROR_PERMISSION_DENIED,
)
from souschef.core.path_utils import _normalize_path
from souschef.parsers.template import _strip_ruby_comments


def parse_attributes(path: str, resolve_precedence: bool = True) -> str:
    """
    Parse a Chef attributes file and extract attribute definitions.

    Analyzes attributes file and extracts all attribute definitions with their
    precedence levels and values. By default, resolves precedence conflicts
    to show the winning value for each attribute path.

    Chef attribute precedence (lowest to highest):
    1. default - Normal default value
    2. force_default - Forced default, higher than regular default
    3. normal - Normal attribute set by cookbook
    4. override - Override values
    5. force_override - Forced override, cannot be overridden
    6. automatic - Automatically detected by Ohai (highest precedence)

    Args:
        path: Path to the attributes (.rb) file.
        resolve_precedence: If True (default), resolves precedence conflicts
            and shows only winning values. If False, shows all attributes.

    Returns:
        Formatted string with extracted attributes.

    """
    try:
        file_path = _normalize_path(path)
        content = file_path.read_text(encoding="utf-8")

        attributes = _extract_attributes(content)

        if not attributes:
            return f"Warning: No attributes found in {path}"

        if resolve_precedence:
            resolved = _resolve_attribute_precedence(attributes)
            return _format_resolved_attributes(resolved)
        else:
            return _format_attributes(attributes)

    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return ERROR_FILE_NOT_FOUND.format(path=path)
    except IsADirectoryError:
        return ERROR_IS_DIRECTORY.format(path=path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=path)
    except Exception as e:
        return f"An error occurred: {e}"


def _extract_attributes(content: str) -> list[dict[str, str]]:
    """
    Extract Chef attributes from attributes file content.

    Args:
        content: Raw content of attributes file.

    Returns:
        List of dictionaries containing attribute information.

    """
    attributes = []
    # Strip comments first
    clean_content = _strip_ruby_comments(content)

    # Match attribute declarations with all precedence levels
    # Chef precedence levels (lowest to highest):
    # default < force_default < normal < override < force_override < automatic
    pattern = (
        r"(default|force_default|normal|override|force_override|automatic)"
        r"((?:\[[^\]]+\])+)\s*=\s*([^\n]+)"
    )

    for match in re.finditer(pattern, clean_content, re.DOTALL):
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


def _get_precedence_level(precedence: str) -> int:
    """
    Get numeric precedence level for Chef attribute precedence.

    Chef attribute precedence (lowest to highest):
    1. default
    2. force_default
    3. normal
    4. override
    5. force_override
    6. automatic

    Args:
        precedence: Chef attribute precedence level.

    Returns:
        Numeric precedence level (1-6).

    """
    precedence_map = {
        "default": 1,
        "force_default": 2,
        "normal": 3,
        "override": 4,
        "force_override": 5,
        "automatic": 6,
    }
    return precedence_map.get(precedence, 1)


def _resolve_attribute_precedence(
    attributes: list[dict[str, str]],
) -> dict[str, dict[str, str | bool | int]]:
    """
    Resolve attribute precedence conflicts based on Chef's precedence rules.

    When multiple attributes with the same path exist, the one with
    higher precedence wins. Returns the winning value for each path
    along with precedence information.

    Args:
        attributes: List of attribute dictionaries with precedence, path, and value.

    Returns:
        Dictionary mapping attribute paths to their resolved values and metadata.

    """
    # Group attributes by path
    path_groups: dict[str, list[dict[str, str]]] = {}
    for attr in attributes:
        path = attr["path"]
        if path not in path_groups:
            path_groups[path] = []
        path_groups[path].append(attr)

    # Resolve precedence for each path
    resolved: dict[str, dict[str, Any]] = {}
    for path, attrs in path_groups.items():
        # Find attribute with highest precedence
        winning_attr = max(attrs, key=lambda a: _get_precedence_level(a["precedence"]))

        # Check for conflicts (multiple values at different precedence levels)
        has_conflict = len(attrs) > 1
        conflict_info = []
        if has_conflict:
            # Sort by precedence for conflict reporting
            sorted_attrs = sorted(
                attrs, key=lambda a: _get_precedence_level(a["precedence"])
            )
            conflict_info = [
                f"{a['precedence']}={a['value']}" for a in sorted_attrs[:-1]
            ]

        resolved[path] = {
            "value": winning_attr["value"],
            "precedence": winning_attr["precedence"],
            "precedence_level": _get_precedence_level(winning_attr["precedence"]),
            "has_conflict": has_conflict,
            "overridden_values": ", ".join(conflict_info) if conflict_info else "",
        }

    return resolved


def _format_attributes(attributes: list[dict[str, str]]) -> str:
    """
    Format attributes list as a readable string.

    Args:
        attributes: List of attribute dictionaries.

    Returns:
        Formatted string representation.

    """
    result = []
    for attr in attributes:
        result.append(f"{attr['precedence']}[{attr['path']}] = {attr['value']}")

    return "\n".join(result)


def _format_resolved_attributes(
    resolved: dict[str, dict[str, str | bool | int]],
) -> str:
    """
    Format resolved attributes with precedence information.

    Args:
        resolved: Dictionary mapping attribute paths to resolved values and metadata.

    Returns:
        Formatted string showing resolved attributes with precedence details.

    """
    if not resolved:
        return "No attributes found."

    result = ["Resolved Attributes (with precedence):", "=" * 50, ""]

    # Sort by attribute path for consistent output
    for path in sorted(resolved.keys()):
        info = resolved[path]
        result.append(f"Attribute: {path}")
        result.append(f"  Value: {info['value']}")
        result.append(
            f"  Precedence: {info['precedence']} (level {info['precedence_level']})"
        )

        if info["has_conflict"]:
            result.append(f"  ⚠️  Overridden values: {info['overridden_values']}")

        result.append("")  # Blank line between attributes

    # Add summary
    conflict_count = sum(1 for info in resolved.values() if info["has_conflict"])
    result.append("=" * 50)
    result.append(f"Total attributes: {len(resolved)}")
    if conflict_count > 0:
        result.append(f"Attributes with precedence conflicts: {conflict_count}")

    return "\n".join(result)
