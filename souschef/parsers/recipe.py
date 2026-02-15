"""Chef recipe parser."""

import re
import signal
from contextlib import contextmanager
from typing import Any

from souschef.core.constants import (
    ERROR_FILE_NOT_FOUND,
    ERROR_IS_DIRECTORY,
    ERROR_PERMISSION_DENIED,
)
from souschef.core.path_utils import (
    _ensure_within_base_path,
    _get_workspace_root,
    _normalize_path,
    safe_read_text,
)
from souschef.parsers.template import _strip_ruby_comments

# Maximum length for resource body content in regex matching
# Prevents ReDoS attacks from extremely large resource blocks
MAX_RESOURCE_BODY_LENGTH = 15000

# Maximum length for conditional expressions and branches
MAX_CONDITION_LENGTH = 200

# Maximum length for case statement body content
MAX_CASE_BODY_LENGTH = 2000

# Maximum time in seconds for regex operations (ReDoS protection)
REGEX_TIMEOUT_SECONDS = 5


class RegexTimeoutError(Exception):
    """Raised when regex operation exceeds timeout."""

    pass


@contextmanager
def _regex_timeout(seconds: int = REGEX_TIMEOUT_SECONDS):
    """
    Context manager to impose timeout on regex operations.

    This protects against ReDoS (Regular Expression Denial of Service) attacks
    by limiting how long a regex operation can run.

    Args:
        seconds: Maximum time allowed for regex operation.

    Raises:
        RegexTimeoutError: If regex operation exceeds timeout.

    Note:
        Uses signal.SIGALRM which is Unix-specific. On Windows, timeout is not enforced
        but code will still function (with potential ReDoS vulnerability).

    """

    def _timeout_handler(signum: int, frame: Any) -> None:
        raise RegexTimeoutError("Regex operation exceeded timeout")

    # Only set alarm on Unix-like systems (signal.SIGALRM not available on Windows)
    try:
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    except (AttributeError, ValueError):
        # Windows or signal not available - proceed without timeout
        yield


def _extract_action(resource_body: str) -> str | None:
    """
    Extract action from resource body.

    Args:
        resource_body: The resource block content.

    Returns:
        Action name or None if not found.

    """
    action_match = re.search(r"action\s+:(\w+)", resource_body)
    return action_match.group(1) if action_match else None


def _extract_properties(resource_body: str) -> dict[str, str]:
    """
    Extract common properties from resource body.

    Args:
        resource_body: The resource block content.

    Returns:
        Dictionary of property names and values.

    """
    properties = {}
    for prop_match in re.finditer(r"(\w+)\s+['\"]([^'\"]+)['\"]", resource_body):
        prop_name = prop_match.group(1)
        if prop_name != "action":
            properties[prop_name] = prop_match.group(2)
    return properties


