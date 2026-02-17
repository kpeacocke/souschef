"""Advanced Chef resource conversion with guards, searches, and notifications."""

import re
from typing import Any


def parse_resource_guards(resource_body: str) -> dict[str, Any]:
    """
    Extract Chef resource guards (only_if, not_if, ignore_failure).

    Guards control when a resource is executed. These map to Ansible conditionals.

    Args:
        resource_body: The resource block content.

    Returns:
        Dictionary with guard type and condition.

    """
    guards: dict[str, Any] = {}

    # Match only_if 'command' or only_if { ... }
    only_if_match = re.search(r"only_if\s+['\"](.+?)['\"]", resource_body)
    if only_if_match:
        guards["only_if"] = only_if_match.group(1)

    # Match not_if 'command' or not_if { ... }
    not_if_match = re.search(r"not_if\s+['\"](.+?)['\"]", resource_body)
    if not_if_match:
        guards["not_if"] = not_if_match.group(1)

    # Match ignore_failure
    if "ignore_failure true" in resource_body:
        guards["ignore_failure"] = True

    return guards


def parse_resource_notifications(resource_body: str) -> list[dict[str, str]]:
    """
    Extract Chef resource notifications (notifies, subscribes).

    Maps to Ansible handlers for unified notification handling.

    Args:
        resource_body: The resource block content.

    Returns:
        List of notification dictionaries with action, resource, and timing.

    """
    notifications: list[dict[str, str]] = []

    # Match notifies :action, 'resource[name]', :immediately/:delayed
    notifies_pattern = r"notifies\s+:(\w+),\s+['\"]([^[]+)\[([^\]]+)\]['\"],\s*:(\w+)"
    for match in re.finditer(notifies_pattern, resource_body):
        notifications.append(
            {
                "type": "notifies",
                "action": match.group(1),
                "resource_type": match.group(2),
                "resource_name": match.group(3),
                "timing": match.group(4),  # immediately, delayed
            }
        )

    # Match subscribes :action, 'resource[name]'
    subscribes_pattern = r"subscribes\s+:(\w+),\s+['\"]([^[]+)\[([^\]]+)\]['\"]"
    for match in re.finditer(subscribes_pattern, resource_body):
        notifications.append(
            {
                "type": "subscribes",
                "action": match.group(1),
                "resource_type": match.group(2),
                "resource_name": match.group(3),
            }
        )

    return notifications


def convert_guard_to_ansible_when(guard_type: str, condition: str) -> str:
    """
    Convert Chef guard to Ansible when clause.

    Args:
        guard_type: 'only_if' or 'not_if'.
        condition: The guard condition string.

    Returns:
        Ansible when clause expression.

    """
    if guard_type == "only_if":
        # Chef: only_if "test -f /tmp/file"
        # Ansible: when: command_result.rc == 0
        return "command_result.rc == 0"
    elif guard_type == "not_if":
        # Chef: not_if "test -f /tmp/file"
        # Ansible: when: command_result.rc != 0
        return "command_result.rc != 0"
    return ""


def parse_resource_search(resource_body: str) -> dict[str, Any]:
    """
    Extract Chef search patterns from recipes.

    Searches are used to query nodes. These map to Ansible inventory queries.

    Args:
        resource_body: The resource block content.

    Returns:
        Dictionary with search index, query, and result handling.

    """
    search_info: dict[str, Any] = {}

    # Match search(:index, 'query_string')
    search_pattern = r"search\s*\(\s*:(\w+),\s+['\"](.+?)['\"]"
    match = re.search(search_pattern, resource_body)
    if match:
        search_info = {
            "index": match.group(1),  # node, role, etc.
            "query": match.group(2),
            "recommended_conversion": (
                "Use ansible.builtin.add_host or inventory_hostname_short "
                "with conditional filtering"
            ),
        }

    return search_info


def generate_advanced_handler_yaml(notifications: list[dict[str, str]]) -> str:
    """
    Generate Ansible handler YAML from Chef notifications.

    Maps Chef's notifies/subscribes to Ansible handlers block.

    Args:
        notifications: List of notification dictionaries.

    Returns:
        YAML representation of Ansible handler block.

    """
    if not notifications:
        return ""

    handlers_yaml = "# Handlers (converted from Chef notifications)\nhandlers:\n"

    for notif in notifications:
        action = notif.get("action", "run")
        resource_name = notif.get("resource_name", "unknown")
        timing = notif.get("timing", "delayed")

        handler_name = f"{notif.get('resource_type')}_{resource_name}_{action}"
        handlers_yaml += f"  - name: {handler_name}\n"
        handlers_yaml += "    debug:\n"
        handlers_yaml += (
            f"      msg: 'Handler triggered by notification - "
            f"{action} {resource_name}'\n"
        )

        if timing == "immediately":
            handlers_yaml += "    listen: 'immediate_notify'\n"

    return handlers_yaml


def estimate_conversion_complexity(resource_body: str) -> str:
    """
    Estimate complexity level of resource conversion.

    Args:
        resource_body: The resource block content.

    Returns:
        Complexity level: 'simple', 'moderate', 'complex'.

    """
    complexity_factors = 0

    # Guards add complexity
    if "only_if" in resource_body or "not_if" in resource_body:
        complexity_factors += 2

    # Searches add complexity (require pre-processing)
    if "search(" in resource_body:
        complexity_factors += 3

    # Notifications add complexity
    if "notifies" in resource_body or "subscribes" in resource_body:
        complexity_factors += 1

    # Multiple actions or nested blocks
    action_count = len(re.findall(r"action\s*:", resource_body))
    complexity_factors += action_count

    # Lazy evaluation adds complexity
    if "lazy" in resource_body:
        complexity_factors += 1

    # Map to complexity levels
    if complexity_factors >= 5:
        return "complex"
    elif complexity_factors >= 2:
        return "moderate"
    return "simple"
