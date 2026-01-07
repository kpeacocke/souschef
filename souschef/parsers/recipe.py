"""Chef recipe parser."""

import re
from typing import Any

from souschef.core.constants import (
    ERROR_FILE_NOT_FOUND,
    ERROR_IS_DIRECTORY,
    ERROR_PERMISSION_DENIED,
)
from souschef.core.path_utils import _normalize_path
from souschef.parsers.template import _strip_ruby_comments

# Maximum length for resource body content in regex matching
# Prevents ReDoS attacks from extremely large resource blocks
MAX_RESOURCE_BODY_LENGTH = 15000

# Maximum length for conditional expressions and branches
MAX_CONDITION_LENGTH = 200

# Maximum length for case statement body content
MAX_CASE_BODY_LENGTH = 2000


def parse_recipe(path: str) -> str:
    """
    Parse a Chef recipe file and extract resources.

    Args:
        path: Path to the recipe (.rb) file.

    Returns:
        Formatted string with extracted Chef resources and their properties.

    """
    try:
        file_path = _normalize_path(path)
        content = file_path.read_text(encoding="utf-8")

        resources = _extract_resources(content)

        if not resources:
            return f"Warning: No Chef resources found in {path}"

        return _format_resources(resources)

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


def _extract_resources(content: str) -> list[dict[str, str]]:
    """
    Extract Chef resources from recipe content.

    Args:
        content: Raw content of recipe file.

    Returns:
        List of dictionaries containing resource information.

    """
    resources = []
    # Strip comments first
    clean_content = _strip_ruby_comments(content)

    # Match Chef resource declarations with various patterns:
    # 1. Standard: package 'nginx' do ... end
    # 2. With parentheses: package('nginx') do ... end
    # 3. Multi-line strings: package 'nginx' do\n  content <<-EOH\n  ...\n  EOH\nend
    # Use a more robust pattern that avoids matching 'end' keywords within the body
    # Pattern breakdown: match any char that doesn't start spelling 'end' at line start
    # This prevents catastrophic backtracking on large files
    pattern = (
        r"(\w+)\s+(?:\()?['\"]([^'\"]+)['\"](?:\))?\s+do"
        rf"((?:[^e]|e(?:[^n]|n(?:[^d]|\d))|(?!^)e(?:n(?:d))){{0,{MAX_RESOURCE_BODY_LENGTH}}}?)"
        r"^end"
    )

    for match in re.finditer(pattern, clean_content, re.DOTALL | re.MULTILINE):
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


def _extract_conditionals(content: str) -> list[dict[str, Any]]:
    """
    Extract Ruby conditionals from recipe code.

    Args:
        content: Ruby code content.

    Returns:
        List of dictionaries with conditional information.

    """
    conditionals = []

    # Match case/when statements
    # Use explicit non-'end' matching to avoid ReDoS
    case_pattern = (
        rf"case\s+([^\n]{{1,{MAX_CONDITION_LENGTH}}})\n"
        rf"([^e]|e[^n]|en[^d]){{0,{MAX_CASE_BODY_LENGTH}}}^end"
    )
    for match in re.finditer(case_pattern, content, re.DOTALL | re.MULTILINE):
        case_expr = match.group(1).strip()
        case_body = match.group(2)
        when_clauses = re.findall(
            rf"when\s+['\"]?([^'\"\n]{{1,{MAX_CONDITION_LENGTH}}})['\"]?\s*\n",
            case_body,
        )
        conditionals.append(
            {
                "type": "case",
                "expression": case_expr,
                "branches": when_clauses,
            }
        )

    # Match if/elsif/else statements
    if_pattern = r"if\s+([^\n]+)\n?"
    for match in re.finditer(if_pattern, content):
        condition = match.group(1).strip()
        if condition and not condition.startswith(("elsif", "end")):
            conditionals.append(
                {
                    "type": "if",
                    "condition": condition,
                }
            )

    # Match unless statements
    unless_pattern = r"unless\s+([^\n]+)\n?"
    for match in re.finditer(unless_pattern, content):
        condition = match.group(1).strip()
        conditionals.append(
            {
                "type": "unless",
                "condition": condition,
            }
        )

    return conditionals


def _format_resources(resources: list[dict[str, Any]]) -> str:
    """
    Format resources list as a readable string.

    Args:
        resources: List of resource dictionaries.

    Returns:
        Formatted string representation.

    """
    result = []
    for i, resource in enumerate(resources, 1):
        if i > 1:
            result.append("")
        result.append(f"Resource {i}:")
        result.append(f"  Type: {resource['type']}")
        result.append(f"  Name: {resource['name']}")
        if "action" in resource:
            result.append(f"  Action: {resource['action']}")
        if "properties" in resource:
            result.append(f"  Properties: {resource['properties']}")

    return "\n".join(result)