def _build_resource(
    resource_type: str, resource_name: str, resource_body: str
) -> dict[str, str]:
    """
    Build a resource dictionary from extracted components.

    Args:
        resource_type: Type of the resource.
        resource_name: Name of the resource instance.
        resource_body: The resource block content.

    Returns:
        Dictionary with resource type, name, action, and properties.

    """
    resource: dict[str, str] = {
        "type": resource_type,
        "name": resource_name,
    }

    action = _extract_action(resource_body)
    if action:
        resource["action"] = action

    properties = _extract_properties(resource_body)
    if properties:
        resource["properties"] = str(properties)

    return resource


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
        workspace_root = _get_workspace_root()
        safe_path = _ensure_within_base_path(file_path, workspace_root)
        content = safe_read_text(safe_path, workspace_root, encoding="utf-8")

        resources = _extract_resources(content)
        include_recipes = _extract_include_recipes(content)

        # Combine resources and include_recipes
        all_items = resources + include_recipes

        if not all_items:
            return f"Warning: No Chef resources or include_recipe calls found in {path}"

        return _format_resources(all_items)

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

    Uses a manual parser to avoid ReDoS vulnerabilities from regex backtracking
    with nested do...end blocks.

    Args:
        content: Raw content of recipe file.

    Returns:
        List of dictionaries containing resource information.

    """
    resources: list[dict[str, str]] = []
    # Strip comments first
    clean_content = _strip_ruby_comments(content)

    # Check for pathologically large content to prevent ReDoS
    if len(clean_content) > 1_000_000:
        return resources

    try:
        with _regex_timeout():
            # First, find all resource declarations (just the header line)
            # Pattern: resource_type 'name' do OR resource_type('name') do
            header_pattern = r"(\w+)\s+(?:\()?['\"]([^'\"]+)['\"](?:\))?\s+do(?:\s|$)"

            for match in re.finditer(header_pattern, clean_content):
                resource_type = match.group(1)
                resource_name = match.group(2)
                start_pos = match.end()

                # Manually find matching 'end' keyword for this 'do'
                # This avoids regex backtracking issues
                end_pos = _find_matching_end(clean_content, start_pos)
                if end_pos == -1:
                    continue

                resource_body = clean_content[start_pos:end_pos]

                # Skip if body is too large (prevent resource exhaustion)
                if len(resource_body) > MAX_RESOURCE_BODY_LENGTH:
                    continue

                resource = _build_resource(resource_type, resource_name, resource_body)
                resources.append(resource)

    except RegexTimeoutError:
        # Return partial results if timeout occurs
        return resources

    return resources


def _find_matching_end(content: str, start_pos: int) -> int:
    """
    Find the position of the matching 'end' keyword for a 'do' block.

    This manual parser counts nested do...end blocks to find the correct
    closing 'end', avoiding regex backtracking issues.

    Args:
        content: The content to search.
        start_pos: Position after the opening 'do' keyword.

    Returns:
        Position of the matching 'end' keyword, or -1 if not found.

    """
    depth = 1
    pos = start_pos
    max_search = min(len(content), start_pos + MAX_RESOURCE_BODY_LENGTH + 1000)

    # Simple word boundary regex for 'do' and 'end' keywords
    do_pattern = re.compile(r"\bdo\b")
    end_pattern = re.compile(r"\bend\b")

    while pos < max_search and depth > 0:
        # Find next 'do' or 'end' keyword
        do_match = do_pattern.search(content, pos, max_search)
        end_match = end_pattern.search(content, pos, max_search)

        # If no more keywords found, block is incomplete
        if not end_match:
            return -1

        # Check which keyword comes first
        if do_match and do_match.start() < end_match.start():
            # Found nested 'do'
            depth += 1
            pos = do_match.end()
        else:
            # Found 'end'
            depth -= 1
            if depth == 0:
                return end_match.start()
            pos = end_match.end()

    return -1


def _extract_include_recipes(content: str) -> list[dict[str, str]]:
    """
    Extract include_recipe calls from recipe content.

    Args:
        content: Raw content of recipe file.

    Returns:
        List of dictionaries containing include_recipe information.

    """
    include_recipes = []
    # Strip comments first
    clean_content = _strip_ruby_comments(content)

    try:
        with _regex_timeout():
            # Match include_recipe calls: include_recipe 'recipe_name'
            pattern = r"include_recipe\s+['\"]([^'\"]+)['\"]"

            for match in re.finditer(pattern, clean_content):
                recipe_name = match.group(1)
                include_recipes.append(
                    {
                        "type": "include_recipe",
                        "name": recipe_name,
                    }
                )
    except RegexTimeoutError:
        # Return partial results if timeout occurs
        pass

    return include_recipes


def _extract_conditionals(content: str) -> list[dict[str, Any]]:
    """
    Extract Ruby conditionals from recipe code.

    Uses timeout protection and manual parsing for nested blocks to prevent ReDoS.

    Args:
        content: Ruby code content.

    Returns:
        List of dictionaries with conditional information.

    """
    conditionals: list[dict[str, Any]] = []

    # Check for pathologically large content to prevent ReDoS
    if len(content) > 1_000_000:
        return conditionals

    try:
        with _regex_timeout():
            # Match case/when statements with manual block parsing
            # Find case headers first
            case_header_pattern = rf"case\s+([^\n]{{1,{MAX_CONDITION_LENGTH}}})\n"

            for match in re.finditer(case_header_pattern, content):
                case_expr = match.group(1).strip()
                start_pos = match.end()

                # Find matching 'end' for this case block
                end_pos = _find_matching_end(content, start_pos)
                if end_pos == -1:
                    continue

                case_body = content[start_pos:end_pos]

                # Skip if body is too large
                if len(case_body) > MAX_CASE_BODY_LENGTH:
                    continue

                # Extract when clauses from the body
                when_clauses = re.findall(
                    rf"when\s+['\"]?([^'\"\n]{{1,{MAX_CONDITION_LENGTH}}})['\"]?\s*(?:\n|$)",
                    case_body,
                )
                conditionals.append(
                    {
                        "type": "case",
                        "expression": case_expr,
                        "branches": when_clauses,
                    }
                )

            # Match if/elsif/else statements (single line conditions only)
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

    except RegexTimeoutError:
        # Return partial results if timeout occurs
        return conditionals

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
        if resource["type"] == "include_recipe":
            result.append(f"Include Recipe {i}:")
            result.append(f"  Recipe: {resource['name']}")
        else:
            result.append(f"Resource {i}:")
            result.append(f"  Type: {resource['type']}")
            result.append(f"  Name: {resource['name']}")
            if "action" in resource:
                result.append(f"  Action: {resource['action']}")
            if "properties" in resource:
                result.append(f"  Properties: {resource['properties']}")

    return "\n".join(result)
