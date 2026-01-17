"""Chef attributes file parser."""

import re
from typing import Any

from souschef.core.constants import (
    ATTRIBUTE_PREFIX,
    ERROR_FILE_NOT_FOUND,
    ERROR_IS_DIRECTORY,
    ERROR_PERMISSION_DENIED,
    VALUE_PREFIX,
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


def _extract_precedence_and_path(line: str) -> tuple[str, str, str] | None:
    """Extract precedence and attribute path from a line."""
    precedence_types = (
        "default",
        "force_default",
        "normal",
        "override",
        "force_override",
        "automatic",
    )
    if not (line.startswith(precedence_types) and "[" in line):
        return None

    # Extract precedence
    if line.startswith("default"):
        precedence = "default"
        attr_part = line[7:].strip()
    elif line.startswith("force_default"):
        precedence = "force_default"
        attr_part = line[13:].strip()
    elif line.startswith("normal"):
        precedence = "normal"
        attr_part = line[6:].strip()
    elif line.startswith("override"):
        precedence = "override"
        attr_part = line[8:].strip()
    elif line.startswith("force_override"):
        precedence = "force_override"
        attr_part = line[14:].strip()
    elif line.startswith("automatic"):
        precedence = "automatic"
        attr_part = line[9:].strip()
    else:
        return None

    # Find the attribute path and value
    equals_pos = attr_part.find("=")
    if equals_pos == -1:
        return None

    attr_path_part = attr_part[:equals_pos].strip()
    value_start = attr_part[equals_pos + 1 :].strip()

    # Clean up the path
    attr_path = (
        attr_path_part.replace("']['", ".")
        .replace('"]["', ".")
        .replace("['", "")
        .replace("']", "")
        .replace('["', "")
        .replace('"]', "")
    )

    return precedence, attr_path, value_start


def _is_ruby_array_syntax(value: str) -> bool:
    """Check if value uses Ruby array syntax."""
    stripped = value.strip()
    return stripped.startswith("%w") or (
        stripped.startswith("[") and stripped.endswith("]")
    )


def _should_stop_collecting(stripped: str, precedence_types: tuple[str, ...]) -> bool:
    """Check if we should stop collecting multiline value based on line content."""
    # Stop if we hit another attribute declaration
    if stripped.startswith(precedence_types) and "[" in stripped:
        return True

    # Stop if we hit Ruby control structures that indicate end of attribute
    return stripped.startswith(
        (
            "case ",
            "if ",
            "unless ",
            "when ",
            "else",
            "end",
            "def ",
            "class ",
            "module ",
        )
    )


def _update_string_state(
    char: str,
    in_string: bool,
    string_char: str | None,
    line: str,
    value_lines: list[str],
) -> tuple[bool, str | None]:
    """Update string parsing state for a single character."""
    if not in_string and char in ('"', "'"):
        return True, char
    elif (
        in_string
        and string_char is not None
        and char == string_char
        and (
            not value_lines
            or line[value_lines[-1].rfind(string_char) + 1 :].count("\\") % 2 == 0
        )
    ):
        return False, None
    return in_string, string_char


def _update_bracket_depths(
    char: str,
    brace_depth: int,
    bracket_depth: int,
    paren_depth: int,
) -> tuple[int, int, int]:
    """Update bracket/braces/parentheses depth counters for a single character."""
    if char == "{":
        return brace_depth + 1, bracket_depth, paren_depth
    elif char == "}":
        return brace_depth - 1, bracket_depth, paren_depth
    elif char == "[":
        return brace_depth, bracket_depth + 1, paren_depth
    elif char == "]":
        return brace_depth, bracket_depth - 1, paren_depth
    elif char == "(":
        return brace_depth, bracket_depth, paren_depth + 1
    elif char == ")":
        return brace_depth, bracket_depth, paren_depth - 1
    return brace_depth, bracket_depth, paren_depth


def _update_parsing_state(
    line: str,
    in_string: bool,
    string_char: str | None,
    brace_depth: int,
    bracket_depth: int,
    paren_depth: int,
    value_lines: list[str],
) -> tuple[bool, str | None, int, int, int]:
    """Update parsing state for string literals and bracket/braces depth."""
    for char in line:
        if in_string:
            in_string, string_char = _update_string_state(
                char,
                in_string,
                string_char,
                line,
                value_lines,
            )
        else:
            # Check for entering string
            if char in ('"', "'"):
                in_string, string_char = True, char
            else:
                # Update bracket depths
                brace_depth, bracket_depth, paren_depth = _update_bracket_depths(
                    char, brace_depth, bracket_depth, paren_depth
                )

    return in_string, string_char, brace_depth, bracket_depth, paren_depth


def _is_value_complete(
    in_string: bool,
    brace_depth: int,
    bracket_depth: int,
    paren_depth: int,
    value_lines: list[str],
    line: str,
    next_line: str,
    precedence_types: tuple[str, ...],
) -> bool:
    """Check if the multiline value collection is complete."""
    # Must be outside strings and have balanced brackets/braces
    if in_string or brace_depth > 0 or bracket_depth > 0 or paren_depth > 0:
        return False

    # For arrays like %w(...), check if we have the closing paren
    if value_lines and value_lines[0].strip().startswith("%w"):
        return ")" in line

    # For regular arrays/hashes, break when brackets are balanced
    return (
        brace_depth == 0
        and bracket_depth == 0
        and paren_depth == 0
        and (
            not next_line
            or next_line.startswith(precedence_types)
            or next_line.startswith(("case ", "if ", "unless "))
        )
    )


def _collect_multiline_value(lines: list[str], start_idx: int) -> tuple[str, int]:
    """Collect multiline attribute value."""
    value_lines: list[str] = []
    i = start_idx
    brace_depth = 0
    bracket_depth = 0
    paren_depth = 0
    in_string = False
    string_char = None

    precedence_types = (
        "default",
        "force_default",
        "normal",
        "override",
        "force_override",
        "automatic",
    )

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines at the beginning
        if not value_lines and not stripped:
            i += 1
            continue

        # Check if we should stop collecting
        if _should_stop_collecting(stripped, precedence_types):
            break

        # Update parsing state for strings and brackets
        (
            in_string,
            string_char,
            brace_depth,
            bracket_depth,
            paren_depth,
        ) = _update_parsing_state(
            line,
            in_string,
            string_char,
            brace_depth,
            bracket_depth,
            paren_depth,
            value_lines,
        )

        value_lines.append(line)

        # Check if the value is complete
        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if _is_value_complete(
            in_string,
            brace_depth,
            bracket_depth,
            paren_depth,
            value_lines,
            line,
            next_line,
            precedence_types,
        ):
            break

        i += 1

    return "\n".join(value_lines).strip(), i


def _convert_ruby_word_array(content: str) -> str:
    """Convert Ruby %w(...) array syntax to YAML list."""
    # Extract the array content
    match = re.match(r"%w\s*\((.*?)\)", content, re.DOTALL)
    if not match:
        return content

    array_content = match.group(1)
    # Split on whitespace and newlines, clean up
    items = []
    for item in re.split(r"\s+", array_content):
        item = item.strip()
        if item and not item.startswith("#"):  # Skip comments
            items.append(f"  - {item}")
    return "\n".join(items) if items else "[]"


def _convert_ruby_array(content: str) -> str:
    """Convert Ruby [item1, item2] array syntax to YAML list."""
    # Remove brackets and strip
    array_content = content.strip()[1:-1]
    if not array_content.strip():
        return "[]"

    items = []
    # Split on commas, but be careful with nested structures
    for item in array_content.split(","):
        item = item.strip()
        if item:
            items.append(f"  - {item}")
    return "\n".join(items) if items else "[]"


def _convert_ruby_hash(content: str) -> str:
    """Convert Ruby {key: value} hash syntax to YAML mapping."""
    # Remove braces and strip
    hash_content = content.strip()[1:-1]
    if not hash_content.strip():
        return "{}"

    lines = []
    # Split on commas
    for pair in hash_content.split(","):
        pair = pair.strip()
        if ":" in pair:
            key, val = pair.split(":", 1)
            lines.append(f"  {key.strip()}: {val.strip()}")
    return "\n".join(lines) if lines else "{}"


def _convert_ruby_value_to_yaml(value: str) -> str:
    """
    Convert Ruby value syntax to YAML-compatible format.

    Args:
        value: Raw Ruby value string.

    Returns:
        YAML-compatible value string.

    """
    stripped = value.strip()

    # Handle %w(...) array syntax
    if stripped.startswith("%w"):
        return _convert_ruby_word_array(stripped)

    # Handle regular arrays [item1, item2]
    if stripped.startswith("[") and stripped.endswith("]"):
        return _convert_ruby_array(stripped)

    # Handle hashes {key: value, key2: value2}
    if stripped.startswith("{") and stripped.endswith("}"):
        return _convert_ruby_hash(stripped)

    # Return as-is for other values
    return value


def _extract_attributes(content: str) -> list[dict[str, str]]:  # noqa: C901
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

    # Split content into lines for easier processing
    lines = clean_content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Try to extract precedence and path
        result = _extract_precedence_and_path(line)
        if result is not None:
            precedence, attr_path, value_start = result

            # Check if this is Ruby array syntax
            is_ruby_array = _is_ruby_array_syntax(value_start)

            # Collect the value (may span multiple lines)
            value_lines = [value_start]
            i += 1

            # Continue collecting lines
            full_value, i = _collect_multiline_value(lines, i)

            if full_value:
                value_lines[0] = full_value

            # Join value lines and clean up
            value = "\n".join(value_lines).strip()

            # For Ruby arrays, reconstruct the full syntax for conversion
            if (
                is_ruby_array
                and not value.startswith("%w")
                and (not value.startswith("["))
            ):
                # This was a multiline Ruby array, reconstruct %w syntax
                value = f"%w(\n{value}\n)"

            # Convert Ruby syntax to YAML-compatible format
            value = _convert_ruby_value_to_yaml(value)

            attributes.append(
                {
                    "precedence": precedence,
                    "path": attr_path,
                    "value": value,
                }
            )
        else:
            i += 1

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
        result.append(f"{ATTRIBUTE_PREFIX}{path}")
        result.append(f"  {VALUE_PREFIX}{info['value']}")
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
